import os
import pandas as pd
import streamlit as st

def check_threshold_alerts():
    """
    Evaluates configurable limits against live EnergyMap data and forecast data.
    Returns a list of active alerts to be displayed in the UI.
    """
    ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    alerts = []
    
    # 1. Evaluate EnergyMap Live Data
    em_path = os.path.join(ROOT, 'data', 'processed', 'energymap_live.csv')
    try:
        if os.path.exists(em_path):
            df_em = pd.read_csv(em_path)
            if not df_em.empty:
                latest_price = float(df_em['dam_price_inr'].iloc[0])
                latest_freq_out = float(df_em['frequency_out_of_band_pct'].iloc[0])
                
                if latest_price > 7500:
                    alerts.append({
                        "level": "error",
                        "msg": f"🚨 IEX DAM Price Alert: Critical pricing detected (₹{latest_price:,.0f}/MWh). Consider maximizing discharge/bids."
                    })
                elif latest_price > 6000:
                    alerts.append({
                        "level": "warning",
                        "msg": f"⚠️ IEX DAM Price Watch: Elevated pricing (₹{latest_price:,.0f}/MWh). Monitor intraday markets."
                    })
                    
                if latest_freq_out > 2.0:
                    alerts.append({
                        "level": "error",
                        "msg": f"🚨 Grid Stability Alert: Grid frequency is outside IEGC bands {latest_freq_out}% of the time today. High DSM penalty risk."
                    })
    except Exception as e:
        pass

    # 2. Evaluate Forecasted Demand/Curtailment (Mock Example)
    try:
        df_solar = pd.read_csv(os.path.join(ROOT, 'reports', 'solar', 'solar_predictions.csv'))
        if not df_solar.empty:
            max_gen = float(df_solar['predicted_solar_generation_mw'].max())
            if max_gen > 15000:
                alerts.append({
                    "level": "warning",
                    "msg": f"⚠️ High Generation Alert: Approaching grid limits ({max_gen:,.0f} MW). Monitor for curtailment instructions."
                })
    except:
        pass
        
    return alerts

def render_alerts_banner():
    """Renders active alerts at the top of the application."""
    alerts = check_threshold_alerts()
    for alert in alerts:
        if alert['level'] == 'error':
            st.error(alert['msg'])
        elif alert['level'] == 'warning':
            st.warning(alert['msg'])
        else:
            st.info(alert['msg'])
