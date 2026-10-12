"""Data cleaning + feature engineering.

Pipeline step:  raw CSV  ->  clean, typed, feature-rich CSV

WHAT THIS MODULE FIXES (typical real-world dirt)
------------------------------------------------
1. duplicate rows (double logger writes)
2. impossible values  (humidity > 100 %, negative rainfall)
3. missing cells (sensor failures)  -> time-aware interpolation per region
4. unsorted / mixed-type dates       -> proper datetime + sort
5. no calendar features              -> year, month, season, decade, doy
6. no climate baseline               -> 1991-2020 monthly normals (WMO style)
7. no anomaly signal                 -> anomaly vs baseline + rolling averages
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C

NUMERIC_COLS = [
    "temperature_c", "rainfall_mm", "humidity_pct",
    "co2_ppm", "sea_level_mm", "wind_speed_ms",
]

SEASON_MAP = {12: "Winter", 1: "Winter", 2: "Winter",
              3: "Spring", 4: "Spring", 5: "Spring",
              6: "Monsoon", 7: "Monsoon", 8: "Monsoon",
              9: "Autumn", 10: "Autumn", 11: "Autumn"}


# ---------------------------------------------------------------------------
def load_raw(path=None) -> pd.DataFrame:
    """Read the raw (dirty) CSV."""
    path = path or C.RAW_CSV
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run `python main.py --generate` first."
        )
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
def clean_data(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Return (clean_df, quality_report)."""
    report: dict[str, int | float] = {}
    report["rows_in"] = int(len(df))

    # 1. drop rows with unparseable dates
    bad_dates = int(df["date"].isna().sum())
    df = df[df["date"].notna()].copy()
    report["rows_bad_date_dropped"] = bad_dates

    # 2. drop exact duplicates
    before = len(df)
    df = df.drop_duplicates().reset_index(drop=True)
    report["duplicate_rows_removed"] = before - len(df)

    # 3. impossible values -> NaN (imputed in step 4)
    nan_before = int(df[NUMERIC_COLS].isna().sum().sum())
    df.loc[df["humidity_pct"] > 100, "humidity_pct"] = np.nan
    df.loc[df["humidity_pct"] < 0, "humidity_pct"] = np.nan
    df.loc[df["rainfall_mm"] < 0, "rainfall_mm"] = np.nan
    df.loc[df["temperature_c"] < -90, "temperature_c"] = np.nan
    df.loc[df["wind_speed_ms"] < 0, "wind_speed_ms"] = np.nan
    report["impossible_values_set_nan"] = int(df[NUMERIC_COLS].isna().sum().sum() - nan_before)

    # 4. sort then interpolate inside each region
    df = df.sort_values(["region", "date"]).reset_index(drop=True)
    missing_before = int(df[NUMERIC_COLS].isna().sum().sum())
    report["missing_cells_before"] = missing_before

    for region, grp in df.groupby("region", sort=False):
        idx = grp.index
        for col in NUMERIC_COLS:
            s = df.loc[idx, col]
            if s.isna().any():
                df.loc[idx, col] = s.interpolate(
                    method="linear", limit_direction="both"
                )
    # any column that is entirely NaN inside a region -> global fill
    for col in NUMERIC_COLS:
        if df[col].isna().any():
            df[col] = df[col].interpolate(method="linear", limit_direction="both")
            df[col] = df[col].fillna(df[col].median())

    report["missing_cells_after"] = int(df[NUMERIC_COLS].isna().sum().sum())
    report["rows_out"] = int(len(df))
    report["missing_pct_before"] = round(100 * report["missing_cells_before"]
                                         / max(1, len(df) * len(NUMERIC_COLS)), 3)
    report["missing_pct_after"] = round(100 * report["missing_cells_after"]
                                        / max(1, len(df) * len(NUMERIC_COLS)), 3)
    return df.reset_index(drop=True), report


# ---------------------------------------------------------------------------
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar, baseline (climatology), anomaly and rolling features."""
    df = df.copy()

    # --- calendar -----------------------------------------------------------
    df["year"] = df["date"].dt.year.astype("int32")
    df["month"] = df["date"].dt.month.astype("int32")
    df["day"] = df["date"].dt.day.astype("int32")
    df["dayofyear"] = df["date"].dt.dayofyear.astype("int32")
    df["season"] = df["month"].map(SEASON_MAP)
    df["decade"] = (df["year"] // 10 * 10).astype("int32")

    # --- 1991-2020 monthly normals (climate baseline) ------------------------
    lo, hi = C.BASELINE_PERIOD
    mask = df["year"].between(lo, hi)
    clim = (
        df.loc[mask]
        .groupby(["region", "month"], as_index=False)
        .agg(temp_normal_c=("temperature_c", "mean"),
             rain_normal_mm=("rainfall_mm", "mean"))
    )
    df = df.merge(clim, on=["region", "month"], how="left")

    # --- anomalies vs baseline ---------------------------------------------
    df["temp_anomaly_c"] = (df["temperature_c"] - df["temp_normal_c"]).round(3)
    df["rain_anomaly_mm"] = (df["rainfall_mm"] - df["rain_normal_mm"]).round(3)

    # --- rolling averages (weather -> climate) ------------------------------
    g = df.groupby("region", sort=False)
    df["temp_roll_30d_c"] = g["temperature_c"].transform(
        lambda s: s.rolling(30, min_periods=10).mean()).round(3)
    df["temp_roll_365d_c"] = g["temperature_c"].transform(
        lambda s: s.rolling(365, min_periods=100).mean()).round(3)
    df["rain_roll_30d_mm"] = g["rainfall_mm"].transform(
        lambda s: s.rolling(30, min_periods=10).sum()).round(2)
    df["hum_roll_30d_pct"] = g["humidity_pct"].transform(
        lambda s: s.rolling(30, min_periods=10).mean()).round(2)

    # --- heat index proxy (simplified NOAA style) ---------------------------
    df["heat_index"] = (
        df["temperature_c"]
        + 0.33 * df["humidity_pct"]
        - 0.7 * 10
        - 4.0
    ).round(2)

    return df


# ---------------------------------------------------------------------------
def run_preprocessing(raw_path=None) -> tuple[pd.DataFrame, dict]:
    """Full step: load -> clean -> engineer -> save processed CSV + report."""
    raw = load_raw(raw_path)
    clean, report = clean_data(raw)
    featured = engineer_features(clean)

    featured.to_csv(C.CLEAN_CSV, index=False)

    rep_df = pd.DataFrame(
        [{"metric": k, "value": v} for k, v in report.items()]
    )
    rep_df.to_csv(C.TABLE_DIR / "data_quality_report.csv", index=False)
    return featured, report


if __name__ == "__main__":  # pragma: no cover
    df, rep = run_preprocessing()
    print(rep)
    print(df.head(3).to_string())
