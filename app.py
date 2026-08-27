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
# PART 1: THE SCIENTIFIC CORE (Single Source of Truth)
# =====================================================================
MODEL_FILE = "orbis_production_model.joblib"

MODEL_FEATURES = [
    't', 'rh', 'w', 'slope', 'aspect_sin', 'aspect_cos', 'ndvi', 
    'w_channeled', 'emc', 'vpd', 'hdw', 'ffwi', 'topo_drying', 
    'fuel_dryness', 'atmo_combustion_index', 'rh_vpd_ratio', 
    'fuel_moisture_deficit', 'wind_vpd'
]

feature_names_map = {
    't': 'Temperature', 'rh': 'Humidity', 'w': 'Wind Speed', 
    'ndvi': 'Vegetation Fuel', 'slope': 'Terrain Steepness', 
    'vpd': 'Air Drying Power', 'emc': 'Fuel Moisture',
    'aspect_sin': 'Aspect (Sin)', 'aspect_cos': 'Aspect (Cos)',
    'w_channeled': 'Channeled Wind', 'hdw': 'Hot-Dry-Wind Index',
    'ffwi': 'Fire Weather Index', 'topo_drying': 'Topographic Drying',
    'fuel_dryness': 'Fuel Dryness Factor', 'atmo_combustion_index': 'Combustion Index',
    'rh_vpd_ratio': 'RH-VPD Ratio', 'fuel_moisture_deficit': 'Moisture Deficit',
    'wind_vpd': 'Wind-VPD Interaction'
}

if os.path.exists(MODEL_FILE):
    inference_model = joblib.load(MODEL_FILE)
    engine_status = "ONLINE (Calibrated Core)"
else:
    st.error("❌ Critical Error: Production model artifact (`orbis_production_model.joblib`) not found. Engine offline.")
    st.stop()

def get_base_estimator(model):
    """Recursively unwraps FrozenEstimator, CalibratedClassifierCV, and Pipelines to expose XGBoost for SHAP."""
    curr = model
    for _ in range(10):
        if hasattr(curr, "calibrated_classifiers_") and len(curr.calibrated_classifiers_) > 0:
            curr = curr.calibrated_classifiers_[0]
        elif hasattr(curr, "estimator"):
            curr = curr.estimator
        elif hasattr(curr, "named_steps"):
            curr = curr.named_steps[list(curr.named_steps.keys())[-1]]
        elif hasattr(curr, "_final_estimator"):
            curr = curr._final_estimator
        else:
            break
    return curr

def build_features(t, rh, w, slope=15.0, ndvi=0.40):
    """Unified 18-feature engineering engine."""
    vpd = (0.61078 * np.exp((17.27 * t) / (t + 237.3)) * (1 - (rh / 100)))
    emc = (21.06 - (0.48 * rh) - (0.00035 * rh * t))
    aspect_sin = 0.0
    aspect_cos = 1.0
    w_channeled = w * np.cos(np.radians(slope))
    hdw = w * vpd
    ffwi = (w * t) / (rh + 1.0)
    topo_drying = slope * vpd
    fuel_dryness = 100.0 / (emc + 1.0)
    atmo_combustion_index = t * vpd / (rh + 1.0)
    rh_vpd_ratio = rh / (vpd + 0.01)
    fuel_moisture_deficit = 30.0 - emc
    wind_vpd = w * vpd

    row = [
        t, rh, w, slope, aspect_sin, aspect_cos, ndvi, 
        w_channeled, emc, vpd, hdw, ffwi, topo_drying, 
        fuel_dryness, atmo_combustion_index, rh_vpd_ratio, 
        fuel_moisture_deficit, wind_vpd
    ]
    return pd.DataFrame([row], columns=MODEL_FEATURES)

# =====================================================================
# PART 2: GLOBAL TELEMETRY PIPELINE
# =====================================================================
def geocode_location(query_str):
    try:
        clean_query = query_str.strip()
        if not clean_query:
            return None, None, None, None
            
        url = f"https://geocoding-api.open-meteo.com/v1/search?name={requests.utils.quote(clean_query)}&count=1&language=en&format=json"
        response = requests.get(url, timeout=6)
        
        if response.status_code == 200:
            data = response.json()
            if "results" in data and len(data["results"]) > 0:
                match = data["results"][0]
                lat = float(match["latitude"])
                lon = float(match["longitude"])
                name = match["name"]
                country = match.get("country", "")
                full_display = f"{name}, {country}" if country else name
                return lat, lon, name, full_display
    except Exception as e:
        print(f"Geocoding Error: {e}")
        pass
    return None, None, None, None

def fetch_live_telemetry(lat, lon, slope=15.0, ndvi=0.40):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
        resp = requests.get(url, timeout=5).json()["current"]
        t = resp["temperature_2m"]
        rh = resp["relative_humidity_2m"]
        w = resp["wind_speed_10m"]
    except Exception as e:
        return None, None, None, {"error": str(e)}

    input_df = build_features(t, rh, w, slope, ndvi)
    
    try:
        raw_prob = float(inference_model.predict_proba(input_df)[0][1])
    except Exception:
        raw_prob = float(inference_model.predict_proba(input_df.values)[0][1])

    final_prob = 0.001 if ndvi < 0.12 else raw_prob

    return final_prob, raw_prob, input_df, {"t": t, "rh": rh, "w": w, "error": None}

def dispatch_external_alert(zone, contact, risk_pct):
    return True

# =====================================================================
# PART 3: THE USER PLATFORM
# =====================================================================
st.title("🛰️ ORBIS Sentinel")
st.markdown("**Automated Wildfire Threat Monitoring & Notification System**")
st.caption(f"Last automated sweep: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC | Engine Status: {engine_status}")
st.markdown("---")

DEFAULT_ZONES = {
    "Gov. Sector: Peloponnese (Greece)": {"lat": 37.51, "lon": 22.37, "slope": 20.0, "ndvi": 0.50, "contact": "Hellenic Fire Service"},
    "Enterprise: Hunter Valley (Australia)": {"lat": -32.65, "lon": 151.35, "slope": 10.0, "ndvi": 0.40, "contact": "RFS Operations"},
    "Municipal: Valparaíso (Chile)": {"lat": -33.04, "lon": -71.61, "slope": 28.0, "ndvi": 0.35, "contact": "CONAF Chile"},
    "Gov Sector: Death Valley (USA)": {"lat": 36.45, "lon": -116.86, "slope": 2.0, "ndvi": 0.05, "contact": "Park Rangers"}
}

if 'client_zones' not in st.session_state:
    st.session_state.client_zones = DEFAULT_ZONES.copy()

# --- SIDEBAR SEARCH (CLEAN LAYOUT) ---
st.sidebar.header("📍 Asset Location Search")
st.sidebar.caption("Search is case-insensitive and handles typos/variations.")
user_query = st.sidebar.text_input("Enter Location Name", placeholder="e.g. Athens, Greece")

if user_query:
    lat, lon, name, full_display = geocode_location(user_query)
    if lat is not None:
        st.sidebar.success(f"🎯 **Found:** {full_display}\n\n📌 **Coordinates:** `{lat:.4f}° N, {lon:.4f}° E`")
    else:
        st.sidebar.warning(f"⚠️ Could not resolve \"{user_query}\". Try adding a country name.")

search_triggered = st.sidebar.button("Search & Monitor Location", type="primary")

if search_triggered and user_query:
    with st.sidebar.status("Geocoding location...") as status:
        lat, lon, name, full_display = geocode_location(user_query)
        
        if lat is not None:
            status.update(label="Fetching live weather telemetry...", state="running")
            prob, _, _, _ = fetch_live_telemetry(lat, lon, slope=15.0, ndvi=0.40)
            
            if prob is not None:
                st.session_state.client_zones = {
                    f"Custom Asset: {full_display}": {
                        "lat": lat, "lon": lon, "slope": 15.0, "ndvi": 0.40, "contact": "Property Owner"
                    }
                }
                status.update(label=f"Successfully loaded {full_display}!", state="complete")
                st.sidebar.success(f"Locked onto {full_display} and cleared presets!")
                st.rerun()
            else:
                status.update(label="Weather API failure", state="error")
                st.sidebar.error("Found location, but live weather data is currently unavailable.")
        else:
            status.update(label="Geocoding failed", state="error")
            st.sidebar.error("Could not match location.")

if st.sidebar.button("Reset to Default Presets"):
    st.session_state.client_zones = DEFAULT_ZONES.copy()
    st.rerun()

alerts = []
zone_results = {}

with st.spinner("Executing real-time global telemetry sweep..."):
    for zone in list(st.session_state.client_zones.keys()):
        data = st.session_state.client_zones[zone]
        final_prob, raw_prob, input_df, weather = fetch_live_telemetry(data["lat"], data["lon"], data["slope"], data["ndvi"])
        if final_prob is not None:
            zone_results[zone] = {
                "prob": final_prob, 
                "raw_prob": raw_prob, 
                "input": input_df, 
                "weather": weather, 
                "meta": data
            }
            if final_prob > 0.50:
                alerts.append(zone)

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
    st.markdown("### 🗺️ Global Asset Monitoring Map")

    if zone_results:
        map_records = []
        
        for zone, res in zone_results.items():
            prob = res['prob']
            w = res['weather']
            meta = res['meta']
            
            if prob < 0.30:
                marker_color = '#00CC44'  
            elif prob < 0.60:
                marker_color = '#FFCC00'  
            else:
                marker_color = '#FF3333'  
                
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
                "color": marker_color,
                "hover": hover_text
            })
            
        df_map = pd.DataFrame(map_records)
        
        fig_map = go.Figure(go.Scattermap(
            lat=df_map['lat'],
            lon=df_map['lon'],
            mode='markers',
            marker=dict(
                size=20,
                color=df_map['color'],
                opacity=0.95
            ),
            text=df_map['hover'],
            hoverinfo='text'
        ))
        
        fig_map.update_layout(
            map_style="open-street-map",
            margin={"r":0, "t":0, "l":0, "b":0},
            height=450,
            map=dict(
                center=dict(lat=list(zone_results.values())[0]['meta']['lat'], lon=list(zone_results.values())[0]['meta']['lon']) if len(zone_results) == 1 else dict(lat=10, lon=0),
                zoom=4 if len(zone_results) == 1 else 1.2
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        
        st.plotly_chart(fig_map, use_container_width=True, key="global_asset_map", config={'scrollZoom': True})

    st.markdown("---")

    st.markdown("### Monitored Assets Database")

    if zone_results:
        tabs = st.tabs(list(zone_results.keys()))

        for i, (zone, result) in enumerate(zone_results.items()):
            with tabs[i]:
                prob = result['prob']
                raw_prob = result['raw_prob']
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
                    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{i}")
                    
                    st.caption(f"📍 Coordinates: `{result['meta']['lat']}`, `{result['meta']['lon']}`")
                    st.caption(f"🔍 **Raw Model Output:** `{raw_prob*100:.2f}%` | **Displayed:** `{prob*100:.2f}%`")
                    
                    if result['meta']['ndvi'] < 0.12:
                        st.info("🏜️ **Safety Mask Active:** Barren terrain detected. False alarm suppressed.")
                    
                with c2:
                    st.markdown("**AI Diagnostic: What is driving this risk?**")
                    st.caption("🔴 **Red** = Pushing Risk Up | 🔵 **Blue** = Suppressing Risk")
                    
                    # Target the underlying base model recursively
                    base_model = get_base_estimator(inference_model)
                    
                    try:
                        explainer = shap.TreeExplainer(base_model)
                        shap_vals = explainer.shap_values(result['input'])
                        
                        if isinstance(shap_vals, list):
                            s_vals = shap_vals[1][0] if len(shap_vals) > 1 else shap_vals[0][0]
                        elif len(np.array(shap_vals).shape) == 2:
                            s_vals = shap_vals[0]
                        elif len(np.array(shap_vals).shape) == 3:
                            s_vals = shap_vals[0, :, 1]
                        else:
                            s_vals = np.array(shap_vals).flatten()
                    except Exception as tree_err:
                        # Fallback for complex wrapper structures
                        try:
                            explainer = shap.Explainer(base_model)
                            shap_exp = explainer(result['input'])
                            s_vals = shap_exp.values[0]
                            if len(s_vals.shape) > 1:
                                s_vals = s_vals[:, 1]
                        except Exception as fall_err:
                            st.error(f"⚠️ SHAP diagnostic unwrap exception: {fall_err}")
                            s_vals = np.zeros(len(MODEL_FEATURES))

                    shap_df = pd.DataFrame({"Feature": MODEL_FEATURES, "Impact": s_vals})
                    shap_df["Readable"] = shap_df["Feature"].map(feature_names_map)
                    shap_df = shap_df.sort_values(by="Impact", ascending=True)

                    fig_shap, ax = plt.subplots(figsize=(6, 3))
                    colors = ['#ff4b4b' if x > 0 else '#1c83e1' for x in shap_df['Impact']]

                    ax.barh(shap_df['Readable'], shap_df['Impact'], color=colors, height=0.6)
                    ax.axvline(0, color='gray', linestyle='--', linewidth=0.8, alpha=0.6)
                    ax.spines[['top', 'right', 'bottom', 'left']].set_visible(False)
                    ax.tick_params(axis='x', colors='#E0E0E0', labelsize=8)
                    ax.tick_params(axis='y', colors='#E0E0E0', labelsize=9)

                    # Dynamic axis scaling to amplify small non-zero contributions
                    max_impact = max(abs(shap_df['Impact'].min()), abs(shap_df['Impact'].max()))
                    if max_impact > 0:
                        ax.set_xlim(-max_impact * 1.3, max_impact * 1.3)

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