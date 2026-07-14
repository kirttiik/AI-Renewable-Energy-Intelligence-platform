"""
Solar Generation Forecasting Model -- Quartz-Inspired Architecture
===================================================================
Upgraded to match the feature engineering approach of the
Quartz Solar Forecast (openclimatefix/open-source-quartz-solar-forecast).

Key upgrades over previous model:
  1. Uses Open-Meteo Quartz features: GHI, DNI, DHI (split radiation)
  2. 3-layer cloud cover: low / mid / high (Quartz innovation)
  3. Visibility (dust/aerosol proxy) -- critical for Khavda desert
  4. Rolling autoregressive features: h_mean_7d, h_median_7d, h_max_7d
  5. Quartz-tuned XGBoost: 500 trees, regularization, no artificial noise
  6. MAPE + forecast intervals saved to solar_predictions.csv
"""

import os
import logging
import pandas as pd
import numpy as np
import pickle
import matplotlib.pyplot as plt

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_XGB = False

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPENMETEO_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_openmeteo.csv")
NASA_WEATHER_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather.csv")
GENERATION_PATH = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")
MODELS_DIR = os.path.join(ROOT_DIR, "models")
REPORTS_DIR = os.path.join(ROOT_DIR, "reports")
SOLAR_REPORTS_DIR = os.path.join(REPORTS_DIR, "solar")

os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(SOLAR_REPORTS_DIR, exist_ok=True)

# ============================================================
# Quartz-Inspired Feature Set
# ============================================================
QUARTZ_FEATURES = [
    # Core radiation (Quartz: shortwave_radiation, direct_radiation)
    "ghi_kwh_m2_day",
    "direct_radiation_kwh_m2_day",
    "dhi_kwh_m2_day",
    "dni_kwh_m2_day",
    "clearness_index",
    "diffuse_fraction",
    "direct_fraction",
    # 3-layer cloud cover (Quartz innovation -- low/mid/high separate)
    "cloud_cover_pct",
    "cloud_cover_low_pct",
    "cloud_cover_mid_pct",
    "cloud_cover_high_pct",
    # Weather (Quartz: temperature, precipitation, wind_speed, visibility)
    "temperature_c",
    "temperature_max_c",
    "temperature_min_c",
    "humidity_pct",
    "rainfall_mm",
    "wind_speed_ms",
    "visibility_km",
    # Temporal
    "month",
    "day_of_year",
    "week_of_year",
    "is_monsoon",
    "is_weekend",
    # Autoregressive rolling features (Quartz: h_mean, h_median, h_max)
    "h_mean_7d",
    "h_median_7d",
    "h_max_7d",
    "h_mean_30d",
]

LEGACY_FEATURES = [
    # From physics engine -- kept as complementary features
    "effective_irradiance",
    "cell_temperature_c",
    "temperature_factor",
    "cloud_factor",
    "performance_ratio",
    "capacity_factor",
    "solar_radiation_kwh_m2_day",
]

TARGET = "solar_generation_mw"

# Quartz-tuned XGBoost hyperparameters
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
    """Load and merge Open-Meteo weather (preferred) + generation data."""
    logger.info("Loading datasets...")

    gen_df = pd.read_csv(GENERATION_PATH)
    gen_df["date"] = pd.to_datetime(gen_df["date"])

    # Use Open-Meteo as primary (Quartz-style features)
    if os.path.exists(OPENMETEO_PATH):
        wx_df = pd.read_csv(OPENMETEO_PATH)
        wx_df["date"] = pd.to_datetime(wx_df["date"])
        logger.info(f"Using Open-Meteo data: {len(wx_df)} rows")
    else:
        logger.warning("Open-Meteo not found, using NASA POWER (legacy).")
        wx_df = pd.read_csv(NASA_WEATHER_PATH)
        wx_df["date"] = pd.to_datetime(wx_df["date"])
        wx_df = wx_df.rename(columns={"solar_radiation_kwh_m2_day": "ghi_kwh_m2_day"})

    # Also load forecast weather if it exists
    forecast_path = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_forecast.csv")
    if os.path.exists(forecast_path):
        fc_df = pd.read_csv(forecast_path)
        fc_df["date"] = pd.to_datetime(fc_df["date"])
        # Rename forecast columns to match Quartz schema if needed
        if "solar_radiation_kwh_m2_day" in fc_df.columns and "ghi_kwh_m2_day" not in fc_df.columns:
            fc_df = fc_df.rename(columns={"solar_radiation_kwh_m2_day": "ghi_kwh_m2_day"})
        wx_df = pd.concat([wx_df, fc_df], ignore_index=True)
        wx_df = wx_df.drop_duplicates(subset=["date"], keep="last")

    # Merge weather + generation
    df = wx_df.merge(gen_df, on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)

    # Add temporal features if missing (from Open-Meteo ingestion they already exist,
    # but NASA POWER fallback may not have them)
    if "day_of_year" not in df.columns:
        df["day_of_year"] = df["date"].dt.dayofyear
    if "month" not in df.columns:
        df["month"] = df["date"].dt.month
    if "week_of_year" not in df.columns:
        df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    if "is_weekend" not in df.columns:
        df["is_weekend"] = df["date"].dt.dayofweek.isin([5, 6]).astype(int)
    if "is_monsoon" not in df.columns:
        df["is_monsoon"] = df["month"].isin([6, 7, 8, 9]).astype(int)
    if "clearness_index" not in df.columns and "ghi_kwh_m2_day" in df.columns:
        df["et_radiation_kwh_m2"] = 6.5 + 1.0 * np.cos(2 * np.pi * (df["day_of_year"] - 172) / 365)
        df["clearness_index"] = (df["ghi_kwh_m2_day"] / df["et_radiation_kwh_m2"]).clip(0, 1)

    # Add rolling autoregressive features (Quartz: h_mean, h_median, h_max)
    df["h_mean_7d"] = df[TARGET].shift(1).rolling(7, min_periods=1).mean()
    df["h_median_7d"] = df[TARGET].shift(1).rolling(7, min_periods=1).median()
    df["h_max_7d"] = df[TARGET].shift(1).rolling(7, min_periods=1).max()
    df["h_mean_30d"] = df[TARGET].shift(1).rolling(30, min_periods=7).mean()

    logger.info(f"Dataset: {len(df)} rows | {df['date'].min().date()} to {df['date'].max().date()}")
    return df


def select_features(df: pd.DataFrame) -> list:
    """Return feature columns available in the dataframe."""
    all_features = QUARTZ_FEATURES + LEGACY_FEATURES
    active = [f for f in all_features if f in df.columns]
    logger.info(f"Active features ({len(active)}): {active}")
    return active


def train_model(df: pd.DataFrame):
    """Chronological 80/20 split + Quartz-tuned XGBoost training."""
    logger.info("Training Quartz-tuned XGBoost model...")

    feature_cols = select_features(df)

    historical = df.dropna(subset=[TARGET]).copy()
    future = df[df[TARGET].isna()].copy()

    split_idx = int(len(historical) * 0.8)
    train_df = historical.iloc[:split_idx]
    test_df = historical.iloc[split_idx:]

    X_train = train_df[feature_cols].fillna(0)
    y_train = train_df[TARGET]
    X_test = test_df[feature_cols].fillna(0)
    y_test = test_df[TARGET]

    logger.info(f"Train: {len(X_train)} | Test: {len(X_test)} | Features: {len(feature_cols)}")

    if HAS_XGB:
        model = XGBRegressor(
            **XGB_PARAMS,
            early_stopping_rounds=30,
            eval_metric="mae",
        )
        val_size = max(20, int(len(X_train) * 0.1))
        X_val = X_train.iloc[-val_size:]
        y_val = y_train.iloc[-val_size:]
        X_tr = X_train.iloc[:-val_size]
        y_tr = y_train.iloc[:-val_size]
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=50)
        logger.info(f"Best iteration: {model.best_iteration}")
    else:
        from sklearn.ensemble import GradientBoostingRegressor
        model = GradientBoostingRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)
        model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_pred = np.clip(y_pred, 0, None)

    return model, X_test, y_test, test_df["date"], future, feature_cols, y_pred


def evaluate_model(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """MAE, RMSE, R2, MAPE metrics."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    y_safe = np.where(y_true == 0, 1e-9, y_true)
    mape = np.mean(np.abs((y_safe - y_pred) / y_safe)) * 100
    metrics = {"MAE": mae, "RMSE": rmse, "R2_Score": r2, "MAPE": mape}
    logger.info(f"Metrics -> MAE:{mae:.1f} | RMSE:{rmse:.1f} | R2:{r2:.4f} | MAPE:{mape:.2f}%")
    return metrics


def save_results(dates, y_true, y_pred, metrics):
    """Save predictions, uncertainty intervals, metrics, and plot."""
    rmse = metrics.get("RMSE", np.std(y_pred) * 0.1)
    PSH = 5.8  # Peak sun hours for Khavda

    preds_df = pd.DataFrame({
        "date": dates.values,
        "actual_solar_generation_mw": y_true.values,
        "predicted_solar_generation_mw": y_pred,
    })
    preds_df["predicted_daily_energy_mwh"] = (preds_df["predicted_solar_generation_mw"] * PSH).round(2)
    preds_df["predicted_solar_generation_mw_lower"] = np.clip(preds_df["predicted_solar_generation_mw"] - 1.96 * rmse, 0, None)
    preds_df["predicted_solar_generation_mw_upper"] = preds_df["predicted_solar_generation_mw"] + 1.96 * rmse

    preds_df.to_csv(os.path.join(SOLAR_REPORTS_DIR, "solar_predictions.csv"), index=False)
    pd.DataFrame([metrics]).to_csv(os.path.join(SOLAR_REPORTS_DIR, "solar_model_metrics.csv"), index=False)

    # Plot
    plt.figure(figsize=(14, 7))
    plt.plot(dates.values, y_true.values, label="Actual", color="#2ECC71", linewidth=1.5, alpha=0.9)
    plt.plot(dates.values, y_pred, label="Predicted (Quartz XGBoost)", color="#FF8C00", linewidth=1.5, linestyle="--")
    plt.fill_between(dates.values,
                     preds_df["predicted_solar_generation_mw_lower"],
                     preds_df["predicted_solar_generation_mw_upper"],
                     alpha=0.15, color="#FF8C00", label="95% Confidence Interval")
    plt.title(f"Quartz-Inspired Solar Forecast vs Actual (20% Holdout)\n"
              f"MAE={metrics['MAE']:.0f}MW | RMSE={metrics['RMSE']:.0f}MW | MAPE={metrics['MAPE']:.1f}% | R2={metrics['R2_Score']:.4f}",
              fontsize=13, fontweight="bold")
    plt.xlabel("Date")
    plt.ylabel("Solar Generation (MW)")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(SOLAR_REPORTS_DIR, "solar_forecast_plot.png"), dpi=200)
    plt.close()
    logger.info("Results saved.")


def main():
    logger.info("=" * 60)
    logger.info("Solar Forecast Model -- Quartz-Inspired Architecture")
    logger.info("=" * 60)

    df = load_data()
    feature_cols = select_features(df)
    model, X_test, y_test, test_dates, future_df, feature_cols, y_pred = train_model(df)
    metrics = evaluate_model(y_test, y_pred)

    if not future_df.empty:
        fut_X = future_df[feature_cols].fillna(0)
        fut_pred = np.clip(model.predict(fut_X), 0, None)
        all_dates = pd.concat([test_dates, future_df["date"]])
        all_true = pd.concat([y_test, pd.Series([np.nan] * len(fut_pred))])
        all_pred = np.concatenate([y_pred, fut_pred])
    else:
        all_dates = test_dates
        all_true = y_test
        all_pred = y_pred

    # Save model
    with open(os.path.join(MODELS_DIR, "solar_model.pkl"), "wb") as f:
        pickle.dump(model, f)

    # Save feature importance
    if hasattr(model, "feature_importances_"):
        imp_df = pd.DataFrame({
            "feature": feature_cols,
            "importance": model.feature_importances_
        }).sort_values("importance", ascending=False)
        imp_df.to_csv(os.path.join(SOLAR_REPORTS_DIR, "solar_feature_importance.csv"), index=False)
        logger.info("Top-5 features: " + str(list(imp_df["feature"].head(5))))

    save_results(all_dates, all_true, all_pred, metrics)
    logger.info("=" * 60)
    logger.info("Quartz-Inspired Solar Model Pipeline COMPLETE!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
