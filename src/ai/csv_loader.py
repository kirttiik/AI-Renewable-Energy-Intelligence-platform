"""
csv_loader.py
─────────────
Automatically scans all pipeline-generated report directories and loads every
CSV found.  Any missing or corrupt file is skipped with a logged warning.

Returns
-------
dict[str, pd.DataFrame]   Keyed by a short human-friendly name derived from
                           the file path.
"""

import os
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

# ── canonical report locations ──────────────────────────────────────────────
REPORT_GLOB_PATHS = [
    "reports/**/*.csv",
    "data/processed/*.csv",
    "data/market/*.csv",
]

# Friendly name map: (path fragment → display name)
_FRIENDLY = {
    "executive_summary":            "Executive Summary",
    "executive_dashboard_kpis":     "Executive KPIs",
    "forecast_accuracy_summary":    "Forecast Accuracy",
    "executive_narrative":          "Executive Narrative",
    "carbon_offset_summary":        "Carbon Offset Summary",
    "executive_sustainability_kpis": "Sustainability KPIs",
    "weather_risk_summary":         "Weather Risk Summary",
    "solar_model_metrics":          "Solar Model Metrics",
    "solar_predictions":            "Solar Predictions",
    "wind_model_metrics":           "Wind Model Metrics",
    "wind_predictions":             "Wind Predictions",
    "wind_model_summary":           "Wind Model Summary",
    "total_output_metrics":         "Total Output Metrics",
    "total_output_predictions":     "Total Output Predictions",
    "explainability_kpis":          "Explainability KPIs",
    "model_comparison":             "Model Comparison",
    "executive_ai_insights":        "AI Insights",
    "ai_generated_summary":         "AI Generated Summary",
    "feature_importance_summary":   "Feature Importance",
    "shap_feature_ranking_solar":   "SHAP Solar Ranking",
    "shap_feature_ranking_wind":    "SHAP Wind Ranking",
    "shap_feature_ranking_total_output": "SHAP Total Ranking",
    "shap_executive_insights":      "SHAP Executive Insights",
    "pv_diagnostics":               "PV Diagnostics",
    "pv_validation_report":         "PV Validation",
    "pv_executive_insights":        "PV Executive Insights",
    "model_comparison_v1_vs_v2":    "PV Model Comparison",
    "iex_market_summary":           "IEX Market Summary",
    "market_executive_insights":    "Market Insights",
    "revenue_backtesting":          "Revenue Backtesting",
    "iex_prices":                   "IEX Prices",
    "carbon_offset_analytics":      "Carbon Analytics",
    "weather_risk_analytics":       "Weather Risk Analytics",
    "khavda_generation":            "Generation Data",
    "total_output_predictions":     "Total Output Predictions",
}


def _friendly_name(filepath: str) -> str:
    stem = Path(filepath).stem
    return _FRIENDLY.get(stem, stem.replace("_", " ").title())


def load_all_reports(root_dir: str) -> dict:
    """
    Walks all report glob paths relative to `root_dir` and returns a dict of
    { friendly_name: pd.DataFrame }.  Missing / unreadable files are skipped.
    """
    root = Path(root_dir)
    loaded: dict[str, pd.DataFrame] = {}
    
    for pattern in REPORT_GLOB_PATHS:
        for csv_path in sorted(root.glob(pattern)):
            friendly = _friendly_name(str(csv_path))
            # Skip duplicates – keep the first (most specific) match
            if friendly in loaded:
                continue
            try:
                df = pd.read_csv(csv_path)
                if df.empty:
                    logger.warning("CSV is empty, skipping: %s", csv_path)
                    continue
                loaded[friendly] = df
                logger.debug("Loaded %s (%d rows)", friendly, len(df))
            except Exception as exc:
                logger.warning("Could not read %s: %s", csv_path, exc)
    
    if not loaded:
        logger.warning("No report CSVs found under: %s", root_dir)
    
    return loaded
