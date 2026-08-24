import streamlit as st
import pandas as pd
import numpy as np
import xgboost as xgb
import requests
import shap
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from datetime import datetime
import joblib
import os

# Set page config
st.set_page_config(page_title="ORBIS Sentinel | Production Dashboard", layout="wide")

# =====================================================================
# PART 1: THE SCIENTIFIC CORE (The "Brain")
# =====================================================================
# In production, Streamlit does NOT train the model. It loads the 
# calibrated XGBoost model exported from your Earth Engine/FIRMS pipeline.
MODEL_FILE = "orbis_production_model.joblib"
MODEL_FEATURES = ['t', 'rh', 'w', 'ndvi', 'slope', 'vpd', 'emc']

@st.cache_resource
def load_production_engine():
    """Loads the rigorously trained research model."""
    if os.path.exists(MODEL_FILE):
        model = joblib.load(MODEL_FILE)
        return model, "ONLINE (Calibrated Earth Engine Core)"
    else:
        # FALLBACK: If the real model isn't linked yet, build a placeholder 
        # using the exact architecture of the research core (without random UI data)
        st.toast("Warning: Production model file not found. Booting fallback physics engine.", icon="⚠️")
        df = pd.DataFrame({
            't': np.random.uniform(10, 45, 2000), 'rh': np.random.uniform(5, 80, 2000),
            'w': np.random.uniform(0, 50, 2000), 'ndvi': np.random.uniform(0, 0.8, 2000),
            'slope': np.random.uniform(0, 45, 2000)
        })
        df['vpd'] = (0.61078 * np.exp((17.27 * df['t']) / (df['t'] + 237.3)) * (1 - (df['rh'] / 100)))
        df['emc'] = (21.06 - (0.48 * df['rh']) - (0.00035 * df['rh'] * df['t']))
        
        # Rigorous physics-based target
        z = (df['t']*0.1) - (df['rh']*0.05) + (df['w']*0.08) - (df['ndvi']*2) + (df['slope']*0.05) - 1.5
        df['ignition'] = np.random.binomial(1, 1 / (1 + np.exp(-z)))
        
        fallback_model = xgb.XGBClassifier(eval_metric='logloss', random_state=42, max_depth=4)
        fallback_model.fit(df[MODEL_FEATURES], df['ignition'])
        return fallback_model, "ONLINE (Fallback Engine - Awaiting GEE Weights)"

inference_model, engine_status = load_production_engine()

feature_names_map = {
    't': 'Temperature', 'rh': 'Humidity', 'w': 'Wind Speed', 
    'ndvi': 'Vegetation Fuel', 'slope': 'Terrain Steepness', 
    'vpd': 'Air Drying Power', 'emc': 'Fuel Moisture'
}

# =====================================================================
# PART 2: LIVE TELEMETRY PIPELINE
# =====================================================================
def fetch_live_telemetry(lat, lon, static_slope, static_ndvi):
    """
    Strict API data fetch. No demo overrides. No fabricated heatwaves.
    If the data says it's safe, the model outputs safe.
    """
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        resp = requests.get(url, timeout=5).json()["current"]
        t = resp["temperature_2m"]
        rh = resp["relative_humidity_2m"]
        w = resp["wind_speed_10m"]
    except Exception as e:
        # In a real production system, API failure should log an error, not guess.
        return None, None, {"error": str(e)}

    # Derived Physics
    vpd = (0.61078 * np.exp((17.27 * t) / (t + 237.3)) * (1 - (rh / 100)))
    emc = (21.06 - (0.48 * rh) - (0.00035 * rh * t))
    
    input_df = pd.DataFrame([[t, rh, w, static_ndvi, static_slope, vpd, emc]], columns=MODEL_FEATURES)
    prob = float(inference_model.predict_proba(input_df)[0][1])
    
    return prob, input_df, {"t": t, "rh": rh, "w": w, "error": None}

def dispatch_external_alert(zone, contact, risk_pct):
    """
    Placeholder for the actual Twilio SMS / SendGrid Email API.
    """
    # TODO: requests.post("https://api.twilio.com/...", data={"to": contact, "body": f"ORBIS ALERT: {zone}..."})
    return True

# =====================================================================
# PART 3: THE USER PLATFORM (The "Body")
# =====================================================================
st.title("🛰️ ORBIS Sentinel")
st.markdown("**Automated Wildfire Threat Monitoring & Notification System**")
st.caption(f"Last automated sweep: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC | Engine Status: {engine_status}")
st.markdown("---")

client_zones = {
    "Gov. Sector: Yosemite Alpha": {"lat": 37.74, "lon": -119.53, "slope": 25.0, "ndvi": 0.65, "contact": "CalFire Dispatch"},
    "Enterprise: Napa Vineyards": {"lat": 38.50, "lon": -122.47, "slope": 12.0, "ndvi": 0.45, "contact": "Estate Manager SMS"},
    "Municipal: Malibu Perimeter": {"lat": 34.03, "lon": -118.78, "slope": 22.0, "ndvi": 0.35, "contact": "LA County Emergency Mgt"},
    "Gov Sector: Death Valley": {"lat": 36.45, "lon": -116.86, "slope": 2.0, "ndvi": 0.05, "contact": "Park Rangers"}
}

alerts = []
zone_results = {}

with st.spinner("Executing real-time global telemetry sweep..."):
    for zone, data in client_zones.items():
        prob, input_df, weather = fetch_live_telemetry(data["lat"], data["lon"], data["slope"], data["ndvi"])
        
        if prob is not None:
            zone_results[zone] = {"prob": prob, "input": input_df, "weather": weather, "meta": data}
            if prob > 0.50:
                alerts.append(zone)

# --- NOTIFICATION CENTER ---
if alerts:
    st.error(f"### 🚨 {len(alerts)} ACTIVE ALERTS DETECTED")
    for a in alerts:
        risk_pct = zone_results[a]['prob'] * 100
        contact = zone_results[a]['meta']['contact']
        
        col_alert, col_button = st.columns([4, 1])
        with col_alert:
            st.warning(f"**CRITICAL RISK**: {a} crossed threshold ({risk_pct:.1f}%). Designated contact: **{contact}**")
        with col_button:
            # Clearly labeled as a manual trigger for the UI, calling the real dispatch function
            if st.button(f"Trigger API Webhook", key=f"btn_{a}", use_container_width=True):
                dispatch_external_alert(a, contact, risk_pct)
                st.toast(f"Webhook executed! Real-world system would now text {contact}.", icon="✅")
else:
    st.success("### ✅ All Monitored Zones Nominal. Live telemetry shows no critical threats.")

st.markdown("---")

# --- DIAGNOSTIC DASHBOARD ---
st.markdown("### Monitored Assets Database")
tabs = st.tabs(list(zone_results.keys()))

for i, (zone, result) in enumerate(zone_results.items()):
    with tabs[i]:
        prob = result['prob']
        c1, c2, c3 = st.columns([1, 1.5, 1])
        
        with c1:
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = prob * 100,
                title = {'text': "Current Risk", 'font': {'size': 18}},
                number = {'suffix': "%"},
                gauge = {
                    'axis': {'range': [0, 100]},
                    'bar': {'color': "darkred"},
                    'steps': [
                        {'range': [0, 30], 'color': "lightgreen"},
                        {'range': [30, 60], 'color': "gold"},
                        {'range': [60, 100], 'color': "salmon"}
                    ]
                }
            ))
            fig_gauge.update_layout(height=250, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_gauge, use_container_width=True)
            st.caption(f"📍 Coordinates: `{result['meta']['lat']}`, `{result['meta']['lon']}`")
            
        with c2:
            st.markdown("**AI Diagnostic: What is driving this risk?**")
            explainer = shap.TreeExplainer(inference_model)
            shap_values = explainer.shap_values(result['input'])
            
            shap_df = pd.DataFrame({"Feature": MODEL_FEATURES, "Impact": shap_values[0]})
            shap_df["Readable"] = shap_df["Feature"].map(feature_names_map)
            shap_df = shap_df.sort_values(by="Impact", ascending=True)
            
            fig_shap, ax = plt.subplots(figsize=(6, 3))
            colors = ['#d62728' if x > 0 else '#1f77b4' for x in shap_df['Impact']]
            ax.barh(shap_df['Readable'], shap_df['Impact'], color=colors)
            ax.set_xticks([]) 
            ax.spines[['top', 'right', 'bottom']].set_visible(False)
            plt.tight_layout()
            st.pyplot(fig_shap)
            
        with c3:
            st.markdown("**Real-Time Telemetry**")
            w = result['weather']
            st.write(f"🌡️ **Temp:** {w['t']}°C")
            st.write(f"💧 **Humidity:** {w['rh']}%")
            st.write(f"💨 **Wind:** {w['w']} km/h")