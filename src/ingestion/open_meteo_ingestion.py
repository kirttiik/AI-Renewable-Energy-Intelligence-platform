"""
Open-Meteo Future Forecast Ingestion Module

Fetches a 14-day future weather forecast for the Khavda Renewable Energy Park
using the free Open-Meteo API. Converts outputs to strictly match the internal
historical weather data schemas.
"""

import os
import requests
import pandas as pd
import logging

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

def fetch_future_weather() -> pd.DataFrame:
    """Fetch 14-day future forecast from Open-Meteo."""
    params = {
        "latitude": KHAVDA_LAT,
        "longitude": KHAVDA_LON,
        "daily": [
            "temperature_2m_max",
            "temperature_2m_min",
            "relative_humidity_2m_mean",
            "precipitation_sum",
            "cloud_cover_mean",
            "wind_speed_10m_max",
            "shortwave_radiation_sum"
        ],
        "timezone": "Asia/Kolkata",
        "wind_speed_unit": "ms",
        "forecast_days": 14
    }
    
    logger.info("Fetching 14-day forecast from Open-Meteo API...")
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        daily_data = data.get('daily', {})
        if not daily_data:
            raise ValueError("No daily data found in Open-Meteo response.")
            
        df = pd.DataFrame(daily_data)
        
        # 1. Date conversion
        df['date'] = pd.to_datetime(df['time'])
        
        # 2. Temperature (Average of Max/Min)
        df['temperature_c'] = (df['temperature_2m_max'] + df['temperature_2m_min']) / 2.0
        
        # 3. Direct mappings
        df['humidity_pct'] = df['relative_humidity_2m_mean']
        df['rainfall_mm'] = df['precipitation_sum']
        df['cloud_cover_pct'] = df['cloud_cover_mean']
        df['wind_speed_ms'] = df['wind_speed_10m_max']
        
        # 4. Solar Radiation mathematical conversion (MJ/m² to kWh/m²)
        df['solar_radiation_kwh_m2_day'] = df['shortwave_radiation_sum'] / 3.6
        
        # Filter strictly to required columns
        required_cols = [
            'date', 'temperature_c', 'humidity_pct', 'wind_speed_ms', 
            'solar_radiation_kwh_m2_day', 'rainfall_mm', 'cloud_cover_pct'
        ]
        
        final_df = df[required_cols].copy()
        
        # Handle edge cases (missing future values)
        final_df.fillna(method='ffill', inplace=True)
        final_df.fillna(0, inplace=True)
        
        logger.info(f"Successfully processed {len(final_df)} days of future weather data.")
        return final_df
        
    except Exception as e:
        logger.error(f"Failed to fetch or process Open-Meteo data: {e}")
        raise

def main():
    logger.info("==================================================")
    logger.info("Starting Open-Meteo Forecast Ingestion")
    logger.info("==================================================")
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    try:
        forecast_df = fetch_future_weather()
        forecast_df.to_csv(OUTPUT_PATH, index=False)
        logger.info(f"Saved 14-day forecast to {OUTPUT_PATH}")
        
        logger.info("==================================================")
        logger.info("Open-Meteo Forecast Ingestion Completed Successfully")
        logger.info("==================================================")
    except Exception as e:
        logger.error(f"Open-Meteo Ingestion Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
