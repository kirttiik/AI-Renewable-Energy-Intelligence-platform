"""
Walk-Forward Backtesting Engine — Solar Generation Forecast
============================================================
Performs rigorous out-of-sample backtesting from 2020-01-01 to today.

Strategy: Walk-Forward Validation
  - Initial training window: 12 months (2020-01-01 to 2020-12-31)
  - Fold size: 30 days (predict next 30 days)
  - Walk forward by 30 days and retrain on expanded dataset
  - Saves all fold predictions to reports/solar/backtest_results.csv

Output:
  reports/solar/backtest_results.csv   - All predictions with fold info
  reports/solar/backtest_plot.png      - Full backtesting chart
  reports/solar/backtest_metrics.csv   - Per-fold MAE/RMSE/MAPE
"""

import os
import sys
import logging
import pickle
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date, datetime, timedelta

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
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "solar")
os.makedirs(REPORTS_DIR, exist_ok=True)

OPENMETEO_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_openmeteo.csv")
GENERATION_PATH = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")
BACKTEST_RESULTS_PATH = os.path.join(REPORTS_DIR, "backtest_results.csv")
BACKTEST_METRICS_PATH = os.path.join(REPORTS_DIR, "backtest_metrics.csv")
BACKTEST_PLOT_PATH = os.path.join(REPORTS_DIR, "backtest_plot.png")

QUARTZ_FEATURE_COLS = [
    # Radiation (Quartz core features)
    "ghi_kwh_m2_day",
    "direct_radiation_kwh_m2_day",
    "dhi_kwh_m2_day",
    "dni_kwh_m2_day",
    "clearness_index",
    "diffuse_fraction",
    "direct_fraction",
    # Cloud cover — 3-layer (Quartz innovation)
    "cloud_cover_pct",
    "cloud_cover_low_pct",
    "cloud_cover_mid_pct",
    "cloud_cover_high_pct",
    # Weather
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
    # Rolling autoregressive (Quartz: h_mean, h_median, h_max)
    "h_mean_7d",
    "h_median_7d",
    "h_max_7d",
    "h_mean_30d",
    # Physics-informed features (from generation engine)
    "effective_irradiance",
    "cell_temperature_c",
    "temperature_factor",
    "cloud_factor",
    "performance_ratio",
    "capacity_factor",
]

TARGET_COL = "solar_generation_mw"

# Quartz-tuned XGBoost hyperparameters
XGBOOST_PARAMS = dict(
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
    early_stopping_rounds=30,
    eval_metric="mae",
)


def load_dataset() -> pd.DataFrame:
    """Merge Open-Meteo weather (2020+) with generation data and add rolling features."""
    logger.info("Loading datasets...")

    # Load generation
    gen_df = pd.read_csv(GENERATION_PATH)
    gen_df["date"] = pd.to_datetime(gen_df["date"])

    # Load Open-Meteo weather (preferred — Quartz-style features)
    if os.path.exists(OPENMETEO_PATH):
        wx_df = pd.read_csv(OPENMETEO_PATH)
        wx_df["date"] = pd.to_datetime(wx_df["date"])
        logger.info(f"Open-Meteo weather loaded: {len(wx_df)} rows ({wx_df['date'].min().date()} to {wx_df['date'].max().date()})")
    else:
        logger.warning("Open-Meteo data not found, falling back to NASA POWER weather.")
        wx_df = pd.read_csv(os.path.join(ROOT_DIR, "data", "raw", "khavda_weather.csv"))
        wx_df["date"] = pd.to_datetime(wx_df["date"])
        # Rename to match expected schema
        wx_df = wx_df.rename(columns={"solar_radiation_kwh_m2_day": "ghi_kwh_m2_day"})

    # Merge on date
    df = wx_df.merge(gen_df, on="date", how="inner")
    df = df.sort_values("date").reset_index(drop=True)

    # Add rolling autoregressive features (Quartz: h_mean, h_median, h_max)
    df["h_mean_7d"] = df[TARGET_COL].shift(1).rolling(7, min_periods=1).mean()
    df["h_median_7d"] = df[TARGET_COL].shift(1).rolling(7, min_periods=1).median()
    df["h_max_7d"] = df[TARGET_COL].shift(1).rolling(7, min_periods=1).max()
    df["h_mean_30d"] = df[TARGET_COL].shift(1).rolling(30, min_periods=7).mean()

    logger.info(f"Combined dataset: {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")
    return df


def get_features(df: pd.DataFrame) -> list:
    """Return only the feature columns that actually exist in the dataset."""
    available = [c for c in QUARTZ_FEATURE_COLS if c in df.columns]
    logger.info(f"Active features ({len(available)}): {available}")
    return available


def make_model():
    """Instantiate the Quartz-tuned XGBoost model."""
    if HAS_XGB:
        params = {k: v for k, v in XGBOOST_PARAMS.items() if k not in ["early_stopping_rounds", "eval_metric"]}
        return XGBRegressor(**params, early_stopping_rounds=30, eval_metric="mae")
    else:
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)


def run_walk_forward_backtest(df: pd.DataFrame, feature_cols: list) -> tuple:
    """Run walk-forward validation from 2020 to today."""
    logger.info("Starting walk-forward backtesting...")

    all_preds = []
    fold_metrics = []

    min_date = df["date"].min()
    max_date = df["date"].max()

    # Initial training window: first 12 months
    train_end = min_date + pd.DateOffset(months=6)
    fold_size_days = 30
    fold_num = 0

    while train_end < max_date:
        test_start = train_end
        test_end = min(test_start + pd.Timedelta(days=fold_size_days), max_date)

        train_df_raw = df[df["date"] < test_start].dropna(subset=[TARGET_COL])
        train_df = train_df_raw.copy()
        train_df[feature_cols] = train_df[feature_cols].fillna(0)
        test_df_raw = df[(df["date"] >= test_start) & (df["date"] < test_end)]
        test_df = test_df_raw.copy()
        test_df[feature_cols] = test_df[feature_cols].fillna(0)

        if len(train_df) < 100 or test_df.empty:
            train_end = test_end
            continue

        X_train = train_df[feature_cols]
        y_train = train_df[TARGET_COL]
        X_test = test_df[feature_cols]

        model = make_model()

        if HAS_XGB:
            # Use last 10% of training data as validation for early stopping
            val_size = max(20, int(len(X_train) * 0.1))
            X_val = X_train.iloc[-val_size:]
            y_val = y_train.iloc[-val_size:]
            X_tr = X_train.iloc[:-val_size]
            y_tr = y_train.iloc[:-val_size]
            model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        else:
            model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        y_pred = np.clip(y_pred, 0, None)

        fold_df = test_df[["date", TARGET_COL]].copy()
        fold_df["predicted_solar_generation_mw"] = y_pred
        fold_df["fold_number"] = fold_num + 1
        fold_df["train_size"] = len(train_df)

        # Per-fold metrics (only where actuals exist)
        valid = fold_df.dropna(subset=[TARGET_COL])
        if len(valid) > 0:
            y_act = valid[TARGET_COL].values
            y_prd = valid["predicted_solar_generation_mw"].values
            y_safe = np.where(y_act == 0, 1e-9, y_act)
            mae = mean_absolute_error(y_act, y_prd)
            rmse = np.sqrt(mean_squared_error(y_act, y_prd))
            mape = np.mean(np.abs((y_safe - y_prd) / y_safe)) * 100
            r2 = r2_score(y_act, y_prd)
            fold_metrics.append({
                "fold": fold_num + 1,
                "test_start": test_start.date(),
                "test_end": test_end.date(),
                "train_size": len(train_df),
                "test_size": len(valid),
                "MAE": round(mae, 2),
                "RMSE": round(rmse, 2),
                "MAPE": round(mape, 2),
                "R2": round(r2, 4),
            })
            logger.info(f"  Fold {fold_num+1:3d} | {test_start.date()} to {test_end.date()} | "
                       f"MAE={mae:.0f} | RMSE={rmse:.0f} | MAPE={mape:.1f}% | R2={r2:.3f}")

        all_preds.append(fold_df)
        train_end = test_end
        fold_num += 1

    results_df = pd.concat(all_preds, ignore_index=True)
    metrics_df = pd.DataFrame(fold_metrics)
    logger.info(f"Walk-forward complete. {fold_num} folds, {len(results_df)} total predictions.")
    return results_df, metrics_df


def plot_backtest(results_df: pd.DataFrame, metrics_df: pd.DataFrame):
    """Generate a professional backtest comparison chart."""
    fig, axes = plt.subplots(2, 1, figsize=(18, 12))

    ax1 = axes[0]
    actuals = results_df.dropna(subset=[TARGET_COL])
    ax1.plot(actuals["date"], actuals[TARGET_COL], label="Actual Generation (MW)",
             color="#2ECC71", linewidth=1.5, alpha=0.9)
    ax1.plot(results_df["date"], results_df["predicted_solar_generation_mw"],
             label="Backtest Predicted (MW)", color="#FF8C00", linewidth=1.2,
             linestyle="--", alpha=0.85)

    # Shade monsoon periods
    for year in results_df["date"].dt.year.unique():
        ax1.axvspan(pd.Timestamp(f"{year}-06-01"), pd.Timestamp(f"{year}-09-30"),
                    alpha=0.05, color="blue", label="_nolegend_")

    ax1.set_title("Khavda Solar — Walk-Forward Backtest (2020–Present)\n"
                  "Quartz-Style Features: 3-Layer Cloud Cover, GHI/DNI/DHI Split, Visibility, Rolling Power",
                  fontsize=14, fontweight="bold")
    ax1.set_ylabel("Solar Generation (MW)", fontsize=12)
    ax1.legend(loc="upper left", fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

    # Per-fold MAPE bar chart
    ax2 = axes[1]
    if not metrics_df.empty:
        colors = ["#2ECC71" if m < 10 else "#F1C40F" if m < 20 else "#E74C3C"
                  for m in metrics_df["MAPE"]]
        bars = ax2.bar(metrics_df["fold"], metrics_df["MAPE"], color=colors, alpha=0.8)
        ax2.axhline(y=metrics_df["MAPE"].mean(), color="red", linestyle="--",
                    label=f"Mean MAPE: {metrics_df['MAPE'].mean():.1f}%")
        ax2.axhline(y=10, color="green", linestyle=":", alpha=0.7, label="Target: <10% MAPE")
        ax2.set_xlabel("Fold Number", fontsize=12)
        ax2.set_ylabel("MAPE (%)", fontsize=12)
        ax2.set_title("Per-Fold MAPE — Walk-Forward Backtesting", fontsize=13, fontweight="bold")
        ax2.legend(fontsize=10)
        ax2.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(BACKTEST_PLOT_PATH, dpi=200, bbox_inches="tight")
    plt.close()
    logger.info(f"Backtest plot saved to {BACKTEST_PLOT_PATH}")


def main():
    logger.info("=" * 60)
    logger.info("Walk-Forward Backtesting Engine")
    logger.info("=" * 60)

    df = load_dataset()
    feature_cols = get_features(df)

    results_df, metrics_df = run_walk_forward_backtest(df, feature_cols)

    results_df.to_csv(BACKTEST_RESULTS_PATH, index=False)
    metrics_df.to_csv(BACKTEST_METRICS_PATH, index=False)
    plot_backtest(results_df, metrics_df)

    if not metrics_df.empty:
        logger.info("=" * 60)
        logger.info(f"OVERALL BACKTEST RESULTS ({len(metrics_df)} folds):")
        logger.info(f"  Mean MAE  : {metrics_df['MAE'].mean():.1f} MW")
        logger.info(f"  Mean RMSE : {metrics_df['RMSE'].mean():.1f} MW")
        logger.info(f"  Mean MAPE : {metrics_df['MAPE'].mean():.1f}%")
        logger.info(f"  Mean R2   : {metrics_df['R2'].mean():.4f}")
        logger.info("=" * 60)

    logger.info("Backtesting COMPLETE!")


if __name__ == "__main__":
    main()

