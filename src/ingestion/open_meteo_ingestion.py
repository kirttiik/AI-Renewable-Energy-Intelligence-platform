"""
Open-Meteo Future Forecast Ingestion Module -- Quartz-Style NWP Features
======================================================================
Fetches a 14-day future weather forecast for the Khavda Renewable Energy Park
using the free Open-Meteo API. Converts outputs to strictly match the internal
historical weather data schemas (33 features).
"""

import os
import requests
import pandas as pd
import numpy as np
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
KHAVDA_LAT = 23.90
KHAVDA_LON = 69.75

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_DIR = os.path.join(ROOT_DIR, 'data', 'raw')
OUTPUT_PATH = os.path.join(OUTPUT_DIR, 'khavda_weather_forecast.csv')

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

def fetch_future_weather() -> pd.DataFrame:
    """Fetch 14-day future forecast from Open-Meteo."""
    params = {
        "latitude": KHAVDA_LAT,
        "longitude": KHAVDA_LON,
        "hourly": ",".join(HOURLY_VARIABLES),
        "timezone": "Asia/Kolkata",
        "temperature_unit": "celsius",
        "wind_speed_unit": "ms",
        "forecast_days": 14
    }
    
    logger.info("Fetching 14-day forecast from Open-Meteo API...")
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        hourly = data.get('hourly', {})
        if not hourly:
            raise ValueError("No hourly data found in Open-Meteo response.")
            
        df = pd.DataFrame(hourly)
        df["datetime"] = pd.to_datetime(df["time"])
        df = df.drop(columns=["time"])
        
        return df
    except Exception as e:
        logger.error(f"Failed to fetch or process Open-Meteo data: {e}")
        raise

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
    df["latitude"] = KHAVDA_LAT
    df["longitude"] = KHAVDA_LON
    df["data_source"] = "Open-Meteo-Forecast"
    df["load_timestamp"] = datetime.now().isoformat()
    return df.sort_values("date").reset_index(drop=True)

def main():
    logger.info("==================================================")
    logger.info("Starting Open-Meteo Forecast Ingestion")
    logger.info("==================================================")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        df_hourly = fetch_future_weather()
        df_daily = aggregate_to_daily(df_hourly)
        df_final = add_derived_features(df_daily)
        
        df_final.to_csv(OUTPUT_PATH, index=False)
        logger.info(f"Successfully saved {len(df_final)} forecast days to {OUTPUT_PATH}")
        logger.info("==================================================")
        logger.info("Open-Meteo Forecast Ingestion Completed Successfully")
        logger.info("==================================================")
    except Exception as e:
        logger.error("Pipeline Failed.")

if __name__ == "__main__":
    main()
