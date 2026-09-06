# Unit and Dimensionality Audit Report

## 1. Generation Metrics
| Variable | Unit | Temporal Resolution | Meaning |
|---|---|---|---|
| `solar_generation_mw` | MW | Daily (Instantaneous) | The absolute peak AC power generated during the day. |
| `daily_energy_mwh` | MWh | Daily (Cumulative) | The total energy generated over the course of the day. Currently calculated as `solar_generation_mw * 7.5` (assuming 7.5 equivalent peak hours). |
| `grid_export_mwh` | MWh | Daily (Cumulative) | `daily_energy_mwh` minus auxiliary consumption. |

## 2. Weather & Irradiance Metrics
| Variable | Unit | Temporal Resolution | Meaning |
|---|---|---|---|
| `ghi_kwh_m2_day` | kWh/m² | Daily (Cumulative) | Total Global Horizontal Irradiance received over the entire day. |
| `ghi_w_m2` | W/m² | Daily (Instantaneous) | Peak irradiance, calculated as `ghi_kwh_m2_day * 1000 / PSH`. |
| `effective_irradiance` | kWh/m² | Daily (Cumulative) | `ghi_kwh_m2_day` multiplied by `cloud_factor` (attenuation). |
| `temperature_c` | °C | Daily (Average) | Mean daily ambient air temperature. |

## 3. Financial & DSM Metrics
| Variable | Unit | Temporal Resolution | Meaning |
|---|---|---|---|
| `dsm_deviation_mw` | MW | Daily (Instantaneous peak) | Difference between actual/forecast peak MW and scheduled peak MW. |
| `dsm_deviation_mwh` | MWh | Daily (Cumulative) | Currently MISSING. Must be derived as `deviation_mw * interval_duration_hours` (e.g. 7.5 hours for daily solar peak equivalent). |
| `penalty_rate_inr_per_mwh` | ₹/MWh | Constant | The regulatory penalty rate. Currently hardcoded to 2500. |
| `dsm_penalty_inr` | ₹ | Daily (Cumulative) | Total financial exposure. *CRITICAL BUG: Currently calculated as MW x ₹/MWh instead of MWh x ₹/MWh.* |

## 4. KPIs
| Variable | Unit | Meaning |
|---|---|---|
| `cuf_daily` (Capacity Factor) | % | `daily_energy_mwh / (Capacity_MW * 24)`. Represents 24-hour capacity utilization. |
| `specific_yield_kwh_kwp` | kWh/kWp | Energy generated per kW of installed capacity. |
| `pr_daily` (Performance Ratio) | Unitless | Ratio of actual yield to theoretical yield at standard test conditions. |
| `soiling_loss_pct` | % | Estimated generation lost to panel dust/soiling. |
