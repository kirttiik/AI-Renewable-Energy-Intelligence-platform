import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

import datetime

def render_digital_twin(horizon="All Time", custom_start=None, custom_end=None):
    st.title(" PVLib Model")
    st.markdown("Live physics simulation, asset health monitoring, and automated root cause analysis.")
    
    st.markdown("---")
    
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    gen_path = os.path.join(ROOT, 'data', 'processed', 'khavda_generation.csv')
    df = pd.DataFrame()
    if os.path.exists(gen_path):
        df = pd.read_csv(gen_path)
        df['date'] = pd.to_datetime(df['date']).dt.date
        df = df.dropna(subset=['solar_generation_mw'])
        df = df.sort_values('date')
        
        # Filter by horizon
        global_today = datetime.date(2026, 9, 5)
        if horizon == "Today":
            df = df[df['date'] == global_today]
        elif horizon == "Yesterday":
            df = df[df['date'] == global_today - datetime.timedelta(days=1)]
        elif horizon == "Tomorrow":
            df = df[df['date'] == global_today + datetime.timedelta(days=1)]
        elif horizon == "Next 14 Days":
            df = df[(df['date'] >= global_today) & (df['date'] <= global_today + datetime.timedelta(days=14))]
        elif horizon == " Custom Range" and custom_start and custom_end:
            df = df[(df['date'] >= custom_start) & (df['date'] <= custom_end)]
            
    if df.empty:
        if horizon in ["Tomorrow", "Next 14 Days"]:
            st.info("The Live Physics Engine requires actual observed weather data to calculate generation, which is not available for future dates. To view future predictions, please navigate to the **Generation Forecast** module (powered by our ML models).")
        else:
            st.error(f"No simulation data available for the selected timeframe ({horizon}).")
        return

    last_row = df.iloc[-1]
    prev_row = df.iloc[-2] if len(df) > 1 else last_row
    
    # -------------------------------------------------------------------------
    # 1. Physics Simulation (Module 1)
    # -------------------------------------------------------------------------
    st.subheader(" Live Physics Simulation")
    c1, c2, c3, c4 = st.columns(4)
    
    expected_gen = last_row.get('solar_generation_mw', 12450.5)
    expected_gen_prev = prev_row.get('solar_generation_mw', expected_gen)
    delta_gen = expected_gen - expected_gen_prev
    
    pr = last_row.get('performance_ratio', 0.82) * 100
    pr_prev = prev_row.get('performance_ratio', pr/100) * 100
    delta_pr = pr - pr_prev
    
    cf = last_row.get('capacity_factor', 0.312) * 100
    cf_prev = prev_row.get('capacity_factor', cf/100) * 100
    delta_cf = cf - cf_prev
    
    temp = last_row.get('cell_temperature_c', 48.2)
    temp_prev = prev_row.get('cell_temperature_c', temp)
    delta_temp = temp - temp_prev
    
    c1.metric("Peak Generation (MW)", f"{expected_gen:,.1f}", delta=f"{delta_gen:+.1f}")
    c2.metric("Performance Ratio", f"{pr:.1f}%", delta=f"{delta_pr:+.1f}%")
    c3.metric("Capacity Factor", f"{cf:.1f}%", delta=f"{delta_cf:+.1f}%")
    c4.metric("Cell Temperature", f"{temp:.1f} °C", delta=f"{delta_temp:+.1f} °C", delta_color="inverse")
    
    # Plot Generation vs Physics Baseline
    df_plot = df.tail(14)
    fig = go.Figure()
    baseline = df_plot.get('physics_baseline_mw', df_plot['solar_generation_mw'] * 1.05)
    fig.add_trace(go.Scatter(x=df_plot["date"], y=baseline, mode='lines+markers', name="Physics Baseline (Theoretical Max)", line=dict(dash='dash', color='gray')))
    fig.add_trace(go.Scatter(x=df_plot["date"], y=df_plot["solar_generation_mw"], mode='lines+markers', name="Actual Peak Generation", fill='tozeroy', line=dict(color='#3498DB')))
    fig.update_layout(title="Daily Peak Generation: Physics Baseline vs Actual", height=300, margin=dict(t=30, b=0, l=0, r=0))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 2. Asset Health Index (Module 3)
    # -------------------------------------------------------------------------
    col_ahi, col_rca = st.columns([1, 1])
    
    def safe_int(v, default=0):
        try:
            return default if pd.isna(v) else int(v)
        except:
            return default

    soiling = last_row.get('soiling_loss_pct', 2.0)
    inv_avail = last_row.get('inverter_availability_pct', 100.0)
    
    # Simple weighted health score
    health_score = safe_int((pr * 0.4) + (inv_avail * 0.4) + ((100 - soiling) * 0.2), 85)
    
    with col_ahi:
        st.subheader(" Asset Health Index")
        st.markdown("Composite score evaluating efficiency, degradation, and stability.")
        
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
        st.progress(safe_int(pr, 80), text=f"Performance Ratio ({pr:.1f}%)")
        st.progress(safe_int(inv_avail, 100), text=f"Inverter Availability ({inv_avail:.1f}%)")
        clean_score = safe_int(100 - soiling, 98)
        st.progress(clean_score, text=f"Panel Cleanliness ({clean_score:.1f}%)")
        
    # -------------------------------------------------------------------------
    # 3. Root Cause Analysis (Module 6)
    # -------------------------------------------------------------------------
    with col_rca:
        st.subheader(" Root Cause Analysis")
        st.markdown("Attribution of generation variance from theoretical maximum.")
        
        # Calculate MW losses based on 20000 capacity
        cap = 20000
        cloud_factor = last_row.get('cloud_factor', 1.0)
        temp_factor = last_row.get('temperature_factor', 1.0)
        
        loss_cloud = -safe_int(cap * (1 - cloud_factor))
        loss_temp = -safe_int(cap * (1 - temp_factor))
        loss_soil = -safe_int(cap * (soiling / 100))
        loss_inv = -safe_int(cap * (1 - inv_avail / 100))
        
        actual_output = safe_int(expected_gen)
        
        # Waterfall chart for RCA
        fig_rca = go.Figure(go.Waterfall(
            name = "Variance", orientation = "v",
            measure = ["absolute", "relative", "relative", "relative", "relative", "total"],
            x = ["DC Capacity", "Cloud Cover", "Temp Derating", "Soiling", "Inv/Grid Losses", "Actual Peak Output"],
            textposition = "outside",
            y = [cap, loss_cloud, loss_temp, loss_soil, loss_inv, actual_output],
            connector = {"line":{"color":"rgb(63, 63, 63)"}},
        ))
        fig_rca.update_layout(title="Generation Variance Waterfall (MW)", height=350, showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig_rca, use_container_width=True)
        
        # Dynamic RCA Insight
        losses = {"Cloud cover": abs(loss_cloud), "Temperature derating": abs(loss_temp), "Soiling": abs(loss_soil)}
        primary_driver = max(losses, key=losses.get)
        st.info(f"**RCA Insight:** {primary_driver} is the primary driver of generation loss today ({losses[primary_driver]} MW).")
