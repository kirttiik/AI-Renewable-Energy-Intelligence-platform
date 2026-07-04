import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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

def render_portfolio_analytics():
    page_header("🌍", "Portfolio Analytics",
        "Aggregated generation, financial, and health metrics across all managed renewable energy assets.")
    help_expander(
        "Provides a macro-level view of AGEL's entire renewable portfolio, benchmarking asset performance geographically.",
        {
            "Total Managed Capacity": "Sum of all active renewable assets across India.",
            "Avg Portfolio Health": "Capacity-weighted average of individual asset health scores.",
            "Total Daily Revenue": "Estimated daily revenue generated across the fleet based on spot and PPA prices.",
        }
    )
    
    # -------------------------------------------------------------------------
    # Portfolio Analytics (Module 7)
    # -------------------------------------------------------------------------
    
    # Simulated Portfolio Data
    sites = ["Khavda (Active)", "Kamuthi", "Kurnool", "Bhadla"]
    capacity = [30000, 648, 1000, 2245]
    today_gen = [12500, 420, 710, 1500]
    health = [88, 92, 75, 81]
    revenue = [450, 18, 25, 60] # in Lakhs
    
    df_port = pd.DataFrame({
        "Site": sites,
        "Capacity (MW)": capacity,
        "Today's Gen (MW)": today_gen,
        "Health Score": health,
        "Est. Revenue (Lakhs INR)": revenue
    })
    
    # High-level KPIs
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Managed Capacity", f"{sum(capacity):,} MW")
    c2.metric("Total Generation Today", f"{sum(today_gen):,} MW")
    c3.metric("Avg Portfolio Health", f"{sum(health)/len(health):.1f} / 100")
    c4.metric("Total Daily Revenue", f"₹ {sum(revenue)} Lakhs")
    
    st.markdown("---")
    
    col_chart, col_table = st.columns([1, 1])
    
    with col_chart:
        section_title("Generation Distribution")
        fig = px.pie(df_port, values="Today's Gen (MW)", names="Site", hole=0.4, title="Generation by Site")
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=350, margin=dict(t=40, b=0, l=0, r=0))
        fig = style_chart(fig)
        st.plotly_chart(fig, use_container_width=True)
        
    with col_table:
        section_title("Site Performance Matrix")
        
        def color_health(val):
            color = 'green' if val > 85 else 'orange' if val > 70 else 'red'
            return f'color: {color}; font-weight: bold'
            
        st.dataframe(df_port.style.map(color_health, subset=['Health Score']), use_container_width=True, height=350)
        
    st.markdown("---")
    section_title("🌍 Geographic Asset Map")
    insight_box("Mapping integration requires GPS coordinate setup. Currently displaying simulated asset locations.", "info")
    
    # Dummy coordinates for the plants
    map_data = pd.DataFrame({
        "lat": [23.95, 9.35, 15.68, 27.53],
        "lon": [69.83, 78.38, 78.10, 71.91],
        "size": capacity,
        "Site": sites
    })
    
    st.map(map_data, zoom=4, use_container_width=True)

    executive_insights_section(
        findings=[
            f"Khavda dominates the portfolio, accounting for {capacity[0]/sum(capacity)*100:.1f}% of total capacity.",
            "Kurnool is currently exhibiting the lowest health score (75) and requires operational review.",
            "Total daily revenue across the fleet exceeds ₹ 550 Lakhs.",
        ],
        summary="The renewable energy portfolio is performing robustly. Khavda's massive scale is driving the vast majority of generation and revenue.",
        recommendations=[
            "Dispatch a regional maintenance audit team to the Kurnool site.",
            "Use Khavda's high performance as a benchmark for Kamuthi and Bhadla operations.",
        ]
    )
    page_footer()
