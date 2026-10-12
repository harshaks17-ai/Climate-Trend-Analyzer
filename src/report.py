"""Automated markdown report generator.

Turns every table the pipeline produced into a recruiter-readable
`outputs/reports/climate_report.md` with computed insights - the kind of
"auto reporting" step real analytics teams ship.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from . import config as C


def _md_table(df: pd.DataFrame, max_rows: int = 12) -> str:
    d = df.head(max_rows)
    header = "| " + " | ".join(str(c) for c in d.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(d.columns)) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |"
            for row in d.itertuples(index=False, name=None)]
    return "\n".join([header, sep, *rows])


def build_report(clean_df: pd.DataFrame,
                 quality: dict,
                 trends: pd.DataFrame,
                 anomaly_metrics: pd.DataFrame,
                 anomaly_summary: pd.DataFrame,
                 forecast_accuracy: pd.DataFrame,
                 projections: pd.DataFrame) -> str:
    """Return the markdown report as a string."""

    # ---------------- computed insights ------------------------------------
    yearly = clean_df.groupby("year")["temp_anomaly_c"].mean()
    warming = (yearly.iloc[-5:].mean() - yearly.iloc[:5].mean())
    temp_trends = trends[trends["variable"] == "temperature_c"].sort_values(
        "slope_per_decade", ascending=False)
    fastest = temp_trends.iloc[0]
    slowest = temp_trends.iloc[-1]
    rain_trends = trends[trends["variable"] == "rainfall_mm"]
    rain_up = int((rain_trends["slope_per_decade"] > 0).sum())
    m = anomaly_metrics.iloc[0].to_dict()
    hot_days = int((clean_df["temp_anomaly_c"] > C.ANOMALY_Z_THRESHOLD
                    * clean_df["temp_anomaly_c"].std()).sum())
    fc_mae = forecast_accuracy["mae"].mean()
    co2_proj = projections[projections["variable"] == "co2_ppm"]
    sea_proj = projections[projections["variable"] == "sea_level_mm"]

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    span = f"{int(clean_df['year'].min())} - {int(clean_df['year'].max())}"

    lines = [
        "# Climate Trend Analyzer - Automated Analysis Report",
        "",
        f"_Generated: {ts}  |  Record span: {span}  |  "
        f"Rows analysed: {len(clean_df):,}_",
        "",
        "---",
        "",
        "## 1. Data Quality",
        "",
        "| metric | value |",
        "| --- | --- |",
        f"| rows in | {quality.get('rows_in', 0):,} |",
        f"| duplicate rows removed | {quality.get('duplicate_rows_removed', 0):,} |",
        f"| impossible values repaired | {quality.get('impossible_values_set_nan', 0):,} |",
        f"| missing cells before imputation | {quality.get('missing_cells_before', 0):,} "
        f"({quality.get('missing_pct_before', 0)} %) |",
        f"| missing cells after imputation | {quality.get('missing_cells_after', 0):,} |",
        f"| rows out | {quality.get('rows_out', 0):,} |",
        "",
        "## 2. Key Findings",
        "",
        f"1. **Warming is confirmed.** Global mean temperature anomaly moved "
        f"**{warming:+.2f} C** between the first and last 5 years of the record.",
        f"2. **Fastest warming region:** {fastest['region']} at "
        f"**{fastest['slope_per_decade']:+.2f} C/decade** "
        f"(Theil-Sen {fastest['theil_sen_per_decade']:+.2f}, "
        f"Mann-Kendall: {fastest['mk_trend']}).",
        f"3. **Slowest warming region:** {slowest['region']} at "
        f"**{slowest['slope_per_decade']:+.2f} C/decade**.",
        f"4. **Rainfall:** {rain_up} of {len(rain_trends)} regions show an "
        f"increasing annual rainfall trend; the rest are flat or drying.",
        f"5. **Extreme events:** {int(m['total_flagged_days']):,} days flagged "
        f"({hot_days:,} beyond +{C.ANOMALY_Z_THRESHOLD} sigma heat). Day-level "
        f"recall **{m['day_recall']:.0%}** / precision {m['day_precision']:.0%}; "
        f"event-level recall **{m['event_recall']:.0%}** / precision "
        f"{m['event_precision']:.0%} across {int(m['truth_events'])} ground-truth "
        f"events.",
        f"6. **Forecast quality:** mean backtest MAE = **{fc_mae:.2f} C** "
        f"(24-month hold-out).",
        f"7. **Projection:** on the current linear trend CO2 reaches "
        f"~**{co2_proj.iloc[-1]['value']:.0f} ppm** and mean sea level "
        f"**+{sea_proj.iloc[-1]['value']:.0f} mm** by {int(co2_proj.iloc[-1]['year'])}.",
        "",
        "## 3. Trend Analysis (temperature)",
        "",
        _md_table(temp_trends[["region", "slope_per_decade", "theil_sen_per_decade",
                               "r2", "p_value", "mk_trend", "total_change"]]),
        "",
        "## 4. Anomaly Detection Metrics",
        "",
        _md_table(anomaly_metrics),
        "",
        "## 5. Anomalies by Region and Type",
        "",
        _md_table(anomaly_summary, max_rows=30),
        "",
        "## 6. Forecast Backtest Accuracy",
        "",
        _md_table(forecast_accuracy),
        "",
        "## 7. Global Projections (next 10 years)",
        "",
        _md_table(projections, max_rows=24),
        "",
        "## 8. Figures",
        "",
    ]
    for f in sorted(C.FIGURE_DIR.glob("*.png")):
        try:
            rel = f.relative_to(C.PROJECT_ROOT).as_posix()
        except ValueError:      # outside the project (e.g. pytest temp dirs)
            rel = f.as_posix()
        lines.append(f"- `{f.name}`")
        lines.append(f"  \n  ![{f.stem}]({rel})")

    lines += [
        "",
        "---",
        "",
        "_Methodology: OLS + Theil-Sen slopes on annual aggregates, "
        "Mann-Kendall monotonic trend test, 1991-2020 WMO baseline climatology, "
        "z-score + IQR + IsolationForest anomaly fusion, Holt-Winters monthly "
        "forecast with 24-month hold-out backtest._",
        "",
    ]
    return "\n".join(lines)


def save_report(content: str, path=None):
    path = path or (C.REPORT_DIR / "climate_report.md")
    path.write_text(content, encoding="utf-8")
    return path
