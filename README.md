# Khavda Digital Twin & Energy Market Intelligence Platform

![Status](https://img.shields.io/badge/Status-Production-success)
![Version](https://img.shields.io/badge/Version-2.1.0-blue)
![Python](https://img.shields.io/badge/Python-3.9+-brightgreen)

## Overview
The **Khavda Digital Twin** is an enterprise-grade AI operations and market intelligence platform designed for the 20 GW Khavda Renewable Energy Park in India. 

The platform bridges the gap between **Physical Engineering Models (pvlib)** and **Machine Learning Predictive AI (XGBoost)**, allowing operators to monitor asset health, optimize day-ahead generation schedules, mitigate Deviation Settlement Mechanism (DSM) penalties, and maximize revenue on the Indian Energy Exchange (IEX).

---

## ??? Core Architecture

The platform executes a daily pipeline (.github/workflows/daily_pipeline.yml) that orchestrates the following flow:

1. **Data Ingestion (src/ingestion/)**:
   - Fetches historical meteorological data via Open-Meteo.
   - Scrapes real-time Day-Ahead Market (DAM) and Real-Time Market (RTM) pricing from IEX.
2. **Physics Engine (pvlib)**:
   - Calculates theoretical maximum generation baselines (Clear Sky Irradiance, Plane-of-Array Irradiance, Cell Temperature modeling) based on plant specifications.
3. **Machine Learning (src/models/)**:
   - Trains and runs XGBoost regressors to predict Day-Ahead and Week-Ahead solar and wind generation, correcting for non-linear weather impacts that the physics engine misses.
4. **Analytics & Presentation (pp.py & src/analytics/)**:
   - Streamlit-powered Enterprise Dashboard providing real-time intelligence to plant operators and market traders.

---

## ?? Key Modules

### 1. Executive Control Center
A high-level dashboard displaying critical top-level KPIs such as Peak Generation, Daily Generation (MWh), Forecast Confidence, and Plant Health Score. Includes a 14-Day Generation & Forecast log distinguishing between physics engine actuals and ML predictions.

### 2. PVLib Model (Live Digital Twin)
A real-time physics simulation of the solar farm. Tracks actual generation against the theoretical pvlib baseline, calculating Performance Ratio (PR) and Capacity Factor (CUF), and performing automated Root Cause Analysis for generation losses (e.g., Soiling, Temperature Derating).

### 3. AI Generation Forecast
Displays Day-Ahead and Week-Ahead generation projections powered by XGBoost. Clearly separates instant Peak Generation (MW) from total Daily Generation (MWh). Features SHAP (SHapley Additive exPlanations) values to explain exactly *why* the AI made a specific forecast (e.g., how much cloud cover reduced the forecast).

### 4. DSM Intelligence & Risk Optimizer
Calculates real-time compliance with the Indian grid's Deviation Settlement Mechanism (DSM). Monitors the ±10% tolerance band and computes exact rupee-value penalty risks for over-injection or under-injection, providing actionable recommendations to adjust generation schedules.

### 5. Energy Market Intelligence
Integrates real-time pricing from the Indian Energy Exchange (IEX). Correlates predicted generation peaks against market price spikes, enabling "Grid Export Arbitrage" to maximize revenue during high-demand hours.

---

## ?? Setup & Installation

### Prerequisites
- Python 3.9+
- Pip package manager

### 1. Clone the Repository
`ash
git clone https://github.com/kirttiik/AI-Renewable-Energy-Intelligence-platform.git
cd AI-Renewable-Energy-Intelligence-platform
`

### 2. Install Dependencies
`ash
pip install -r requirements.txt
`
*(Key dependencies include: streamlit, pandas, plotly, xgboost, pvlib, shap, playwright)*

### 3. Install Playwright Browsers (for IEX scraping)
`ash
playwright install chromium
`

### 4. Run the Pipeline (Optional, generates fresh data)
`ash
python run_pipeline.py
`

### 5. Launch the Dashboard
`ash
streamlit run app.py
`

---

## ????? Built For
Designed for the **Khavda Renewable Energy Park Management Team** & **AGEL Enterprise Operations**.
