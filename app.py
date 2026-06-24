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
    st.image("https://cdn-icons-png.flaticon.com/512/3254/3254095.png", width=100)
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
        "🔬 SHAP Analytics",
        "⚡ IEX Analytics",
        "🌐 Grid Intelligence",
    ]
    selection = st.radio("Navigation", sections)
    
    st.markdown("---")
    global_time_horizon = st.radio(
        "⏱️ Time Horizon",
        ["All Time", "Yesterday", "Today", "Tomorrow", "📅 Custom Range"],
        index=0,
        help="Filter data by time period. Custom Range lets you pick exact dates."
    )
    
    # Custom date range pickers (only shown when Custom Range is selected)
    custom_start_date = None
    custom_end_date   = None
    if global_time_horizon == "📅 Custom Range":
        import datetime as dt
        today_sys = dt.date.today()
        default_start = today_sys - dt.timedelta(days=30)
        date_range = st.date_input(
            "Select Date Range",
            value=(default_start, today_sys),
            min_value=dt.date(2021, 1, 1),
            max_value=today_sys + dt.timedelta(days=14),
            key="custom_date_range"
        )
        if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
            custom_start_date, custom_end_date = date_range
        elif isinstance(date_range, dt.date):
            custom_start_date = custom_end_date = date_range
    
    st.markdown("---")
    st.markdown("v1.0.0 | Production")

# Load hourly data
def load_hourly_data():
    ROOT = os.path.dirname(os.path.abspath(__file__))
    hourly_path = os.path.join(ROOT, 'data', 'raw', 'khavda_hourly.csv')
    if os.path.exists(hourly_path):
        df = pd.read_csv(hourly_path)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame()

hourly_data = load_hourly_data()

# Single-day horizons that should show hourly charts
SINGLE_DAY_HORIZONS = {"Yesterday", "Today", "Tomorrow"}

def filter_by_time_horizon(df, horizon, custom_start=None, custom_end=None):
    """Filters a DataFrame by date relative to the last actual historical observation."""
    if df is None or df.empty or 'date' not in df.columns:
        return df
    
    df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])

    # Custom Range handling
    if horizon == "📅 Custom Range":
        if custom_start and custom_end:
            start = pd.Timestamp(custom_start)
            end   = pd.Timestamp(custom_end)
            return df[(df['date'] >= start) & (df['date'] <= end)]
        return df

    # Find the true "Today" (last day of actual historical data)
    global_today = pd.to_datetime('today').normalize()
    
    if 'actual_total_generation_mw' in df.columns:
        hist_df = df.dropna(subset=['actual_total_generation_mw'])
        if not hist_df.empty:
            global_today = hist_df['date'].max()
    elif 'actual_solar_generation_mw' in df.columns:
        hist_df = df.dropna(subset=['actual_solar_generation_mw'])
        if not hist_df.empty:
            global_today = hist_df['date'].max()
    elif 'actual_wind_generation_mw' in df.columns:
        hist_df = df.dropna(subset=['actual_wind_generation_mw'])
        if not hist_df.empty:
            global_today = hist_df['date'].max()
    else:
        df_max = df['date'].max()
        if pd.notna(df_max) and df_max < global_today:
            global_today = df_max
            
    if horizon == "All Time":
        return df
    elif horizon == "Today":
        target_date = global_today
    elif horizon == "Yesterday":
        target_date = global_today - pd.Timedelta(days=1)
    elif horizon == "Tomorrow":
        target_date = global_today + pd.Timedelta(days=1)
    else:
        return df
        
    return df[df['date'].dt.date == target_date.date()]


def get_hourly_for_horizon(horizon, custom_start=None, custom_end=None):
    """Return hourly rows for the current time horizon."""
    if hourly_data.empty:
        return pd.DataFrame()
    
    hdf = hourly_data.copy()
    
    if horizon == "📅 Custom Range":
        if custom_start and custom_end:
            return hdf[(hdf['date'] >= custom_start) & (hdf['date'] <= custom_end)]
        return hdf
    
    # Determine reference date from system clock
    ref_today = pd.Timestamp.now().normalize().date()
    
    if horizon == "Today":
        target = ref_today
    elif horizon == "Yesterday":
        target = ref_today - pd.Timedelta(days=1)
    elif horizon == "Tomorrow":
        target = ref_today + pd.Timedelta(days=1)
    else:
        return hdf  # All Time — return all hourly data
    
    return hdf[hdf['date'] == target]


def render_hourly_charts(horizon, custom_start=None, custom_end=None):
    """Render hourly generation and weather charts for single-day views."""
    hdf = get_hourly_for_horizon(horizon, custom_start, custom_end)
    
    if hdf.empty:
        st.info("Hourly data not yet available. The pipeline will generate it on the next run.")
        return
    
    label = horizon if horizon != "📅 Custom Range" else f"{custom_start} → {custom_end}"
    st.subheader(f"⏰ Hourly Generation Breakdown — {label}")
    
    if horizon in SINGLE_DAY_HORIZONS or (horizon == "📅 Custom Range" and custom_start == custom_end):
        # Single day — show by hour on x-axis
        fig_hourly = go.Figure()
        fig_hourly.add_trace(go.Bar(
            x=hdf['hour'], y=hdf['solar_generation_mw'],
            name='Solar (MW)', marker_color='#FFB347'
        ))
        fig_hourly.add_trace(go.Bar(
            x=hdf['hour'], y=hdf['wind_generation_mw'],
            name='Wind (MW)', marker_color='#5B9BD5'
        ))
        fig_hourly.update_layout(
            barmode='stack',
            xaxis_title='Hour of Day',
            yaxis_title='Generation (MW)',
            title='Hourly Solar + Wind Generation Profile',
            xaxis=dict(tickmode='linear', tick0=0, dtick=1),
            legend=dict(orientation='h', yanchor='bottom', y=1.02),
            height=400
        )
        st.plotly_chart(fig_hourly, use_container_width=True)
        
        # Weather conditions
        col1, col2 = st.columns(2)
        with col1:
            fig_solar_rad = px.area(
                hdf, x='hour', y='solar_radiation_wm2',
                title='Hourly Solar Irradiance (W/m²)',
                color_discrete_sequence=['#FF8C00']
            )
            fig_solar_rad.update_layout(height=300, xaxis_title='Hour')
            st.plotly_chart(fig_solar_rad, use_container_width=True)
        with col2:
            fig_wind = px.line(
                hdf, x='hour', y='wind_speed_ms',
                title='Hourly Wind Speed (m/s)',
                color_discrete_sequence=['#00BFFF']
            )
            fig_wind.update_layout(height=300, xaxis_title='Hour')
            st.plotly_chart(fig_wind, use_container_width=True)
        
        # Key metrics row
        peak_solar_hour = int(hdf.loc[hdf['solar_generation_mw'].idxmax(), 'hour']) if not hdf.empty else 'N/A'
        peak_wind_hour  = int(hdf.loc[hdf['wind_generation_mw'].idxmax(), 'hour']) if not hdf.empty else 'N/A'
        total_gen       = hdf['total_generation_mw'].sum()
        peak_hour_total = int(hdf.loc[hdf['total_generation_mw'].idxmax(), 'hour']) if not hdf.empty else 'N/A'
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Peak Solar Hour", f"{peak_solar_hour}:00")
        c2.metric("Peak Wind Hour",  f"{peak_wind_hour}:00")
        c3.metric("Peak Combined",   f"{peak_hour_total}:00")
        c4.metric("Daily Total",     f"{total_gen:,.0f} MW")
    else:
        # Multi-day range — show by datetime
        fig_multi = go.Figure()
        fig_multi.add_trace(go.Scatter(
            x=hdf['datetime'], y=hdf['solar_generation_mw'],
            name='Solar (MW)', fill='tozeroy', line=dict(color='#FFB347')
        ))
        fig_multi.add_trace(go.Scatter(
            x=hdf['datetime'], y=hdf['wind_generation_mw'],
            name='Wind (MW)', fill='tozeroy', line=dict(color='#5B9BD5')
        ))
        fig_multi.update_layout(
            xaxis_title='Date/Time', yaxis_title='Generation (MW)',
            title='Hourly Generation (Multi-Day View)', height=400
        )
        st.plotly_chart(fig_multi, use_container_width=True)


# ==========================================
# PAGE ROUTING & RENDER FUNCTIONS
# ==========================================

def render_executive_overview():
    st.title("🏠 Executive Overview")
    st.markdown("High-level consolidation of Generation, Financials, Sustainability, and Risk.")
    
    df_exec = filter_by_time_horizon(data['exec_summary'], global_time_horizon, custom_start_date, custom_end_date)
    
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
    
    df_rev = filter_by_time_horizon(data['revenue'], global_time_horizon, custom_start_date, custom_end_date)
    if not df_rev.empty:
        # Show hourly breakdown first for single-day views
        if global_time_horizon in SINGLE_DAY_HORIZONS or global_time_horizon == "📅 Custom Range":
            render_hourly_charts(global_time_horizon, custom_start_date, custom_end_date)
            st.markdown("---")
            st.subheader("Daily Summary")
        
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
    
    # Show hourly breakdown for single-day views
    if global_time_horizon in SINGLE_DAY_HORIZONS or global_time_horizon == "📅 Custom Range":
        render_hourly_charts(global_time_horizon, custom_start_date, custom_end_date)
        st.markdown("---")
    
    df_total = filter_by_time_horizon(data['total_pred'], global_time_horizon, custom_start_date, custom_end_date)
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
    
    df_carb = filter_by_time_horizon(data['carbon'], global_time_horizon, custom_start_date, custom_end_date)
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
    
    df_risk = filter_by_time_horizon(data['weather_risk'], global_time_horizon, custom_start_date, custom_end_date)
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
    
    df_rev = filter_by_time_horizon(data['revenue'], global_time_horizon, custom_start_date, custom_end_date)
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

# ===========================================================================
# IEX ANALYTICS — Data Loader (cached)
# ===========================================================================
@st.cache_data(ttl=3600, show_spinner=False)
def load_iex_data():
    """Load or generate all IEX analytics data.
    Note: Cache busted to load restored optimistic/pessimistic columns.
    """
    import sys
    ROOT = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, ROOT)

    market_dir  = os.path.join(ROOT, 'data', 'market')
    iex_path    = os.path.join(market_dir, 'iex_prices.csv')
    backtest_path = os.path.join(ROOT, 'reports', 'market', 'revenue_backtesting.csv')
    future_path   = os.path.join(ROOT, 'reports', 'market', 'future_market_revenue.csv')
    summary_path  = os.path.join(ROOT, 'reports', 'market', 'iex_market_summary.csv')
    insights_path = os.path.join(ROOT, 'reports', 'market', 'market_executive_insights.csv')

    # Auto-generate if missing
    if not os.path.exists(iex_path):
        try:
            from src.ingestion.iex_price_generator import main as _gen
            _gen()
        except Exception as e:
            st.warning(f"Could not auto-generate IEX prices: {e}")

    if not os.path.exists(backtest_path):
        try:
            from src.analytics.iex_analytics import run_iex_analytics
            run_iex_analytics()
        except Exception as e:
            st.warning(f"Could not run IEX analytics engine: {e}")

    def _read(p):
        if os.path.exists(p):
            df = pd.read_csv(p)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            if 'iex_prices.csv' in p:
                if 'dam_price_rs_mwh' in df.columns:
                    df['dam_price_rs_kwh'] = (df['dam_price_rs_mwh'] / 1000).round(2)
                if 'rtm_price_rs_mwh' in df.columns:
                    df['rtm_price_rs_kwh'] = (df['rtm_price_rs_mwh'] / 1000).round(2)
                elif 'dam_price_rs_mwh' in df.columns:
                    df['rtm_price_rs_kwh'] = (df['dam_price_rs_mwh'] * 1.03 / 1000).round(2)
            return df
        return pd.DataFrame()

    return {
        'iex'      : _read(iex_path),
        'backtest' : _read(backtest_path),
        'future'   : _read(future_path),
        'summary'  : _read(summary_path),
        'insights' : _read(insights_path),
    }


# ===========================================================================
# IEX ANALYTICS — Render
# ===========================================================================
def render_iex_analytics():
    st.title("⚡ IEX Market Intelligence")
    st.markdown(
        "Real-time Indian Energy Exchange (IEX) Day-Ahead Market analytics "
        "fused with AI generation forecasts for end-to-end revenue intelligence."
    )

    iex_d = load_iex_data()
    iex      = iex_d['iex']
    backtest = iex_d['backtest']
    future   = iex_d['future']
    summary  = iex_d['summary']
    insights = iex_d['insights']

    if iex.empty:
        st.error("⚠️ IEX price data could not be loaded. Please run the pipeline first.")
        return

    # ── filter by global time horizon ────────────────────────────────────────
    iex_f  = filter_by_time_horizon(iex,      global_time_horizon, custom_start_date, custom_end_date)
    bt_f   = filter_by_time_horizon(backtest,  global_time_horizon, custom_start_date, custom_end_date)
    if iex_f.empty:
        iex_f  = iex
        bt_f   = backtest

    # ======================================================================
    # SECTION 1 — MARKET OVERVIEW KPIs
    # ======================================================================
    st.markdown("---")
    st.subheader("📊 Market Overview")

    kpi = summary.iloc[0].to_dict() if not summary.empty else {}

    avg_price   = safe_number(kpi.get('avg_dam_price_rs_kwh', iex_f['dam_price_rs_kwh'].mean()))
    avg_rtm     = safe_number(kpi.get('avg_rtm_price_rs_kwh', iex_f['rtm_price_rs_kwh'].mean()))
    max_price   = safe_number(kpi.get('max_dam_price_rs_kwh', iex_f['dam_price_rs_kwh'].max()))
    min_price   = safe_number(kpi.get('min_dam_price_rs_kwh', iex_f['dam_price_rs_kwh'].min()))
    volatility  = safe_number(kpi.get('price_volatility_pct',
                              (iex_f['dam_price_rs_kwh'].std() / iex_f['dam_price_rs_kwh'].mean()) * 100))
    total_rev   = safe_number(kpi.get('total_revenue_inr', bt_f['revenue_inr'].sum() if not bt_f.empty else 0))
    avg_day_rev = safe_number(kpi.get('avg_daily_revenue_inr', bt_f['revenue_inr'].mean() if not bt_f.empty else 0))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💹 Avg DAM Price",       f"₹{avg_price:,.2f} /kWh")
    c2.metric("⚡ Avg RTM Price",       f"₹{avg_rtm:,.2f} /kWh")
    c3.metric("⬆️ Peak DAM Price",       f"₹{max_price:,.2f} /kWh")
    c4.metric("⬇️ Floor DAM Price",      f"₹{min_price:,.2f} /kWh")

    c5, c6, c7 = st.columns(3)
    c5.metric("💰 Avg Daily Revenue",    f"₹{avg_day_rev/1e5:.2f} L")
    c6.metric("🏆 Total Market Revenue", f"₹{total_rev/1e7:.2f} Cr")
    c7.metric("📈 Price Volatility",      f"{volatility:.2f}%")

    # ======================================================================
    # SECTION 2 — IEX PRICE ANALYTICS
    # ======================================================================
    st.markdown("---")
    st.subheader("📈 IEX DAM Price Analytics")

    tab1, tab2, tab3, tab4 = st.tabs([
        "Daily Trend", "Monthly Avg", "Distribution", "Volatility"
    ])

    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=iex_f['date'], y=iex_f['dam_price_rs_kwh'],
            mode='lines', name='DAM Price',
            line=dict(color='#FF6B35', width=1.5)
        ))
        if 'rtm_price_rs_kwh' in iex_f.columns:
            fig.add_trace(go.Scatter(
                x=iex_f['date'], y=iex_f['rtm_price_rs_kwh'],
                mode='lines', name='RTM Price',
                line=dict(color='#2ECC71', width=1.5, dash='dot')
            ))
        fig.add_trace(go.Scatter(
            x=iex_f['date'],
            y=iex_f['dam_price_rs_kwh'].rolling(30, min_periods=1).mean(),
            mode='lines', name='30-Day MA (DAM)',
            line=dict(color='#004E89', width=2, dash='dash')
        ))
        # Highlight highest / lowest days
        if not iex_f.empty:
            hi_row = iex_f.loc[iex_f['dam_price_rs_kwh'].idxmax()]
            lo_row = iex_f.loc[iex_f['dam_price_rs_kwh'].idxmin()]
            fig.add_trace(go.Scatter(
                x=[hi_row['date']], y=[hi_row['dam_price_rs_kwh']],
                mode='markers', name='Highest Day',
                marker=dict(color='red', size=10, symbol='star')
            ))
            fig.add_trace(go.Scatter(
                x=[lo_row['date']], y=[lo_row['dam_price_rs_kwh']],
                mode='markers', name='Lowest Day',
                marker=dict(color='green', size=10, symbol='star')
            ))
        fig.update_layout(
            title='Daily Market Clearing Price (₹/kWh)',
            xaxis_title='Date', yaxis_title='₹ / kWh',
            height=420, legend=dict(orientation='h', y=1.1)
        )
        st.plotly_chart(fig, use_container_width=True)

        if not iex_f.empty:
            hi = iex_f.loc[iex_f['dam_price_rs_kwh'].idxmax()]
            lo = iex_f.loc[iex_f['dam_price_rs_kwh'].idxmin()]
            c1, c2 = st.columns(2)
            c1.info(f"🔴 **Highest Price Day:** {hi['date'].strftime('%d %b %Y')}  —  ₹{hi['dam_price_rs_kwh']:,.2f}/kWh")
            c2.success(f"🟢 **Lowest Price Day:** {lo['date'].strftime('%d %b %Y')}  —  ₹{lo['dam_price_rs_kwh']:,.2f}/kWh")

    with tab2:
        monthly_avg = iex.groupby(iex['date'].dt.to_period('M'))['dam_price_rs_kwh'].mean().reset_index()
        monthly_avg['date'] = monthly_avg['date'].astype(str)
        fig2 = px.bar(
            monthly_avg, x='date', y='dam_price_rs_kwh',
            title='Monthly Average DAM Price (₹/kWh)',
            color='dam_price_rs_kwh',
            color_continuous_scale='RdYlGn_r',
            labels={'date': 'Month', 'dam_price_rs_kwh': '₹/kWh'}
        )
        fig2.update_layout(height=420, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        fig3 = px.histogram(
            iex_f, x='dam_price_rs_kwh', nbins=50,
            title='DAM Price Distribution (₹/kWh)',
            labels={'dam_price_rs_kwh': '₹/kWh', 'count': 'Days'},
            color_discrete_sequence=['#5B9BD5']
        )
        fig3.add_vline(x=avg_price, line_dash='dash', line_color='red',
                       annotation_text=f'Avg: ₹{avg_price:,.2f}', annotation_position='top right')
        fig3.update_layout(height=400)
        st.plotly_chart(fig3, use_container_width=True)

    with tab4:
        rolling_std = iex_f['dam_price_rs_kwh'].rolling(30, min_periods=1).std()
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=iex_f['date'], y=rolling_std,
            fill='tozeroy', name='30-Day Rolling σ',
            line=dict(color='#FF4444')
        ))
        fig4.update_layout(
            title='30-Day Rolling Price Volatility (₹/kWh σ)',
            xaxis_title='Date', yaxis_title='Std Dev (₹/kWh)', height=380
        )
        st.plotly_chart(fig4, use_container_width=True)

    # ======================================================================
    # SECTION 3 — REVENUE BACKTESTING
    # ======================================================================
    st.markdown("---")
    st.subheader("💸 Revenue Backtesting  (Generation × DAM Price)")

    if bt_f.empty:
        st.warning("No revenue backtest data for the selected time horizon.")
    else:
        total_bt = bt_f['revenue_inr'].sum()
        avg_bt   = bt_f['revenue_inr'].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Revenue",    f"₹{total_bt/1e7:.2f} Cr")
        c2.metric("Avg Daily Revenue", f"₹{avg_bt/1e5:.2f} L")
        c3.metric("Days Analysed",    f"{len(bt_f):,}")

        # Revenue Trend Chart
        fig_rev = go.Figure()
        fig_rev.add_trace(go.Scatter(
            x=bt_f['date'], y=bt_f['revenue_lakhs'],
            fill='tozeroy', name='Revenue (₹ Lakhs)',
            line=dict(color='#2ECC71', width=1.5)
        ))
        fig_rev.add_trace(go.Scatter(
            x=bt_f['date'],
            y=bt_f['revenue_lakhs'].rolling(30, min_periods=1).mean(),
            name='30-Day MA', line=dict(color='#E74C3C', dash='dash', width=2)
        ))
        fig_rev.update_layout(
            title='Daily Market Revenue Trend (₹ Lakhs)',
            xaxis_title='Date', yaxis_title='₹ Lakhs', height=380
        )
        st.plotly_chart(fig_rev, use_container_width=True)

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Top 10 Revenue Days**")
            top10 = bt_f.nlargest(10, 'revenue_inr')[[
                'date','total_generation_mw','dam_price_rs_kwh','rtm_price_rs_kwh','revenue_lakhs'
            ]].copy()
            top10['date'] = top10['date'].dt.strftime('%d %b %Y')
            top10.columns = ['Date','Generation (MW)','DAM (₹/kWh)','RTM (₹/kWh)','Revenue (₹ L)']
            st.dataframe(top10.reset_index(drop=True), use_container_width=True)

        with col_b:
            st.markdown("**Bottom 10 Revenue Days**")
            bot10 = bt_f.nsmallest(10, 'revenue_inr')[[
                'date','total_generation_mw','dam_price_rs_kwh','rtm_price_rs_kwh','revenue_lakhs'
            ]].copy()
            bot10['date'] = bot10['date'].dt.strftime('%d %b %Y')
            bot10.columns = ['Date','Generation (MW)','DAM (₹/kWh)','RTM (₹/kWh)','Revenue (₹ L)']
            st.dataframe(bot10.reset_index(drop=True), use_container_width=True)

        st.markdown("**Full Backtesting Dataset**")
        display_bt = bt_f[['date','solar_generation_mw','wind_generation_mw',
                            'total_generation_mw','dam_price_rs_kwh','rtm_price_rs_kwh',
                            'revenue_inr','revenue_lakhs','revenue_crores']].copy()
        display_bt['date'] = display_bt['date'].dt.strftime('%Y-%m-%d')
        display_bt.columns = [
            'Date','Solar MW','Wind MW','Total MW',
            'DAM (₹/kWh)','RTM (₹/kWh)','Revenue (₹)','Revenue (Lakhs)','Revenue (Crores)'
        ]
        st.dataframe(display_bt.tail(60), use_container_width=True)

    # ======================================================================
    # SECTION 4 — FUTURE REVENUE FORECAST
    # ======================================================================
    st.markdown("---")
    st.subheader("🔮 Future Revenue Forecast")

    if future.empty:
        st.info("No future forecast data available. Run the pipeline to generate predictions.")
    else:
        days_ahead = len(future)
        total_fut  = future['forecast_revenue_inr'].sum()
        avg_fut    = future['forecast_revenue_inr'].mean()

        c1, c2, c3 = st.columns(3)
        c1.metric("Forecast Horizon",       f"{days_ahead} days")
        c2.metric("Total Forecast Revenue", f"₹{total_fut/1e5:.2f} L")
        c3.metric("Avg Daily Revenue",      f"₹{avg_fut/1e5:.2f} L")

        fig_fut = go.Figure()
        fig_fut.add_trace(go.Bar(
            x=future['date'], y=future['forecast_revenue_lakhs'],
            name='Expected Revenue', marker_color='#3498DB'
        ))
        fig_fut.add_trace(go.Scatter(
            x=future['date'], y=future['optimistic_revenue_inr'] / 1e5,
            name='Optimistic (+15%)', mode='lines',
            line=dict(color='#2ECC71', dash='dot', width=2)
        ))
        fig_fut.add_trace(go.Scatter(
            x=future['date'], y=future['pessimistic_revenue_inr'] / 1e5,
            name='Pessimistic (-15%)', mode='lines',
            line=dict(color='#E74C3C', dash='dot', width=2)
        ))
        fig_fut.update_layout(
            title='Forward Revenue Forecast with Upside/Downside Bands (₹ Lakhs)',
            xaxis_title='Date', yaxis_title='₹ Lakhs', height=400,
            legend=dict(orientation='h', y=1.1)
        )
        st.plotly_chart(fig_fut, use_container_width=True)

        # Invalidate cache if needed
        # @st.cache_data
        # def load_iex_data():
        #     # Refresh cache by timestamp
        
        display_fut = future[[
            'date','forecast_generation_mw','expected_dam_price_kwh',
            'forecast_revenue_lakhs','optimistic_revenue_inr','pessimistic_revenue_inr'
        ]].copy()
        display_fut['date'] = display_fut['date'].dt.strftime('%Y-%m-%d')
        display_fut['optimistic_revenue_inr']   /= 1e5
        display_fut['pessimistic_revenue_inr']  /= 1e5
        display_fut.columns = [
            'Date','Forecast Gen (MW)','Expected Price (₹/kWh)',
            'Revenue (₹ L)','Optimistic (₹ L)','Pessimistic (₹ L)'
        ]
        st.dataframe(display_fut, use_container_width=True)

    # ======================================================================
    # SECTION 5 — SCENARIO SIMULATOR
    # ======================================================================
    st.markdown("---")
    st.subheader("🎮 Revenue Scenario Simulator")
    st.markdown("Adjust market conditions and see the projected revenue impact in real-time.")

    col_sl1, col_sl2 = st.columns(2)
    with col_sl1:
        price_up   = st.slider("📈 Price Increase (%)",   min_value=0,   max_value=100, value=0,   step=5,  key='scen_price_up')
        price_down = st.slider("📉 Price Decrease (%)",  min_value=0,   max_value=50,  value=0,   step=5,  key='scen_price_dn')
    with col_sl2:
        gen_up   = st.slider("⚡ Generation Increase (%)", min_value=0,  max_value=50,  value=0,  step=5,  key='scen_gen_up')
        gen_down = st.slider("🟥 Generation Decrease (%)", min_value=0, max_value=50,  value=0,  step=5,  key='scen_gen_dn')

    net_price_chg = price_up - price_down
    net_gen_chg   = gen_up   - gen_down

    if not backtest.empty:
        from src.analytics.iex_analytics import simulate_scenario
        scen = simulate_scenario(backtest, net_price_chg, net_gen_chg)

        s1, s2, s3, s4 = st.columns(4)
        delta_str = f"{'+'if scen['delta_crores']>=0 else ''}{scen['delta_crores']:.2f} Cr"
        pct_str   = f"{'+'if scen['pct_impact']>=0 else ''}{scen['pct_impact']:.2f}%"
        s1.metric("Base Revenue",     f"₹{scen['base_crores']:.2f} Cr")
        s2.metric("Scenario Revenue", f"₹{scen['scenario_crores']:.2f} Cr",
                  delta=delta_str,
                  delta_color="normal" if scen['delta_crores'] >= 0 else "inverse")
        s3.metric("Revenue Δ",        delta_str)
        s4.metric("% Impact",          pct_str)

        # Visual comparison bar
        fig_scen = go.Figure(go.Bar(
            x=['Base Revenue', 'Scenario Revenue'],
            y=[scen['base_crores'], scen['scenario_crores']],
            marker_color=['#3498DB', '#2ECC71' if scen['scenario_crores'] >= scen['base_crores'] else '#E74C3C'],
            text=[f"₹{scen['base_crores']:.2f} Cr", f"₹{scen['scenario_crores']:.2f} Cr"],
            textposition='outside'
        ))
        fig_scen.update_layout(
            title='Base vs Scenario Revenue Comparison (₹ Crores)',
            yaxis_title='₹ Crores', height=350
        )
        st.plotly_chart(fig_scen, use_container_width=True)
    else:
        st.info("Run the pipeline to enable scenario simulation.")

    # ======================================================================
    # SECTION 6 — EXECUTIVE MARKET INSIGHTS
    # ======================================================================
    st.markdown("---")
    st.subheader("🧠 Executive Market Insights")

    if not insights.empty:
        for _, row in insights.iterrows():
            with st.expander(f"📌 {row.get('Section', 'Insight')}", expanded=False):
                st.markdown(row.get('Insight', ''))
    else:
        # Fallback static insights
        static_insights = [
            ("Price Seasonality",
             "IEX DAM prices peak during summer months (April–June) driven by high cooling demand, "
             "aligning perfectly with Khavda's solar generation peak — a powerful revenue multiplier."),
            ("Revenue Concentration",
             "The top 3 revenue months account for the majority of annual market revenue. "
             "Strategic scheduling of maintenance windows during monsoon months maximises revenue capture."),
            ("Market Volatility Risk",
             "IEX price volatility requires a hedging strategy. PPAs for 60–70% of capacity is recommended "
             "alongside active participation in the spot market for the remaining volume."),
            ("Future Revenue Outlook",
             "AI-driven forecasts confirm stable renewable output over the next 14 days. "
             "Revenue is expected to remain consistent with seasonal averages."),
            ("Market Floor Strategy",
             "Khavda's variable cost per MWh remains well below the IEX market price floor, "
             "ensuring positive contribution margin under all market clearing scenarios."),
        ]
        for section, text in static_insights:
            with st.expander(f"📌 {section}", expanded=False):
                st.markdown(text)

    # ======================================================================
    # SECTION 7 — DOWNLOAD EXPORTS
    # ======================================================================
    st.markdown("---")
    st.subheader("📥 Export Market Reports")

    ROOT = os.path.dirname(os.path.abspath(__file__))
    export_files = {
        "IEX Market Summary KPIs": os.path.join(ROOT, 'reports', 'market', 'iex_market_summary.csv'),
        "Revenue Backtesting":     os.path.join(ROOT, 'reports', 'market', 'revenue_backtesting.csv'),
        "Future Market Revenue":   os.path.join(ROOT, 'reports', 'market', 'future_market_revenue.csv'),
        "Executive Market Insights": os.path.join(ROOT, 'reports', 'market', 'market_executive_insights.csv'),
    }

    cols = st.columns(len(export_files))
    for i, (label, path) in enumerate(export_files.items()):
        with cols[i]:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    st.download_button(
                        label=f"⬇️ {label}",
                        data=f.read(),
                        file_name=os.path.basename(path),
                        mime='text/csv',
                        key=f'dl_{i}'
                    )
            else:
                st.caption(f"{label} not generated yet.")


# ==========================================
# ROUTING LOGIC
# ==========================================

# ===========================================================================
# GRID INTELLIGENCE
# ===========================================================================
def render_grid_analytics():
    st.title("🌐 Grid Intelligence (NLDC Frequency Monitor)")
    st.markdown(
        """
        Track National Load Despatch Centre (NLDC) daily grid frequency to predict 
        curtailment risks and Deviation Settlement Mechanism (DSM) financial penalties.
        """
    )
    st.markdown("---")

    ROOT = os.path.dirname(os.path.abspath(__file__))
    grid_path = os.path.join(ROOT, 'data', 'grid', 'nldc_grid_frequency.csv')
    
    if not os.path.exists(grid_path):
        st.warning("Grid frequency data not found. Please run the NLDC scraper pipeline.")
        return
        
    df = pd.read_csv(grid_path)
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['date'] = df['datetime'].dt.date
    
    # Filter by time horizon
    df_f = filter_by_time_horizon(df, global_time_horizon, custom_start_date, custom_end_date)
    
    if df_f.empty:
        st.info(f"No grid frequency data available for the selected horizon: {global_time_horizon}")
        return
        
    avg_freq = df_f['frequency_hz'].mean()
    min_freq = df_f['frequency_hz'].min()
    max_freq = df_f['frequency_hz'].max()
    
    avg_freq = df_f['frequency_hz'].mean()
    min_freq = df_f['frequency_hz'].min()
    max_freq = df_f['frequency_hz'].max()
    danger_blocks = df_f[df_f['grid_stress_flag'] != "Normal"].shape[0]
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="Average Frequency", value=f"{avg_freq:.3f} Hz")
    with col2:
        st.metric(label="Minimum Frequency", value=f"{min_freq:.3f} Hz", delta=f"{min_freq - 50.00:.3f} Hz", delta_color="inverse")
    with col3:
        st.metric(label="Maximum Frequency", value=f"{max_freq:.3f} Hz", delta=f"{max_freq - 50.00:.3f} Hz", delta_color="inverse")
    with col4:
        st.metric(label="Danger Zone Blocks", value=f"{danger_blocks}", delta="Action Required" if danger_blocks > 0 else "Stable", delta_color="off" if danger_blocks == 0 else "inverse")
    
    st.markdown("---")
    st.subheader("📈 15-Minute Frequency Profile & Regulatory Bands")
    
    fig = go.Figure()
    
    # Plot the real-time frequency timeline
    fig.add_trace(go.Scatter(
        x=df_f['datetime'], 
        y=df_f['frequency_hz'],
        mode='lines+markers',
        name='Grid Frequency',
        line=dict(color='#3498DB', width=2.5),
        marker=dict(size=4)
    ))
    
    # Add upper regulatory ceiling line (50.05 Hz)
    fig.add_hline(
        y=50.05, line_dash="dash", line_color="red", 
        annotation_text="Over-frequency Ceiling (50.05 Hz)", annotation_position="top left"
    )
    
    # Add lower regulatory floor line (49.90 Hz)
    fig.add_hline(
        y=49.90, line_dash="dash", line_color="red", 
        annotation_text="Under-frequency Floor (49.90 Hz)", annotation_position="bottom left"
    )
    
    # Shaded Area for the Safe Operating Zone
    fig.add_hrect(
        y0=49.90, y1=50.05, 
        fillcolor="green", opacity=0.08, 
        layer="below", line_width=0,
        annotation_text="CERC Safe Shaded Band",
        annotation_position="inside top left"
    )
    
    fig.update_layout(
        xaxis_title='Time of Day (15-Min Blocks)',
        yaxis_title='Grid Frequency (Hz)',
        yaxis=dict(range=[49.75, 50.30]),
        hovermode="x unified",
        height=500,
        showlegend=False,
        margin=dict(l=20, r=20, t=20, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.subheader("📑 Deviation Settlement Mechanism (DSM) Logs")
    st.markdown("Historical 15-minute raw interval logging with operational risk classification:")
    
    display_df = df_f[['datetime', 'frequency_hz', 'grid_stress_flag']].copy()
    display_df.columns = ['Time', 'Frequency (Hz)', 'Grid Stress Flag']
    
    # Custom color styler function for the dataframe UI
    def style_flags(val):
        if str(val) == "Normal":
            return "color: #2ecc71; font-weight: bold;"
        elif "Under-frequency" in str(val):
            return "color: #e74c3c; font-weight: bold;"
        elif "Over-frequency" in str(val):
            return "color: #f39c12; font-weight: bold;"
        return ""
        
    st.dataframe(display_df.style.map(style_flags, subset=['Grid Stress Flag']), use_container_width=True, height=400)

    st.markdown("---")
    st.markdown("## ⚡ Real-Time Grid Crisis Simulator")
    st.markdown(
        """
        **Industrial Control Room Simulation Tool:** 
        Test how varying operational response times to sudden weather anomalies and grid frequency 
        excursions impact financial penalties under the Deviation Settlement Mechanism (DSM).
        """
    )
    
    col_input1, col_input2 = st.columns([2, 1])
    
    with col_input1:
        scenario = st.selectbox(
            "Select Operational Crisis Scenario:",
            [
                "Scenario 1: Sudden Cloud Cover (Under-generation)",
                "Scenario 2: Midday Solar Peak (Over-generation)",
                "Scenario 3: Stable Operations (Baseline)"
            ]
        )
    
    with col_input2:
        response_time = st.slider(
            "Operator Response Time (Minutes):", 
            min_value=0, 
            max_value=60, 
            value=15, 
            step=1
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    def run_simulation(selected_scenario, minutes_delayed):
        freq_hz = 50.00
        sched_mw = 1000
        actual_mw = 1000
        action = "Hold Baseline"
        financial_impact = 0
        impact_type = "Penalty"
        
        PENALTY_MULTIPLIER = 5000 
        OPPORTUNITY_MULTIPLIER = 3000
        
        if "Scenario 1" in selected_scenario:
            freq_hz = 49.82
            actual_mw = 800
            action = "Immediate Schedule Revision / Buy Power on Open Market"
            deficit = sched_mw - actual_mw
            financial_impact = deficit * minutes_delayed * PENALTY_MULTIPLIER
            impact_type = "DSM Penalty Accrued (₹)"
            
        elif "Scenario 2" in selected_scenario:
            freq_hz = 50.15
            actual_mw = 1200
            action = "Divert to Battery Storage / Sell on IEX Real-Time Market (RTM)"
            surplus = actual_mw - sched_mw
            financial_impact = surplus * minutes_delayed * OPPORTUNITY_MULTIPLIER
            impact_type = "Avoidable Revenue Loss (₹)"
            
        elif "Scenario 3" in selected_scenario:
            freq_hz = 50.00
            actual_mw = 995
            action = "Hold Baseline"
            financial_impact = 0
            impact_type = "DSM Penalty Accrued (₹)"
            
        efficiency_rating = max(0.0, 100 - ((minutes_delayed / 60) * 100))
        return freq_hz, sched_mw, actual_mw, action, financial_impact, impact_type, efficiency_rating
    
    sim_freq, sim_sched, sim_actual, sim_action, sim_finance, sim_finance_label, sim_efficiency = run_simulation(scenario, response_time)
    
    c1, c2, c3 = st.columns(3)
    with c1:
        freq_delta = sim_freq - 50.00
        st.metric(
            label="Grid Frequency (Hz)", 
            value=f"{sim_freq:.2f} Hz", 
            delta=f"{freq_delta:.2f} Hz", 
            delta_color="inverse" if abs(freq_delta) > 0.05 else "normal"
        )
    with c2:
        mw_gap = sim_actual - sim_sched
        st.metric(
            label="Actual vs Scheduled (MW)", 
            value=f"{sim_actual} MW", 
            delta=f"{mw_gap} MW Deviation",
            delta_color="off" if mw_gap == 0 else "normal"
        )
    with c3:
        st.markdown("**System Recommendation:**")
        if "Scenario 1" in scenario:
            st.error(f"🚨 {sim_action}")
        elif "Scenario 2" in scenario:
            st.warning(f"⚠️ {sim_action}")
        else:
            st.success(f"✅ {sim_action}")
            
    st.markdown("---")
    
    with st.container():
        st.markdown("### 💸 Financial Impact Analysis")
        if sim_finance > 0:
            st.markdown(f"#### {sim_finance_label}: <span style='color:#E74C3C'>**₹ {sim_finance:,.2f}**</span>", unsafe_allow_html=True)
            st.caption("Notice how delayed response time scales the financial penalty dramatically during crisis events.")
        else:
            st.markdown(f"#### {sim_finance_label}: <span style='color:#2ECC71'>**₹ 0.00**</span>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"**Operator Efficiency Rating: {int(sim_efficiency)}%**")
        st.progress(sim_efficiency / 100.0)

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
elif selection == "⚡ IEX Analytics":
    render_iex_analytics()
elif selection == "🌐 Grid Intelligence":
    render_grid_analytics()

# Footer
st.markdown("---")
st.markdown("<div align='center'>Built for Khavda Renewable Energy Park Management Team</div>", unsafe_allow_html=True)
