"""
settings.py
──────────────────────────────────────────────────────────────────────────────
Konfigurasi global aplikasi: dataset GEE, parameter hidrologi, provinsi.
──────────────────────────────────────────────────────────────────────────────
"""

# ─── App Configuration ────────────────────────────────────────────────────────
APP_CONFIG = {
    "name": "Hydro Rainfall Analyzer",
    "version": "1.0.0",
    "author": "Hydrology Analyst",
    "github": "https://github.com/yourusername/hydro-rainfall-analyzer",
}

# ─── Dataset Options ──────────────────────────────────────────────────────────
# Setiap dataset memiliki:
#   id           : GEE ImageCollection asset ID
#   band         : Nama band curah hujan
#   scale_factor : Faktor konversi ke mm
#                  GPM IMERG  : rate dalam mm/hr, resolusi 30 menit → ×0.5 (0.5 jam)
#                  CHIRPS     : sudah dalam mm/hari → ×1
#                  GSMaP      : rate dalam mm/hr, resolusi 1 jam → ×1
#   scale        : Skala reduksi spasial (meter) untuk reduceRegion
#   vis_max      : Nilai maksimum colorbar (mm/hari)
#   spatial_res  : Deskripsi resolusi spasial
#   temporal_res : Deskripsi resolusi temporal
#   coverage     : Cakupan temporal dataset

DATASET_OPTIONS = {
    "GPM_IMERG": {
        "label": "GPM IMERG V07 (NASA)",
        "id": "NASA/GPM_L3/IMERG_V07",
        "band": "precipitation",
        "scale_factor": 0.5,      # mm/hr × 0.5 hr = mm per 30-min
        "scale": 11000,            # ~0.1° dalam meter
        "vis_max": 50,
        "spatial_res": "0.1° (~11 km)",
        "temporal_res": "30 menit",
        "coverage": "2000 – sekarang",
    },
    "CHIRPS": {
        "label": "CHIRPS Daily (UCSB)",
        "id": "UCSB-CHG/CHIRPS/DAILY",
        "band": "precipitation",
        "scale_factor": 1.0,       # sudah mm/hari
        "scale": 5500,             # ~0.05°
        "vis_max": 80,
        "spatial_res": "0.05° (~5.5 km)",
        "temporal_res": "Harian",
        "coverage": "1981 – sekarang",
    },
    "GSMaP": {
        "label": "GSMaP Operational (JAXA)",
        "id": "JAXA/GPM_L3/GSMaP/v6/operational",
        "band": "hourlyPrecipRate",
        "scale_factor": 1.0,       # mm/hr per jam → sum = mm/hari
        "scale": 11000,            # ~0.1°
        "vis_max": 60,
        "spatial_res": "0.1° (~11 km)",
        "temporal_res": "1 jam",
        "coverage": "2014 – sekarang",
    },
}

# ─── Threshold Slider Options ─────────────────────────────────────────────────
# Berdasarkan klasifikasi BMKG
THRESHOLD_OPTIONS = [5, 10, 20, 30, 50, 75, 100, 150, 200]

# ─── Provinsi Indonesia (Approximate Bounding Boxes) ─────────────────────────
# Format: [lon_min, lat_min, lon_max, lat_max]
INDONESIA_PROVINCES = {
    "Aceh":                     [94.97, 1.68, 98.49, 5.90],
    "Sumatera Utara":           [97.55, 1.07, 100.09, 4.73],
    "Sumatera Barat":           [98.35, -3.36, 101.47, 1.10],
    "Riau":                     [100.03, -0.37, 104.34, 2.73],
    "Jambi":                    [101.31, -2.93, 104.84, 0.43],
    "Sumatera Selatan":         [102.09, -5.85, 106.87, -1.00],
    "Bengkulu":                 [101.42, -5.52, 103.80, -2.17],
    "Lampung":                  [103.83, -6.09, 106.10, -3.78],
    "Bangka Belitung":          [105.11, -3.59, 108.28, -1.04],
    "Kepulauan Riau":           [103.24, 0.42, 108.87, 4.07],
    "DKI Jakarta":              [106.65, -6.37, 107.00, -6.07],
    "Jawa Barat":               [106.35, -7.82, 108.79, -5.89],
    "Jawa Tengah":              [108.46, -8.21, 111.65, -5.94],
    "DI Yogyakarta":            [109.91, -8.21, 110.81, -7.56],
    "Jawa Timur":               [110.77, -8.93, 114.58, -5.97],
    "Banten":                   [105.26, -7.07, 106.63, -5.79],
    "Bali":                     [114.47, -8.84, 115.72, -8.05],
    "Nusa Tenggara Barat":      [115.73, -9.21, 117.08, -7.89],
    "Nusa Tenggara Timur":      [117.49, -11.00, 125.22, -7.99],
    "Kalimantan Barat":         [108.00, -3.03, 117.99, 2.09],
    "Kalimantan Tengah":        [108.64, -4.77, 116.82, 1.71],
    "Kalimantan Selatan":       [114.35, -4.77, 117.04, -1.24],
    "Kalimantan Timur":         [113.39, -2.86, 119.34, 3.15],
    "Kalimantan Utara":         [114.73, 0.94, 118.35, 4.41],
    "Sulawesi Utara":           [123.35, 0.40, 125.49, 4.02],
    "Sulawesi Tengah":          [119.42, -4.49, 124.62, 1.74],
    "Sulawesi Selatan":         [119.24, -5.72, 121.00, -1.99],
    "Sulawesi Tenggara":        [120.58, -5.73, 124.41, -2.26],
    "Gorontalo":                [121.28, 0.35, 123.37, 1.09],
    "Sulawesi Barat":           [118.77, -3.77, 119.90, -0.85],
    "Maluku":                   [124.34, -8.56, 135.65, -2.26],
    "Maluku Utara":             [124.20, -2.19, 129.44, 2.43],
    "Papua Barat":              [129.39, -4.60, 134.82, 0.70],
    "Papua":                    [134.32, -9.27, 141.02, -1.12],
}
