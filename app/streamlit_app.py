"""Climate Trend Analyzer - animated 3D dashboard (Streamlit).

Run with:   streamlit run app/streamlit_app.py

Design rules
------------
* dark futuristic theme (see .streamlit/config.toml)
* typographic signs only (▲ ▼ ● ◆ ■ ═ ─ → ★) - no emoji anywhere
* glass cards, gradient title, scan-line and pulse animations
* Plotly 3D surfaces / scatters + animated frames for year-by-year playback
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import config as C  # noqa: E402

# ---------------------------------------------------------------------------
# page setup
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Climate Trend Analyzer",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# custom CSS  (glass cards, gradient title, scan lines, pulse animations)
# ---------------------------------------------------------------------------
st.markdown(
    """
<style>
:root{
  --cyan:#00e5ff; --pink:#ff4d6d; --gold:#ffd166; --mint:#06d6a0;
  --violet:#8b5cf6; --ink:#05060f; --panel:rgba(13,16,48,.62);
}
.stApp{
  background:
    radial-gradient(1100px 620px at 8% -8%, rgba(0,229,255,.16), transparent 60%),
    radial-gradient(900px 560px at 96% 4%, rgba(139,92,246,.18), transparent 62%),
    radial-gradient(1200px 700px at 50% 118%, rgba(255,77,109,.12), transparent 60%),
    #05060f;
  background-size:180% 180%, 170% 170%, 160% 160%, 100% 100%;
  animation: drift 26s ease-in-out infinite alternate;
}
@keyframes drift{from{background-position:0% 0%,100% 0%,50% 100%,0 0}
                 to{background-position:20% 12%,80% 10%,40% 90%,0 0}}
header[data-testid="stHeader"]{background:transparent;}
div[data-testid="stToolbar"]{display:none;}

/* ---------- title block ---------- */
.cta-title{
  font-size:2.6rem; font-weight:800; letter-spacing:.06em; margin:0;
  background:linear-gradient(92deg,#00e5ff 0%,#8b5cf6 38%,#ff4d6d 72%,#ffd166 100%);
  background-size:220% 100%;
  -webkit-background-clip:text; background-clip:text; color:transparent;
  animation:sweep 7s linear infinite;
}
@keyframes sweep{from{background-position:0% 50%}to{background-position:220% 50%}}
.cta-sub{
  color:#9fb3d9; font-size:.95rem; letter-spacing:.22em;
  text-transform:uppercase; margin-top:-.4rem;
}
.cta-rule{
  height:3px; margin:.55rem 0 1.1rem 0; border-radius:3px;
  background:linear-gradient(90deg,transparent,#00e5ff,#8b5cf6,#ff4d6d,transparent);
  background-size:200% 100%; animation:sweep 4.5s linear infinite;
  box-shadow:0 0 14px rgba(0,229,255,.45);
}

/* ---------- glass cards ---------- */
.cta-card{
  position:relative; overflow:hidden;
  background:var(--panel); backdrop-filter:blur(9px);
  border:1px solid rgba(0,229,255,.28); border-radius:16px;
  padding:16px 18px; min-height:118px;
  box-shadow:0 10px 30px rgba(0,0,0,.45), inset 0 0 24px rgba(0,229,255,.05);
  transition:transform .25s ease, box-shadow .25s ease;
}
.cta-card:hover{
  transform:translateY(-5px);
  box-shadow:0 16px 40px rgba(0,0,0,.6), 0 0 22px rgba(0,229,255,.35);
  border-color:rgba(0,229,255,.7);
}
.cta-card::after{
  content:""; position:absolute; top:0; left:-60%;
  width:45%; height:100%;
  background:linear-gradient(120deg,transparent,rgba(255,255,255,.14),transparent);
  animation:shine 5.5s ease-in-out infinite;
}
@keyframes shine{0%{left:-60%}55%{left:130%}100%{left:130%}}
.cta-label{
  font-size:.72rem; letter-spacing:.24em; text-transform:uppercase;
  color:#8ea6cc;
}
.cta-value{
  font-size:2.05rem; font-weight:800; color:#e6f1ff; line-height:1.15;
  text-shadow:0 0 18px rgba(0,229,255,.35);
}
.cta-delta{font-size:.8rem; color:#06d6a0; letter-spacing:.06em}
.cta-delta.neg{color:#ff4d6d}
.cta-badge{
  position:absolute; top:14px; right:16px; font-size:1.1rem; color:#ffd166;
  animation:pulse 2.4s ease-in-out infinite;
}
@keyframes pulse{0%,100%{opacity:.45; transform:scale(.92)}50%{opacity:1; transform:scale(1.08)}}

/* ---------- section headers ---------- */
.cta-sec{
  font-size:1.15rem; font-weight:700; letter-spacing:.14em;
  color:#e6f1ff; text-transform:uppercase; margin:.4rem 0 .2rem 0;
}
.cta-sec span{color:#00e5ff;}
.cta-note{
  color:#8ea6cc; font-size:.83rem; letter-spacing:.05em; margin-bottom:.55rem;
}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"]{
  background:linear-gradient(180deg,#070a1c 0%,#0a0d24 60%,#080b1e 100%);
  border-right:1px solid rgba(0,229,255,.22);
}
section[data-testid="stSidebar"] .stRadio label{
  letter-spacing:.08em; font-weight:600;
}
.cta-side{
  color:#00e5ff; font-weight:800; letter-spacing:.2em;
  font-size:.95rem; margin-bottom:.2rem;
}
.cta-live{
  display:flex; align-items:center; gap:.5rem; color:#9fb3d9;
  font-size:.75rem; letter-spacing:.18em; text-transform:uppercase;
}
.cta-dot{
  width:9px; height:9px; border-radius:50%; background:#06d6a0;
  box-shadow:0 0 10px #06d6a0; animation:blink 1.6s ease-in-out infinite;
}
@keyframes blink{0%,100%{opacity:.25}50%{opacity:1}}

/* ---------- tables / metric ---------- */
div[data-testid="stDataFrame"]{
  border:1px solid rgba(0,229,255,.25); border-radius:12px;
}
div[data-testid="stMetric"]{
  background:var(--panel); border:1px solid rgba(139,92,246,.35);
  border-radius:14px; padding:12px 14px;
}
div[data-testid="stTabs"] button{letter-spacing:.1em; font-weight:600;}
footer{visibility:hidden;}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# data access (cached, auto-builds anything that is missing)
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["date"])


def ensure_pipeline_stage(stage: str) -> None:
    """Run `python main.py --steps <stage>` if its artefacts are missing."""
    import subprocess

    checks = {
        "preprocess": C.CLEAN_CSV,
        "trends": C.TABLE_DIR / "trend_analysis.csv",
        "anomaly": C.PROCESSED_DIR / "climate_flagged.csv",
        "forecast": C.TABLE_DIR / "temperature_forecast.csv",
        "eda": C.TABLE_DIR / "yearly_summary.csv",
    }
    target = checks.get(stage)
    if target is not None and target.exists():
        return
    if not C.RAW_CSV.exists():
        subprocess.run([sys.executable, str(ROOT / "main.py"), "--regenerate",
                        "--steps", "generate"], cwd=str(ROOT), check=False)
    if stage == "preprocess":
        subprocess.run([sys.executable, str(ROOT / "main.py"),
                        "--steps", "preprocess"], cwd=str(ROOT), check=False)
        return
    subprocess.run([sys.executable, str(ROOT / "main.py"), "--steps", stage],
                   cwd=str(ROOT), check=False)


@st.cache_data(show_spinner=False)
def get_clean() -> pd.DataFrame:
    if not C.CLEAN_CSV.exists():
        return pd.DataFrame()
    return load_frame(C.CLEAN_CSV)


@st.cache_data(show_spinner=False)
def get_flagged() -> pd.DataFrame:
    p = C.PROCESSED_DIR / "climate_flagged.csv"
    if not p.exists():
        return pd.DataFrame()
    return load_frame(p)


@st.cache_data(show_spinner=False)
def get_forecast() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    f = C.TABLE_DIR / "temperature_forecast.csv"
    a = C.TABLE_DIR / "forecast_accuracy.csv"
    p = C.TABLE_DIR / "global_projections.csv"
    if not (f.exists() and a.exists() and p.exists()):
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
    fc = pd.read_csv(f, parse_dates=["date"])
    acc = pd.read_csv(a)
    proj = pd.read_csv(p)
    return fc, acc, proj


@st.cache_data(show_spinner=False)
def get_table(name: str, index_col: int | None = None) -> pd.DataFrame:
    path = C.TABLE_DIR / f"{name}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, index_col=index_col)


def kpi_cards(k: dict) -> None:
    cards = [
        ("DATA ROWS", f"{k['rows']:,}", f"◆ {k['regions']} regions | {k['years']}", "▲"),
        ("MEAN TEMP", f"{k['mean_temp_c']} C", "daily mean, full record", "●"),
        ("WARMING SHIFT", f"+{k['warming_c']} C", "last 5y vs first 5y", "▲"),
        ("CO2 LEVEL", f"{k['co2_now']} ppm", "latest annual mean", "◆"),
        ("SEA LEVEL", f"+{k['sea_rise_mm']} mm", "since start of record", "▼"),
        ("EXTREME DAYS", f"{k['anomaly_days']:,}", f"{k['anomaly_pct']} % of record", "■"),
    ]
    cols = st.columns(len(cards))
    for col, (label, value, delta, badge) in zip(cols, cards):
        neg = " neg" if value.startswith("-") else ""
        col.markdown(
            f"""
<div class="cta-card">
  <div class="cta-badge">{badge}</div>
  <div class="cta-label">{label}</div>
  <div class="cta-value">{value}</div>
  <div class="cta-delta{neg}">{delta}</div>
</div>""",
            unsafe_allow_html=True,
        )


def section(title: str, note: str = "") -> None:
    st.markdown(f'<div class="cta-sec">═ {title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="cta-note">{note}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="cta-side">◆ CLIMATE TREND ANALYZER</div>',
                unsafe_allow_html=True)
    st.markdown('<div class="cta-live"><span class="cta-dot"></span> pipeline online</div>',
                unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio(
        "NAVIGATE",
        ["OVERVIEW", "DATA EXPLORER", "3D CLIMATE WORLD", "TREND ANALYSIS",
         "EXTREME EVENTS", "FORECASTING", "REPORT & EXPORT"],
        label_visibility="collapsed",
    )
    st.markdown("---")

    region_box = st.multiselect(
        "REGIONS", [r[0] for r in C.REGIONS],
        default=[r[0] for r in C.REGIONS],
    )
    year_min, year_max = st.slider("YEAR RANGE", 1990, 2024, (1990, 2024))
    st.markdown("---")

    if st.button(" REBUILD PIPELINE", use_container_width=True):
        st.session_state["rebuild"] = True
    st.markdown(
        '<div class="cta-note">signs: ▲ up  ▼ down  ● live  ◆ module  '
        '■ block  ★ key  ✓ done</div>',
        unsafe_allow_html=True,
    )

if st.session_state.get("rebuild"):
    st.session_state["rebuild"] = False
    with st.spinner(" REBUILDING PIPELINE - DO NOT CLOSE THE TAB"):
        import subprocess
        subprocess.run([sys.executable, str(ROOT / "main.py"), "--regenerate"],
                       cwd=str(ROOT), check=False)
    st.cache_data.clear()

# ---------------------------------------------------------------------------
# header
# ---------------------------------------------------------------------------
st.markdown(
    '<div class="cta-title">CLIMATE TREND ANALYZER</div>'
    '<div class="cta-sub">statistical analysis &#183; anomaly detection &#183; '
    'forecasting &#183; virtual simulation 1990-2024</div>'
    '<div class="cta-rule"></div>',
    unsafe_allow_html=True,
)

# first-run bootstrap ------------------------------------------------------
if not C.CLEAN_CSV.exists():
    with st.spinner(" BUILDING DATASET - FIRST RUN ONLY"):
        ensure_pipeline_stage("preprocess")

df = get_clean()
if df.empty:
    st.error(" dataset missing - press REBUILD PIPELINE in the sidebar")
    st.stop()

if region_box:
    df = df[df["region"].isin(region_box)]
df = df[df["year"].between(year_min, year_max)]

from src.visuals import (  # noqa: E402
    fig_anomaly_heatmap, fig_animated_yearly, fig_climate_pillar,
    fig_forecast_lines, fig_scatter3d_anomalies, fig_surface_temperature,
    fig_yearly_lines, kpi_summary,
)

# ---------------------------------------------------------------------------
# pages
# ---------------------------------------------------------------------------
if page == "OVERVIEW":
    k = kpi_summary(df)
    kpi_cards(k)
    st.markdown("")
    c1, c2 = st.columns([1.25, 1])
    with c1:
        section("ANNUAL TEMPERATURE BY REGION",
                "line chart - each series is a region, dots mark yearly means")
        st.plotly_chart(fig_yearly_lines(df), use_container_width=True)
    with c2:
        section("CLIMATE PILLAR", "3D path of CO2 -> temperature -> sea level")
        st.plotly_chart(fig_climate_pillar(df), use_container_width=True)
    section("MONTHLY ANOMALY HEATMAP",
            "red = warmer than 1991-2020 normal, blue = cooler")
    st.plotly_chart(fig_anomaly_heatmap(df), use_container_width=True)

elif page == "DATA EXPLORER":
    section("DATASET PREVIEW", "cleaned + feature engineered frame")
    st.dataframe(df.head(120), use_container_width=True, height=340)

    q = get_table("data_quality_report")
    m = get_table("missing_values")
    c1, c2 = st.columns(2)
    with c1:
        section("DATA QUALITY LOG", "duplicates removed, values repaired")
        if not q.empty:
            st.dataframe(q, use_container_width=True, height=300, hide_index=True)
    with c2:
        section("MISSING VALUES", "post-cleaning audit - target is 0.000 %")
        if not m.empty:
            m2 = m[m["missing_count"] > 0]
            if m2.empty:
                st.success(" ✓ all columns complete - 0 missing cells")
            else:
                st.dataframe(m2, use_container_width=True, height=300,
                             hide_index=True)

    section("VARIABLE CORRELATION")
    corr = get_table("correlation_matrix", index_col=0)
    if not corr.empty:
        import plotly.express as px
        fig = px.imshow(corr.values, x=corr.columns, y=corr.index,
                        color_continuous_scale="RdBu_r",
                        zmin=-1, zmax=1,
                        text_auto=".2f", aspect="auto")
        fig.update_layout(template="plotly_dark", height=520,
                          paper_bgcolor="rgba(0,0,0,0)",
                          title="Correlation matrix")
        st.plotly_chart(fig, use_container_width=True)

    section("STATIC CHART GALLERY", "matplotlib outputs written by main.py")
    figs = sorted(C.FIGURE_DIR.glob("*.png"))
    if figs:
        cols = st.columns(2)
        for i, f in enumerate(figs):
            with cols[i % 2].container(border=True):
                st.image(str(f), caption=f.stem.replace("_", " ").upper())
    else:
        st.info(" ○ run the pipeline to generate charts")

elif page == "3D CLIMATE WORLD":
    ensure_pipeline_stage("anomaly")
    flagged = get_flagged()
    if flagged.empty:
        flagged = df
    reg3 = region_box[0] if region_box else None

    section("TEMPERATURE SURFACE", "x = month, y = year, z = mean temperature")
    st.plotly_chart(fig_surface_temperature(df, region=None),
                    use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("REGION SURFACE", "same surface filtered to one region")
        if reg3:
            st.plotly_chart(fig_surface_temperature(flagged, region=reg3),
                            use_container_width=True)
        else:
            st.info(" ○ select at least one region in the sidebar")
    with c2:
        section("ANOMALY SPACE", "year x heat anomaly x rainfall, × marks extremes")
        st.plotly_chart(fig_scatter3d_anomalies(flagged), use_container_width=True)

    section("ANIMATED WARMING", "press play - one frame per year")
    st.plotly_chart(fig_animated_yearly(df), use_container_width=True)

elif page == "TREND ANALYSIS":
    ensure_pipeline_stage("trends")
    trends = get_table("trend_analysis")
    shifts = get_table("seasonal_shift")

    if trends.empty:
        st.warning(" ○ trend tables missing - press REBUILD PIPELINE")
    else:
        t = trends[trends["variable"] == "temperature_c"].sort_values(
            "slope_per_decade", ascending=False)
        fastest = t.iloc[0]
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("FASTEST WARMING", fastest["region"],
                  f"{fastest['slope_per_decade']:+.2f} C / decade")
        k2.metric("SLOWEST WARMING", t.iloc[-1]["region"],
                  f"{t.iloc[-1]['slope_per_decade']:+.2f} C / decade")
        k3.metric("SIGNIFICANT TRENDS",
                  f"{int((t['mk_trend'] == 'increasing').sum())} / {len(t)}",
                  "Mann-Kendall p < 0.05")
        k4.metric("GLOBAL SHIFT",
                  f"{t['total_change'].mean():+.1f} C", "mean over record")

        section("TREND COEFFICIENTS", "OLS slope per decade with significance")
        st.dataframe(trends, use_container_width=True, hide_index=True, height=320)

        p1 = C.FIGURE_DIR / "09_trend_coefficients.png"
        p2 = C.FIGURE_DIR / "08_temperature_anomaly_trend.png"
        c1, c2 = st.columns(2)
        if p1.exists():
            with c1:
                st.image(str(p1), use_container_width=True)
        if p2.exists():
            with c2:
                st.image(str(p2), use_container_width=True)

        section("SEASONAL SHIFT", "centre-of-heat day moving earlier / later")
        if not shifts.empty:
            st.dataframe(shifts, use_container_width=True, hide_index=True)

        p3 = C.FIGURE_DIR / "10_rainfall_variability.png"
        p4 = C.FIGURE_DIR / "06_decadal_comparison.png"
        c3, c4 = st.columns(2)
        if p3.exists():
            with c3:
                st.image(str(p3), use_container_width=True)
        if p4.exists():
            with c4:
                st.image(str(p4), use_container_width=True)

elif page == "EXTREME EVENTS":
    ensure_pipeline_stage("anomaly")
    flagged = get_flagged()
    if flagged.empty:
        st.warning(" ○ anomaly output missing - press REBUILD PIPELINE")
        st.stop()
    flagged = flagged[flagged["region"].isin(region_box)] if region_box else flagged
    flagged = flagged[flagged["year"].between(year_min, year_max)]
    metrics = get_table("anomaly_metrics")
    summary = get_table("anomaly_summary")

    if not metrics.empty:
        m = metrics.iloc[0]
        b1, b2, b3, b4 = st.columns(4)
        b1.metric("DAY RECALL", f"{m['day_recall']:.0%}",
                  f"precision {m['day_precision']:.0%}")
        b2.metric("EVENT RECALL", f"{m['event_recall']:.0%}",
                  f"precision {m['event_precision']:.0%}")
        b3.metric("FLAGGED DAYS", f"{int(m['total_flagged_days']):,}",
                  f"truth days {int(m['truth_days']):,}")
        b4.metric("EVENTS FOUND", f"{int(m['matched_events'])} / {int(m['truth_events'])}",
                  "matched with ±2 day tolerance")

    region_pick = region_box[0] if region_box else C.REGIONS[0][0]
    section("EVENT TIMELINE", f"daily temperature with flagged extremes - {region_pick}")
    from src.visuals import fig_anomaly_timeline
    st.plotly_chart(fig_anomaly_timeline(flagged, region_pick),
                    use_container_width=True)

    section("DETECTED EVENTS BY TYPE")
    if not summary.empty:
        import plotly.express as px
        fig = px.bar(summary, x="region", y="count", color="anomaly_type",
                     barmode="stack", color_discrete_sequence=C.PALETTE,
                     title="Flagged days per region and type")
        fig.update_layout(template="plotly_dark", height=460,
                          paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

    top = get_table("top_anomalies")
    if not top.empty:
        section("TOP 100 ANOMALIES", "highest scoring days - exportable CSV")
        st.dataframe(top, use_container_width=True, height=340)
        st.download_button(" ↓ DOWNLOAD anomalies.csv",
                           top.to_csv(index=False).encode("utf-8"),
                           "anomalies_top100.csv", "text/csv")

elif page == "FORECASTING":
    ensure_pipeline_stage("forecast")
    forecast, accuracy, projections = get_forecast()
    if forecast.empty:
        st.warning(" ○ forecast outputs missing - press REBUILD PIPELINE")
        st.stop()

    mreg = region_box[0] if region_box else C.REGIONS[0][0]
    section("5-YEAR TEMPERATURE FORECAST",
            "Holt-Winters monthly model - dashed line = forecast")
    st.plotly_chart(fig_forecast_lines(
        df.groupby(["region", "date"], as_index=False)["temperature_c"].mean(),
        forecast, mreg), use_container_width=True)

    section("BACKTEST ACCURACY", "24-month hold-out: predicted vs actual")
    if not accuracy.empty:
        st.dataframe(accuracy, use_container_width=True, hide_index=True)
    p = C.FIGURE_DIR / "15_forecast_backtest.png"
    if p.exists():
        st.image(str(p), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        section("GLOBAL PROJECTIONS", "linear continuation to +10 years")
        if not projections.empty:
            st.dataframe(projections, use_container_width=True, hide_index=True,
                         height=330)
    with c2:
        p2 = C.FIGURE_DIR / "16_global_projections.png"
        if p2.exists():
            st.image(str(p2), use_container_width=True)

elif page == "REPORT & EXPORT":
    section("AUTOMATED REPORT", "markdown produced by main.py - stage 07")
    report_path = C.REPORT_DIR / "climate_report.md"
    if report_path.exists():
        content = report_path.read_text(encoding="utf-8")
        st.markdown(content)
        st.download_button(" ↓ DOWNLOAD climate_report.md",
                           content.encode("utf-8"), "climate_report.md",
                           "text/markdown")
    else:
        st.info(" ○ report missing - run the full pipeline first")

    section("TABLE EXPORTS")
    tables = sorted(C.TABLE_DIR.glob("*.csv"))
    if tables:
        cols = st.columns(3)
        for i, t in enumerate(tables):
            with cols[i % 3].container(border=True):
                st.markdown(f"**■ {t.stem}**")
                st.caption(f"{len(pd.read_csv(t)):,} rows")
                st.download_button(" ↓ download", t.read_bytes(),
                                   file_name=t.name, key=f"dl_{t.name}")
    else:
        st.info(" ○ no tables found")

    section("FIGURE EXPORTS")
    figs = sorted(C.FIGURE_DIR.glob("*.png"))
    if figs:
        cols = st.columns(4)
        for i, f in enumerate(figs):
            with cols[i % 4].container(border=True):
                st.image(str(f))
                st.download_button(" ↓ download", f.read_bytes(),
                                   file_name=f.name, key=f"df_{f.name}")
    else:
        st.info(" ○ no figures found")

# footer ---------------------------------------------------------------------
st.markdown(
    """
<div class="cta-rule" style="margin-top:1.6rem"></div>
<div class="cta-note" style="text-align:center">
  CLIMATE TREND ANALYZER  &#183;  python &#183; pandas &#183; scikit-learn
  &#183; statsmodels &#183; plotly &#183; streamlit  &#183;
  virtual simulation dataset 1990-2024  &#183;  built as student proof-of-work
</div>""",
    unsafe_allow_html=True,
)
