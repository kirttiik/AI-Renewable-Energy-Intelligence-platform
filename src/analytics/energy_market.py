import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

def render_kpi_card(title, value_str, unit="", context_main="", context_sub="", source=""):
    import html
    def get_font_size(text):
        length = len(text)
        if length > 20: return "1.2rem"
        if length > 15: return "1.5rem"
        if length > 10: return "1.8rem"
        return "2rem"

    val_str = html.escape(str(value_str))
    fs = get_font_size(val_str)
    
    html_str = f"""
    <div style="background-color: #1E293B; border-radius: 8px; padding: 16px; margin-bottom: 12px; border-left: 5px solid #3B82F6; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="color: #9CA3AF; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px;">{title}</div>
        <div style="display: flex; align-items: baseline; gap: 4px; margin-bottom: 4px;">
            <div style="color: #F8FAFC; font-size: {fs}; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{val_str}">{val_str}</div>
            <div style="color: #9CA3AF; font-size: 1rem; font-weight: 500;">{unit}</div>
        </div>
        <div style="color: #60A5FA; font-size: 0.85rem; font-weight: 600; margin-bottom: 2px;">{context_main}</div>
        <div style="color: #6B7280; font-size: 0.75rem; font-style: italic; margin-bottom: 6px;">{context_sub}</div>
        <div style="display: inline-block; background-color: #374151; color: #D1D5DB; padding: 2px 6px; border-radius: 4px; font-size: 0.7rem; font-weight: 600;">Data Source: {source}</div>
    </div>
    """
    return html_str

def render_iex_analytics():
    st.title("📈 Energy Market Intelligence (IEX)")
    st.markdown("Analyze actual historical pricing trends from the Indian Energy Exchange (IEX).")
    
    data_path = "data/raw/iex_dam_actuals.csv"
    if not os.path.exists(data_path):
        st.warning(f"IEX Data not found at {data_path}. Please run the scraper pipeline.")
        return
        
    df = pd.read_csv(data_path)
    df.rename(columns=lambda x: x.replace(" *", "").strip(), inplace=True)
    
    if "MCP (Rs/MWh)" not in df.columns:
        st.error("Missing MCP column in scraped data.")
        return
        
    # Process the data
    df['MCP (INR/kWh)'] = df['MCP (Rs/MWh)'] / 1000
    df['Datetime'] = pd.to_datetime(df['Date'] + " " + df['Time Block'].str.split(" - ").str[0], format="%d-%m-%Y %H:%M")
    
    # Simulate RTM spread to show comparative analysis
    np.random.seed(42)
    df['RTM (INR/kWh)'] = df['MCP (INR/kWh)'] + np.random.normal(0, 0.5, size=len(df))
    # Occasional spikes
    spike_indices = np.random.choice(len(df), size=max(1, len(df)//20), replace=False)
    df.loc[spike_indices, 'RTM (INR/kWh)'] += np.random.uniform(2, 4, size=len(spike_indices))
    df['RTM (INR/kWh)'] = np.clip(df['RTM (INR/kWh)'], 0.5, None)
    
    # Calculate daily averages for the macro view
    daily_df = df.groupby('Date').agg(
        avg_dam=('MCP (INR/kWh)', 'mean'),
        avg_rtm=('RTM (INR/kWh)', 'mean'),
        peak_dam=('MCP (INR/kWh)', 'max'),
        min_dam=('MCP (INR/kWh)', 'min')
    ).reset_index()
    daily_df['SortDate'] = pd.to_datetime(daily_df['Date'], format="%d-%m-%Y")
    daily_df.sort_values(by='SortDate', inplace=True)
    
    # Overall KPIs
    latest_date = daily_df['Date'].iloc[-1]
    latest_stats = daily_df.iloc[-1]
    
    st.markdown(f"**Latest Data Received:** {latest_date} | **Total Historical Days:** {len(daily_df)}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(render_kpi_card(f"Avg DAM Price ({latest_date})", f"{latest_stats['avg_dam']:.2f}", "₹/kWh", "Day Ahead Market", "Average clearing price across all blocks.", "IEX Scraper"), unsafe_allow_html=True)
    with col2:
        st.markdown(render_kpi_card(f"Peak DAM Price ({latest_date})", f"{latest_stats['peak_dam']:.2f}", "₹/kWh", "Day Ahead Market", "Maximum clearing price recorded.", "IEX Scraper"), unsafe_allow_html=True)
    with col3:
        st.markdown(render_kpi_card(f"Avg RTM Price ({latest_date})", f"{latest_stats['avg_rtm']:.2f}", "₹/kWh", "Real Time Market", "Simulated RTM price estimate.", "Calculated (Sim)"), unsafe_allow_html=True)
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["📊 Daily Historical Trends", "⏱️ Intraday 15-Min Profile"])
    
    with tab1:
        st.subheader("Historical Market Prices (Daily Average)")
        fig_daily = go.Figure()
        fig_daily.add_trace(go.Scatter(x=daily_df['SortDate'], y=daily_df['avg_dam'], mode='lines+markers', name='Avg DAM', line=dict(color='blue', width=2)))
        fig_daily.add_trace(go.Scatter(x=daily_df['SortDate'], y=daily_df['avg_rtm'], mode='lines+markers', name='Avg RTM (Simulated)', line=dict(color='red', width=2, dash='dot')))
        
        fig_daily.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (INR/kWh)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            height=450
        )
        st.plotly_chart(fig_daily, use_container_width=True)
        
    with tab2:
        st.subheader("Granular Intraday Profiling")
        selected_date = st.selectbox("Select Date for Intraday Analysis", daily_df['Date'][::-1])
        intra_df = df[df['Date'] == selected_date].copy()
        
        fig_intra = go.Figure()
        fig_intra.add_trace(go.Scatter(x=intra_df['Datetime'], y=intra_df['MCP (INR/kWh)'], mode='lines', name='DAM', line=dict(color='blue', width=2)))
        fig_intra.add_trace(go.Scatter(x=intra_df['Datetime'], y=intra_df['RTM (INR/kWh)'], mode='lines', name='RTM (Sim)', line=dict(color='red', width=2, dash='dot')))
        
        fig_intra.update_layout(
            xaxis_title="Time",
            yaxis_title="Price (INR/kWh)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            hovermode="x unified",
            height=450
        )
        st.plotly_chart(fig_intra, use_container_width=True)
        
        # Intra-day interpretation
        peak_hour = intra_df.loc[intra_df['MCP (INR/kWh)'].idxmax(), 'Time Block']
        intra_max = intra_df['MCP (INR/kWh)'].max()
        st.info(f"🔥 **Peak Demand Insight ({selected_date}):** The highest clearing price occurred during the **{peak_hour}** block (₹{intra_max:.2f}/kWh). Recommend discharging battery storage or maximizing generation to this window.")

    st.markdown("---")
    st.markdown("**Data Source Note:** *This dashboard is now powered by an automated pipeline appending ACTUAL historical scraped IEX data. RTM is overlaid as a simulated spread for comparative analysis.*")
