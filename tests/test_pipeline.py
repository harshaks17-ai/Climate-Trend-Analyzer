"""End-to-end + unit tests for the Climate Trend Analyzer pipeline.

Run with:   pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as C  # noqa: E402


# ---------------------------------------------------------------------------
# fixture: isolated, miniature environment (5 years of data in tmp folders)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def env(tmp_path_factory):
    """Patch every output path to a temp folder and build a small dataset."""
    root = tmp_path_factory.mktemp("climate")
    paths = {
        "DATA_DIR": root / "data",
        "RAW_DIR": root / "data" / "raw",
        "PROCESSED_DIR": root / "data" / "processed",
        "OUTPUT_DIR": root / "outputs",
        "FIGURE_DIR": root / "outputs" / "figures",
        "TABLE_DIR": root / "outputs" / "tables",
        "REPORT_DIR": root / "outputs" / "reports",
        "MODEL_DIR": root / "models",
        "IMAGE_DIR": root / "images",
        "DOC_DIR": root / "docs",
    }
    for name, path in paths.items():
        setattr(C, name, path)
        path.mkdir(parents=True, exist_ok=True)
    C.RAW_CSV = C.RAW_DIR / "climate_raw.csv"
    C.CLEAN_CSV = C.PROCESSED_DIR / "climate_clean.csv"

    from src.simulation import generate_climate_dataset, save_dataset
    raw, events = generate_climate_dataset(start_year=1990, end_year=1997)
    save_dataset(raw)
    return {"raw": raw, "events": events, "root": root}


@pytest.fixture(scope="module")
def clean(env):
    from src.preprocessing import run_preprocessing
    df, report = run_preprocessing()
    return {"df": df, "report": report}


# ---------------------------------------------------------------------------
# 1. simulation
# ---------------------------------------------------------------------------
def test_simulation_shape_and_columns(env):
    raw = env["raw"]
    assert len(raw) > 10_000
    for col in ["date", "region", "temperature_c", "rainfall_mm", "humidity_pct",
                "co2_ppm", "sea_level_mm", "wind_speed_ms", "injected_event"]:
        assert col in raw.columns, f"missing column {col}"
    assert raw["region"].nunique() == len(C.REGIONS)


def test_simulation_contains_quality_issues(env):
    raw = env["raw"]
    assert raw.duplicated().sum() > 0, "expected duplicate rows in raw data"
    assert raw.isna().sum().sum() > 0, "expected missing cells in raw data"
    assert (raw["humidity_pct"] > 100).any(), "expected impossible humidity values"
    assert (raw["rainfall_mm"] < 0).any(), "expected negative rainfall values"


def test_simulation_ground_truth_events(env):
    events = env["events"]
    assert len(events) > 10
    assert set(events["event_type"]) == {"heatwave", "cold_snap", "flood"}
    raw = env["raw"]
    assert (raw["injected_event"] != "none").sum() > 100


def test_simulation_is_reproducible(env):
    from src.simulation import generate_climate_dataset
    a, _ = generate_climate_dataset(start_year=1990, end_year=1993)
    b, _ = generate_climate_dataset(start_year=1990, end_year=1993)
    pd.testing.assert_frame_equal(
        a.drop(columns=["injected_event"]), b.drop(columns=["injected_event"]))


# ---------------------------------------------------------------------------
# 2. preprocessing
# ---------------------------------------------------------------------------
def test_cleaning_removes_duplicates_and_nans(clean):
    df = clean["df"]
    assert df.duplicated(subset=["date", "region"]).sum() == 0
    numeric = ["temperature_c", "rainfall_mm", "humidity_pct",
               "co2_ppm", "sea_level_mm", "wind_speed_ms"]
    assert df[numeric].isna().sum().sum() == 0


def test_cleaning_fixes_impossible_values(clean):
    df = clean["df"]
    assert df["humidity_pct"].between(0, 100).all()
    assert (df["rainfall_mm"] >= 0).all()
    assert (df["wind_speed_ms"] >= 0).all()


def test_features_created(clean):
    df = clean["df"]
    for col in ["year", "month", "season", "decade", "temp_normal_c",
                "rain_normal_mm", "temp_anomaly_c", "temp_roll_365d_c",
                "rain_roll_30d_mm", "heat_index"]:
        assert col in df.columns, f"missing feature {col}"
    assert set(df["season"]) == {"Winter", "Spring", "Monsoon", "Autumn"}


def test_dates_sorted_within_region(clean):
    df = clean["df"]
    for _, grp in df.groupby("region"):
        assert grp["date"].is_monotonic_increasing


# ---------------------------------------------------------------------------
# 3. statistical building blocks
# ---------------------------------------------------------------------------
def test_linear_trend_on_known_line():
    from src.trends import linear_trend
    x = np.arange(1990, 2020, dtype=float)
    y = 3.0 + 0.2 * x
    fit = linear_trend(x, y)
    assert fit["slope"] == pytest.approx(0.2, abs=1e-9)
    assert fit["slope_per_decade"] == pytest.approx(2.0, abs=1e-8)
    assert fit["r2"] == pytest.approx(1.0, abs=1e-9)
    assert fit["p_value"] < 0.001


def test_theil_sen_robust_to_outlier():
    from src.trends import theil_sen_slope
    x = np.arange(30, dtype=float)
    y = 0.5 * x
    y[10] += 50                       # single huge outlier
    assert theil_sen_slope(x, y) == pytest.approx(5.0, abs=0.5)


def test_mann_kendall_detects_increasing():
    from src.trends import mann_kendall
    rng = np.random.default_rng(0)
    y = np.cumsum(rng.normal(1.0, 0.3, 80))
    res = mann_kendall(y)
    assert res["trend"] == "increasing"
    assert res["p_value"] < 0.05


def test_mann_kendall_flat_series():
    from src.trends import mann_kendall
    rng = np.random.default_rng(1)
    res = mann_kendall(rng.normal(0, 1, 100))
    assert res["trend"] == "no significant trend"


# ---------------------------------------------------------------------------
# 4. trends module
# ---------------------------------------------------------------------------
def test_trends_table(clean):
    from src.trends import trend_by_region
    trends = trend_by_region(clean["df"])
    assert len(trends) == len(C.REGIONS) * 4
    temp = trends[trends["variable"] == "temperature_c"]
    assert (temp["slope_per_decade"] > 0).sum() >= 3, "most regions should warm"
    assert temp["slope_per_decade"].mean() > 0
    co2 = trends[trends["variable"] == "co2_ppm"]
    assert (co2["slope_per_decade"] > 0).all()


def test_seasonal_shift_table(clean):
    from src.trends import hottest_day_shift
    shifts = hottest_day_shift(clean["df"])
    assert set(shifts["region"]) == {r[0] for r in C.REGIONS}


# ---------------------------------------------------------------------------
# 5. anomaly detection
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def anomaly(clean):
    from src.anomaly import run_anomaly_detection
    return run_anomaly_detection(clean["df"])


def test_anomaly_metrics_against_ground_truth(anomaly):
    m = anomaly["metrics"].iloc[0]
    assert m["day_recall"] >= 0.45
    assert m["day_precision"] >= 0.40
    assert m["event_recall"] >= 0.70
    assert 0 < m["total_flagged_days"] < 0.15 * m["true_negative"] + 5000


def test_anomaly_output_columns(anomaly):
    flagged = anomaly["flagged"]
    for col in ["z_temp", "flag_z", "flag_rain", "flag_iforest",
                "vote_count", "is_anomaly", "anomaly_type", "anomaly_score"]:
        assert col in flagged.columns
    assert set(flagged["anomaly_type"].unique()) <= {
        "heat_extreme", "cold_extreme", "rain_extreme", "multivariate", "normal"}


def test_top_anomalies_sorted(anomaly):
    top = anomaly["top"]
    assert len(top) > 0
    assert top["anomaly_score"].is_monotonic_decreasing


# ---------------------------------------------------------------------------
# 6. forecasting
# ---------------------------------------------------------------------------
def test_monthly_preparation(clean):
    from src.forecast import prepare_monthly
    monthly = prepare_monthly(clean["df"])
    assert monthly["date"].dt.day.eq(1).all(), "monthly index must start on the 1st"
    assert monthly.groupby("region").size().min() >= 70


def test_backtest_reasonable_error(clean):
    from src.forecast import backtest_series, prepare_monthly
    monthly = prepare_monthly(clean["df"])
    series = (monthly[monthly["region"] == C.REGIONS[0][0]]
              .sort_values("date").set_index("date")["temperature_c"])
    acc = backtest_series(series, method="holt_winters")
    assert acc["mae"] < 3.0
    assert acc["rmse"] < 4.5


def test_forecast_runs_and_projects_warming(clean):
    from src.forecast import run_forecast
    res = run_forecast(clean["df"], method="holt_winters")
    fc = res["forecast"]
    assert fc["region"].nunique() == len(C.REGIONS)
    assert len(fc) == len(C.REGIONS) * 60
    proj = res["projections"]
    co2 = proj[proj["variable"] == "co2_ppm"].sort_values("year")
    sea = proj[proj["variable"] == "sea_level_mm"].sort_values("year")
    assert co2["value"].is_monotonic_increasing
    assert sea["value"].is_monotonic_increasing


def test_linear_forecast_fallback(clean):
    from src.forecast import run_forecast
    res = run_forecast(clean["df"], method="linear")
    assert not res["forecast"].empty


# ---------------------------------------------------------------------------
# 7. EDA + report + visuals
# ---------------------------------------------------------------------------
def test_eda_tables_and_figures(clean):
    from src.eda import run_eda
    res = run_eda(clean["df"])
    assert len(res["tables"]) >= 5
    assert all(p.exists() for p in res["figures"].values())
    corr = pd.read_csv(C.TABLE_DIR / "correlation_matrix.csv", index_col=0)
    assert corr.loc["temperature_c", "temperature_c"] == pytest.approx(1.0)


def test_report_content(clean, env, anomaly):
    from src.forecast import run_forecast
    from src.report import build_report, save_report
    from src.trends import run_trend_analysis
    trends = run_trend_analysis(clean["df"])
    fc = run_forecast(clean["df"])
    content = build_report(
        clean_df=clean["df"], quality=clean["report"],
        trends=trends["trends"], anomaly_metrics=anomaly["metrics"],
        anomaly_summary=anomaly["summary"], forecast_accuracy=fc["accuracy"],
        projections=fc["projections"])
    assert "Key Findings" in content
    assert "Warming is confirmed" in content
    path = save_report(content)
    assert path.exists() and path.stat().st_size > 1000


def test_visuals_return_plotly_figures(clean, anomaly):
    from plotly.graph_objects import Figure
    from src.visuals import (fig_climate_pillar, fig_scatter3d_anomalies,
                             fig_surface_temperature, fig_anomaly_heatmap,
                             fig_animated_yearly, fig_yearly_lines)
    df = clean["df"]
    assert isinstance(fig_surface_temperature(df), Figure)
    assert isinstance(fig_surface_temperature(df, region=C.REGIONS[0][0]), Figure)
    assert isinstance(fig_scatter3d_anomalies(df, sample=800), Figure)
    assert isinstance(fig_climate_pillar(df), Figure)
    assert isinstance(fig_anomaly_heatmap(df), Figure)
    small = (df.groupby(["region", "year", "month"], as_index=False)
             .agg(temperature_c=("temperature_c", "mean"),
                  rainfall_mm=("rainfall_mm", "sum")))
    assert isinstance(fig_animated_yearly(small), Figure)
    assert isinstance(fig_yearly_lines(df), Figure)


def test_kpi_summary(clean, anomaly):
    from src.visuals import kpi_summary
    k = kpi_summary(anomaly["flagged"])
    assert k["rows"] > 0
    assert k["regions"] == len(C.REGIONS)
    assert k["warming_c"] > 0
    assert k["anomaly_days"] > 0


# ---------------------------------------------------------------------------
# 8. CLI
# ---------------------------------------------------------------------------
def test_main_runs_selected_steps(clean):
    from main import main
    rc = main(["--steps", "eda", "trends"])
    assert rc == 0
    assert (C.TABLE_DIR / "trend_analysis.csv").exists()
