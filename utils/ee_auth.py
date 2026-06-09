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

            # Buat credentials dari private key yang di-store di secrets
            credentials = ee.ServiceAccountCredentials(
                email=service_account_email,
                key_data=private_key,
            )
            ee.Initialize(credentials)
            return True, "Berhasil diinisialisasi via Streamlit Secrets (Service Account)"
    except Exception as e:
        pass  # Lanjut ke strategy berikutnya

    # ── Strategy 2: Environment Variable (Docker / CI) ────────────────────────
    try:
        sa_json = os.environ.get("GEE_SERVICE_ACCOUNT_JSON")
        if sa_json:
            sa_info = json.loads(sa_json)
            credentials = ee.ServiceAccountCredentials(
                email=sa_info["client_email"],
                key_data=sa_info["private_key"],
            )
            ee.Initialize(credentials)
            return True, "Berhasil diinisialisasi via Environment Variable"
    except Exception as e:
        pass

    # ── Strategy 3: Local credentials (Development) ──────────────────────────
    try:
        # ee.Authenticate() sudah pernah dijalankan sebelumnya
        ee.Initialize(project=os.environ.get("GEE_PROJECT_ID", ""))
        return True, "Berhasil diinisialisasi via kredensial lokal"
    except Exception as e:
        pass

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
