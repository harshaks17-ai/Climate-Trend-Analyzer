"""Interactive Plotly visualisation layer (3D + animated) for the dashboard.

Every function returns a `plotly.graph_objects.Figure` styled with the dark
theme of the app, so the Streamlit UI only has to call them.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from . import config as C

DARK = dict(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(10,14,36,0.55)",
    font=dict(family="Segoe UI, Inter, sans-serif", color="#e6f1ff", size=13),
    margin=dict(l=40, r=20, t=60, b=40),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
)


def _apply(fig: go.Figure, title: str, height: int = 520) -> go.Figure:
    fig.update_layout(**DARK, title=dict(text=title, x=0.02, font=dict(size=18)),
                      height=height)
    return fig


# ---------------------------------------------------------------------------
# KPI helpers
# ---------------------------------------------------------------------------
def kpi_summary(df: pd.DataFrame) -> dict:
    """Headline numbers for the dashboard cards."""
    yearly = df.groupby("year")["temp_anomaly_c"].mean()
    first = yearly.iloc[:5].mean()
    last = yearly.iloc[-5:].mean()
    anomaly_days = int(df["is_anomaly"].sum()) if "is_anomaly" in df else 0
    return {
        "rows": int(len(df)),
        "regions": int(df["region"].nunique()),
        "years": f"{int(df['year'].min())}-{int(df['year'].max())}",
        "warming_c": round(float(last - first), 2),
        "mean_temp_c": round(float(df["temperature_c"].mean()), 2),
        "total_rain_mm": round(float(df["rainfall_mm"].sum() / 1000), 1),
        "co2_now": round(float(df.groupby("year")["co2_ppm"].mean().iloc[-1]), 1),
        "sea_rise_mm": round(float(
            df.groupby("year")["sea_level_mm"].mean().iloc[-1]
            - df.groupby("year")["sea_level_mm"].mean().iloc[0]), 1),
        "anomaly_days": anomaly_days,
        "anomaly_pct": round(100 * anomaly_days / max(1, len(df)), 2),
    }


# ---------------------------------------------------------------------------
# 1. 3D surface: month x year -> temperature
# ---------------------------------------------------------------------------
def fig_surface_temperature(df: pd.DataFrame, region: str | None = None) -> go.Figure:
    data = df if region is None else df[df["region"] == region]
    pivot = (data.groupby(["year", "month"])["temperature_c"]
             .mean().unstack("month").sort_index())
    z = pivot.to_numpy()
    fig = go.Figure(data=[go.Surface(
        x=pivot.columns.to_numpy(), y=pivot.index.to_numpy(), z=z,
        colorscale="Turbo", colorbar=dict(title="C"),
        contours_z=dict(show=True, usecolormap=True, highlightcolor="#00e5ff"),
    )])
    title = "3D Temperature Surface: Month x Year"
    if region:
        title += f"  |  {region}"
    _apply(fig, title, height=640)
    fig.update_layout(scene=dict(
        xaxis_title="Month", yaxis_title="Year", zaxis_title="Temperature (C)",
        xaxis=dict(backgroundcolor="rgba(0,0,0,0)"),
        yaxis=dict(backgroundcolor="rgba(0,0,0,0)"),
        zaxis=dict(backgroundcolor="rgba(0,0,0,0)"),
        aspectmode="manual", aspectratio=dict(x=1.4, y=1.6, z=0.7),
    ))
    fig.update_scenes(camera=dict(eye=dict(x=1.6, y=-1.7, z=0.9)))
    return fig


# ---------------------------------------------------------------------------
# 2. 3D scatter: temperature anomaly vs rainfall over time
# ---------------------------------------------------------------------------
def fig_scatter3d_anomalies(df: pd.DataFrame, sample: int = 6000) -> go.Figure:
    cols = ["date", "region", "temp_anomaly_c", "rainfall_mm", "year"]
    if "is_anomaly" in df.columns:
        cols.append("is_anomaly")
    d = df[cols].dropna().copy()

    if "is_anomaly" in d.columns:
        anom = d[d["is_anomaly"].astype(bool)]
        normal = d[~d["is_anomaly"].astype(bool)]
    else:
        anom = d.iloc[0:0]
        normal = d
    keep_n = max(0, sample - len(anom))
    if keep_n > 0 and len(normal) > keep_n:
        normal = normal.sample(keep_n, random_state=C.SEED)
    elif len(normal) > 5000:
        normal = normal.sample(5000, random_state=C.SEED)
    d = pd.concat([normal, anom], ignore_index=True)
    if len(d) > 1:
        d = d.sample(frac=1.0, random_state=C.SEED).reset_index(drop=True)

    has_flag = "is_anomaly" in d.columns
    d["event"] = np.where(d["is_anomaly"].astype(bool) if has_flag else False,
                          "extreme day", "normal day")
    fig = px.scatter_3d(
        d, x="year", y="temp_anomaly_c", z="rainfall_mm",
        color="region", symbol="event",
        opacity=0.75,
        category_orders={"event": ["normal day", "extreme day"]},
        symbol_sequence=["circle", "x"],
        color_discrete_sequence=C.PALETTE,
        hover_data={"date": True, "temp_anomaly_c": ":.2f", "rainfall_mm": ":.1f"},
        title="3D Anomaly Space: Year x Heat Anomaly x Rainfall",
    )
    fig.update_traces(marker=dict(size=3.2, line=dict(width=0)))
    fig.update_layout(**DARK, height=640)
    fig.update_scenes(
        xaxis_title="Year", yaxis_title="Heat anomaly (C)",
        zaxis_title="Rainfall (mm/day)",
        aspectmode="auto", camera=dict(eye=dict(x=1.5, y=-1.6, z=0.8)),
    )
    return fig


# ---------------------------------------------------------------------------
# 3. animated yearly bars (frames = years)
# ---------------------------------------------------------------------------
def fig_animated_yearly(df: pd.DataFrame) -> go.Figure:
    yearly = (df.groupby(["region", "year"], as_index=False)
              .agg(temp_c=("temperature_c", "mean"),
                   rain_mm=("rainfall_mm", "sum")))
    fig = px.bar(
        yearly, x="region", y="temp_c", color="region",
        animation_frame="year", animation_group="region",
        range_y=[yearly["temp_c"].min() - 2, yearly["temp_c"].max() + 2],
        color_discrete_sequence=C.PALETTE,
        title="Animated Warming: Mean Temperature per Region (one frame = one year)",
        labels={"temp_c": "Temperature (C)", "region": "Region"},
    )
    fig.update_layout(**DARK, height=560, showlegend=False)
    fig.update_yaxes(rangemode="tozero", gridcolor="rgba(255,255,255,0.08)")
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)")
    return fig


# ---------------------------------------------------------------------------
# 4. animated heatmap: month x year anomaly
# ---------------------------------------------------------------------------
def fig_anomaly_heatmap(df: pd.DataFrame, region: str | None = None) -> go.Figure:
    data = df if region is None else df[df["region"] == region]
    pivot = (data.groupby(["year", "month"])["temp_anomaly_c"]
             .mean().unstack("month").sort_index())
    span = float(np.nanmax(np.abs(pivot.to_numpy()))) or 1.0
    fig = px.imshow(
        pivot, x=pivot.columns, y=pivot.index,
        color_continuous_scale="RdBu_r",
        zmin=-span, zmax=span,
        labels=dict(x="Month", y="Year", color="Anomaly (C)"),
        aspect="auto",
    )
    _apply(fig, "Monthly Temperature Anomaly Heatmap (vs 1991-2020 normal)", 560)
    fig.update_xaxes(dtick=1)
    return fig


# ---------------------------------------------------------------------------
# 5. 3D rising line: CO2 -> temperature -> sea level
# ---------------------------------------------------------------------------
def fig_climate_pillar(df: pd.DataFrame) -> go.Figure:
    d = (df.groupby("year", as_index=False)
         .agg(co2=("co2_ppm", "mean"), temp=("temperature_c", "mean"),
              sea=("sea_level_mm", "mean")))
    fig = go.Figure(data=[go.Scatter3d(
        x=d["co2"], y=d["temp"], z=d["sea"],
        mode="lines+markers+text",
        line=dict(color="#00e5ff", width=6),
        marker=dict(size=4, color=d["year"], colorscale="Viridis",
                    showscale=True, colorbar=dict(title="Year")),
        text=[str(y) for y in d["year"]], textposition="top center",
        textfont=dict(size=8, color="#9fb3d9"),
        hovertemplate="CO2 %{x} ppm<br>Temp %{y:.1f} C<br>Year %{customdata}<extra></extra>",
        customdata=d["year"],
    )])
    _apply(fig, "3D Climate Pillar: CO2 -> Temperature -> Sea Level (1990-2024)", 620)
    fig.update_scenes(
        xaxis_title="CO2 (ppm)", yaxis_title="Temperature (C)",
        zaxis_title="Sea level (mm)",
        aspectmode="auto", camera=dict(eye=dict(x=1.7, y=-1.5, z=0.7)),
    )
    return fig


# ---------------------------------------------------------------------------
# 6. forecast lines
# ---------------------------------------------------------------------------
def fig_forecast_lines(monthly: pd.DataFrame, forecast: pd.DataFrame,
                       region: str) -> go.Figure:
    hist = monthly[monthly["region"] == region]
    fc = forecast[forecast["region"] == region]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=hist["date"], y=hist["temperature_c"],
                             mode="lines", name="observed",
                             line=dict(color=C.PALETTE[0], width=2)))
    fig.add_trace(go.Scatter(x=fc["date"], y=fc["forecast_temp_c"],
                             mode="lines", name="forecast",
                             line=dict(color=C.PALETTE[1], width=3, dash="dash")))
    fig.add_vline(x=pd.Timestamp(f"{C.END_YEAR}-12-01"),
                  line_dash="dot", line_color="#ffd166")
    _apply(fig, f"Temperature Forecast - {region}", 460)
    fig.update_layout(xaxis_title="Date", yaxis_title="Temperature (C)",
                      legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06))
    return fig


# ---------------------------------------------------------------------------
# 7. anomaly timeline with markers
# ---------------------------------------------------------------------------
def fig_anomaly_timeline(flagged: pd.DataFrame, region: str) -> go.Figure:
    d = flagged[flagged["region"] == region]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=d["date"], y=d["temperature_c"], mode="lines",
                             name="daily temperature",
                             line=dict(color=C.PALETTE[0], width=1)))
    fig.add_trace(go.Scatter(x=d["date"], y=d["temp_roll_365d_c"], mode="lines",
                             name="365d climate mean",
                             line=dict(color=C.PALETTE[5], width=2.4)))
    an = d[d["is_anomaly"]]
    fig.add_trace(go.Scatter(x=an["date"], y=an["temperature_c"], mode="markers",
                             name="flagged extremes",
                             marker=dict(color=C.PALETTE[1], size=5,
                                         symbol="x", line=dict(width=1))))
    _apply(fig, f"Extreme Event Detection - {region}", 470)
    fig.update_layout(xaxis_title="Date", yaxis_title="Temperature (C)",
                      legend=dict(orientation="h", y=1.12, x=0))
    fig.update_xaxes(rangeslider=dict(visible=True, thickness=0.06))
    return fig


# ---------------------------------------------------------------------------
# 8. region comparison line
# ---------------------------------------------------------------------------
def fig_yearly_lines(df: pd.DataFrame) -> go.Figure:
    yearly = (df.groupby(["region", "year"], as_index=False)
              .agg(temp_c=("temperature_c", "mean")))
    fig = px.line(yearly, x="year", y="temp_c", color="region",
                  color_discrete_sequence=C.PALETTE, markers=True,
                  title="Annual Mean Temperature by Region",
                  labels={"temp_c": "Temperature (C)"})
    fig.update_layout(**DARK, height=480)
    fig.update_traces(line=dict(width=2.5))
    return fig
