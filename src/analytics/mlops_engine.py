import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import datetime
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

def render_mlops_hub():
    page_header("⚙️", "MLOps & Model Monitoring",
        "Track model drift, evaluate prediction accuracy, and orchestrate automated ML retraining workflows.")
    help_expander(
        "Monitors the continuous performance of the AI generation models and orchestrates the deployment lifecycle.",
        {
            "MAE": "Mean Absolute Error. Lower is better. Tracks drift over time.",
            "Drift Threshold": "The error limit beyond which the model must be retrained to maintain IEX trading compliance.",
            "Model Registry": "Version control for machine learning models.",
        }
    )
    
    # -------------------------------------------------------------------------
    # 1. Model Drift Monitoring (Module 4)
    # -------------------------------------------------------------------------
    section_title("📉 Model Performance Drift")
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Current Solar MAE", "1.62 MW", "+0.04 MW", delta_color="inverse")
    c2.metric("Current Wind MAE", "4.91 MW", "+0.15 MW", delta_color="inverse")
    c3.metric("Overall Drift Score", "12.4%", "+2.1%", delta_color="inverse")
    c4.metric("Last Retrained", "14 Days Ago")
    
    # Generate drift trend data
    days = [datetime.date.today() - datetime.timedelta(days=i) for i in range(30, 0, -1)]
    base_mae = np.linspace(1.2, 1.6, 30)
    mae_trend = base_mae + np.random.normal(0, 0.1, 30)
    rmse_trend = mae_trend * 1.8 + np.random.normal(0, 0.2, 30)
    
    df_drift = pd.DataFrame({"Date": days, "MAE": mae_trend, "RMSE": rmse_trend})
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_drift["Date"], y=df_drift["MAE"], name="Mean Absolute Error (MAE)", line=dict(color='#E74C3C')))
    fig.add_trace(go.Scatter(x=df_drift["Date"], y=df_drift["RMSE"], name="Root Mean Square Error (RMSE)", line=dict(color='#F39C12')))
    # Add drift threshold line
    fig.add_hline(y=1.5, line_dash="dot", annotation_text="Drift Threshold (1.5)", annotation_position="top left", line_color="red")
    
    fig.update_layout(title="Prediction Error Trend (Last 30 Days)", height=300, margin=dict(t=30, b=0, l=0, r=0))
    fig = style_chart(fig)
    st.plotly_chart(fig, use_container_width=True)
    
    if mae_trend[-1] > 1.5:
        insight_box("**Drift Alert:** Solar model MAE has crossed the acceptable threshold (1.5 MW). Retraining recommended.", "warning")
    else:
        insight_box("Models are performing within acceptable accuracy thresholds.", "success")

    st.markdown("---")
    
    # -------------------------------------------------------------------------
    # 2. Automated Model Retraining (Module 5)
    # -------------------------------------------------------------------------
    section_title("🔄 Automated Retraining Workflow")
    st.markdown("Orchestrate the end-to-end ML training pipeline.")
    
    col_flow, col_action = st.columns([2, 1])
    
    with col_flow:
        st.markdown("""
        **Pipeline Status:**
        - 📥 **1. New Data Ingestion:** 14 new days of data available.
        - ⚙️ **2. Model Retraining:** *Pending Trigger*
        - 📊 **3. Validation:** *Pending*
        - 📦 **4. Model Registry:** Currently on `v2.4.1`
        - 🚀 **5. Deployment:** *Pending*
        """)
        st.progress(20, text="Pipeline Stage: Data Ready (20%)")
        
    with col_action:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚀 Trigger Full Retraining Pipeline", type="primary", use_container_width=True):
            insight_box("Pipeline triggered successfully. (Simulated execution via GitHub Actions / Airflow).", "success")
            insight_box("Check back in ~15 minutes for updated model artifacts.", "info")
            
    st.markdown("---")
    section_title("📦 Model Registry")
    reg_data = {
        "Version": ["v2.4.1 (Active)", "v2.4.0", "v2.3.5", "v2.3.4"],
        "Deployment Date": ["2026-06-20", "2026-06-05", "2026-05-15", "2026-05-01"],
        "Solar R²": [0.96, 0.95, 0.94, 0.92],
        "Wind R²": [0.88, 0.89, 0.85, 0.84],
        "Status": ["Deployed", "Archived", "Archived", "Archived"]
    }
    st.dataframe(pd.DataFrame(reg_data), use_container_width=True)

    executive_insights_section(
        findings=[
            "The active solar model (v2.4.1) is approaching the 1.5 MW MAE drift threshold.",
            "Wind model accuracy remains highly stable.",
            "New training data (14 days) is queued and ready for ingestion.",
        ],
        summary="Model accuracy is gradually decaying as expected due to seasonal weather transitions. Retraining is recommended to maintain IEX trading accuracy.",
        recommendations=[
            "Trigger the automated retraining pipeline prior to the next trading cycle.",
            "Evaluate if the next iteration requires hyperparameter tuning to better capture monsoon dynamics.",
        ]
    )
    page_footer()
