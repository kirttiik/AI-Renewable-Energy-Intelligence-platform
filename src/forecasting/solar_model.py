"""
Solar Generation Forecasting Model

This module builds a production-grade machine learning pipeline to forecast 
solar generation at the Khavda Renewable Energy Park based on weather features 
and engineered time-series features.
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
    from sklearn.ensemble import RandomForestRegressor
    HAS_XGB = False

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================================================
# CONSTANTS & PATHS
# ==================================================
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEATHER_PATH = os.path.join(ROOT_DIR, 'data', 'raw', 'khavda_weather.csv')
GENERATION_PATH = os.path.join(ROOT_DIR, 'data', 'processed', 'khavda_generation.csv')
MODELS_DIR = os.path.join(ROOT_DIR, 'models')
REPORTS_DIR = os.path.join(ROOT_DIR, 'reports')
SOLAR_REPORTS_DIR = os.path.join(REPORTS_DIR, 'solar')

# Create necessary output directories
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(SOLAR_REPORTS_DIR, exist_ok=True)

def load_data() -> pd.DataFrame:
    """
    Load raw weather data and processed generation data, and merge them on the 'date' column.
    """
    logger.info("Loading weather and generation datasets...")
    try:
        weather_df = pd.read_csv(WEATHER_PATH)
        gen_df = pd.read_csv(GENERATION_PATH)
        
        # Merge datasets on the date field
        df = pd.merge(weather_df, gen_df, on='date', how='inner')
        logger.info(f"Successfully merged datasets. Shape: {df.shape}")
        
        return df
    except Exception as e:
        logger.error(f"Failed to load and merge data: {e}")
        raise

def feature_engineering(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert dates to datetime objects and engineer new time-series features.
    Filters the dataset down to the required features and target.
    """
    logger.info("Performing feature engineering...")
    try:
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Extract temporal features
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month
        df['quarter'] = df['date'].dt.quarter
        df['day_of_year'] = df['date'].dt.dayofyear
        df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
        df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6]).astype(int)
        
        # Define exact features required by specifications
        features = [
            'temperature_c', 
            'humidity_pct', 
            'solar_radiation_kwh_m2_day',
            'cloud_cover_pct', 
            'rainfall_mm', 
            'year', 
            'month', 
            'quarter',
            'day_of_year', 
            'week_of_year', 
            'is_weekend'
        ]
        target = 'solar_generation_mw'
        
        # Subselect the required columns and handle any potential NaNs
        final_df = df[['date'] + features + [target]].dropna()
        
        # Ensure chronological order for proper time series splitting
        final_df = final_df.sort_values('date').reset_index(drop=True)
        
        logger.info(f"Feature engineering complete. Prepared dataset shape: {final_df.shape}")
        return final_df
    except Exception as e:
        logger.error(f"Error during feature engineering: {e}")
        raise

def train_model(df: pd.DataFrame):
    """
    Perform an 80/20 chronological time series split and train the machine learning model.
    """
    logger.info("Executing 80/20 time series split and training model...")
    try:
        # Time Series Split (80% Train, 20% Test) - strictly without shuffling
        split_idx = int(len(df) * 0.8)
        
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]
        
        # Isolate features and target
        feature_cols = [col for col in df.columns if col not in ['date', 'solar_generation_mw']]
        
        X_train = train_df[feature_cols]
        y_train = train_df['solar_generation_mw']
        X_test = test_df[feature_cols]
        y_test = test_df['solar_generation_mw']
        
        logger.info(f"Training instances: {len(X_train)} | Testing instances: {len(X_test)}")
        
        # Initialize and Train Model
        if HAS_XGB:
            logger.info("XGBoost Regressor detected and instantiated.")
            model = XGBRegressor(n_estimators=100, learning_rate=0.1, random_state=42)
        else:
            logger.info("XGBoost not available. Falling back to RandomForestRegressor.")
            model = RandomForestRegressor(n_estimators=100, random_state=42)
            
        model.fit(X_train, y_train)
        logger.info("Model training completed successfully.")
        
        return model, X_test, y_test, test_df['date']
    except Exception as e:
        logger.error(f"Error during model training: {e}")
        raise

def evaluate_model(y_true: pd.Series, y_pred: np.ndarray) -> dict:
    """
    Calculate core evaluation metrics: MAE, RMSE, and R2.
    """
    logger.info("Evaluating model performance on test set...")
    try:
        mae = mean_absolute_error(y_true, y_pred)
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        r2 = r2_score(y_true, y_pred)
        
        metrics = {
            'MAE': mae, 
            'RMSE': rmse, 
            'R2_Score': r2
        }
        
        logger.info(f"Model Metrics -> MAE: {mae:.2f} | RMSE: {rmse:.2f} | R2: {r2:.4f}")
        return metrics
    except Exception as e:
        logger.error(f"Error during model evaluation: {e}")
        raise

def save_model(model) -> None:
    """
    Serialize and save the trained model.
    """
    model_path = os.path.join(MODELS_DIR, 'solar_model.pkl')
    logger.info(f"Saving trained model to {model_path}...")
    try:
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        logger.info("Model saved successfully.")
    except Exception as e:
        logger.error(f"Failed to save the model: {e}")
        raise

def save_results(dates: pd.Series, y_true: pd.Series, y_pred: np.ndarray, metrics: dict) -> None:
    """
    Save predictions, metrics, and generate an actual vs predicted plot.
    """
    logger.info("Saving predictions, metrics, and visualizations...")
    try:
        # 1. Save Predictions to CSV
        preds_df = pd.DataFrame({
            'date': dates,
            'actual_solar_generation_mw': y_true.values,
            'predicted_solar_generation_mw': y_pred
        })
        preds_path = os.path.join(SOLAR_REPORTS_DIR, 'solar_predictions.csv')
        preds_df.to_csv(preds_path, index=False)
        
        # 2. Save Metrics to CSV
        metrics_df = pd.DataFrame([metrics])
        metrics_path = os.path.join(SOLAR_REPORTS_DIR, 'solar_model_metrics.csv')
        metrics_df.to_csv(metrics_path, index=False)
        
        # 3. Generate Plot
        plt.figure(figsize=(14, 7))
        plt.plot(dates, y_true.values, label='Actual Generation', color='#1f77b4', alpha=0.8, linewidth=1.5)
        plt.plot(dates, y_pred, label='Predicted Generation', color='#ff7f0e', alpha=0.8, linewidth=1.5)
        plt.title('Solar Generation Forecast vs Actual (20% Holdout Test Set)', fontsize=14, fontweight='bold')
        plt.xlabel('Date', fontsize=12)
        plt.ylabel('Solar Generation (MW)', fontsize=12)
        plt.legend(loc='upper right')
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.tight_layout()
        
        plot_path = os.path.join(SOLAR_REPORTS_DIR, 'solar_forecast_plot.png')
        plt.savefig(plot_path, dpi=300)
        plt.close()
        
        logger.info(f"Results successfully saved in {SOLAR_REPORTS_DIR}")
    except Exception as e:
        logger.error(f"Failed to save results/visualizations: {e}")
        raise

def main() -> None:
    """
    Main orchestration function.
    """
    logger.info("==================================================")
    logger.info("Starting Solar Forecast Modeling Pipeline")
    logger.info("==================================================")
    try:
        df = load_data()
        df = feature_engineering(df)
        
        model, X_test, y_test, test_dates = train_model(df)
        
        # Generate predictions
        y_pred = model.predict(X_test)
        
        # Evaluate
        metrics = evaluate_model(y_test, y_pred)
        
        # Save artifacts
        save_model(model)
        save_results(test_dates, y_test, y_pred, metrics)
        
        # Extract and save feature importance
        if hasattr(model, 'feature_importances_'):
            importance_df = pd.DataFrame({
                'feature': X_test.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            importance_path = os.path.join(SOLAR_REPORTS_DIR, 'solar_feature_importance.csv')
            importance_df.to_csv(importance_path, index=False)
            logger.info(f"Saved feature importance to {importance_path}")
        
        logger.info("==================================================")
        logger.info("Solar Forecast Modeling Pipeline Completed Successfully!")
        logger.info("==================================================")
    except Exception as e:
        logger.error(f"Pipeline failed with an error: {e}")

if __name__ == "__main__":
    main()
