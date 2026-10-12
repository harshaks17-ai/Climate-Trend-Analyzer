"""Forecasting module - estimate future climate patterns.

Approach (beginner-friendly yet industry standard):
1. Resample daily data to MONTHLY series (climate works on months/years).
2. Hold out the last 24 months -> honest BACKTEST (MAE / RMSE / MAPE).
3. Fit Holt-Winters Exponential Smoothing (level + trend + seasonality).
   - optional SARIMAX for the "advanced" path (method="sarima")
   - linear trend + Fourier seasonality as a zero-dependency fallback
4. Forecast 5 years into the future for every region.
5. Project global CO2 and sea level with a linear trend to 2035.
"""

from __future__ import annotations

import warnings

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from . import config as C

sns.set_theme(style="whitegrid", palette=C.PALETTE)
plt.rcParams.update(C.MPL_THEME)
warnings.filterwarnings("ignore", category=FutureWarning)

HORIZON_MONTHS = 60          # 5 years ahead
TEST_MONTHS = 24             # backtest window


# ---------------------------------------------------------------------------
# data preparation
# ---------------------------------------------------------------------------
def prepare_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Long format: date (month start), region, temperature_c, rainfall_mm..."""
    monthly = (
        df.set_index("date")
        .groupby("region")
        .resample("MS")
        .agg(temperature_c=("temperature_c", "mean"),
             rainfall_mm=("rainfall_mm", "sum"),
             co2_ppm=("co2_ppm", "mean"),
             sea_level_mm=("sea_level_mm", "mean"))
        .reset_index()
        .dropna(subset=["temperature_c"])
    )
    return monthly


# ---------------------------------------------------------------------------
# model backends
# ---------------------------------------------------------------------------
def _holt_winters(train: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    model = ExponentialSmoothing(
        train.to_numpy(dtype=float),
        trend="add", seasonal="add", seasonal_periods=12,
        initialization_method="estimated",
    ).fit(optimized=True)
    return np.asarray(model.forecast(horizon), dtype=float)


def _sarima(train: pd.Series, horizon: int) -> np.ndarray:
    from statsmodels.tsa.statespace.sarimax import SARIMAX
    model = SARIMAX(
        train.to_numpy(dtype=float),
        order=(1, 1, 1), seasonal_order=(1, 1, 1, 12),
        enforce_stationarity=False, enforce_invertibility=False,
    ).fit(disp=False, maxiter=200)
    return np.asarray(model.forecast(horizon), dtype=float)


def _linear_seasonal(train: pd.Series, horizon: int) -> np.ndarray:
    """OLS trend + Fourier terms (month seasonality). No statsmodels needed."""
    y = train.to_numpy(dtype=float)
    t = np.arange(len(y))
    x0 = np.ones(len(y))
    terms = [x0, t]
    for k in (1, 2):
        terms.append(np.sin(2 * np.pi * k * t / 12))
        terms.append(np.cos(2 * np.pi * k * t / 12))
    X = np.column_stack(terms)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)

    tf = np.arange(len(y), len(y) + horizon)
    fterms = [np.ones(horizon), tf]
    for k in (1, 2):
        fterms.append(np.sin(2 * np.pi * k * tf / 12))
        fterms.append(np.cos(2 * np.pi * k * tf / 12))
    Xf = np.column_stack(fterms)
    return Xf @ beta


BACKENDS = {"holt_winters": _holt_winters, "sarima": _sarima, "linear": _linear_seasonal}


def forecast_series(series: pd.Series, horizon: int = HORIZON_MONTHS,
                    method: str = "holt_winters") -> np.ndarray:
    """Forecast a monthly series; falls back to the linear model if needed."""
    fn = BACKENDS.get(method, _holt_winters)
    try:
        return fn(series, horizon)
    except Exception:
        return _linear_seasonal(series, horizon)


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------
def backtest_series(series: pd.Series, method: str = "holt_winters",
                    test_months: int = TEST_MONTHS) -> dict:
    """Train on data[:-test], predict the hold-out, score it."""
    if len(series) <= test_months + 24:
        return {"mae": np.nan, "rmse": np.nan, "mape": np.nan, "method": method}
    train, test = series.iloc[:-test_months], series.iloc[-test_months:]
    pred = forecast_series(train, horizon=test_months, method=method)[:len(test)]
    err = pred - test.to_numpy(dtype=float)
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    denom = np.where(np.abs(test.to_numpy(dtype=float)) < 1e-9, np.nan,
                     np.abs(test.to_numpy(dtype=float)))
    mape = float(np.nanmean(np.abs(err) / denom) * 100)
    return {"mae": round(mae, 3), "rmse": round(rmse, 3),
            "mape": round(mape, 2), "method": method}


# ---------------------------------------------------------------------------
# high level runner
# ---------------------------------------------------------------------------
def run_forecast(df: pd.DataFrame, method: str = "holt_winters") -> dict:
    """Forecast temperature for every region + global CO2 / sea level."""
    monthly = prepare_monthly(df)
    forecasts, acc_rows = [], []

    for region, grp in monthly.groupby("region"):
        grp = grp.sort_values("date").reset_index(drop=True)
        series = grp.set_index("date")["temperature_c"]

        acc_rows.append({"region": region, "variable": "temperature_c",
                         **backtest_series(series, method=method)})

        fc = forecast_series(series, HORIZON_MONTHS, method=method)
        future_dates = pd.date_range(
            grp["date"].max() + pd.offsets.MonthBegin(1), periods=HORIZON_MONTHS,
            freq="MS")
        forecasts.append(pd.DataFrame({
            "date": future_dates, "region": region,
            "forecast_temp_c": np.round(fc, 2),
        }))
    forecast_df = pd.concat(forecasts, ignore_index=True)

    # ---- global projections (CO2 + sea level) -----------------------------
    projections = []
    yearly = df.groupby("year", as_index=False).agg(
        co2_ppm=("co2_ppm", "mean"), sea_level_mm=("sea_level_mm", "mean"))
    for var, unit in [("co2_ppm", "ppm"), ("sea_level_mm", "mm")]:
        x = yearly["year"].to_numpy(float)
        y = yearly[var].to_numpy(float)
        mask = x <= C.END_YEAR
        fit = stats.linregress(x[mask], y[mask])
        years_f = np.arange(C.END_YEAR + 1, C.END_YEAR + 11)
        for yr, val in zip(years_f, fit.intercept + fit.slope * years_f):
            projections.append({"year": int(yr), "variable": var,
                                "unit": unit, "value": round(float(val), 2),
                                "slope_per_decade": round(float(fit.slope * 10), 2),
                                "r2": round(float(fit.rvalue**2), 4)})
    projection_df = pd.DataFrame(projections)

    # ---- save --------------------------------------------------------------
    forecast_df.to_csv(C.TABLE_DIR / "temperature_forecast.csv", index=False)
    accuracy_df = pd.DataFrame(acc_rows)
    accuracy_df.to_csv(C.TABLE_DIR / "forecast_accuracy.csv", index=False)
    projection_df.to_csv(C.TABLE_DIR / "global_projections.csv", index=False)

    figures = {
        "forecast": chart_forecast(monthly, forecast_df),
        "backtest": chart_backtest(monthly, method=method),
        "projections": chart_projections(yearly, projection_df),
    }
    return {"monthly": monthly, "forecast": forecast_df,
            "accuracy": accuracy_df, "projections": projection_df,
            "figures": figures}


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------
def chart_forecast(monthly: pd.DataFrame, forecast_df: pd.DataFrame) -> "Path":
    """History + 5-year forecast per region."""
    fig, axes = plt.subplots(len(C.REGIONS), 1, figsize=(11, 3.1 * len(C.REGIONS)),
                             sharex=False)
    axes = np.atleast_1d(axes)
    for ax, (region, grp) in zip(axes, monthly.groupby("region")):
        fc = forecast_df[forecast_df["region"] == region]
        ax.plot(grp["date"], grp["temperature_c"], lw=1.1, color=C.PALETTE[0],
                label="observed monthly mean")
        ax.plot(fc["date"], fc["forecast_temp_c"], lw=2.2, color=C.PALETTE[1],
                ls="--", label=f"forecast ({HORIZON_MONTHS // 12} yr)")
        ax.axvline(pd.Timestamp(f"{C.END_YEAR}-12-01"), color="white",
                   lw=1, alpha=0.6)
        ax.set_title(region, weight="bold", loc="left")
        ax.set_ylabel("C")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    axes[-1].set_xlabel("Date")
    fig.suptitle("Monthly Temperature: Observed vs Forecast", weight="bold", y=1.0)
    path = C.FIGURE_DIR / "14_temperature_forecast.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def chart_backtest(monthly: pd.DataFrame, method: str) -> "Path":
    """Honest hold-out test: predicted vs actual for the last 24 months."""
    region = C.REGIONS[0][0]
    grp = monthly[monthly["region"] == region].sort_values("date")
    series = grp.set_index("date")["temperature_c"]
    train, test = series.iloc[:-TEST_MONTHS], series.iloc[-TEST_MONTHS:]
    pred = forecast_series(train, horizon=TEST_MONTHS, method=method)[:len(test)]

    fig, ax = plt.subplots(figsize=(11, 4.6))
    ax.plot(train.index, train, lw=1.2, color=C.PALETTE[0], label="train")
    ax.plot(test.index, test, lw=2.0, color=C.PALETTE[2], label="actual (hold-out)")
    ax.plot(test.index, pred, lw=2.0, ls="--", color=C.PALETTE[1],
            label="predicted (backtest)")
    err = np.abs(pred - test.to_numpy())
    ax.set_title(f"Backtest - {region}  (MAE={np.mean(err):.2f} C, "
                 f"{TEST_MONTHS} months held out)", weight="bold")
    ax.set_xlabel("Date"); ax.set_ylabel("Temperature (C)")
    ax.legend(frameon=False, fontsize=9)
    path = C.FIGURE_DIR / "15_forecast_backtest.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def chart_projections(yearly: pd.DataFrame, projection_df: pd.DataFrame) -> "Path":
    """CO2 and sea level: history + linear projection to +10 years."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    for ax, var, color, unit in [
        (axes[0], "co2_ppm", C.PALETTE[3], "ppm"),
        (axes[1], "sea_level_mm", C.PALETTE[4], "mm"),
    ]:
        ax.plot(yearly["year"], yearly[var], lw=2.0, color=color, label="observed")
        proj = projection_df[projection_df["variable"] == var]
        ax.plot(proj["year"], proj["value"], lw=2.0, ls="--",
                color=C.PALETTE[1], marker="o", ms=4, label="projection")
        ax.set_title(f"{var.replace('_', ' ').title()} -> +10 yr", weight="bold")
        ax.set_ylabel(unit); ax.legend(frameon=False, fontsize=8)
    fig.suptitle("Global Projections (linear trend continuation)",
                 weight="bold", y=1.02)
    path = C.FIGURE_DIR / "16_global_projections.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


if __name__ == "__main__":  # pragma: no cover
    from .preprocessing import run_preprocessing
    df, _ = run_preprocessing()
    res = run_forecast(df)
    print(res["accuracy"].to_string(index=False))
    print(res["projections"].head().to_string(index=False))
