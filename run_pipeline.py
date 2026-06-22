import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

PIPELINE_STEPS = [
    "src/ingestion/iex_scraper.py",
    "src/ingestion/khavda_weather_ingestion.py",
    "src/ingestion/open_meteo_ingestion.py",
    "src/ingestion/generate_renewable_generation.py",
    "src/forecasting/solar_model.py",
    "src/forecasting/wind_model.py",
    "src/forecasting/total_output_model.py",
    "src/ingestion/open_meteo_hourly_ingestion.py",   # After models — uses their predictions
    "src/analytics/carbon_offset.py",
    "src/analytics/weather_risk.py",
    "src/analytics/iex_analytics.py",
    "src/analytics/revenue_analytics.py",
    "src/analytics/model_explainability.py",
    "src/analytics/shap_explainability.py",
    "src/analytics/executive_summary.py"
]

def run_script(script_path):
    logging.info(f"🚀 Running {script_path}...")
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"❌ Failed to execute {script_path}")
        logging.error(result.stderr)
        sys.exit(1)
    else:
        logging.info(f"✅ Successfully completed {script_path}")

if __name__ == "__main__":
    logging.info("Starting Master Pipeline Execution")
    for step in PIPELINE_STEPS:
        run_script(step)
    logging.info("🎉 Master Pipeline Execution Completed Successfully!")
