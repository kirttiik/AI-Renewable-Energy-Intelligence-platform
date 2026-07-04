import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

def render_portfolio_analytics():
    st.title("🌍 Portfolio Analytics")
    st.markdown("Aggregated generation, financial, and health metrics across all managed renewable energy assets.")
    
    st.markdown("---")
    
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
        st.subheader("Generation Distribution")
        fig = px.pie(df_port, values="Today's Gen (MW)", names="Site", hole=0.4, title="Generation by Site")
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(height=350, margin=dict(t=40, b=0, l=0, r=0))
        st.plotly_chart(fig, use_container_width=True)
        
    with col_table:
        st.subheader("Site Performance Matrix")
        
        def color_health(val):
            color = 'green' if val > 85 else 'orange' if val > 70 else 'red'
            return f'color: {color}; font-weight: bold'
            
        st.dataframe(df_port.style.applymap(color_health, subset=['Health Score']), use_container_width=True, height=350)
        
    st.markdown("---")
    st.subheader("🌍 Geographic Asset Map")
    st.info("Mapping integration requires GPS coordinate setup. Currently displaying simulated asset locations.")
    
    # Dummy coordinates for the plants
    map_data = pd.DataFrame({
        "lat": [23.95, 9.35, 15.68, 27.53],
        "lon": [69.83, 78.38, 78.10, 71.91],
        "size": capacity,
        "Site": sites
    })
    
    st.map(map_data, zoom=4, use_container_width=True)
