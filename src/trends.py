"""Long-term climate trend analysis (statistics module).

Techniques used (all interview-friendly):
1. Ordinary Least Squares linear trend      -> slope per decade + p-value
2. Theil-Sen robust slope                   -> outlier-resistant trend
3. Mann-Kendall non-parametric test         -> is the trend monotonic?
4. Total change over the record             -> absolute warming since 1990
5. Seasonal shift                          -> is the hottest day moving?
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# statistical building blocks (kept pure so tests can call them directly)
# ---------------------------------------------------------------------------
def linear_trend(x: np.ndarray, y: np.ndarray) -> dict:
    """OLS fit of y on x. Returns slope, intercept, r2, p-value."""
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x, float)[mask], np.asarray(y, float)[mask]
    res = stats.linregress(x, y)
    return {
        "slope": float(res.slope),
        "intercept": float(res.intercept),
        "r2": float(res.rvalue**2),
        "p_value": float(res.pvalue),
        "stderr": float(res.stderr),
        "slope_per_decade": float(res.slope * 10),
    }


def theil_sen_slope(x: np.ndarray, y: np.ndarray) -> float:
    """Robust slope (median of all pairwise slopes)."""
    mask = np.isfinite(x) & np.isfinite(y)
    slope, _, _, _ = stats.theilslopes(np.asarray(y, float)[mask],
                                       np.asarray(x, float)[mask])
    return float(slope * 10)   # per decade


def mann_kendall(y: np.ndarray) -> dict:
    """Mann-Kendall trend test (no normality assumption).

    H0: no monotonic trend.  p < 0.05 -> trend is significant.
    """
    y = np.asarray(y, dtype=float)
    y = y[np.isfinite(y)]
    n = len(y)
    if n < 5:
        return {"tau": np.nan, "p_value": np.nan, "z": np.nan,
                "trend": "insufficient data"}

    s = 0
    for k in range(n - 1):
        s += int(np.sum(np.sign(y[k + 1:] - y[k])))
    unique, counts = np.unique(y, return_counts=True)
    ties = int(np.sum(counts * (counts - 1) * (2 * counts + 5)))
    var_s = (n * (n - 1) * (2 * n + 5) - ties) / 18.0
    if var_s <= 0:
        return {"tau": 0.0, "p_value": 1.0, "z": 0.0, "trend": "no trend"}

    if s > 0:
        z = (s - 1) / np.sqrt(var_s)
    elif s < 0:
        z = (s + 1) / np.sqrt(var_s)
    else:
        z = 0.0
    p = 2 * stats.norm.sf(abs(z))
    tau = s / (0.5 * n * (n - 1))
    label = "increasing" if (z > 1.96 and p < 0.05) else (
        "decreasing" if (z < -1.96 and p < 0.05) else "no significant trend")
    return {"tau": float(tau), "p_value": float(p), "z": float(z), "trend": label}


# ---------------------------------------------------------------------------
# high level analyses
# ---------------------------------------------------------------------------
def trend_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Per-region long-term trend for every key climate variable."""
    rows = []
    for region, grp in df.groupby("region"):
        yearly = grp.groupby("year").agg(
            temperature_c=("temperature_c", "mean"),
            rainfall_mm=("rainfall_mm", "sum"),
            co2_ppm=("co2_ppm", "mean"),
            sea_level_mm=("sea_level_mm", "mean"),
        ).reset_index()
        x = yearly["year"].to_numpy(float)
        for var, unit in [("temperature_c", "C/decade"),
                          ("rainfall_mm", "mm/decade"),
                          ("co2_ppm", "ppm/decade"),
                          ("sea_level_mm", "mm/decade")]:
            y = yearly[var].to_numpy(float)
            ols = linear_trend(x, y)
            mk = mann_kendall(y)
            rows.append({
                "region": region,
                "variable": var,
                "slope_per_decade": round(ols["slope_per_decade"], 3),
                "theil_sen_per_decade": round(theil_sen_slope(x, y), 3),
                "r2": round(ols["r2"], 3),
                "p_value": float(f"{ols['p_value']:.3e}"),
                "mk_p_value": float(f"{mk['p_value']:.3e}"),
                "mk_trend": mk["trend"],
                "unit": unit,
                "total_change": round(float(y[-1] - y[0]), 2),
            })
    return pd.DataFrame(rows)


def hottest_day_shift(df: pd.DataFrame) -> pd.DataFrame:
    """Does the hottest day of the year move? (seasonal shift evidence)."""
    rows = []
    for (region, year), grp in df.groupby(["region", "year"]):
        if len(grp) < 350:          # need a near-complete year
            continue
        # centre-of-heat: circular mean of dayofyear weighted by temperature
        ang = 2 * np.pi * grp["dayofyear"].to_numpy() / 365.25
        w = grp["temperature_c"].to_numpy()
        mean_ang = np.arctan2(np.sum(np.sin(ang) * w), np.sum(np.cos(ang) * w))
        doy = (mean_ang / (2 * np.pi) * 365.25) % 365.25
        rows.append({"region": region, "year": year, "center_of_heat_doy": float(doy)})
    centre = pd.DataFrame(rows)
    if centre.empty:
        return centre
    out = []
    for region, grp in centre.groupby("region"):
        fit = linear_trend(grp["year"].to_numpy(float),
                           grp["center_of_heat_doy"].to_numpy(float))
        out.append({
            "region": region,
            "shift_days_per_decade": round(fit["slope_per_decade"], 2),
            "r2": round(fit["r2"], 3),
            "p_value": float(f"{fit['p_value']:.3e}"),
        })
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------
def chart_temperature_anomaly_trend(df: pd.DataFrame) -> "Path":
    """Global (all-region mean) annual anomaly with OLS fit + 95 % band."""
    yearly = df.groupby("year")["temp_anomaly_c"].mean().reset_index()
    x = yearly["year"].to_numpy(float)
    y = yearly["temp_anomaly_c"].to_numpy(float)
    fit = linear_trend(x, y)
    yhat = fit["intercept"] + fit["slope"] * x
    resid = y - yhat
    se = np.std(resid, ddof=2)
    n = len(x)
    t_crit = stats.t.ppf(0.975, df=max(1, n - 2))
    band = t_crit * se * np.sqrt(1 / n + (x - x.mean()) ** 2 / np.sum((x - x.mean()) ** 2))

    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.bar(x, y, color=C.PALETTE[0], alpha=0.45, label="Annual anomaly vs 1991-2020")
    ax.plot(x, yhat, color=C.PALETTE[1], lw=2.4,
            label=f"OLS trend = {fit['slope_per_decade']:+.2f} C/decade "
                  f"(R2={fit['r2']:.2f}, p={fit['p_value']:.1e})")
    ax.fill_between(x, yhat - band, yhat + band, color=C.PALETTE[1], alpha=0.18,
                    label="95 % confidence band")
    ax.axhline(0, color="white", lw=1)
    ax.set_title("Global Mean Temperature Anomaly  1990-2024", weight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("Anomaly (C)")
    ax.legend(frameon=False, fontsize=9)
    path = C.FIGURE_DIR / "08_temperature_anomaly_trend.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def chart_trend_coefficients(trends: pd.DataFrame) -> "Path":
    """Bar chart of warming rate per region (C/decade)."""
    t = trends[trends["variable"] == "temperature_c"].sort_values(
        "slope_per_decade", ascending=False)
    fig, ax = plt.subplots(figsize=(9, 4.8))
    bars = ax.bar(t["region"], t["slope_per_decade"], color=C.PALETTE[0],
                  edgecolor="white")
    ax.bar_label(bars, fmt="%+.2f", padding=3, fontsize=9)
    ax.axhline(0, color="white", lw=1)
    ax.set_title("Warming Rate by Region  (C per decade, OLS on annual means)",
                 weight="bold")
    ax.set_ylabel("C / decade")
    ax.tick_params(axis="x", rotation=15)
    path = C.FIGURE_DIR / "09_trend_coefficients.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def chart_rainfall_variability(df: pd.DataFrame) -> "Path":
    """Yearly rainfall vs its rolling mean (variability / extremes)."""
    yearly = df.groupby(["region", "year"], as_index=False)["rainfall_mm"].sum()
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (region, grp) in enumerate(yearly.groupby("region")):
        ax.plot(grp["year"], grp["rainfall_mm"], lw=1.3, alpha=0.65,
                color=C.PALETTE[i % len(C.PALETTE)], label=region)
        roll = grp["rainfall_mm"].rolling(7, min_periods=3).mean()
        ax.plot(grp["year"], roll, lw=2.4, color=C.PALETTE[i % len(C.PALETTE)])
    ax.set_title("Annual Rainfall and 7-Year Rolling Mean", weight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("Total rainfall (mm)")
    ax.legend(frameon=False, fontsize=8, ncol=3)
    path = C.FIGURE_DIR / "10_rainfall_variability.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


# ---------------------------------------------------------------------------
def run_trend_analysis(df: pd.DataFrame) -> dict:
    """Full trend module: tables + charts."""
    trends = trend_by_region(df)
    shifts = hottest_day_shift(df)

    trends.to_csv(C.TABLE_DIR / "trend_analysis.csv", index=False)
    shifts.to_csv(C.TABLE_DIR / "seasonal_shift.csv", index=False)

    figures = {
        "anomaly_trend": chart_temperature_anomaly_trend(df),
        "trend_coefficients": chart_trend_coefficients(trends),
        "rainfall_variability": chart_rainfall_variability(df),
    }
    return {"trends": trends, "shifts": shifts, "figures": figures}


if __name__ == "__main__":  # pragma: no cover
    from .preprocessing import run_preprocessing
    df, _ = run_preprocessing()
    res = run_trend_analysis(df)
    print(res["trends"].to_string(index=False))
