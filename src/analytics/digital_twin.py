import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

def render_digital_twin():
    st.title("🛰 Renewable Energy Digital Twin")
    st.markdown("Live physics simulation, asset health monitoring, and automated root cause analysis.")
    
    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 1. Physics Simulation (Module 1)
    # -------------------------------------------------------------------------
    st.subheader("⚙️ Live Physics Simulation")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Expected Generation (MW)", "12,450.5", delta="-120.3", delta_color="inverse")
    c2.metric("Performance Ratio", "82.4%", delta="+0.3%")
    c3.metric("Capacity Factor", "31.2%", delta="-0.5%", delta_color="inverse")
    c4.metric("Cell Temperature", "48.2 °C", delta="+2.1 °C", delta_color="inverse")
    
    # Fake time series data for physics visualization
    hours = list(range(6, 19))
    expected = [500, 1200, 2500, 4000, 5200, 6000, 6200, 6000, 5000, 3500, 2000, 800, 100]
    actual =   [490, 1150, 2400, 3800, 4900, 5600, 5800, 5700, 4800, 3400, 1900, 750, 90]
    df_sim = pd.DataFrame({"Hour": hours, "Expected": expected, "Actual": actual})
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_sim["Hour"], y=df_sim["Expected"], name="Expected (Physics Model)", line=dict(dash='dash', color='gray')))
    fig.add_trace(go.Scatter(x=df_sim["Hour"], y=df_sim["Actual"], name="Actual Generation", fill='tozeroy', line=dict(color='#3498DB')))
    fig.update_layout(title="Generation Envelope: Expected vs Actual", height=300, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 2. Asset Health Index (Module 3)
    # -------------------------------------------------------------------------
    col_ahi, col_rca = st.columns([1, 1])
    
    with col_ahi:
        st.subheader("🏥 Asset Health Index")
        st.markdown("Composite score evaluating efficiency, degradation, and stability.")
        
        health_score = 88
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = health_score,
            title = {'text': "Overall Plant Health Score"},
            gauge = {
                'axis': {'range': [0, 100]},
                'bar': {'color': "#2ECC71" if health_score > 80 else "#F1C40F"},
                'steps': [
                    {'range': [0, 60], 'color': "#E74C3C"},
                    {'range': [60, 80], 'color': "#F1C40F"},
                    {'range': [80, 100], 'color': "rgba(46, 204, 113, 0.2)"}],
            }
        ))
        fig_gauge.update_layout(height=280, margin=dict(t=40, b=0, l=20, r=20))
        st.plotly_chart(fig_gauge, use_container_width=True)
        
        st.markdown("**Health Drivers:**")
        st.progress(85, text="Performance Ratio (85%)")
        st.progress(92, text="Temperature Stress Resilience (92%)")
        st.progress(78, text="Generation Stability (78%)")
        
    # -------------------------------------------------------------------------
    # 3. Root Cause Analysis (Module 6)
    # -------------------------------------------------------------------------
    with col_rca:
        st.subheader("🔍 Root Cause Analysis")
        st.markdown("Attribution of generation variance from theoretical maximum.")
        
        # Waterfall chart for RCA
        fig_rca = go.Figure(go.Waterfall(
            name = "Variance", orientation = "v",
            measure = ["absolute", "relative", "relative", "relative", "relative", "relative", "total"],
            x = ["Theoretical Max", "Cloud Cover", "Temperature", "Soiling", "Inverter Clipping", "Grid Curtailment", "Actual Output"],
            textposition = "outside",
            y = [14000, -850, -420, -150, -80, 0, 12500],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_rca.update_layout(title="Generation Variance Waterfall (MW)", height=350, showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_rca, use_container_width=True)
        
        st.info("**RCA Insight:** Cloud cover attenuation is the primary driver of generation loss today (-850 MW), followed by temperature-induced derating (-420 MW).")
