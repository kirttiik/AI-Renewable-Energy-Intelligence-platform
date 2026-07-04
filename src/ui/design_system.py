"""
design_system.py
─────────────────
Enterprise Design System for the Khavda Renewable Energy Digital Twin.

All UI helper functions are defined here and imported into app.py.
DO NOT modify any analytics, ML, or pipeline logic in this file.
"""

from __future__ import annotations
import datetime
import pandas as pd
import streamlit as st

# ── Platform constants ────────────────────────────────────────────────────────
PLATFORM_VERSION  = "v3.1.0"
PLATFORM_NAME     = "Khavda Digital Twin"
PLATFORM_CLIENT   = "Adani Green Energy Ltd."
DATA_SOURCES      = "NASA POWER · Open-Meteo · IEX India · pvlib"

# ── Chart defaults ────────────────────────────────────────────────────────────
CHART_HEIGHT       = 340
CHART_TEMPLATE     = "plotly_white"
CHART_FONT_FAMILY  = "Inter, Segoe UI, sans-serif"
CHART_FONT_SIZE    = 12
CHART_MARGINS      = dict(t=40, b=20, l=10, r=10)
ACCENT_COLOR       = "#1E3D59"
SUCCESS_COLOR      = "#2ECC71"
WARNING_COLOR      = "#F39C12"
DANGER_COLOR       = "#E74C3C"
INFO_COLOR         = "#3498DB"
NEUTRAL_COLOR      = "#BDC3C7"

# ── Global CSS ────────────────────────────────────────────────────────────────
ENTERPRISE_CSS = """
<style>
/* ── Typography & Base ─────────────────── */
html, body, [class*="css"] {
    font-family: 'Segoe UI', Inter, system-ui, sans-serif;
}

/* ── Page header bar ───────────────────── */
.ent-page-header {
    background: linear-gradient(135deg, #1E3D59 0%, #16324a 100%);
    border-radius: 10px;
    padding: 18px 24px 14px;
    margin-bottom: 18px;
    border-left: 5px solid #F1C40F;
}
.ent-page-header h1 {
    color: #FFFFFF !important;
    font-size: 1.5rem !important;
    margin: 0 0 4px 0 !important;
    font-weight: 600 !important;
}
.ent-page-header .desc  { color: #BDC3C7; font-size: 0.87rem; margin: 0; }
.ent-page-header .ts    { color: #7F8C8D; font-size: 0.78rem; margin-top: 6px; }

/* ── KPI metric cards ──────────────────── */
div[data-testid="metric-container"] {
    background: #FFFFFF;
    border: 1px solid #E8ECF0;
    border-radius: 8px;
    padding: 12px 16px;
    border-left: 4px solid #1E3D59;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
div[data-testid="metric-container"]:hover {
    border-left-color: #F1C40F;
    box-shadow: 0 3px 8px rgba(0,0,0,0.12);
    transition: all .2s ease;
}
div[data-testid="metric-container"] label {
    color: #5D6D7E !important;
    font-size: 0.78rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.03em !important;
}
div[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #1E3D59 !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
}

/* ── Section dividers ──────────────────── */
.ent-section-title {
    color: #1E3D59 !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
    border-bottom: 2px solid #E8ECF0;
    padding-bottom: 6px;
    margin: 18px 0 12px 0 !important;
}

/* ── Info/Insight boxes ────────────────── */
.ent-insight-box {
    background: #F8FAFC;
    border: 1px solid #DDE3EA;
    border-left: 4px solid #1E3D59;
    border-radius: 6px;
    padding: 14px 18px;
    margin: 8px 0;
    font-size: 0.9rem;
    line-height: 1.6;
}
.ent-insight-box.success { border-left-color: #2ECC71; background: #F0FBF4; }
.ent-insight-box.warning { border-left-color: #F39C12; background: #FEFAED; }
.ent-insight-box.danger  { border-left-color: #E74C3C; background: #FEF1F0; }

/* ── Status pills ──────────────────────── */
.pill-green  { background:#E8F8F1; color:#1a7a45; border:1px solid #2ECC71; border-radius:12px; padding:2px 10px; font-size:0.75rem; font-weight:600; margin-right:6px; }
.pill-yellow { background:#FEF9E7; color:#9a7300; border:1px solid #F1C40F; border-radius:12px; padding:2px 10px; font-size:0.75rem; font-weight:600; margin-right:6px; }
.pill-red    { background:#FDEDEC; color:#922b21; border:1px solid #E74C3C; border-radius:12px; padding:2px 10px; font-size:0.75rem; font-weight:600; margin-right:6px; }
.pill-blue   { background:#EAF4FB; color:#1a5276; border:1px solid #3498DB; border-radius:12px; padding:2px 10px; font-size:0.75rem; font-weight:600; margin-right:6px; }

/* ── Page footer ───────────────────────── */
.ent-footer {
    background: #F5F7FA;
    border: 1px solid #E8ECF0;
    border-radius: 6px;
    padding: 10px 16px;
    margin-top: 24px;
    font-size: 0.76rem;
    color: #7F8C8D;
    text-align: center;
}

/* ── Empty state ───────────────────────── */
.ent-empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #7F8C8D;
    background: #FAFBFC;
    border: 1px dashed #C8D0D8;
    border-radius: 8px;
    margin: 8px 0;
}
.ent-empty-state .icon { font-size: 2.5rem; margin-bottom: 8px; }

/* ── Sidebar enhancements ──────────────── */
section[data-testid="stSidebar"] {
    background: #0f2336 !important;
}
section[data-testid="stSidebar"] .stRadio label {
    color: #BDC3C7 !important;
    font-size: 0.88rem;
}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {
    color: #FFFFFF !important;
}

/* ── Dataframe styling ─────────────────── */
.stDataFrame { border: 1px solid #E8ECF0; border-radius: 8px; }

/* ── Tab styling ───────────────────────── */
button[data-baseweb="tab"] { font-weight: 600; font-size: 0.85rem; }

/* ── Expander styling ──────────────────── */
details summary { font-weight: 600; color: #1E3D59; }
</style>
"""


# ── Helper: apply chart defaults ──────────────────────────────────────────────
def style_chart(fig, title: str = "", height: int = CHART_HEIGHT) -> object:
    """Apply consistent enterprise styling to any Plotly figure."""
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color=ACCENT_COLOR, family=CHART_FONT_FAMILY)),
        height=height,
        template=CHART_TEMPLATE,
        margin=CHART_MARGINS,
        font=dict(family=CHART_FONT_FAMILY, size=CHART_FONT_SIZE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        paper_bgcolor="white",
        plot_bgcolor="#F8FAFC",
    )
    fig.update_xaxes(showgrid=True, gridcolor="#F0F2F5", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#F0F2F5", zeroline=False)
    return fig


# ── Helper: page header ───────────────────────────────────────────────────────
def page_header(icon: str, title: str, description: str, last_updated: str | None = None):
    """Render a consistent enterprise page header."""
    ts = last_updated or datetime.datetime.now().strftime("Last refreshed: %Y-%m-%d %H:%M IST")
    st.markdown(f"""
    <div class="ent-page-header">
        <h1>{icon} {title}</h1>
        <p class="desc">{description}</p>
        <p class="ts">🕐 {ts}</p>
    </div>
    """, unsafe_allow_html=True)


# ── Helper: section title ─────────────────────────────────────────────────────
def section_title(text: str):
    st.markdown(f'<p class="ent-section-title">{text}</p>', unsafe_allow_html=True)


# ── Helper: empty state ───────────────────────────────────────────────────────
def empty_state(message: str = "No data available", icon: str = "📭"):
    st.markdown(f"""
    <div class="ent-empty-state">
        <div class="icon">{icon}</div>
        <p><strong>{message}</strong></p>
        <p style="font-size:0.8rem;">Run the pipeline to generate this report.</p>
    </div>
    """, unsafe_allow_html=True)


# ── Helper: insight box ───────────────────────────────────────────────────────
def insight_box(text: str, kind: str = "info"):
    """kind: info | success | warning | danger"""
    cls = "" if kind == "info" else kind
    st.markdown(f'<div class="ent-insight-box {cls}">{text}</div>', unsafe_allow_html=True)


# ── Helper: executive insights section ───────────────────────────────────────
def executive_insights_section(findings: list[str], summary: str, recommendations: list[str]):
    """Render a consistent Executive Insights block at the bottom of every page."""
    st.markdown("---")
    section_title("📋 Executive Insights")
    
    with st.expander("View Executive Insights & Recommendations", expanded=True):
        col_f, col_r = st.columns(2)
        
        with col_f:
            st.markdown("**🔍 Key Findings**")
            for f in findings:
                st.markdown(f"• {f}")
            st.markdown(f"\n**📝 Business Summary**\n\n{summary}")
        
        with col_r:
            st.markdown("**⚙️ Operational Recommendations**")
            for i, rec in enumerate(recommendations, 1):
                st.markdown(f"{i}. {rec}")


# ── Helper: page footer ───────────────────────────────────────────────────────
def page_footer():
    """Render a consistent enterprise footer on every page."""
    update_ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")
    st.markdown(f"""
    <div class="ent-footer">
        <strong>{PLATFORM_NAME}</strong> &nbsp;·&nbsp;
        {PLATFORM_VERSION} &nbsp;·&nbsp;
        {PLATFORM_CLIENT} &nbsp;·&nbsp;
        Data Sources: {DATA_SOURCES} &nbsp;·&nbsp;
        🕐 {update_ts}
    </div>
    """, unsafe_allow_html=True)


# ── Helper: help expander ─────────────────────────────────────────────────────
def help_expander(page_description: str, kpis: dict[str, str]):
    """Render a collapsible 'What does this page show?' help section."""
    with st.expander("❓ What does this page show?", expanded=False):
        st.markdown(page_description)
        if kpis:
            st.markdown("---")
            st.markdown("**KPI Reference Guide:**")
            for kpi_name, kpi_desc in kpis.items():
                st.markdown(f"- **{kpi_name}:** {kpi_desc}")


# ── Helper: download table ────────────────────────────────────────────────────
def downloadable_table(df: pd.DataFrame, label: str = "Download CSV", filename: str = "report.csv"):
    """Show a dataframe with a download button below it."""
    if df is None or df.empty:
        empty_state(f"No data available for {filename}")
        return
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"⬇️ {label}",
        data=csv,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


# ── Helper: status chip ───────────────────────────────────────────────────────
def status_chip(label: str, status: str) -> str:
    """Returns an HTML status chip. status: green | yellow | red | blue"""
    cls = {"green": "pill-green", "yellow": "pill-yellow", "red": "pill-red", "blue": "pill-blue"}.get(status, "pill-blue")
    return f'<span class="{cls}">{label}</span>'


# ── Sidebar: platform status bar ─────────────────────────────────────────────
def sidebar_status_bar(root_dir: str):
    """Render a small platform status section at the bottom of the sidebar."""
    import os

    def _chk(paths):
        for p in paths:
            if os.path.exists(os.path.join(root_dir, p)):
                return "🟢"
        return "🔴"

    pipeline   = _chk(["data/processed/khavda_generation.csv"])
    nasa       = _chk(["data/raw/khavda_weather.csv", "data/raw/khavda_hourly.csv"])
    openmeteo  = _chk(["data/raw/khavda_weather_forecast.csv", "data/raw/open_meteo_forecast.csv"])
    iex        = _chk(["data/market/iex_prices.csv", "data/raw/iex_dam_prices.csv"])
    models     = _chk(["reports/solar/solar_predictions.csv", "reports/total_output/total_output_predictions.csv"])

    # Gemini: check for API key
    gemini_key = os.getenv("GEMINI_API_KEY", "")
    if not gemini_key:
        try:
            import streamlit as _st
            gemini_key = _st.secrets.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    gemini = "🟢" if gemini_key else "🔴"

    st.markdown("---")
    st.markdown("**📡 System Status**")
    st.markdown(
        f"{pipeline} Pipeline &nbsp; {nasa} NASA API &nbsp; {openmeteo} Open-Meteo  \n"
        f"{iex} IEX &nbsp; {gemini} Gemini AI &nbsp; {models} ML Models",
        unsafe_allow_html=False
    )
    st.markdown("---")
    st.caption(f"{PLATFORM_VERSION} · {PLATFORM_CLIENT}")
