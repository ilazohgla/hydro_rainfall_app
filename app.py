"""
================================================================================
  HYDRO RAINFALL ANALYZER
  Analisis Curah Hujan Multi-Dataset via Google Earth Engine
  Author  : Hydrology Analyst Portfolio
  Stack   : Python · Streamlit · geemap · Earth Engine API · Plotly
================================================================================
"""

import streamlit as st
import ee
import geemap.foliumap as geemap
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import json
import os
from datetime import date, timedelta
from utils.ee_auth import initialize_ee
from utils.ee_processing import (
    aggregate_to_daily,
    build_stats_fc,
    compute_threshold_summary,
    get_dataset_config,
)
from utils.chart_builder import (
    plot_time_series,
    plot_statistics_bar,
    plot_threshold_heatmap,
    plot_monthly_summary,
)
from config.settings import APP_CONFIG, DATASET_OPTIONS, THRESHOLD_OPTIONS

# ─── Page Configuration ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hydro Rainfall Analyzer",
    page_icon="🌧️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Load Custom CSS ─────────────────────────────────────────────────────────
def load_css():
    css = """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {
            font-family: 'Space Grotesk', sans-serif;
        }

        /* Dark geo-science theme */
        .stApp {
            background: #0d1117;
            color: #e6edf3;
        }

        .main-header {
            background: linear-gradient(135deg, #0f3460 0%, #16213e 50%, #0a3d62 100%);
            border: 1px solid #1e3a5f;
            border-radius: 12px;
            padding: 2rem 2.5rem;
            margin-bottom: 1.5rem;
            position: relative;
            overflow: hidden;
        }

        .main-header::before {
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 300px;
            height: 300px;
            background: radial-gradient(circle, rgba(0, 180, 216, 0.15) 0%, transparent 70%);
            border-radius: 50%;
        }

        .main-header h1 {
            font-size: 2.2rem;
            font-weight: 700;
            color: #ffffff;
            margin: 0;
            letter-spacing: -0.02em;
        }

        .main-header .subtitle {
            color: #00b4d8;
            font-size: 0.95rem;
            font-weight: 400;
            margin-top: 0.4rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }

        .badge-pill {
            display: inline-block;
            background: rgba(0, 180, 216, 0.15);
            border: 1px solid rgba(0, 180, 216, 0.4);
            color: #00b4d8;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.72rem;
            padding: 2px 10px;
            border-radius: 20px;
            margin-right: 6px;
            margin-top: 8px;
        }

        /* Metric cards */
        .metric-card {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 10px;
            padding: 1.2rem 1.4rem;
            text-align: center;
            transition: border-color 0.2s;
        }

        .metric-card:hover { border-color: #00b4d8; }

        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #00b4d8;
            font-family: 'JetBrains Mono', monospace;
        }

        .metric-label {
            font-size: 0.8rem;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin-top: 4px;
        }

        .metric-unit {
            font-size: 0.85rem;
            color: #58a6ff;
        }

        /* Section titles */
        .section-title {
            font-size: 0.75rem;
            font-weight: 600;
            color: #8b949e;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            border-bottom: 1px solid #21262d;
            padding-bottom: 6px;
            margin-bottom: 14px;
        }

        /* Sidebar */
        [data-testid="stSidebar"] {
            background: #0d1117;
            border-right: 1px solid #21262d;
        }

        /* Status badges */
        .status-success { color: #3fb950; }
        .status-warning { color: #d29922; }
        .status-error   { color: #f85149; }

        /* Info panel */
        .info-panel {
            background: #161b22;
            border-left: 3px solid #00b4d8;
            border-radius: 0 8px 8px 0;
            padding: 0.9rem 1.2rem;
            font-size: 0.87rem;
            color: #c9d1d9;
            margin: 0.8rem 0;
        }

        /* Plotly chart background override */
        .js-plotly-plot .plotly .main-svg {
            background: transparent !important;
        }

        /* Streamlit widget overrides */
        .stSelectbox > div > div,
        .stDateInput > div > div > input {
            background: #161b22 !important;
            border-color: #21262d !important;
            color: #e6edf3 !important;
        }

        .stButton > button {
            background: linear-gradient(135deg, #00b4d8, #0077b6);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            letter-spacing: 0.04em;
            padding: 0.5rem 1.5rem;
            width: 100%;
            transition: opacity 0.2s;
        }

        .stButton > button:hover { opacity: 0.85; }

        div[data-testid="stExpander"] {
            background: #161b22;
            border: 1px solid #21262d;
            border-radius: 8px;
        }

        .stTabs [data-baseweb="tab-list"] {
            background: #161b22;
            border-radius: 8px;
            border: 1px solid #21262d;
        }

        .stTabs [data-baseweb="tab"] {
            color: #8b949e;
            font-weight: 500;
        }

        .stTabs [aria-selected="true"] {
            color: #00b4d8 !important;
        }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ─── Header Component ─────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>🌧️ Hydro Rainfall Analyzer</h1>
        <div class="subtitle">Analisis Curah Hujan Spasial · Multi-Dataset · Google Earth Engine</div>
        <div style="margin-top: 10px;">
            <span class="badge-pill">GPM IMERG</span>
            <span class="badge-pill">CHIRPS</span>
            <span class="badge-pill">GSMaP</span>
            <span class="badge-pill">Streamlit Cloud</span>
            <span class="badge-pill">Earth Engine</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar: Control Panel ───────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Control Panel")
        st.markdown('<div class="section-title">Dataset Configuration</div>', unsafe_allow_html=True)

        dataset = st.selectbox(
            "Pilih Dataset Curah Hujan",
            options=list(DATASET_OPTIONS.keys()),
            format_func=lambda x: DATASET_OPTIONS[x]["label"],
            help="GPM IMERG: resolusi 0.1°/30 menit | CHIRPS: 0.05°/harian | GSMaP: 0.1°/1 jam",
        )

        st.markdown('<div class="section-title" style="margin-top:16px;">Periode Analisis</div>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            default_start = date.today() - timedelta(days=30)
            start_date = st.date_input("Mulai", value=default_start, min_value=date(2000, 1, 1))
        with col2:
            end_date = st.date_input("Selesai", value=date.today() - timedelta(days=1))

        if start_date >= end_date:
            st.error("⚠️ Tanggal mulai harus lebih awal dari tanggal selesai.")
            return None

        st.markdown('<div class="section-title" style="margin-top:16px;">Area of Interest (AOI)</div>', unsafe_allow_html=True)

        aoi_method = st.radio(
            "Metode AOI",
            ["Bounding Box Manual", "Unggah GeoJSON", "Provinsi Indonesia"],
            horizontal=False,
        )

        aoi_geometry = None

        if aoi_method == "Bounding Box Manual":
            with st.expander("📐 Koordinat Bounding Box", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    lon_min = st.number_input("Lon Min", value=106.5, format="%.4f")
                    lat_min = st.number_input("Lat Min", value=-7.5, format="%.4f")
                with c2:
                    lon_max = st.number_input("Lon Max", value=107.5, format="%.4f")
                    lat_max = st.number_input("Lat Max", value=-6.5, format="%.4f")
                aoi_geometry = ee.Geometry.Rectangle([lon_min, lat_min, lon_max, lat_max])

        elif aoi_method == "Unggah GeoJSON":
            uploaded = st.file_uploader("Upload file .geojson", type=["geojson", "json"])
            if uploaded:
                try:
                    geojson_data = json.load(uploaded)
                    aoi_geometry = ee.Geometry(geojson_data["features"][0]["geometry"])
                    st.success("✅ GeoJSON berhasil dimuat")
                except Exception as e:
                    st.error(f"❌ Gagal membaca GeoJSON: {e}")

        elif aoi_method == "Provinsi Indonesia":
            from config.settings import INDONESIA_PROVINCES
            prov = st.selectbox("Pilih Provinsi", list(INDONESIA_PROVINCES.keys()))
            coords = INDONESIA_PROVINCES[prov]
            aoi_geometry = ee.Geometry.Rectangle(coords)

        st.markdown('<div class="section-title" style="margin-top:16px;">Parameter Analisis</div>', unsafe_allow_html=True)

        aggregation = st.selectbox(
            "Agregasi Temporal",
            ["Harian", "Mingguan", "Bulanan"],
        )

        threshold = st.select_slider(
            "Threshold Hujan Lebat (mm/hari)",
            options=THRESHOLD_OPTIONS,
            value=50,
        )

        percentile = st.slider("Persentil Statistik (Px)", min_value=50, max_value=99, value=95, step=1)

        run = st.button("🚀 Jalankan Analisis", type="primary")

        st.markdown("---")
        st.markdown("""
        <div style="font-size:0.78rem; color:#8b949e; line-height:1.6;">
            <b style="color:#c9d1d9;">Hydro Rainfall Analyzer</b><br>
            Dibangun dengan Earth Engine Python API + geemap + Streamlit.<br><br>
            📌 <a href="https://github.com" style="color:#58a6ff;">GitHub Repository</a><br>
            📄 <a href="https://earthengine.google.com" style="color:#58a6ff;">GEE Documentation</a>
        </div>
        """, unsafe_allow_html=True)

        return {
            "dataset": dataset,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "aoi": aoi_geometry,
            "aggregation": aggregation,
            "threshold": threshold,
            "percentile": percentile,
            "run": run,
        }


# ─── Metric Cards Row ─────────────────────────────────────────────────────────
def render_metrics(stats: dict):
    cols = st.columns(5)
    metrics = [
        ("Total Curah Hujan", stats.get("total", 0), "mm"),
        ("Rata-rata Harian", stats.get("mean", 0), "mm/hr"),
        ("Maksimum", stats.get("max", 0), "mm/hr"),
        ("P95", stats.get("p95", 0), "mm/hr"),
        ("Hari Hujan Lebat", stats.get("heavy_days", 0), "hari"),
    ]
    for col, (label, value, unit) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{value:.1f}</div>
                <div class="metric-unit">{unit}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)


# ─── Map Component ────────────────────────────────────────────────────────────
def render_map(params: dict, image: ee.Image, aoi: ee.Geometry):
    st.markdown('<div class="section-title">🗺️ Peta Spasial</div>', unsafe_allow_html=True)

    cfg = get_dataset_config(params["dataset"])
    m = geemap.Map(
        center=[-2.5, 118],
        zoom=5,
        basemap="CartoDB.DarkMatter",
    )

    vis_params = {
        "min": 0,
        "max": cfg["vis_max"],
        "palette": ["#001219", "#0077b6", "#00b4d8", "#90e0ef", "#caf0f8",
                    "#ade8f4", "#48cae4", "#023e8a", "#f0f4c3", "#f9c74f",
                    "#f3722c", "#f94144"],
    }

    m.addLayer(image, vis_params, f"Curah Hujan - {cfg['label']}", True)
    m.addLayer(aoi, {"color": "#00b4d8", "fillColor": "00000000", "width": 2}, "AOI", True)
    m.add_colorbar(vis_params, label="mm/hari", orientation="vertical", layer_name=cfg["label"])

    map_html = m.to_html()
    st.components.v1.html(map_html, height=480, scrolling=False)


# ─── Main App Logic ───────────────────────────────────────────────────────────
def main():
    load_css()
    render_header()

    # ── Initialize EE ──
    with st.spinner("Menginisialisasi Google Earth Engine..."):
        success, msg = initialize_ee()

    if not success:
        st.error(f"❌ Gagal menginisialisasi Earth Engine: {msg}")
        st.info("💡 Pastikan variabel lingkungan `GEE_SERVICE_ACCOUNT` dan `GEE_PRIVATE_KEY` sudah dikonfigurasi di Streamlit Cloud Secrets.")
        st.stop()

    # ── Sidebar Controls ──
    params = render_sidebar()
    if params is None:
        st.stop()

    # ── Default State ──
    if not params["run"]:
        # Landing / idle state
        col_info, col_guide = st.columns([2, 1])
        with col_info:
            st.markdown("""
            <div class="info-panel">
                🌊 <b>Selamat datang di Hydro Rainfall Analyzer!</b><br>
                Pilih dataset, tentukan periode dan AOI di panel kiri, lalu klik
                <b>Jalankan Analisis</b> untuk memulai pemrosesan via Google Earth Engine.
            </div>
            """, unsafe_allow_html=True)

            with st.expander("📚 Dataset yang Tersedia", expanded=True):
                for key, val in DATASET_OPTIONS.items():
                    st.markdown(f"""
                    **{val['label']}**
                    - Resolusi Spasial: `{val['spatial_res']}`
                    - Resolusi Temporal: `{val['temporal_res']}`
                    - Cakupan: {val['coverage']}
                    """)

        with col_guide:
            st.markdown("""
            <div class="info-panel">
                <b>Alur Kerja</b><br><br>
                1️⃣ Pilih dataset curah hujan<br>
                2️⃣ Tentukan rentang tanggal<br>
                3️⃣ Definisikan Area of Interest<br>
                4️⃣ Atur parameter analisis<br>
                5️⃣ Klik Jalankan Analisis
            </div>
            """, unsafe_allow_html=True)
        return

    # ── Run Analysis ──
    if params["aoi"] is None:
        st.warning("⚠️ Harap definisikan Area of Interest (AOI) terlebih dahulu.")
        st.stop()

    progress = st.progress(0, text="Memulai analisis...")

    try:
        # Step 1: Aggregate to daily
        progress.progress(15, text="🛰️ Mengambil & mengagregasi data dari GEE...")
        cfg = get_dataset_config(params["dataset"])
        daily_collection = aggregate_to_daily(
            dataset_id=cfg["id"],
            band=cfg["band"],
            scale_factor=cfg["scale_factor"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            aoi=params["aoi"],
            aggregation=params["aggregation"],
        )

        # Step 2: Build statistics FeatureCollection
        progress.progress(40, text="📊 Menghitung statistik spasial (Mean, Max, P95)...")
        stats_df = build_stats_fc(
            collection=daily_collection,
            aoi=params["aoi"],
            scale=cfg["scale"],
            percentile=params["percentile"],
        )

        # Step 3: Threshold analysis
        progress.progress(65, text="🌩️ Menganalisis kejadian hujan lebat...")
        threshold_summary = compute_threshold_summary(
            df=stats_df,
            threshold=params["threshold"],
        )

        # Step 4: Composite image for map
        progress.progress(80, text="🗺️ Membuat komposit spasial untuk peta...")
        mean_image = daily_collection.mean().clip(params["aoi"])

        progress.progress(100, text="✅ Analisis selesai!")
        progress.empty()

        # ── Summary Metrics ──
        st.markdown("### 📈 Ringkasan Statistik")
        summary_stats = {
            "total": stats_df["mean"].sum(),
            "mean": stats_df["mean"].mean(),
            "max": stats_df["max"].max(),
            "p95": stats_df[f"p{params['percentile']}"].quantile(0.95),
            "heavy_days": threshold_summary["heavy_days"],
        }
        render_metrics(summary_stats)

        st.markdown("---")

        # ── Tabs: Charts + Map ──
        tab_ts, tab_bar, tab_heat, tab_map, tab_data = st.tabs([
            "📈 Time Series", "📊 Statistik Spasial", "🔥 Heatmap Threshold",
            "🗺️ Peta", "📋 Data Tabel"
        ])

        with tab_ts:
            st.markdown('<div class="section-title">Curah Hujan Harian / Periodik</div>', unsafe_allow_html=True)
            fig_ts = plot_time_series(stats_df, params["threshold"], params["dataset"])
            st.plotly_chart(fig_ts, use_container_width=True)

        with tab_bar:
            st.markdown('<div class="section-title">Distribusi Statistik Spasial</div>', unsafe_allow_html=True)
            fig_bar = plot_statistics_bar(stats_df, params["percentile"])
            st.plotly_chart(fig_bar, use_container_width=True)

            col_a, col_b = st.columns(2)
            with col_a:
                fig_monthly = plot_monthly_summary(stats_df)
                st.plotly_chart(fig_monthly, use_container_width=True)
            with col_b:
                # Threshold pie
                total = len(stats_df)
                heavy = threshold_summary["heavy_days"]
                fig_pie = go.Figure(go.Pie(
                    labels=["Normal", f"Lebat (>{params['threshold']}mm)", "Ekstrem (>100mm)"],
                    values=[total - heavy, heavy - threshold_summary.get("extreme_days", 0),
                            threshold_summary.get("extreme_days", 0)],
                    hole=0.45,
                    marker_colors=["#0077b6", "#f3722c", "#f94144"],
                    textfont=dict(color="#e6edf3"),
                ))
                fig_pie.update_layout(
                    title="Klasifikasi Intensitas Hujan",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e6edf3", family="Space Grotesk"),
                    legend=dict(font=dict(color="#e6edf3")),
                )
                st.plotly_chart(fig_pie, use_container_width=True)

        with tab_heat:
            st.markdown('<div class="section-title">Heatmap Kejadian Hujan per Bulan</div>', unsafe_allow_html=True)
            fig_heat = plot_threshold_heatmap(stats_df, params["threshold"])
            st.plotly_chart(fig_heat, use_container_width=True)

        with tab_map:
            render_map(params, mean_image, params["aoi"])

        with tab_data:
            st.markdown('<div class="section-title">Data Statistik Harian</div>', unsafe_allow_html=True)
            display_df = stats_df.round(3)
            st.dataframe(display_df, use_container_width=True, height=400)
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download CSV",
                data=csv,
                file_name=f"rainfall_{params['dataset']}_{params['start_date']}_{params['end_date']}.csv",
                mime="text/csv",
            )

    except Exception as e:
        progress.empty()
        st.error(f"❌ Analisis gagal: {str(e)}")
        with st.expander("🐛 Detail Error"):
            import traceback
            st.code(traceback.format_exc(), language="python")


if __name__ == "__main__":
    main()
