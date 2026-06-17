"""
Khavda Renewable Energy Digital Twin - Executive Dashboard
Built with Streamlit, Pandas, and Plotly.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="Khavda Digital Twin",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    .reportview-container .main .block-container { padding-top: 2rem; }
    h1, h2, h3 { color: #1E3D59; }
    .stMetric { background-color: #F5F7FA; padding: 15px; border-radius: 5px; border-left: 5px solid #1E3D59; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# DATA LOADING UTILITIES
# ==========================================
def load_data(paths):
    """Load a CSV file from the first valid path found."""
    for path in paths:
        if os.path.exists(path):
            try:
                df = pd.read_csv(path)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                return df
            except Exception as e:
                st.warning(f"Error loading {path}: {e}")
    return pd.DataFrame()

def get_data_sources():
    """Resolve paths to datasets, handling the recent folder restructure."""
    ROOT = os.path.dirname(os.path.abspath(__file__))
    
    return {
        'exec_summary': load_data([
            os.path.join(ROOT, 'reports', 'executive', 'executive_summary.csv'),
            os.path.join(ROOT, 'reports', 'executive_summary.csv')
        ]),
        'exec_kpis': load_data([
            os.path.join(ROOT, 'reports', 'executive', 'executive_dashboard_kpis.csv'),
            os.path.join(ROOT, 'reports', 'executive_dashboard_kpis.csv')
        ]),
        'forecast_accuracy': load_data([
            os.path.join(ROOT, 'reports', 'executive', 'forecast_accuracy_summary.csv'),
            os.path.join(ROOT, 'reports', 'forecast_accuracy_summary.csv')
        ]),
        'model_comp': load_data([
            os.path.join(ROOT, 'reports', 'explainability', 'model_comparison.csv'),
            os.path.join(ROOT, 'reports', 'model_comparison.csv')
        ]),
        'explain_kpis': load_data([
            os.path.join(ROOT, 'reports', 'explainability', 'explainability_kpis.csv'),
            os.path.join(ROOT, 'reports', 'explainability_kpis.csv')
        ]),
        'revenue': load_data([
            os.path.join(ROOT, 'data', 'processed', 'revenue_analytics.csv')
        ]),
        'weather_risk': load_data([
            os.path.join(ROOT, 'data', 'processed', 'weather_risk_analytics.csv')
        ]),
        'carbon': load_data([
            os.path.join(ROOT, 'data', 'processed', 'carbon_offset_analytics.csv')
        ]),
        'solar_pred': load_data([
            os.path.join(ROOT, 'reports', 'solar', 'solar_predictions.csv'),
            os.path.join(ROOT, 'reports', 'solar_predictions.csv')
        ]),
        'wind_pred': load_data([
            os.path.join(ROOT, 'reports', 'wind', 'wind_predictions.csv'),
            os.path.join(ROOT, 'reports', 'wind_predictions.csv')
        ]),
        'total_pred': load_data([
            os.path.join(ROOT, 'reports', 'total_output', 'total_output_predictions.csv'),
            os.path.join(ROOT, 'reports', 'total_output_predictions.csv')
        ]),
        'explain_insights': load_data([
            os.path.join(ROOT, 'reports', 'explainability', 'executive_ai_insights.csv')
        ]),
        'total_metrics': load_data([
            os.path.join(ROOT, 'reports', 'total_output', 'total_output_metrics.csv')
        ]),
        'shap_solar_rank': load_data([
            os.path.join(ROOT, 'reports', 'shap_feature_ranking_solar.csv')
        ])
    }

def safe_number(value):
    try:
        return float(value)
    except:
        return 0

data = get_data_sources()

# ==========================================
# SIDEBAR NAVIGATION
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3254/3254095.png", width=100) # Placeholder Logo
    st.title("Khavda Digital Twin")
    st.markdown("---")
    
    sections = [
        "🏠 Executive Overview",
        "⚡ Generation Analytics",
        "🔮 Forecasting",
        "🌱 Carbon Analytics",
        "⚠️ Weather Risk",
        "💰 Revenue Analytics",
        "🧠 AI Explainability",
        "🔬 SHAP Analytics"
    ]
    selection = st.radio("Navigation", sections)
    
    st.markdown("---")
    global_time_horizon = st.radio(
        "⏱️ Time Horizon",
        ["All Time", "Yesterday", "Today", "Tomorrow"],
        index=0,
        help="Filters data relative to the most recent date available in the dataset."
    )
    
    st.markdown("---")
    st.markdown("v1.0.0 | Production")

def filter_by_time_horizon(df, horizon):
    """Filters a DataFrame by date relative to its own max date."""
    if df is None or df.empty or 'date' not in df.columns:
        return df
    
    # Ensure datetime without overwriting original if we can avoid warnings
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
        
    max_date = df['date'].max()
    if pd.isna(max_date):
        return df
        
    if horizon == "All Time":
        return df
    elif horizon == "Today":
        target_date = max_date
    elif horizon == "Yesterday":
        target_date = max_date - pd.Timedelta(days=1)
    elif horizon == "Tomorrow":
        target_date = max_date + pd.Timedelta(days=1)
    else:
        return df
        
    return df[df['date'].dt.date == target_date.date()]

# ==========================================
# PAGE ROUTING & RENDER FUNCTIONS
# ==========================================

def render_executive_overview():
    st.title("🏠 Executive Overview")
    st.markdown("High-level consolidation of Generation, Financials, Sustainability, and Risk.")
    
    df_exec = filter_by_time_horizon(data['exec_summary'], global_time_horizon)
    
    if not df_exec.empty:
        total_gen = df_exec['total_generation_mw'].sum()
        total_rev = df_exec['daily_revenue_inr'].sum()
        co2_avoided = df_exec['co2_avoided_tons'].sum()
        
        if len(df_exec) > 0 and 'predicted_total_generation_mw' in df_exec.columns:
            avg_error = (df_exec['total_generation_mw'] - df_exec['predicted_total_generation_mw']).abs().mean()
            avg_error_str = f"{avg_error:.2f} MW"
        else:
            avg_error_str = "N/A"
            
        coal_saved = df_exec['coal_saved_tons'].sum()
        trees = df_exec['trees_equivalent_million'].sum()
        crit_days = (df_exec['overall_risk_level'] == 'CRITICAL').sum()
        high_days = (df_exec['overall_risk_level'] == 'HIGH').sum()
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Generation", f"{safe_number(total_gen):,.0f} MW")
        col2.metric("Total Revenue", f"₹ {safe_number(total_rev):,.0f}")
        col3.metric("CO₂ Avoided", f"{safe_number(co2_avoided):,.0f} Tons")
        col4.metric("Average Forecast Error", avg_error_str)
        
        st.markdown("<br>", unsafe_allow_html=True)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Coal Saved", f"{safe_number(coal_saved):,.0f} Tons")
        col2.metric("Trees Equivalent", f"{safe_number(trees):,.0f} M")
        col3.metric("Critical Risk Days", f"{crit_days}")
        col4.metric("High Risk Days", f"{high_days}")
    else:
        st.warning("No Executive data available for the selected Time Horizon.")
        
    st.markdown("---")
    st.subheader("Executive Summary Table")
    
    if not df_exec.empty:
        st.dataframe(df_exec.tail(30).style.highlight_max(axis=0))
    else:
        st.warning("Executive Summary dataset is missing or empty for this timeframe.")

def render_generation_analytics():
    st.title("⚡ Generation Analytics")
    st.markdown("Detailed breakdown of Solar, Wind, and Total Energy Generation.")
    
    df_rev = filter_by_time_horizon(data['revenue'], global_time_horizon)
    if not df_rev.empty:
        # Solar vs Wind Generation Trend
        fig = px.line(df_rev, x='date', y=['solar_generation_mw', 'wind_generation_mw'],
                      labels={'value': 'Generation (MW)', 'date': 'Date', 'variable': 'Source'},
                      title='Solar vs Wind Generation Trend', color_discrete_sequence=['orange', 'blue'])
        st.plotly_chart(fig, use_container_width=True)
        
        # Total Generation
        fig2 = px.area(df_rev, x='date', y='total_generation_mw',
                       title='Total Combined Generation Trend', color_discrete_sequence=['green'])
        st.plotly_chart(fig2, use_container_width=True)
        
        # Monthly Aggregation
        df_rev['month'] = df_rev['date'].dt.to_period('M')
        monthly = df_rev.groupby('month')[['solar_generation_mw', 'wind_generation_mw']].sum().reset_index()
        monthly['month'] = monthly['month'].astype(str)
        fig3 = px.bar(monthly, x='month', y=['solar_generation_mw', 'wind_generation_mw'],
                      title='Monthly Aggregated Generation', barmode='group')
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.warning("Revenue/Generation dataset is missing.")

def render_forecasting():
    st.title("🔮 Forecasting")
    st.markdown("AI-driven predictions for energy generation.")
    
    df_total = filter_by_time_horizon(data['total_pred'], global_time_horizon)
    if not df_total.empty:
        st.subheader("Total Output Forecast")
        fig = go.Figure()
        
        # Try to find actual columns (handling different naming conventions)
        actual_col = 'actual_total_generation_mw' if 'actual_total_generation_mw' in df_total.columns else 'actual_generation_mw'
        pred_col = 'predicted_total_generation_mw' if 'predicted_total_generation_mw' in df_total.columns else 'predicted_generation_mw'
        
        if actual_col in df_total.columns:
            fig.add_trace(go.Scatter(x=df_total['date'], y=df_total[actual_col], name="Actual Generation", mode='lines'))
        if pred_col in df_total.columns:
            fig.add_trace(go.Scatter(x=df_total['date'], y=df_total[pred_col], name="Predicted Generation", mode='lines', line=dict(dash='dash')))
            
        fig.update_layout(title="Total Output: Actual vs Predicted", yaxis_title="Generation (MW)")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Total prediction dataset missing.")
        
    col1, col2 = st.columns(2)
    with col1:
        df_solar = filter_by_time_horizon(data['solar_pred'], global_time_horizon)
        if not df_solar.empty:
            st.subheader("Solar Forecast Metrics")
            st.dataframe(df_solar.head(10))
    with col2:
        df_wind = filter_by_time_horizon(data['wind_pred'], global_time_horizon)
        if not df_wind.empty:
            st.subheader("Wind Forecast Metrics")
            st.dataframe(df_wind.head(10))
            
    if not data['forecast_accuracy'].empty:
        st.markdown("---")
        st.subheader("Forecast Accuracy Metrics")
        st.table(data['forecast_accuracy'])

def render_carbon_analytics():
    st.title("🌱 Carbon Analytics")
    st.markdown("Sustainability tracking and environmental impact.")
    
    df_carb = filter_by_time_horizon(data['carbon'], global_time_horizon)
    if not df_carb.empty:
        total_co2 = df_carb['co2_avoided_tons'].sum()
        total_coal = df_carb['coal_saved_tons'].sum()
        total_trees = df_carb['trees_equivalent_million'].sum()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("Total CO₂ Avoided", f"{safe_number(total_co2):,.2f} Tons")
        col2.metric("Total Coal Saved", f"{safe_number(total_coal):,.2f} Tons")
        col3.metric("Trees Equivalent", f"{safe_number(total_trees):,.2f} Million")
        
        fig = px.area(df_carb, x='date', y='co2_avoided_tons', title="CO₂ Avoided Over Time", color_discrete_sequence=['forestgreen'])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Carbon Analytics dataset is missing.")

def render_weather_risk():
    st.title("⚠️ Weather Risk")
    st.markdown("Analysis of extreme weather events and their operational impact.")
    
    df_risk = filter_by_time_horizon(data['weather_risk'], global_time_horizon)
    if not df_risk.empty:
        counts = df_risk['overall_risk_level'].value_counts()
        
        col1, col2, col3 = st.columns(3)
        col1.metric("High Risk Days", int(counts.get('HIGH', 0)))
        col2.metric("Medium Risk Days", int(counts.get('MEDIUM', 0)))
        col3.metric("Low Risk Days", int(counts.get('LOW', 0)))
        
        fig = px.pie(values=counts.values, names=counts.index, title="Risk Level Distribution", color=counts.index,
                     color_discrete_map={'LOW':'green', 'MEDIUM':'orange', 'HIGH':'red'})
        st.plotly_chart(fig, use_container_width=True)
        
        # Risk Categories Breakdown
        factors = df_risk['active_high_risk_factors'].value_counts().reset_index()
        factors.columns = ['Risk Factor', 'Count']
        fig2 = px.bar(factors, x='Risk Factor', y='Count', title="Most Common Risk Factors", color='Count')
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Weather Risk dataset is missing.")

def render_revenue_analytics():
    st.title("💰 Revenue Analytics")
    st.markdown("Financial intelligence translating engineering output into monetary value.")
    
    df_rev = filter_by_time_horizon(data['revenue'], global_time_horizon)
    if not df_rev.empty:
        total_rev = df_rev['daily_revenue_inr'].sum()
        avg_rev = df_rev['daily_revenue_inr'].mean()
        risk_rev = df_rev.get('revenue_at_risk_inr', pd.Series(0)).sum()
        ann_rev = avg_rev * 365
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Revenue (INR)", f"₹ {safe_number(total_rev):,.0f}")
        col2.metric("Avg Daily Revenue", f"₹ {safe_number(avg_rev):,.0f}")
        col3.metric("Revenue At Risk", f"₹ {safe_number(risk_rev):,.0f}")
        col4.metric("Annualized Revenue", f"₹ {safe_number(ann_rev):,.0f}")
        
        fig = px.line(df_rev, x='date', y='daily_revenue_inr', title="Daily Revenue Trend", color_discrete_sequence=['teal'])
        st.plotly_chart(fig, use_container_width=True)
        
        fig2 = px.area(df_rev, x='date', y=['solar_revenue_inr', 'wind_revenue_inr'], title="Revenue Breakdown: Solar vs Wind")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.warning("Revenue Analytics dataset is missing.")

def render_explainability():
    st.title("🧠 AI Explainability")
    st.markdown("Demystifying machine learning predictions and feature importance.")
    
    df_kpi = data['explain_kpis']
    if not df_kpi.empty:
        kpi_dict = df_kpi.set_index('KPI').to_dict('index')
        
        def format_explain_kpi(kpi_name):
            if kpi_name in kpi_dict:
                row = kpi_dict[kpi_name]
                val = row['Value']
                pct = row.get('Importance_Percentage', None)
                if pd.notna(pct):
                    return f"{val} ({pct:.2f}%)"
                return str(val)
            return "N/A"
            
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Most Influential Feature", format_explain_kpi('Most Influential Feature'))
        col2.metric("Most Explainable Model", format_explain_kpi('Most Explainable Model'))
        col3.metric("Dominant Renewable Driver", format_explain_kpi('Dominant Renewable Driver'))
        
        acc_df = data.get('total_metrics', pd.DataFrame())
        if not acc_df.empty and 'R2_Score' in acc_df.columns:
            r2_val = float(acc_df['R2_Score'].iloc[0]) * 100
            col4.metric("Forecast Accuracy", f"Total Output ({r2_val:.2f}%)")
        else:
            col4.metric("Forecast Accuracy", "N/A")
    else:
        st.warning("Explainability KPIs dataset missing.")
        
    df_comp = data['model_comp']
    if not df_comp.empty:
        st.markdown("---")
        st.subheader("Model Feature Importance Comparison")
        
        friendly_labels = {
            'wind_speed_ms': 'Wind Speed',
            'solar_radiation_kwh_m2_day': 'Solar Radiation',
            'cloud_cover_pct': 'Cloud Cover',
            'temperature_c': 'Temperature'
        }
        
        if 'Top Driver' in df_comp.columns and 'Importance' in df_comp.columns:
            df_comp['Feature Label'] = df_comp['Top Driver'].map(lambda x: friendly_labels.get(x, x))
            df_comp['Importance_Numeric'] = df_comp['Importance'].astype(float) * 100
            df_comp = df_comp.sort_values('Importance_Numeric', ascending=False)
            
            fig = px.bar(df_comp, x='Model', y='Importance_Numeric', color='Feature Label', 
                         title="Dominant Feature per Model", barmode='group', 
                         labels={'Importance_Numeric': 'Importance %'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_comp[['Model', 'Top Driver', 'Importance %', 'Business Meaning']], use_container_width=True)
        else:
            st.warning("Updated Model Comparison data not yet available. Please re-run the pipeline.")
    
    df_insights = data['explain_insights']
    if not df_insights.empty:
        st.markdown("---")
        st.subheader("Executive AI Insights")
        st.table(df_insights)

def render_shap_analytics():
    st.title("🔬 SHAP Analytics")
    st.markdown("Advanced Model Explainability using SHapley Additive exPlanations.")
    
    shap_rank_df = data.get('shap_solar_rank', pd.DataFrame())
    ROOT = os.path.dirname(os.path.abspath(__file__))
    shap_plot_path = os.path.join(ROOT, 'reports', 'shap_summary_solar.png')
    
    if shap_rank_df.empty:
        st.warning("SHAP feature ranking data not available. Please run the SHAP pipeline.")
        return
        
    # Calculate Contribution Percentage
    total_shap = shap_rank_df['Mean_Absolute_SHAP'].sum()
    shap_rank_df['Contribution_Percentage'] = (shap_rank_df['Mean_Absolute_SHAP'] / total_shap) * 100
    
    # KPIs
    top_driver = shap_rank_df.iloc[0]['Feature']
    second_driver = shap_rank_df.iloc[1]['Feature'] if len(shap_rank_df) > 1 else "N/A"
    total_features = len(shap_rank_df)
    
    # Friendly labels
    friendly_labels = {
        'cloud_cover_pct': 'Cloud Cover',
        'solar_radiation_kwh_m2_day': 'Solar Radiation',
        'temperature_c': 'Temperature',
        'humidity_pct': 'Humidity',
        'rainfall_mm': 'Rainfall',
        'wind_speed_ms': 'Wind Speed',
        'month': 'Month',
        'quarter': 'Quarter',
        'day_of_year': 'Day of Year',
        'week_of_year': 'Week of Year',
        'is_weekend': 'Is Weekend',
        'year': 'Year'
    }
    
    shap_rank_df['Feature'] = shap_rank_df['Feature'].map(lambda x: friendly_labels.get(x, x))
    top_driver_friendly = friendly_labels.get(top_driver, top_driver)
    second_driver_friendly = friendly_labels.get(second_driver, second_driver)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Top SHAP Driver", top_driver_friendly)
    col2.metric("Second Most Important Driver", second_driver_friendly)
    col3.metric("Total SHAP Features", total_features)
    
    st.markdown("---")
    st.subheader("Feature Ranking")
    
    # Format for display
    display_df = shap_rank_df[['Feature', 'Mean_Absolute_SHAP', 'Contribution_Percentage']].copy()
    display_df['Mean_Absolute_SHAP'] = display_df['Mean_Absolute_SHAP'].round(4)
    display_df['Contribution_Percentage'] = display_df['Contribution_Percentage'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(display_df, use_container_width=True)
    
    st.markdown("---")
    st.subheader("SHAP Summary Plot (Solar)")
    if os.path.exists(shap_plot_path):
        st.image(shap_plot_path, use_container_width=True)
    else:
        st.warning("SHAP summary plot not found.")
        
    st.markdown("---")
    st.subheader("Business Insights")
    insights = [
        "Cloud cover is the strongest driver of solar generation variability.",
        "Solar radiation remains a major positive contributor to generation output.",
        "Atmospheric conditions explain the majority of forecast variation."
    ]
    for insight in insights:
        st.markdown(f"- {insight}")

# ==========================================
# ROUTING LOGIC
# ==========================================
if selection == "🏠 Executive Overview":
    render_executive_overview()
elif selection == "⚡ Generation Analytics":
    render_generation_analytics()
elif selection == "🔮 Forecasting":
    render_forecasting()
elif selection == "🌱 Carbon Analytics":
    render_carbon_analytics()
elif selection == "⚠️ Weather Risk":
    render_weather_risk()
elif selection == "💰 Revenue Analytics":
    render_revenue_analytics()
elif selection == "🧠 AI Explainability":
    render_explainability()
elif selection == "🔬 SHAP Analytics":
    render_shap_analytics()

# Footer
st.markdown("---")
st.markdown("<div align='center'>Built for Khavda Renewable Energy Park Management Team</div>", unsafe_allow_html=True)
