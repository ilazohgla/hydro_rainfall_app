"""
ee_processing.py
──────────────────────────────────────────────────────────────────────────────
Logika pemrosesan Earth Engine (Python API).

Fungsi utama:
  - aggregate_to_daily()      : Konversi koleksi raw ke agregat harian/mingguan/bulanan
  - build_stats_fc()          : Hitung statistik spasial per periode (Mean, Min, Max, Pxx)
  - compute_threshold_summary(): Ringkasan kejadian hujan berdasarkan threshold
  - get_dataset_config()      : Konfigurasi tiap dataset (GPM, CHIRPS, GSMaP)

Ini adalah konversi langsung dari script GEE JavaScript ke Python Earth Engine API.
──────────────────────────────────────────────────────────────────────────────
"""

import ee
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config.settings import DATASET_OPTIONS


# ─── Dataset Configuration ────────────────────────────────────────────────────

def get_dataset_config(dataset_key: str) -> dict:
    """
    Kembalikan konfigurasi lengkap untuk dataset yang dipilih.
    Nilai dikompilasi dari DATASET_OPTIONS di config/settings.py.
    """
    cfg = DATASET_OPTIONS[dataset_key].copy()
    cfg["key"] = dataset_key
    return cfg


# ─── Daily Aggregation ────────────────────────────────────────────────────────

def aggregate_to_daily(
    dataset_id: str,
    band: str,
    scale_factor: float,
    start_date: str,
    end_date: str,
    aoi: ee.Geometry,
    aggregation: str = "Harian",
) -> ee.ImageCollection:
    """
    Konversi koleksi citra sub-daily (misal: 30 menit GPM) ke agregat
    harian, mingguan, atau bulanan.

    JavaScript equivalent:
    ──────────────────────
    function aggregateToDaily(collection, startDate, endDate) {
      var dayList = ee.List.sequence(0, endDate.difference(startDate, 'day').subtract(1));
      return ee.ImageCollection(dayList.map(function(n) {
        var d = startDate.advance(n, 'day');
        var dailySum = collection
          .filterDate(d, d.advance(1, 'day'))
          .select(band)
          .sum()
          .multiply(scaleToMM);
        return dailySum.set('system:time_start', d.millis());
      }));
    }

    Parameters
    ----------
    dataset_id   : GEE collection ID (e.g. "NASA/GPM_L3/IMERG_V07")
    band         : Nama band curah hujan
    scale_factor : Faktor konversi ke mm (misal: GPM rate mm/hr × 0.5 untuk 30min)
    start_date   : "YYYY-MM-DD"
    end_date     : "YYYY-MM-DD"
    aoi          : ee.Geometry AOI
    aggregation  : "Harian" | "Mingguan" | "Bulanan"
    """

    # Load raw collection
    raw_collection = (
        ee.ImageCollection(dataset_id)
        .filterDate(start_date, end_date)
        .filterBounds(aoi)
        .select([band], ["precipitation"])
    )

    start = ee.Date(start_date)
    end = ee.Date(end_date)

    if aggregation in ["Half Hourly", "Hourly"]:
        def scale_and_clip(img):
            return img.multiply(scale_factor).clip(aoi).copyProperties(img, ["system:time_start"])
        return raw_collection.map(scale_and_clip)

    if aggregation == "Harian":
        n_periods = end.difference(start, "day").round()
        period_unit = "day"
    elif aggregation == "Mingguan":
        n_periods = end.difference(start, "week").round()
        period_unit = "week"
    else:  # Bulanan
        n_periods = end.difference(start, "month").round()
        period_unit = "month"

    period_list = ee.List.sequence(0, n_periods.subtract(1))

    def aggregate_one_period(n):
        period_start = start.advance(n, period_unit)
        period_end = period_start.advance(1, period_unit)

        # Sum semua citra dalam periode → konversi ke mm
        period_sum = (
            raw_collection
            .filterDate(period_start, period_end)
            .sum()
            .multiply(scale_factor)
            .clip(aoi)
        )

        return period_sum.set({
            "system:time_start": period_start.millis(),
            "system:time_end": period_end.millis(),
            "period_start": period_start.format("YYYY-MM-dd"),
        })

    aggregated = ee.ImageCollection(period_list.map(aggregate_one_period))
    return aggregated


# ─── Spatial Statistics ───────────────────────────────────────────────────────

def build_stats_fc(
    collection: ee.ImageCollection,
    aoi: ee.Geometry,
    scale: int = 5000,
    percentile: int = 95,
) -> pd.DataFrame:
    """
    Hitung statistik spasial untuk setiap image dalam koleksi.
    Mengambil: Mean, Min, Max, StdDev, Persentil Pxx ke dalam DataFrame.

    JavaScript equivalent:
    ──────────────────────
    function buildStatsFC(collection, aoi) {
      return collection.map(function(image) {
        var stats = image.reduceRegion({
          reducer: ee.Reducer.mean()
                     .combine(ee.Reducer.min(), '', true)
                     .combine(ee.Reducer.max(), '', true)
                     .combine(ee.Reducer.stdDev(), '', true)
                     .combine(ee.Reducer.percentile([95]), '', true),
          geometry: aoi,
          scale: 5000,
          maxPixels: 1e13,
          bestEffort: true,
        });
        return ee.Feature(null, stats)
          .set('system:time_start', image.get('system:time_start'))
          .set('date', ee.Date(image.get('system:time_start')).format('YYYY-MM-dd'));
      });
    }

    Returns
    -------
    pd.DataFrame dengan kolom: date, mean, min, max, stddev, p{percentile}
    """

    # Combined reducer: mean + min + max + stdDev + percentile
    combined_reducer = (
        ee.Reducer.mean()
        .combine(ee.Reducer.min(), sharedInputs=True)
        .combine(ee.Reducer.max(), sharedInputs=True)
        .combine(ee.Reducer.stdDev(), sharedInputs=True)
        .combine(ee.Reducer.percentile([percentile]), sharedInputs=True)
    )

    def extract_stats(image):
        stats = image.reduceRegion(
            reducer=combined_reducer,
            geometry=aoi,
            scale=scale,
            maxPixels=1e13,
            bestEffort=True,
        )

        date_str = ee.Date(image.get("system:time_start")).format("YYYY-MM-dd HH:mm:ss")

        return ee.Feature(None, {
            "date": date_str,
            "mean": stats.get("precipitation_mean", stats.get("mean", 0)),
            "min": stats.get("precipitation_min", stats.get("min", 0)),
            "max": stats.get("precipitation_max", stats.get("max", 0)),
            "stddev": stats.get("precipitation_stdDev", stats.get("stdDev", 0)),
            f"p{percentile}": stats.get(
                f"precipitation_p{percentile}", stats.get(f"p{percentile}", 0)
            ),
        })

    stats_fc = collection.map(extract_stats)

    # Convert FeatureCollection → Python dict via getInfo()
    try:
        fc_info = stats_fc.getInfo()
        records = []
        for feature in fc_info["features"]:
            props = feature["properties"]
            records.append(props)

        df = pd.DataFrame(records)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").reset_index(drop=True)

        # Isi NaN dengan 0 (area tanpa hujan)
        numeric_cols = [c for c in df.columns if c != "date"]
        df[numeric_cols] = df[numeric_cols].fillna(0).clip(lower=0)

        return df

    except Exception as e:
        # Fallback: return dummy dataframe untuk development tanpa koneksi GEE
        raise RuntimeError(
            f"Gagal mengambil data dari GEE. Pastikan autentikasi dan AOI sudah benar.\n"
            f"Detail: {str(e)}"
        )


# ─── Threshold / Hydrological Summary ────────────────────────────────────────

def compute_threshold_summary(df: pd.DataFrame, threshold: float = 50.0) -> dict:
    """
    Hitung ringkasan hidrologi berdasarkan thresholding.

    Klasifikasi BMKG (mm/hari):
      < 5   : Tidak hujan
      5–20  : Hujan ringan
      20–50 : Hujan sedang
      50–100: Hujan lebat
      > 100 : Hujan sangat lebat / ekstrem

    JavaScript equivalent:
    ──────────────────────
    var heavyDays = dailyStats.filter(ee.Filter.gte('mean', threshold));
    var extremeDays = dailyStats.filter(ee.Filter.gte('mean', 100));

    Returns
    -------
    dict dengan kunci: heavy_days, extreme_days, dry_days, normal_days,
                       heavy_pct, total_heavy_rain, max_consecutive_heavy
    """

    if df.empty:
        return {"heavy_days": 0, "extreme_days": 0, "dry_days": 0, "normal_days": 0}

    rain_col = "mean"  # Gunakan mean spasial sebagai representasi kawasan

    # Klasifikasi BMKG
    dry = df[df[rain_col] < 5]
    light = df[(df[rain_col] >= 5) & (df[rain_col] < 20)]
    moderate = df[(df[rain_col] >= 20) & (df[rain_col] < 50)]
    heavy = df[(df[rain_col] >= threshold) & (df[rain_col] < 100)]
    extreme = df[df[rain_col] >= 100]

    # Hari hujan lebat berturut-turut (max consecutive heavy days)
    is_heavy = (df[rain_col] >= threshold).astype(int)
    max_consecutive = 0
    current_streak = 0
    for val in is_heavy:
        if val == 1:
            current_streak += 1
            max_consecutive = max(max_consecutive, current_streak)
        else:
            current_streak = 0

    total = len(df)
    heavy_count = len(df[df[rain_col] >= threshold])

    return {
        "heavy_days": heavy_count,
        "extreme_days": len(extreme),
        "heavy_pct": round(heavy_count / total * 100, 1) if total > 0 else 0,
        "dry_days": len(dry),
        "light_days": len(light),
        "moderate_days": len(moderate),
        "normal_days": total - heavy_count,
        "total_heavy_rain": round(df.loc[df[rain_col] >= threshold, rain_col].sum(), 2),
        "max_consecutive_heavy": max_consecutive,
        "total_periods": total,
    }
