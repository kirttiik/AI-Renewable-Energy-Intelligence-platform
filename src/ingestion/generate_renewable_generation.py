"""
Khavda Solar PV Generation Engine (SCADA-Grade Physics Model)
=============================================================
Adani Green Energy Ltd (AGEL) — Khavda, Gujarat

Physics Model calibrated to real-world Khavda operating data:
  - Installed Capacity: 20 GW AC (27 GW DC)
  - Target daily generation: 10,000 - 12,000 MWh (good days)
  - Annual CUF: ~27%
  - Location: 23.83 N, 68.77 E (Gujarat desert)

SCADA-Grade Output Columns:
  solar_generation_mw         - Instantaneous daily peak AC output (MW)
  daily_energy_mwh            - Total AC energy generated per day (MWh)
  cuf_daily                   - Capacity Utilization Factor for the day
  specific_yield_kwh_kwp      - Specific energy yield (kWh/kWp)
  pr_daily                    - Daily Performance Ratio
  soiling_loss_pct            - Estimated soiling loss (%)
  inverter_availability_pct   - Inverter uptime (%)
  grid_export_mwh             - Energy exported to grid after auxiliary consumption
  effective_irradiance        - GHI after cloud attenuation (kWh/m2/day)
  ghi_w_m2                    - Peak GHI in W/m2
  cell_temperature_c          - PV cell operating temperature (degC)
  temperature_factor          - Efficiency multiplier from temperature
  cloud_factor                - Cloud attenuation factor [0, 1]
  performance_ratio           - System PR (constant from config)
  capacity_factor             - Ratio of actual to rated output
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
    logging.warning("pvlib not installed — using NOCT fallback model.")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

ROOT_DIR     = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEATHER_PATH = os.path.join(ROOT_DIR, "data", "raw", "khavda_weather.csv")
CONFIG_PATH  = os.path.join(ROOT_DIR, "config", "plant_config.yaml")
OUTPUT_PATH  = os.path.join(ROOT_DIR, "data", "processed", "khavda_generation.csv")


# ---------------------------------------------------------------------------
# 1. Load Configuration
# ---------------------------------------------------------------------------
def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        cfg = yaml.safe_load(f)
    s = cfg.get("solar", {})
    if s.get("installed_capacity_mw", 0) <= 0:
        raise ValueError("installed_capacity_mw must be > 0 in plant_config.yaml")
    logger.info(f"Loaded config: {cfg['site']['name']} | {s['installed_capacity_mw']} MW")
    return cfg


# ---------------------------------------------------------------------------
# 2. Load Weather Data
# ---------------------------------------------------------------------------
def load_weather_data() -> pd.DataFrame:
    logger.info(f"Loading weather data from {WEATHER_PATH}")
    df = pd.read_csv(WEATHER_PATH)

    forecast_path = WEATHER_PATH.replace("khavda_weather.csv", "khavda_weather_forecast.csv")
    if os.path.exists(forecast_path):
        forecast_df = pd.read_csv(forecast_path)
        df = pd.concat([df, forecast_df], ignore_index=True)
        df = df.drop_duplicates(subset=["date"], keep="last")

    df["date"] = pd.to_datetime(df["date"])
    numeric_cols = [
        "temperature_c", "cloud_cover_pct",
        "solar_radiation_kwh_m2_day", "wind_speed_ms",
        "humidity_pct", "rainfall_mm"
    ]
    df[numeric_cols] = df[numeric_cols].ffill().fillna(0)
    logger.info(f"Weather data loaded -- {len(df)} rows ({df['date'].min().date()} to {df['date'].max().date()})")
    return df


# ---------------------------------------------------------------------------
# 3. PV Feature Engineering
# ---------------------------------------------------------------------------
def engineer_pv_features(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    s     = cfg["solar"]
    NOCT  = s["noct_c"]
    GAMMA = s["temperature_coefficient"]
    T_STC = s["reference_temp_c"]
    PR    = s["performance_ratio"]
    PSH   = s.get("peak_sun_hours", 5.8)

    # GHI W/m2 peak approximation
    df["ghi_w_m2"] = (df["solar_radiation_kwh_m2_day"] * 1000.0 / PSH).clip(lower=0)

    # Cloud factor
    df["cloud_factor"] = (1.0 - df["cloud_cover_pct"] / 100.0).clip(0.0, 1.0)

    # Effective irradiance after cloud attenuation
    df["effective_irradiance"] = (df["solar_radiation_kwh_m2_day"] * df["cloud_factor"]).clip(lower=0)

    # PV Cell Temperature
    if HAS_PVLIB:
        df["cell_temperature_c"] = pvlib.temperature.faiman(
            poa_global=df["ghi_w_m2"],
            temp_air=df["temperature_c"],
            wind_speed=df["wind_speed_ms"].clip(lower=0),
        )
    else:
        df["cell_temperature_c"] = (
            df["temperature_c"] + ((NOCT - 20.0) / 800.0) * df["ghi_w_m2"]
        )

    # Temperature Factor
    df["temperature_factor"] = (
        1.0 + GAMMA * (df["cell_temperature_c"] - T_STC)
    ).clip(0.70, 1.05)

    # Performance Ratio column
    df["performance_ratio"] = PR

    # Advanced pvlib solar geometry features
    if HAS_PVLIB:
        lat  = cfg["site"]["latitude"]
        lon  = cfg["site"]["longitude"]
        tz   = "Asia/Kolkata"
        tilt = s.get("tilt_degrees", 25.0)
        azim = s.get("azimuth_degrees", 180.0)

        dt_idx = pd.DatetimeIndex(df["date"]).tz_localize(tz) + pd.Timedelta(hours=12, minutes=30)
        solpos = pvlib.solarposition.get_solarposition(dt_idx, lat, lon)

        df["solar_zenith"]    = solpos["zenith"].values
        df["solar_elevation"] = solpos["elevation"].values
        df["solar_azimuth"]   = solpos["azimuth"].values
        df["air_mass"]        = pvlib.atmosphere.get_relative_airmass(df["solar_zenith"]).fillna(1.5)

        loc = pvlib.location.Location(lat, lon, tz=tz)
        cs  = loc.get_clearsky(dt_idx)
        df["clear_sky_irradiance_kwh_m2_day"] = cs["ghi"].values * PSH / 1000.0

        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt, surface_azimuth=azim,
            solar_zenith=df["solar_zenith"], solar_azimuth=df["solar_azimuth"],
            dni=cs["dni"].values, ghi=df["ghi_w_m2"], dhi=cs["dhi"].values
        )
        df["poa_irradiance_w_m2"] = poa["poa_global"].values
    else:
        df["solar_zenith"]                    = 45.0
        df["solar_elevation"]                 = 45.0
        df["solar_azimuth"]                   = 180.0
        df["air_mass"]                        = 1.5
        df["clear_sky_irradiance_kwh_m2_day"] = df["solar_radiation_kwh_m2_day"]
        df["poa_irradiance_w_m2"]             = df["ghi_w_m2"]

    logger.info("PV feature engineering complete.")
    return df


# ---------------------------------------------------------------------------
# 4. SCADA-Calibrated Solar Generation Engine
# ---------------------------------------------------------------------------
def calculate_solar_generation(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """
    Industry-standard PV generation formula calibrated to Khavda:

        AC_Power_MW = Capacity_MW x PR x (Eff_Irr / Max_Irr) x Temp_Factor
                      x (1 - Soiling_Loss) x Inverter_Availability
                      x Grid_Availability x (1 - Cable_Loss) x (1 - Transformer_Loss)

    SCADA output KPIs are computed from this base power.
    """
    s         = cfg["solar"]
    CAPACITY  = s["installed_capacity_mw"]
    PR        = s["performance_ratio"]
    PSH       = s.get("peak_sun_hours", 5.8)
    GRID_AVAIL = s.get("grid_availability_pct", 0.995)
    AUX_CONS  = s.get("auxiliary_consumption_pct", 0.005)
    SOI_BASE  = s.get("soiling_base_pct", 0.02)
    SOI_MAX   = s.get("soiling_max_pct", 0.12)
    INV_EFF   = s.get("inverter_efficiency", 0.98)
    TRF_EFF   = s.get("transformer_efficiency", 0.995)
    CABLE     = s.get("cable_loss_pct", 0.005)

    # Calibrated reference irradiance for Khavda
    # MAX_GHI = 6.75 kWh/m2/day ensures 20GW plant outputs 10k-12k MW at peak (good-day GHI ~5-6 kWh/m2)
    MAX_GHI = 6.75

    n   = len(df)
    rng = np.random.default_rng(seed=42)

    # Soiling model: sawtooth over 15-day clean cycle with seasonal modulation
    clean_interval = int(s.get("soiling_clean_interval_days", 15))
    soiling_cycle  = np.tile(np.linspace(SOI_BASE, SOI_BASE + 0.04, clean_interval), n // clean_interval + 1)[:n]
    months         = pd.DatetimeIndex(df["date"]).month.to_numpy()
    # Monsoon: rain cleans panels (Jun-Sep)
    soiling_cycle  = np.where(np.isin(months, [6, 7, 8, 9]), soiling_cycle * 0.4, soiling_cycle)
    # Dust season: higher soiling (Mar-May)
    soiling_cycle  = np.where(np.isin(months, [3, 4, 5]), np.minimum(soiling_cycle * 2.0, SOI_MAX), soiling_cycle)

    # SCADA measurement noise: +/- 3% (sensor accuracy)
    measurement_noise = rng.normal(1.0, 0.03, n)

    # Inverter availability: 98.5% average uptime, occasional minor trips
    inv_avail = rng.choice([1.0, 0.97, 0.95, 0.99], size=n, p=[0.92, 0.04, 0.02, 0.02])

    # Normalised effective irradiance
    eff_irr_norm = (df["effective_irradiance"] / MAX_GHI).clip(0.0, 1.0)

    # Final AC power at grid connection
    solar_gen = (
        CAPACITY
        * PR
        * eff_irr_norm
        * df["temperature_factor"]
        * (1.0 - soiling_cycle)
        * inv_avail
        * INV_EFF
        * TRF_EFF
        * (1.0 - CABLE)
        * GRID_AVAIL
        * measurement_noise
    )
    solar_gen = solar_gen.clip(0.0, CAPACITY)

    # Assign columns
    df["solar_generation_mw"]       = solar_gen.values
    df["total_generation_mw"]       = df["solar_generation_mw"]
    df["daily_energy_mwh"]          = (df["solar_generation_mw"] * PSH).round(2)
    df["grid_export_mwh"]           = (df["daily_energy_mwh"] * (1.0 - AUX_CONS)).round(2)
    df["cuf_daily"]                 = (df["solar_generation_mw"] / CAPACITY).round(4)
    df["pr_daily"]                  = (eff_irr_norm.values * df["temperature_factor"].values * PR).clip(0, 1).round(4)
    df["soiling_loss_pct"]          = (soiling_cycle * 100).round(2)
    df["inverter_availability_pct"] = (inv_avail * 100).round(2)
    df["specific_yield_kwh_kwp"]    = ((df["daily_energy_mwh"] * 1000) / (CAPACITY * 1000)).round(4)
    df["capacity_factor"]           = df["cuf_daily"]

    # Pure physics baseline (no stochastic noise) — for Actual vs ML vs Physics comparison
    physics_base = (
        CAPACITY * PR * eff_irr_norm * df["temperature_factor"]
        * (1.0 - SOI_BASE)   # use base soiling only
        * INV_EFF * TRF_EFF * (1.0 - CABLE) * GRID_AVAIL
    ).clip(0.0, CAPACITY)
    df["physics_baseline_mw"]   = physics_base.values.round(2)
    df["physics_baseline_mwh"]  = (df["physics_baseline_mw"] * PSH).round(2)

    logger.info(
        f"Generation computed -- peak={df['solar_generation_mw'].max():.1f} MW, "
        f"mean={df['solar_generation_mw'].mean():.1f} MW, "
        f"mean_daily_mwh={df['daily_energy_mwh'].mean():.0f} MWh"
    )
    return df


# ---------------------------------------------------------------------------
# 5. Validation
# ---------------------------------------------------------------------------
def validate_generation_data(df: pd.DataFrame, cfg: dict) -> bool:
    cap = cfg["solar"]["installed_capacity_mw"]
    logger.info("Running SCADA validation checks...")

    critical_cols = [
        "solar_generation_mw", "daily_energy_mwh", "cuf_daily",
        "effective_irradiance", "cell_temperature_c",
        "temperature_factor", "cloud_factor", "performance_ratio"
    ]
    if df[critical_cols].isnull().any().any():
        logger.error("Validation Failed: Null values in critical columns.")
        return False
    if (df["solar_generation_mw"] < 0).any():
        logger.error("Validation Failed: Negative generation values detected.")
        return False
    if (df["solar_generation_mw"] > cap).any():
        over = (df["solar_generation_mw"] > cap).sum()
        logger.error(f"Validation Failed: {over} rows exceed installed capacity {cap} MW.")
        return False
    if ((df["cloud_factor"] < 0) | (df["cloud_factor"] > 1)).any():
        logger.error("Validation Failed: Cloud factor out of [0,1] bounds.")
        return False
    if ((df["temperature_factor"] < 0.70) | (df["temperature_factor"] > 1.05)).any():
        logger.error("Validation Failed: Temperature factor out of physical limits.")
        return False

    logger.info("All SCADA validation checks passed.")
    return True


# ---------------------------------------------------------------------------
# 6. Save Output
# ---------------------------------------------------------------------------
def save_generation_data(df: pd.DataFrame) -> None:
    output_cols = [
        "date", "site_name",
        "solar_generation_mw", "total_generation_mw",
        "daily_energy_mwh", "grid_export_mwh",
        "physics_baseline_mw", "physics_baseline_mwh",
        "cuf_daily", "pr_daily",
        "specific_yield_kwh_kwp", "soiling_loss_pct", "inverter_availability_pct",
        "ghi_w_m2", "effective_irradiance", "cloud_factor",
        "cell_temperature_c", "temperature_factor",
        "performance_ratio", "capacity_factor",
        "solar_zenith", "solar_elevation", "solar_azimuth", "air_mass",
        "clear_sky_irradiance_kwh_m2_day", "poa_irradiance_w_m2"
    ]
    if "site_name" not in df.columns:
        df["site_name"] = "Khavda Renewable Energy Park"
    final_cols = [c for c in output_cols if c in df.columns]
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df[final_cols].to_csv(OUTPUT_PATH, index=False)
    logger.info(f"Generation data saved to {OUTPUT_PATH} -- {len(df)} rows.")


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------
def main() -> None:
    logger.info("=" * 60)
    logger.info("Khavda Solar Generation Engine (SCADA-Grade) -- Starting")
    logger.info("=" * 60)
    try:
        cfg = load_config()
        df  = load_weather_data()
        df  = engineer_pv_features(df, cfg)
        df  = calculate_solar_generation(df, cfg)
        if not validate_generation_data(df, cfg):
            raise RuntimeError("Physics validation failed. Aborting save.")
        save_generation_data(df)
        logger.info("=" * 60)
        logger.info("Khavda Solar Generation Engine -- Completed")
        logger.info("=" * 60)
    except Exception as exc:
        logger.exception(f"Pipeline failed: {exc}")
        raise


if __name__ == "__main__":
    main()
