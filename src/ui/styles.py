"""
styles.py — AGEL Enterprise Design System
==========================================
Complete CSS design language for the Khavda Renewable Energy Intelligence Platform.
Inspired by enterprise platforms like Power BI, GE Digital APM, and Tableau.

Color Palette:
  • Primary Deep Blue   : #0D1B2A, #1B3A5C, #2C5F8A
  • Secondary Green     : #0A3D2E, #1A7A4A, #27AE60
  • Accent Orange       : #C05810, #E67E22, #F39C12
  • Neutral             : #0D1117, #161B22, #21262D, #30363D, #8B949E, #C9D1D9, #F0F6FC
  • Status Green        : #238636
  • Status Yellow       : #9E6A03
  • Status Red          : #DA3633
"""

ENTERPRISE_CSS = """
<style>

/* ─────────────────────────────────────────────────────────────────────────── */
/* GOOGLE FONTS IMPORT                                                          */
/* ─────────────────────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ─────────────────────────────────────────────────────────────────────────── */
/* ROOT TOKENS                                                                   */
/* ─────────────────────────────────────────────────────────────────────────── */
:root {
  --bg-primary:       #0D1117;
  --bg-secondary:     #161B22;
  --bg-card:          #1C2128;
  --bg-card-hover:    #21262D;
  --bg-input:         #21262D;
  --border-subtle:    #30363D;
  --border-accent:    #1B3A5C;

  --text-primary:     #F0F6FC;
  --text-secondary:   #C9D1D9;
  --text-muted:       #8B949E;
  --text-link:        #58A6FF;

  --blue-primary:     #1B3A5C;
  --blue-bright:      #2C5F8A;
  --blue-light:       #58A6FF;
  --blue-glow:        rgba(88, 166, 255, 0.15);

  --green-primary:    #1A7A4A;
  --green-bright:     #27AE60;
  --green-light:      #2ECC71;
  --green-glow:       rgba(46, 204, 113, 0.15);
  --green-status:     #238636;

  --orange-primary:   #E67E22;
  --orange-bright:    #F39C12;
  --orange-glow:      rgba(243, 156, 18, 0.15);

  --red-status:       #DA3633;
  --yellow-status:    #9E6A03;

  --radius-sm:        6px;
  --radius-md:        10px;
  --radius-lg:        16px;
  --radius-xl:        20px;

  --shadow-sm:        0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3);
  --shadow-md:        0 4px 12px rgba(0,0,0,0.5), 0 2px 4px rgba(0,0,0,0.3);
  --shadow-lg:        0 10px 40px rgba(0,0,0,0.6), 0 4px 8px rgba(0,0,0,0.3);
  --shadow-glow-blue: 0 0 20px rgba(88, 166, 255, 0.12);
  --shadow-glow-green:0 0 20px rgba(46, 204, 113, 0.12);

  --font-sans:        'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono:        'JetBrains Mono', 'Fira Code', monospace;

  --transition-fast:  150ms ease;
  --transition-md:    250ms ease;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* GLOBAL RESETS & BASE                                                          */
/* ─────────────────────────────────────────────────────────────────────────── */
.stApp {
  background-color: var(--bg-primary) !important;
  font-family: var(--font-sans) !important;
  color: var(--text-primary) !important;
}

.block-container {
  padding: 1.5rem 2rem !important;
  max-width: 1600px !important;
}

h1, h2, h3, h4, h5, h6 {
  font-family: var(--font-sans) !important;
  color: var(--text-primary) !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em;
  line-height: 1.3;
}

h1 { font-size: 1.75rem !important; font-weight: 700 !important; }
h2 { font-size: 1.35rem !important; }
h3 { font-size: 1.15rem !important; }

p, li, span { font-family: var(--font-sans) !important; color: var(--text-secondary); }

a { color: var(--blue-light) !important; text-decoration: none; }
a:hover { text-decoration: underline; }

/* ─────────────────────────────────────────────────────────────────────────── */
/* SIDEBAR                                                                        */
/* ─────────────────────────────────────────────────────────────────────────── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0D1117 0%, #111827 100%) !important;
  border-right: 1px solid var(--border-subtle) !important;
  box-shadow: 4px 0 24px rgba(0,0,0,0.4) !important;
}

[data-testid="stSidebar"] .stRadio label {
  color: var(--text-secondary) !important;
  font-size: 0.875rem !important;
  font-weight: 500 !important;
  padding: 6px 10px !important;
  border-radius: var(--radius-sm) !important;
  transition: all var(--transition-fast) !important;
  cursor: pointer;
}

[data-testid="stSidebar"] .stRadio label:hover {
  background: rgba(88, 166, 255, 0.08) !important;
  color: var(--text-primary) !important;
}

[data-testid="stSidebar"] .stRadio [aria-checked="true"] + label,
[data-testid="stSidebar"] .stRadio [data-testid="stWidgetLabel"]:has(+ [aria-checked="true"]) {
  background: var(--blue-glow) !important;
  color: var(--blue-light) !important;
  border-left: 3px solid var(--blue-light) !important;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
  color: var(--text-primary) !important;
}

[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
  color: var(--text-muted) !important;
  font-size: 0.8rem !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* STREAMLIT METRICS                                                              */
/* ─────────────────────────────────────────────────────────────────────────── */
[data-testid="metric-container"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-md) !important;
  padding: 18px 20px !important;
  box-shadow: var(--shadow-sm) !important;
  transition: all var(--transition-md) !important;
  position: relative;
  overflow: hidden;
}

[data-testid="metric-container"]:hover {
  border-color: var(--blue-bright) !important;
  box-shadow: var(--shadow-md), var(--shadow-glow-blue) !important;
  transform: translateY(-1px) !important;
}

[data-testid="metric-container"]::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--blue-bright), var(--green-bright));
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}

[data-testid="stMetricLabel"] {
  font-size: 0.72rem !important;
  font-weight: 600 !important;
  color: var(--text-muted) !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
}

[data-testid="stMetricValue"] {
  font-size: 1.6rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  font-family: var(--font-sans) !important;
  line-height: 1.2 !important;
}

[data-testid="stMetricDelta"] {
  font-size: 0.78rem !important;
  font-weight: 600 !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* PLOTLY CHARTS                                                                  */
/* ─────────────────────────────────────────────────────────────────────────── */
.js-plotly-plot .plotly {
  border-radius: var(--radius-md) !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* STREAMLIT BUTTONS                                                              */
/* ─────────────────────────────────────────────────────────────────────────── */
.stButton > button {
  background: var(--bg-card) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-md) !important;
  font-family: var(--font-sans) !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  padding: 8px 16px !important;
  transition: all var(--transition-fast) !important;
  box-shadow: var(--shadow-sm) !important;
}

.stButton > button:hover {
  background: var(--blue-glow) !important;
  border-color: var(--blue-light) !important;
  color: var(--blue-light) !important;
  transform: translateY(-1px) !important;
  box-shadow: var(--shadow-md) !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #1B3A5C 0%, #2C5F8A 100%) !important;
  border-color: var(--blue-bright) !important;
  color: white !important;
  font-weight: 600 !important;
  box-shadow: var(--shadow-md), var(--shadow-glow-blue) !important;
}

.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #2C5F8A 0%, #3A7ABF 100%) !important;
  transform: translateY(-2px) !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* STREAMLIT EXPANDERS                                                            */
/* ─────────────────────────────────────────────────────────────────────────── */
details[data-testid="stExpander"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-md) !important;
  margin-bottom: 12px !important;
  box-shadow: var(--shadow-sm) !important;
}

details[data-testid="stExpander"] summary {
  font-weight: 600 !important;
  font-size: 0.9rem !important;
  color: var(--text-primary) !important;
  padding: 12px 16px !important;
}

details[data-testid="stExpander"] summary:hover {
  background: var(--bg-card-hover) !important;
  border-radius: var(--radius-md) !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* STREAMLIT DATA TABLES                                                          */
/* ─────────────────────────────────────────────────────────────────────────── */
[data-testid="stDataFrame"] {
  border-radius: var(--radius-md) !important;
  overflow: hidden !important;
  border: 1px solid var(--border-subtle) !important;
}

[data-testid="stDataFrame"] th {
  background: var(--bg-secondary) !important;
  color: var(--text-muted) !important;
  font-size: 0.75rem !important;
  font-weight: 600 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.05em !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* STREAMLIT ALERTS / INFO / WARNING / ERROR                                     */
/* ─────────────────────────────────────────────────────────────────────────── */
[data-testid="stAlert"] {
  border-radius: var(--radius-md) !important;
  border-width: 1px !important;
  font-size: 0.875rem !important;
  font-family: var(--font-sans) !important;
}

/* Info */
[data-baseweb="notification"][kind="info"],
.element-container div[role="alert"].stAlert[data-type="info"] {
  background: rgba(88, 166, 255, 0.08) !important;
  border-color: rgba(88, 166, 255, 0.3) !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* STREAMLIT INPUTS / SELECTS / RADIO                                            */
/* ─────────────────────────────────────────────────────────────────────────── */
.stTextInput > div > div > input,
.stSelectbox > div > div > div,
.stMultiSelect > div > div > div,
.stNumberInput > div > div > input,
.stTextArea > div > div > textarea {
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-subtle) !important;
  border-radius: var(--radius-sm) !important;
  font-family: var(--font-sans) !important;
  font-size: 0.875rem !important;
  transition: border-color var(--transition-fast);
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
  border-color: var(--blue-light) !important;
  box-shadow: 0 0 0 3px var(--blue-glow) !important;
}

.stRadio > label, .stCheckbox > label {
  color: var(--text-secondary) !important;
  font-size: 0.875rem !important;
  font-family: var(--font-sans) !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* PROGRESS BARS                                                                  */
/* ─────────────────────────────────────────────────────────────────────────── */
[data-testid="stProgress"] > div {
  background: var(--border-subtle) !important;
  border-radius: 4px !important;
}

[data-testid="stProgress"] > div > div {
  background: linear-gradient(90deg, var(--blue-bright), var(--green-bright)) !important;
  border-radius: 4px !important;
  transition: width 600ms ease !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* DIVIDER                                                                        */
/* ─────────────────────────────────────────────────────────────────────────── */
hr {
  border: none !important;
  border-top: 1px solid var(--border-subtle) !important;
  margin: 1.5rem 0 !important;
}

/* ─────────────────────────────────────────────────────────────────────────── */
/* CUSTOM COMPONENTS (injected via st.markdown)                                   */
/* ─────────────────────────────────────────────────────────────────────────── */

/* Page Header */
.agel-page-header {
  background: linear-gradient(135deg, #0D1B2A 0%, #1B3A5C 100%);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-lg);
  padding: 24px 32px;
  margin-bottom: 24px;
  position: relative;
  overflow: hidden;
  box-shadow: var(--shadow-md);
}
.agel-page-header::after {
  content: '';
  position: absolute;
  top: -50%; right: -10%;
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(88,166,255,0.06) 0%, transparent 70%);
  border-radius: 50%;
}
.agel-page-header h1 {
  font-size: 1.6rem !important;
  font-weight: 700 !important;
  color: #F0F6FC !important;
  margin: 0 0 4px 0 !important;
}
.agel-page-header .subtitle {
  color: #8B949E;
  font-size: 0.875rem;
  margin: 0;
}
.agel-page-header .badges {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  flex-wrap: wrap;
}

/* Badge / Chip */
.agel-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.agel-badge.green  { background: rgba(35, 134, 54, 0.2);  color: #3FB950; border: 1px solid rgba(35,134,54,0.4); }
.agel-badge.blue   { background: rgba(88, 166, 255, 0.15); color: #58A6FF; border: 1px solid rgba(88,166,255,0.3); }
.agel-badge.orange { background: rgba(230,126,34,0.15);    color: #F39C12; border: 1px solid rgba(230,126,34,0.3); }
.agel-badge.red    { background: rgba(218,54,51,0.15);     color: #F85149; border: 1px solid rgba(218,54,51,0.3); }
.agel-badge.grey   { background: rgba(139,148,158,0.15);   color: #8B949E; border: 1px solid rgba(139,148,158,0.3); }

/* Mission Control Banner */
.mission-control-banner {
  background: linear-gradient(135deg, #0D1B2A 0%, #0A1628 50%, #0D2137 100%);
  border: 1px solid #1B3A5C;
  border-radius: var(--radius-xl);
  padding: 28px 36px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 28px;
  box-shadow: var(--shadow-lg), 0 0 60px rgba(27,58,92,0.3);
  position: relative;
  overflow: hidden;
}
.mission-control-banner::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(90deg, #1B3A5C, #2C5F8A, #27AE60, #E67E22);
}
.mission-control-banner .platform-name {
  font-size: 1.5rem;
  font-weight: 800;
  color: #F0F6FC;
  letter-spacing: -0.03em;
}
.mission-control-banner .platform-sub {
  font-size: 0.8rem;
  color: #8B949E;
  margin-top: 3px;
}
.mission-control-banner .status-grid {
  display: flex;
  gap: 20px;
  align-items: center;
}
.mission-control-banner .status-item {
  text-align: center;
}
.mission-control-banner .status-item .label {
  font-size: 0.68rem;
  color: #8B949E;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}
.mission-control-banner .status-item .value {
  font-size: 0.9rem;
  color: #F0F6FC;
  font-weight: 600;
  margin-top: 2px;
}

/* KPI Card */
.agel-kpi-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
  position: relative;
  overflow: hidden;
  transition: all var(--transition-md);
  box-shadow: var(--shadow-sm);
  cursor: default;
  height: 100%;
}
.agel-kpi-card:hover {
  border-color: var(--blue-bright);
  box-shadow: var(--shadow-md), var(--shadow-glow-blue);
  transform: translateY(-2px);
}
.agel-kpi-card .card-icon {
  font-size: 1.4rem;
  margin-bottom: 8px;
  display: block;
}
.agel-kpi-card .card-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 8px;
}
.agel-kpi-card .card-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1;
  margin-bottom: 6px;
  font-family: var(--font-sans);
}
.agel-kpi-card .card-value.small { font-size: 1.2rem; }
.agel-kpi-card .card-delta-pos { font-size: 0.78rem; color: #3FB950; font-weight: 600; }
.agel-kpi-card .card-delta-neg { font-size: 0.78rem; color: #F85149; font-weight: 600; }
.agel-kpi-card .card-delta-neu { font-size: 0.78rem; color: #8B949E; font-weight: 600; }
.agel-kpi-card .card-status {
  position: absolute; top: 14px; right: 14px;
  font-size: 0.7rem; font-weight: 600;
  padding: 3px 8px; border-radius: 12px;
}
.agel-kpi-card .card-status.ok { background: rgba(35,134,54,0.2); color: #3FB950; }
.agel-kpi-card .card-status.warn { background: rgba(158,106,3,0.2); color: #D29922; }
.agel-kpi-card .card-status.crit { background: rgba(218,54,51,0.2); color: #F85149; }
.agel-kpi-card .card-ts {
  font-size: 0.68rem; color: var(--text-muted);
  margin-top: 8px; display: block;
}
.agel-kpi-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}
.agel-kpi-card.blue::before   { background: linear-gradient(90deg, #1B3A5C, #58A6FF); }
.agel-kpi-card.green::before  { background: linear-gradient(90deg, #1A7A4A, #27AE60); }
.agel-kpi-card.orange::before { background: linear-gradient(90deg, #C05810, #F39C12); }
.agel-kpi-card.red::before    { background: linear-gradient(90deg, #7A0020, #DA3633); }

/* Alert Banners */
.agel-alert {
  border-radius: var(--radius-md);
  padding: 14px 18px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 0.875rem;
  border: 1px solid;
}
.agel-alert .alert-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 1px; }
.agel-alert .alert-title { font-weight: 700; margin-bottom: 2px; }
.agel-alert .alert-body  { color: var(--text-secondary); }
.agel-alert.success { background: rgba(35,134,54,0.1);  border-color: rgba(35,134,54,0.35);  color: #3FB950; }
.agel-alert.warning { background: rgba(158,106,3,0.1);  border-color: rgba(158,106,3,0.35);  color: #D29922; }
.agel-alert.error   { background: rgba(218,54,51,0.1);  border-color: rgba(218,54,51,0.35);  color: #F85149; }
.agel-alert.info    { background: rgba(88,166,255,0.08); border-color: rgba(88,166,255,0.25); color: #58A6FF; }

/* Section Header */
.agel-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 24px 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-subtle);
}
.agel-section-header .icon { font-size: 1.2rem; }
.agel-section-header h3 {
  font-size: 1rem !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  margin: 0 !important;
}
.agel-section-header .desc {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-left: auto;
}

/* Status Dot */
.status-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  animation: pulse-dot 2s infinite;
}
.status-dot.green  { background: #3FB950; box-shadow: 0 0 6px rgba(63,185,80,0.6); }
.status-dot.yellow { background: #D29922; box-shadow: 0 0 6px rgba(210,153,34,0.6); }
.status-dot.red    { background: #F85149; box-shadow: 0 0 6px rgba(248,81,73,0.6); }
.status-dot.grey   { background: #8B949E; }

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* Empty State */
.agel-empty-state {
  text-align: center;
  padding: 60px 20px;
  background: var(--bg-card);
  border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-lg);
}
.agel-empty-state .icon { font-size: 3rem; margin-bottom: 12px; display: block; opacity: 0.4; }
.agel-empty-state .title { font-size: 1rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.agel-empty-state .desc  { font-size: 0.8rem; color: var(--text-muted); }

/* Footer */
.agel-footer {
  text-align: center;
  padding: 16px;
  border-top: 1px solid var(--border-subtle);
  margin-top: 40px;
  font-size: 0.75rem;
  color: var(--text-muted);
  font-family: var(--font-sans);
}

/* Chat Messages */
.chat-user-msg {
  background: linear-gradient(135deg, #1B3A5C 0%, #2C5F8A 100%);
  color: #F0F6FC;
  border-radius: 18px 18px 4px 18px;
  padding: 12px 18px;
  margin: 10px 0 10px 20%;
  font-size: 0.875rem;
  line-height: 1.5;
  box-shadow: var(--shadow-sm);
  position: relative;
}
.chat-user-msg .msg-label {
  font-size: 0.68rem; color: rgba(240,246,252,0.6);
  font-weight: 600; letter-spacing: 0.06em;
  margin-bottom: 5px; text-transform: uppercase;
}
.chat-ai-msg {
  background: var(--bg-card);
  color: var(--text-secondary);
  border-radius: 18px 18px 18px 4px;
  padding: 16px 20px;
  margin: 10px 20% 10px 0;
  font-size: 0.875rem;
  line-height: 1.6;
  border: 1px solid var(--border-subtle);
  border-left: 3px solid var(--orange-primary);
  box-shadow: var(--shadow-sm);
}
.chat-ai-msg .msg-label {
  font-size: 0.68rem; color: var(--text-muted);
  font-weight: 600; letter-spacing: 0.06em;
  margin-bottom: 8px; text-transform: uppercase;
}
.chat-ai-msg h4 { color: var(--text-primary) !important; font-size: 0.9rem !important; margin: 10px 0 4px 0 !important; }
.chat-ai-msg ul  { margin: 4px 0 8px 0; padding-left: 18px; }
.chat-ai-msg li  { color: var(--text-secondary); margin-bottom: 3px; }

/* Sidebar version info */
.sidebar-version {
  padding: 10px 0;
  border-top: 1px solid var(--border-subtle);
  text-align: center;
}
.sidebar-version .ver { font-size: 0.75rem; color: var(--text-muted); }
.sidebar-version .usr { font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); }

/* Inference Chain Banner */
.inference-chain {
  background: linear-gradient(90deg, #0D1B2A, #1B3A5C);
  border: 1px solid #2C5F8A;
  border-radius: var(--radius-md);
  padding: 14px 20px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 20px;
  font-size: 0.875rem;
}
.inference-chain .step { color: #C9D1D9; }
.inference-chain .arrow { color: #F39C12; font-weight: 700; }
.inference-chain .result { color: #58A6FF; font-weight: 700; }
.inference-chain .label { color: #F39C12; font-weight: 700; margin-right: 4px; }

/* Monitoring Health Card */
.health-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-md);
}
.health-card:hover {
  border-color: var(--border-accent);
  box-shadow: var(--shadow-md);
}
.health-card .hc-icon  { font-size: 1.6rem; flex-shrink: 0; }
.health-card .hc-name  { font-weight: 600; font-size: 0.875rem; color: var(--text-primary); }
.health-card .hc-desc  { font-size: 0.775rem; color: var(--text-muted); margin-top: 2px; }
.health-card .hc-badge { margin-left: auto; flex-shrink: 0; }

/* Scrollbar styling */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg-primary); }
::-webkit-scrollbar-thumb { background: var(--border-subtle); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--blue-bright); }

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
  gap: 4px;
  background: var(--bg-secondary);
  padding: 4px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
}
.stTabs [data-baseweb="tab"] {
  border-radius: var(--radius-sm) !important;
  font-size: 0.85rem !important;
  font-weight: 500 !important;
  color: var(--text-muted) !important;
  padding: 8px 16px !important;
  border: none !important;
  background: transparent !important;
  transition: all var(--transition-fast) !important;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
  background: var(--bg-card) !important;
  color: var(--text-primary) !important;
  box-shadow: var(--shadow-sm) !important;
}
.stTabs [data-baseweb="tab-panel"] {
  padding: 16px 0 0 0 !important;
}

</style>
"""


def inject_design_system():
    """Call this once at the top of app.py to inject the full design system."""
    import streamlit as st
    st.markdown(ENTERPRISE_CSS, unsafe_allow_html=True)
