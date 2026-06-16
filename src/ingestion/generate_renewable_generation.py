"""
Renewable Generation Synthesis Module

This module serves as a Weather-Driven Renewable Generation Modeling Engine for the 
Khavda Renewable Energy Park. It estimates historical Solar and Wind generation (MW) 
based on weather conditions ingested from the NASA POWER API and predefined 
capacity and efficiency assumptions.
"""

import os
import pandas as pd
import numpy as np
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================================================
# KHAVDA ASSUMPTIONS & CONSTANTS
# ==================================================
SOLAR_CAPACITY_MW = 1000.0
WIND_CAPACITY_MW = 500.0
SOLAR_EFFICIENCY = 0.22
WIND_EFFICIENCY = 0.35

# Additional engineering constants for realistic modeling
SOLAR_TEMP_COEF = -0.004  # 0.4% efficiency loss per degree C above threshold
SOLAR_TEMP_THRESHOLD_C = 25.0

WIND_CUT_IN_SPEED = 3.0   # m/s
WIND_RATED_SPEED = 12.0   # m/s
WIND_CUT_OUT_SPEED = 25.0 # m/s

def load_weather_data() -> pd.DataFrame:
    """
    Load raw weather data for Khavda from the data/raw directory.
    """
    try:
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        file_path = os.path.join(root_dir, "data", "raw", "khavda_weather.csv")
        
        logger.info(f"Loading weather data from {file_path}")
        df = pd.read_csv(file_path)
        
        # Ensure date is datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Fill missing numeric values with 0 or forward fill to avoid breaking calculations
        numeric_cols = ['temperature_c', 'cloud_cover_pct', 'solar_radiation_kwh_m2_day', 'wind_speed_ms']
        df[numeric_cols] = df[numeric_cols].ffill().fillna(0)
        
        return df
    except Exception as e:
        logger.error(f"Error loading weather data: {e}")
        raise

def calculate_solar_generation(df: pd.DataFrame) -> pd.Series:
    """
    Calculate solar generation (MW) based on weather conditions.
    
    Logic Requirements Addressed:
    1. Base generation is driven by solar radiation (Higher radiation = higher gen).
    2. Cloud cover percentage acts as a derating factor (Higher cloud cover = lower gen).
    3. High temperatures (above 25C) reduce panel efficiency slightly.
    4. Total generation is strictly capped at the installed capacity.
    """
    # 1. Base potential from radiation (kWh/m2/day)
    # Normalizing against an assumed max daily radiation of 8.0 for full output scaling
    base_potential = (df['solar_radiation_kwh_m2_day'] / 8.0) * SOLAR_CAPACITY_MW * SOLAR_EFFICIENCY
    
    # 2. Cloud cover penalty
    # Assume 100% cloud cover still allows ~40% generation due to diffuse radiation
    cloud_penalty = 1.0 - (df['cloud_cover_pct'] / 100.0 * 0.6)
    
    # 3. Temperature penalty
    # Apply the temperature coefficient (-0.004/C) for temperatures above the 25C threshold
    temp_diff = np.maximum(df['temperature_c'] - SOLAR_TEMP_THRESHOLD_C, 0)
    temp_penalty = 1.0 + (temp_diff * SOLAR_TEMP_COEF)
    
    # Calculate final generation
    solar_gen = base_potential * cloud_penalty * temp_penalty
    
    # 4. Capacity constraints: Ensure non-negative and capped at SOLAR_CAPACITY_MW
    solar_gen = np.clip(solar_gen, 0, SOLAR_CAPACITY_MW)
    
    return solar_gen

def calculate_wind_generation(df: pd.DataFrame) -> pd.Series:
    """
    Calculate wind generation (MW) using a simplified engineering wind power curve.
    
    Logic Requirements Addressed:
    1. Low wind speed (< Cut-in) = 0 MW
    2. Medium wind speed (Cut-in to Rated) = Increasing generation (cubic scaling)
    3. High wind speed (Rated to Cut-out) = Maximum generation scaled by efficiency
    4. Very High wind speed (> Cut-out) = 0 MW (safety shutdown)
    5. Generation must not exceed installed capacity.
    """
    wind_speed = df['wind_speed_ms']
    
    # Initialize series with zeros
    wind_gen = pd.Series(0.0, index=df.index)
    
    # Region 2: Between cut-in and rated speed (increasing generation)
    # Using a cubic scaling typical for wind turbine power formulas (P ~ v^3)
    mask_curve = (wind_speed >= WIND_CUT_IN_SPEED) & (wind_speed < WIND_RATED_SPEED)
    power_factor = ((wind_speed[mask_curve] - WIND_CUT_IN_SPEED) / (WIND_RATED_SPEED - WIND_CUT_IN_SPEED)) ** 3
    wind_gen[mask_curve] = power_factor * WIND_CAPACITY_MW * WIND_EFFICIENCY
    
    # Region 3: Between rated and cut-out speed (max generation)
    mask_rated = (wind_speed >= WIND_RATED_SPEED) & (wind_speed <= WIND_CUT_OUT_SPEED)
    wind_gen[mask_rated] = WIND_CAPACITY_MW * WIND_EFFICIENCY
    
    # Capacity constraints: Ensure non-negative and capped at WIND_CAPACITY_MW
    wind_gen = np.clip(wind_gen, 0, WIND_CAPACITY_MW)
    
    return wind_gen

def generate_total_output(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Solar, Wind, and Total generation and attach them to the dataframe.
    """
    logger.info("Calculating Solar Generation...")
    df['solar_generation_mw'] = calculate_solar_generation(df)
    
    logger.info("Calculating Wind Generation...")
    df['wind_generation_mw'] = calculate_wind_generation(df)
    
    logger.info("Calculating Total Generation...")
    df['total_generation_mw'] = df['solar_generation_mw'] + df['wind_generation_mw']
    
    return df

def validate_generation_data(df: pd.DataFrame) -> bool:
    """
    Validate the synthesized generation data against engineering and data quality rules.
    - No negative generation
    - No values above installed capacity
    - No null values in final generation columns
    """
    logger.info("Validating synthesized generation data...")
    
    gen_cols = ['solar_generation_mw', 'wind_generation_mw', 'total_generation_mw']
    
    # Check for nulls
    if df[gen_cols].isnull().any().any():
        logger.error("Validation Failed: Null values detected in generation columns.")
        return False
        
    # Check for negative values
    if (df[gen_cols] < 0).any().any():
        logger.error("Validation Failed: Negative generation values detected.")
        return False
        
    # Check solar capacity constraints
    if (df['solar_generation_mw'] > SOLAR_CAPACITY_MW).any():
        logger.error("Validation Failed: Solar generation exceeds installed capacity.")
        return False
        
    # Check wind capacity constraints
    if (df['wind_generation_mw'] > WIND_CAPACITY_MW).any():
        logger.error("Validation Failed: Wind generation exceeds installed capacity.")
        return False
        
    logger.info("Data validation passed successfully.")
    return True

def save_generation_data(df: pd.DataFrame) -> None:
    """
    Save the final dataframe containing the calculated generation data to data/processed.
    """
    try:
        # Isolate the output columns required by the project specifications
        output_cols = ['date', 'solar_generation_mw', 'wind_generation_mw', 'total_generation_mw', 'site_name']
        output_df = df[output_cols]
        
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        processed_dir = os.path.join(root_dir, "data", "processed")
        
        # Ensure directory exists
        os.makedirs(processed_dir, exist_ok=True)
        
        file_path = os.path.join(processed_dir, "khavda_generation.csv")
        output_df.to_csv(file_path, index=False)
        logger.info(f"Generation data successfully saved to {file_path}")
        
    except Exception as e:
        logger.error(f"Error saving generation data: {e}")
        raise

def main() -> None:
    """
    Main orchestration function for the Weather-Driven Renewable Generation Modeling Engine.
    """
    logger.info("Starting Khavda Renewable Generation Modeling Engine...")
    
    try:
        # 1. Extract Data
        df = load_weather_data()
        
        # 2. Transform (Apply Engineering Models)
        df = generate_total_output(df)
        
        # 3. Validate
        if validate_generation_data(df):
            # 4. Load (Save Data)
            save_generation_data(df)
        else:
            logger.error("Pipeline execution halted due to data validation failures.")
            
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        
    logger.info("Generation Modeling Engine Completed.")

if __name__ == "__main__":
    main()
