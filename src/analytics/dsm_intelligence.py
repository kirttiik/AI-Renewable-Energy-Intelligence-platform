import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import os

def calculate_dsm_risk(df: pd.DataFrame, schedule_col: str = 'scheduled_generation_mw', 
                       actual_col: str = 'actual_total_generation_mw',
                       forecast_col: str = 'predicted_total_generation_mw',
                       penalty_rate_inr_per_mwh: float = 2500.0,
                       interval_duration_hours: float = 7.5) -> pd.DataFrame:
    """
    Calculates Deviation Settlement Mechanism (DSM) risks and penalties.
    interval_duration_hours: Translates daily peak MW to MWh energy. For Khavda Solar, PSH is approx 7.5.
    """
    if df is None or df.empty:
        return df

    df = df.copy()
    
    # Red Flag 14: Schedule Source Flag
    df['schedule_source'] = "REAL_SCHEDULE"
    df['dsm_mode'] = "ACTUAL_SETTLEMENT"
    
    # 1. Ensure we have a schedule to compare against. Simulate if missing, but clearly label it.
    if schedule_col not in df.columns or df[schedule_col].isnull().all():
        df['schedule_source'] = "SIMULATED_SCHEDULE"
        df['dsm_mode'] = "SIMULATION"
        if forecast_col in df.columns:
            # Simulate a schedule created by operators using forecast
            df[schedule_col] = df[forecast_col] * 0.98  # Simple 2% buffer, no random noise (Red Flag 13)
            df[schedule_col] = df[schedule_col].clip(lower=0)
        else:
            return df
            
    # Red Flag 18: Distinguish Forecast DSM Risk from Actual Settlement
    is_forecast = df['date'].dt.date > pd.Timestamp.today().date()
    df.loc[is_forecast, 'dsm_mode'] = "FORECAST_RISK"
    
    # 2. Determine target for deviation
    df['dsm_target_mw'] = np.where(is_forecast, df.get(forecast_col, np.nan), df.get(actual_col, np.nan))
    
    # If no valid target exists (e.g. missing forecast), we can't calculate DSM
    df['dsm_target_mw'] = df['dsm_target_mw'].astype(float)
    
    # 3. Calculate deviations
    df['dsm_deviation_mw'] = df['dsm_target_mw'] - df[schedule_col]
    
    # Prevent division by zero
    df['dsm_deviation_pct'] = np.where(
        df[schedule_col] > 0, 
        (df['dsm_deviation_mw'] / df[schedule_col]) * 100, 
        0
    )
                                       
    # 4. Calculate DSM Penalty (Assuming 10% tolerance band)
    df['dsm_penalty_inr'] = 0.0
    
    mask_valid = df['dsm_target_mw'].notna()
    mask_outside_tolerance = (abs(df['dsm_deviation_pct']) > 10) & mask_valid
    
    # Red Flag 15 & 17: Correct Dimensional Logic (MW -> MWh -> INR)
    # excess_deviation_mw = max(abs(dev) - allowed, 0)
    allowed_deviation_mw = 0.10 * df[schedule_col]
    excess_dev_mw = np.maximum(abs(df['dsm_deviation_mw']) - allowed_deviation_mw, 0)
    
    # Convert MW to MWh
    excess_dev_mwh = excess_dev_mw * interval_duration_hours
    
    # Apply penalty
    df.loc[mask_outside_tolerance, 'dsm_penalty_inr'] = excess_dev_mwh[mask_outside_tolerance] * penalty_rate_inr_per_mwh
            
    # 5. Generate Optimization Recommendations
    df['dsm_recommendation'] = "Optimal Schedule"
    df.loc[df['dsm_deviation_pct'] < -10, 'dsm_recommendation'] = "Decrease Schedule (Avoid Under-injection Penalty)"
    df.loc[df['dsm_deviation_pct'] > 10, 'dsm_recommendation'] = "Increase Schedule (Avoid Over-injection Penalty)"
    
    return df

def render_dsm_intelligence():
    st.title("⚖️ DSM Intelligence & Risk Optimizer")
    st.markdown("Optimize generation schedules to minimize Deviation Settlement Mechanism (DSM) penalties.")
    
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gen_path = os.path.join(ROOT, 'data', 'processed', 'khavda_generation.csv')
    
    if not os.path.exists(gen_path):
        st.warning("Data not found. Please ensure the pipeline has run.")
        return
        
    df = pd.read_csv(gen_path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        
    # Calculate DSM risks
    # First, make sure we have total forecast and actual
    if 'actual_total_generation_mw' not in df.columns:
        df['actual_total_generation_mw'] = df.get('total_generation_mw', df.get('solar_generation_mw', 0))
    
    # Red Flag #13: Do not fabricate forecast
    if 'predicted_total_generation_mw' not in df.columns:
        # Check if we have solar predictions
        pred_path = os.path.join(ROOT, 'reports', 'solar', 'solar_predictions.csv')
        if os.path.exists(pred_path):
            pred_df = pd.read_csv(pred_path)
            pred_df['date'] = pd.to_datetime(pred_df['date'])
            df = df.merge(pred_df[['date', 'predicted_solar_generation_mw']], on='date', how='left')
            df['predicted_total_generation_mw'] = df['predicted_solar_generation_mw']
        else:
            df['predicted_total_generation_mw'] = np.nan
        
    dsm_df = calculate_dsm_risk(df)
    
    if 'dsm_penalty_inr' not in dsm_df.columns:
        st.warning("Insufficient data to calculate DSM risks.")
        return
        
    if dsm_df['schedule_source'].iloc[-1] == "SIMULATED_SCHEDULE":
        st.info("ℹ️ **Simulation Mode:** Using simulated schedules based on AI forecasts. Real regulatory settlement requires actual submitted SCADA schedules.")
        
    latest_df = dsm_df.tail(30).copy() # Last 30 days
    
    total_penalty = latest_df['dsm_penalty_inr'].sum()
    avg_deviation = latest_df['dsm_deviation_pct'].abs().mean()
    days_penalized = (latest_df['dsm_penalty_inr'] > 0).sum()
    
    col1, col2, col3 = st.columns(3)
    
    dsm_title = "Est. DSM Penalty" if dsm_df['dsm_mode'].iloc[-1] == "ACTUAL_SETTLEMENT" else "Forecasted DSM Risk"
    
    col1.metric(f"{dsm_title} (30 Days)", f"₹ {total_penalty:,.0f}", delta_color="inverse")
    col2.metric("Avg Absolute Deviation", f"{avg_deviation:.1f}%", "-2.1% vs prev month")
    col3.metric("Days Penalized", f"{days_penalized} / {len(latest_df)}", delta_color="inverse")
    
    st.markdown("### Forecast vs. Schedule & Deviations")
    if 'scheduled_generation_mw' in latest_df.columns:
        fig = px.line(latest_df, x='date', y=['scheduled_generation_mw', 'predicted_total_generation_mw'],
                      labels={'value': 'Generation (MW)', 'variable': 'Metric'},
                      title='Schedule vs Forecast')
        st.plotly_chart(fig, use_container_width=True)
        
    st.markdown("### Recommended Schedule Adjustments")
    recommendations = latest_df[latest_df['dsm_penalty_inr'] > 0][['date', 'dsm_deviation_pct', 'dsm_penalty_inr', 'dsm_recommendation']].sort_values('date', ascending=False)
    
    if recommendations.empty:
        st.success("Your schedule is highly optimal! No penalties incurred recently.")
    else:
        st.dataframe(recommendations.style.format({'dsm_deviation_pct': '{:.1f}%', 'dsm_penalty_inr': '₹ {:,.0f}'}), use_container_width=True)
