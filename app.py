"""
Khavda Renewable Energy Digital Twin - Executive Dashboard
Built with Streamlit, Pandas, and Plotly.
"""

import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
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
            # Compare using .dt.date to safely ignore time components
            return df[(df['date'].dt.date >= custom_start) & (df['date'].dt.date <= custom_end)]
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
    st.title("📊 Daily Executive Intelligence Summary")
    
    # 1. Header & Dynamic Banner
    selected_date = st.date_input("Select Reporting Date:", datetime.date.today())
    
    st.info("💡 **Automated Briefing:** Generation is exceeding targets by 2.5% today. Weather is optimal, but monitor grid frequency between 17:00-19:00 for potential DSM penalty exposure.")
    st.markdown("---")
    
    # Dummy data
    total_yield = 12450.50
    net_revenue = 4520500
    dsm_exposure = 15000
    carbon_offset = 10209.4
    
    # 2. Core KPIs
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Portfolio Yield", f"{total_yield:,.0f} MWh", "+2.5%")
    with c2:
        st.metric("Total Net Revenue", f"₹ {net_revenue/100000:,.2f} L", "+1.2 L")
    with c3:
        st.metric("DSM Risk Exposure", f"₹ {dsm_exposure:,.0f}", "-₹ 5,000", delta_color="inverse")
    with c4:
        st.metric("Carbon Footprint Offset", f"{carbon_offset:,.0f} Tons", "+400 Tons")
        
    st.markdown("---")
    
    # 3. The 5-Module Integration
    col_left, col_right = st.columns(2)
    
    with col_left:
        with st.expander("🌤️ Module 1: Weather & Climate Risk", expanded=True):
            st.markdown("**Peak GHI:** 950 W/m²")
            st.markdown("**Avg Temperature:** 34°C")
            st.markdown("**Alerts:** Dust Accumulation Warning (Amber)")
            
        with st.expander("⚡ Module 2: ML Generation Analytics", expanded=True):
            st.markdown("**XGBoost Model Accuracy:** 96.4%")
            st.markdown("**Forecasted Yield:** 12,450 MWh")
            st.markdown("**Top SHAP Feature:** Cloud Cover Index")
            
        with st.expander("🌱 Module 5: Sustainability Reporting", expanded=True):
            st.markdown("**CO2 Avoided:** 10,209 Tons")
            st.markdown("**Coal Displaced:** 6,225 Tons")

    with col_right:
        with st.expander("💰 Module 3: Commercial Revenue (IEX)", expanded=True):
            st.markdown("**DAM Realized Revenue:** ₹ 38.5 L")
            st.markdown("**RTM Dispatch Events:** 3 Peaks Targeted")
            st.markdown("**Avg Clearing Price:** ₹ 4.15 / kWh")
            
        with st.expander("⚖️ Module 4: Grid Integrity (NLDC)", expanded=True):
            st.markdown("**Avg Grid Frequency:** 49.98 Hz")
            st.markdown("**Excursion Warning Minutes:** 15 Mins")
            st.markdown("**DSM Penalty Status:** Low Risk (₹ 15,000)")
            
    st.markdown("---")
    
    # 4. Visual Data (Plotly)
    st.subheader("📈 Daily Generation Portfolio Contribution")
    fig = go.Figure(data=[go.Pie(
        labels=['Solar Farm Block A', 'Solar Farm Block B', 'Wind Turbines'],
        values=[6000, 2500, 3950.5],
        hole=.4,
        marker_colors=['#F1C40F', '#E67E22', '#3498DB']
    )])
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=300)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # 5. The CSV Export Fix (Crucial)
    st.subheader("📑 Comprehensive Corporate Ledger")
    st.caption("Detailed 5-module cross-sectional data prepared for C-suite export.")
    
    df_executive_report = pd.DataFrame([
        ["Weather", "Peak GHI", "950", "W/m²", "Optimal"],
        ["Weather", "Temperature", "34", "°C", "Normal"],
        ["Weather", "Dust Alert", "Amber", "Level", "Action Required"],
        ["ML Generation", "Model Accuracy", "96.4", "%", "Excellent"],
        ["ML Generation", "Forecasted Yield", "12450", "MWh", "On Track"],
        ["ML Generation", "Top SHAP Feature", "Cloud Cover", "Index", "Monitored"],
        ["Commercial (IEX)", "DAM Revenue", "38.5", "Lakh INR", "Target Met"],
        ["Commercial (IEX)", "RTM Peaks Targeted", "3", "Events", "Executed"],
        ["Commercial (IEX)", "Avg Clearing Price", "4.15", "INR/kWh", "Favorable"],
        ["Grid Integrity", "Avg Frequency", "49.98", "Hz", "Safe Zone"],
        ["Grid Integrity", "Excursion Minutes", "15", "Mins", "Monitor"],
        ["Grid Integrity", "DSM Penalty", "15000", "INR", "Low Risk"],
        ["Sustainability", "CO2 Avoided", "10209", "Tons", "Verified"],
        ["Sustainability", "Coal Displaced", "6225", "Tons", "Verified"]
    ], columns=["Module", "KPI Parameter", "Value", "Unit", "Status / Assessment"])
    
    csv_data = df_executive_report.to_csv(index=False).encode('utf-8')
    
    st.download_button(
        label="📥 Download Corporate Ledger (CSV)",
        data=csv_data,
        file_name=f"Khavda_Corporate_Ledger_{selected_date}.csv",
        mime="text/csv",
    )
    
    st.dataframe(df_executive_report, use_container_width=True)

def render_generation_analytics():
    st.title("⚡ Generation Analytics & Performance Tracking")
    st.markdown("Track granular asset performance against ML-forecasted baselines to immediately identify operational gaps.")
    
    # 1. Page Header & KPI Pulse
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Today's Solar Yield", "8,450 MWh", "+1.2%")
    with c2:
        st.metric("Today's Wind Yield", "3,200 MWh", "-4.5%")
    with c3:
        st.metric("Total Combined Yield", "11,650 MWh", "Normal")
    with c4:
        st.metric("Current Capacity Factor", "28.4%", "-0.8%")
        
    st.markdown("---")
    
    # 1b. PV Performance Panel — reads from the physics-informed generation CSV
    st.subheader("🔬 PV Performance Panel (Physics-Informed)")
    
    ROOT = os.path.dirname(os.path.abspath(__file__))
    gen_path = os.path.join(ROOT, 'data', 'processed', 'khavda_generation.csv')
    
    pv_cols = ['effective_irradiance', 'cell_temperature_c', 'temperature_factor',
               'cloud_factor', 'performance_ratio', 'capacity_factor']
    
    if os.path.exists(gen_path):
        df_gen = pd.read_csv(gen_path)
        pv_available = [c for c in pv_cols if c in df_gen.columns]
        
        if pv_available:
            latest = df_gen.iloc[-1]
            p1, p2, p3, p4, p5, p6 = st.columns(6)
            
            eff_irr = latest.get('effective_irradiance', 0)
            cell_t  = latest.get('cell_temperature_c', 0)
            t_fac   = latest.get('temperature_factor', 1)
            c_fac   = latest.get('cloud_factor', 1)
            pr      = latest.get('performance_ratio', 0.82)
            cf      = latest.get('capacity_factor', 0)
            
            p1.metric("Effective Irradiance", f"{eff_irr:.2f} kWh/m²/d",
                      help="GHI × Cloud Factor — actual solar energy reaching PV modules")
            p2.metric("PV Cell Temperature", f"{cell_t:.1f} °C",
                      delta=f"{cell_t - 25:.1f} °C vs STC", delta_color="inverse",
                      help="pvlib Faiman model — operating temperature of PV cells")
            p3.metric("Temperature Factor", f"{t_fac:.4f}",
                      delta=f"{(t_fac - 1)*100:.2f}% efficiency",
                      delta_color="inverse",
                      help="γ·ΔT derating — efficiency loss from cell overheating")
            p4.metric("Cloud Factor", f"{c_fac:.3f}",
                      help="1 − Cloud_Cover/100 — direct cloud attenuation factor")
            p5.metric("Performance Ratio", f"{pr:.2f}",
                      help="System PR = 0.82 — inverter, cable, dust, mismatch losses")
            p6.metric("Capacity Factor", f"{cf:.3f}",
                      help="Actual / Installed Capacity — fleet utilisation rate")
        else:
            st.info("PV engineered features not yet in generation CSV. Re-run the pipeline after upgrading to pvlib engine.")
    else:
        # Demo values when no CSV exists yet
        p1, p2, p3, p4, p5, p6 = st.columns(6)
        p1.metric("Effective Irradiance", "5.84 kWh/m²/d")
        p2.metric("PV Cell Temperature", "52.3 °C", "+27.3 °C vs STC", delta_color="inverse")
        p3.metric("Temperature Factor", "0.8908", "-10.9% efficiency", delta_color="inverse")
        p4.metric("Cloud Factor", "0.730")
        p5.metric("Performance Ratio", "0.82")
        p6.metric("Capacity Factor", "0.312")
        st.caption("⚠ Demo data — run the pvlib generation pipeline to display live values.")
    
    st.markdown("---")
    
    # Generate Dummy Time-Series Data
    import numpy as np
    import datetime
    
    now = datetime.datetime.now()
    times = [now - datetime.timedelta(hours=i) for i in range(72, -1, -1)]
    np.random.seed(42)
    
    # Base daily pattern + noise
    forecast = 500 + 300 * np.sin(np.linspace(0, 3 * np.pi, 73)) + np.random.normal(0, 20, 73)
    actual = forecast.copy()
    
    # Inject underperformance anomaly (Actual drops below forecast)
    actual[20:30] -= np.random.uniform(100, 150, 10)  # Sudden drop in actual
    actual[50:60] -= np.random.uniform(50, 100, 10)   # Another drop
    
    df_micro = pd.DataFrame({"Time": times, "Forecast": forecast, "Actual": actual})
    
    # 2. The Micro View: 72-Hour Operational Window
    st.subheader("🔍 Short-Term Analytics (Actual vs. Forecast)")
    
    fig_micro = go.Figure()
    
    # Add Forecast Line (Dashed)
    fig_micro.add_trace(go.Scatter(
        x=df_micro["Time"], y=df_micro["Forecast"],
        mode='lines',
        name='XGBoost Forecast Baseline',
        line=dict(color='gray', dash='dash', width=2)
    ))
    
    # Add Actual Line (Solid) with fill to next y
    fig_micro.add_trace(go.Scatter(
        x=df_micro["Time"], y=df_micro["Actual"],
        mode='lines',
        name='Actual Generation',
        line=dict(color='#3498DB', width=3),
        fill='tonexty',
        fillcolor='rgba(231, 76, 60, 0.2)' # Faint red gap fill
    ))
    
    fig_micro.update_layout(
        xaxis_title="Time (Last 48 Hrs + Next 24 Hrs)",
        yaxis_title="Generation (MW)",
        hovermode="x unified",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0)
    )
    st.plotly_chart(fig_micro, use_container_width=True)
    
    st.markdown("---")
    
    # 3. The Macro View: Seasonal Trends
    st.subheader("📅 Macro Seasonality (Year-to-Date)")
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    solar_monthly = [300, 320, 380, 410, 450, 430, 400, 390, 410, 380, 330, 310]
    wind_monthly = [150, 160, 180, 200, 250, 350, 400, 380, 280, 220, 180, 160]
    
    df_macro = pd.DataFrame({
        "Month": months * 2,
        "Generation (GWh)": solar_monthly + wind_monthly,
        "Source": ["Solar"] * 12 + ["Wind"] * 12
    })
    
    fig_macro = px.bar(
        df_macro, x="Month", y="Generation (GWh)", color="Source",
        barmode="group",
        color_discrete_map={"Solar": "#F1C40F", "Wind": "#3498DB"}
    )
    fig_macro.update_layout(height=350, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_macro, use_container_width=True)
    
    st.markdown("---")
    
    # 4. Asset Underperformance Log
    st.subheader("⚠️ Deviation & Anomaly Log")
    
    # Filter anomalies where Actual is >10% below Forecast
    df_micro['Deviation (%)'] = ((df_micro['Actual'] - df_micro['Forecast']) / df_micro['Forecast']) * 100
    df_anomalies = df_micro[df_micro['Deviation (%)'] < -10].copy()
    
    if not df_anomalies.empty:
        df_anomalies['Time'] = df_anomalies['Time'].dt.strftime('%Y-%m-%d %H:%M')
        df_anomalies['Forecast'] = df_anomalies['Forecast'].round(1)
        df_anomalies['Actual'] = df_anomalies['Actual'].round(1)
        df_anomalies['Deviation (%)'] = df_anomalies['Deviation (%)'].round(1).astype(str) + "%"
        
        # Add mock root causes
        causes = ["Inverter Trip (Block 4)", "Sudden Cloud Cover", "Grid Curtailment Command"]
        df_anomalies['Potential Root Cause'] = np.random.choice(causes, size=len(df_anomalies))
        
        st.dataframe(
            df_anomalies[['Time', 'Forecast', 'Actual', 'Deviation (%)', 'Potential Root Cause']].head(10),
            use_container_width=True
        )
    else:
        st.success("No significant deviations detected in the operational window.")



def render_forecasting():
    st.title("🔮 AI Forecasting & Predictive Intelligence")
    st.markdown("Day-Ahead and Week-Ahead generation projections powered by XGBoost.")
    
    # Pipeline Chain Banner
    st.markdown("""
    <div style="background-color:#1a1a2e;padding:12px 20px;border-radius:8px;border-left:4px solid #F1C40F;margin-bottom:16px;">
    <span style="color:#F1C40F;font-weight:bold;">⚙️ Inference Chain: </span>
    <span style="color:#BDC3C7;">pvlib Physics Engine (GHI → Effective Irradiance → Cell Temp)</span>
    <span style="color:#F1C40F;"> → </span>
    <span style="color:#BDC3C7;">Feature Engineering (PR · Cloud Factor · Temp Factor)</span>
    <span style="color:#F1C40F;"> → </span>
    <span style="color:#2ECC71;font-weight:bold;">XGBoost Correction</span>
    <span style="color:#F1C40F;"> → </span>
    <span style="color:#3498DB;font-weight:bold;">Final Forecast (MW)</span>
    </div>
    """, unsafe_allow_html=True)
    
    # 1. Page Header & AI Health Pulse
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Mean Absolute Error (MAE)", "1.98 MW", "-0.12 MW Improvement", delta_color="inverse")
    with c2:
        st.metric("Root Mean Squared Error (RMSE)", "4.43 MW")
    with c3:
        st.metric("Mean Absolute Percentage Error (MAPE)", "2.12%", "High Accuracy")
    with c4:
        st.metric("Next 24H Projected Yield", "14,250 MWh")
        
    st.markdown("---")
    
    # Generate Dummy Future Data
    import numpy as np
    import datetime
    
    now = datetime.datetime.now()
    times = [now + datetime.timedelta(hours=i) for i in range(-24, 7*24)]
    np.random.seed(42)
    
    solar = np.maximum(0, 4000 * np.sin(np.linspace(0, 8 * np.pi, len(times))) + np.random.normal(0, 200, len(times)))
    wind = 1500 + 500 * np.sin(np.linspace(0, 4 * np.pi, len(times))) + np.random.normal(0, 100, len(times))
    
    df_future = pd.DataFrame({"Time": times, "Solar": solar, "Wind": wind})
    
    # 2. The Future Horizon View
    st.subheader("📅 Week-Ahead Predictive Generation Curve")
    
    fig_future = go.Figure()
    fig_future.add_trace(go.Scatter(x=df_future["Time"], y=df_future["Wind"], mode='lines', name='Forecasted Wind (MW)', stackgroup='one', fillcolor='#3498DB', line=dict(width=0)))
    fig_future.add_trace(go.Scatter(x=df_future["Time"], y=df_future["Solar"], mode='lines', name='Forecasted Solar (MW)', stackgroup='one', fillcolor='#F1C40F', line=dict(width=0)))
    
    fig_future.add_vline(x=now, line_width=3, line_dash="dash", line_color="red", annotation_text="Right Now", annotation_position="top right")
    
    fig_future.update_layout(xaxis_title="Time", yaxis_title="Generation (MW)", hovermode="x unified", height=400, margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig_future, use_container_width=True)
    
    st.markdown("---")
    
    # 3. Forecast Error Distribution
    st.subheader("🎯 Model Accuracy & Error Distribution")
    
    col_scatter, col_hist = st.columns(2)
    
    # Generate mock 30-day accuracy data
    actuals = np.random.uniform(500, 5000, 300)
    predictions = actuals + np.random.normal(0, actuals * 0.02)  # ~2% error
    errors = actuals - predictions
    
    with col_scatter:
        fig_scatter = go.Figure()
        fig_scatter.add_trace(go.Scatter(x=actuals, y=predictions, mode='markers', marker=dict(color='#9B59B6', size=4, opacity=0.6), name='Actual vs Predicted'))
        # Perfect diagonal line
        fig_scatter.add_trace(go.Scatter(x=[500, 5000], y=[500, 5000], mode='lines', line=dict(color='black', dash='dash'), name='Perfect Accuracy (y=x)'))
        fig_scatter.update_layout(title="Actual vs Predicted (Last 30 Days)", xaxis_title="Actual Generation (MW)", yaxis_title="Predicted Generation (MW)", height=350, margin=dict(l=0, r=0, t=40, b=0), showlegend=False)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    with col_hist:
        fig_hist = px.histogram(x=errors, nbins=30, title="Error Distribution (Actual - Predicted)", labels={'x': 'Error (MW)', 'y': 'Frequency'}, color_discrete_sequence=['#E67E22'])
        fig_hist.update_layout(height=350, margin=dict(l=0, r=0, t=40, b=0))
        st.plotly_chart(fig_hist, use_container_width=True)
        
    st.markdown("---")
    
    # 4. Commercial Trading Action Plan
    st.info("💡 **Trading Insight:** The XGBoost model predicts a 15% surge in wind generation over the next 48 hours due to incoming coastal fronts. Recommend increasing Day-Ahead Market (DAM) volume bids for the evening peak blocks.")

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
        fig.update_traces(mode='lines+markers')
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
            mode='lines+markers', name='DAM Price',
            line=dict(color='#FF6B35', width=1.5)
        ))
        if 'rtm_price_rs_kwh' in iex_f.columns:
            fig.add_trace(go.Scatter(
                x=iex_f['date'], y=iex_f['rtm_price_rs_kwh'],
                mode='lines+markers', name='RTM Price',
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
