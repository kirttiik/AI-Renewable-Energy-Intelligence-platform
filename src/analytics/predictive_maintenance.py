import streamlit as st
import pandas as pd
import plotly.express as px
import os
import sys

_APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)
try:
    from src.ui.design_system import (
        page_header, help_expander, section_title, style_chart,
        insight_box, executive_insights_section, page_footer
    )
except ImportError:
    def page_header(icon, title, desc): st.title(f"{icon} {title}")
    def help_expander(desc, kpis): pass
    def section_title(text): st.subheader(text)
    def style_chart(fig, title=""): return fig
    def insight_box(text, kind="info"): st.info(text)
    def executive_insights_section(findings, summary, recommendations): pass
    def page_footer(): pass

def render_predictive_maintenance():
    page_header("🛠", "Operations & Maintenance",
        "Forecast asset degradation, prioritize maintenance schedules, and simulate extreme operational scenarios.")
    help_expander(
        "Combines physical sensor data with AI anomaly detection to predict asset failures before they occur.",
        {
            "Health Score": "Current operational health of the specific asset group.",
            "Temperature Stress": "Thermal load placed on the asset based on current operating conditions.",
            "Maintenance Priority": "AI-ranked priority queue for the engineering team.",
        }
    )
    
    # -------------------------------------------------------------------------
    # 1. Predictive Maintenance (Module 2)
    # -------------------------------------------------------------------------
    section_title("🔧 Predictive Maintenance Queue")
    
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
        
    st.dataframe(df_maint.style.map(color_priority, subset=['Maintenance Priority']), use_container_width=True)
    
    c1, c2, c3 = st.columns(3)
    with c1: insight_box("**Alert:** Inverter Block A showing severe temperature stress.", "danger")
    with c2: insight_box("**Recommendation:** Delay tracker maintenance until high-wind period passes.", "warning")
    with c3: insight_box("**Status:** Transformer temperatures are within normal limits.", "success")

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 2. Advanced Scenario Planning (Module 8)
    # -------------------------------------------------------------------------
    section_title("🌩 Advanced Scenario Simulator")
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
        fig = style_chart(fig)
        fig.update_layout(height=300, margin=dict(t=30, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)

    executive_insights_section(
        findings=[
            "Inverter Block A requires immediate thermal inspection.",
            "Scenario analysis shows that extreme heatwaves will cause a ~5.8% drop in generation efficiency.",
            "Heavy dust accumulation poses a severe risk to tracker actuators.",
        ],
        summary="Predictive maintenance models indicate localized thermal stress on specific inverter blocks, though overall plant health remains robust.",
        recommendations=[
            "Dispatch engineering team to Inverter Block A immediately.",
            "Prepare wet wash schedule for PV Module Array C within the next 48 hours.",
        ]
    )
    page_footer()
