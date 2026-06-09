"""
setup_local.py
──────────────────────────────────────────────────────────────────────────────
Script helper untuk setup awal di lingkungan development lokal.
Jalankan SEKALI setelah clone repositori.

  python setup_local.py

──────────────────────────────────────────────────────────────────────────────
"""

import subprocess
import sys
import os
from pathlib import Path


def run(cmd: str, check=True):
    print(f"\n▶ {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=False)
    if check and result.returncode != 0:
        print(f"❌ Command gagal dengan exit code {result.returncode}")
        sys.exit(1)
    return result


def main():
    print("=" * 60)
    print("  Hydro Rainfall Analyzer — Setup Development Lokal")
    print("=" * 60)

    # 1. Check Python version
    print(f"\n✅ Python {sys.version}")
    if sys.version_info < (3, 10):
        print("❌ Python 3.10+ diperlukan. Download dari https://python.org")
        sys.exit(1)

    # 2. Install dependencies
    print("\n📦 Menginstall dependensi dari requirements.txt...")
    run(f"{sys.executable} -m pip install -r requirements.txt")

    # 3. Autentikasi GEE
    print("\n🔐 Autentikasi Google Earth Engine...")
    print("Browser akan terbuka. Login dengan akun Google yang terdaftar di GEE.")
    run("earthengine authenticate")

    # 4. Buat .streamlit/secrets.toml dari template
    secrets_dir = Path(".streamlit")
    secrets_dir.mkdir(exist_ok=True)
    secrets_file = secrets_dir / "secrets.toml"
    template_file = secrets_dir / "secrets.toml.template"

    if not secrets_file.exists() and template_file.exists():
        import shutil
        shutil.copy(template_file, secrets_file)
        print(f"\n📄 Dibuat: .streamlit/secrets.toml")
        print("   Edit file tersebut dan isi kredensial Service Account GEE Anda.")
    elif secrets_file.exists():
        print(f"\n✅ .streamlit/secrets.toml sudah ada.")

    print("\n" + "=" * 60)
    print("  ✅ Setup selesai!")
    print("  Jalankan aplikasi dengan:")
    print("    streamlit run app.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
