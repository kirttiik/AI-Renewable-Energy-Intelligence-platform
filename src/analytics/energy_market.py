import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os

def render_iex_analytics():
    st.title("📈 Energy Market Intelligence (IEX)")
    st.markdown("Analyze daily pricing trends across the Indian Energy Exchange (IEX) to optimize renewable energy sales strategy.")
    
    # 1. Generate/Load simulated IEX data
    dates = pd.date_range(end=pd.Timestamp.today().date(), periods=60)
    np.random.seed(42)
    
    # DAM is the baseline (Day Ahead Market), say around 3.5 to 5.5 INR/kWh
    dam_base = 4.5
    dam_prices = dam_base + np.random.normal(0, 0.4, size=len(dates))
    
    # GDAM (Green Day Ahead Market) typically tracks DAM but might have a slight premium
    gdam_prices = dam_prices + np.random.normal(0.1, 0.2, size=len(dates))
    
    # RTM (Real-Time Market) is much more volatile, spiking when there are sudden grid deficits
    rtm_prices = dam_prices + np.random.normal(0, 1.2, size=len(dates))
    # Occasional extreme spikes
    spike_indices = np.random.choice(len(dates), size=3, replace=False)
    rtm_prices[spike_indices] += np.random.uniform(3, 6, size=3)
    
    # Ensure no negative prices
    dam_prices = np.clip(dam_prices, 1.0, None)
    gdam_prices = np.clip(gdam_prices, 1.0, None)
    rtm_prices = np.clip(rtm_prices, 1.0, None)
    
    df = pd.DataFrame({
        'Date': dates,
        'DAM (INR/kWh)': dam_prices,
        'GDAM (INR/kWh)': gdam_prices,
        'RTM (INR/kWh)': rtm_prices
    })
    
    # KPIs
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Latest GDAM Price", f"₹ {latest['GDAM (INR/kWh)']:.2f}", f"{latest['GDAM (INR/kWh)'] - prev['GDAM (INR/kWh)']:.2f} vs yesterday")
    col2.metric("Latest DAM Price", f"₹ {latest['DAM (INR/kWh)']:.2f}", f"{latest['DAM (INR/kWh)'] - prev['DAM (INR/kWh)']:.2f} vs yesterday")
    col3.metric("Latest RTM Price", f"₹ {latest['RTM (INR/kWh)']:.2f}", f"{latest['RTM (INR/kWh)'] - prev['RTM (INR/kWh)']:.2f} vs yesterday")
    
    st.markdown("---")
    
    # Main Chart
    st.subheader("Market Price Trends (Last 60 Days)")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df['Date'], y=df['DAM (INR/kWh)'], mode='lines', name='DAM', line=dict(color='blue', width=2)))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['GDAM (INR/kWh)'], mode='lines', name='GDAM', line=dict(color='green', width=2)))
    fig.add_trace(go.Scatter(x=df['Date'], y=df['RTM (INR/kWh)'], mode='lines', name='RTM', line=dict(color='red', width=2, dash='dot')))
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Price (INR/kWh)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        height=450
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Interpretation Engine
    st.subheader("🤖 AI Market Interpretation")
    
    # Calculate volatility and spreads
    rtm_volatility = df['RTM (INR/kWh)'].std()
    dam_volatility = df['DAM (INR/kWh)'].std()
    
    avg_gdam_premium = (df['GDAM (INR/kWh)'] - df['DAM (INR/kWh)']).mean()
    rtm_spikes = (df['RTM (INR/kWh)'] > df['DAM (INR/kWh)'] * 1.3).sum()
    
    interpretation = []
    
    if avg_gdam_premium > 0.05:
        interpretation.append(f"✅ **Green Premium:** The Green Day Ahead Market (GDAM) is trading at an average premium of ₹{avg_gdam_premium:.2f}/kWh over the standard DAM. Selling un-contracted renewable generation here is highly favorable.")
    else:
        interpretation.append(f"⚠️ **Weak Green Premium:** GDAM is closely tracking DAM with negligible premium (₹{avg_gdam_premium:.2f}/kWh).")
        
    if rtm_volatility > dam_volatility * 1.5:
        interpretation.append(f"📈 **High RTM Volatility:** The Real-Time Market (RTM) shows significant price instability compared to DAM. In the last 60 days, there were **{rtm_spikes} days** where RTM prices spiked more than 30% above DAM. Holding a small percentage of capacity for RTM could yield windfall profits during grid deficit hours.")
    else:
        interpretation.append(f"⚖️ **Stable RTM:** RTM prices are currently stable and tracking close to day-ahead forecasts. Selling ahead (DAM/GDAM) is currently the lowest-risk strategy.")
        
    for text in interpretation:
        st.info(text)
        
    st.markdown("---")
    st.markdown("**Data Source Note:** *This is a realistic simulated dataset representing Indian Energy Exchange market structures for prototyping purposes.*")
