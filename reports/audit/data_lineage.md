# Data Lineage Audit Report

## 1. Generation Data Lineage (The Target)
**Path**: `src/ingestion/generate_renewable_generation.py`
- **SOURCE**: Open-Meteo Weather API + plant configuration (Capacity, PR, Soiling constants).
- **RAW DATA**: `khavda_weather_openmeteo.csv` (Weather observations).
- **PROCESSED DATA**: `khavda_generation.csv`
- **TRANSFORMATION**: 
  - Converts weather to GHI/Effective Irradiance.
  - Passes through PVLib (or simplified physics equations) to get `cell_temperature_c` and `temperature_factor`.
  - Calculates `solar_generation_mw` (AC Peak Power) = `Capacity x PR x (Eff_Irr/Max_Irr) x Temp_Factor x Availability x Noise`.
- **STATUS**: **SIMULATED**. The column `solar_generation_mw` is not real SCADA data; it is mathematically derived from the weather inputs with synthetic noise applied.
- **DOWNSTREAM CONSUMERS**: `solar_model.py`, `backtest_solar_model.py`, `dsm_intelligence.py`, `pv_engine_analytics.py`, Streamlit `app.py`.

## 2. Weather Feature Lineage
**Path**: `src/ingestion/openmeteo_historical_ingestion.py`
- **SOURCE**: Open-Meteo Historical API
- **RAW DATA**: Direct solar radiation, cloud cover, temperature, wind, humidity, precipitation.
- **RESOLUTION**: Daily aggregates (sums/means) from hourly data.
- **TRANSFORMATION**: Straight pass-through with minor imputations.
- **STATUS**: **OBSERVED** (Historical) and **FORECAST** (Future).
- **DOWNSTREAM CONSUMERS**: ML Feature Engineering pipeline.

## 3. ML Feature Lineage
**Path**: `src/forecasting/feature_engineering.py` (To be created)
- **SOURCE**: `khavda_weather_openmeteo.csv` + `khavda_generation.csv`
- **FEATURES**: 
  - Weather features (GHI, DNI, DHI, cloud cover).
  - Time features (month, day of year).
  - Rolling target features (`h_mean_7d`).
- **LEAKAGE RISK**: High if PVLib metrics from `generate_renewable_generation.py` are included, as they reconstruct the synthetic target equation.
- **DOWNSTREAM CONSUMERS**: XGBoost Model Training and Prediction.

## 4. DSM Intelligence Lineage
**Path**: `src/analytics/dsm_intelligence.py`
- **SOURCE**: `khavda_generation.csv` (Actual) and `solar_predictions.csv` (Forecast).
- **TRANSFORMATION**: 
  - Subtracts `schedule` from `target`.
  - If schedule is missing, it currently *fabricates* one by adding noise to the forecast (Red Flag #13).
  - Calculates penalty by multiplying MW by INR rate directly (Red Flag #15).
- **DOWNSTREAM CONSUMERS**: Streamlit `app.py` DSM dashboard.

## 5. Key Column Summary
| Column | Source | Unit | Resolution | Status | Downstream |
|---|---|---|---|---|---|
| `solar_generation_mw` | `generate_renewable...` | MW (Peak) | Daily | SIMULATED | ML Target |
| `daily_energy_mwh` | `generate_renewable...` | MWh | Daily | SIMULATED | Analytics |
| `scheduled_generation_mw` | `dsm_intelligence.py` | MW | Daily | SYNTHETIC (Currently) | DSM Engine |
| `ghi_kwh_m2_day` | Open-Meteo | kWh/m² | Daily | OBSERVED/FORECAST | ML Features |
