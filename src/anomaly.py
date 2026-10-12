"""Anomaly / extreme-event detection.

Three complementary methods (each one is a common interview answer):

1. Z-Score        - flag days whose deseasonalised temperature anomaly is
                    more than 2.5 standard deviations from the regional normal.
2. Percentiles    - flag extreme rainfall above the 99th percentile of that
                    region-month (rainfall is skewed, percentiles beat z-scores;
                    the classic Tukey IQR fence is computed alongside).
3. IsolationForest- unsupervised ML that isolates multivariate outliers using
                    temperature anomaly, rainfall, humidity, wind and heat index.

FUSION RULE (explainable, not a black box)
-------------------------------------------
    keep a day if  (two or more methods agree)
                OR (it sits inside a run of >= 2 consecutive days flagged by
                    at least one method, i.e. a persistent event rather than
                    a single noisy spike)

Because the simulator logged the injected events, detection quality is
measured two ways:
    * day-level  recall / precision
    * event-level recall / precision  (contiguous runs matched with +/- 2 days)
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from . import config as C

sns.set_theme(style="whitegrid", palette=C.PALETTE)
plt.rcParams.update(C.MPL_THEME)

EVENT_TOLERANCE_DAYS = 2


# ---------------------------------------------------------------------------
# method 1: z-score
# ---------------------------------------------------------------------------
def zscore_flags(df: pd.DataFrame,
                 threshold: float = C.ANOMALY_Z_THRESHOLD) -> pd.DataFrame:
    """|z| of the deseasonalised temperature anomaly inside each region."""
    out = df.copy()
    mean = out.groupby("region")["temp_anomaly_c"].transform("mean")
    std = out.groupby("region")["temp_anomaly_c"].transform("std").replace(0, np.nan)
    out["z_temp"] = ((out["temp_anomaly_c"] - mean) / std).round(3)
    out["flag_z"] = out["z_temp"].abs() > threshold
    return out


# ---------------------------------------------------------------------------
# method 2: rainfall percentiles (+ classic Tukey fence for reference)
# ---------------------------------------------------------------------------
def rain_extreme_flags(df: pd.DataFrame, pct: float = 99.0) -> pd.DataFrame:
    """Extreme-rain flag: above the regional-monthly percentile fence.

    `flag_rain`  -> used in the fusion (p99 percentile rule)
    `flag_iqr`   -> classic Tukey fence (q3 + 3 * IQR), reported for reference
    """
    out = df.copy()
    grp = out.groupby(["region", "month"])["rainfall_mm"]
    out["rain_p99_mm"] = grp.transform(lambda s: float(s.quantile(pct / 100.0))).round(2)
    q1 = grp.transform(lambda s: float(s.quantile(0.25)))
    q3 = grp.transform(lambda s: float(s.quantile(0.75)))
    iqr = (q3 - q1).replace(0, np.nan)
    out["rain_upper_fence"] = (q3 + 3.0 * iqr).round(2)
    out["flag_iqr"] = out["rainfall_mm"] > out["rain_upper_fence"]
    out["flag_rain"] = out["rainfall_mm"] >= out["rain_p99_mm"]
    return out


# ---------------------------------------------------------------------------
# method 3: isolation forest
# ---------------------------------------------------------------------------
def isolation_forest_flags(df: pd.DataFrame,
                           contamination: float = 0.005,
                           seed: int = C.SEED) -> pd.DataFrame:
    """Multivariate unsupervised outlier detection."""
    out = df.copy()
    features = ["temp_anomaly_c", "rainfall_mm", "humidity_pct",
                "wind_speed_ms", "heat_index"]
    X = out[features].to_numpy(dtype=float)
    medians = np.nanmedian(X, axis=0)
    medians = np.where(np.isfinite(medians), medians, 0.0)
    X = np.where(np.isnan(X), medians, X)

    Xs = StandardScaler().fit_transform(X)
    model = IsolationForest(n_estimators=200, contamination=contamination,
                            random_state=seed, n_jobs=-1)
    pred = model.fit_predict(Xs)                 # 1 = normal, -1 = anomaly
    out["iforest_score"] = np.round(-model.score_samples(Xs), 4)
    out["flag_iforest"] = pred == -1
    return out


# ---------------------------------------------------------------------------
# fusion
# ---------------------------------------------------------------------------
def _mark_persistent_runs(flag: pd.Series, regions: pd.Series) -> pd.Series:
    """True where the day sits inside a run of >= 2 consecutive flagged days.

    Implemented per region on the (already date-sorted) frame.
    """
    parts = []
    for _, grp in flag.groupby(regions, sort=False):
        arr = grp.to_numpy(dtype=bool)
        neigh = np.zeros_like(arr)
        if len(arr) > 1:
            neigh[1:] |= arr[:-1]
            neigh[:-1] |= arr[1:]
        parts.append(pd.Series(arr & neigh, index=grp.index))
    return pd.concat(parts).sort_index()


def detect_anomalies(df: pd.DataFrame,
                     z_threshold: float = C.ANOMALY_Z_THRESHOLD,
                     rain_pct: float = 99.0,
                     contamination: float = 0.005
                     ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Run the three methods, fuse them, evaluate against ground truth.

    Returns (flagged, summary, metrics).
    """
    out = zscore_flags(df, threshold=z_threshold)
    out = rain_extreme_flags(out, pct=rain_pct)
    out = isolation_forest_flags(out, contamination=contamination)

    votes = (out["flag_z"].astype(int) + out["flag_rain"].astype(int)
             + out["flag_iforest"].astype(int))
    out["vote_count"] = votes

    persistent = _mark_persistent_runs(votes >= 1, out["region"])
    out["is_persistent"] = persistent
    out["is_anomaly"] = persistent | (votes >= 2)
    out["anomaly_score"] = (votes / 3.0).round(3)

    out["anomaly_type"] = np.select(
        [
            out["is_anomaly"] & out["flag_rain"] & (out["z_temp"].abs() <= 2.5),
            out["is_anomaly"] & (out["z_temp"] <= -2.5),
            out["is_anomaly"] & (out["z_temp"] >= 2.5),
            out["is_anomaly"],
        ],
        ["rain_extreme", "cold_extreme", "heat_extreme", "multivariate"],
        default="normal",
    )

    metrics = _evaluate(out)
    summary = (
        out[out["is_anomaly"]]
        .groupby(["region", "anomaly_type"], as_index=False)
        .agg(count=("is_anomaly", "size"),
             mean_score=("anomaly_score", "mean"),
             mean_z=("z_temp", "mean"))
        .round(3)
    )
    return out, summary, metrics


# ---------------------------------------------------------------------------
# evaluation
# ---------------------------------------------------------------------------
def _runs(mask: np.ndarray, dates: pd.Series, regions: pd.Series
          ) -> list[tuple[str, pd.Timestamp, pd.Timestamp]]:
    """Contiguous True runs per region -> (region, start_date, end_date)."""
    runs: list[tuple[str, pd.Timestamp, pd.Timestamp]] = []
    tmp = pd.DataFrame({"flag": mask, "date": dates.to_numpy(),
                        "region": regions.to_numpy()})
    for region, grp in tmp.groupby("region", sort=False):
        f = grp["flag"].to_numpy()
        if not f.any():
            continue
        idx = np.flatnonzero(f)
        breaks = np.flatnonzero(np.diff(idx) > 1)
        starts = np.r_[idx[0], idx[breaks + 1]]
        ends = np.r_[idx[breaks], idx[-1]]
        d = grp["date"].to_numpy()
        for s, e in zip(starts, ends):
            runs.append((region, pd.Timestamp(d[s]), pd.Timestamp(d[e])))
    return runs


def _match(a_runs, b_runs, tol_days: int = EVENT_TOLERANCE_DAYS) -> int:
    """How many runs in `a` are covered (within tol) by a run in `b`."""
    matched = 0
    for region, s, e in a_runs:
        hit = False
        for r2, s2, e2 in b_runs:
            if r2 != region:
                continue
            if e2 >= s - pd.Timedelta(days=tol_days) and s2 <= e + pd.Timedelta(days=tol_days):
                hit = True
                break
        matched += int(hit)
    return matched


def _evaluate(out: pd.DataFrame) -> pd.DataFrame:
    truth = out["injected_event"].fillna("none").ne("none").to_numpy()
    pred = out["is_anomaly"].to_numpy()

    tp = int(np.sum(truth & pred))
    fp = int(np.sum(~truth & pred))
    fn = int(np.sum(truth & ~pred))
    tn = int(np.sum(~truth & ~pred))

    t_runs = _runs(truth, out["date"], out["region"])
    p_runs = _runs(pred, out["date"], out["region"])
    m_t = _match(t_runs, p_runs)
    m_p = _match(p_runs, t_runs)

    return pd.DataFrame([{
        "true_positive": tp, "false_positive": fp,
        "false_negative": fn, "true_negative": tn,
        "day_recall": round(tp / max(1, tp + fn), 3),
        "day_precision": round(tp / max(1, tp + fp), 3),
        "day_f1": round(2 * tp / max(1, 2 * tp + fp + fn), 3),
        "accuracy": round((tp + tn) / max(1, tp + tn + fp + fn), 3),
        "truth_events": len(t_runs),
        "detected_events": len(p_runs),
        "matched_events": m_t,
        "event_recall": round(m_t / max(1, len(t_runs)), 3),
        "event_precision": round(m_p / max(1, len(p_runs)), 3),
        "total_flagged_days": int(pred.sum()),
        "truth_days": int(truth.sum()),
    }])


# ---------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------
def chart_anomaly_timeline(flagged: pd.DataFrame, years: tuple[int, int] = (2014, 2024)) -> "Path":
    """Daily temperature with flagged extremes for one representative region."""
    region = C.REGIONS[0][0]
    sub = flagged[(flagged["region"] == region)
                  & (flagged["year"].between(*years))]
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(sub["date"], sub["temperature_c"], lw=0.7, color=C.PALETTE[0],
            label="Daily temperature")
    ax.plot(sub["date"], sub["temp_roll_365d_c"], lw=2.2, color=C.PALETTE[5],
            label="365-day rolling mean (climate signal)")
    anomalies = sub[sub["is_anomaly"]]
    ax.scatter(anomalies["date"], anomalies["temperature_c"], s=14,
               color=C.PALETTE[1], zorder=5,
               label=f"Flagged extremes (n={len(anomalies)})")
    ax.set_title(f"Extreme Event Detection - {region}", weight="bold")
    ax.set_xlabel("Date"); ax.set_ylabel("Temperature (C)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    path = C.FIGURE_DIR / "11_anomaly_timeline.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def chart_anomaly_scatter(flagged: pd.DataFrame) -> "Path":
    """2-D view: temperature anomaly vs rainfall, anomalies highlighted."""
    sample = flagged.sample(min(25000, len(flagged)), random_state=C.SEED)
    fig, ax = plt.subplots(figsize=(9.5, 6))
    ax.scatter(sample["rainfall_mm"], sample["temp_anomaly_c"],
               s=6, c="#5b6b8c", alpha=0.35, label="normal days")
    an = sample[sample["is_anomaly"]]
    ax.scatter(an["rainfall_mm"], an["temp_anomaly_c"], s=16,
               c=C.PALETTE[1], alpha=0.85, label="detected anomalies")
    ax.set_xlabel("Rainfall (mm/day)")
    ax.set_ylabel("Temperature anomaly (C)")
    ax.set_title("Anomaly Space: Heat vs Rain Extremes", weight="bold")
    ax.legend(frameon=False, fontsize=9)
    path = C.FIGURE_DIR / "12_anomaly_scatter.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


def chart_anomaly_counts(flagged: pd.DataFrame) -> "Path":
    """How many extremes of each type, per region."""
    an = flagged[flagged["is_anomaly"]]
    order = sorted(an["anomaly_type"].unique()) if len(an) else []
    fig, ax = plt.subplots(figsize=(9.5, 5))
    sns.countplot(data=an, x="region", hue="anomaly_type",
                  hue_order=order, palette=C.PALETTE[:len(order) or 1], ax=ax)
    ax.set_title("Detected Extreme Events by Region and Type", weight="bold")
    ax.set_xlabel("Region"); ax.set_ylabel("Event count")
    ax.tick_params(axis="x", rotation=15)
    ax.legend(frameon=False, fontsize=8, title="type")
    path = C.FIGURE_DIR / "13_anomaly_counts.png"
    fig.savefig(path, bbox_inches="tight"); plt.close(fig)
    return path


# ---------------------------------------------------------------------------
def run_anomaly_detection(df: pd.DataFrame) -> dict:
    """Full anomaly module: flags + evaluation + tables + charts."""
    flagged, summary, metrics = detect_anomalies(df)

    summary.to_csv(C.TABLE_DIR / "anomaly_summary.csv", index=False)
    metrics.to_csv(C.TABLE_DIR / "anomaly_metrics.csv", index=False)
    # cache the flagged frame so the dashboard loads instantly
    flagged.to_csv(C.PROCESSED_DIR / "climate_flagged.csv", index=False)

    cols = ["date", "region", "temperature_c", "rainfall_mm",
            "temp_anomaly_c", "z_temp", "anomaly_score",
            "anomaly_type", "injected_event"]
    top = flagged[flagged["is_anomaly"]].nlargest(100, "anomaly_score")[cols]
    for c in ["temperature_c", "rainfall_mm", "temp_anomaly_c",
              "z_temp", "anomaly_score"]:
        top[c] = top[c].round(3)
    top.to_csv(C.TABLE_DIR / "top_anomalies.csv", index=False)

    figures = {
        "anomaly_timeline": chart_anomaly_timeline(flagged),
        "anomaly_scatter": chart_anomaly_scatter(flagged),
        "anomaly_counts": chart_anomaly_counts(flagged),
    }
    return {"flagged": flagged, "summary": summary,
            "metrics": metrics, "top": top, "figures": figures}


if __name__ == "__main__":  # pragma: no cover
    from .preprocessing import run_preprocessing
    df, _ = run_preprocessing()
    res = run_anomaly_detection(df)
    print(res["metrics"].T.to_string())
    print(res["summary"].to_string(index=False))
