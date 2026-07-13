"""
Physics-Informed PV & Wind Generation Engine (pvlib)
=====================================================

Replaces the empirical radiation-scaling approach with a full
physics-informed photovoltaic model powered by pvlib:

  1. Load plant configuration from config/plant_config.yaml
  2. Convert daily GHI (kWh/m²/day) to approximate W/m² peak irradiance
  3. Compute PV cell temperature using the Faiman (NOCT) model via pvlib
  4. Apply temperature-dependent efficiency correction (γ·ΔT)
  5. Compute effective irradiance (GHI × cloud factor)
  6. Apply system Performance Ratio (PR = 0.82)
  7. Calculate final DC→AC power output, clamped to installed capacity
  8. Retain wind model (cubic power-curve — no pvlib equivalent needed)
  9. Compute and persist all engineered PV features for ML consumption
  10. Run multi-rule validation before saving

Engineered columns added to khavda_generation.csv:
  effective_irradiance_kwh_m2_day
  ghi_w_m2                        (approximate peak W/m²)
  cell_temperature_c
  temperature_factor
  cloud_factor
  performance_ratio
  capacity_factor
"""

import os
import logging
import yaml
import pandas as pd
import numpy as np

try:
    import pvlib
    HAS_PVLIB = True
except ImportError:
    HAS_PVLIB = False
    logging.warning("pvlib not installed — falling back to manual NOCT cell-temp calculation.")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEATHER_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather.csv")
CONFIG_PATH  = os.path.join(ROOT_DIR, "config", "plant_config.yaml")
OUTPUT_PATH  = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")


# ---------------------------------------------------------------------------
# 1. Load Configuration
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Load plant parameters from config/plant_config.yaml."""
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
        
    # --- Configuration Validation ---
    s = cfg.get("solar", {})
    w = cfg.get("wind", {})
    if s.get("installed_capacity_mw", 0) <= 0 or w.get("installed_capacity_mw", 0) <= 0:
        logger.warning("Config Validation: Installed capacity must be > 0.")
    if not (0 < s.get("performance_ratio", 0) <= 1):
        logger.warning("Config Validation: Invalid performance ratio.")
    if s.get("temperature_coefficient") is None:
        logger.warning("Config Validation: Missing temperature coefficient.")
    if s.get("noct_c") is None:
        logger.warning("Config Validation: Missing NOCT.")
    if w.get("cut_in_speed_ms") is None or w.get("cut_out_speed_ms") is None:
        logger.warning("Config Validation: Missing wind cut-in/cut-out speeds.")

    logger.info(f"Loaded plant config: {cfg['site']['name']}")
    return cfg


# ---------------------------------------------------------------------------
# 2. Load Weather Data
# ---------------------------------------------------------------------------
def load_weather_data() -> pd.DataFrame:
    """Load raw weather CSV and forward-fill sparse sensor gaps."""
    logger.info(f"Loading weather data from {WEATHER_PATH}")
    df = pd.read_csv(WEATHER_PATH)
    df["date"] = pd.to_datetime(df["date"])

    numeric_cols = [
        "temperature_c", "cloud_cover_pct",
        "solar_radiation_kwh_m2_day", "wind_speed_ms",
        "humidity_pct", "rainfall_mm"
    ]
    df[numeric_cols] = df[numeric_cols].ffill().fillna(0)
    logger.info(f"Weather data loaded — {len(df)} rows.")
    return df


# ---------------------------------------------------------------------------
# 3. PV Feature Engineering
# ---------------------------------------------------------------------------
def engineer_pv_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Derive physics-informed PV features from raw weather columns.

    Parameters added:
      ghi_w_m2               — approximate peak GHI in W/m²
      effective_irradiance    — GHI after cloud attenuation (kWh/m²/day)
      cloud_factor            — linear cloud-cover penalty [0, 1]
      cell_temperature_c     — PV module operating temperature (pvlib or NOCT)
      temperature_factor     — efficiency multiplier from temperature [0.70, 1.05]
      performance_ratio      — system losses constant (PR = 0.82)
    """
    solar_cfg = cfg["solar"]
    NOCT      = solar_cfg["noct_c"]
    GAMMA     = solar_cfg["temperature_coefficient"]   # -0.004 /°C
    T_STC     = solar_cfg["reference_temp_c"]          # 25 °C
    PR        = solar_cfg["performance_ratio"]

    # --- 3a. Convert daily kWh/m²/day → approximate peak W/m² (÷ by 3.6) --------
    # A common heuristic: 1 kWh/m²/day ≈ 1 PSH (peak-sun-hour), so the
    # average irradiance over daylight (~8 h) ≈ GHI_kWh × 1000 / 8
    df["ghi_w_m2"] = (df["solar_radiation_kwh_m2_day"] * 1000.0 / 8.0).clip(lower=0)

    # --- 3b. Cloud Factor (linear attenuation) -----------------------------------
    df["cloud_factor"] = (1.0 - df["cloud_cover_pct"] / 100.0).clip(0.0, 1.0)

    # --- 3c. Effective Irradiance (kWh/m²/day after cloud attenuation) -----------
    df["effective_irradiance"] = (
        df["solar_radiation_kwh_m2_day"] * df["cloud_factor"]
    ).clip(lower=0)

    # --- 3d. PV Cell Temperature (pvlib Faiman model or fallback NOCT) -----------
    if HAS_PVLIB:
        # pvlib.temperature.faiman expects W/m² irradiance and ambient temp in °C
        df["cell_temperature_c"] = pvlib.temperature.faiman(
            poa_global=df["ghi_w_m2"],           # Plane-of-array irradiance (W/m²)
            temp_air=df["temperature_c"],          # Ambient temperature (°C)
            wind_speed=df["wind_speed_ms"].clip(lower=0),
        )
    else:
        # NOCT approximation: T_cell = T_amb + (NOCT - 20)/800 × GHI_W/m²
        df["cell_temperature_c"] = (
            df["temperature_c"] + ((NOCT - 20.0) / 800.0) * df["ghi_w_m2"]
        )

    # --- 3e. Temperature Factor --------------------------------------------------
    df["temperature_factor"] = (
        1.0 + GAMMA * (df["cell_temperature_c"] - T_STC)
    ).clip(0.70, 1.05)

    # --- 3f. Performance Ratio (constant, stored as a column for ML) -------------
    df["performance_ratio"] = PR

    # --- 3g. Advanced PV Engineering Features (pvlib) ----------------------------
    if HAS_PVLIB:
        lat = cfg["site"]["latitude"]
        lon = cfg["site"]["longitude"]
        tz = "Asia/Kolkata"
        
        # Representative time for daily data (e.g., solar noon ~12:30 local)
        dt_idx = pd.DatetimeIndex(df["date"]).tz_localize(tz) + pd.Timedelta(hours=12, minutes=30)
        
        solpos = pvlib.solarposition.get_solarposition(dt_idx, lat, lon)
        df["solar_zenith"] = solpos["zenith"].values
        df["solar_elevation"] = solpos["elevation"].values
        df["solar_azimuth"] = solpos["azimuth"].values

        df["air_mass"] = pvlib.atmosphere.get_relative_airmass(df["solar_zenith"]).fillna(1.5)

        loc = pvlib.location.Location(lat, lon, tz=tz)
        cs = loc.get_clearsky(dt_idx)
        df["clear_sky_irradiance_kwh_m2_day"] = cs["ghi"].values * 8.0 / 1000.0

        tilt = solar_cfg.get("tilt_degrees", 20)
        azimuth = solar_cfg.get("azimuth_degrees", 180)
        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=azimuth,
            solar_zenith=df["solar_zenith"],
            solar_azimuth=df["solar_azimuth"],
            dni=cs["dni"].values, 
            ghi=df["ghi_w_m2"],
            dhi=cs["dhi"].values
        )
        df["poa_irradiance_w_m2"] = poa["poa_global"].values
    else:
        df["solar_zenith"] = 45.0
        df["solar_elevation"] = 45.0
        df["solar_azimuth"] = 180.0
        df["air_mass"] = 1.5
        df["clear_sky_irradiance_kwh_m2_day"] = df["solar_radiation_kwh_m2_day"]
        df["poa_irradiance_w_m2"] = df["ghi_w_m2"]

    logger.info("PV feature engineering complete.")
    return df


# ---------------------------------------------------------------------------
# 4. Physics-Informed Solar Generation
# ---------------------------------------------------------------------------
def calculate_solar_generation(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """
    Estimated_Generation =
        Installed_Capacity × PR × (Effective_Irradiance / Max_Effective_Irradiance)
        × Temperature_Factor × Cloud_Factor

    Clamped to [0, Installed_Capacity_MW].
    """
    solar_cfg   = cfg["solar"]
    CAPACITY    = solar_cfg["installed_capacity_mw"]
    EFFICIENCY  = solar_cfg["module_efficiency"]
    REF_GHI     = solar_cfg["reference_irradiance_w_m2"]  # 1000 W/m² STC

    # Normalise effective irradiance by the STC reference (1000 W/m² → 8 kWh/m²/day)
    max_eff_irr = REF_GHI / 1000.0 * 8.0   # ≈ 8.0 kWh/m²/day (theoretical max)

    # Introduce aggressive real-world variances (stochastic noise)
    np.random.seed(42)  # For reproducibility
    n_samples = len(df)
    
    # 1. Heavy soiling loss (dust storms, lack of cleaning): varies between 0.85 and 1.0
    soiling_loss = np.random.uniform(0.85, 1.0, n_samples)
    
    # 2. Inverter clipping & thermal derating: 5-10% drops
    inverter_efficiency = np.random.uniform(0.90, 1.0, n_samples)
    
    # 3. Extreme unmodeled variance: Gaussian noise std dev ~35%
    sensor_noise = np.random.normal(1.0, 0.35, n_samples)
    
    # 4. Random forced outages (2% chance of severe drop)
    forced_outage = np.random.choice([1.0, 0.1], size=n_samples, p=[0.98, 0.02])

    solar_gen = (
        CAPACITY
        * EFFICIENCY
        * df["performance_ratio"]
        * (df["effective_irradiance"] / max_eff_irr)
        * df["temperature_factor"]
        * df["cloud_factor"]
        * soiling_loss
        * inverter_efficiency
        * sensor_noise
        * forced_outage
    )

    return solar_gen.clip(0, CAPACITY)


# ---------------------------------------------------------------------------
# 5. Wind Power-Curve Model
# ---------------------------------------------------------------------------
def calculate_wind_generation(df: pd.DataFrame, cfg: dict) -> pd.Series:
    """
    Classic 3-region wind turbine power curve:
      Region 1 (<cut-in)  → 0 MW
      Region 2 (cut-in … rated) → cubic ramp
      Region 3 (rated … cut-out) → rated power
      Region 4 (>cut-out) → 0 MW (safety shutdown)
    """
    wind_cfg   = cfg["wind"]
    CAPACITY   = wind_cfg["installed_capacity_mw"]
    EFFICIENCY = wind_cfg["efficiency"]
    V_CI       = wind_cfg["cut_in_speed_ms"]
    V_R        = wind_cfg["rated_speed_ms"]
    V_CO       = wind_cfg["cut_out_speed_ms"]

    v = df["wind_speed_ms"].clip(lower=0)
    wind_gen = pd.Series(0.0, index=df.index)

    # Region 2: cubic ramp
    mask_r2 = (v >= V_CI) & (v < V_R)
    wind_gen[mask_r2] = (
        ((v[mask_r2] - V_CI) / (V_R - V_CI)) ** 3
        * CAPACITY * EFFICIENCY
    )

    # Region 3: rated output
    mask_r3 = (v >= V_R) & (v <= V_CO)
    wind_gen[mask_r3] = CAPACITY * EFFICIENCY

    # Introduce real-world variances (stochastic noise)
    np.random.seed(101)
    n_samples = len(df)
    
    # 1. Wake effects / aerodynamic turbulence: varies between 0.90 and 1.0
    wake_loss = np.random.uniform(0.90, 1.0, n_samples)
    
    # 2. Sensor measurement noise: Gaussian noise std dev 2%
    sensor_noise = np.random.normal(1.0, 0.02, n_samples)
    
    wind_gen = wind_gen * wake_loss * sensor_noise

    return wind_gen.clip(0, CAPACITY)


# ---------------------------------------------------------------------------
# 6. Assemble Generation Dataframe
# ---------------------------------------------------------------------------
def generate_total_output(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    logger.info("Calculating Solar Generation (pvlib-informed)…")
    df["solar_generation_mw"] = calculate_solar_generation(df, cfg)

    logger.info("Calculating Wind Generation (power-curve)…")
    df["wind_generation_mw"] = calculate_wind_generation(df, cfg)

    logger.info("Calculating Total Generation…")
    df["total_generation_mw"] = df["solar_generation_mw"] + df["wind_generation_mw"]

    # Capacity Factor = Actual / Installed
    total_installed = cfg["solar"]["installed_capacity_mw"] + cfg["wind"]["installed_capacity_mw"]
    df["capacity_factor"] = (df["total_generation_mw"] / total_installed).clip(0, 1)

    return df


# ---------------------------------------------------------------------------
# 7. Validation
# ---------------------------------------------------------------------------
def validate_generation_data(df: pd.DataFrame, cfg: dict) -> bool:
    """
    Enforce hard physics constraints before persisting data.
    """
    logger.info("Running validation checks…")
    solar_cap = cfg["solar"]["installed_capacity_mw"]
    wind_cap  = cfg["wind"]["installed_capacity_mw"]

    gen_cols = ["solar_generation_mw", "wind_generation_mw", "total_generation_mw"]
    pv_cols  = [
        "effective_irradiance", "cell_temperature_c",
        "temperature_factor", "cloud_factor", "performance_ratio", "capacity_factor",
        "solar_zenith", "solar_elevation", "solar_azimuth", "air_mass",
        "clear_sky_irradiance_kwh_m2_day", "poa_irradiance_w_m2"
    ]

    # No nulls
    if df[gen_cols + pv_cols].isnull().any().any():
        logger.error("Validation Failed: Null values in engineered columns.")
        return False

    # No negative generation
    if (df[gen_cols] < 0).any().any():
        logger.error("Validation Failed: Negative generation values detected.")
        return False

    # Capacity ceilings
    if (df["solar_generation_mw"] > solar_cap).any():
        logger.error("Validation Failed: Solar exceeds installed capacity.")
        return False
    if (df["wind_generation_mw"] > wind_cap).any():
        logger.error("Validation Failed: Wind exceeds installed capacity.")
        return False

    # Cloud factor ∈ [0, 1]
    if ((df["cloud_factor"] < 0) | (df["cloud_factor"] > 1)).any():
        logger.error("Validation Failed: Cloud factor out of [0, 1] bounds.")
        return False

    # Temperature factor ∈ [0.70, 1.05]
    if ((df["temperature_factor"] < 0.70) | (df["temperature_factor"] > 1.05)).any():
        logger.error("Validation Failed: Temperature factor out of physical limits.")
        return False

    logger.info("All validation checks passed ✓")
    return True


# ---------------------------------------------------------------------------
# 8. Save Output
# ---------------------------------------------------------------------------
def save_generation_data(df: pd.DataFrame) -> None:
    """
    Persist generation + all PV engineered features to data/processed/.
    All downstream ML models consume this file.
    """
    output_cols = [
        "date", "site_name",
        "solar_generation_mw", "wind_generation_mw", "total_generation_mw",
        # PV engineered features (consumed by ML feature_engineering)
        "ghi_w_m2", "effective_irradiance", "cloud_factor",
        "cell_temperature_c", "temperature_factor",
        "performance_ratio", "capacity_factor",
        "solar_zenith", "solar_elevation", "solar_azimuth", "air_mass",
        "clear_sky_irradiance_kwh_m2_day", "poa_irradiance_w_m2"
    ]
    # site_name may be absent in some weather CSVs — add a default
    if "site_name" not in df.columns:
        df["site_name"] = "Khavda"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df[output_cols].to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Generation data saved → {OUTPUT_PATH}")


# ---------------------------------------------------------------------------
# 9. Main Orchestration
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("=" * 60)
    logger.info("Physics-Informed PV Generation Engine — Starting")
    logger.info("=" * 60)

    try:
        cfg = load_config()
        df  = load_weather_data()
        df  = engineer_pv_features(df, cfg)
        df  = generate_total_output(df, cfg)

        if validate_generation_data(df, cfg):
            save_generation_data(df)
        else:
            logger.error("Pipeline halted — validation failed.")

    except Exception as exc:
        logger.exception(f"Pipeline failed: {exc}")
        raise

    logger.info("Physics-Informed PV Generation Engine — Completed ✓")


if __name__ == "__main__":
    main()
