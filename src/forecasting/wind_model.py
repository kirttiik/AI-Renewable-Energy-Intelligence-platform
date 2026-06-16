"""
Wind Generation Forecasting Model

Builds a machine learning forecasting pipeline to predict wind power generation 
using historical weather observations and engineered temporal features.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import logging
import pickle
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

try:
    from xgboost import XGBRegressor
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    from sklearn.ensemble import RandomForestRegressor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEATHER_DATA_PATH = os.path.join(ROOT_DIR, 'data', 'raw', 'khavda_weather.csv')
GENERATION_DATA_PATH = os.path.join(ROOT_DIR, 'data', 'processed', 'khavda_generation.csv')
MODEL_DIR = os.path.join(ROOT_DIR, 'models')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')
WIND_REPORTS_DIR = os.path.join(REPORTS_DIR, 'wind')

MODEL_PATH = os.path.join(MODEL_DIR, 'wind_model.pkl')
PREDICTIONS_PATH = os.path.join(WIND_REPORTS_DIR, 'wind_predictions.csv')
METRICS_PATH = os.path.join(WIND_REPORTS_DIR, 'wind_model_metrics.csv')
SUMMARY_PATH = os.path.join(WIND_REPORTS_DIR, 'wind_model_summary.csv')
FEATURE_IMPORTANCE_PATH = os.path.join(WIND_REPORTS_DIR, 'wind_feature_importance.csv')
PLOT_PATH = os.path.join(WIND_REPORTS_DIR, 'wind_forecast_plot.png')

# Ensure directories exist
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(WIND_REPORTS_DIR, exist_ok=True)


def load_data() -> pd.DataFrame:
    logger.info("Loading weather and generation data...")
    try:
        weather_df = pd.read_csv(WEATHER_DATA_PATH)
        gen_df = pd.read_csv(GENERATION_DATA_PATH)
        
        weather_df['date'] = pd.to_datetime(weather_df['date'])
        gen_df['date'] = pd.to_datetime(gen_df['date'])
        
        # Merge datasets on date
        df = pd.merge(weather_df, gen_df, on='date', how='inner')
        
        logger.info(f"Merged dataset shape: {df.shape}")
        return df
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        raise


def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    logger.info("Performing feature engineering...")
    df = df.copy()
    
    # Sort chronologically to prevent data leakage
    df = df.sort_values('date').reset_index(drop=True)
    
    # Create Temporal Features
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['day_of_year'] = df['date'].dt.dayofyear
    df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
    df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6]).astype(int)
    
    features = [
        'wind_speed_ms', 'temperature_c', 'humidity_pct', 'rainfall_mm', 'cloud_cover_pct',
        'month', 'quarter', 'day_of_year', 'week_of_year', 'is_weekend'
    ]
    target = 'wind_generation_mw'
    
    req_cols = features + [target, 'date']
    df = df[req_cols]
    
    # Remove null values
    initial_len = len(df)
    df = df.dropna()
    if len(df) < initial_len:
        logger.info(f"Dropped {initial_len - len(df)} rows containing null values.")
        
    return df


def train_model(df: pd.DataFrame):
    logger.info("Splitting data and training model...")
    features = [
        'wind_speed_ms', 'temperature_c', 'humidity_pct', 'rainfall_mm', 'cloud_cover_pct',
        'month', 'quarter', 'day_of_year', 'week_of_year', 'is_weekend'
    ]
    target = 'wind_generation_mw'
    
    # Chronological Split: 80% Train, 20% Test (Do NOT randomly shuffle)
    split_idx = int(len(df) * 0.8)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:]
    
    X_train = train_df[features]
    y_train = train_df[target]
    X_test = test_df[features]
    y_test = test_df[target]
    
    if HAS_XGBOOST:
        logger.info("Training XGBoost Regressor...")
        model = XGBRegressor(n_estimators=100, learning_rate=0.1, max_depth=6, random_state=42)
    else:
        logger.warning("XGBoost not found. Falling back to RandomForestRegressor...")
        model = RandomForestRegressor(n_estimators=100, max_depth=6, random_state=42)
        
    model.fit(X_train, y_train)
    logger.info("Model training completed.")
    
    # Generate predictions for evaluation
    y_train_pred = model.predict(X_train)
    train_df = train_df.copy()
    train_df['predicted_wind_generation_mw'] = y_train_pred
    
    y_test_pred = model.predict(X_test)
    test_df = test_df.copy()
    test_df['predicted_wind_generation_mw'] = y_test_pred
    
    return model, train_df, test_df, features


def evaluate_model(train_df: pd.DataFrame, test_df: pd.DataFrame):
    logger.info("Evaluating model performance on train and test sets...")
    
    y_train_true = train_df['wind_generation_mw']
    y_train_pred = train_df['predicted_wind_generation_mw']
    train_mae = mean_absolute_error(y_train_true, y_train_pred)
    train_rmse = np.sqrt(mean_squared_error(y_train_true, y_train_pred))
    train_r2 = r2_score(y_train_true, y_train_pred)

    y_test_true = test_df['wind_generation_mw']
    y_test_pred = test_df['predicted_wind_generation_mw']
    test_mae = mean_absolute_error(y_test_true, y_test_pred)
    test_rmse = np.sqrt(mean_squared_error(y_test_true, y_test_pred))
    test_r2 = r2_score(y_test_true, y_test_pred)
    
    metrics = {
        'Train_MAE': round(train_mae, 4),
        'Train_RMSE': round(train_rmse, 4),
        'Train_R2': round(train_r2, 4),
        'Test_MAE': round(test_mae, 4),
        'Test_RMSE': round(test_rmse, 4),
        'Test_R2': round(test_r2, 4)
    }
    logger.info(f"Evaluation Metrics: {metrics}")
    return metrics


def save_model(model):
    logger.info(f"Saving trained model to {MODEL_PATH}...")
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)


def save_feature_importance(model, feature_names):
    logger.info("Calculating and saving feature importance...")
    if hasattr(model, 'feature_importances_'):
        importances = model.feature_importances_
        imp_df = pd.DataFrame({
            'feature': feature_names,
            'importance': importances
        }).sort_values(by='importance', ascending=False)
        top_5 = imp_df.head(5)['feature'].tolist()
        logger.info("Top 5 Features:\n" + "\n".join(top_5))
        
        imp_df.to_csv(FEATURE_IMPORTANCE_PATH, index=False)
        logger.info(f"Feature importance saved to {FEATURE_IMPORTANCE_PATH}")
        return top_5[0] if len(top_5) > 0 else 'UNKNOWN'
    else:
        logger.warning("Model does not expose feature importances.")
        return 'UNKNOWN'


def save_results(test_df: pd.DataFrame, metrics: dict, train_len: int, test_len: int, best_feature: str):
    logger.info("Saving predictions and metrics...")
    
    # Save predictions
    output_df = test_df[['date', 'wind_generation_mw', 'predicted_wind_generation_mw']].rename(
        columns={'wind_generation_mw': 'actual_wind_generation_mw'}
    )
    output_df.to_csv(PREDICTIONS_PATH, index=False)
    
    # Save metrics
    pd.DataFrame([metrics]).to_csv(METRICS_PATH, index=False)
    
    # Save model summary
    summary_data = [
        {'Metric': 'Train R2', 'Value': metrics['Train_R2']},
        {'Metric': 'Test R2', 'Value': metrics['Test_R2']},
        {'Metric': 'Best Feature', 'Value': best_feature},
        {'Metric': 'Model Type', 'Value': 'XGBoost' if HAS_XGBOOST else 'RandomForest'},
        {'Metric': 'Training Records', 'Value': train_len},
        {'Metric': 'Testing Records', 'Value': test_len}
    ]
    pd.DataFrame(summary_data).to_csv(SUMMARY_PATH, index=False)
    
    logger.info(f"Predictions saved to {PREDICTIONS_PATH}")
    logger.info(f"Metrics saved to {METRICS_PATH}")
    logger.info(f"Summary saved to {SUMMARY_PATH}")


def create_visualizations(test_df: pd.DataFrame):
    logger.info("Generating visualization...")
    plt.figure(figsize=(14, 6))
    
    plt.plot(test_df['date'], test_df['wind_generation_mw'], label='Actual Wind Generation', color='blue', alpha=0.7)
    plt.plot(test_df['date'], test_df['predicted_wind_generation_mw'], label='Predicted Wind Generation', color='orange', alpha=0.8, linestyle='--')
    
    plt.title('Actual vs Predicted Wind Generation', fontsize=14, fontweight='bold')
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Wind Generation (MW)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    
    plt.savefig(PLOT_PATH, dpi=300)
    plt.close()
    logger.info(f"Forecast plot saved to {PLOT_PATH}")


def main():
    logger.info("==================================================")
    logger.info("Starting Wind Generation Forecasting Pipeline")
    logger.info("==================================================")
    
    try:
        df = load_data()
        df = feature_engineering(df)
        
        # Validation checks
        if df.isnull().values.any():
            raise ValueError("Data contains null values after feature engineering.")
        if df['date'].duplicated().any():
            raise ValueError("Data contains duplicate dates.")
            
        model, train_df, test_df, feature_names = train_model(df)
        metrics = evaluate_model(train_df, test_df)
        
        save_model(model)
        best_feature = save_feature_importance(model, feature_names)
        save_results(test_df, metrics, len(train_df), len(test_df), best_feature)
        create_visualizations(test_df)
        
        logger.info("==================================================")
        logger.info("Wind Pipeline Completed Successfully")
        logger.info("==================================================")
        
    except Exception as e:
        logger.error(f"Pipeline Failed: {e}")

if __name__ == "__main__":
    main()
