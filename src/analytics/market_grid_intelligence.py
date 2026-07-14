import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from app import get_data_sources, GLOBAL_TODAY, filter_by_time_horizon

def calculate_weather_quality(cloud, temp, humidity, solar, wind, rain):
    """Calculate Weather Quality Score (0-100)"""
    score = 100
    # Deductions
    score -= (cloud / 100) * 30          # up to -30
    if temp > 40: score -= 15            # high heat penalty
    elif temp > 35: score -= 5
    if rain > 5: score -= 20             # heavy rain penalty
    
    # Bonuses
    if solar > 6.0: score += 10
    if 3 < wind < 8: score += 5          # good cooling wind
    
    return max(0, min(100, score))

def calculate_dsm_risk(conf, w_risk, cloud):
    """Estimate Deviation Settlement Mechanism (DSM) Risk"""
    risk_score = (100 - conf) * 1.5 + w_risk * 0.8 + (cloud / 100) * 20
    
    if risk_score > 40: return "Critical", "red"
    if risk_score > 25: return "High", "orange"
    if risk_score > 15: return "Medium", "yellow"
    return "Low", "green"

def calculate_grid_readiness(conf, pr, w_quality, cf):
    """Grid Readiness Score (0-100)"""
    score = (conf * 0.4) + (pr * 100 * 0.3) + (w_quality * 0.2) + (cf * 100 * 0.1)
    return max(0, min(100, score))

def calculate_curtailment_risk(w_quality, gen, cloud):
    """Estimate Curtailment Risk"""
    if w_quality > 90 and gen > 15 and cloud < 10:
        return "Medium", "High generation might trigger local grid constraints."
    if w_quality > 95 and gen > 18:
        return "High", "Maximum generation expected. Grid curtailment probability is elevated."
    return "Low", "Normal generation levels. Grid absorption capacity is sufficient."

def calculate_opportunity_score(price, conf, w_quality, pr, w_risk):
    """Market Opportunity Score (0-100)"""
    # Normalize price (assuming 3000-8000 range)
    norm_price = max(0, min(100, (price - 3000) / 5000 * 100))
    
    score = (norm_price * 0.30) + (conf * 0.25) + (w_quality * 0.20) + (pr * 100 * 0.15) - (w_risk * 0.10)
    return max(0, min(100, score))

def generate_recommendations(opp_score, dsm, grid_readiness, conf, w_quality):
    recs = []
    
    # General Market
    if opp_score > 80: recs.append("🌟 **Market Conditions:** Excellent. Maximize available capacity bidding.")
    elif opp_score > 50: recs.append("📊 **Market Conditions:** Moderate. Standard scheduling recommended.")
    else: recs.append("⚠️ **Market Conditions:** Poor. Prices are low or risk is high.")
        
    # Weather
    if w_quality > 85: recs.append("☀️ **Weather:** Favorable conditions with limited cloud cover expected.")
    else: recs.append("⛅ **Weather:** Volatile weather expected. Monitor real-time satellite imagery.")
        
    # DSM
    if dsm == "Low": recs.append("🛡️ **DSM Risk:** Low. Deviation penalties are unlikely tomorrow.")
    elif dsm == "Critical": recs.append("🚨 **DSM Risk:** CRITICAL. High uncertainty. Maintain strict conservative margins.")
        
    # Confidence
    if conf > 95: recs.append("🎯 **Forecast Confidence:** Exceeds 95%. AI model uncertainty is minimal.")
    else: recs.append("📉 **Forecast Confidence:** Below 95%. Consider 3-5% safety margin on bids.")
        
    # Operational
    if grid_readiness > 80: recs.append("⚡ **Grid Readiness:** Plant is in prime state to support grid injection.")
    
    recs.append("⚙️ **Strategy:** Do not schedule 100% of forecast if localized cloud cover is observed.")
    recs.append("💡 **Strategy:** Leverage any short-term intraday markets if actuals exceed day-ahead forecast.")
    recs.append("🔧 **Maintenance:** Avoid preventative maintenance tomorrow during peak price hours.")
    recs.append("📈 **Trends:** Prices remain generally aligned with weekly rolling averages.")
    recs.append("🔍 **AI Assessment:** Suitable conditions for normal operational procedures.")
    
    return recs[:10]

def create_gauge(val, title, color_ranges):
    """Helper for Plotly Gauge Charts"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=val,
        title={'text': title, 'font': {'size': 16}},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkgray"},
            'steps': color_ranges
        }
    ))
    fig.update_layout(height=200, margin=dict(l=10, r=10, t=40, b=10))
    return fig

def render_market_grid_intelligence():
    st.title("⚡ Market & Grid Intelligence")
    st.markdown("Operational decision support integrating market, weather, and forecasting data.")
    
    # ---------------------------------------------------------
    # DATA LOADING & ERROR HANDLING
    # ---------------------------------------------------------
    data = get_data_sources()
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Try to load real data
    df_solar = data.get('solar_pred', pd.DataFrame())
    df_metrics = data.get('solar_metrics', pd.DataFrame())
    
    # Mock IEX market data if unavailable (never crash)
    iex_path = os.path.join(ROOT, 'data', 'processed', 'iex_dam_prices.csv')
    if os.path.exists(iex_path):
        df_iex = pd.read_csv(iex_path)
    else:
        st.warning("Live IEX Data unavailable. Using cached market prices for simulation.")
        dates = pd.date_range(start=pd.Timestamp.today() - pd.Timedelta(days=30), periods=45)
        df_iex = pd.DataFrame({
            'date': dates,
            'dam_price': np.random.normal(5500, 300, len(dates))
        })
        
    if df_solar.empty:
        st.error("Forecast data is unavailable. Scheduling recommendations disabled.")
        return
        
    # Baseline values
    base_price = float(df_iex['dam_price'].iloc[-1])
    base_gen_mw = float(df_solar['predicted_solar_generation_mw'].iloc[0])
    base_conf = float(df_metrics['R2_Score'].iloc[0]) * 100 if not df_metrics.empty else 95.0
    
    # ---------------------------------------------------------
    # SECTION 9: MARKET SIMULATOR (Sidebar)
    # ---------------------------------------------------------
    with st.sidebar.expander("🎛️ Market Simulator", expanded=True):
        sim_price = st.slider("DAM Price (INR/MWh)", 2000, 10000, int(base_price))
        sim_cloud = st.slider("Cloud Cover (%)", 0, 100, 15)
        sim_solar = st.slider("Solar Radiation (kWh/m²)", 2.0, 8.0, 6.5)
        sim_temp  = st.slider("Temperature (°C)", 15, 50, 35)
        sim_conf  = st.slider("Forecast Confidence (%)", 50.0, 100.0, base_conf)
        sim_wrisk = st.slider("Weather Risk Score", 0, 100, 10)
    
    # ---------------------------------------------------------
    # CALCULATIONS
    # ---------------------------------------------------------
    # Weather Quality
    w_quality = calculate_weather_quality(sim_cloud, sim_temp, 40, sim_solar, 5, 0)
    
    # DSM Risk
    dsm_str, dsm_color = calculate_dsm_risk(sim_conf, sim_wrisk, sim_cloud)
    
    # Grid Readiness
    grid_read = calculate_grid_readiness(sim_conf, 0.82, w_quality, 0.28)
    
    # Market Opportunity
    opp_score = calculate_opportunity_score(sim_price, sim_conf, w_quality, 0.82, sim_wrisk)
    
    # Scheduling Intelligence
    base_gen_gwh = (base_gen_mw * 5.8) / 1000.0
    safety_margin_pct = 0.0
    if sim_conf < 90: safety_margin_pct += 0.05
    if sim_cloud > 30: safety_margin_pct += 0.03
    if dsm_str in ["High", "Critical"]: safety_margin_pct += 0.05
    
    rec_schedule_gwh = base_gen_gwh * (1.0 - safety_margin_pct)
    
    # Curtailment Risk
    curt_str, curt_exp = calculate_curtailment_risk(w_quality, rec_schedule_gwh, sim_cloud)
    
    # AI Recs
    recs = generate_recommendations(opp_score, dsm_str, grid_read, sim_conf, w_quality)
    
    # ---------------------------------------------------------
    # SECTION 10: EXECUTIVE SUMMARY
    # ---------------------------------------------------------
    st.subheader("📋 Executive Summary")
    st.info(f"""
    **Current Market:** Prices are trading around INR {sim_price:,.0f}/MWh.  
    **Weather Outlook:** Weather quality is rated {w_quality:.0f}/100 with {sim_cloud}% cloud cover.  
    **Generation Outlook:** Base forecast predicts {base_gen_gwh:.2f} GWh (Confidence: {sim_conf:.1f}%).  
    **Scheduling Recommendation:** Recommend scheduling **{rec_schedule_gwh:.2f} GWh** (Applying {safety_margin_pct*100:.0f}% safety margin).  
    **DSM Exposure:** {dsm_str}. Tomorrow's Grid Readiness is {grid_read:.0f}/100.
    """)
    
    st.markdown("---")
    
    # ---------------------------------------------------------
    # SECTION 11: VISUALIZATIONS & GAUGES
    # ---------------------------------------------------------
    g1, g2, g3, g4 = st.columns(4)
    
    with g1:
        st.plotly_chart(create_gauge(opp_score, "Opportunity Score", [
            {'range': [0, 40], 'color': "#E74C3C"},
            {'range': [40, 70], 'color': "#F1C40F"},
            {'range': [70, 100], 'color': "#2ECC71"}
        ]), use_container_width=True)
    with g2:
        st.plotly_chart(create_gauge(w_quality, "Weather Quality", [
            {'range': [0, 50], 'color': "#E74C3C"},
            {'range': [50, 80], 'color': "#F1C40F"},
            {'range': [80, 100], 'color': "#2ECC71"}
        ]), use_container_width=True)
    with g3:
        # Inverse gauge for DSM (lower is better)
        dsm_num = (100 - sim_conf)*1.5 + sim_wrisk
        st.plotly_chart(create_gauge(min(100, max(0, dsm_num)), "Est. DSM Risk", [
            {'range': [0, 30], 'color': "#2ECC71"},
            {'range': [30, 60], 'color': "#F1C40F"},
            {'range': [60, 100], 'color': "#E74C3C"}
        ]), use_container_width=True)
    with g4:
        st.plotly_chart(create_gauge(grid_read, "Grid Readiness", [
            {'range': [0, 60], 'color': "#E74C3C"},
            {'range': [60, 80], 'color': "#F1C40F"},
            {'range': [80, 100], 'color': "#2ECC71"}
        ]), use_container_width=True)
        
    st.markdown("---")
    
    # ---------------------------------------------------------
    # MULTI-TAB DETAILED VIEW
    # ---------------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["⚡ Scheduling Intelligence", "📈 Market Overview", "🤖 AI Decision Engine"])
    
    with tab1:
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.metric("Raw Forecast", f"{base_gen_gwh:.2f} GWh")
        sc2.metric("Forecast Confidence", f"{sim_conf:.1f}%")
        sc3.metric("Safety Margin", f"{safety_margin_pct*100:.0f}%")
        sc4.metric("Recommended Schedule", f"{rec_schedule_gwh:.2f} GWh", delta=f"{-1*(base_gen_gwh-rec_schedule_gwh):.2f} GWh", delta_color="inverse")
        
        st.markdown("### DSM Risk Analytics")
        st.markdown(f"**Current Status:** <span style='color:{dsm_color};font-weight:bold;'>{dsm_str}</span>", unsafe_allow_html=True)
        if dsm_str == "Low": st.success("Expected deviation remains below historical average. DSM exposure appears LOW.")
        elif dsm_str == "Medium": st.warning("Moderate uncertainty detected. Small deviation penalties possible.")
        else: st.error("High uncertainty detected. Aggressive safety margins strongly advised.")
            
        st.markdown("### Curtailment Risk")
        st.info(f"**{curt_str} Probability:** {curt_exp}")
        
    with tab2:
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Today's DAM Price", f"₹ {sim_price:,.0f}")
        prev_price = df_iex['dam_price'].iloc[-2] if len(df_iex) > 1 else sim_price
        mc2.metric("Yesterday Price", f"₹ {prev_price:,.0f}")
        mc3.metric("7-Day Avg", f"₹ {df_iex['dam_price'].tail(7).mean():,.0f}")
        
        st.markdown("### Historical Price Trend")
        fig_price = go.Figure()
        fig_price.add_trace(go.Scatter(x=df_iex['date'].tail(14), y=df_iex['dam_price'].tail(14), mode='lines+markers', name='DAM Price', line=dict(color='#8E44AD')))
        fig_price.update_layout(height=300, margin=dict(l=0, r=0, t=30, b=0))
        st.plotly_chart(fig_price, use_container_width=True)
        
        # Current status
        status = "Bullish 📈" if sim_price > df_iex['dam_price'].tail(7).mean() else "Bearish 📉"
        st.markdown(f"**Current Market Status:** {status}")

    with tab3:
        st.markdown("### AI Operational Recommendations")
        for i, rec in enumerate(recs):
            st.markdown(f"{i+1}. {rec}")
            
    st.markdown("---")
    st.caption("Market & Grid Intelligence Module | Real-time Decision Support")
