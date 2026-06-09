"""
chart_builder.py
──────────────────────────────────────────────────────────────────────────────
Builder untuk semua visualisasi Plotly dalam tema dark geo-science.
──────────────────────────────────────────────────────────────────────────────
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


# ─── Shared Theme ─────────────────────────────────────────────────────────────

PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#0d1117",
    font=dict(family="Space Grotesk, sans-serif", color="#e6edf3", size=12),
    xaxis=dict(
        gridcolor="#21262d",
        linecolor="#30363d",
        tickcolor="#30363d",
        showgrid=True,
    ),
    yaxis=dict(
        gridcolor="#21262d",
        linecolor="#30363d",
        tickcolor="#30363d",
        showgrid=True,
    ),
    legend=dict(
        bgcolor="rgba(22,27,34,0.8)",
        bordercolor="#21262d",
        borderwidth=1,
        font=dict(color="#c9d1d9"),
    ),
    margin=dict(l=50, r=30, t=60, b=50),
    hovermode="x unified",
)

COLOR_RAIN = "#00b4d8"
COLOR_MAX = "#f3722c"
COLOR_P95 = "#f9c74f"
COLOR_HEAVY = "#f94144"
COLOR_MIN = "#48cae4"
COLOR_MEAN = "#90e0ef"


# ─── Time Series Chart ────────────────────────────────────────────────────────

def plot_time_series(df: pd.DataFrame, threshold: float, dataset_label: str) -> go.Figure:
    """
    Area chart time series curah hujan dengan:
    - Area fill untuk mean curah hujan
    - Line untuk nilai maksimum
    - Shaded region untuk P95
    - Garis horizontal threshold (hujan lebat)
    - Shaded background untuk kejadian ekstrem
    """

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        shared_xaxes=True,
        vertical_spacing=0.06,
        subplot_titles=["Curah Hujan Harian (mm)", "StdDev Spasial (mm)"],
    )

    x = df["date"]

    # ── Row 1: Main rainfall traces ──
    # Area fill: mean
    fig.add_trace(
        go.Scatter(
            x=x, y=df["mean"],
            name="Mean Spasial",
            fill="tozeroy",
            fillcolor="rgba(0,180,216,0.15)",
            line=dict(color=COLOR_RAIN, width=2),
            hovertemplate="<b>Mean</b>: %{y:.2f} mm<extra></extra>",
        ),
        row=1, col=1,
    )

    # Line: max
    fig.add_trace(
        go.Scatter(
            x=x, y=df["max"],
            name="Maksimum",
            line=dict(color=COLOR_MAX, width=1.5, dash="dot"),
            hovertemplate="<b>Max</b>: %{y:.2f} mm<extra></extra>",
        ),
        row=1, col=1,
    )

    # Line: P95
    p_col = [c for c in df.columns if c.startswith("p") and c[1:].isdigit()]
    if p_col:
        fig.add_trace(
            go.Scatter(
                x=x, y=df[p_col[0]],
                name=f"P{p_col[0][1:]} (Persentil)",
                line=dict(color=COLOR_P95, width=1.5, dash="dash"),
                hovertemplate=f"<b>{p_col[0].upper()}</b>: %{{y:.2f}} mm<extra></extra>",
            ),
            row=1, col=1,
        )

    # Threshold line
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=COLOR_HEAVY,
        line_width=1.5,
        annotation_text=f"  Threshold: {threshold} mm",
        annotation_font_color=COLOR_HEAVY,
        annotation_font_size=11,
        row=1, col=1,
    )

    # Highlight extreme events
    heavy_mask = df["mean"] >= threshold
    if heavy_mask.any():
        heavy_dates = df.loc[heavy_mask, "date"]
        for hd in heavy_dates:
            fig.add_vrect(
                x0=hd - pd.Timedelta(hours=12),
                x1=hd + pd.Timedelta(hours=12),
                fillcolor="rgba(249,65,68,0.08)",
                line_width=0,
                row=1, col=1,
            )

    # ── Row 2: StdDev ──
    if "stddev" in df.columns:
        fig.add_trace(
            go.Bar(
                x=x, y=df["stddev"],
                name="StdDev",
                marker_color="rgba(144,224,239,0.6)",
                hovertemplate="<b>StdDev</b>: %{y:.2f} mm<extra></extra>",
            ),
            row=2, col=1,
        )

    layout = PLOTLY_LAYOUT.copy()
    layout.update(
        title=dict(
            text=f"<b>Time Series Curah Hujan</b> — {dataset_label}",
            font=dict(size=15, color="#e6edf3"),
        ),
        height=500,
        showlegend=True,
    )
    fig.update_layout(**layout)
    fig.update_xaxes(gridcolor="#21262d", linecolor="#30363d")
    fig.update_yaxes(gridcolor="#21262d", linecolor="#30363d")

    return fig


# ─── Statistics Bar Chart ─────────────────────────────────────────────────────

def plot_statistics_bar(df: pd.DataFrame, percentile: int = 95) -> go.Figure:
    """
    Grouped bar chart statistik spasial agregat (bulanan).
    """

    df_copy = df.copy()
    df_copy["month"] = df_copy["date"].dt.to_period("M").astype(str)
    monthly = df_copy.groupby("month").agg({
        "mean": "mean",
        "max": "max",
        "min": "mean",
        **{f"p{percentile}": "mean"} if f"p{percentile}" in df_copy.columns else {},
    }).reset_index()

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["mean"],
        name="Mean Bulanan",
        marker_color=COLOR_RAIN,
        opacity=0.9,
    ))

    fig.add_trace(go.Bar(
        x=monthly["month"], y=monthly["max"],
        name="Max Bulanan",
        marker_color=COLOR_MAX,
        opacity=0.7,
    ))

    if f"p{percentile}" in monthly.columns:
        fig.add_trace(go.Bar(
            x=monthly["month"], y=monthly[f"p{percentile}"],
            name=f"P{percentile} Bulanan",
            marker_color=COLOR_P95,
            opacity=0.7,
        ))

    layout = PLOTLY_LAYOUT.copy()
    layout.update(
        title="<b>Statistik Curah Hujan Bulanan</b>",
        barmode="group",
        height=380,
        xaxis_title="Bulan",
        yaxis_title="Curah Hujan (mm)",
    )
    fig.update_layout(**layout)

    return fig


# ─── Monthly Summary Bar ──────────────────────────────────────────────────────

def plot_monthly_summary(df: pd.DataFrame) -> go.Figure:
    """
    Bar chart total curah hujan bulanan (akumulasi).
    """

    df_copy = df.copy()
    df_copy["month"] = df_copy["date"].dt.to_period("M").astype(str)
    monthly_total = df_copy.groupby("month")["mean"].sum().reset_index()
    monthly_total.columns = ["month", "total_rain"]

    colors = px.colors.sequential.Blues[3:]
    n = len(monthly_total)
    bar_colors = [colors[int(i / n * (len(colors) - 1))] for i in range(n)]

    fig = go.Figure(go.Bar(
        x=monthly_total["month"],
        y=monthly_total["total_rain"],
        marker_color=bar_colors,
        hovertemplate="<b>%{x}</b><br>Total: %{y:.1f} mm<extra></extra>",
        name="Total Hujan",
    ))

    layout = PLOTLY_LAYOUT.copy()
    layout.update(
        title="<b>Akumulasi Curah Hujan per Bulan</b>",
        height=340,
        xaxis_title="Bulan",
        yaxis_title="Total Curah Hujan (mm)",
        showlegend=False,
    )
    fig.update_layout(**layout)

    return fig


# ─── Threshold Heatmap ────────────────────────────────────────────────────────

def plot_threshold_heatmap(df: pd.DataFrame, threshold: float = 50.0) -> go.Figure:
    """
    Calendar heatmap (bulan × minggu) intensitas curah hujan.
    Diinspirasi oleh GitHub contribution graph.
    """

    df_copy = df.copy()
    df_copy["month"] = df_copy["date"].dt.month
    df_copy["day_of_week"] = df_copy["date"].dt.dayofweek
    df_copy["week"] = df_copy["date"].dt.isocalendar().week.astype(int)
    df_copy["year_month"] = df_copy["date"].dt.to_period("M").astype(str)

    # Pivot: bulan vs hari dalam bulan
    df_copy["day_of_month"] = df_copy["date"].dt.day
    months = sorted(df_copy["year_month"].unique())

    fig = go.Figure()

    # Heatmap per bulan
    pivot = df_copy.pivot_table(
        index="year_month",
        columns="day_of_month",
        values="mean",
        aggfunc="mean",
    )

    z = pivot.values
    y_labels = list(pivot.index)
    x_labels = list(pivot.columns)

    # Custom colorscale: biru tua → putih → oranye → merah
    colorscale = [
        [0.0, "#0d1117"],
        [0.1, "#023e8a"],
        [0.3, "#0077b6"],
        [0.5, "#00b4d8"],
        [0.65, "#90e0ef"],
        [0.75, "#f9c74f"],
        [0.85, "#f3722c"],
        [1.0, "#f94144"],
    ]

    fig.add_trace(go.Heatmap(
        z=z,
        x=[f"Hari {d}" for d in x_labels],
        y=y_labels,
        colorscale=colorscale,
        hovertemplate="<b>%{y}</b> — %{x}<br>Curah Hujan: %{z:.1f} mm<extra></extra>",
        colorbar=dict(
            title="mm/hari",
            titlefont=dict(color="#e6edf3"),
            tickfont=dict(color="#e6edf3"),
            bgcolor="rgba(22,27,34,0.8)",
            bordercolor="#21262d",
        ),
    ))

    layout = PLOTLY_LAYOUT.copy()
    layout.update(
        title=f"<b>Heatmap Intensitas Curah Hujan</b> (Threshold: {threshold} mm)",
        height=max(250, 40 * len(y_labels) + 100),
        xaxis=dict(
            **layout["xaxis"],
            title="Hari dalam Bulan",
            tickfont=dict(size=9),
        ),
        yaxis=dict(
            **layout["yaxis"],
            title="Bulan",
            tickfont=dict(size=10),
        ),
    )
    fig.update_layout(**layout)

    return fig
