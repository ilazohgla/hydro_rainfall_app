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
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

        /* ════════════════════════════════════════════════════════════════
           AURORA HYDRO — Futuristic Glassmorphism Theme
           ════════════════════════════════════════════════════════════════ */
        :root {
            --bg-deep: #04060d;
            --glass: rgba(255, 255, 255, 0.035);
            --border: rgba(148, 163, 255, 0.14);
            --border-strong: rgba(0, 229, 255, 0.45);
            --cyan: #00e5ff;
            --blue: #38bdf8;
            --violet: #8b5cf6;
            --pink: #f472b6;
            --amber: #fbbf24;
            --orange: #fb923c;
            --rose: #f43f5e;
            --text: #e8f1ff;
            --muted: #8fa3bf;
            --mono: 'JetBrains Mono', monospace;
            --display: 'Orbitron', sans-serif;
            --sans: 'Space Grotesk', sans-serif;
        }

        html, body, [class*="css"], [class*="st-"] {
            font-family: var(--sans);
        }

        h1, h2, h3 {
            font-family: var(--display);
            letter-spacing: 0.01em;
        }

        /* ── Deep space base ── */
        .stApp {
            background:
                radial-gradient(1100px 700px at 85% -10%, rgba(30, 58, 138, 0.35) 0%, transparent 60%),
                radial-gradient(900px 650px at -10% 110%, rgba(88, 28, 135, 0.28) 0%, transparent 55%),
                linear-gradient(180deg, #04060d 0%, #070c1a 50%, #04060d 100%);
            color: var(--text);
        }

        /* ── Animated aurora blobs ── */
        .stApp::before {
            content: '';
            position: fixed;
            inset: -30%;
            z-index: 0;
            pointer-events: none;
            background:
                radial-gradient(38% 32% at 28% 26%, rgba(0, 180, 255, 0.20) 0%, transparent 70%),
                radial-gradient(30% 28% at 72% 64%, rgba(124, 58, 237, 0.16) 0%, transparent 70%),
                radial-gradient(26% 24% at 55% 12%, rgba(0, 229, 255, 0.12) 0%, transparent 70%);
            filter: blur(70px);
            animation: auroraDrift 26s ease-in-out infinite alternate;
        }

        /* ── Tech grid overlay ── */
        .stApp::after {
            content: '';
            position: fixed;
            inset: 0;
            z-index: 0;
            pointer-events: none;
            background-image:
                linear-gradient(rgba(148, 163, 255, 0.05) 1px, transparent 1px),
                linear-gradient(90deg, rgba(148, 163, 255, 0.05) 1px, transparent 1px);
            background-size: 44px 44px;
            -webkit-mask-image: radial-gradient(ellipse 90% 70% at 50% 20%, #000 20%, transparent 80%);
            mask-image: radial-gradient(ellipse 90% 70% at 50% 20%, #000 20%, transparent 80%);
        }

        @keyframes auroraDrift {
            0%   { transform: translate3d(-4%, -3%, 0) scale(1) rotate(0deg); }
            50%  { transform: translate3d(3%, 4%, 0) scale(1.12) rotate(6deg); }
            100% { transform: translate3d(-2%, 2%, 0) scale(1.05) rotate(-4deg); }
        }

        /* Content above aurora layers */
        .main .block-container {
            position: relative;
            z-index: 1;
            padding-top: 1.6rem;
            padding-bottom: 3.5rem;
            max-width: 1440px;
        }
        [data-testid="stSidebar"] { position: relative; z-index: 2; }

        /* ════════════════════════════════════════════════════════════════
           HERO HEADER
           ════════════════════════════════════════════════════════════════ */
        .hero-header {
            position: relative;
            background: linear-gradient(135deg, rgba(17, 26, 54, 0.85) 0%, rgba(10, 16, 32, 0.65) 55%, rgba(23, 13, 46, 0.75) 100%);
            border: 1px solid var(--border);
            border-radius: 26px;
            padding: 2.4rem 2.6rem 2rem;
            margin-bottom: 1.8rem;
            overflow: hidden;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            box-shadow: 0 20px 60px rgba(2, 6, 18, 0.6), inset 0 1px 0 rgba(255, 255, 255, 0.06);
        }

        .hero-header::before {
            content: '';
            position: absolute;
            top: 0; left: 8%; right: 8%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.9), rgba(139, 92, 246, 0.9), transparent);
        }

        .hero-header::after {
            content: '';
            position: absolute;
            top: -60%; bottom: -60%;
            left: -35%;
            width: 26%;
            background: linear-gradient(105deg, transparent 0%, rgba(255, 255, 255, 0.10) 45%, rgba(255, 255, 255, 0.22) 50%, rgba(255, 255, 255, 0.10) 55%, transparent 100%);
            transform: skewX(-18deg);
            animation: heroShine 7s ease-in-out infinite;
            pointer-events: none;
        }

        @keyframes heroShine {
            0%, 55% { left: -35%; }
            85%, 100% { left: 130%; }
        }

        .hero-kicker {
            font-family: var(--mono);
            font-size: 0.72rem;
            font-weight: 500;
            letter-spacing: 0.32em;
            text-transform: uppercase;
            color: var(--cyan);
            text-shadow: 0 0 18px rgba(0, 229, 255, 0.55);
            margin-bottom: 0.7rem;
        }

        .hero-title {
            font-family: var(--display);
            font-size: 2.5rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            margin: 0;
            color: var(--text);
            text-shadow: 0 0 40px rgba(0, 180, 255, 0.25);
        }

        .hero-title .grad {
            background: linear-gradient(92deg, #00e5ff 0%, #38bdf8 35%, #8b5cf6 80%, #f472b6 110%);
            background-size: 200% 100%;
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            color: transparent;
            animation: gradShift 6s ease-in-out infinite alternate;
        }

        @keyframes gradShift {
            0%   { background-position: 0% 50%; }
            100% { background-position: 100% 50%; }
        }

        .hero-sub {
            color: var(--muted);
            font-size: 0.95rem;
            font-weight: 400;
            margin-top: 0.55rem;
            letter-spacing: 0.04em;
        }

        .hero-badges {
            margin-top: 1.1rem;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }

        .tech-badge {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 5px 14px;
            font-family: var(--mono);
            font-size: 0.68rem;
            font-weight: 500;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            color: #c7d6f2;
            transition: all 0.25s ease;
        }

        .tech-badge:hover {
            border-color: var(--border-strong);
            color: var(--cyan);
            box-shadow: 0 0 16px rgba(0, 229, 255, 0.25);
            transform: translateY(-2px);
        }

        .tech-badge .dot {
            width: 6px; height: 6px;
            border-radius: 50%;
            background: var(--cyan);
            box-shadow: 0 0 8px var(--cyan);
            animation: pulseDot 2.2s ease-in-out infinite;
        }

        @keyframes pulseDot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50%      { opacity: 0.45; transform: scale(0.8); }
        }

        /* ════════════════════════════════════════════════════════════════
           METRIC CARDS
           ════════════════════════════════════════════════════════════════ */
        .metric-card {
            position: relative;
            background: linear-gradient(160deg, rgba(255, 255, 255, 0.055) 0%, rgba(255, 255, 255, 0.015) 100%);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 1.35rem 1.1rem 1.15rem;
            text-align: center;
            overflow: hidden;
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.25, 1), border-color 0.3s, box-shadow 0.3s;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0; left: 20%; right: 20%;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(0, 229, 255, 0.7), transparent);
            opacity: 0.6;
        }

        .metric-card:hover {
            transform: translateY(-5px);
            border-color: var(--border-strong);
            box-shadow: 0 12px 40px rgba(0, 180, 255, 0.16), 0 0 24px rgba(0, 229, 255, 0.08);
        }

        .metric-icon { font-size: 1.25rem; margin-bottom: 2px; filter: drop-shadow(0 0 8px rgba(0, 229, 255, 0.5)); }

        .metric-value {
            font-family: var(--display);
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            background: linear-gradient(180deg, #ffffff 0%, #9be8ff 60%, #38bdf8 100%);
            -webkit-background-clip: text;
            background-clip: text;
            -webkit-text-fill-color: transparent;
            color: transparent;
            filter: drop-shadow(0 0 14px rgba(0, 229, 255, 0.35));
        }

        .metric-unit {
            font-size: 0.8rem;
            color: var(--cyan);
            font-family: var(--mono);
            margin-top: -2px;
        }

        .metric-label {
            font-size: 0.72rem;
            font-weight: 600;
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: 0.09em;
            margin-top: 6px;
        }

        /* ════════════════════════════════════════════════════════════════
           SECTION TITLES
           ════════════════════════════════════════════════════════════════ */
        .section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: var(--mono);
            font-size: 0.68rem;
            font-weight: 600;
            color: #7e93b8;
            text-transform: uppercase;
            letter-spacing: 0.18em;
            margin: 0 0 12px 0;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }

        .section-title::before {
            content: '';
            width: 6px; height: 6px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--cyan), var(--violet));
            box-shadow: 0 0 10px var(--cyan);
        }

        /* ════════════════════════════════════════════════════════════════
           SIDEBAR
           ════════════════════════════════════════════════════════════════ */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(10, 16, 32, 0.92) 0%, rgba(6, 9, 18, 0.96) 100%);
            backdrop-filter: blur(24px);
            -webkit-backdrop-filter: blur(24px);
            border-right: 1px solid var(--border);
        }

        [data-testid="stSidebar"] hr { border-color: var(--border); }

        .sidebar-footer {
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 12px 14px;
            font-size: 0.76rem;
            line-height: 1.8;
            color: var(--muted);
        }

        .sidebar-footer a { color: var(--cyan); text-decoration: none; }
        .sidebar-footer a:hover { text-shadow: 0 0 12px rgba(0, 229, 255, 0.6); }
        .footer-title { font-family: var(--mono); font-weight: 600; color: #c7d6f2; letter-spacing: 0.06em; }
        .footer-meta { font-size: 0.68rem; margin-bottom: 6px; color: #7e93b8; }

        /* ════════════════════════════════════════════════════════════════
           PANELS & ALERTS
           ════════════════════════════════════════════════════════════════ */
        .info-panel {
            position: relative;
            background: linear-gradient(135deg, rgba(0, 229, 255, 0.07) 0%, rgba(139, 92, 246, 0.05) 100%);
            border: 1px solid var(--border);
            border-left: 3px solid var(--cyan);
            border-radius: 16px;
            padding: 1rem 1.3rem;
            font-size: 0.88rem;
            color: #c9d6ef;
            margin: 0.8rem 0;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
            box-shadow: 0 8px 30px rgba(0, 180, 255, 0.08);
        }

        [data-testid="stAlert"] {
            border-radius: 16px;
            border: 1px solid var(--border);
            background: rgba(13, 20, 38, 0.6);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
        }

        .status-success { color: #34d399; }
        .status-warning { color: var(--amber); }
        .status-error   { color: var(--rose); }

        /* ════════════════════════════════════════════════════════════════
           BUTTONS
           ════════════════════════════════════════════════════════════════ */
        .stButton > button {
            position: relative;
            overflow: hidden;
            background: linear-gradient(120deg, #00e5ff 0%, #2f7cf6 55%, #8b5cf6 100%);
            color: #04060d;
            font-weight: 700;
            font-family: var(--sans);
            letter-spacing: 0.05em;
            border: none;
            border-radius: 14px;
            padding: 0.6rem 1.6rem;
            width: 100%;
            box-shadow: 0 4px 22px rgba(0, 180, 255, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.25);
            transition: transform 0.25s cubic-bezier(0.2, 0.8, 0.3, 1), box-shadow 0.25s;
        }

        .stButton > button::after {
            content: '';
            position: absolute;
            top: -60%; bottom: -60%; left: -45%;
            width: 30%;
            background: linear-gradient(105deg, transparent, rgba(255, 255, 255, 0.45), transparent);
            transform: skewX(-20deg);
            animation: btnShine 4.5s ease-in-out infinite;
        }

        @keyframes btnShine {
            0%, 60% { left: -45%; }
            100%    { left: 135%; }
        }

        .stButton > button:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 34px rgba(0, 180, 255, 0.5), 0 0 28px rgba(139, 92, 246, 0.3);
        }

        .stButton > button:active { transform: translateY(0) scale(0.98); }

        .stDownloadButton > button,
        [data-testid="stBaseButton-secondary"] {
            background: var(--glass);
            border: 1px solid var(--border);
            color: var(--cyan);
            border-radius: 12px;
            font-weight: 600;
            transition: all 0.25s;
        }

        .stDownloadButton > button:hover {
            border-color: var(--border-strong);
            color: var(--cyan);
            box-shadow: 0 0 18px rgba(0, 229, 255, 0.2);
            transform: translateY(-2px);
        }

        /* ════════════════════════════════════════════════════════════════
           INPUTS & WIDGETS
           ════════════════════════════════════════════════════════════════ */
        .stSelectbox > div > div,
        .stDateInput > div > div,
        .stTextInput > div > div,
        .stNumberInput > div > div,
        .stTextArea > div > div {
            background: rgba(255, 255, 255, 0.03) !important;
            border: 1px solid var(--border) !important;
            border-radius: 12px !important;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        .stSelectbox > div > div:hover,
        .stDateInput > div > div:hover,
        .stTextInput > div > div:hover,
        .stNumberInput > div > div:hover {
            border-color: rgba(148, 163, 255, 0.3) !important;
        }

        .stSelectbox > div > div:focus-within,
        .stDateInput > div > div:focus-within,
        .stTextInput > div > div:focus-within,
        .stNumberInput > div > div:focus-within {
            border-color: var(--border-strong) !important;
            box-shadow: 0 0 0 3px rgba(0, 229, 255, 0.12), 0 0 18px rgba(0, 229, 255, 0.15) !important;
        }

        .stSelectbox [data-baseweb="select"] > div { background: transparent !important; border: none !important; }
        .stSelectbox [data-baseweb="popover"] [role="listbox"] { background: #0d1730; border: 1px solid var(--border); border-radius: 12px; }
        .stSelectbox [data-baseweb="popover"] [role="option"]:hover { background: rgba(0, 229, 255, 0.08); }

        /* Radio pills */
        [data-testid="stRadio"] div[role="radiogroup"] > label {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid transparent;
            border-radius: 12px;
            padding: 8px 14px;
            margin-bottom: 6px;
            transition: all 0.2s;
        }

        [data-testid="stRadio"] div[role="radiogroup"] > label:hover {
            border-color: var(--border);
            background: rgba(255, 255, 255, 0.05);
        }

        [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
            border-color: var(--border-strong);
            background: linear-gradient(120deg, rgba(0, 229, 255, 0.10), rgba(139, 92, 246, 0.08));
            box-shadow: 0 0 14px rgba(0, 229, 255, 0.12);
        }

        /* Sliders */
        [data-testid="stSlider"] [data-baseweb="slider"] > div > div {
            background: linear-gradient(90deg, #00e5ff, #8b5cf6) !important;
        }

        [data-testid="stSlider"] [role="slider"] {
            background: #e8f1ff !important;
            border: 2px solid #00e5ff !important;
            box-shadow: 0 0 12px rgba(0, 229, 255, 0.8) !important;
        }

        /* Expander */
        div[data-testid="stExpander"] {
            background: var(--glass);
            border: 1px solid var(--border);
            border-radius: 16px;
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            overflow: hidden;
            transition: border-color 0.25s;
        }

        div[data-testid="stExpander"]:hover { border-color: rgba(148, 163, 255, 0.28); }
        div[data-testid="stExpander"] summary { border-radius: 16px; }

        /* Tabs — pill style */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 6px;
            width: fit-content;
        }

        .stTabs [data-baseweb="tab"] {
            background: transparent;
            color: var(--muted);
            border-radius: 12px;
            padding: 8px 18px;
            font-weight: 600;
            letter-spacing: 0.02em;
            border: 1px solid transparent;
            transition: all 0.25s;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: var(--text);
            background: rgba(255, 255, 255, 0.04);
        }

        .stTabs [aria-selected="true"] {
            color: #04060d !important;
            background: linear-gradient(120deg, #00e5ff, #8b5cf6) !important;
            box-shadow: 0 0 18px rgba(0, 229, 255, 0.35) !important;
        }

        /* Progress */
        [data-testid="stProgress"] > div > div { background: rgba(255, 255, 255, 0.06); border-radius: 999px; }
        [data-testid="stProgress"] > div > div > div > div {
            background: linear-gradient(90deg, #00e5ff, #38bdf8, #8b5cf6);
            box-shadow: 0 0 12px rgba(0, 229, 255, 0.5);
        }

        /* File uploader */
        [data-testid="stFileUploader"] section {
            background: rgba(255, 255, 255, 0.02);
            border: 1px dashed rgba(148, 163, 255, 0.35);
            border-radius: 16px;
            transition: border-color 0.2s;
        }

        [data-testid="stFileUploader"] section:hover { border-color: var(--border-strong); }

        /* Dataframe */
        [data-testid="stDataFrame"] {
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            backdrop-filter: blur(10px);
            -webkit-backdrop-filter: blur(10px);
        }

        /* ════════════════════════════════════════════════════════════════
           CHARTS & MISC
           ════════════════════════════════════════════════════════════════ */
        .js-plotly-plot .plotly .main-svg { background: transparent !important; }

        /* Hide Streamlit chrome */
        #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] { visibility: hidden; height: 0; }
        header[data-testid="stHeader"] { background: transparent; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 10px; height: 10px; }
        ::-webkit-scrollbar-track { background: #05080f; }
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #16233f, #1f2f55);
            border-radius: 10px;
            border: 2px solid #05080f;
        }
        ::-webkit-scrollbar-thumb:hover { background: linear-gradient(180deg, #1d2e52, #2b4073); }

        ::selection { background: rgba(0, 229, 255, 0.28); color: #ffffff; }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# ─── Header Component ─────────────────────────────────────────────────────────
def render_header():
    st.markdown("""
    <div class="hero-header">
        <div class="hero-kicker">🌧️ Hydro · Climate Intelligence Platform</div>
        <h1 class="hero-title">Hydro Rainfall <span class="grad">Analyzer</span></h1>
        <div class="hero-sub">Analisis Curah Hujan Spasial · Multi-Dataset · Google Earth Engine</div>
        <div class="hero-badges">
            <span class="tech-badge"><span class="dot"></span>GPM IMERG</span>
            <span class="tech-badge"><span class="dot"></span>CHIRPS</span>
            <span class="tech-badge"><span class="dot"></span>GSMaP</span>
            <span class="tech-badge"><span class="dot"></span>Streamlit Cloud</span>
            <span class="tech-badge"><span class="dot"></span>Earth Engine</span>
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
        <div class="sidebar-footer">
            <div class="footer-title">Hydro Rainfall Analyzer</div>
            <div class="footer-meta">Earth Engine · geemap · Streamlit</div>
            📌 <a href="https://github.com/ilazohgla/hydro_rainfall_app" target="_blank">GitHub Repository</a><br>
            📄 <a href="https://earthengine.google.com" target="_blank">GEE Documentation</a>
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
        ("🌧️", "Total Curah Hujan", stats.get("total", 0), "mm"),
        ("📊", "Rata-rata Harian", stats.get("mean", 0), "mm/hr"),
        ("⬆️", "Maksimum", stats.get("max", 0), "mm/hr"),
        ("📈", "P95", stats.get("p95", 0), "mm/hr"),
        ("⛈️", "Hari Hujan Lebat", stats.get("heavy_days", 0), "hari"),
    ]
    for col, (icon, label, value, unit) in zip(cols, metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-icon">{icon}</div>
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
                    "color": "#00e5ff",
                    "fillColor": "none",
                    "weight": 2.5,
                    "dashArray": "6, 6",
                }
            ).add_to(m)
            m.fit_bounds(bounds)
    except Exception as e:
        pass

    # Add Layer Control
    folium.LayerControl(position="topright", collapsed=False).add_to(m)

    # Add Floating Glass Legend matching BMKG_PALETTE
    legend_html = """
    <div style="
        position: fixed; 
        bottom: 30px; left: 30px; width: 172px; 
        background: rgba(10, 16, 32, 0.78);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(148, 163, 255, 0.25); 
        border-radius: 16px;
        z-index: 9999; 
        font-size: 11px; 
        font-family: 'Space Grotesk', sans-serif;
        color: #e8f1ff;
        padding: 14px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5);
    ">
    <b style="color: #00e5ff; font-size: 12px; letter-spacing: 0.08em;">LEGENDA CURAH HUJAN</b><br>
    <span style="font-size: 10px; color: #8fa3bf; margin-bottom: 8px; display: inline-block;">Rata-rata (mm/hari)</span><br>
    <div style="line-height: 1.8;">
        <i style="background:#3D0909; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> &lt; 10<br>
        <i style="background:#8B251E; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 10 – 20<br>
        <i style="background:#D95F02; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 20 – 50<br>
        <i style="background:#E6AB02; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 50 – 75<br>
        <i style="background:#FFF200; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 75 – 100<br>
        <i style="background:#D2F53C; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 100 – 150<br>
        <i style="background:#89DB89; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 150 – 200<br>
        <i style="background:#34A834; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> 200 – 250<br>
        <i style="background:#005A00; width:16px; height:10px; float:left; margin-top:4px; margin-right:8px; border-radius:3px;"></i> &ge; 250
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
                    marker_colors=["#22d3ee", "#fb923c", "#f43f5e"],
                    textfont=dict(color="#e8f1ff"),
                ))
                fig_pie.update_layout(
                    title="Klasifikasi Intensitas Hujan",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#e8f1ff", family="Space Grotesk"),
                    legend=dict(font=dict(color="#e8f1ff")),
                    hoverlabel=dict(bgcolor="#0d1730", bordercolor="rgba(148,163,255,0.3)"),
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
