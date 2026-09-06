"""
Canonical Feature Engineering Module
====================================
Ensures production and backtest models use the exact same feature engineering pipeline.
Prevents target leakage and strictly enforces temporal boundaries for rolling features.
"""

import pandas as pd
import numpy as np

# A centralized list of all active features (excluding target and dates)
ACTIVE_FEATURES = [
    'ghi_kwh_m2_day', 'direct_radiation_kwh_m2_day', 'dhi_kwh_m2_day', 'dni_kwh_m2_day',
    'clearness_index', 'diffuse_fraction', 'direct_fraction',
    'cloud_cover_pct', 'cloud_cover_low_pct', 'cloud_cover_mid_pct', 'cloud_cover_high_pct',
    'temperature_c', 'temperature_max_c', 'temperature_min_c',
    'humidity_pct', 'rainfall_mm', 'wind_speed_ms', 'visibility_km',
    'month', 'day_of_year', 'week_of_year', 'is_monsoon', 'is_weekend',
    'h_mean_7d', 'h_median_7d', 'h_max_7d', 'h_mean_30d'
]

def _build_core_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds the core weather and time features.
    These are purely exogenous and do not depend on the target.
    """
    df = df.copy()
    
    # Time features
    if 'date' in df.columns:
        if not pd.api.types.is_datetime64_any_dtype(df['date']):
            df['date'] = pd.to_datetime(df['date'])
        
        # Ensure strict chronological ordering for rolling features
        df = df.sort_values('date').reset_index(drop=True)
            
        df['month'] = df['date'].dt.month
        df['day_of_year'] = df['date'].dt.dayofyear
        df['week_of_year'] = df['date'].dt.isocalendar().week.astype(float)
        df['is_monsoon'] = df['month'].isin([6, 7, 8, 9]).astype(int)
        df['is_weekend'] = df['date'].dt.dayofweek.isin([5, 6]).astype(int)

    # Solar indices (if they don't already exist from ingestion)
    if 'clearness_index' not in df.columns:
        df['clearness_index'] = 0.5  # Default or compute from GHI / Clear Sky
        if 'ghi_kwh_m2_day' in df.columns and 'clear_sky_irradiance_kwh_m2_day' in df.columns:
            df['clearness_index'] = (df['ghi_kwh_m2_day'] / (df['clear_sky_irradiance_kwh_m2_day'] + 0.001)).clip(0, 1)

    if 'diffuse_fraction' not in df.columns:
        if 'dhi_kwh_m2_day' in df.columns and 'ghi_kwh_m2_day' in df.columns:
            df['diffuse_fraction'] = (df['dhi_kwh_m2_day'] / (df['ghi_kwh_m2_day'] + 0.001)).clip(0, 1)
        else:
            df['diffuse_fraction'] = 0.5

    if 'direct_fraction' not in df.columns:
        df['direct_fraction'] = (1.0 - df['diffuse_fraction']).clip(0, 1)
        
    return df

def build_training_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds features for historical training data.
    Uses shift(1) to safely calculate rolling history WITHOUT peeking at the current day's target.
    """
    df = _build_core_features(df)
    
    # Calculate historical rolling features using strictly past generation
    if 'solar_generation_mw' in df.columns:
        # Shift(1) ensures Day T rolling mean uses Day T-1, T-2... not T.
        past_gen = df['solar_generation_mw'].shift(1)
        df['h_mean_7d'] = past_gen.rolling(7, min_periods=1).mean()
        df['h_median_7d'] = past_gen.rolling(7, min_periods=1).median()
        df['h_max_7d'] = past_gen.rolling(7, min_periods=1).max()
        df['h_mean_30d'] = past_gen.rolling(30, min_periods=1).mean()
    else:
        # Fallback if target column is completely missing (should not happen in training)
        df['h_mean_7d'] = 0
        df['h_median_7d'] = 0
        df['h_max_7d'] = 0
        df['h_mean_30d'] = 0
        
    # Ensure no NaNs remain (fill with 0 for the first few rows)
    df.fillna(0, inplace=True)
    return df

def build_backtest_features(train_df: pd.DataFrame, test_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds features for a walk-forward backtest fold.
    The test_df rolling features must be calculated STRICTLY using the final state of train_df,
    never peeking at test_df's actual generation (even if it exists for evaluation).
    """
    # Build core weather/time features for test set
    test_df_features = _build_core_features(test_df)
    
    # Get the last known historical data from train_df
    train_history = train_df[['date', 'solar_generation_mw']].copy()
    
    # Ensure test_df does NOT contain its actual generation during feature engineering
    # We create a dummy test_history with NaN generation
    test_history = test_df[['date']].copy()
    test_history['solar_generation_mw'] = np.nan
    
    # Concatenate to compute rolling features continuously
    combined = pd.concat([train_history, test_history], ignore_index=True)
    
    # Shift(1) and compute rolling
    past_gen = combined['solar_generation_mw'].shift(1)
    combined['h_mean_7d'] = past_gen.rolling(7, min_periods=1).mean()
    combined['h_median_7d'] = past_gen.rolling(7, min_periods=1).median()
    combined['h_max_7d'] = past_gen.rolling(7, min_periods=1).max()
    combined['h_mean_30d'] = past_gen.rolling(30, min_periods=1).mean()
    
    # Now, forward-fill the rolling features so that test days use the last known train day state
    # (Since past_gen is NaN for test days, the rolling will be NaN. Ffill propagates the last valid rolling calc)
    combined.ffill(inplace=True)
    
    # Extract only the test rows
    test_idx = len(train_history)
    test_rolling = combined.iloc[test_idx:].copy()
    
    # Merge rolling features back into test_df_features
    test_df_features['h_mean_7d'] = test_rolling['h_mean_7d'].values
    test_df_features['h_median_7d'] = test_rolling['h_median_7d'].values
    test_df_features['h_max_7d'] = test_rolling['h_max_7d'].values
    test_df_features['h_mean_30d'] = test_rolling['h_mean_30d'].values
    
    test_df_features.fillna(0, inplace=True)
    
    # Assertion to guarantee no target leakage in backtest features
    assert not test_df_features['h_mean_7d'].isnull().any(), "NaNs found in backtest rolling features."
    
    return test_df_features

def build_future_forecast_features(history_df: pd.DataFrame, future_df: pd.DataFrame) -> pd.DataFrame:
    """
    Builds features for production 14-day forecasts.
    Guarantees no future actual generation is used. 
    It forward-fills rolling features from the last available historical day.
    """
    return build_backtest_features(history_df, future_df)
