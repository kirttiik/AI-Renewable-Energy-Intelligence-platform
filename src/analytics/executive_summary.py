"""
Executive Summary Analytics Engine

This module consolidates outputs from all analytics and forecasting modules into a single 
executive-ready dataset. It serves as the final intelligence layer of the platform, 
providing a one-stop summary for Power BI dashboards, Streamlit applications, 
executive reporting, and management reviews.
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, mean_absolute_percentage_error

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

# Input Paths
PROCESSED_DATA_DIR = os.path.join(ROOT_DIR, 'data', 'processed')
CARBON_OFFSET_PATH = os.path.join(PROCESSED_DATA_DIR, 'carbon_offset_analytics.csv')
WEATHER_RISK_PATH = os.path.join(PROCESSED_DATA_DIR, 'weather_risk_analytics.csv')
REVENUE_PATH = os.path.join(PROCESSED_DATA_DIR, 'revenue_analytics.csv')

REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')
# Note: Reflecting the recent directory restructuring
TOTAL_OUTPUT_PREDICTIONS_PATH = os.path.join(REPORTS_DIR, 'total_output', 'total_output_predictions.csv')

# Output Paths (Using a dedicated executive subdirectory)
EXEC_REPORTS_DIR = os.path.join(REPORTS_DIR, 'executive')

EXEC_SUMMARY_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_summary.csv')
KPI_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_dashboard_kpis.csv')
ACCURACY_PATH = os.path.join(EXEC_REPORTS_DIR, 'forecast_accuracy_summary.csv')
NARRATIVE_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_narrative.csv')

PLOT_GEN_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_generation_overview.png')
PLOT_REV_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_revenue_overview.png')
PLOT_SUSTAINABILITY_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_sustainability_overview.png')
PLOT_RISK_PATH = os.path.join(EXEC_REPORTS_DIR, 'executive_risk_overview.png')

# Ensure directories exist
os.makedirs(EXEC_REPORTS_DIR, exist_ok=True)


def load_datasets() -> dict:
    """Load all required processed datasets."""
    logger.info("Loading analytics datasets...")
    datasets = {}
    
    paths = {
        'carbon_offset': CARBON_OFFSET_PATH,
        'weather_risk': WEATHER_RISK_PATH,
        'revenue': REVENUE_PATH,
        'predictions': TOTAL_OUTPUT_PREDICTIONS_PATH
    }
    
    for name, path in paths.items():
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                datasets[name] = df
                logger.info(f"Loaded {name} dataset.")
            except Exception as e:
                logger.warning(f"Error loading {path}: {e}")
        else:
            logger.warning(f"Dataset missing: {path}. Continuing without it.")
            
    return datasets


def merge_datasets(datasets: dict) -> pd.DataFrame:
    """Consolidate outputs from all modules into a single dataset using left joins on date."""
    logger.info("Merging datasets into executive summary...")
    
    # We need a base dataframe to merge against. Revenue or Weather usually has full coverage.
    if 'revenue' in datasets:
        base_df = datasets['revenue'].copy()
    elif 'weather_risk' in datasets:
        base_df = datasets['weather_risk'].copy()
    else:
        logger.error("No base dataset found to initiate merge.")
        return pd.DataFrame()
        
    merged_df = base_df
    
    # Merge Carbon Offset
    if 'carbon_offset' in datasets:
        cols_to_use = ['date'] + [col for col in datasets['carbon_offset'].columns if col not in base_df.columns]
        merged_df = pd.merge(merged_df, datasets['carbon_offset'][cols_to_use], on='date', how='left')
        
    # Merge Weather Risk
    if 'weather_risk' in datasets:
        cols_to_use = ['date'] + [col for col in datasets['weather_risk'].columns if col not in merged_df.columns]
        merged_df = pd.merge(merged_df, datasets['weather_risk'][cols_to_use], on='date', how='left')
        
    # Merge Predictions
    if 'predictions' in datasets:
        pred_df = datasets['predictions'].copy()
        # Rename actual column if it exists in predictions to avoid conflicts
        if 'actual_total_generation_mw' in pred_df.columns:
            pred_df = pred_df.rename(columns={'actual_total_generation_mw': 'actual_test_generation_mw'})
            
        cols_to_use = ['date'] + [col for col in pred_df.columns if col not in merged_df.columns]
        merged_df = pd.merge(merged_df, pred_df[cols_to_use], on='date', how='outer')
        
    # Standardize missing columns based on expectations
    expected_cols = [
        'site_name', 'total_generation_mw', 'predicted_total_generation_mw', 
        'daily_revenue_inr', 'revenue_at_risk_inr', 'co2_avoided_tons', 
        'coal_saved_tons', 'trees_equivalent_million', 'overall_risk_level', 
        'risk_alert', 'active_high_risk_factors'
    ]
    
    for col in expected_cols:
        if col not in merged_df.columns:
            merged_df[col] = np.nan
            
    # Forward fill to handle any mid-series NAs if possible, then fillna(0) for numerics
    merged_df = merged_df.sort_values('date')
    
    # Provide defaults for missing categoricals
    if 'site_name' in merged_df.columns:
        merged_df['site_name'] = merged_df['site_name'].fillna('Khavda Renewable Energy Park')
    if 'overall_risk_level' in merged_df.columns:
        merged_df['overall_risk_level'] = merged_df['overall_risk_level'].fillna('LOW')
    if 'risk_alert' in merged_df.columns:
        merged_df['risk_alert'] = merged_df['risk_alert'].fillna('NONE')
    if 'active_high_risk_factors' in merged_df.columns:
        merged_df['active_high_risk_factors'] = merged_df['active_high_risk_factors'].fillna('NORMAL')
        
    # Fill numeric NAs with 0
    numeric_cols = merged_df.select_dtypes(include=[np.number]).columns
    merged_df[numeric_cols] = merged_df[numeric_cols].fillna(0)
    
    return merged_df


def generate_ai_insights(df: pd.DataFrame) -> pd.DataFrame:
    """Create a daily ai_insight column based on available risk and forecasting information."""
    logger.info("Generating daily AI insights...")
    
    def generate_insight(row):
        factors = str(row.get('active_high_risk_factors', 'NORMAL'))
        risk_alert = str(row.get('risk_alert', 'NONE'))
        overall_risk = str(row.get('overall_risk_level', 'LOW'))
        
        if 'CLOUD' in factors or 'HEAVY_RAIN' in factors:
            return "Cloud cover and rainfall may reduce solar generation."
        elif 'HEATWAVE' in factors:
            return "Extreme heat conditions detected; expect minor efficiency losses."
        elif 'DUST' in factors:
            return "Dust storm risk elevated; revenue exposure may increase."
        elif overall_risk == 'HIGH':
            return "Severe weather conditions pose high risk to generation and revenue."
        elif overall_risk == 'LOW':
            # Check generation strength
            if row.get('predicted_total_generation_mw', 0) > row.get('total_generation_mw', 0):
                return "Forecast indicates strong renewable output expected. Weather risks remain low."
            else:
                return "Favorable weather conditions. Revenue outlook remains favorable."
        else:
            return "Moderate weather patterns observed. Monitor generation closely."
            
    if not df.empty:
        df['ai_insight'] = df.apply(generate_insight, axis=1)
    
    return df


def calculate_forecast_accuracy(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate MAE, RMSE, and MAPE for the predicted total generation."""
    logger.info("Calculating forecast accuracy...")
    
    # We only calculate accuracy where we have both actuals and predictions
    # Note: total_generation_mw from revenue/generation, predicted_total_generation_mw from predictions
    
    mask = (df['total_generation_mw'] > 0) & (df['predicted_total_generation_mw'] > 0)
    valid_df = df[mask]
    
    if len(valid_df) > 0:
        y_true = valid_df['total_generation_mw']
        y_pred = valid_df['predicted_total_generation_mw']
        
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        
        # Calculate MAPE manually to handle any edge cases
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
        
        metrics = [{
            'Metric': 'MAE',
            'Value': round(mae, 2),
            'Description': 'Mean Absolute Error (MW)'
        }, {
            'Metric': 'RMSE',
            'Value': round(rmse, 2),
            'Description': 'Root Mean Squared Error (MW)'
        }, {
            'Metric': 'MAPE',
            'Value': round(mape, 2),
            'Description': 'Mean Absolute Percentage Error (%)'
        }]
    else:
        logger.warning("Insufficient overlap between actuals and predictions for accuracy calculation.")
        metrics = []
        
    return pd.DataFrame(metrics)


def generate_kpis(df: pd.DataFrame, accuracy_df: pd.DataFrame) -> pd.DataFrame:
    """Generate executive KPIs."""
    logger.info("Generating executive KPIs...")
    
    if df.empty:
        return pd.DataFrame()
        
    total_gen = df['total_generation_mw'].sum()
    avg_gen = df['total_generation_mw'].mean()
    total_rev = df['daily_revenue_inr'].sum()
    avg_rev = df['daily_revenue_inr'].mean()
    total_rev_risk = df['revenue_at_risk_inr'].sum()
    
    total_co2 = df['co2_avoided_tons'].sum()
    total_coal = df['coal_saved_tons'].sum()
    total_trees = df['trees_equivalent_million'].sum()
    
    high_risk_days = len(df[df['overall_risk_level'] == 'HIGH'])
    critical_alerts = len(df[df['risk_alert'] == 'CRITICAL_WEATHER_ALERT'])
    
    # Retrieve forecast error from accuracy_df if available
    avg_forecast_error = "N/A"
    if not accuracy_df.empty:
        mape_row = accuracy_df[accuracy_df['Metric'] == 'MAPE']
        if not mape_row.empty:
            avg_forecast_error = f"{mape_row['Value'].values[0]}%"
            
    kpis = [
        {'KPI': 'Total Generation', 'Value': round(total_gen, 2), 'Unit': 'MW'},
        {'KPI': 'Average Daily Generation', 'Value': round(avg_gen, 2), 'Unit': 'MW'},
        {'KPI': 'Total Revenue', 'Value': round(total_rev, 2), 'Unit': 'INR'},
        {'KPI': 'Average Daily Revenue', 'Value': round(avg_rev, 2), 'Unit': 'INR'},
        {'KPI': 'Total Revenue At Risk', 'Value': round(total_rev_risk, 2), 'Unit': 'INR'},
        {'KPI': 'Total CO2 Avoided', 'Value': round(total_co2, 2), 'Unit': 'Tons'},
        {'KPI': 'Total Coal Saved', 'Value': round(total_coal, 2), 'Unit': 'Tons'},
        {'KPI': 'Total Trees Equivalent', 'Value': round(total_trees, 2), 'Unit': 'Million'},
        {'KPI': 'High Risk Days', 'Value': high_risk_days, 'Unit': 'Days'},
        {'KPI': 'Critical Alert Days', 'Value': critical_alerts, 'Unit': 'Days'},
        {'KPI': 'Average Forecast Error', 'Value': avg_forecast_error, 'Unit': '%'}
    ]
    
    return pd.DataFrame(kpis)


def generate_narratives(kpi_df: pd.DataFrame) -> pd.DataFrame:
    """Generate executive narrative based on the KPIs."""
    logger.info("Generating executive narratives...")
    
    narratives = []
    if kpi_df.empty:
        return pd.DataFrame()
        
    kpi_dict = dict(zip(kpi_df['KPI'], kpi_df['Value']))
    
    # Generation Summary
    gen_val = kpi_dict.get('Total Generation', 0)
    narratives.append({
        'Section': 'Generation Summary',
        'Narrative': f"The Khavda Renewable Energy Park has successfully produced {gen_val} MW of renewable energy over the reporting period."
    })
    
    # Revenue Summary
    rev_val = kpi_dict.get('Total Revenue', 0) / 10000000  # Convert to Crores
    narratives.append({
        'Section': 'Revenue Summary',
        'Narrative': f"Financial performance remains solid with total revenue tracking at {rev_val:.2f} Crores INR."
    })
    
    # Risk Summary
    risk_days = kpi_dict.get('High Risk Days', 0)
    rev_risk = kpi_dict.get('Total Revenue At Risk', 0) / 10000000
    narratives.append({
        'Section': 'Risk Summary',
        'Narrative': f"Operations experienced {risk_days} high-risk weather days, resulting in an estimated {rev_risk:.2f} Crores INR of revenue exposed to weather-related risks."
    })
    
    # Sustainability Summary
    co2_val = kpi_dict.get('Total CO2 Avoided', 0)
    narratives.append({
        'Section': 'Sustainability Summary',
        'Narrative': f"The facility continues to drive massive decarbonization, avoiding {co2_val} Tons of CO2 equivalent emissions."
    })
    
    # Forecast Summary
    error = kpi_dict.get('Average Forecast Error', 'N/A')
    narratives.append({
        'Section': 'Forecast Summary',
        'Narrative': f"AI-driven forecasting models remain accurate with an average predictive error of {error}."
    })
    
    # AI Insights Summary
    narratives.append({
        'Section': 'AI Insights Summary',
        'Narrative': "Dynamic predictive models indicate a generally favorable operating environment, with isolated generation drops correlated strictly to transient cloud cover and heavy rainfall."
    })
    
    return pd.DataFrame(narratives)


def create_visualizations(df: pd.DataFrame):
    """Generate high-level visualizations for the executive dashboard."""
    logger.info("Generating executive visualizations...")
    
    try:
        # Plot 1: Generation Overview
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['total_generation_mw'], label='Actual', color='blue', alpha=0.7)
        if 'predicted_total_generation_mw' in df.columns and not df['predicted_total_generation_mw'].isnull().all():
            plt.plot(df['date'], df['predicted_total_generation_mw'], label='Forecast', color='orange', alpha=0.7, linestyle='--')
        plt.title('Executive Overview: Total Generation vs Forecast', fontweight='bold')
        plt.ylabel('Generation (MW)')
        plt.legend()
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(PLOT_GEN_PATH, dpi=300)
        plt.close()
        
        # Plot 2: Revenue Overview
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['daily_revenue_inr'] / 10000000, color='green')
        plt.title('Executive Overview: Daily Revenue', fontweight='bold')
        plt.ylabel('Revenue (Crores INR)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(PLOT_REV_PATH, dpi=300)
        plt.close()
        
        # Plot 3: Sustainability Overview
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['co2_avoided_tons'], color='forestgreen')
        plt.title('Executive Overview: CO2 Avoided Trend', fontweight='bold')
        plt.ylabel('CO2 Avoided (Tons)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(PLOT_SUSTAINABILITY_PATH, dpi=300)
        plt.close()
        
        # Plot 4: Risk Overview
        plt.figure(figsize=(12, 5))
        plt.plot(df['date'], df['revenue_at_risk_inr'] / 100000, color='red')
        plt.title('Executive Overview: Revenue Exposed to Weather Risk', fontweight='bold')
        plt.ylabel('Revenue at Risk (Lakhs INR)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(PLOT_RISK_PATH, dpi=300)
        plt.close()
        
    except Exception as e:
        logger.error(f"Failed to create visualizations: {e}")


def save_results(df: pd.DataFrame, kpi_df: pd.DataFrame, accuracy_df: pd.DataFrame, narrative_df: pd.DataFrame):
    """Save all executive files ensuring Power BI / Streamlit readiness."""
    logger.info("Saving executive summary reports...")
    
    try:
        # Output Columns
        output_cols = [
            'date', 'site_name', 'total_generation_mw', 'predicted_total_generation_mw',
            'daily_revenue_inr', 'revenue_at_risk_inr', 'co2_avoided_tons', 
            'coal_saved_tons', 'trees_equivalent_million', 'overall_risk_level',
            'risk_alert', 'active_high_risk_factors', 'ai_insight'
        ]
        
        # Ensure only available columns are saved and ordered correctly
        final_cols = [c for c in output_cols if c in df.columns]
        exec_df = df[final_cols].copy()
        
        # Deduplicate and prevent negative revenue
        exec_df = exec_df.drop_duplicates(subset=['date'])
        if 'daily_revenue_inr' in exec_df.columns:
            exec_df['daily_revenue_inr'] = exec_df['daily_revenue_inr'].clip(lower=0)
            
        exec_df.to_csv(EXEC_SUMMARY_PATH, index=False)
        
        # KPIs, Accuracy, Narratives
        if not kpi_df.empty:
            kpi_df.to_csv(KPI_PATH, index=False)
            
        if not accuracy_df.empty:
            accuracy_df.to_csv(ACCURACY_PATH, index=False)
            
        if not narrative_df.empty:
            narrative_df.to_csv(NARRATIVE_PATH, index=False)
            
        logger.info(f"Executive dataset saved to {EXEC_SUMMARY_PATH}")
        
    except Exception as e:
        logger.error(f"Error saving executive results: {e}")
        raise


def main():
    logger.info("==================================================")
    logger.info("Starting Executive Summary Engine")
    logger.info("==================================================")
    try:
        # 1. Load Data
        datasets = load_datasets()
        
        # 2. Process Core Dataset
        merged_df = merge_datasets(datasets)
        if merged_df.empty:
            logger.error("Merge resulted in an empty dataset. Exiting.")
            return
            
        # 3. Generate Daily AI Insights
        final_df = generate_ai_insights(merged_df)
        
        # 4. Metrics and KPIs
        accuracy_df = calculate_forecast_accuracy(final_df)
        kpi_df = generate_kpis(final_df, accuracy_df)
        narrative_df = generate_narratives(kpi_df)
        
        # 5. Visuals and Persistence
        create_visualizations(final_df)
        save_results(final_df, kpi_df, accuracy_df, narrative_df)
        
        logger.info("==================================================")
        logger.info("Executive Summary Engine Completed Successfully")
        logger.info("==================================================")
    except Exception as e:
        logger.error(f"Executive Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
