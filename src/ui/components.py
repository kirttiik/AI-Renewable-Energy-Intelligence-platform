"""
components.py — AGEL Reusable UI Components
============================================
Pre-built HTML/Streamlit component helpers using the enterprise design system.
Import and call these from any render_*() function in app.py.
"""

from __future__ import annotations
import datetime
import streamlit as st


# ─── Page Header ──────────────────────────────────────────────────────────────

def page_header(
    icon: str,
    title: str,
    subtitle: str = "",
    badges: list[tuple[str, str]] | None = None   # [(label, color), ...]
):
    """Render a full-width AGEL page header banner."""
    badges_html = ""
    if badges:
        for label, color in badges:
            badges_html += f'<span class="agel-badge {color}">{label}</span>'

    st.markdown(f"""
    <div class="agel-page-header">
        <div>
            <h1>{icon} {title}</h1>
            {"<p class='subtitle'>" + subtitle + "</p>" if subtitle else ""}
            {"<div class='badges'>" + badges_html + "</div>" if badges_html else ""}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Section Header ────────────────────────────────────────────────────────────

def section_header(icon: str, title: str, desc: str = ""):
    st.markdown(f"""
    <div class="agel-section-header">
        <span class="icon">{icon}</span>
        <h3>{title}</h3>
        {"<span class='desc'>" + desc + "</span>" if desc else ""}
    </div>
    """, unsafe_allow_html=True)


# ─── KPI Card ─────────────────────────────────────────────────────────────────

def kpi_card(
    icon: str,
    label: str,
    value: str,
    delta: str = "",
    delta_dir: str = "neutral",   # "pos", "neg", "neutral"
    status: str = "ok",           # "ok", "warn", "crit"
    status_label: str = "LIVE",
    color: str = "blue",          # "blue", "green", "orange", "red"
    tooltip: str = "",
    last_updated: str = "",
    small_value: bool = False
):
    """Render a premium KPI card component."""
    delta_class = {"pos": "card-delta-pos", "neg": "card-delta-neg", "neutral": "card-delta-neu"}.get(delta_dir, "card-delta-neu")
    delta_icon  = {"pos": "▲", "neg": "▼", "neutral": "●"}.get(delta_dir, "")
    val_class   = "card-value small" if small_value else "card-value"
    ts          = last_updated or datetime.datetime.now().strftime("%H:%M IST")

    st.markdown(f"""
    <div class="agel-kpi-card {color}" title="{tooltip}">
        <span class="card-status {status}">{status_label}</span>
        <span class="card-icon">{icon}</span>
        <div class="card-label">{label}</div>
        <div class="{val_class}">{value}</div>
        {"<div class='" + delta_class + "'>" + delta_icon + " " + delta + "</div>" if delta else ""}
        <span class="card-ts">Updated {ts}</span>
    </div>
    """, unsafe_allow_html=True)


# ─── Alert Banner ─────────────────────────────────────────────────────────────

def alert_banner(kind: str, title: str, message: str):
    """
    kind: "success", "warning", "error", "info"
    """
    icons = {"success": "✅", "warning": "⚠️", "error": "🔴", "info": "ℹ️"}
    icon = icons.get(kind, "ℹ️")
    st.markdown(f"""
    <div class="agel-alert {kind}">
        <span class="alert-icon">{icon}</span>
        <div>
            <div class="alert-title">{title}</div>
            <div class="alert-body">{message}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Mission Control Banner ───────────────────────────────────────────────────

def mission_control_banner(
    platform_name: str,
    platform_sub: str,
    pipeline_status: str,
    weather_status: str,
    market_status: str,
    last_updated: str,
    version: str = "v3.0.0"
):
    """Top-of-page mission control header for the Executive Control Center."""
    st.markdown(f"""
    <div class="mission-control-banner">
        <div>
            <div class="platform-name">{platform_name}</div>
            <div class="platform-sub">{platform_sub}</div>
        </div>
        <div class="status-grid">
            <div class="status-item">
                <div class="label">Pipeline</div>
                <div class="value">{pipeline_status}</div>
            </div>
            <div class="status-item">
                <div class="label">Weather</div>
                <div class="value">{weather_status}</div>
            </div>
            <div class="status-item">
                <div class="label">Market</div>
                <div class="value">{market_status}</div>
            </div>
            <div class="status-item">
                <div class="label">Last Update</div>
                <div class="value">{last_updated}</div>
            </div>
            <div class="status-item">
                <div class="label">Platform</div>
                <div class="value">{version}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Health Card ──────────────────────────────────────────────────────────────

def health_card(icon: str, name: str, desc: str, status: str, color: str = "green"):
    """Render a single system health card for the Platform Health page."""
    st.markdown(f"""
    <div class="health-card">
        <span class="hc-icon">{icon}</span>
        <div>
            <div class="hc-name">{name}</div>
            <div class="hc-desc">{desc}</div>
        </div>
        <div class="hc-badge">
            <span class="agel-badge {color}">{status}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Empty State ──────────────────────────────────────────────────────────────

def empty_state(icon: str = "📭", title: str = "No Data Available", desc: str = "Run the pipeline to generate data."):
    st.markdown(f"""
    <div class="agel-empty-state">
        <span class="icon">{icon}</span>
        <div class="title">{title}</div>
        <div class="desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)


# ─── Badge ────────────────────────────────────────────────────────────────────

def badge(label: str, color: str = "blue") -> str:
    """Return HTML for an inline badge."""
    return f'<span class="agel-badge {color}">{label}</span>'


# ─── Status Dot ───────────────────────────────────────────────────────────────

def status_dot(color: str = "green", label: str = "") -> str:
    """Return HTML for an animated status dot."""
    return f'<span class="status-dot {color}"></span>{label}'


# ─── Page Footer ──────────────────────────────────────────────────────────────

def page_footer():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")
    st.markdown(f"""
    <div class="agel-footer">
        <strong>Khavda Renewable Energy Intelligence Platform</strong> &nbsp;|&nbsp;
        Adani Green Energy Ltd (AGEL) &nbsp;|&nbsp;
        Version 3.0.0 &nbsp;|&nbsp;
        {now} &nbsp;|&nbsp;
        Physics-informed PV · XGBoost ML · Gemini AI
    </div>
    """, unsafe_allow_html=True)


# ─── Sidebar Content ──────────────────────────────────────────────────────────

def render_sidebar_footer(version: str = "v3.0.0"):
    import streamlit as st
    st.markdown(f"""
    <div class="sidebar-version">
        <div class="usr">👤 Operations Analyst</div>
        <div class="ver">
            <span class="status-dot green" style="display:inline-block;"></span>
            {version} · Production
        </div>
    </div>
    """, unsafe_allow_html=True)


# ─── Chat Message Renderers ───────────────────────────────────────────────────

def chat_user_message(text: str):
    import streamlit as st
    st.markdown(f"""
    <div class="chat-user-msg">
        <div class="msg-label">👤 &nbsp; You</div>
        {text}
    </div>
    """, unsafe_allow_html=True)


def chat_ai_message(text: str):
    import streamlit as st
    import re
    # Convert markdown bold/bullets to HTML roughly
    rendered = text.replace("\n", "<br>")
    st.markdown(f"""
    <div class="chat-ai-msg">
        <div class="msg-label">🤖 &nbsp; AI Copilot</div>
        {rendered}
    </div>
    """, unsafe_allow_html=True)
