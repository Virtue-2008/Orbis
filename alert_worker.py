import os
import time
import json
import math
import requests
from datetime import datetime

# Optional SDK Imports
try:
    from twilio.rest import Client as TwilioClient
except ImportError:
    TwilioClient = None

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail
except ImportError:
    SendGridAPIClient = None


# -------------------------------------------------------------------
# 1. CONFIGURATION & MONITORED SECTORS
# -------------------------------------------------------------------
CHECK_INTERVAL_SECONDS = 900  # Runs check every 15 minutes
SECTOR_FILE = "watched_sectors.json"

DEFAULT_SECTORS = [
    {
        "name": "Malibu, California",
        "lat": 34.0259,
        "lon": -118.7798,
        "contact_phone": "+15550192834",
        "contact_email": "chief@malibufire.gov"
    },
    {
        "name": "Boulder, Colorado",
        "lat": 40.0150,
        "lon": -105.2705,
        "contact_phone": "+15550192835",
        "contact_email": "eoc@bouldercounty.gov"
    }
]

def load_monitored_sectors():
    if not os.path.exists(SECTOR_FILE):
        with open(SECTOR_FILE, "w") as f:
            json.dump(DEFAULT_SECTORS, f, indent=2)
        return DEFAULT_SECTORS
    with open(SECTOR_FILE, "r") as f:
        return json.load(f)


# -------------------------------------------------------------------
# 2. LIGHTWEIGHT PHYSICS ENGINE
# -------------------------------------------------------------------
def calculate_fosberg_fwi(temp_c: float, humidity_pct: float, wind_kmh: float) -> float:
    """Fosberg Fire Weather Index (FFWI) scale (0-100)."""
    temp_f = (temp_c * 9/5) + 32
    rh = max(1.0, min(100.0, humidity_pct))
    
    if rh < 10:
        emc = 0.03229 + 0.281073 * rh - 0.000578 * rh * temp_f
    elif rh < 50:
        emc = 2.22749 + 0.160107 * rh - 0.014784 * temp_f
    else:
        emc = 21.0606 + 0.005565 * (rh**2) - 0.00035 * rh * temp_f - 0.483199 * rh
        
    m = max(0.1, emc / 30.0)
    eta = 1 - 2*m + 1.5*(m**2) - 0.5*(m**3)
    wind_mph = wind_kmh * 0.621371
    u = max(1.0, wind_mph)
    
    ffwi = (1.0 / 30.0) * eta * math.sqrt(1 + (u**2)) * 100.0
    return min(100.0, max(0.0, ffwi))

def fetch_current_telemetry(lat: float, lon: float):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
    try:
        res = requests.get(url, timeout=10).json()
        return res.get("current", {})
    except Exception as e:
        print(f"[ERROR] Failed to fetch telemetry for [{lat}, {lon}]: {e}")
        return None


# -------------------------------------------------------------------
# 3. NOTIFICATION DISPATCHERS
# -------------------------------------------------------------------
def send_sms_alert(to_number: str, message_body: str):
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    
    if not (account_sid and auth_token and from_number and TwilioClient):
        print(f"[SIMULATED SMS to {to_number}]: {message_body}")
        return

    try:
        client = TwilioClient(account_sid, auth_token)
        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_number
        )
        print(f"[SMS DISPATCHED] SID: {message.sid}")
    except Exception as e:
        print(f"[ERROR] Twilio dispatch failed: {e}")

def send_email_alert(to_email: str, sector_name: str, ffwi: float, temp: float, wind: float):
    api_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("ALERT_EMAIL_FROM", "alerts@orbis-wildfire.gov")
    
    subject = f"🚨 RED FLAG ALERT: {sector_name} (FFWI Index: {ffwi:.0f}/100)"
    content = f"""
    <h2>ORBIS Wildfire Automated Threat Notification</h2>
    <p><b>Target Sector:</b> {sector_name}</p>
    <p><b>Fosberg Fire Weather Index:</b> <span style="color:red;"><b>{ffwi:.0f} / 100</b></span></p>
    <hr>
    <h4>Observed Weather Conditions:</h4>
    <ul>
      <li><b>Temperature:</b> {temp:.1f} °C</li>
      <li><b>Wind Speed:</b> {wind:.1f} km/h</li>
    </ul>
    <p><i>Access the ORBIS Dashboard for real-time GIS infrastructure threat corridors and PDF exports.</i></p>
    """
    
    if not (api_key and SendGridAPIClient):
        print(f"[SIMULATED EMAIL to {to_email}]: Subject: {subject}")
        return

    try:
        sg = SendGridAPIClient(api_key)
        message = Mail(from_email=from_email, to_emails=to_email, subject=subject, html_content=content)
        response = sg.send(message)
        print(f"[EMAIL DISPATCHED] Status Code: {response.status_code}")
    except Exception as e:
        print(f"[ERROR] SendGrid dispatch failed: {e}")


# -------------------------------------------------------------------
# 4. CRON EXECUTION LOOP
# -------------------------------------------------------------------
def run_alert_cycle():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting sector threat evaluation...")
    sectors = load_monitored_sectors()
    
    for sector in sectors:
        name = sector["name"]
        lat, lon = sector["lat"], sector["lon"]
        
        telemetry = fetch_current_telemetry(lat, lon)
        if not telemetry:
            continue
            
        temp = telemetry.get("temperature_2m", 0.0)
        rh = telemetry.get("relative_humidity_2m", 50.0)
        wind = telemetry.get("wind_speed_10m", 0.0)
        
        ffwi = calculate_fosberg_fwi(temp, rh, wind)
        print(f" -> Sector: {name:<20} | FFWI: {ffwi:.1f}/100 | Temp: {temp}°C | Wind: {wind}km/h")
        
        # Critical Threat Threshold Evaluation
        if ffwi >= 50.0:
            alert_msg = f"ALERT: Red Flag Wildfire Threat for {name}. Fosberg FWI reached {ffwi:.0f}/100. Temp: {temp}°C, Wind: {wind}km/h. Check ORBIS dashboard immediately."
            
            send_sms_alert(sector["contact_phone"], alert_msg)
            send_email_alert(sector["contact_email"], name, ffwi, temp, wind)

if __name__ == "__main__":
    print("======================================================")
    print(" ORBIS BACKGROUND ALERT WORKER STARTED")
    print("======================================================")
    while True:
        run_alert_cycle()
        time.sleep(CHECK_INTERVAL_SECONDS)