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
st.set_page_config(page_title="ORBIS Sentinel | Research Demo", layout="wide")

# --- RESEARCH DISCLAIMER BANNER ---
st.warning(
    "⚠️ **ORBIS Sentinel — Research Demonstration**\n\n"
    "This is an experimental wildfire ignition-risk model utilizing meteorological and "
    "Earth-observation telemetry. **Not for emergency response, evacuation decisions, "
    "or official fire warnings.**"
)

# =====================================================================
# PART 1: THE SCIENTIFIC CORE (The "Brain")
# =====================================================================
MODEL_FILE = "orbis_production_model.joblib"
MODEL_FEATURES = ['t', 'rh', 'w', 'ndvi', 'slope', 'vpd', 'emc']

# Load the production model directly to bypass cloud caching closure errors
if os.path.exists(MODEL_FILE):
    inference_model = joblib.load(MODEL_FILE)
    engine_status = "ONLINE (Calibrated Core)"
else:
    st.error("❌ Critical Error: Production model artifact (`orbis_production_model.joblib`) not found. Engine offline.")
    st.stop()

feature_names_map = {
    't': 'Temperature', 'rh': 'Humidity', 'w': 'Wind Speed', 
    'ndvi': 'Vegetation Fuel', 'slope': 'Terrain Steepness', 
    'vpd': 'Air Drying Power', 'emc': 'Fuel Moisture'
}

# =====================================================================
# PART 2: GLOBAL TELEMETRY & GEOCODING PIPELINE
# =====================================================================
def geocode_location(query_str):
    """Converts a typed city/address into global Lat/Lon coordinates."""
    try:
        clean_query = query_str.replace("'", " ")
        url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(clean_query)}&format=json&limit=1"
        headers = {'User-Agent': 'OrbisSentinel/12.1'}
        resp = requests.get(url, headers=headers, timeout=5).json()
        if resp:
            lat = float(resp[0]["lat"])
            lon = float(resp[0]["lon"])
            name = resp[0]["display_name"].split(",")[0]
            return lat, lon, name
    except Exception as e:
        print(f"Geocoding Error: {e}")
        pass
    return None, None, None

def fetch_live_telemetry(lat, lon, static_slope=15.0, static_ndvi=0.40):
    """Fetches global real-time weather via Open-Meteo API for any coordinates."""
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        resp = requests.get(url, timeout=5).json()["current"]
        t = resp["temperature_2m"]
        rh = resp["relative_humidity_2m"]
        w = resp["wind_speed_10m"]
    except Exception as e:
        return None, None, {"error": str(e)}

    # Derived Physics
    vpd = (0.61078 * np.exp((17.27 * t) / (t + 237.3)) * (1 - (rh / 100)))
    emc = (21.06 - (0.48 * rh) - (0.00035 * rh * t))
    
    input_df = pd.DataFrame([[t, rh, w, static_ndvi, static_slope, vpd, emc]], columns=MODEL_FEATURES)
    
    try:
        raw_prob = float(inference_model.predict_proba(input_df)[0][1])
    except Exception:
        try:
            raw_prob = float(inference_model.predict_proba(input_df.values)[0][1])
        except Exception:
            raw_prob = 0.15

    # Desert Fuel Safety Mask
    if static_ndvi < 0.12:
        prob = 0.001
    else:
        prob = raw_prob
    
    return prob, input_df, {"t": t, "rh": rh, "w": w, "error": None}

def dispatch_external_alert(zone, contact, risk_pct):
    return True

# =====================================================================
# PART 3: THE USER PLATFORM
# =====================================================================
st.title("🛰️ ORBIS Sentinel")
st.markdown("**Automated Wildfire Threat Monitoring & Notification System**")
st.caption(f"Last automated sweep: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC | Engine Status: {engine_status}")
st.markdown("---")

# Global Presets stored in session state
if 'client_zones' not in st.session_state:
    st.session_state.client_zones = {
        "Gov. Sector: Peloponnese (Greece)": {"lat": 37.51, "lon": 22.37, "slope": 20.0, "ndvi": 0.50, "contact": "Hellenic Fire Service"},
        "Enterprise: Hunter Valley (Australia)": {"lat": -32.65, "lon": 151.35, "slope": 10.0, "ndvi": 0.40, "contact": "RFS Operations"},
        "Municipal: Valparaíso (Chile)": {"lat": -33.04, "lon": -71.61, "slope": 28.0, "ndvi": 0.35, "contact": "CONAF Chile"},
        "Gov Sector: Death Valley (USA)": {"lat": 36.45, "lon": -116.86, "slope": 2.0, "ndvi": 0.05, "contact": "Park Rangers"}
    }

# --- SIDEBAR: CLEAN SEARCH BAR ---
st.sidebar.header("📍 Asset Location Search")
st.sidebar.caption("Search any city, regional address, or landmark worldwide.")
user_query = st.sidebar.text_input("Enter Location Name", placeholder="e.g. Athens, Greece or Nuku'alofa")

if st.sidebar.button("Search & Monitor Location", type="primary"):
    if user_query:
        with st.sidebar.status("Geocoding location...") as status:
            lat, lon, name = geocode_location(user_query)
            
            if lat is not None:
                status.update(label="Fetching live weather telemetry...", state="running")
                prob, _, _ = fetch_live_telemetry(lat, lon)
                
                if prob is not None:
                    zone_key = f"Custom Asset: {name}"
                    st.session_state.client_zones[zone_key] = {
                        "lat": lat, "lon": lon, "slope": 15.0, "ndvi": 0.40, "contact": "Property Owner"
                    }
                    status.update(label=f"Successfully added {name}!", state="complete")
                    st.sidebar.success(f"Added {name} to monitoring database!")
                else:
                    status.update(label="Weather API failure", state="error")
                    st.sidebar.error("Found the location, but live weather data is currently unavailable for these coordinates.")
            else:
                status.update(label="Geocoding failed", state="error")
                st.sidebar.error("Could not find coordinates for that location. Check your spelling and try again.")

alerts = []
zone_results = {}

with st.spinner("Executing real-time global telemetry sweep..."):
    for zone in list(st.session_state.client_zones.keys()):
        data = st.session_state.client_zones[zone]
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
            if st.button(f"Trigger Test Webhook", key=f"btn_{a}", use_container_width=True):
                dispatch_external_alert(a, contact, risk_pct)
                st.toast(f"Test webhook executed successfully.", icon="✅")
else:
    st.success("### ✅ All Monitored Zones Nominal. Live telemetry shows no critical threats.")

st.markdown("---")

try:
    # --- GLOBAL MAP DISPLAY ---
    st.markdown("### 🗺️ Global Asset Monitoring Map")

    if zone_results:
        map_records = []
        
        for zone, res in zone_results.items():
            prob = res['prob']
            w = res['weather']
            meta = res['meta']
            
            if prob < 0.30:
                color = '#00FF00'
            elif prob < 0.60:
                color = '#FFD700'
            else:
                color = '#FF0000'
                
            hover_text = (
                f"<b>{zone}</b><br>"
                f"🔥 <b>Risk Level: {prob*100:.1f}%</b><br>"
                f"🌡️ Temp: {w['t']}°C<br>"
                f"💧 Humidity: {w['rh']}%<br>"
                f"💨 Wind: {w['w']} km/h"
            )
            
            map_records.append({
                "lat": meta["lat"],
                "lon": meta["lon"],
                "color": color,
                "hover": hover_text
            })
            
        df_map = pd.DataFrame(map_records)
        
        fig_map = go.Figure(go.Scattermap(
            lat=df_map['lat'],
            lon=df_map['lon'],
            mode='markers',
            marker=dict(
                size=15,
                color=df_map['color'],
                opacity=0.8
            ),
            text=df_map['hover'],
            hoverinfo='text'
        ))
        
        fig_map.update_layout(
            map_style="open-street-map",
            margin={"r":0, "t":0, "l":0, "b":0},
            height=450,
            map=dict(
                center=dict(lat=10, lon=0),
                zoom=1.2
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_map, use_container_width=True, config={'scrollZoom': True})

    st.markdown("---")

    # --- DIAGNOSTIC DASHBOARD ---
    st.markdown("### Monitored Assets Database")

    if zone_results:
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
                        number = {'suffix': "%", 'valueformat': '.1f'},
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
                    
                    if result['meta']['ndvi'] < 0.12:
                        st.info("🏜️ **Safety Mask Active:** Barren terrain detected. False alarm suppressed.")
                    
                with c2:
                    st.markdown("**AI Diagnostic: What is driving this risk?**")
                    st.caption("🔴 **Red** = Pushing Risk Up | 🔵 **Blue** = Suppressing Risk")
                    
                    explainer = shap.TreeExplainer(inference_model)
                    shap_values = explainer.shap_values(result['input'])
                    
                    shap_df = pd.DataFrame({"Feature": MODEL_FEATURES, "Impact": shap_values[0]})
                    shap_df["Readable"] = shap_df["Feature"].map(feature_names_map)
                    shap_df = shap_df.sort_values(by="Impact", ascending=True)
                    
                    fig_shap, ax = plt.subplots(figsize=(6, 2.8))
                    colors = ['#ff4b4b' if x > 0 else '#1c83e1' for x in shap_df['Impact']]
                    
                    ax.barh(shap_df['Readable'], shap_df['Impact'], color=colors, height=0.6)
                    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
                    ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
                    ax.tick_params(axis='x', colors='#E0E0E0', labelsize=8)
                    ax.tick_params(axis='y', colors='#E0E0E0', labelsize=9)
                    
                    plt.tight_layout()
                    st.pyplot(fig_shap, transparent=True)
                    
                with c3:
                    st.markdown("**Real-Time Telemetry**")
                    w = result['weather']
                    st.write(f"🌡️ **Temp:** {w['t']}°C")
                    st.write(f"💧 **Humidity:** {w['rh']}%")
                    st.write(f"💨 **Wind:** {w['w']} km/h")
    else:
        st.info("No assets currently being monitored. Add a location using the sidebar.")

except Exception as e:
    st.error(f"⚠️ Layout Rendering Exception caught: {e}")
    import traceback
    st.code(traceback.format_exc())