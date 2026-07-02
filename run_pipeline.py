"""
Master Pipeline Orchestrator
=============================
Runs all data ingestion, ML forecasting, and analytics scripts in dependency order.

Failure policy:
  - Critical steps (weather ingest, generation engine, ML models) will ABORT the pipeline.
  - Non-critical steps (analytics, explainability) log failures but continue.

This ensures GitHub Actions correctly marks the run as FAILED when core data
cannot be produced, but analytics-layer failures don't kill the whole pipeline.
"""

import subprocess
import sys
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ---------------------------------------------------------------------------
# Pipeline Step Definitions
# Each tuple: (script_path, is_critical)
# is_critical=True  → pipeline aborts on failure
# is_critical=False → logs error, continues to next step
# ---------------------------------------------------------------------------
PIPELINE_STEPS = [
    # ── Data Ingestion (Critical) ──────────────────────────────────────────
    ("src/ingestion/iex_scraper.py",                    False),  # IEX may be down — non-critical
    ("src/ingestion/khavda_weather_ingestion.py",       True),   # NASA POWER — core input
    ("src/ingestion/open_meteo_ingestion.py",           True),   # Future forecast — core input

    # ── Physics-Informed Generation Engine (Critical) ──────────────────────
    ("src/ingestion/generate_renewable_generation.py",  True),   # pvlib PV engine

    # ── ML Forecasting (Critical) ──────────────────────────────────────────
    ("src/forecasting/solar_model.py",                  True),
    ("src/forecasting/wind_model.py",                   True),
    ("src/forecasting/total_output_model.py",           True),

    # ── Hourly Forecast Ingestion (after models) ───────────────────────────
    ("src/ingestion/open_meteo_hourly_ingestion.py",    False),

    # ── Analytics Layer (Non-Critical — failures logged but continue) ──────
    ("src/analytics/carbon_offset.py",                  False),
    ("src/analytics/weather_risk.py",                   False),
    ("src/analytics/iex_analytics.py",                  False),
    ("src/analytics/model_explainability.py",            False),
    ("src/analytics/shap_explainability.py",             False),
    ("src/analytics/executive_summary.py",               False),
]


def run_script(script_path: str, is_critical: bool) -> bool:
    """
    Execute a Python script as a subprocess.
    Returns True on success, False on failure.
    Raises SystemExit if the step is critical and fails.
    """
    logging.info(f"🚀 Running {'[CRITICAL]' if is_critical else '[optional]'} {script_path} ...")
    result = subprocess.run(
        [sys.executable, script_path],
        capture_output=True,
        text=True
    )

    if result.stdout:
        logging.info(result.stdout.strip())

    if result.returncode != 0:
        logging.error(f"❌ Failed: {script_path}")
        logging.error(result.stderr.strip() if result.stderr else "(no stderr captured)")

        if is_critical:
            logging.critical(
                f"CRITICAL step failed — aborting pipeline to prevent cascading "
                f"failures in downstream steps."
            )
            sys.exit(1)

        return False

    logging.info(f"✅ Completed: {script_path}")
    return True


if __name__ == "__main__":
    logging.info("=" * 60)
    logging.info("Khavda Digital Twin — Master Pipeline Starting")
    logging.info("=" * 60)

    failed_steps = []

    for script_path, is_critical in PIPELINE_STEPS:
        success = run_script(script_path, is_critical)
        if not success:
            failed_steps.append(script_path)

    logging.info("=" * 60)
    if failed_steps:
        logging.warning(
            f"Pipeline completed with {len(failed_steps)} non-critical failure(s):\n"
            + "\n".join(f"  - {s}" for s in failed_steps)
        )
    else:
        logging.info("🎉 All pipeline steps completed successfully!")
    logging.info("=" * 60)
