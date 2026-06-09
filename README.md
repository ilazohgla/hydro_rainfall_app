# 🌧️ Hydro Rainfall Analyzer

> **Analisis Curah Hujan Spasial Multi-Dataset berbasis Google Earth Engine**
> Dibangun dengan Python · Streamlit · geemap · Plotly

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app.streamlit.app)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GEE](https://img.shields.io/badge/Google%20Earth%20Engine-4285F4?logo=google&logoColor=white)](https://earthengine.google.com)

---

## 📌 Tentang Proyek

**Hydro Rainfall Analyzer** adalah aplikasi web analisis curah hujan berbasis cloud yang memanfaatkan kekuatan komputasi **Google Earth Engine (GEE)** untuk memproses dataset curah hujan satelit skala regional hingga global. Aplikasi ini dirancang untuk mendukung kebutuhan **analis hidrologi, peneliti iklim, dan insinyur sumber daya air**.

### Fitur Utama

| Fitur | Keterangan |
|-------|-----------|
| 🛰️ **Multi-Dataset** | GPM IMERG, CHIRPS Daily, GSMaP (JAXA) |
| 📅 **Fleksibel Temporal** | Agregasi harian, mingguan, bulanan |
| 🗺️ **Visualisasi Spasial** | Peta interaktif dengan geemap + Folium |
| 📊 **Statistik Spasial** | Mean, Min, Max, StdDev, Persentil (Pxx) |
| 🌩️ **Analisis Threshold** | Klasifikasi hujan BMKG (ringan → ekstrem) |
| 📐 **Input AOI Fleksibel** | Bounding Box, GeoJSON Upload, Provinsi Indonesia |
| 🇮🇩 **Indonesia-Ready** | Semua 34 Provinsi Indonesia tersedia sebagai preset |
| ⬇️ **Export CSV** | Download hasil analisis langsung dari browser |

---

## 🏗️ Arsitektur Aplikasi

```
hydro-rainfall-analyzer/
│
├── app.py                      # Entry point Streamlit
├── requirements.txt            # Dependensi Python
├── .gitignore
│
├── config/
│   ├── __init__.py
│   └── settings.py             # Konfigurasi dataset GEE, provinsi, threshold
│
├── utils/
│   ├── __init__.py
│   ├── ee_auth.py              # Autentikasi Earth Engine (multi-strategy)
│   ├── ee_processing.py        # Logika inti GEE: aggregasi + statistik
│   └── chart_builder.py        # Builder grafik Plotly (dark theme)
│
└── .streamlit/
    ├── config.toml             # Konfigurasi tema Streamlit
    └── secrets.toml.template   # Template autentikasi (JANGAN di-commit)
```

### Alur Data

```
[GEE ImageCollection]
       │
       ▼
aggregate_to_daily()          ← Konversi sub-daily → harian/mingguan/bulanan
       │                         (sum + scale_factor ke mm)
       ▼
build_stats_fc()              ← reduceRegion per periode
       │                         (Mean, Min, Max, StdDev, P95)
       ▼
compute_threshold_summary()   ← Klasifikasi BMKG
       │                         (Normal, Lebat, Ekstrem)
       ▼
[Plotly Charts + geemap]      ← Visualisasi interaktif di Streamlit
```

---

## 🛰️ Dataset yang Didukung

### GPM IMERG V07 (NASA)
- **Asset GEE**: `NASA/GPM_L3/IMERG_V07`
- **Resolusi Spasial**: 0.1° (~11 km)
- **Resolusi Temporal**: 30 menit
- **Cakupan**: 2000 – sekarang
- **Band**: `precipitation` (mm/hr) → dikali 0.5 → mm per 30 menit

### CHIRPS Daily (UCSB)
- **Asset GEE**: `UCSB-CHG/CHIRPS/DAILY`
- **Resolusi Spasial**: 0.05° (~5.5 km)
- **Resolusi Temporal**: Harian
- **Cakupan**: 1981 – sekarang
- **Band**: `precipitation` (mm/hari)

### GSMaP Operational (JAXA)
- **Asset GEE**: `JAXA/GPM_L3/GSMaP/v6/operational`
- **Resolusi Spasial**: 0.1° (~11 km)
- **Resolusi Temporal**: 1 jam
- **Cakupan**: 2014 – sekarang
- **Band**: `hourlyPrecipRate` (mm/hr) → dikali 1 → mm per jam

---

## ⚙️ Instalasi & Menjalankan Secara Lokal

### Prasyarat
- Python 3.10 atau 3.11
- Akun Google Earth Engine ([daftar gratis](https://earthengine.google.com/signup/))
- Git

### Langkah-langkah

```bash
# 1. Clone repositori
git clone https://github.com/ilazohgla/hydro-rainfall-app.git
cd hydro-rainfall-analyzer

# 2. Buat virtual environment
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependensi
pip install -r requirements.txt

# 4. Autentikasi GEE (cukup sekali)
earthengine authenticate

# 5. Jalankan aplikasi
streamlit run app.py
```

Buka browser di `http://localhost:8501`

---

## 🔐 Autentikasi Google Earth Engine

Aplikasi ini menggunakan **strategi autentikasi berlapis** untuk mendukung lingkungan development dan production:

```
┌─────────────────────────────────────────────────────┐
│           Strategi Autentikasi (Prioritas)          │
├─────┬───────────────────────────────────────────────┤
│  1  │ Streamlit Secrets       → Production (Cloud)  │
│  2  │ Environment Variable    → Docker / CI/CD       │
│  3  │ Local credentials file  → Development          │
│  4  │ ~/.config/earthengine/  → Development          │
└─────┴───────────────────────────────────────────────┘
```

### Untuk Development Lokal

```bash
# Jalankan sekali, ikuti instruksi di browser
earthengine authenticate
```

### Untuk Deployment Streamlit Cloud (Service Account)

1. **Buat Service Account** di [Google Cloud Console](https://console.cloud.google.com/iam-admin/serviceaccounts):
   - IAM & Admin → Service Accounts → Create Service Account
   - Role: **Earth Engine Resource Viewer** (minimal)

2. **Generate Private Key**:
   - Service Account → Keys → Add Key → JSON
   - Simpan file `.json` di tempat aman (JANGAN upload ke GitHub!)

3. **Daftarkan Service Account di GEE**:
   ```
   https://code.earthengine.google.com/register
   ```
   Pilih "Use with a Cloud Project" dan daftarkan email service account.

4. **Tambahkan ke Streamlit Secrets**:
   Di Streamlit Cloud Dashboard → App Settings → Secrets:

   ```toml
   GEE_SERVICE_ACCOUNT = "nama-sa@project-id.iam.gserviceaccount.com"
   GEE_PRIVATE_KEY = """
   -----BEGIN RSA PRIVATE KEY-----
   [isi private_key dari file JSON]
   -----END RSA PRIVATE KEY-----
   """
   ```

   > ⚠️ **KEAMANAN**: Private key bersifat rahasia. Streamlit Secrets dienkripsi dan tidak terekspos ke publik atau ke dalam kode Anda.

---

## 📊 Contoh Analisis

### Kasus: Analisis Kejadian Hujan Ekstrem di Jawa Barat (Jan 2024)

```
Dataset  : CHIRPS Daily
Periode  : 2024-01-01 s/d 2024-01-31
AOI      : Provinsi Jawa Barat (preset)
Threshold: 50 mm/hari
Persentil: P95
```

**Hasil**:
- Total curah hujan rata-rata: 312.4 mm
- Rata-rata harian: 10.1 mm/hari
- Hari hujan lebat (≥50 mm): 4 hari
- Kejadian ekstrem (≥100 mm): 1 hari
- P95: 47.3 mm/hari

---

## 🔬 Metodologi

### Konversi Ke Nilai Harian

```python
# GPM IMERG (30 menit, mm/hr) → mm/hari
daily_sum = collection
    .filterDate(day_start, day_end)
    .select("precipitation")
    .sum()
    .multiply(0.5)   # mm/hr × 0.5 hr = mm per step

# CHIRPS (sudah mm/hari) → langsung sum
daily_sum = collection
    .filterDate(day_start, day_end)
    .select("precipitation")
    .sum()
    .multiply(1.0)
```

### Statistik Spasial

```python
# Combined reducer — satu pass, semua statistik
reducer = (ee.Reducer.mean()
    .combine(ee.Reducer.min(), sharedInputs=True)
    .combine(ee.Reducer.max(), sharedInputs=True)
    .combine(ee.Reducer.stdDev(), sharedInputs=True)
    .combine(ee.Reducer.percentile([95]), sharedInputs=True))

stats = image.reduceRegion(
    reducer=reducer,
    geometry=aoi,
    scale=5000,
    maxPixels=1e13,
    bestEffort=True,
)
```

### Klasifikasi Intensitas (BMKG)

| Kelas / Kategori | Range (mm/hari) | Kode Warna |
|------------------|----------------|------------|
| Sangat Ringan / Normal | < 10 | `#3D0909` |
| Ringan | 10 – 20 | `#8B251E` |
| Sedang | 20 – 50 | `#D95F02` |
| Lebat | 50 – 75 | `#E6AB02` |
| Sangat Lebat | 75 – 100 | `#FFF200` |
| Ekstrem (Level I) | 100 – 150 | `#D2F53C` |
| Ekstrem (Level II) | 150 – 200 | `#89DB89` |
| Ekstrem (Level III) | 200 – 250 | `#34A834` |
| Ekstrem (Bencana) | ≥ 250 | `#005A00` |

---

## 🚀 Deploy ke Streamlit Cloud

```bash
# 1. Push ke GitHub (pastikan secrets.toml TIDAK ter-commit)
git add .
git commit -m "Initial release: Hydro Rainfall Analyzer v1.0"
git push origin main

# 2. Buka https://share.streamlit.io
# 3. New App → Connect repo → Set main file: app.py
# 4. Advanced → Secrets → Paste konfigurasi GEE
# 5. Deploy!
```

---

## 🧰 Stack Teknologi

| Komponen | Library | Versi |
|----------|---------|-------|
| Frontend / UI | Streamlit | ≥1.35 |
| GEE Interface | geemap | ≥0.31 |
| GEE Backend | earthengine-api | ≥0.1.390 |
| Peta Interaktif | Folium | ≥0.15 |
| Grafik | Plotly | ≥5.18 |
| Data | Pandas / NumPy | ≥2.1 / ≥1.26 |
| Geospasial | GeoPandas / Shapely | ≥0.14 / ≥2.0 |

---

## 📁 Lisensi

MIT License — bebas digunakan untuk keperluan pendidikan, penelitian, dan portofolio.

---

## 👤 Tentang Penulis

Dibangun sebagai proyek portofolio oleh seorang **Analis Hidrologi** yang berfokus pada:
- Pemodelan curah hujan dan debit sungai
- Analisis data penginderaan jauh (remote sensing)
- Pengembangan tools geospasial berbasis Python

📧 Email: qodri.alghozali@gmail.com
🔗 LinkedIn: [https://www.linkedin.com/in/muhammad-qodri-al-ghozali-a7b11120b/](https://linkedin.com)
🐙 GitHub: [github.com/ilazohgla](https://github.com)

---

*Terima kasih kepada NASA, UCSB-CHG, dan JAXA atas dataset curah hujan yang tersedia secara publik melalui Google Earth Engine.*
