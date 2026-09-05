import os
import pandas as pd
import numpy as np
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GENERATION_PATH = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")
OPENMETEO_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather_openmeteo.csv")

TARGET = "solar_generation_mw"

QUARTZ_FEATURES = [
    "ghi_kwh_m2_day", "direct_radiation_kwh_m2_day", "dhi_kwh_m2_day", "dni_kwh_m2_day",
    "clearness_index", "diffuse_fraction", "direct_fraction",
    "cloud_cover_pct", "cloud_cover_low_pct", "cloud_cover_mid_pct", "cloud_cover_high_pct",
    "temperature_c", "visibility_km",
    "month", "day_of_year",
    "h_mean_7d", "h_median_7d", "h_max_7d"
]

LEGACY_FEATURES = [
    "effective_irradiance", "cell_temperature_c", "temperature_factor",
    "cloud_factor", "performance_ratio", "capacity_factor", "solar_radiation_kwh_m2_day"
]

XGB_PARAMS = dict(n_estimators=500, learning_rate=0.05, max_depth=6, random_state=42, n_jobs=-1)

def eval_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    y_safe = np.where(y_true == 0, 1e-9, y_true)
    mape = np.mean(np.abs((y_safe - y_pred) / y_safe)) * 100
    return mae, rmse, r2, mape

def get_data():
    gen_df = pd.read_csv(GENERATION_PATH)
    gen_df["date"] = pd.to_datetime(gen_df["date"])
    wx_df = pd.read_csv(OPENMETEO_PATH)
    wx_df["date"] = pd.to_datetime(wx_df["date"])
    df = wx_df.merge(gen_df, on="date", how="left")
    df = df.sort_values("date").reset_index(drop=True)
    
    if "day_of_year" not in df.columns: df["day_of_year"] = df["date"].dt.dayofyear
    if "month" not in df.columns: df["month"] = df["date"].dt.month
    if "clearness_index" not in df.columns:
        df["et_radiation"] = 6.5 + 1.0 * np.cos(2 * np.pi * (df["day_of_year"] - 172) / 365)
        df["clearness_index"] = (df["ghi_kwh_m2_day"] / df["et_radiation"]).clip(0, 1)

    df["h_mean_7d"] = df[TARGET].shift(1).rolling(7, min_periods=1).mean()
    df["h_median_7d"] = df[TARGET].shift(1).rolling(7, min_periods=1).median()
    df["h_max_7d"] = df[TARGET].shift(1).rolling(7, min_periods=1).max()
    
    historical = df.dropna(subset=[TARGET]).copy()
    split_idx = int(len(historical) * 0.8)
    return historical.iloc[:split_idx], historical.iloc[split_idx:], historical

def run_experiment(name, train_df, test_df, features):
    features = [f for f in features if f in train_df.columns]
    X_train = train_df[features].fillna(0)
    y_train = train_df[TARGET]
    X_test = test_df[features].fillna(0)
    y_test = test_df[TARGET]
    
    model = XGBRegressor(**XGB_PARAMS)
    model.fit(X_train, y_train)
    y_pred = np.clip(model.predict(X_test), 0, None)
    
    mae, rmse, r2, mape = eval_metrics(y_test, y_pred)
    print(f"{name:30} | MAE: {mae:6.1f} | RMSE: {rmse:6.1f} | R2: {r2:6.4f} | MAPE: {mape:6.2f}%")
    return {"Model": name, "MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape}

if __name__ == "__main__":
    train_df, test_df, full_df = get_data()
    print("--- ML Leakage Audit ---")
    results = []
    
    # PVLib Baseline
    y_true = test_df[TARGET]
    y_pred_pvlib = test_df["physics_baseline_mw"]
    mae, rmse, r2, mape = eval_metrics(y_true, y_pred_pvlib)
    print(f"{'PVLib Physics':30} | MAE: {mae:6.1f} | RMSE: {rmse:6.1f} | R2: {r2:6.4f} | MAPE: {mape:6.2f}%")
    results.append({"Model": "PVLib Physics", "MAE": mae, "RMSE": rmse, "R2": r2, "MAPE": mape})
    
    # Exp A: Current Model (All features)
    results.append(run_experiment("XGBoost Current (Leaky)", train_df, test_df, QUARTZ_FEATURES + LEGACY_FEATURES))
    
    # Exp B: Remove Rolling Features (Still Leaky due to Legacy)
    no_roll_features = [f for f in QUARTZ_FEATURES + LEGACY_FEATURES if "h_" not in f]
    results.append(run_experiment("XGBoost (No Rolling)", train_df, test_df, no_roll_features))
    
    # Exp C: Remove Legacy Features (Leakage-Free)
    results.append(run_experiment("XGBoost Leakage-Free", train_df, test_df, QUARTZ_FEATURES))
    
    # Output to markdown
    df_res = pd.DataFrame(results)
    with open(os.path.join(ROOT_DIR, "reports", "audit_results.md"), "w") as f:
        f.write("# Model Performance Comparison\n\n")
        f.write(df_res.to_markdown(index=False))
