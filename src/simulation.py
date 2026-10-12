"""Virtual climate dataset generator (simulation module).

WHY THIS MODULE
---------------
Students do not have access to government climate servers (IMD, NOAA, NASA).
This module builds a *physically plausible* daily climate dataset that behaves
like real records:

  * annual seasonal cycle (hot monsoon summer, cool winter)
  * long-term warming trend  (+0.18 .. +0.34 C per decade per region)
  * rising CO2 (Mauna Loa style curve) and rising mean sea level
  * autocorrelated weather noise (today resembles yesterday)
  * injected EXTREME EVENTS  (heatwaves, cold snaps, floods)  -> ground truth
  * injected sensor errors    (missing cells, humidity > 100, negative rain)
  * duplicate rows            -> real-world dirt

Because a fixed SEED is used, every machine produces the identical dataset.

USAGE
-----
    from src.simulation import generate_climate_dataset, save_dataset
    df, events = generate_climate_dataset()
    save_dataset(df)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


# ---------------------------------------------------------------------------
# helper curves
# ---------------------------------------------------------------------------
def _warming_curve(years_from_start: np.ndarray, rate_per_decade: float) -> np.ndarray:
    """Near-linear warming with a small acceleration term (realistic)."""
    decades = years_from_start / 10.0
    return rate_per_decade * decades + 0.015 * decades**2


def _co2_curve(doy: np.ndarray, year: np.ndarray, start_year: int) -> np.ndarray:
    """Mauna Loa style CO2: quadratic rise + yearly breathing cycle."""
    y = year - start_year
    trend = 354.4 + 1.5 * y + 0.012 * y**2          # ~354 ppm -> ~421 ppm
    seasonal = 2.5 * np.cos(2 * np.pi * (doy - 135) / 365.25)  # peak ~May
    return trend + seasonal


def _sea_level_curve(years_from_start: np.ndarray, noise: np.ndarray) -> np.ndarray:
    """Global mean sea level: ~2.2 mm/yr + accelerating term."""
    return 2.2 * years_from_start + 0.025 * years_from_start**2 + noise


def _monsoon_factor(doy: np.ndarray) -> np.ndarray:
    """0..1 wet-season weight: Jun-Sep monsoon peak (doy ~ 200)."""
    raw = np.exp(1.6 * np.cos(2 * np.pi * (doy - 210) / 365.25))
    return (raw - raw.min()) / (raw.max() - raw.min())


def _annual_cycle(doy: np.ndarray, peak_day: float = 200.0) -> np.ndarray:
    """-1..1 cosine cycle peaking on `peak_day` of the year."""
    return np.cos(2 * np.pi * (doy - peak_day) / 365.25)


# ---------------------------------------------------------------------------
# main generator
# ---------------------------------------------------------------------------
def generate_climate_dataset(
    start_year: int = C.START_YEAR,
    end_year: int = C.END_YEAR,
    seed: int = C.SEED,
    inject_quality_issues: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build the simulated daily climate dataset.

    Returns
    -------
    events_df : pd.DataFrame
        Ground-truth log of injected extreme events
        (columns: date, region, event_type, magnitude).
    """
    rng = np.random.default_rng(seed)

    dates = pd.date_range(f"{start_year}-01-01", f"{end_year}-12-31", freq=C.FREQ)
    doy = dates.dayofyear.to_numpy(dtype=float)
    year = dates.year.to_numpy(dtype=float)
    years_from_start = year - start_year + (doy / 365.25)

    frames: list[pd.DataFrame] = []
    event_log: list[dict] = []

    for region, base_temp, warm_rate, rain_base, phase in C.REGIONS:
        n = len(dates)

        # ---- temperature -------------------------------------------------
        seasonal = 6.5 * _annual_cycle(doy, peak_day=200 + phase)   # amplitude 6.5C
        trend = _warming_curve(years_from_start, warm_rate)
        # AR(1) weather noise: yesterday's anomaly persists today
        white = rng.normal(0, 1.0, n)
        ar1 = np.zeros(n)
        for i in range(1, n):
            ar1[i] = 0.85 * ar1[i - 1] + white[i]
        temp = base_temp + seasonal + trend + ar1

        # ---- rainfall ----------------------------------------------------
        wet = _monsoon_factor(doy)
        lam = 0.35 + 4.5 * wet                                   # daily mean mm
        rain = rng.gamma(shape=np.clip(lam, 0.2, None), scale=1.0, size=n)
        rain[rng.random(n) < (0.62 - 0.55 * wet)] = 0.0          # dry days
        rain *= rain_base * (1.0 + 0.10 * years_from_start / 10)  # slightly wetter

        # ---- humidity ----------------------------------------------------
        humidity = (
            52.0
            + 30.0 * wet
            - 1.4 * (temp - (base_temp + trend))
            + rng.normal(0, 4.0, n)
        )

        # ---- wind --------------------------------------------------------
        wind = 4.5 + 2.0 * _annual_cycle(doy, peak_day=30) + rng.gamma(2.0, 1.1, n)

        # ---- global columns ----------------------------------------------
        co2 = _co2_curve(doy, year, start_year)
        sea = _sea_level_curve(years_from_start, rng.normal(0, 2.5, n))
        if not C.REGIONS[0][0] == region:
            sea = sea + rng.normal(0, 1.0, 1).item()   # small regional offset

        event_flag = np.full(n, "none", dtype=object)

        # ---- inject EXTREME EVENTS (ground truth) -------------------------
        def _window(start: int, length: int) -> slice:
            return slice(start, start + length)

        # heatwaves: late May - Jun
        for _ in range(max(1, int(0.55 * (end_year - start_year + 1)))):
            y_idx = rng.integers(0, end_year - start_year + 1)
            y_start = int(np.flatnonzero(dates.year == start_year + y_idx)[0])
            anchor = y_start + int(rng.integers(130, 185))
            ln = int(rng.integers(4, 9))
            amp = float(rng.uniform(5.5, 10.5))
            w = _window(anchor, ln)
            if w.stop < n:
                bump = amp * np.exp(-0.5 * ((np.arange(ln) - ln / 2) / (ln / 3)) ** 2)
                temp[w] += bump
                humidity[w] -= 12
                event_flag[w] = "heatwave"
                event_log.append({
                    "date": dates[anchor].date().isoformat(),
                    "region": region, "event_type": "heatwave",
                    "magnitude": round(float(bump.max()), 2),
                })

        # cold snaps: Dec - Jan
        for _ in range(max(1, int(0.35 * (end_year - start_year + 1)))):
            y_idx = rng.integers(0, end_year - start_year + 1)
            y_start = int(np.flatnonzero(dates.year == start_year + y_idx)[0])
            anchor = y_start + int(rng.integers(340, 375))
            ln = int(rng.integers(3, 7))
            amp = float(rng.uniform(5.0, 9.5))
            w = _window(anchor, ln)
            if w.stop < n:
                temp[w] -= amp
                event_flag[w] = "cold_snap"
                event_log.append({
                    "date": dates[min(anchor, n - 1)].date().isoformat(),
                    "region": region, "event_type": "cold_snap",
                    "magnitude": round(amp, 2),
                })

        # floods: Jul - Sep, rainfall multiplier
        for _ in range(max(1, int(0.45 * (end_year - start_year + 1)))):
            y_idx = rng.integers(0, end_year - start_year + 1)
            y_start = int(np.flatnonzero(dates.year == start_year + y_idx)[0])
            anchor = y_start + int(rng.integers(185, 265))
            ln = int(rng.integers(2, 5))
            mult = float(rng.uniform(8.0, 18.0))
            w = _window(anchor, ln)
            if w.stop < n:
                rain[w] *= mult
                humidity[w] = np.clip(humidity[w] + 15, 0, 99)
                event_flag[w] = "flood"
                event_log.append({
                    "date": dates[anchor].date().isoformat(),
                    "region": region, "event_type": "flood",
                    "magnitude": round(mult, 2),
                })

        frame = pd.DataFrame({
            "date": dates,
            "region": region,
            "temperature_c": np.round(temp, 2),
            "rainfall_mm": np.round(np.clip(rain, 0, None), 2),
            "humidity_pct": np.round(humidity, 1),
            "co2_ppm": np.round(co2, 2),
            "sea_level_mm": np.round(sea, 2),
            "wind_speed_ms": np.round(np.clip(wind, 0, None), 2),
            "injected_event": event_flag,
        })
        frames.append(frame)

    df = pd.concat(frames, ignore_index=True)

    # ---- inject DATA-QUALITY problems (so cleaning has real work) ---------
    if inject_quality_issues:
        rng_q = np.random.default_rng(seed + 7)
        # (a) missing cells
        mask = rng_q.random(df.shape[0]) < C.MISSING_RATE
        cols = ["temperature_c", "rainfall_mm", "humidity_pct",
                "co2_ppm", "sea_level_mm", "wind_speed_ms"]
        for c in cols:
            hit = mask & (rng_q.random(df.shape[0]) < 0.35)
            df.loc[hit, c] = np.nan
        # (b) impossible sensor readings
        bad_h = rng_q.choice(df.index, size=45, replace=False)
        df.loc[bad_h, "humidity_pct"] = rng_q.uniform(101, 140, len(bad_h)).round(1)
        bad_r = rng_q.choice(df.index, size=35, replace=False)
        df.loc[bad_r, "rainfall_mm"] = -rng_q.uniform(0.5, 25.0, len(bad_r)).round(2)
        # (c) duplicated rows (double logger writes)
        dup_idx = rng_q.choice(df.index, size=240, replace=False)
        df = pd.concat([df, df.loc[dup_idx]], ignore_index=True)
        # (d) shuffle so duplicates are not adjacent
        df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    df["date"] = pd.to_datetime(df["date"])
    events_df = pd.DataFrame(event_log, columns=["date", "region", "event_type", "magnitude"])
    if not events_df.empty:
        events_df["date"] = pd.to_datetime(events_df["date"])
    return df, events_df


def save_dataset(df: pd.DataFrame, path=None) -> "Path":
    """Persist the raw dataset as CSV."""
    path = path or C.RAW_CSV
    df.to_csv(path, index=False)
    return path


def load_events(path=None) -> pd.DataFrame:
    """Load the ground-truth event log (recreated with the same seed)."""
    _, events = generate_climate_dataset()
    return events


if __name__ == "__main__":  # pragma: no cover
    data, ev = generate_climate_dataset()
    p = save_dataset(data)
    print(f"rows={len(data):,} regions={data['region'].nunique()} "
          f"span={data['date'].min().date()} .. {data['date'].max().date()}")
    print(f"saved -> {p}  | injected events: {len(ev)}")
