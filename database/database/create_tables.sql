-- =====================================================
-- Khavda Energy Market Intelligence Platform
-- PostgreSQL Database Schema (Version 1)
-- =====================================================

-- =====================================================
-- Dimension & Master Tables
-- =====================================================

CREATE TABLE dim_site (
    site_id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) NOT NULL,
    latitude NUMERIC,
    longitude NUMERIC
);

CREATE TABLE site_metadata (
    metadata_id SERIAL PRIMARY KEY,
    site_id INT NOT NULL REFERENCES dim_site(site_id),
    site_name VARCHAR(150) NOT NULL,
    capacity_mw NUMERIC NOT NULL,
    commissioning_phase VARCHAR(50),
    technology_type VARCHAR(50), -- 'Solar', 'Wind'
    developer_name VARCHAR(100), -- 'Adani Green Energy'
    latitude NUMERIC,
    longitude NUMERIC,
    status VARCHAR(50), -- 'Active', 'Under Construction'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE dim_date (
    date_id DATE PRIMARY KEY,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    quarter INT NOT NULL,
    day_of_week INT NOT NULL,
    is_weekend BOOLEAN DEFAULT FALSE,
    is_holiday BOOLEAN DEFAULT FALSE
);

CREATE TABLE model_registry (
    model_id SERIAL PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    model_type VARCHAR(50), -- 'XGBoost', 'Prophet', 'LightGBM'
    target_variable VARCHAR(50),
    deployed_date DATE,
    mae NUMERIC,
    rmse NUMERIC,
    r2_score NUMERIC,
    is_active BOOLEAN DEFAULT TRUE
);

-- =====================================================
-- Fact Tables
-- =====================================================

CREATE TABLE fact_weather (
    weather_id BIGSERIAL PRIMARY KEY,
    date_id DATE NOT NULL REFERENCES dim_date(date_id),
    timestamp_utc TIMESTAMP, 
    site_id INT NOT NULL REFERENCES dim_site(site_id),
    temperature_c NUMERIC,
    humidity_pct NUMERIC,
    wind_speed_ms NUMERIC,
    solar_radiation_kwh_m2_day NUMERIC,
    rainfall_mm NUMERIC,
    cloud_cover_pct NUMERIC,
    CONSTRAINT uk_weather_ts_site UNIQUE NULLS NOT DISTINCT (date_id, timestamp_utc, site_id)
);

CREATE TABLE fact_solar_generation (
    gen_id BIGSERIAL PRIMARY KEY,
    date_id DATE NOT NULL REFERENCES dim_date(date_id),
    timestamp_utc TIMESTAMP, 
    site_id INT NOT NULL REFERENCES dim_site(site_id),
    actual_generation_mw NUMERIC,
    plf_pct NUMERIC,
    CONSTRAINT uk_solar_gen_ts_site UNIQUE NULLS NOT DISTINCT (date_id, timestamp_utc, site_id)
);

CREATE TABLE fact_wind_generation (
    gen_id BIGSERIAL PRIMARY KEY,
    date_id DATE NOT NULL REFERENCES dim_date(date_id),
    timestamp_utc TIMESTAMP, 
    site_id INT NOT NULL REFERENCES dim_site(site_id),
    actual_generation_mw NUMERIC,
    plf_pct NUMERIC,
    CONSTRAINT uk_wind_gen_ts_site UNIQUE NULLS NOT DISTINCT (date_id, timestamp_utc, site_id)
);

CREATE TABLE fact_forecast_results (
    forecast_id BIGSERIAL PRIMARY KEY,
    model_id INT NOT NULL REFERENCES model_registry(model_id),
    forecast_run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    target_date_id DATE NOT NULL REFERENCES dim_date(date_id),
    target_timestamp_utc TIMESTAMP, 
    site_id INT REFERENCES dim_site(site_id), 
    target_variable VARCHAR(100) NOT NULL, 
    predicted_value NUMERIC NOT NULL,
    lower_bound_value NUMERIC,
    upper_bound_value NUMERIC
);

-- =====================================================
-- Indexes for Performance
-- =====================================================

CREATE INDEX idx_dim_site_name ON dim_site(site_name);
CREATE INDEX idx_site_metadata_tech ON site_metadata(technology_type);

CREATE INDEX idx_weather_date ON fact_weather(date_id);
CREATE INDEX idx_weather_site ON fact_weather(site_id);
CREATE INDEX idx_weather_ts ON fact_weather(timestamp_utc);

CREATE INDEX idx_solar_gen_date ON fact_solar_generation(date_id);
CREATE INDEX idx_solar_gen_site ON fact_solar_generation(site_id);
CREATE INDEX idx_solar_gen_ts ON fact_solar_generation(timestamp_utc);

CREATE INDEX idx_wind_gen_date ON fact_wind_generation(date_id);
CREATE INDEX idx_wind_gen_site ON fact_wind_generation(site_id);
CREATE INDEX idx_wind_gen_ts ON fact_wind_generation(timestamp_utc);

CREATE INDEX idx_forecast_target_date ON fact_forecast_results(target_date_id);
CREATE INDEX idx_forecast_model ON fact_forecast_results(model_id);
CREATE INDEX idx_forecast_site ON fact_forecast_results(site_id);
CREATE INDEX idx_forecast_ts ON fact_forecast_results(target_timestamp_utc);
