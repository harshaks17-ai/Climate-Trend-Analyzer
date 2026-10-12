#!/usr/bin/env python
"""Climate Trend Analyzer - end-to-end pipeline.

USAGE
-----
    python main.py                 # run every step (generates data if missing)
    python main.py --regenerate    # force a fresh simulated dataset
    python main.py --method sarima # use SARIMAX for forecasting
    python main.py --skip-forecast # skip the forecasting stage
    python main.py --steps eda trends   # run only selected stages

STAGES
------
    generate -> preprocess -> eda -> trends -> anomaly -> forecast -> report
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from src import config as C

# Windows terminals often default to cp1252 -> reconfigure to UTF-8 so the
# typographic signs (▲ ● ◆ ...) print instead of crashing the pipeline.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass

SY = C.SYMBOLS


def _banner(step: str, title: str) -> None:
    print("\n" + "=" * 72)
    print(f"  {SY['double']} {step}  {SY['line']}  {title}")
    print("=" * 72)


def stage_generate(force: bool = False):
    from src.simulation import generate_climate_dataset, save_dataset
    if C.RAW_CSV.exists() and not force:
        print(f"  {SY['check']} raw dataset already present: {C.RAW_CSV.name}")
        return None
    df, events = generate_climate_dataset()
    path = save_dataset(df)
    events.to_csv(C.TABLE_DIR / "injected_events_ground_truth.csv", index=False)
    print(f"  {SY['check']} simulated {len(df):,} rows, "
          f"{len(events)} injected extreme events -> {path}")
    return df


def stage_preprocess():
    from src.preprocessing import run_preprocessing
    df, report = run_preprocessing()
    print(f"  {SY['check']} cleaned rows = {report['rows_out']:,} | "
          f"duplicates removed = {report['duplicate_rows_removed']} | "
          f"missing {report['missing_pct_before']}% -> {report['missing_pct_after']}%")
    print(f"  {SY['arrow']} features engineered: calendar, baseline normals, "
          f"anomalies, rolling means, heat index")
    return df, report


def stage_eda(df):
    from src.eda import run_eda
    res = run_eda(df)
    print(f"  {SY['check']} tables : {len(res['tables'])} saved to outputs/tables/")
    print(f"  {SY['check']} charts : {len(res['figures'])} saved to outputs/figures/")
    return res


def stage_trends(df):
    from src.trends import run_trend_analysis
    res = run_trend_analysis(df)
    t = res["trends"]
    temp = t[t["variable"] == "temperature_c"].sort_values("slope_per_decade",
                                                           ascending=False)
    print(f"  {SY['up']} fastest warming : {temp.iloc[0]['region']} "
          f"{temp.iloc[0]['slope_per_decade']:+.2f} C/decade")
    print(f"  {SY['down']} slowest warming: {temp.iloc[-1]['region']} "
          f"{temp.iloc[-1]['slope_per_decade']:+.2f} C/decade")
    print(f"  {SY['check']} Mann-Kendall significant trends: "
          f"{int((t['mk_trend'] == 'increasing').sum())} increasing / "
          f"{int((t['mk_trend'] == 'decreasing').sum())} decreasing")
    return res


def stage_anomaly(df):
    from src.anomaly import run_anomaly_detection
    res = run_anomaly_detection(df)
    m = res["metrics"].iloc[0]
    print(f"  {SY['diamond']} flagged days    : {int(m['total_flagged_days']):,} "
          f"({res['flagged']['is_anomaly'].mean() * 100:.2f} % of record)")
    print(f"  {SY['check']} day  recall/prec: {m['day_recall']:.0%} / "
          f"{m['day_precision']:.0%}  (F1 {m['day_f1']:.2f})")
    print(f"  {SY['check']} event recall/prec: {m['event_recall']:.0%} / "
          f"{m['event_precision']:.0%}  "
          f"({m['matched_events']}/{m['truth_events']} truth events found)")
    print(res["summary"].to_string(index=False))
    return res


def stage_forecast(df, method: str = "holt_winters"):
    from src.forecast import run_forecast
    res = run_forecast(df, method=method)
    print(f"  {SY['arrow']} model = {method} | horizon = 60 months | "
          f"backtest = 24 months")
    print(res["accuracy"].round(3).to_string(index=False))
    return res


def stage_report(df, quality, trends_res, anomaly_res, forecast_res):
    from src.report import build_report, save_report
    content = build_report(
        clean_df=df,
        quality=quality,
        trends=trends_res["trends"],
        anomaly_metrics=anomaly_res["metrics"],
        anomaly_summary=anomaly_res["summary"],
        forecast_accuracy=forecast_res["accuracy"],
        projections=forecast_res["projections"],
    )
    path = save_report(content)
    print(f"  {SY['check']} report -> {path}")
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Climate Trend Analyzer pipeline")
    parser.add_argument("--regenerate", action="store_true",
                        help="force fresh simulated dataset")
    parser.add_argument("--method", default="holt_winters",
                        choices=["holt_winters", "sarima", "linear"],
                        help="forecasting backend")
    parser.add_argument("--skip-forecast", action="store_true")
    parser.add_argument("--steps", nargs="*", default=None,
                        choices=["generate", "preprocess", "eda", "trends",
                                 "anomaly", "forecast", "report"],
                        help="run only these stages, in order")
    args = parser.parse_args(argv)

    wanted = args.steps or ["generate", "preprocess", "eda", "trends",
                            "anomaly", "forecast", "report"]
    if args.skip_forecast and "forecast" in wanted:
        wanted = [s for s in wanted if s not in ("forecast", "report")]

    t0 = time.time()
    print("=" * 72)
    print(f"  {SY['star']} CLIMATE TREND ANALYZER {SY['line']} "
          f"{' -> '.join(wanted)}")
    print("=" * 72)

    quality: dict = {}

    if "generate" in wanted:
        _banner("STAGE 01", "Virtual climate dataset generation")
        stage_generate(force=args.regenerate)

    if "preprocess" in wanted:
        _banner("STAGE 02", "Data cleaning + feature engineering")
        df, quality = stage_preprocess()
    else:
        # individual stages still need the featured frame -> rebuild quietly
        from src.preprocessing import run_preprocessing
        if not C.RAW_CSV.exists():
            print(f"  {SY['cross']} {C.RAW_CSV} missing. "
                  f"Run `python main.py --regenerate` first.")
            return 2
        df, quality = run_preprocessing()
        print(f"  {SY['check']} loaded processed dataset ({len(df):,} rows)")

    trends_res = anomaly_res = forecast_res = None

    if "eda" in wanted:
        _banner("STAGE 03", "Exploratory data analysis")
        stage_eda(df)

    if "trends" in wanted:
        _banner("STAGE 04", "Long-term trend analysis")
        trends_res = stage_trends(df)

    if "anomaly" in wanted:
        _banner("STAGE 05", "Anomaly / extreme-event detection")
        anomaly_res = stage_anomaly(df)

    if "forecast" in wanted:
        _banner("STAGE 06", "Forecasting + global projections")
        forecast_res = stage_forecast(df, method=args.method)

    ok = trends_res and anomaly_res and forecast_res
    if "report" in wanted and ok:
        _banner("STAGE 07", "Automated report")
        stage_report(df, quality or {}, trends_res, anomaly_res, forecast_res)
    elif "report" in wanted:
        print(f"  {SY['cross']} report skipped: run the full pipeline first")

    elapsed = time.time() - t0
    print("\n" + "=" * 72)
    print(f"  {SY['check']} PIPELINE FINISHED IN {elapsed:.1f} s")
    print(f"  {SY['arrow']} figures : {C.FIGURE_DIR}")
    print(f"  {SY['arrow']} tables  : {C.TABLE_DIR}")
    print(f"  {SY['arrow']} report  : {C.REPORT_DIR / 'climate_report.md'}")
    print(f"  {SY['arrow']} dashboard: streamlit run app/streamlit_app.py")
    print("=" * 72 + "\n")

    summary = {
        "seconds": round(elapsed, 2),
        "stages": wanted,
        "rows": int(len(df)),
        "figures": len(list(C.FIGURE_DIR.glob('*.png'))),
        "tables": len(list(C.TABLE_DIR.glob('*.csv'))),
    }
    (C.OUTPUT_DIR / "pipeline_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
