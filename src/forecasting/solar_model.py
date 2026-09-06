"""
Solar Generation Forecasting Model -- Production & Registry
===========================================================
- Separates evaluation holdout from production retraining.
- Uses centralized leakage-free feature engineering.
- Saves P10/P50/P90 residuals based on historical variance.
- Logs metadata to reports/models/model_registry.json.
- Calculates and logs baseline models for comparison.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt
from datetime import datetime

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_XGB = False

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.forecasting.feature_engineering import ACTIVE_FEATURES, build_training_features, build_future_forecast_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPENMETEO_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_openmeteo.csv")
GENERATION_PATH = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
SOLAR_REPORTS_DIR = os.path.join(REPORTS_DIR, "solar")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(SOLAR_REPORTS_DIR, exist_ok=True)
os.makedirs(os.path.join(REPORTS_DIR, "models"), exist_ok=True)

TARGET = "solar_generation_mw"
PSH = 5.8  # Peak sun hours for energy approximation

XGB_PARAMS = dict(
    n_estimators=500,
    learning_rate=0.05,
    max_depth=6,
    subsample=0.8,
    colsample_bytree=0.8,
    min_child_weight=5,
    gamma=0.1,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=42,
    n_jobs=-1,
)

def load_data() -> pd.DataFrame:
    logger.info("Loading datasets...")
    gen_df = pd.read_csv(GENERATION_PATH)
    gen_df["date"] = pd.to_datetime(gen_df["date"])

    if os.path.exists(OPENMETEO_PATH):
        wx_df = pd.read_csv(OPENMETEO_PATH)
        wx_df["date"] = pd.to_datetime(wx_df["date"])
    else:
        raise FileNotFoundError("Open-Meteo weather data is required.")

    forecast_path = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_forecast.csv")
    if os.path.exists(forecast_path):
        fc_df = pd.read_csv(forecast_path)
        fc_df["date"] = pd.to_datetime(fc_df["date"])
        wx_df = pd.concat([wx_df, fc_df], ignore_index=True)
        wx_df = wx_df.drop_duplicates(subset=["date"], keep="last")

    df = wx_df.merge(gen_df, on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)
    return df

def evaluate_model(y_true, y_pred, name="Model"):
    if len(y_true) == 0:
        return {"MAE": 0, "RMSE": 0, "R2_Score": 0, "MAPE": 0}
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    y_safe = np.where(y_true == 0, 1e-9, y_true)
    mape = np.mean(np.abs((y_safe - y_pred) / y_safe)) * 100
    logger.info(f"{name} -> MAE:{mae:.1f} | RMSE:{rmse:.1f} | R2:{r2:.4f} | MAPE:{mape:.2f}%")
    return {"MAE": mae, "RMSE": rmse, "R2_Score": r2, "MAPE": mape}

def compute_baselines(test_df: pd.DataFrame, y_true: pd.Series):
    logger.info("--- Baseline Evaluations ---")
    
    # 1. Naive (Persistence) - Predict yesterday's actual
    # The naive prediction is simply shifting the actual target by 1 day.
    naive_pred = y_true.shift(1).bfill().values
    evaluate_model(y_true, naive_pred, "Naive Baseline")
    
    # 2. 7-Day Average
    # In a true backtest, we would ffill this correctly, but since test_df already has h_mean_7d correctly bounded:
    avg7_pred = test_df['h_mean_7d'].values
    evaluate_model(y_true, avg7_pred, "7-Day Avg Baseline")
    
    # 3. PVLib Physics Baseline
    if 'physics_baseline_mw' in test_df.columns:
        pvlib_pred = test_df['physics_baseline_mw'].fillna(0).values
        evaluate_model(y_true, pvlib_pred, "PVLib Baseline")

def train_and_evaluate(df: pd.DataFrame):
    logger.info("Building features...")
    
    # Split into history (has target) and future (no target)
    historical_raw = df.dropna(subset=[TARGET]).copy()
    future_raw = df[df[TARGET].isna()].copy()
    
    # 1. Build training features safely
    historical = build_training_features(historical_raw)
    
    # Ensure active features exist
    available_features = [f for f in ACTIVE_FEATURES if f in historical.columns]
    
    # 2. Validation Holdout Split (365 days)
    test_size = min(365, int(len(historical) * 0.2))
    train_df = historical.iloc[:-test_size].copy()
    test_df = historical.iloc[-test_size:].copy()
    
    # Fix rolling features for test_df to prevent leakage from the test period itself
    # We use the future forecast feature builder to perfectly simulate an out-of-sample forward fill
    test_df_safe = build_future_forecast_features(train_df, test_df)
    
    X_train = train_df[available_features].fillna(0)
    y_train = train_df[TARGET]
    X_test = test_df_safe[available_features].fillna(0)
    y_test = test_df[TARGET] # True targets
    
    logger.info("--- Validation Phase ---")
    logger.info(f"Val Train: {len(X_train)} | Val Test: {len(X_test)} | Features: {len(available_features)}")
    
    if HAS_XGB:
        val_model = XGBRegressor(**XGB_PARAMS, early_stopping_rounds=30, eval_metric="mae")
        val_size = max(20, int(len(X_train) * 0.1))
        X_val = X_train.iloc[-val_size:]
        y_val = y_train.iloc[-val_size:]
        X_tr = X_train.iloc[:-val_size]
        y_tr = y_train.iloc[:-val_size]
        val_model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        best_iters = val_model.best_iteration
    else:
        val_model = GradientBoostingRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
        val_model.fit(X_train, y_train)
        best_iters = 500

    y_pred_val = np.clip(val_model.predict(X_test), 0, None)
    val_metrics = evaluate_model(y_test, y_pred_val, "XGBoost (Holdout)")
    compute_baselines(test_df_safe, y_test)
    
    # Compute empirical residuals for P10/P90
    residuals = y_test.values - y_pred_val
    p10_offset = np.percentile(residuals, 10)
    p90_offset = np.percentile(residuals, 90)

    # 3. Production Phase (Retrain on 100% of historical data)
    logger.info("--- Production Phase (Full Retrain) ---")
    X_full = historical[available_features].fillna(0)
    y_full = historical[TARGET]
    
    if HAS_XGB:
        prod_params = XGB_PARAMS.copy()
        prod_params["n_estimators"] = best_iters
        prod_model = XGBRegressor(**prod_params)
        prod_model.fit(X_full, y_full)
    else:
        prod_model = GradientBoostingRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
        prod_model.fit(X_full, y_full)
        
    # 4. Future Forecast
    future_pred = None
    future_safe = None
    if not future_raw.empty:
        future_safe = build_future_forecast_features(historical_raw, future_raw)
        X_future = future_safe[available_features].fillna(0)
        future_pred = np.clip(prod_model.predict(X_future), 0, None)
        
    # 5. Save Model Registry
    registry_data = {
        "model_version": "v3.0.0-quartz-leakage-free",
        "timestamp": datetime.now().isoformat(),
        "training_start": str(historical["date"].min().date()),
        "training_end": str(historical["date"].max().date()),
        "training_rows": len(historical),
        "target": TARGET,
        "feature_count": len(available_features),
        "features": available_features,
        "xgboost_parameters": prod_params if HAS_XGB else {},
        "test_metrics": val_metrics,
        "uncertainty_offsets": {
            "p10_offset_mw": float(p10_offset),
            "p90_offset_mw": float(p90_offset)
        }
    }
    with open(os.path.join(REPORTS_DIR, "models", "model_registry.json"), "w") as f:
        json.dump(registry_data, f, indent=4)
        
    return prod_model, test_df_safe, y_test, y_pred_val, future_safe, future_pred, val_metrics, p10_offset, p90_offset

def save_predictions(test_df, y_test, y_pred_val, future_df, future_pred, metrics, p10_offset, p90_offset):
    # Historical Evaluation rows
    out_eval = pd.DataFrame({
        "date": test_df["date"],
        "actual_solar_generation_mw": y_test.values,
        "predicted_solar_generation_mw": y_pred_val,
        "p10_mw": np.clip(y_pred_val + p10_offset, 0, None),
        "p50_mw": y_pred_val,
        "p90_mw": np.clip(y_pred_val + p90_offset, 0, None),
    })
    
    # Future Prediction rows
    out_fut = pd.DataFrame()
    if future_df is not None and future_pred is not None:
        out_fut = pd.DataFrame({
            "date": future_df["date"],
            "actual_solar_generation_mw": np.nan,
            "predicted_solar_generation_mw": future_pred,
            "p10_mw": np.clip(future_pred + p10_offset, 0, None),
            "p50_mw": future_pred,
            "p90_mw": np.clip(future_pred + p90_offset, 0, None),
        })
        
    final_df = pd.concat([out_eval, out_fut], ignore_index=True)
    final_df["predicted_daily_energy_mwh"] = (final_df["predicted_solar_generation_mw"] * PSH).round(2)
    
    final_df.to_csv(os.path.join(SOLAR_REPORTS_DIR, "solar_predictions.csv"), index=False)
    pd.DataFrame([metrics]).to_csv(os.path.join(SOLAR_REPORTS_DIR, "solar_model_metrics.csv"), index=False)
    
def main():
    logger.info("=" * 60)
    logger.info("Solar Forecast Model Pipeline (Leakage-Free)")
    logger.info("=" * 60)
    
    df = load_data()
    prod_model, test_df, y_test, y_pred_val, future_df, future_pred, val_metrics, p10, p90 = train_and_evaluate(df)
    save_predictions(test_df, y_test, y_pred_val, future_df, future_pred, val_metrics, p10, p90)
    
    # Save Model
    with open(os.path.join(MODELS_DIR, "solar_model.pkl"), "wb") as f:
        pickle.dump(prod_model, f)
        
    # Feature Importance
    if hasattr(prod_model, "feature_importances_"):
        features = [f for f in ACTIVE_FEATURES if f in test_df.columns]
        imp_df = pd.DataFrame({
            "feature": features,
            "importance": prod_model.feature_importances_
        }).sort_values("importance", ascending=False)
        imp_df.to_csv(os.path.join(SOLAR_REPORTS_DIR, "solar_feature_importance.csv"), index=False)
        
    logger.info("Pipeline complete.")

if __name__ == "__main__":
    main()
