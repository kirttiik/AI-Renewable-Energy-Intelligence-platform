"""
Weather Risk Analytics Engine

This module identifies weather conditions which may negatively impact 
renewable energy generation and plant operations at the Khavda Renewable Energy Park.
It generates operational risk indicators and alerts suitable for a Renewable Energy 
Operations Command Center and executive dashboard reporting.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================================================
# PATHS AND CONFIGURATION
# ==================================================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUT_DATA_PATH = os.path.join(ROOT_DIR, 'data', 'raw', 'khavda_weather_openmeteo.csv')
OUTPUT_DATA_PATH = os.path.join(ROOT_DIR, 'data', 'processed', 'weather_risk_analytics.csv')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')
WEATHER_REPORTS_DIR = os.path.join(REPORTS_DIR, 'weather')
SUMMARY_PATH = os.path.join(WEATHER_REPORTS_DIR, 'weather_risk_summary.csv')

# Ensure directories exist
os.makedirs(os.path.join(ROOT_DIR, 'data', 'processed'), exist_ok=True)
os.makedirs(WEATHER_REPORTS_DIR, exist_ok=True)

def load_weather_data() -> pd.DataFrame:
    """Load the raw historical weather data and future forecasts."""
    logger.info(f"Loading weather data...")
    try:
        df = pd.read_csv(INPUT_DATA_PATH)
        forecast_path = os.path.join(ROOT_DIR, 'data', 'raw', 'khavda_weather_forecast.csv')
        
        if os.path.exists(forecast_path):
            forecast_df = pd.read_csv(forecast_path)
            # rename solar_radiation to ghi if forecast uses old schema
            if 'solar_radiation_kwh_m2_day' in forecast_df.columns:
                forecast_df = forecast_df.rename(columns={'solar_radiation_kwh_m2_day': 'ghi_kwh_m2_day'})
            df = pd.concat([df, forecast_df], ignore_index=True)
            df = df.drop_duplicates(subset=['date'], keep='last')
            
        df['date'] = pd.to_datetime(df['date'])
        
        # Clean missing raw data
        numeric_cols = ['temperature_c', 'humidity_pct', 'wind_speed_ms', 
                        'ghi_kwh_m2_day', 'rainfall_mm', 'cloud_cover_pct']
        
        for col in numeric_cols:
            if col not in df.columns:
                df[col] = 0
                
        df[numeric_cols] = df[numeric_cols].ffill().fillna(0)
        
        return df
    except Exception as e:
        logger.error(f"Failed to load weather data: {e}")
        raise

def calculate_heatwave_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluate Heatwave Risk.
    
    Heatwave impact on solar performance:
    Solar panels suffer efficiency losses at high temperatures (typically -0.4% per degree C above 25C).
    Extreme heatwaves (> 42C) can cause inverter derating, trigger thermal safety shutdowns,
    and accelerate hardware degradation across the plant.
    """
    logger.info("Calculating Heatwave Risk...")
    conditions = [
        (df['temperature_c'] >= 42),
        (df['temperature_c'] >= 38) & (df['temperature_c'] < 42),
        (df['temperature_c'] < 38)
    ]
    choices_str = ['HIGH', 'MEDIUM', 'LOW']
    choices_num = [3, 2, 1]
    
    df['heatwave_risk'] = np.select(conditions, choices_str, default='LOW')
    df['heatwave_score'] = np.select(conditions, choices_num, default=1)
    return df

def calculate_cloud_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluate Cloud Curtailment Risk.
    
    Cloud cover impact on solar generation:
    Thick cloud cover (> 70%) directly blocks direct normal irradiance (DNI), 
    causing sharp and unpredictable drops in solar power output. This creates a "ramp down"
    event which requires immediate grid balancing and fast-responding reserve generation.
    """
    logger.info("Calculating Cloud Curtailment Risk...")
    conditions = [
        (df['cloud_cover_pct'] >= 70),
        (df['cloud_cover_pct'] >= 40) & (df['cloud_cover_pct'] < 70),
        (df['cloud_cover_pct'] < 40)
    ]
    choices_str = ['HIGH', 'MEDIUM', 'LOW']
    choices_num = [3, 2, 1]
    
    df['cloud_curtailment_risk'] = np.select(conditions, choices_str, default='LOW')
    df['cloud_score'] = np.select(conditions, choices_num, default=1)
    return df

def calculate_rainfall_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluate Heavy Rain Risk.
    
    Rainfall operational risks:
    While light rain is beneficial as it naturally cleans solar panels (mitigating soiling losses),
    heavy rain (>20mm) can cause localized site flooding, washouts of access roads,
    hinder maintenance crew access, and is often associated with severe convective storm systems.
    """
    logger.info("Calculating Heavy Rain Risk...")
    conditions = [
        (df['rainfall_mm'] >= 20),
        (df['rainfall_mm'] >= 10) & (df['rainfall_mm'] < 20),
        (df['rainfall_mm'] < 10)
    ]
    choices_str = ['HIGH', 'MEDIUM', 'LOW']
    choices_num = [3, 2, 1]
    
    df['heavy_rain_risk'] = np.select(conditions, choices_str, default='LOW')
    df['rain_score'] = np.select(conditions, choices_num, default=1)
    return df

def calculate_dust_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluate Dust Storm Risk.
    
    Dust storm impact on panel efficiency:
    High winds (>12 m/s) in arid/desert regions like Khavda create severe dust storms. 
    Dust accumulation (soiling) physically blocks sunlight from reaching the photovoltaic cells, 
    causing severe, lingering performance drops until the panels are manually or robotically cleaned.
    Rainfall mitigates dust risk by washing the airborne dust and panels.
    """
    logger.info("Calculating Dust Storm Risk...")
    conditions = [
        (df['wind_speed_ms'] >= 12) & (df['rainfall_mm'] < 2),
        (df['wind_speed_ms'] >= 8) & (df['wind_speed_ms'] < 12) | ((df['wind_speed_ms'] >= 12) & (df['rainfall_mm'] >= 2)),
        (df['wind_speed_ms'] < 8)
    ]
    choices_str = ['HIGH', 'MEDIUM', 'LOW']
    choices_num = [3, 2, 1]
    
    df['dust_storm_risk'] = np.select(conditions, choices_str, default='LOW')
    df['dust_score'] = np.select(conditions, choices_num, default=1)
    return df

def calculate_overall_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the composite overall risk score and map to a categorical level.
    """
    logger.info("Calculating Overall Risk Score and Level...")
    # Formula: Average of all risk category scores
    df['overall_risk_score'] = (df['heatwave_score'] + df['cloud_score'] + df['rain_score'] + df['dust_score']) / 4.0
    
    conditions = [
        (df['overall_risk_score'] >= 2.2),
        (df['overall_risk_score'] >= 1.5) & (df['overall_risk_score'] < 2.2),
        (df['overall_risk_score'] < 1.5)
    ]
    choices_str = ['HIGH', 'MEDIUM', 'LOW']
    df['overall_risk_level'] = np.select(conditions, choices_str, default='LOW')
    
    # Active risk alerting for operational dashboards
    alert_conditions = [
        (df['overall_risk_score'] >= 2.2),
        (df['overall_risk_score'] >= 1.8)
    ]
    alert_choices = ['CRITICAL_WEATHER_ALERT', 'WEATHER_WARNING']
    df['risk_alert'] = np.select(alert_conditions, alert_choices, default='NORMAL_OPERATIONS')
    
    def get_active_factors(row):
        factors = []
        if row['heatwave_risk'] == 'HIGH': factors.append('HEATWAVE')
        if row['cloud_curtailment_risk'] == 'HIGH': factors.append('CLOUD_CURTAILMENT')
        if row['heavy_rain_risk'] == 'HIGH': factors.append('HEAVY_RAIN')
        if row['dust_storm_risk'] == 'HIGH': factors.append('DUST_STORM')
        return '|'.join(factors) if factors else 'NORMAL'
        
    df['active_high_risk_factors'] = df.apply(get_active_factors, axis=1)
    
    return df

def generate_summary_kpis(df: pd.DataFrame) -> dict:
    """Generate high-level KPI aggregations for executive reporting."""
    logger.info("Generating Summary KPIs...")
    # Calculate most common risk factor
    factors = df[df['active_high_risk_factors'] != 'NORMAL']['active_high_risk_factors']
    if len(factors) > 0:
        all_factors = factors.str.split('|').explode()
        most_common = all_factors.value_counts().index[0]
    else:
        most_common = 'NONE'
        
    kpis = {
        'High_Risk_Days': int((df['overall_risk_level'] == 'HIGH').sum()),
        'Medium_Risk_Days': int((df['overall_risk_level'] == 'MEDIUM').sum()),
        'Low_Risk_Days': int((df['overall_risk_level'] == 'LOW').sum()),
        'Weather_Warning_Days': int((df['risk_alert'] == 'WEATHER_WARNING').sum()),
        'Critical_Alert_Days': int((df['risk_alert'] == 'CRITICAL_WEATHER_ALERT').sum()),
        'Average_Risk_Score': float(df['overall_risk_score'].mean().round(2)),
        'Maximum_Risk_Score': float(df['overall_risk_score'].max()),
        'Most_Common_Risk_Factor': most_common
    }
    return kpis

def create_visualizations(df: pd.DataFrame):
    """Generate graphical trends of the operational weather risks."""
    logger.info("Generating Visualizations...")
    try:
        # Plot 1: Overall Risk Trend
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['overall_risk_score'], color='firebrick', linewidth=1.5)
        plt.title('Overall Weather Risk Score Trend', fontweight='bold')
        plt.ylabel('Risk Score (1=Low, 3=High)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(WEATHER_REPORTS_DIR, 'overall_risk_trend.png'), dpi=300)
        plt.close()
        
        # Plot 2: Heatwave Risk Trend
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['heatwave_score'], color='darkorange', linewidth=1.5)
        plt.title('Heatwave Risk Trend', fontweight='bold')
        plt.ylabel('Risk Score')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(WEATHER_REPORTS_DIR, 'heatwave_risk_trend.png'), dpi=300)
        plt.close()
        
        # Plot 3: Cloud Risk Trend
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['cloud_score'], color='slategray', linewidth=1.5)
        plt.title('Cloud Curtailment Risk Trend', fontweight='bold')
        plt.ylabel('Risk Score')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(WEATHER_REPORTS_DIR, 'cloud_risk_trend.png'), dpi=300)
        plt.close()
        
        # Plot 4: Dashboard Summary Grid
        fig, axs = plt.subplots(2, 2, figsize=(16, 10))
        
        axs[0, 0].plot(df['date'], df['overall_risk_score'], color='firebrick')
        axs[0, 0].set_title('Overall Operational Risk', fontweight='bold')
        
        axs[0, 1].plot(df['date'], df['heatwave_score'], color='darkorange')
        axs[0, 1].set_title('Heatwave Risk', fontweight='bold')
        
        axs[1, 0].plot(df['date'], df['rain_score'], color='teal')
        axs[1, 0].set_title('Heavy Rain Risk', fontweight='bold')
        
        axs[1, 1].plot(df['date'], df['dust_score'], color='saddlebrown')
        axs[1, 1].set_title('Dust Storm Risk', fontweight='bold')
        
        for ax in axs.flat:
            ax.grid(True, alpha=0.3)
            ax.set_ylabel('Score (1-3)')
            ax.tick_params(axis='x', rotation=45)
            
        plt.tight_layout()
        plt.savefig(os.path.join(WEATHER_REPORTS_DIR, 'weather_risk_dashboard.png'), dpi=300)
        plt.close()
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
        raise

def validate_data(df: pd.DataFrame):
    """Validate calculated scores, fill nulls from future forecast rows before they reach save."""
    logger.info("Validating Output Data...")
    
    if df.isnull().any().any():
        logger.warning("Null values detected in output dataframe. Filling with defaults...")
        # Fill categoricals with LOW/NONE defaults
        for col in ['heatwave_risk', 'cloud_curtailment_risk', 'heavy_rain_risk', 'dust_storm_risk', 'overall_risk_level']:
            if col in df.columns:
                df[col] = df[col].fillna('LOW')
        if 'risk_alert' in df.columns:
            df['risk_alert'] = df['risk_alert'].fillna('NONE')
        if 'active_high_risk_factors' in df.columns:
            df['active_high_risk_factors'] = df['active_high_risk_factors'].fillna('NORMAL')
        if 'site_name' in df.columns:
            df['site_name'] = df['site_name'].fillna('Khavda Renewable Energy Park')
        # Fill numeric cols with 1 (LOW score)
        score_cols = ['heatwave_score', 'cloud_score', 'rain_score', 'dust_score', 'overall_risk_score']
        for col in score_cols:
            if col in df.columns:
                df[col] = df[col].fillna(1)
        
    score_cols = ['heatwave_score', 'cloud_score', 'rain_score', 'dust_score', 'overall_risk_score']
    for col in score_cols:
        if col in df.columns and not df[col].between(1, 3).all():
            logger.error(f"Validation Error: Scores out of allowed range [1-3] in column: {col}.")
            return False, df
            
    logger.info("Validation passed successfully.")
    return True, df

def save_results(df: pd.DataFrame, kpis: dict):
    """Save processed datasets and executive summary files."""
    logger.info("Saving analytics results and KPIs...")
    try:
        # Save Main Processed Data
        output_cols = [
            'date', 'site_name', 'heatwave_risk', 'cloud_curtailment_risk', 
            'heavy_rain_risk', 'dust_storm_risk', 'overall_risk_score', 'overall_risk_level', 'risk_alert',
            'active_high_risk_factors'
        ]
        df[output_cols].to_csv(OUTPUT_DATA_PATH, index=False)
        
        # Format KPI Summary for Power BI ingestion
        kpi_rows = [
            {'KPI': 'High Risk Days', 'Value': kpis['High_Risk_Days']},
            {'KPI': 'Medium Risk Days', 'Value': kpis['Medium_Risk_Days']},
            {'KPI': 'Low Risk Days', 'Value': kpis['Low_Risk_Days']},
            {'KPI': 'Weather Warning Days', 'Value': kpis['Weather_Warning_Days']},
            {'KPI': 'Critical Alert Days', 'Value': kpis['Critical_Alert_Days']},
            {'KPI': 'Average Risk Score', 'Value': kpis['Average_Risk_Score']},
            {'KPI': 'Maximum Risk Score', 'Value': kpis['Maximum_Risk_Score']},
            {'KPI': 'Most Common Risk Factor', 'Value': kpis['Most_Common_Risk_Factor']}
        ]
        pd.DataFrame(kpi_rows).to_csv(SUMMARY_PATH, index=False)
        
        logger.info(f"Main Analytics Data saved to {OUTPUT_DATA_PATH}")
        logger.info(f"Summary KPIs saved to {SUMMARY_PATH}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")
        raise

def main():
    logger.info("==================================================")
    logger.info("Starting Weather Risk Analytics Engine")
    logger.info("==================================================")
    try:
        df = load_weather_data()
        
        # Apply Risk Methodologies
        df = calculate_heatwave_risk(df)
        df = calculate_cloud_risk(df)
        df = calculate_rainfall_risk(df)
        df = calculate_dust_risk(df)
        
        # Aggregate Overall Profile
        df = calculate_overall_risk(df)
        
        is_valid, df = validate_data(df)
        if not is_valid:
            logger.error("Pipeline halted due to validation errors.")
            return
            
        # Compile Reporting Assets
        kpis = generate_summary_kpis(df)
        create_visualizations(df)
        save_results(df, kpis)
        
        logger.info("==================================================")
        logger.info("Weather Risk Analytics Engine Completed Successfully")
        logger.info("==================================================")
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
