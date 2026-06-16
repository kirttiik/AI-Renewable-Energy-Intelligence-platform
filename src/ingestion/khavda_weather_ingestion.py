"""
Khavda Renewable Energy Park Weather Ingestion Module

This module fetches hyper-local daily weather data from the NASA POWER API
for the Khavda Renewable Energy Park. It extracts Temperature, Humidity,
Wind Speed, Solar Radiation, Rainfall, and Cloud Cover.
"""

import os
import requests
import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
PARAMETERS = "T2M,RH2M,WS10M,ALLSKY_SFC_SW_DWN,PRECTOTCORR,CLOUD_AMT"

KHAVDA_LAT = 23.90
KHAVDA_LON = 69.75
SITE_NAME = "Khavda Renewable Energy Park"

REQUIRED_COLUMNS = [
    'temperature_c',
    'humidity_pct',
    'wind_speed_ms',
    'solar_radiation_kwh_m2_day',
    'rainfall_mm',
    'cloud_cover_pct'
]

def fetch_weather_data(start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
    """Fetch weather data from NASA POWER API."""
    params = {
        "parameters": PARAMETERS,
        "community": "RE",
        "longitude": KHAVDA_LON,
        "latitude": KHAVDA_LAT,
        "start": start_date,
        "end": end_date,
        "format": "JSON"
    }
    
    logger.info(f"Fetching data from NASA POWER API from {start_date} to {end_date}")
    try:
        response = requests.get(NASA_POWER_URL, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logger.error("NASA POWER API request timed out.")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from NASA POWER API: {e}")
        return None

def process_weather_data(data: Dict[str, Any]) -> pd.DataFrame:
    """Parse API JSON response into a Pandas DataFrame and clean data."""
    try:
        timeseries_data = data.get("properties", {}).get("parameter", {})
        if not timeseries_data:
            raise ValueError("No parameter data found in API response.")
            
        df = pd.DataFrame(timeseries_data).reset_index()
        df.rename(columns={'index': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'], format='%Y%m%d')
        
        column_mapping = {
            'T2M': 'temperature_c',
            'RH2M': 'humidity_pct',
            'WS10M': 'wind_speed_ms',
            'ALLSKY_SFC_SW_DWN': 'solar_radiation_kwh_m2_day',
            'PRECTOTCORR': 'rainfall_mm',
            'CLOUD_AMT': 'cloud_cover_pct'
        }
        df.rename(columns=column_mapping, inplace=True)
        
        # Replace NASA's missing data fill values (-999, -999.0) with NaN
        df = df.replace([-999, -999.0], pd.NA)
        
        return df
    except Exception as e:
        logger.error(f"Error processing weather data: {e}")
        raise

def validate_weather_data(df: pd.DataFrame) -> bool:
    """Validate DataFrame for required columns and ensure it's not empty."""
    if df.empty:
        logger.warning("Validation Failed: Dataframe is empty.")
        return False
        
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        logger.error(f"Validation Failed: Missing required columns: {missing_columns}")
        return False
        
    logger.info("Data validation successful.")
    return True

def add_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Add static and dynamic metadata columns to the DataFrame."""
    df['site_name'] = SITE_NAME
    df['latitude'] = KHAVDA_LAT
    df['longitude'] = KHAVDA_LON
    df['data_source'] = "NASA_POWER"
    df['load_timestamp'] = datetime.now()
    return df

def save_weather_data(df: pd.DataFrame) -> None:
    """Save the final DataFrame to the raw data directory as a CSV."""
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        raw_data_dir = os.path.join(root_dir, "data", "raw")
        os.makedirs(raw_data_dir, exist_ok=True)
        
        file_path = os.path.join(raw_data_dir, "khavda_weather.csv")
        df.to_csv(file_path, index=False)
        logger.info(f"Data successfully saved to {file_path}")
    except Exception as e:
        logger.error(f"Error saving data to CSV: {e}")
        raise

def main() -> None:
    """Main orchestration function for the ingestion pipeline."""
    logger.info("Starting Khavda Weather Ingestion Pipeline...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=5*365)
    
    start_date_str = start_date.strftime("%Y%m%d")
    end_date_str = end_date.strftime("%Y%m%d")
    
    raw_data = fetch_weather_data(start_date_str, end_date_str)
    
    if raw_data:
        try:
            df = process_weather_data(raw_data)
            
            if validate_weather_data(df):
                df = add_metadata(df)
                save_weather_data(df)
            else:
                logger.error("Pipeline stopped due to validation failure.")
                
        except Exception as e:
            logger.error(f"Pipeline failed during processing/saving: {e}")
    else:
        logger.warning("Pipeline stopped due to API extraction failure.")
        
    logger.info("Pipeline execution completed.")

if __name__ == "__main__":
    main()
