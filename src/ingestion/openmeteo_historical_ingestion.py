"""
Open-Meteo Historical Weather Ingestion -- Quartz-Style NWP Features
======================================================================
Fetches HOURLY historical weather data for Khavda, Gujarat from the
Open-Meteo Historical Archive API and aggregates to daily.

Data range: 2020-01-01 to today
Output: data/raw/khavda_weather_openmeteo.csv
"""

import os
import logging
import requests
import pandas as pd
import numpy as np
from datetime import date, datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_openmeteo.csv")

LAT = 23.83
LON = 68.77
START_DATE = "2020-01-01"
END_DATE = date.today().strftime("%Y-%m-%d")
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "wind_speed_10m",
    "visibility",
    "direct_normal_irradiance",
]


def fetch_year(year: int) -> pd.DataFrame:
    start = f"{year}-01-01"
    end_dt = min(date.today(), date(year, 12, 31))
    end = end_dt.strftime("%Y-%m-%d")
    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": start,
        "end_date": end,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Asia/Kolkata",
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
    }
    resp = requests.get(ARCHIVE_URL, params=params, timeout=120)
    resp.raise_for_status()
    hourly = resp.json().get("hourly", {})
    if not hourly:
        raise ValueError(f"No hourly data for {year}")
    df = pd.DataFrame(hourly)
    df["datetime"] = pd.to_datetime(df["time"])
    df = df.drop(columns=["time"])
    return df


def aggregate_to_daily(df_hourly: pd.DataFrame) -> pd.DataFrame:
    df_hourly = df_hourly.copy()
    df_hourly["date"] = df_hourly["datetime"].dt.date

    agg_all = df_hourly.groupby("date").agg(
        temperature_c=("temperature_2m", "mean"),
        temperature_max_c=("temperature_2m", "max"),
        temperature_min_c=("temperature_2m", "min"),
        humidity_pct=("relative_humidity_2m", "mean"),
        rainfall_mm=("precipitation", "sum"),
        wind_speed_ms=("wind_speed_10m", "mean"),
        wind_speed_max_ms=("wind_speed_10m", "max"),
        cloud_cover_pct=("cloud_cover", "mean"),
        cloud_cover_low_pct=("cloud_cover_low", "mean"),
        cloud_cover_mid_pct=("cloud_cover_mid", "mean"),
        cloud_cover_high_pct=("cloud_cover_high", "mean"),
        visibility_km=("visibility", lambda x: x.mean() / 1000.0),
        ghi_kwh_m2_day=("shortwave_radiation", lambda x: x.clip(lower=0).sum() / 1000.0),
        direct_radiation_kwh_m2_day=("direct_radiation", lambda x: x.clip(lower=0).sum() / 1000.0),
        dhi_kwh_m2_day=("diffuse_radiation", lambda x: x.clip(lower=0).sum() / 1000.0),
        dni_kwh_m2_day=("direct_normal_irradiance", lambda x: x.clip(lower=0).sum() / 1000.0),
        dni_peak_w_m2=("direct_normal_irradiance", "max"),
    ).reset_index()

    agg_all["date"] = pd.to_datetime(agg_all["date"])
    return agg_all


def add_derived_features(df: pd.DataFrame) -> pd.DataFrame:
    df["diffuse_fraction"] = np.where(
        df["ghi_kwh_m2_day"] > 0,
        (df["dhi_kwh_m2_day"] / df["ghi_kwh_m2_day"]).clip(0, 1), 0.0
    )
    df["direct_fraction"] = np.where(
        df["ghi_kwh_m2_day"] > 0,
        (df["direct_radiation_kwh_m2_day"] / df["ghi_kwh_m2_day"]).clip(0, 1), 0.0
    )
    df["day_of_year"] = df["date"].dt.dayofyear
    df["et_radiation_kwh_m2"] = 6.5 + 1.0 * np.cos(2 * np.pi * (df["day_of_year"] - 172) / 365)
    df["clearness_index"] = (df["ghi_kwh_m2_day"] / df["et_radiation_kwh_m2"]).clip(0, 1)
    df["month"] = df["date"].dt.month
    df["quarter"] = df["date"].dt.quarter
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)
    df["is_monsoon"] = df["month"].isin([6, 7, 8, 9]).astype(int)
    df["site_name"] = "Khavda Renewable Energy Park"
    df["latitude"] = LAT
    df["longitude"] = LON
    df["data_source"] = "Open-Meteo-Archive"
    df["load_timestamp"] = datetime.now().isoformat()
    return df.sort_values("date").reset_index(drop=True)


def main():
    logger.info("=" * 60)
    logger.info("Open-Meteo Historical Ingestion -- Quartz NWP Features")
    logger.info(f"Target: {START_DATE} to {END_DATE}")
    logger.info("=" * 60)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    all_years = []
    current_year = date.today().year

    for year in range(2020, current_year + 1):
        logger.info(f"Fetching year {year}...")
        try:
            df_year = fetch_year(year)
            logger.info(f"  -> {len(df_year)} hourly rows for {year}")
            all_years.append(df_year)
        except Exception as e:
            logger.error(f"  -> FAILED for {year}: {e}")

    if not all_years:
        raise RuntimeError("No data fetched. Check API connectivity.")

    df_hourly = pd.concat(all_years, ignore_index=True)
    logger.info(f"Total hourly rows: {len(df_hourly)}")

    logger.info("Aggregating to daily...")
    df_daily = aggregate_to_daily(df_hourly)

    logger.info("Adding derived Quartz features...")
    df_final = add_derived_features(df_daily)

    df_final.to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Saved {len(df_final)} daily rows to {OUTPUT_PATH}")
    logger.info(f"Date range: {df_final['date'].min()} to {df_final['date'].max()}")
    logger.info(f"Columns ({len(df_final.columns)}): {list(df_final.columns)}")
    logger.info("=" * 60)
    logger.info("COMPLETE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
