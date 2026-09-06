"""
Walk-Forward Backtesting Engine — Solar Generation Forecast
============================================================
Performs rigorous out-of-sample backtesting from 2020-01-01 to today.
- Uses centralized leakage-free feature engineering.
- Initial training window: 12 months.
- Fold size: 30 days.
- Calculates 14-day specific performance metrics.
"""

import os
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

try:
    from xgboost import XGBRegressor
    HAS_XGB = True
except ImportError:
    from sklearn.ensemble import GradientBoostingRegressor
    HAS_XGB = False

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from src.forecasting.feature_engineering import ACTIVE_FEATURES, build_backtest_features

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(ROOT_DIR, "reports", "solar")
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, "reports", "backtest"), exist_ok=True)

OPENMETEO_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_openmeteo.csv")
GENERATION_PATH = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")

BACKTEST_RESULTS_PATH = os.path.join(ROOT_DIR, "reports", "backtest", "walk_forward_results.csv")
BACKTEST_SUMMARY_PATH = os.path.join(ROOT_DIR, "reports", "backtest", "walk_forward_summary.csv")
BACKTEST_14DAY_PATH = os.path.join(ROOT_DIR, "reports", "backtest", "14_day_forecast_metrics.csv")
BACKTEST_PLOT_PATH = os.path.join(ROOT_DIR, "reports", "backtest", "backtest_plot.png")
HORIZON_PLOT_PATH = os.path.join(ROOT_DIR, "reports", "backtest", "forecast_error_vs_horizon.png")

TARGET_COL = "solar_generation_mw"

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
    logger.info("Loading datasets...")
    gen_df = pd.read_csv(GENERATION_PATH)
    gen_df["date"] = pd.to_datetime(gen_df["date"])

    if os.path.exists(OPENMETEO_PATH):
        wx_df = pd.read_csv(OPENMETEO_PATH)
        wx_df["date"] = pd.to_datetime(wx_df["date"])
    else:
        raise FileNotFoundError("Open-Meteo weather data required.")

    df = wx_df.merge(gen_df, on="date", how="inner")
    df = df.sort_values("date").reset_index(drop=True)
    return df

def make_model():
    if HAS_XGB:
        params = {k: v for k, v in XGBOOST_PARAMS.items() if k not in ["early_stopping_rounds", "eval_metric"]}
        return XGBRegressor(**params, early_stopping_rounds=30, eval_metric="mae")
    else:
        from sklearn.ensemble import GradientBoostingRegressor
        return GradientBoostingRegressor(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42)

def run_walk_forward_backtest(df: pd.DataFrame) -> tuple:
    logger.info("Starting walk-forward backtesting...")
    all_preds = []
    fold_metrics = []
    horizon_metrics = []

    min_date = df["date"].min()
    max_date = df["date"].max()

    # Red Flag #5: Initial training window = 12 months
    train_end = min_date + pd.DateOffset(months=12)
    fold_size_days = 30
    fold_num = 0

    while train_end < max_date:
        test_start = train_end
        test_end = min(test_start + pd.Timedelta(days=fold_size_days), max_date)

        train_df_raw = df[df["date"] < test_start].dropna(subset=[TARGET_COL]).copy()
        test_df_raw = df[(df["date"] >= test_start) & (df["date"] < test_end)].copy()

        if len(train_df_raw) < 300 or test_df_raw.empty:
            train_end = test_end
            continue
            
        # Build features using the centralized feature_engineering module
        train_df = build_backtest_features(train_df_raw, train_df_raw)  # Self-build for train
        test_df = build_backtest_features(train_df_raw, test_df_raw)    # Build test safely using train history

        active = [f for f in ACTIVE_FEATURES if f in train_df.columns]
        X_train = train_df[active].fillna(0)
        y_train = train_df[TARGET_COL]
        X_test = test_df[active].fillna(0)

        model = make_model()

        if HAS_XGB:
            val_size = max(20, int(len(X_train) * 0.1))
            X_val = X_train.iloc[-val_size:]
            y_val = y_train.iloc[-val_size:]
            X_tr = X_train.iloc[:-val_size]
            y_tr = y_train.iloc[:-val_size]
            model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False)
        else:
            model.fit(X_train, y_train)

        y_pred = np.clip(model.predict(X_test), 0, None)

        fold_df = test_df_raw[["date", TARGET_COL]].copy()
        fold_df["predicted_solar_generation_mw"] = y_pred
        fold_df["fold_number"] = fold_num + 1
        
        # Calculate Horizon Metrics (Red Flag #6)
        fold_df["horizon"] = (fold_df["date"] - test_start).dt.days + 1
        for _, row in fold_df.iterrows():
            if pd.notna(row[TARGET_COL]) and row["horizon"] <= 14:
                horizon_metrics.append({
                    "horizon": row["horizon"],
                    "y_true": row[TARGET_COL],
                    "y_pred": row["predicted_solar_generation_mw"]
                })

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
                "fold_start": test_start.date(),
                "train_end": (test_start - pd.Timedelta(days=1)).date(),
                "forecast_start": test_start.date(),
                "forecast_end": test_end.date(),
                "horizon_days": len(valid),
                "MAE": round(mae, 2),
                "RMSE": round(rmse, 2),
                "MAPE": round(mape, 2),
                "R2": round(r2, 4),
            })
            logger.info(f"Fold {fold_num+1:3d} | R2={r2:.3f}")

        all_preds.append(fold_df)
        train_end = test_end
        fold_num += 1

    results_df = pd.concat(all_preds, ignore_index=True)
    summary_df = pd.DataFrame(fold_metrics)
    
    # Aggregate 14-day horizon metrics
    hdf = pd.DataFrame(horizon_metrics)
    horizons_summary = []
    if not hdf.empty:
        for h in range(1, 15):
            h_data = hdf[hdf["horizon"] == h]
            if not h_data.empty:
                yt = h_data["y_true"].values
                yp = h_data["y_pred"].values
                ys = np.where(yt == 0, 1e-9, yt)
                horizons_summary.append({
                    "horizon": h,
                    "MAE": mean_absolute_error(yt, yp),
                    "RMSE": np.sqrt(mean_squared_error(yt, yp)),
                    "R2": r2_score(yt, yp),
                    "MAPE": np.mean(np.abs((ys - yp) / ys)) * 100
                })
    horizon_df = pd.DataFrame(horizons_summary)

    logger.info(f"Walk-forward complete. {fold_num} folds.")
    return results_df, summary_df, horizon_df

def plot_horizon_error(horizon_df: pd.DataFrame):
    if horizon_df.empty: return
    plt.figure(figsize=(10, 5))
    plt.plot(horizon_df["horizon"], horizon_df["MAE"], marker='o', color="#E74C3C")
    plt.title("Forecast Error (MAE) vs Forecast Horizon")
    plt.xlabel("Horizon (Days Ahead)")
    plt.ylabel("Mean Absolute Error (MW)")
    plt.grid(True, alpha=0.3)
    plt.xticks(range(1, 15))
    plt.savefig(HORIZON_PLOT_PATH, dpi=200, bbox_inches="tight")
    plt.close()

def main():
    logger.info("=" * 60)
    logger.info("Walk-Forward Backtesting Engine (Leakage-Free)")
    logger.info("Note: Historical-weather conditional evaluation.")
    logger.info("=" * 60)

    df = load_dataset()
    results_df, summary_df, horizon_df = run_walk_forward_backtest(df)

    results_df.to_csv(BACKTEST_RESULTS_PATH, index=False)
    summary_df.to_csv(BACKTEST_SUMMARY_PATH, index=False)
    horizon_df.to_csv(BACKTEST_14DAY_PATH, index=False)
    
    plot_horizon_error(horizon_df)
    
    if not summary_df.empty:
        logger.info("=" * 60)
        logger.info(f"Mean R2   : {summary_df['R2'].mean():.4f}")
        logger.info("=" * 60)

if __name__ == "__main__":
    main()
