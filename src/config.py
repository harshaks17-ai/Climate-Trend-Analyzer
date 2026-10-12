"""Global configuration: paths, constants, simulation parameters.

Why this file exists
--------------------
Every other module imports paths and settings from here so that nothing
hard-codes a folder name. Change a path once, the whole pipeline follows.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make UTF-8 signs print safely on Windows cp1252 terminals.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass

# --------------------------------------------------------------------------
# 1. PATHS  (project root = folder that contains this src/ package)
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

NOTEBOOK_DIR = PROJECT_ROOT / "notebooks"
MODEL_DIR = PROJECT_ROOT / "models"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
TABLE_DIR = OUTPUT_DIR / "tables"
REPORT_DIR = OUTPUT_DIR / "reports"

IMAGE_DIR = PROJECT_ROOT / "images"       # README screenshots
DOC_DIR = PROJECT_ROOT / "docs"
APP_DIR = PROJECT_ROOT / "app"

RAW_CSV = RAW_DIR / "climate_raw.csv"
CLEAN_CSV = PROCESSED_DIR / "climate_clean.csv"

for _p in (RAW_DIR, PROCESSED_DIR, FIGURE_DIR, TABLE_DIR, REPORT_DIR, IMAGE_DIR, DOC_DIR, MODEL_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# --------------------------------------------------------------------------
# 2. SIMULATION SETTINGS (virtual dataset that mimics real climate records)
# --------------------------------------------------------------------------
SEED = 42                      # reproducibility: same data on every machine
START_YEAR = 1990
END_YEAR = 2024                # inclusive
FREQ = "D"                     # daily observations

# Region portfolio: (region_name, base_temperature_C, warming_rate_C_per_decade,
#                    rainfall_base_mm, phase_shift_for_season)
REGIONS: list[tuple[str, float, float, float, int]] = [
    ("North India",   24.5, 0.28, 3.2, 0),
    ("South India",   27.5, 0.22, 5.8, -45),
    ("Coastal India", 26.8, 0.20, 7.4, -30),
    ("Northern Plains", 21.0, 0.34, 2.1, 15),
    ("Western Ghats", 23.0, 0.18, 9.2, -20),
]

# Missing-data and anomaly injection rates (kept small and realistic)
MISSING_RATE = 0.015           # 1.5 % of cells become NaN during "sensor failure"
ANOMALY_RATE = 0.004           # ~0.4 % days flagged as injected extreme events

# --------------------------------------------------------------------------
# 3. ANALYSIS SETTINGS
# --------------------------------------------------------------------------
BASELINE_PERIOD = (1991, 2020)   # WMO-style 30-year climate normal
ANOMALY_Z_THRESHOLD = 2.5      # |z| > 2.5  -> extreme heat / cold day
RANDOM_FOREST_STATE = SEED

# Chart styling for static (matplotlib) figures
MPL_THEME = {
    "figure.figsize": (11, 5),
    "figure.dpi": 120,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
}

# Colour system (dark UI, no emoji anywhere - only typographic signs)
PALETTE = ["#00e5ff", "#ff4d6d", "#ffd166", "#06d6a0", "#8b5cf6", "#f78c6a"]
SYMBOLS = {
    "up": "▲", "down": "▼", "dot": "●", "ring": "○", "diamond": "◆",
    "square": "■", "arrow": "→", "line": "─", "double": "═",
    "bar": "█", "shade": "░", "check": "✓", "cross": "✗", "star": "★",
}
