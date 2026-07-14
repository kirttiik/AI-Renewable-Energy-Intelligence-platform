import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove wind from multi-day chart
content = re.sub(r"fig_multi\.add_trace\(go\.Scatter\(\s*x=hdf\['datetime'\],\s*y=hdf\['wind_generation_mw'\],.*?#5B9BD5'\)\s*\)\s*\)\n", "", content, flags=re.DOTALL)
content = content.replace("c1.metric(\"Peak Solar Hour\", f\"{peak_solar_hour}:00\")\n        c2.metric(\"Peak Wind Hour\",  f\"{peak_wind_hour}:00\")\n        c3.metric(\"Peak Combined\",   f\"{peak_hour_total}:00\")", "c1.metric(\"Peak Solar Hour\", f\"{peak_solar_hour}:00\")\n        c2.empty()\n        c3.empty()")

# 2. Remove wind model metrics from the explainability tab
wind_metrics_regex = r"_wind_m\s*=\s*{.*?}.*?c_p2\.markdown\(\"\*\*Wind Generation Model\*\*\"\).*?c_p2\.write.*?c_p2\.write.*?c_p2\.write.*?c_p2\.write.*?\n"
content = re.sub(wind_metrics_regex, "", content, flags=re.DOTALL)

# 3. Remove Wind from the radar chart
content = re.sub(r"fig_radar\.add_trace\(go\.Scatterpolar.*?name='Wind Model'\)\)", "", content, flags=re.DOTALL)
content = re.sub(r"_w_r2\s*=\s*round.*?_w_rmse_score\s*=\s*max.*?\n", "", content, flags=re.DOTALL)

# 4. Remove entire IEX Analytics rendering function
iex_regex = r"# IEX ANALYTICS — Data Loader.*?def render_iex_analytics\(\):.*?(?=\n# ==========================================|\Z)"
content = re.sub(iex_regex, "", content, flags=re.DOTALL)

# 5. Remove "IEX Market Analytics" from the sidebar navigation
content = content.replace("\"IEX Market Analytics\",", "")
content = content.replace("elif page == \"IEX Market Analytics\":\n        render_iex_analytics()", "")

# 6. Remove Wind speed chart
wind_chart_regex = r"fig_wind\s*=\s*px\.line\(.*?st\.plotly_chart\(fig_wind, use_container_width=True\)"
content = re.sub(wind_chart_regex, "", content, flags=re.DOTALL)

# 7. Remove wind from Hourly Solar + Wind Generation Profile
content = re.sub(r"fig_hourly\.add_trace\(go\.Bar\(\s*x=hdf\['hour'\],\s*y=hdf\['wind_generation_mw'\].*?#5B9BD5'\)\s*\)\s*\)\n", "", content, flags=re.DOTALL)
content = content.replace("Hourly Solar + Wind Generation Profile", "Hourly Solar Generation Profile")

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Scrubbed wind and IEX from app.py")
