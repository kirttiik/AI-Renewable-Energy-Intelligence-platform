import streamlit as st
import pandas as pd
import plotly.express as px

def render_predictive_maintenance():
    st.title("🛠 Predictive Maintenance & Scenarios")
    st.markdown("Forecast asset degradation, prioritize maintenance schedules, and simulate extreme operational scenarios.")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 1. Predictive Maintenance (Module 2)
    # -------------------------------------------------------------------------
    st.subheader("🔧 Predictive Maintenance Queue")
    
    data = {
        "Asset Group": ["Inverter Block A", "PV Module Array C", "Inverter Block B", "Transformer T-02", "Tracker System X"],
        "Health Score": [72, 81, 88, 94, 76],
        "Temperature Stress": ["HIGH", "MEDIUM", "LOW", "LOW", "MEDIUM"],
        "Maintenance Priority": ["CRITICAL", "HIGH", "NORMAL", "LOW", "HIGH"],
        "Recommended Action": ["Inspect cooling fans", "Schedule wet wash", "Routine check", "No action", "Lubricate actuators"]
    }
    df_maint = pd.DataFrame(data)
    
    def color_priority(val):
        color = 'red' if val == 'CRITICAL' else 'orange' if val == 'HIGH' else 'green' if val == 'NORMAL' else 'grey'
        return f'color: {color}; font-weight: bold'
        
    st.dataframe(df_maint.style.applymap(color_priority, subset=['Maintenance Priority']), use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    c1.warning("⚠️ **Alert:** Inverter Block A showing severe temperature stress.")
    c2.info("💡 **Recommendation:** Delay tracker maintenance until high-wind period passes.")
    c3.success("✅ **Status:** Transformer temperatures are within normal limits.")

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 2. Advanced Scenario Planning (Module 8)
    # -------------------------------------------------------------------------
    st.subheader("🌩 Advanced Scenario Simulator")
    st.markdown("Simulate the impact of predefined extreme conditions on plant performance.")
    
    scenario = st.radio("Select Simulation Scenario:", 
                        ["Extreme Heatwave (+5°C Ambient)", 
                         "Severe Monsoon (80% Cloud Cover)", 
                         "Heavy Dust Storm (High Soiling)", 
                         "Grid Curtailment (Max 10,000 MW)",
                         "IEX Market Spike (DAM Price > ₹10/kWh)"],
                        horizontal=True)
                        
    col_sim1, col_sim2 = st.columns(2)
    
    with col_sim1:
        if "Heatwave" in scenario:
            st.error("**Simulation Results: Extreme Heatwave**")
            st.metric("Estimated Cell Temp Peak", "62.5 °C", "+14.3 °C", delta_color="inverse")
            st.metric("Efficiency Loss", "5.8%", "+2.1%", delta_color="inverse")
            st.metric("Generation Impact", "-840 MW")
        elif "Monsoon" in scenario:
            st.info("**Simulation Results: Severe Monsoon**")
            st.metric("Effective Irradiance Drop", "65%", "-45%", delta_color="inverse")
            st.metric("Performance Ratio", "78%", "-4%", delta_color="inverse")
            st.metric("Generation Impact", "-4,200 MW")
        elif "Dust Storm" in scenario:
            st.warning("**Simulation Results: Heavy Dust Storm**")
            st.metric("Soiling Loss", "8.5%", "+7.3%", delta_color="inverse")
            st.metric("Tracker Jam Risk", "HIGH")
            st.metric("Maintenance Trigger", "Immediate Wash Required")
        elif "Curtailment" in scenario:
            st.error("**Simulation Results: Grid Curtailment**")
            st.metric("Clipped Energy", "2,450 MWh")
            st.metric("Financial Loss (Estimated)", "₹ 85.7 Lakhs")
        elif "Market Spike" in scenario:
            st.success("**Simulation Results: Market Spike**")
            st.metric("Target Output", "Maximum Available")
            st.metric("Projected Revenue Surge", "+24.5%")
            st.metric("Recommendation", "Defer all maintenance. Maximize output.")
            
    with col_sim2:
        # Generic chart to show "Baseline vs Simulated"
        import numpy as np
        hours = list(range(6, 19))
        baseline = np.array([500, 1200, 2500, 4000, 5200, 6000, 6200, 6000, 5000, 3500, 2000, 800, 100])
        
        if "Heatwave" in scenario: sim = baseline * 0.92
        elif "Monsoon" in scenario: sim = baseline * 0.35
        elif "Dust" in scenario: sim = baseline * 0.91
        elif "Curtailment" in scenario: sim = np.clip(baseline, 0, 5000)
        else: sim = baseline * 1.05
        
        df_chart = pd.DataFrame({"Hour": hours, "Baseline": baseline, "Simulated": sim})
        fig = px.line(df_chart, x="Hour", y=["Baseline", "Simulated"], title="Generation Curve Comparison")
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
