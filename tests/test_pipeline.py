import pytest
import pandas as pd
import numpy as np
import os
from src.forecasting.feature_engineering import build_training_features, build_backtest_features, build_future_forecast_features
from src.analytics.dsm_intelligence import calculate_dsm_risk

# Dummy data generator for tests
def get_dummy_data(rows=60):
    dates = pd.date_range(start='2023-01-01', periods=rows, freq='D')
    df = pd.DataFrame({'date': dates})
    df['solar_generation_mw'] = np.random.uniform(0, 100, rows)
    df['ghi_kwh_m2_day'] = np.random.uniform(2, 7, rows)
    return df

def test_feature_temporal_leakage():
    """Phase 13: Test No target leakage & Rolling features only use prior observations"""
    df = get_dummy_data(30)
    
    # We want to ensure that h_mean_7d for Day T is purely based on Day T-1 and before.
    # Let's spike the target on Day 10
    df.loc[10, 'solar_generation_mw'] = 9999
    
    features = build_training_features(df)
    
    # Day 10's h_mean_7d should NOT be massive, because the 9999 happens ON day 10.
    assert features.loc[10, 'h_mean_7d'] < 1000, "Target leakage detected! Day 10 rolling feature contains Day 10 actuals."
    
    # Day 11's h_mean_7d SHOULD be massive, because it includes Day 10's actual.
    assert features.loc[11, 'h_mean_7d'] > 1000, "Rolling feature not updating correctly."

def test_backtest_feature_consistency():
    """Phase 13: Test Production/backtest feature consistency"""
    df = get_dummy_data(60)
    train_raw = df.iloc[:40].copy()
    test_raw = df.iloc[40:].copy()
    
    # Build backtest features
    test_features = build_backtest_features(train_raw, test_raw)
    
    # Ensure test features don't have NaN rolling features
    assert not test_features['h_mean_7d'].isnull().any(), "Backtest features have NaNs for rolling stats."
    
    # Check that if we wipe out test_raw target entirely, test_features remain EXACTLY the same 
    # (proving no future data usage)
    test_raw_no_target = test_raw.copy()
    test_raw_no_target['solar_generation_mw'] = np.nan
    test_features_blind = build_backtest_features(train_raw, test_raw_no_target)
    
    pd.testing.assert_series_equal(test_features['h_mean_7d'], test_features_blind['h_mean_7d'], 
                                   obj="Rolling features must be identical whether future target is present or not.")

def test_dsm_no_fabricated_forecast():
    """Phase 13: Test No fabricated forecast and No fabricated schedule"""
    # Create empty predictions scenario
    df = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=3),
        'actual_total_generation_mw': [100, 105, 95]
    })
    
    # No schedule and no forecast
    dsm_df = calculate_dsm_risk(df)
    
    # It should just return without inventing things if there's no forecast to base a simulation on
    assert 'dsm_penalty_inr' not in dsm_df.columns, "DSM should not calculate if no schedule and no forecast exist."
    
    # Now provide a forecast but no schedule
    df['predicted_total_generation_mw'] = [100, 100, 100]
    dsm_df_2 = calculate_dsm_risk(df)
    
    assert dsm_df_2['schedule_source'].iloc[0] == "SIMULATED_SCHEDULE", "Should explicitly flag fabricated schedules."
    assert dsm_df_2['dsm_mode'].iloc[0] == "SIMULATION"

def test_dsm_zero_schedule():
    """Phase 13: Correct zero-schedule DSM behavior"""
    df = pd.DataFrame({
        'date': pd.date_range('2023-01-01', periods=1),
        'actual_total_generation_mw': [100],
        'scheduled_generation_mw': [0] # Zero schedule
    })
    
    dsm_df = calculate_dsm_risk(df)
    
    # Deviation MW is 100 - 0 = 100. Allowed is 10% of 0 = 0.
    # Excess = 100.
    # Penalty = 100 MW * 7.5 hours * 2500 INR/MWh = 1,875,000 INR
    expected_penalty = 100 * 7.5 * 2500
    
    assert dsm_df['dsm_penalty_inr'].iloc[0] == expected_penalty, "Zero schedule math is incorrect."

def test_chronological_ordering():
    """Phase 13: Chronological ordering test"""
    df = get_dummy_data(30)
    # Shuffle dates
    df = df.sample(frac=1).reset_index(drop=True)
    
    features = build_training_features(df)
    # Ensure it sorted
    assert features['date'].is_monotonic_increasing, "Feature engineering did not sort by date chronologically."
