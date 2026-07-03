"""
context_builder.py
──────────────────
Converts loaded DataFrames into a single, structured plain-text context block
to be injected into the Gemini system / user prompt.

Rules
─────
- Never send raw CSV rows.
- Summarise each dataset to its most operationally relevant numbers.
- Cap total context at ≈4 000 words to stay comfortably within Gemini's
  context window.
- Clearly mark sections so the model can locate specific facts.
"""

from __future__ import annotations

import logging
import textwrap
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

_MAX_CHARS = 16_000   # ~4 000 words


# ── helper utilities ──────────────────────────────────────────────────────────

def _safe_val(df: pd.DataFrame, col: str, agg: str = "last") -> str:
    if df is None or df.empty or col not in df.columns:
        return "N/A"
    series = df[col].dropna()
    if series.empty:
        return "N/A"
    try:
        if agg == "last":
            return str(round(float(series.iloc[-1]), 3))
        if agg == "mean":
            return str(round(float(series.mean()), 3))
        if agg == "sum":
            return str(round(float(series.sum()), 3))
        if agg == "max":
            return str(round(float(series.max()), 3))
        if agg == "min":
            return str(round(float(series.min()), 3))
    except Exception:
        return str(series.iloc[-1])
    return "N/A"


def _df_to_compact_table(df: pd.DataFrame, max_rows: int = 5) -> str:
    if df is None or df.empty:
        return "  (no data)"
    snippet = df.head(max_rows)
    return snippet.to_string(index=False, max_colwidth=40)


def _section(title: str, body: str) -> str:
    return f"\n{'='*60}\n{title.upper()}\n{'='*60}\n{body.strip()}\n"


# ── per-dataset summarisers ───────────────────────────────────────────────────

def _summarise_exec(reports: dict) -> str:
    lines = []
    df = reports.get("Executive Summary")
    if df is not None and not df.empty:
        for col in df.columns:
            try:
                val = df[col].dropna().iloc[-1]
                lines.append(f"  {col}: {val}")
            except Exception:
                pass
    df2 = reports.get("Executive KPIs")
    if df2 is not None and not df2.empty:
        for _, row in df2.head(10).iterrows():
            try:
                lines.append(f"  {row.iloc[0]}: {row.iloc[-1]}")
            except Exception:
                pass
    df3 = reports.get("Executive Narrative")
    if df3 is not None and not df3.empty:
        txt = df3.iloc[0, 0] if df3.shape[1] >= 1 else ""
        if txt:
            lines.append(f"\n  Executive Narrative: {str(txt)[:500]}")
    return "\n".join(lines) if lines else "  Not available."


def _summarise_generation(reports: dict) -> str:
    lines = []
    df = reports.get("Total Output Predictions")
    if df is not None and not df.empty:
        lines.append(f"  Total Generation (last): {_safe_val(df, 'total_generation_mw')} MW")
        lines.append(f"  Solar Generation (last): {_safe_val(df, 'solar_generation_mw')} MW")
        lines.append(f"  Wind Generation (last):  {_safe_val(df, 'wind_generation_mw')} MW")
        lines.append(f"  Forecast Confidence:     {_safe_val(df, 'forecast_confidence_pct')}%")
    df2 = reports.get("Forecast Accuracy")
    if df2 is not None and not df2.empty:
        lines.append(f"  Solar MAE: {_safe_val(df2, 'Solar_MAE')} MW | Wind MAE: {_safe_val(df2, 'Wind_MAE')} MW")
    return "\n".join(lines) if lines else "  Not available."


def _summarise_pv(reports: dict) -> str:
    lines = []
    df = reports.get("Generation Data")
    if df is not None and not df.empty:
        lines.append(f"  Effective Irradiance (avg):  {_safe_val(df, 'effective_irradiance', 'mean')} kWh/m²/d")
        lines.append(f"  POA Irradiance (avg):        {_safe_val(df, 'poa_irradiance_w_m2', 'mean')} W/m²")
        lines.append(f"  Cell Temperature (avg):      {_safe_val(df, 'cell_temperature_c', 'mean')} °C")
        lines.append(f"  Cell Temperature (max):      {_safe_val(df, 'cell_temperature_c', 'max')} °C")
        lines.append(f"  Temperature Factor (avg):    {_safe_val(df, 'temperature_factor', 'mean')}")
        lines.append(f"  Cloud Factor (avg):          {_safe_val(df, 'cloud_factor', 'mean')}")
        lines.append(f"  Performance Ratio (avg):     {_safe_val(df, 'performance_ratio', 'mean')}")
        lines.append(f"  Capacity Factor (avg):       {_safe_val(df, 'capacity_factor', 'mean')}")
        lines.append(f"  Solar Zenith (avg):          {_safe_val(df, 'solar_zenith', 'mean')}°")
        # Derived losses
        try:
            cf_mean = float(df['cloud_factor'].dropna().mean())
            tf_mean = float(df['temperature_factor'].dropna().mean())
            lines.append(f"  Cloud Curtailment (avg):     {round((1-cf_mean)*100, 2)}%")
            lines.append(f"  Temperature Loss (avg):      {round((1-tf_mean)*100, 2)}%")
        except Exception:
            pass
    df2 = reports.get("PV Diagnostics")
    if df2 is not None and not df2.empty:
        lines.append("\n  PV Diagnostics:")
        lines.append(_df_to_compact_table(df2, max_rows=6))
    df3 = reports.get("PV Executive Insights")
    if df3 is not None and not df3.empty:
        lines.append("\n  PV Executive Insights:")
        for _, row in df3.head(5).iterrows():
            try:
                lines.append(f"  - {row.iloc[-1]}")
            except Exception:
                pass
    return "\n".join(lines) if lines else "  Not available."


def _summarise_weather(reports: dict) -> str:
    lines = []
    df = reports.get("Weather Risk Analytics")
    if df is None:
        df = reports.get("Weather Risk Summary")
    if df is not None and not df.empty:
        if 'overall_risk_level' in df.columns:
            counts = df['overall_risk_level'].value_counts()
            lines.append(f"  Risk Distribution — HIGH: {counts.get('HIGH',0)} days, MEDIUM: {counts.get('MEDIUM',0)} days, LOW: {counts.get('LOW',0)} days")
        latest = df.iloc[-1]
        for col in ['temperature_c', 'wind_speed_ms', 'humidity_pct', 'cloud_cover_pct', 'rainfall_mm']:
            if col in df.columns:
                lines.append(f"  {col.replace('_',' ').title()} (latest): {_safe_val(df, col)}")
    return "\n".join(lines) if lines else "  Not available."


def _summarise_carbon(reports: dict) -> str:
    lines = []
    df = reports.get("Carbon Analytics")
    if df is None:
        df = reports.get("Carbon Offset Summary")
    if df is not None and not df.empty:
        lines.append(f"  CO₂ Avoided (total):    {_safe_val(df, 'co2_avoided_tons', 'sum')} Tons")
        lines.append(f"  Coal Saved (total):     {_safe_val(df, 'coal_saved_tons', 'sum')} Tons")
        lines.append(f"  Trees Equivalent (sum): {_safe_val(df, 'trees_equivalent_million', 'sum')} Million")
    return "\n".join(lines) if lines else "  Not available."


def _summarise_market(reports: dict) -> str:
    lines = []
    df = reports.get("IEX Market Summary")
    if df is None:
        df = reports.get("Market Insights")
    if df is not None and not df.empty:
        lines.append(f"  Avg DAM Price (latest): {_safe_val(df, 'avg_dam_price_rs_kwh')} ₹/kWh")
        lines.append(f"  Peak DAM Price:         {_safe_val(df, 'peak_dam_price_rs_kwh', 'max')} ₹/kWh")
        for col in ['market_recommendation', 'market_insight', 'executive_insight']:
            if col in df.columns:
                txt = df[col].dropna()
                if not txt.empty:
                    lines.append(f"  Market Insight: {str(txt.iloc[0])[:300]}")
                    break
    df2 = reports.get("Revenue Backtesting")
    if df2 is not None and not df2.empty:
        lines.append(f"  Estimated Revenue (latest): {_safe_val(df2, 'estimated_revenue_inr')} INR")
    return "\n".join(lines) if lines else "  Not available."


def _summarise_models(reports: dict) -> str:
    lines = []
    for name, df in [
        ("Solar", reports.get("Solar Model Metrics")),
        ("Wind",  reports.get("Wind Model Metrics")),
        ("Total", reports.get("Total Output Metrics")),
    ]:
        if df is not None and not df.empty:
            lines.append(f"\n  {name} Model:")
            for col in df.columns:
                try:
                    val = df[col].dropna().iloc[-1]
                    lines.append(f"    {col}: {val}")
                except Exception:
                    pass
    return "\n".join(lines) if lines else "  Not available."


def _summarise_shap(reports: dict) -> str:
    lines = []
    df = reports.get("SHAP Solar Ranking")
    if df is None:
        df = reports.get("SHAP Total Ranking")
    if df is not None and not df.empty:
        top10 = df.head(10)
        lines.append("  Top 10 SHAP Features (Solar Model):")
        for _, row in top10.iterrows():
            feat = row.get('Feature', row.iloc[0])
            shap = row.get('Mean_Absolute_SHAP', row.iloc[-1])
            lines.append(f"    - {feat}: {round(float(shap), 4)}")
    df2 = reports.get("SHAP Executive Insights")
    if df2 is not None and not df2.empty:
        lines.append("\n  SHAP Executive Insights:")
        for _, row in df2.head(5).iterrows():
            try:
                lines.append(f"  - {row.iloc[-1]}")
            except Exception:
                pass
    return "\n".join(lines) if lines else "  Not available."


def _summarise_explainability(reports: dict) -> str:
    lines = []
    df = reports.get("AI Insights")
    if df is None:
        df = reports.get("AI Generated Summary")
    if df is not None and not df.empty:
        lines.append("  AI-Generated Insights:")
        for _, row in df.head(8).iterrows():
            try:
                lines.append(f"  - {row.iloc[-1]}")
            except Exception:
                pass
    df2 = reports.get("Model Comparison")
    if df2 is not None and not df2.empty:
        lines.append("\n  Model Feature Comparison:")
        lines.append(_df_to_compact_table(df2, max_rows=5))
    return "\n".join(lines) if lines else "  Not available."


# ── main builder ──────────────────────────────────────────────────────────────

def build_context(reports: dict, available_keys: list[str] | None = None) -> str:
    """
    Compiles all loaded reports into a structured plain-text context block.

    Parameters
    ----------
    reports        : dict returned by csv_loader.load_all_reports()
    available_keys : list of report names that were successfully loaded
                     (for transparency in the prompt)

    Returns
    -------
    str  Context string, truncated to _MAX_CHARS if needed.
    """
    today_str = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M IST")
    
    ctx_parts = [
        f"CONTEXT GENERATED AT: {today_str}",
        f"AVAILABLE REPORTS: {', '.join(available_keys or list(reports.keys())) or 'None'}",
    ]

    ctx_parts.append(_section("1. Executive Operations Summary",
                               _summarise_exec(reports)))
    ctx_parts.append(_section("2. Generation & Forecast Status",
                               _summarise_generation(reports)))
    ctx_parts.append(_section("3. PV Physics & Plant Performance",
                               _summarise_pv(reports)))
    ctx_parts.append(_section("4. Weather Intelligence",
                               _summarise_weather(reports)))
    ctx_parts.append(_section("5. Carbon & Sustainability",
                               _summarise_carbon(reports)))
    ctx_parts.append(_section("6. IEX Energy Market",
                               _summarise_market(reports)))
    ctx_parts.append(_section("7. AI & ML Model Performance",
                               _summarise_models(reports)))
    ctx_parts.append(_section("8. SHAP Explainability",
                               _summarise_shap(reports)))
    ctx_parts.append(_section("9. AI-Generated Engineering Insights",
                               _summarise_explainability(reports)))

    full_ctx = "\n".join(ctx_parts)

    if len(full_ctx) > _MAX_CHARS:
        full_ctx = full_ctx[:_MAX_CHARS] + "\n\n[Context truncated to fit model limits.]"

    return full_ctx
