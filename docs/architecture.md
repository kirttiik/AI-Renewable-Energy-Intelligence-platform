# 🏗️ System Architecture

**Khavda Renewable Energy Digital Twin**

This document outlines the high-level architecture, data flows, and technological foundations of the Renewable Energy Market Intelligence Platform.

---

## 1. System Architecture Diagram

```mermaid
flowchart TD
    subgraph Data Ingestion
    A[NASA POWER API] --> B[Weather Ingestion]
    end
    
    subgraph Core Simulation
    B --> C[Generation Simulation]
    end
    
    subgraph Machine Learning Forecasting
    C --> D1[Solar Forecast Model]
    C --> D2[Wind Forecast Model]
    C --> D3[Total Output Forecast Model]
    end
    
    subgraph Analytics Engines
    D1 --> E1[Carbon Analytics]
    D2 --> E1
    D3 --> E1
    
    B --> E2[Weather Risk Analytics]
    C --> E3[Revenue Analytics]
    
    D1 --> E4[AI Explainability]
    D2 --> E4
    D3 --> E4
    end
    
    subgraph Executive Intelligence
    E1 --> F[Executive Summary Engine]
    E2 --> F
    E3 --> F
    E4 --> F
    D3 --> F
    end
    
    subgraph Dashboards & Reporting
    F --> G1[(Power BI)]
    F --> G2[(Streamlit App)]
    end
```

---

## 2. Processing Workflow

1. **Weather Ingestion**: Connects to the NASA POWER API to download historical and current meteorological data (radiation, wind speed, temperature, humidity) for the Khavda coordinates.
2. **Generation Simulation**: Applies physical models and capacity constraints to synthesize ground-truth historical generation data (MW) for solar and wind assets.
3. **Forecasting Models**: XGBoost models predict 24-hour ahead and historical holdout generation values for Solar, Wind, and Total Output.
4. **Carbon Analytics**: Translates forecasted generation into avoided CO₂ emissions, coal saved, and trees equivalent metrics.
5. **Weather Risk Analytics**: Scans meteorological parameters to detect extreme conditions (e.g., Heatwaves, Dust Storms) and triggers alerts.
6. **Revenue Analytics**: Merges generation expectations with financial tariffs and applies revenue-at-risk deductions based on weather severity.
7. **AI Explainability**: Aggregates feature importance across all models to generate plain-text interpretations of AI predictions.
8. **Executive Summary**: A unified pipeline that joins all output tables chronologically into a single, comprehensive management dataset.

---

## 3. Technology Architecture

| Layer | Technology Stack |
| :--- | :--- |
| **Data Ingestion** | `requests`, NASA POWER API |
| **Data Processing** | `pandas`, `numpy` |
| **Machine Learning** | `xgboost`, `scikit-learn` |
| **Visualization (Local)**| `matplotlib`, `seaborn` |
| **Data Storage** | Local File System (CSV) / PostgreSQL *(Planned)* |
| **Business Intelligence**| Power BI *(Planned)*, Streamlit *(Planned)* |
| **Version Control** | Git / GitHub |

---

## 4. Module Interaction Diagram

```mermaid
sequenceDiagram
    participant API as NASA POWER
    participant ING as Ingestion Layer
    participant ML as ML Forecasting
    participant ANA as Analytics Engines
    participant EXEC as Executive Summary
    
    API->>ING: Return JSON Weather Data
    ING->>ML: Pass Cleaned Weather Matrix
    ML->>ML: Predict Solar/Wind/Total (MW)
    ML->>ANA: Pass Forecast Arrays
    ING->>ANA: Pass Weather Risk Matrix
    ANA->>ANA: Calculate Risk/Revenue/ESG
    ANA->>EXEC: Push Flattened Metrics
    EXEC->>EXEC: Join all tables on Date
    EXEC-->>EXEC: Output Final CSVs
```
