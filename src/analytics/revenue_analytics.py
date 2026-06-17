"""
Revenue Analytics Engine

This module estimates the financial value of renewable energy generation at the 
Khavda Renewable Energy Park. It converts energy generation data into revenue, 
annual business value, and weather-related revenue risk metrics.

Outputs are generated for Power BI dashboards, Streamlit applications, and executive reporting.
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================================================
# CONSTANTS & ASSUMPTIONS
# ==================================================
# Base Tariff Assumption: ₹4,500 per MWh
# This represents a blended or PPA-based rate for the generated renewable power.
BASE_TARIFF_PER_MWH = 4500

# Weather Risk Revenue Exposure Percentages
# Defines how much daily revenue is assumed to be at risk during various weather events.
RISK_IMPACT_PCT = {
    'LOW': 0.01,    # 1% Revenue at Risk
    'MEDIUM': 0.05, # 5% Revenue at Risk
    'HIGH': 0.10    # 10% Revenue at Risk
}

# ==================================================
# PATHS AND CONFIGURATION
# ==================================================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED_DATA_DIR = os.path.join(ROOT_DIR, 'data', 'processed')

GENERATION_PATH = os.path.join(PROCESSED_DATA_DIR, 'khavda_generation.csv')
WEATHER_RISK_PATH = os.path.join(PROCESSED_DATA_DIR, 'weather_risk_analytics.csv')
OUTPUT_DATA_PATH = os.path.join(PROCESSED_DATA_DIR, 'revenue_analytics.csv')

REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')
REVENUE_REPORTS_DIR = os.path.join(REPORTS_DIR, 'revenue')

SUMMARY_PATH = os.path.join(REVENUE_REPORTS_DIR, 'revenue_summary.csv')
KPI_PATH = os.path.join(REVENUE_REPORTS_DIR, 'revenue_kpis.csv')
INSIGHTS_PATH = os.path.join(REVENUE_REPORTS_DIR, 'revenue_insights.csv')

TREND_PLOT_PATH = os.path.join(REVENUE_REPORTS_DIR, 'revenue_trend.png')
BREAKDOWN_PLOT_PATH = os.path.join(REVENUE_REPORTS_DIR, 'revenue_breakdown.png')
RISK_PLOT_PATH = os.path.join(REVENUE_REPORTS_DIR, 'revenue_risk_analysis.png')

# Ensure directories exist
os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
os.makedirs(REVENUE_REPORTS_DIR, exist_ok=True)


def load_generation_data() -> pd.DataFrame:
    """Load historical generation data and extend with future AI predictions."""
    logger.info("Loading generation data (historical + future predictions)...")
    try:
        # 1. Load historical actuals
        hist = pd.read_csv(GENERATION_PATH)
        hist['date'] = pd.to_datetime(hist['date'])
        last_hist_date = hist['date'].max()
        
        # 2. Load future predictions (from the forecasting models)
        solar_pred_path = os.path.join(ROOT_DIR, 'reports', 'solar', 'solar_predictions.csv')
        wind_pred_path  = os.path.join(ROOT_DIR, 'reports', 'wind', 'wind_predictions.csv')
        total_pred_path = os.path.join(ROOT_DIR, 'reports', 'total_output', 'total_output_predictions.csv')
        
        future_rows = []
        if os.path.exists(total_pred_path):
            total_pred = pd.read_csv(total_pred_path)
            total_pred['date'] = pd.to_datetime(total_pred['date'])
            # Only take rows beyond last historical date with null actuals (true future)
            future_total = total_pred[
                (total_pred['date'] > last_hist_date) & 
                (total_pred['actual_total_generation_mw'].isna())
            ][['date', 'predicted_total_generation_mw']].copy()
            
            if not future_total.empty and os.path.exists(solar_pred_path) and os.path.exists(wind_pred_path):
                solar_pred = pd.read_csv(solar_pred_path)
                solar_pred['date'] = pd.to_datetime(solar_pred['date'])
                wind_pred = pd.read_csv(wind_pred_path)
                wind_pred['date'] = pd.to_datetime(wind_pred['date'])
                
                future_solar = solar_pred[solar_pred['date'] > last_hist_date][['date', 'predicted_solar_generation_mw']]
                future_wind  = wind_pred[wind_pred['date'] > last_hist_date][['date', 'predicted_wind_generation_mw']]
                
                future_merged = pd.merge(future_total, future_solar, on='date', how='left')
                future_merged = pd.merge(future_merged, future_wind, on='date', how='left')
                future_merged = future_merged.rename(columns={
                    'predicted_total_generation_mw' : 'total_generation_mw',
                    'predicted_solar_generation_mw' : 'solar_generation_mw',
                    'predicted_wind_generation_mw'  : 'wind_generation_mw',
                })
                future_merged['site_name'] = 'Khavda Renewable Energy Park'
                future_rows.append(future_merged)
        
        # 3. Combine historical + future
        if future_rows:
            future_df = pd.concat(future_rows, ignore_index=True)
            # Fill any missing solar/wind estimates from total
            future_df['solar_generation_mw'] = future_df['solar_generation_mw'].fillna(future_df['total_generation_mw'] * 0.6)
            future_df['wind_generation_mw']  = future_df['wind_generation_mw'].fillna(future_df['total_generation_mw'] * 0.4)
            df = pd.concat([hist, future_df], ignore_index=True)
            logger.info(f"Appended {len(future_df)} future rows to generation data.")
        else:
            df = hist
            logger.warning("No future prediction rows found.")
        
        return df
    except Exception as e:
        logger.error(f"Failed to load generation data: {e}")
        import traceback; logger.error(traceback.format_exc())
        raise


def load_weather_risk_data() -> pd.DataFrame:
    """Load weather risk analytics data if available."""
    logger.info("Loading weather risk analytics data...")
    if os.path.exists(WEATHER_RISK_PATH):
        try:
            df = pd.read_csv(WEATHER_RISK_PATH)
            df['date'] = pd.to_datetime(df['date'])
            return df
        except Exception as e:
            logger.error(f"Failed to load weather risk data: {e}")
            return pd.DataFrame()
    else:
        logger.warning(f"Weather risk data not found at {WEATHER_RISK_PATH}.")
        return pd.DataFrame()


def calculate_revenue(gen_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate the financial value of the generated power.
    Methodology: Revenue (INR) = Generation (MW) * BASE_TARIFF_PER_MWH
    Provides breakouts in raw INR, Lakhs (100,000s), and Crores (10,000,000s).
    """
    logger.info("Calculating baseline revenue metrics...")
    df = gen_df.copy()
    
    # Validation to prevent negative generation errors
    df['solar_generation_mw'] = df['solar_generation_mw'].clip(lower=0)
    df['wind_generation_mw'] = df['wind_generation_mw'].clip(lower=0)
    df['total_generation_mw'] = df['total_generation_mw'].clip(lower=0)
    
    # Base Revenue Calculations (INR)
    df['solar_revenue_inr'] = np.round(df['solar_generation_mw'] * BASE_TARIFF_PER_MWH, 2)
    df['wind_revenue_inr'] = np.round(df['wind_generation_mw'] * BASE_TARIFF_PER_MWH, 2)
    df['daily_revenue_inr'] = np.round(df['total_generation_mw'] * BASE_TARIFF_PER_MWH, 2)
    
    # Financial Denominations
    df['daily_revenue_lakhs'] = np.round(df['daily_revenue_inr'] / 1_000_00, 2)
    df['daily_revenue_crores'] = np.round(df['daily_revenue_inr'] / 1_000_0000, 2)
    
    return df


def calculate_revenue_risk(rev_df: pd.DataFrame, weather_df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply revenue-at-risk logic based on weather risk levels.
    """
    logger.info("Calculating revenue-at-risk...")
    df = rev_df.copy()
    
    if not weather_df.empty:
        # Merge on date
        merged = pd.merge(df, weather_df[['date', 'overall_risk_level']], on='date', how='left')
        
        # Fill missing risk levels with 'LOW' as a baseline assumption
        merged['overall_risk_level'] = merged['overall_risk_level'].fillna('LOW')
        
        # Map risk levels to percentages
        merged['risk_percentage'] = merged['overall_risk_level'].map(RISK_IMPACT_PCT).fillna(RISK_IMPACT_PCT['LOW'])
        
        # Calculate revenue at risk
        merged['revenue_at_risk_inr'] = np.round(merged['daily_revenue_inr'] * merged['risk_percentage'], 2)
        
        # Cleanup
        merged = merged.drop(columns=['risk_percentage'])
        return merged
    else:
        logger.warning("No weather data provided. Assuming 0 revenue at risk.")
        df['overall_risk_level'] = 'UNKNOWN'
        df['revenue_at_risk_inr'] = 0.0
        return df


def generate_kpis(df: pd.DataFrame) -> dict:
    """Generate executive KPI summary metrics."""
    logger.info("Generating executive KPIs...")
    
    total_revenue = df['daily_revenue_inr'].sum()
    average_daily_revenue = df['daily_revenue_inr'].mean()
    max_daily = df['daily_revenue_inr'].max()
    min_daily = df['daily_revenue_inr'].min()
    
    annualized_revenue = average_daily_revenue * 365
    total_revenue_at_risk = df['revenue_at_risk_inr'].sum()
    
    kpis = {
        'Total_Revenue': round(total_revenue, 2),
        'Average_Daily_Revenue': round(average_daily_revenue, 2),
        'Maximum_Daily_Revenue': round(max_daily, 2),
        'Minimum_Daily_Revenue': round(min_daily, 2),
        'Annualized_Revenue': round(annualized_revenue, 2),
        'Total_Revenue_At_Risk': round(total_revenue_at_risk, 2)
    }
    return kpis


def generate_business_insights(df: pd.DataFrame, kpis: dict) -> pd.DataFrame:
    """Generate plain-text business insights based on the revenue profile."""
    logger.info("Generating business insights...")
    insights = []
    
    total_solar = df['solar_revenue_inr'].sum()
    total_wind = df['wind_revenue_inr'].sum()
    
    if total_solar > total_wind:
        insights.append("Solar generation contributes the majority of revenue.")
    else:
        insights.append("Wind generation contributes the majority of revenue.")
        
    risk_ratio = kpis['Total_Revenue_At_Risk'] / kpis['Total_Revenue'] if kpis['Total_Revenue'] > 0 else 0
    if risk_ratio < 0.03:
        insights.append("Weather-related revenue exposure remains low.")
    elif risk_ratio < 0.07:
        insights.append("Weather-related revenue exposure is moderate.")
    else:
        insights.append("Significant revenue is exposed to adverse weather conditions.")
        
    # Example benchmark assumption: 1.5 Billion INR
    if kpis['Annualized_Revenue'] > 1_500_000_000:
        insights.append("Annual revenue potential exceeds expected benchmark.")
    else:
        insights.append("Annual revenue potential is tracking below the high-performance benchmark.")
        
    return pd.DataFrame({'Business_Insight': insights})


def create_visualizations(df: pd.DataFrame):
    """Generate financial dashboard visualizations."""
    logger.info("Generating financial visualizations...")
    try:
        # Plot 1: Daily Revenue Trend
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['daily_revenue_inr'] / 1_000_0000, color='green', linewidth=1.5)
        plt.title('Daily Revenue Trend', fontweight='bold', fontsize=14)
        plt.ylabel('Revenue (Crores INR)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(TREND_PLOT_PATH, dpi=300)
        plt.close()
        
        # Plot 2: Solar vs Wind Breakdown
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['solar_revenue_inr'] / 1_000_0000, label='Solar Revenue', color='orange', alpha=0.8)
        plt.plot(df['date'], df['wind_revenue_inr'] / 1_000_0000, label='Wind Revenue', color='blue', alpha=0.8)
        plt.title('Revenue Breakdown: Solar vs Wind', fontweight='bold', fontsize=14)
        plt.ylabel('Revenue (Crores INR)', fontsize=12)
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(BREAKDOWN_PLOT_PATH, dpi=300)
        plt.close()
        
        # Plot 3: Revenue at Risk
        plt.figure(figsize=(12, 5))
        plt.fill_between(df['date'], df['revenue_at_risk_inr'] / 1_000_00, color='red', alpha=0.4)
        plt.plot(df['date'], df['revenue_at_risk_inr'] / 1_000_00, color='darkred', linewidth=1)
        plt.title('Revenue at Risk Over Time', fontweight='bold', fontsize=14)
        plt.ylabel('Revenue at Risk (Lakhs INR)', fontsize=12)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(RISK_PLOT_PATH, dpi=300)
        plt.close()
        
    except Exception as e:
        logger.error(f"Error generating visualizations: {e}")
        raise


def save_results(df: pd.DataFrame, kpis: dict, insights_df: pd.DataFrame):
    """Save processed datasets and formatted CSV reports for dashboard consumption."""
    logger.info("Saving results...")
    try:
        # Ensure site_name exists
        if 'site_name' not in df.columns:
            df['site_name'] = 'Khavda Renewable Energy Park'
            
        # 1. Output Dataset Validation and Save
        output_cols = [
            'date', 'site_name', 'solar_generation_mw', 'wind_generation_mw', 'total_generation_mw',
            'solar_revenue_inr', 'wind_revenue_inr', 'daily_revenue_inr', 'revenue_at_risk_inr',
            'daily_revenue_lakhs', 'daily_revenue_crores'
        ]
        
        # Only validate/fill columns that exist
        existing_cols = [c for c in output_cols if c in df.columns]
        if df[existing_cols].isnull().any().any():
            logger.warning("Null values detected in output dataset. Forward filling...")
            df = df.ffill().fillna(0)
            
        df[existing_cols].to_csv(OUTPUT_DATA_PATH, index=False)
        
        # 2. Executive Summary Metrics
        summary_df = pd.DataFrame([kpis])
        summary_df.to_csv(SUMMARY_PATH, index=False)
        
        # 3. KPI Formatted File
        kpi_rows = [
            {'KPI': 'Total Revenue', 'Value': kpis['Total_Revenue'], 'Unit': 'INR'},
            {'KPI': 'Average Daily Revenue', 'Value': kpis['Average_Daily_Revenue'], 'Unit': 'INR'},
            {'KPI': 'Maximum Daily Revenue', 'Value': kpis['Maximum_Daily_Revenue'], 'Unit': 'INR'},
            {'KPI': 'Minimum Daily Revenue', 'Value': kpis['Minimum_Daily_Revenue'], 'Unit': 'INR'},
            {'KPI': 'Annualized Revenue', 'Value': kpis['Annualized_Revenue'], 'Unit': 'INR'},
            {'KPI': 'Total Revenue At Risk', 'Value': kpis['Total_Revenue_At_Risk'], 'Unit': 'INR'}
        ]
        kpi_df = pd.DataFrame(kpi_rows)
        kpi_df.to_csv(KPI_PATH, index=False)
        
        # 4. Insights
        insights_df.to_csv(INSIGHTS_PATH, index=False)
        
        logger.info(f"Analytics output saved to {OUTPUT_DATA_PATH}")
        logger.info(f"Reports successfully saved to {REVENUE_REPORTS_DIR}")
        
    except Exception as e:
        logger.error(f"Failed to save results: {e}")
        raise


def main():
    logger.info("==================================================")
    logger.info("Starting Revenue Analytics Engine")
    logger.info("==================================================")
    try:
        # Load Data
        gen_df = load_generation_data()
        weather_df = load_weather_risk_data()
        
        # Core Calculations
        rev_df = calculate_revenue(gen_df)
        final_df = calculate_revenue_risk(rev_df, weather_df)
        
        # Metrics and Insights
        kpis = generate_kpis(final_df)
        insights_df = generate_business_insights(final_df, kpis)
        
        # Visuals and Export
        create_visualizations(final_df)
        save_results(final_df, kpis, insights_df)
        
        logger.info("==================================================")
        logger.info("Revenue Analytics Engine Completed Successfully")
        logger.info("==================================================")
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
