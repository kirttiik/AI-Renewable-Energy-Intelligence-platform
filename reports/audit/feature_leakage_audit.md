# Feature Leakage Audit Report

## 1. PVLib / Physics Target Leakage
The following features are currently calculated in `generate_renewable_generation.py` BEFORE the target `solar_generation_mw` is calculated. Since the target is a direct mathematical product of these features (Target = Capacity x PR x Effective Irradiance x Temperature Factor x Noise), using these features in ML models is a direct target leak.

| Feature | Source | Target Dependency | Available at Forecast? | Leakage Risk | Decision |
|---|---|---|---|---|---|
| `effective_irradiance` | PVLib / Math | Target is proportional | Yes | EXTREME | **REMOVE** |
| `cell_temperature_c` | PVLib | Used for Temp Factor | Yes | HIGH | **REMOVE** |
| `temperature_factor` | Math | Target is proportional | Yes | EXTREME | **REMOVE** |
| `cloud_factor` | Math | Target is proportional | Yes | EXTREME | **REMOVE** |
| `performance_ratio` | Config | Target is proportional | Yes | EXTREME | **REMOVE** |
| `capacity_factor` | Math | Derived from Target | No | EXTREME | **REMOVE** |

## 2. Temporal Target Leakage (Multi-Step Horizon)
The following features are derived from the target `solar_generation_mw`. They are valid ONLY IF strictly limited to past observations (e.g., `shift(1)` relative to the prediction date).

| Feature | Source | Target Dependency | Available at Forecast? | Leakage Risk | Decision |
|---|---|---|---|---|---|
| `h_mean_7d` | Target History | Yes | Yes (if `shift(1)`) | HIGH | **FIX BOUNDARIES** |
| `h_median_7d`| Target History | Yes | Yes (if `shift(1)`) | HIGH | **FIX BOUNDARIES** |
| `h_max_7d` | Target History | Yes | Yes (if `shift(1)`) | HIGH | **FIX BOUNDARIES** |
| `h_mean_30d` | Target History | Yes | Yes (if `shift(1)`) | HIGH | **FIX BOUNDARIES** |

*Note: Future forecast windows (Days 1 to 14) MUST forward-fill the last known historical rolling value. They must never use the future simulated target to calculate future rolling features.*

## 3. Approved Leakage-Free Features
The ML pipeline may safely use:
- `ghi_kwh_m2_day`
- `direct_radiation_kwh_m2_day`
- `dhi_kwh_m2_day`
- `dni_kwh_m2_day`
- `clearness_index`, `diffuse_fraction`, `direct_fraction`
- `cloud_cover_pct`, `cloud_cover_low_pct`, `cloud_cover_mid_pct`, `cloud_cover_high_pct`
- `temperature_c`, `temperature_max_c`, `temperature_min_c`
- `humidity_pct`, `rainfall_mm`, `wind_speed_ms`, `visibility_km`
- `month`, `day_of_year`, `week_of_year`, `is_monsoon`, `is_weekend`
- Appropriately boundary-controlled historical features (`h_mean_7d`, etc.)
