"""
gemini_client.py
─────────────────
Thin wrapper around google-generativeai.

Features
────────
- Reads API key from .env  OR  st.secrets (for Streamlit Cloud).
- Maintains a multi-turn conversation history so the Copilot remembers context.
- Retry logic with exponential back-off.
- Graceful failure – never raises unhandled exceptions to the Streamlit layer.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# ── try to load .env — always resolve to the project root ────────────────────
try:
    from dotenv import load_dotenv
    # Walk up from this file (src/ai/gemini_client.py) → project root
    _HERE = Path(__file__).resolve()
    _PROJECT_ROOT = _HERE.parent.parent.parent   # src/ai -> src -> project root
    _DOTENV_PATH  = _PROJECT_ROOT / ".env"
    if _DOTENV_PATH.exists():
        load_dotenv(dotenv_path=str(_DOTENV_PATH), override=True)
        logger.info("Loaded .env from %s", _DOTENV_PATH)
    else:
        load_dotenv(override=True)   # fallback: search cwd
except ImportError:
    pass

# ── Gemini import (guarded) ───────────────────────────────────────────────────
try:
    import google.generativeai as genai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    logger.error("google-generativeai not installed. Run: pip install google-generativeai")

# ── constants ─────────────────────────────────────────────────────────────────
MODEL_NAME   = "gemini-2.5-flash"
MAX_RETRIES  = 3
RETRY_DELAY  = 2.0   # seconds (doubles each retry)
TIMEOUT_SECS = 60

SYSTEM_PROMPT = """
You are an expert AI Renewable Energy Operations Assistant for the Khavda 
Renewable Energy Park (Adani Green Energy Ltd).

Your sole knowledge source is the OPERATIONAL CONTEXT provided in each message.
This context is auto-generated from live pipeline reports.

RULES
─────
1. Answer ONLY from the supplied context. Never fabricate numbers.
2. If the requested information is not in the context, respond:
   "The requested information is not currently available in the operational reports."
3. Always structure your answers with:
   • Executive Summary (2–3 sentences)
   • Engineering Analysis (bullet points where applicable)
   • Business Implication
   • Operational Recommendation (≥ 5 actions when relevant)
   • Confidence: HIGH / MEDIUM / LOW  (based on data availability)
4. When explaining SHAP values, explain them in plain engineering language.
5. When explaining ML metrics (MAE, RMSE, R²), explain their practical meaning.
6. Use markdown tables when comparing multiple values.
7. NEVER return raw JSON or CSV rows.
8. Keep responses concise but complete. Target 300–600 words.
9. When generating executive reports, use professional tone suitable for 
   senior AGEL leadership.
10. Remember the full conversation history when answering follow-up questions.
""".strip()


def _get_api_key() -> Optional[str]:
    """Reads API key from environment, .env file, or Streamlit secrets."""
    # 1. os environment (set by .env via dotenv)
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if key:
        return key
    # 2. Streamlit secrets (Streamlit Cloud / deployed)
    try:
        import streamlit as st
        key = st.secrets.get("GEMINI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass
    return None


class GeminiCopilot:
    """
    Stateful Gemini chat client.
    Maintains a conversation history list so the model has memory.
    """

    def __init__(self, system_context: str):
        self._api_key    = _get_api_key()
        self._context    = system_context
        self._model      = None
        self._chat       = None
        self._history    = []   # list of {role, parts}
        self._ready      = False
        self._init_error = ""
        self._initialise()

    # ── setup ─────────────────────────────────────────────────────────────────

    def _initialise(self):
        if not _GENAI_AVAILABLE:
            self._init_error = "google-generativeai package is not installed."
            return
        if not self._api_key:
            self._init_error = (
                "GEMINI_API_KEY not found. "
                "Add it to a .env file or Streamlit secrets as GEMINI_API_KEY=xxxx"
            )
            return
        try:
            genai.configure(api_key=self._api_key)
            gen_config = genai.GenerationConfig(
                temperature=0.3,
                top_p=0.9,
                max_output_tokens=2048,
            )
            self._model = genai.GenerativeModel(
                model_name=MODEL_NAME,
                generation_config=gen_config,
                system_instruction=SYSTEM_PROMPT,
            )
            # Start a persistent chat session
            self._chat  = self._model.start_chat(history=[])
            self._ready = True
            logger.info("GeminiCopilot initialised with model %s", MODEL_NAME)
        except Exception as exc:
            self._init_error = f"Gemini initialisation failed: {exc}"
            logger.error(self._init_error)

    # ── public API ────────────────────────────────────────────────────────────

    @property
    def is_ready(self) -> bool:
        return self._ready

    @property
    def error_message(self) -> str:
        return self._init_error

    def send_message(self, user_question: str) -> str:
        """
        Send a user question and return the model's response.
        The context is injected once at the start of each session by being
        prepended to the first message, then the chat history carries memory.
        """
        if not self._ready:
            return f"⚠️ AI Assistant temporarily unavailable: {self._init_error}"

        # Build the full user message
        # On the first turn, include the full operational context
        if len(self._chat.history) == 0:
            full_message = (
                f"OPERATIONAL CONTEXT (live pipeline data):\n"
                f"{'─'*60}\n"
                f"{self._context}\n"
                f"{'─'*60}\n\n"
                f"USER QUESTION: {user_question}"
            )
        else:
            full_message = user_question

        delay = RETRY_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self._chat.send_message(full_message)
                return response.text
            except Exception as exc:
                logger.warning("Gemini attempt %d/%d failed: %s", attempt, MAX_RETRIES, exc)
                if attempt < MAX_RETRIES:
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error("All Gemini retries exhausted.")
                    return (
                        "⚠️ **AI Assistant temporarily unavailable.**\n\n"
                        f"Error: {exc}\n\n"
                        "Please check your API key and network connection."
                    )

    def reset_chat(self):
        """Clear conversation history and start a new chat session."""
        if self._model:
            try:
                self._chat = self._model.start_chat(history=[])
            except Exception:
                pass

    def get_history(self) -> list[dict]:
        """Return the conversation history for export."""
        if not self._chat:
            return []
        history = []
        for msg in self._chat.history:
            role = msg.role
            text = ""
            for part in msg.parts:
                if hasattr(part, "text"):
                    text += part.text
            history.append({"role": role, "content": text})
        return history
