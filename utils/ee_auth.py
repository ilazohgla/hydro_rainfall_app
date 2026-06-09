"""
ee_auth.py
──────────────────────────────────────────────────────────────────────────────
Modul autentikasi Google Earth Engine.

Strategi:
  1. Deployment (Streamlit Cloud) → Service Account via st.secrets
  2. Development lokal             → `earthengine authenticate` (credentials.json)
  3. Fallback                      → Autentikasi interaktif via OAuth2
──────────────────────────────────────────────────────────────────────────────
"""

import ee
import os
import json
import streamlit as st
from pathlib import Path


def initialize_ee() -> tuple[bool, str]:
    """
    Inisialisasi Earth Engine dengan strategi:
      1. Coba Service Account dari Streamlit Secrets (untuk Streamlit Cloud)
      2. Coba credentials lokal (~/.config/earthengine/credentials)
      3. Coba environment variable GEE_SERVICE_ACCOUNT_JSON

    Returns
    -------
    (success: bool, message: str)
    """

    # ── Strategy 1: Streamlit Secrets (Production/Cloud Deploy) ──────────────
    try:
        if hasattr(st, "secrets") and "GEE_SERVICE_ACCOUNT" in st.secrets:
            service_account_email = st.secrets["GEE_SERVICE_ACCOUNT"]
            private_key = st.secrets["GEE_PRIVATE_KEY"]
            project_id = st.secrets.get("GEE_PROJECT_ID", "")

            # Buat credentials dari private key yang di-store di secrets
            credentials = ee.ServiceAccountCredentials(
                email=service_account_email,
                key_data=private_key,
            )
            # Pass project_id secara eksplisit untuk mencegah hanging/timeout
            ee.Initialize(credentials, project=project_id)
            return True, "Berhasil diinisialisasi via Streamlit Secrets (Service Account)"
    except Exception as e:
        print(f"Strategy 1 Failed: {e}")

    # ── Strategy 2: Environment Variable (Docker / CI) ────────────────────────
    try:
        sa_json = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            sa_info = json.loads(sa_json)
            credentials = ee.ServiceAccountCredentials(
                email=sa_info["client_email"],
                key_data=sa_info["private_key"],
            )
            project_id = sa_info.get("project_id", os.environ.get("GEE_PROJECT_ID", ""))
            ee.Initialize(credentials, project=project_id)
            return True, "Berhasil diinisialisasi via Environment Variable"
    except Exception as e:
        print(f"Strategy 2 Failed: {e}")

    # ── Strategy 3: Local credentials (Development) ──────────────────────────
    try:
        # ee.Initialize dengan project dari environment variable
        project_id = os.environ.get("GEE_PROJECT_ID", "")
        if project_id:
            ee.Initialize(project=project_id)
            return True, f"Berhasil diinisialisasi via kredensial lokal dengan project: {project_id}"
    except Exception as e:
        print(f"Strategy 3 Failed: {e}")

    # ── Strategy 4: Credential file path ─────────────────────────────────────
    try:
        cred_file = Path.home() / ".config" / "earthengine" / "credentials"
        if cred_file.exists():
            ee.Initialize()
            return True, "Berhasil diinisialisasi via file credentials"
    except Exception as e:
        return False, str(e)

    return False, (
        "Tidak dapat menginisialisasi Earth Engine. "
        "Untuk deployment, tambahkan GEE_SERVICE_ACCOUNT dan GEE_PRIVATE_KEY "
        "ke Streamlit Secrets. Untuk development lokal, jalankan: "
        "`earthengine authenticate`"
    )
