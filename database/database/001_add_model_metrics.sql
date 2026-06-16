-- =====================================================
-- Khavda Energy Market Intelligence Platform
-- Migration: Add model metrics and forecast timestamps
-- =====================================================

-- 1. Update model_registry table
ALTER TABLE model_registry
ADD COLUMN mae NUMERIC,
ADD COLUMN rmse NUMERIC,
ADD COLUMN r2_score NUMERIC,
ADD COLUMN is_active BOOLEAN DEFAULT TRUE;

-- 2. Update fact_forecast_results table
ALTER TABLE fact_forecast_results
ADD COLUMN forecast_run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- =====================================================
-- Recommended Indexes for New Columns
-- =====================================================

-- Index for filtering active models quickly
CREATE INDEX idx_model_registry_active ON model_registry(is_active);

-- Index for sorting/filtering forecasts by when they were run
CREATE INDEX idx_forecast_run_ts ON fact_forecast_results(forecast_run_timestamp);
