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
import geemap
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
            ["Bounding Box Manual", "Unggah GeoJSON", "Unggah Shapefile (.zip)", "Provinsi Indonesia"],
            horizontal=False,
        )

        aoi_geometry = None
        aoi_local = None

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
                aoi_local = {"type": "Polygon", "coordinates": [[[lon_min, lat_min], [lon_max, lat_min], [lon_max, lat_max], [lon_min, lat_max], [lon_min, lat_min]]]}

        elif aoi_method == "Unggah GeoJSON":
            uploaded = st.file_uploader("Upload file .geojson", type=["geojson", "json"])
            if uploaded:
                try:
                    geojson_data = json.load(uploaded)
                    aoi_geometry = ee.Geometry(geojson_data["features"][0]["geometry"])
                    aoi_local = geojson_data["features"][0]["geometry"]
                    st.success("✅ GeoJSON berhasil dimuat")
                except Exception as e:
                    st.error(f"❌ Gagal membaca GeoJSON: {e}")

        elif aoi_method == "Unggah Shapefile (.zip)":
            uploaded = st.file_uploader("Upload Shapefile (.zip berisi .shp, .shx, .dbf, .prj)", type=["zip"])
            if uploaded:
                try:
                    import geopandas as gpd
                    import tempfile
                    
                    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
                        tmp.write(uploaded.read())
                        tmp_path = tmp.name
                    
                    gdf = gpd.read_file(tmp_path)
                    
                    if gdf.crs is not None and gdf.crs.to_string() != "EPSG:4326":
                        gdf = gdf.to_crs(epsg=4326)
                        
                    geom_json = gdf.geometry.iloc[0].__geo_interface__
                    aoi_geometry = ee.Geometry(geom_json)
                    aoi_local = geom_json
                    st.success("✅ Shapefile berhasil dimuat")
                    
                    os.unlink(tmp_path)
                except Exception as e:
                    st.error(f"❌ Gagal membaca Shapefile: {e}")

        elif aoi_method == "Provinsi Indonesia":
            from config.settings import INDONESIA_PROVINCES
            prov = st.selectbox("Pilih Provinsi", list(INDONESIA_PROVINCES.keys()))
            coords = INDONESIA_PROVINCES[prov]
            aoi_geometry = ee.Geometry.Rectangle(coords)
            aoi_local = {"type": "Polygon", "coordinates": [[[coords[0], coords[1]], [coords[2], coords[1]], [coords[2], coords[3]], [coords[0], coords[3]], [coords[0], coords[1]]]]}

        st.markdown('<div class="section-title" style="margin-top:16px;">Parameter Analisis</div>', unsafe_allow_html=True)

        # Dynamic options based on dataset
        if dataset == "GPM_IMERG":
            agg_options = ["Half Hourly", "Harian", "Mingguan", "Bulanan"]
        elif dataset == "GSMaP":
            agg_options = ["Hourly", "Harian", "Mingguan", "Bulanan"]
        else: # CHIRPS
            agg_options = ["Harian", "Mingguan", "Bulanan"]

        aggregation = st.selectbox(
            "Agregasi Temporal",
            options=agg_options,
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
            "aoi_local": aoi_local,
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
    st.markdown('<div class="section-title">🗺️ Peta Spasial (Rata-rata Curah Hujan Harian)</div>', unsafe_allow_html=True)

    import folium

    cfg = get_dataset_config(params["dataset"])
    
    # Helper function to extract bounds from GeoJSON coordinates locally
    def get_geojson_bounds(geojson_geom):
        flat_coords = []
        def traverse(lst):
            if isinstance(lst[0], (int, float)):
                flat_coords.append(lst)
            else:
                for sub in lst:
                    traverse(sub)
        
        if "coordinates" in geojson_geom:
            traverse(geojson_geom["coordinates"])
        elif "geometry" in geojson_geom:
            traverse(geojson_geom["geometry"]["coordinates"])
            
        if not flat_coords:
            return None
        lons = [c[0] for c in flat_coords]
        lats = [c[1] for c in flat_coords]
        return [[min(lats), min(lons)], [max(lats), max(lons)]]

    # Calculate center and bounds before initializing the map
    center = [-2.5, 118]
    zoom = 5
    bounds = None
    try:
        aoi_geojson = params.get("aoi_local")
        if aoi_geojson:
            bounds = get_geojson_bounds(aoi_geojson)
            if bounds:
                center = [(bounds[0][0] + bounds[1][0]) / 2, (bounds[0][1] + bounds[1][1]) / 2]
                zoom = 8
    except Exception as e:
        pass

    # Initialize folium map with dynamic center
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        control_scale=True,
        tiles=None
    )

    # Add OpenStreetMap Basemap
    folium.TileLayer(
        tiles="openstreetmap",
        name="OpenStreetMap",
        overlay=False,
        control=True
    ).add_to(m)

    # Add Google Satellite Basemap (Hybrid with labels)
    folium.TileLayer(
        tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
        attr="Google",
        name="Google Satellite",
        overlay=False,
        control=True
    ).add_to(m)

    # BMKG Palette
    BMKG_PALETTE = [
        '#3D0909', # 0 : < 10 mm/hari
        '#8B251E', # 1 : 10–20
        '#D95F02', # 2 : 20–50
        '#E6AB02', # 3 : 50–75
        '#FFF200', # 4 : 75–100
        '#D2F53C', # 5 : 100–150
        '#89DB89', # 6 : 150–200
        '#34A834', # 7 : 200–250
        '#005A00'  # 8 : >= 250
    ]

    # Add GEE Rainfall Layer
    vis_params = {
        "min": 0,
        "max": 250,
        "palette": BMKG_PALETTE,
    }

    try:
        map_id_dict = ee.Image(image).getMapId(vis_params)
        folium.raster_layers.TileLayer(
            tiles=map_id_dict['tile_fetcher'].url_format,
            attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
            name=f"Curah Hujan - {cfg['label']}",
            overlay=True,
            control=True
        ).add_to(m)
    except Exception as e:
        st.error(f"⚠️ Gagal memuat layer GEE pada peta: {e}")

    # Add AOI Layer and Zoom / Fit Bounds
    try:
        if bounds and aoi_geojson:
            folium.GeoJson(
                aoi_geojson,
                name="Area of Interest (AOI)",
                style_function=lambda x: {
                    "color": "#00b4d8",
                    "fillColor": "none",
                    "weight": 2.5
                }
            ).add_to(m)
            m.fit_bounds(bounds)
    except Exception as e:
        pass

    # Add Layer Control
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    # Add Floating HTML Legend matching BMKG_PALETTE
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 160px; height: 250px; 
        background-color: #161b22; 
        border: 2px solid #21262d; 
        border-radius: 8px;
        z-index:9999; 
        font-size:11px; 
        font-family: 'Space Grotesk', sans-serif;
        color: #e6edf3;
        padding: 12px;
        opacity: 0.9;
    ">
    <b style="color: #00b4d8; font-size:12px;">Legenda Curah Hujan</b><br>
    <span style="font-size: 10px; color: #8b949e; margin-bottom: 8px; display:inline-block;">Rata-rata (mm/hari)</span><br>
    <div style="line-height: 1.8;">
        <i style="background:#3D0909; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> &lt; 10<br>
        <i style="background:#8B251E; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 10 – 20<br>
        <i style="background:#D95F02; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 20 – 50<br>
        <i style="background:#E6AB02; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 50 – 75<br>
        <i style="background:#FFF200; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 75 – 100<br>
        <i style="background:#D2F53C; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 100 – 150<br>
        <i style="background:#89DB89; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 150 – 200<br>
        <i style="background:#34A834; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> 200 – 250<br>
        <i style="background:#005A00; width:15px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:1px;"></i> &ge; 250
    </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # Add JavaScript to fix hidden tab rendering and bounds zooming by polling visibility
    if bounds:
        fit_bounds_js = f"""
        <script>
        (function() {{
            var check_count = 0;
            var check_interval = setInterval(function() {{
                var maps = document.getElementsByClassName('folium-map');
                for (var i = 0; i < maps.length; i++) {{
                    var map_id = maps[i].id;
                    var map_obj = window[map_id];
                    if (map_obj && maps[i].offsetHeight > 100) {{
                        map_obj.invalidateSize();
                        map_obj.fitBounds({bounds});
                        clearInterval(check_interval);
                        return;
                    }}
                }}
                check_count++;
                if (check_count > 60) {{
                    clearInterval(check_interval);
                }}
            }}, 500);
        }})();
        </script>
        """
        m.get_root().html.add_child(folium.Element(fit_bounds_js))

    # Render map (Render raw HTML content directly to avoid double nesting iframe scrollbars)
    st.iframe(m.get_root().render(), height=550)


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

        # Step 4: Composite image for map (selalu rata-rata curah hujan harian)
        progress.progress(80, text="🗺️ Membuat komposit spasial untuk peta...")
        daily_collection_for_map = aggregate_to_daily(
            dataset_id=cfg["id"],
            band=cfg["band"],
            scale_factor=cfg["scale_factor"],
            start_date=params["start_date"],
            end_date=params["end_date"],
            aoi=params["aoi"],
            aggregation="Harian",
        )
        mean_image = daily_collection_for_map.mean().clip(params["aoi"])

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
