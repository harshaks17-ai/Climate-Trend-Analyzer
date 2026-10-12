"""Exploratory Data Analysis (EDA) - tables + static charts.

Produces the "first look" artefacts every data-analyst project needs:
summary statistics, missing-value audit, correlations, climatology,
yearly/decadal aggregates - plus publication-style PNG charts.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")  # headless: works on servers / CI without a display

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from . import config as C

sns.set_theme(style="whitegrid", palette=C.PALETTE)
plt.rcParams.update(C.MPL_THEME)

VALUE_COLS = ["temperature_c", "rainfall_mm", "humidity_pct",
              "co2_ppm", "sea_level_mm", "wind_speed_ms"]


# ---------------------------------------------------------------------------
# tables
# ---------------------------------------------------------------------------
def summary_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Build the core EDA tables (saved later as CSV)."""
    tables: dict[str, pd.DataFrame] = {}

    # 1. descriptive statistics per region
    agg = (
        df.groupby("region")[VALUE_COLS]
        .agg(["mean", "std", "min", "max"])
        .round(2)
    )
    agg.columns = [f"{var}_{stat}" for var, stat in agg.columns]
    tables["summary_by_region"] = agg.reset_index()

    # 2. missing value audit (should be zero after preprocessing)
    tables["missing_values"] = (
        pd.DataFrame({
            "column": df.columns,
            "missing_count": [int(df[c].isna().sum()) for c in df.columns],
            "missing_pct": [round(100 * df[c].isna().mean(), 3) for c in df.columns],
        })
        .sort_values("missing_pct", ascending=False)
        .reset_index(drop=True)
    )

    # 3. correlation matrix (numeric core)
    tables["correlation_matrix"] = (
        df[VALUE_COLS + ["temp_anomaly_c"]].corr(numeric_only=True).round(3)
    )

    # 4. monthly climatology
    tables["monthly_climatology"] = (
        df.groupby(["region", "month"])
        .agg(mean_temp_c=("temperature_c", "mean"),
             total_rain_mm=("rainfall_mm", "mean"),
             mean_humidity_pct=("humidity_pct", "mean"))
        .round(2)
        .reset_index()
    )

    # 5. yearly aggregates (one row per region-year)
    tables["yearly_summary"] = (
        df.groupby(["region", "year"])
        .agg(mean_temp_c=("temperature_c", "mean"),
             total_rain_mm=("rainfall_mm", "sum"),
             max_temp_c=("temperature_c", "max"),
             hot_days=("temperature_c", lambda s: int((s > s.mean() + 2).sum())),
             co2_ppm=("co2_ppm", "mean"),
             sea_level_mm=("sea_level_mm", "mean"))
        .round(2)
        .reset_index()
    )

    # 6. decadal summary (long-term comparison)
    annual_rain = (
        df.groupby(["region", "decade", "year"], as_index=False)["rainfall_mm"]
        .sum()
        .groupby(["region", "decade"], as_index=False)["rainfall_mm"]
        .mean()
        .rename(columns={"rainfall_mm": "total_rain_mm_per_year"})
    )
    tables["decadal_summary"] = (
        df.groupby(["region", "decade"])
        .agg(mean_temp_c=("temperature_c", "mean"),
             mean_co2_ppm=("co2_ppm", "mean"),
             mean_sea_level_mm=("sea_level_mm", "mean"))
        .round(2)
        .reset_index()
        .merge(annual_rain, on=["region", "decade"], how="left")
        .round(2)
    )
    return tables


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------
def _save(fig, name: str):
    path = C.FIGURE_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


def chart_yearly_temperature(tables: dict, df: pd.DataFrame) -> "Path":
    """Long-term annual mean temperature per region."""
    yearly = tables["yearly_summary"]
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for i, (region, grp) in enumerate(yearly.groupby("region")):
        ax.plot(grp["year"], grp["mean_temp_c"], lw=1.8,
                color=C.PALETTE[i % len(C.PALETTE)], label=region)
        z = np.polyfit(grp["year"], grp["mean_temp_c"], 1)
        ax.plot(grp["year"], np.polyval(z, grp["year"]), lw=1.0, ls="--",
                color=C.PALETTE[i % len(C.PALETTE)], alpha=0.7)
    ax.set_title("Annual Mean Temperature Trend by Region  (dashed = linear fit)",
                 weight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("Temperature (C)")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    return _save(fig, "01_yearly_temperature_trend.png")


def chart_monthly_climatology(tables: dict) -> "Path":
    """1991-2020 monthly normals: temperature and rainfall together."""
    clim = tables["monthly_climatology"].groupby("month").agg(
        t=("mean_temp_c", "mean"), r=("total_rain_mm", "mean")).reset_index()
    fig, ax1 = plt.subplots(figsize=(11, 5))
    ax2 = ax1.twinx()
    ax2.bar(clim["month"], clim["r"], color=C.PALETTE[1], alpha=0.30, label="Rainfall (mm)")
    ax1.plot(clim["month"], clim["t"], color=C.PALETTE[0], lw=2.4,
             marker="o", ms=5, label="Temperature (C)")
    ax1.set_xticks(range(1, 13))
    ax1.set_xlabel("Month"); ax1.set_ylabel("Temperature (C)")
    ax2.set_ylabel("Rainfall (mm)")
    ax1.set_title("Monthly Climate Normals  (1991-2020 baseline)", weight="bold")
    lines = ax1.get_lines() + ax2.patches
    ax1.legend(lines, [l.get_label() for l in lines], frameon=False, loc="upper left")
    return _save(fig, "02_monthly_climatology.png")


def chart_rainfall_trend(tables: dict) -> "Path":
    """Annual rainfall totals per region."""
    yearly = tables["yearly_summary"]
    fig, ax = plt.subplots(figsize=(11, 5))
    for i, (region, grp) in enumerate(yearly.groupby("region")):
        ax.plot(grp["year"], grp["total_rain_mm"], lw=1.4,
                color=C.PALETTE[i % len(C.PALETTE)], label=region)
    ax.set_title("Annual Total Rainfall by Region", weight="bold")
    ax.set_xlabel("Year"); ax.set_ylabel("Rainfall (mm / year)")
    ax.legend(frameon=False, ncol=3, fontsize=8)
    return _save(fig, "03_rainfall_trend.png")


def chart_correlation(tables: dict) -> "Path":
    """Heatmap of variable relationships."""
    corr = tables["correlation_matrix"]
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm",
                center=0, square=True, cbar_kws={"shrink": 0.8}, ax=ax)
    ax.set_title("Feature Correlation Matrix", weight="bold")
    return _save(fig, "04_correlation_heatmap.png")


def chart_anomaly_distribution(df: pd.DataFrame) -> "Path":
    """Distribution of temperature anomalies (baseline = 1991-2020)."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    sample = df["temp_anomaly_c"].dropna().sample(
        min(20000, len(df)), random_state=C.SEED)
    sns.histplot(sample, bins=80, kde=True, color=C.PALETTE[0], ax=ax)
    ax.axvline(0, color="white", lw=1.2)
    ax.axvline(C.ANOMALY_Z_THRESHOLD * sample.std(), color=C.PALETTE[1],
               ls="--", label=f"+{C.ANOMALY_Z_THRESHOLD} sigma threshold")
    ax.set_title("Temperature Anomaly Distribution vs 1991-2020 Normal",
                 weight="bold")
    ax.set_xlabel("Anomaly (C)"); ax.legend(frameon=False)
    return _save(fig, "05_anomaly_distribution.png")


def chart_decadal_comparison(tables: dict) -> "Path":
    """Decade-by-decade warming comparison."""
    dec = tables["decadal_summary"]
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=dec, x="decade", y="mean_temp_c", hue="region",
                palette=C.PALETTE[:max(1, dec["region"].nunique())], ax=ax)
    ax.set_title("Mean Temperature by Decade and Region", weight="bold")
    ax.set_xlabel("Decade"); ax.set_ylabel("Temperature (C)")
    ax.legend(frameon=False, fontsize=8, ncol=2)
    return _save(fig, "06_decadal_comparison.png")


def chart_distribution_grid(df: pd.DataFrame) -> "Path":
    """2x3 grid of value distributions."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 7))
    for ax, col in zip(axes.ravel(), VALUE_COLS):
        sns.histplot(df[col].dropna(), bins=60, kde=True,
                     color=C.PALETTE[0], ax=ax)
        ax.set_title(col, weight="bold")
    fig.suptitle("Distribution of Climate Variables", weight="bold", y=1.01)
    fig.tight_layout()
    return _save(fig, "07_distribution_grid.png")


# ---------------------------------------------------------------------------
def run_eda(df: pd.DataFrame) -> dict:
    """Generate every EDA table + chart. Returns {name: path}."""
    tables = summary_tables(df)

    for name, tbl in tables.items():
        # the correlation matrix must keep its row index
        tbl.to_csv(C.TABLE_DIR / f"{name}.csv", index=(name == "correlation_matrix"))

    figures = {
        "yearly_temperature": chart_yearly_temperature(tables, df),
        "monthly_climatology": chart_monthly_climatology(tables),
        "rainfall_trend": chart_rainfall_trend(tables),
        "correlation": chart_correlation(tables),
        "anomaly_distribution": chart_anomaly_distribution(df),
        "decadal_comparison": chart_decadal_comparison(tables),
        "distribution_grid": chart_distribution_grid(df),
    }
    return {"tables": {k: C.TABLE_DIR / f"{k}.csv" for k in tables},
            "figures": figures}


if __name__ == "__main__":  # pragma: no cover
    from .preprocessing import run_preprocessing
    df, _ = run_preprocessing()
    res = run_eda(df)
    print(res)
