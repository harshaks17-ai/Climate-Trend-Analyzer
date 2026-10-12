"""Dashboard smoke tests (Streamlit AppTest).

Every sidebar page is executed in-process; any Python exception fails the test.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

st_v1 = pytest.importorskip("streamlit.testing.v1", reason="streamlit too old")
from streamlit.testing.v1 import AppTest  # noqa: E402

from src import config as C  # noqa: E402

PAGES = [
    "OVERVIEW", "DATA EXPLORER", "3D CLIMATE WORLD", "TREND ANALYSIS",
    "EXTREME EVENTS", "FORECASTING", "REPORT & EXPORT",
]


@pytest.fixture(scope="module")
def built_outputs():
    """Make sure the pipeline artefacts the app reads actually exist."""
    import subprocess
    if not (C.CLEAN_CSV.exists()
            and (C.PROCESSED_DIR / "climate_flagged.csv").exists()
            and (C.TABLE_DIR / "temperature_forecast.csv").exists()):
        subprocess.run([sys.executable, str(ROOT / "main.py")],
                       cwd=str(ROOT), check=False)
    assert C.CLEAN_CSV.exists()


def _app() -> "AppTest":
    return AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"),
                             default_timeout=300)


def test_app_starts(built_outputs):
    at = _app()
    at.run()
    assert not at.exception, at.exception
    assert len(at.sidebar.radio) >= 1


@pytest.mark.parametrize("page", PAGES)
def test_app_pages_render(built_outputs, page):
    at = _app()
    at.run()
    at.sidebar.radio[0].set_value(page)
    at.run()
    assert not at.exception, f"{page}: {at.exception}"


def test_app_region_filter(built_outputs):
    at = _app()
    at.run()
    at.sidebar.radio[0].set_value("OVERVIEW")
    at.sidebar.multiselect[0].set_value(["North India"])
    at.run()
    assert not at.exception, at.exception


def test_app_year_slider(built_outputs):
    at = _app()
    at.run()
    at.sidebar.radio[0].set_value("OVERVIEW")
    at.sidebar.slider[0].set_value((2000, 2024))
    at.run()
    assert not at.exception, at.exception
