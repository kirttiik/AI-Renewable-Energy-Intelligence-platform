"""
copilot.py
──────────
Streamlit page renderer for the AI Renewable Energy Operations Copilot.

Call render_copilot() from app.py — this is the only public interface.
"""

from __future__ import annotations

import os
import sys
import logging
import datetime

import pandas as pd
import streamlit as st

# ── add src to path so sub-modules resolve ────────────────────────────────────
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.ai.csv_loader      import load_all_reports
from src.ai.context_builder import build_context
from src.ai.gemini_client   import GeminiCopilot

logger = logging.getLogger(__name__)

# ── suggested questions ───────────────────────────────────────────────────────
SUGGESTED_QUESTIONS = [
    "Summarize today's renewable operations",
    "Explain today's weather risk",
    "Explain the SHAP results",
    "Why did generation decrease recently?",
    "How is the plant performing?",
    "Explain today's carbon savings",
    "Summarize the IEX energy market",
    "Explain the physics-informed PV model",
    "Compare solar and wind performance",
    "Generate an executive report",
    "What should operators do tomorrow?",
    "What is the forecast confidence level?",
]

# ── CSS styling ───────────────────────────────────────────────────────────────
_CSS = """
<style>
.copilot-banner {
    background: linear-gradient(135deg, #1E3D59 0%, #0d2137 100%);
    border-radius: 12px;
    padding: 20px 28px;
    margin-bottom: 18px;
    border-left: 5px solid #F1C40F;
}
.copilot-banner h1 { color: #F1C40F !important; margin: 0; font-size: 1.8rem; }
.copilot-banner p  { color: #BDC3C7; margin: 4px 0 0 0; font-size: 0.95rem; }

.chat-user {
    background: #1E3D59;
    color: #ECF0F1;
    border-radius: 14px 14px 4px 14px;
    padding: 12px 16px;
    margin: 8px 0 8px 60px;
    font-size: 0.95rem;
}
.chat-ai {
    background: #F5F7FA;
    color: #1E3D59;
    border-radius: 14px 14px 14px 4px;
    padding: 14px 18px;
    margin: 8px 60px 8px 0;
    border-left: 4px solid #F1C40F;
    font-size: 0.93rem;
}
.chip-available   { background: #2ECC71; color: white; border-radius: 12px; padding: 3px 10px; font-size: 0.75rem; margin-right: 6px; }
.chip-unavailable { background: #E74C3C; color: white; border-radius: 12px; padding: 3px 10px; font-size: 0.75rem; margin-right: 6px; }
.chip-info        { background: #3498DB; color: white; border-radius: 12px; padding: 3px 10px; font-size: 0.75rem; margin-right: 6px; }
</style>
"""


# ── session-state helpers ─────────────────────────────────────────────────────

def _init_session():
    if "copilot_messages"  not in st.session_state:
        st.session_state["copilot_messages"] = []   # [{role, content}]
    if "copilot_client"    not in st.session_state:
        st.session_state["copilot_client"]   = None
    if "copilot_context"   not in st.session_state:
        st.session_state["copilot_context"]  = None
    if "copilot_reports"   not in st.session_state:
        st.session_state["copilot_reports"]  = None


def _get_or_build_client() -> GeminiCopilot:
    """Build the copilot client once per session and cache it."""
    if st.session_state["copilot_client"] is not None:
        return st.session_state["copilot_client"]

    # Load reports
    reports = load_all_reports(_ROOT)
    st.session_state["copilot_reports"] = reports

    # Build context
    context = build_context(reports, available_keys=list(reports.keys()))
    st.session_state["copilot_context"] = context

    # Instantiate client
    client = GeminiCopilot(system_context=context)
    st.session_state["copilot_client"] = client
    return client


# ── chat rendering ────────────────────────────────────────────────────────────

def _render_messages():
    for msg in st.session_state["copilot_messages"]:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="chat-user">👤 <strong>You</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                f'<div class="chat-ai">🤖 <strong>AI Copilot</strong><br>{msg["content"]}</div>',
                unsafe_allow_html=True
            )


def _send(question: str, client: GeminiCopilot):
    """Append user message, call Gemini, append assistant response."""
    st.session_state["copilot_messages"].append({"role": "user", "content": question})

    with st.spinner("🔄 Analysing operational data..."):
        reply = client.send_message(question)

    st.session_state["copilot_messages"].append({"role": "assistant", "content": reply})


# ── main renderer ─────────────────────────────────────────────────────────────

def render_copilot():
    st.markdown(_CSS, unsafe_allow_html=True)
    _init_session()

    # ── Banner ──────────────────────────────────────────────────────────────
    st.markdown("""
    <div class="copilot-banner">
        <h1>🤖 AI Renewable Energy Operations Copilot</h1>
        <p>Ask questions about renewable generation, weather, forecasting,
           market intelligence and plant performance.<br>
           Powered by Google Gemini · Context: Live pipeline reports</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Build / retrieve client ──────────────────────────────────────────────
    client = _get_or_build_client()
    reports = st.session_state.get("copilot_reports", {})

    # ── Status chips ─────────────────────────────────────────────────────────
    api_status = (
        '<span class="chip-available">✅ Gemini API Connected</span>'
        if client.is_ready else
        '<span class="chip-unavailable">❌ Gemini API Offline</span>'
    )
    report_count = len(reports)
    reports_chip = f'<span class="chip-info">📂 {report_count} Reports Loaded</span>'
    ts_chip = f'<span class="chip-info">🕐 {datetime.datetime.now().strftime("%H:%M IST")}</span>'
    st.markdown(f"{api_status} {reports_chip} {ts_chip}", unsafe_allow_html=True)

    if not client.is_ready:
        st.error(f"⚠️ {client.error_message}")
        st.info(
            "**Setup Instructions:**\n"
            "1. Create a `.env` file in the project root.\n"
            "2. Add: `GEMINI_API_KEY=your_key_here`\n"
            "3. Get a free key at: https://aistudio.google.com/app/apikey\n"
            "4. Restart the Streamlit app."
        )
        return

    # ── Reports availability expander ────────────────────────────────────────
    with st.expander("📋 Loaded Data Sources", expanded=False):
        if reports:
            cols = st.columns(3)
            for i, name in enumerate(sorted(reports.keys())):
                df = reports[name]
                cols[i % 3].markdown(
                    f'<span class="chip-available">✅</span> **{name}** ({len(df)} rows)',
                    unsafe_allow_html=True
                )
        else:
            st.warning("No reports found. Please run the pipeline first.")

    st.markdown("---")

    # ── Suggested question buttons ───────────────────────────────────────────
    st.markdown("**💡 Suggested Questions** — click to ask instantly:")
    cols = st.columns(3)
    for i, q in enumerate(SUGGESTED_QUESTIONS):
        with cols[i % 3]:
            if st.button(q, key=f"sq_{i}", use_container_width=True):
                _send(q, client)
                st.rerun()

    st.markdown("---")
    
    # ── Proactive AI Advisor (Module 9) ──────────────────────────────────────
    st.subheader("📢 Proactive AI Advisor")
    st.markdown("Automatically generate a comprehensive daily brief covering operations, risks, and market opportunities.")
    if st.button("✨ Generate AI Daily Brief", type="primary", use_container_width=True):
        prompt = (
            "Generate a comprehensive Daily Executive Brief. Include:\n"
            "1. Tomorrow's Risks\n"
            "2. Market Opportunities\n"
            "3. Maintenance Suggestions\n"
            "4. Operational Warnings\n"
            "Keep it highly professional, structured with bullet points and bold text."
        )
        _send(prompt, client)
        st.rerun()

    st.markdown("---")

    # ── Chat history ─────────────────────────────────────────────────────────
    if st.session_state["copilot_messages"]:
        _render_messages()
    else:
        st.markdown(
            """
            <div style="text-align:center; color:#7F8C8D; padding: 40px 0;">
                <p style="font-size:2rem;">💬</p>
                <p>No conversation yet. Use the suggested questions above or type your own below.</p>
            </div>
            """,
            unsafe_allow_html=True
        )

    # ── Chat input ───────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask anything about your renewable energy operations...")
    if user_input and user_input.strip():
        _send(user_input.strip(), client)
        st.rerun()

    # ── Action bar ───────────────────────────────────────────────────────────
    st.markdown("---")
    col_clear, col_export, col_refresh = st.columns([1, 1, 1])

    with col_clear:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state["copilot_messages"] = []
            # Reset the Gemini chat session so it forgets prior context
            client.reset_chat()
            st.rerun()

    with col_export:
        if st.button("📥 Export Conversation", use_container_width=True):
            history = st.session_state["copilot_messages"]
            if history:
                lines = []
                for m in history:
                    prefix = "YOU" if m["role"] == "user" else "COPILOT"
                    lines.append(f"[{prefix}]\n{m['content']}\n")
                export_text = "\n".join(lines)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Download .txt",
                    data=export_text,
                    file_name=f"copilot_conversation_{ts}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            else:
                st.info("No conversation to export yet.")

    with col_refresh:
        if st.button("🔄 Refresh Context", use_container_width=True):
            # Force reload of reports and rebuild context
            st.session_state["copilot_client"] = None
            st.session_state["copilot_context"] = None
            st.session_state["copilot_reports"] = None
            st.session_state["copilot_messages"] = []
            st.success("Context refreshed. Chat history cleared.")
            st.rerun()
