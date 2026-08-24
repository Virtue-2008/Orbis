import requests
from geopy.geocoders import Nominatim

# -----------------------------
# ORBIS WILDFIRE V0.2
# -----------------------------

geolocator = Nominatim(user_agent="orbis")

location_name = input("Enter a location: ")

location = geolocator.geocode(location_name)

if location is None:
    print("❌ Location not found.")
    quit()

latitude = location.latitude
longitude = location.longitude

url = "https://api.open-meteo.com/v1/forecast"

parameters = {
    "latitude": latitude,
    "longitude": longitude,
    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation"
}

response = requests.get(url, params=parameters)
weather = response.json()

current = weather["current"]

temperature = current["temperature_2m"]
humidity = current["relative_humidity_2m"]
wind = current["wind_speed_10m"]
precipitation = current["precipitation"]


# -----------------------------
# CALCULATE INDIVIDUAL SCORES
# -----------------------------

temperature_score = min(max((temperature - 15) * 4, 0), 100)

humidity_score = min(max((50 - humidity) * 2, 0), 100)

wind_score = min(wind * 4, 100)


# -----------------------------
# COMBINE THE SCORES
# -----------------------------

wildfire_score = (
    temperature_score * 0.4
    + humidity_score * 0.4
    + wind_score * 0.2
)


# -----------------------------
# DETERMINE RISK LEVEL
# -----------------------------

if wildfire_score < 20:
    risk_level = "VERY LOW"

elif wildfire_score < 40:
    risk_level = "LOW"

elif wildfire_score < 60:
    risk_level = "MODERATE"

elif wildfire_score < 80:
    risk_level = "HIGH"

else:
    risk_level = "EXTREME"

# -----------------------------
# DISPLAY ORBIS
# -----------------------------

print("================================")
print("        ORBIS WILDFIRE")
print("================================")
print()

print(f"Location: {location.address}")
print(f"Coordinates       {latitude:.2f}, {longitude:.2f}")
print()

print(f"Temperature       {temperature} °C")
print(f"Relative humidity {humidity} %")
print(f"Wind              {wind} km/h")
print(f"Precipitation     {precipitation} mm")

print()
print("--------------------------------")
print("   WILDFIRE CONDITIONS INDEX")
print("--------------------------------")
print()

print(f"             {wildfire_score:.0f} / 100")
print()
print(f"             {risk_level}")

print()
print("--------------------------------")
print("        FACTOR IMPACT")
print("--------------------------------")
print()

# Temperature
if temperature_score >= 75:
    print("🌡️ Temperature")
    print(f"{temperature_score:.0f}/100 — HIGH INCREASE")
elif temperature_score >= 50:
    print("🌡️ Temperature")
    print(f"{temperature_score:.0f}/100 — INCREASING")
elif temperature_score > 0:
    print("🌡️ Temperature")
    print(f"{temperature_score:.0f}/100 — LOW")
else:
    print("🌡️ Temperature")
    print("MINIMAL IMPACT")

print()

# Atmospheric dryness

if humidity_score == 0:
    print("💧 Atmospheric dryness")
    print("LOW — MOIST AIR IS LIMITING CONDITIONS")

elif humidity_score >= 75:
    print("💧 Atmospheric dryness")
    print(f"{humidity_score:.0f}/100 — EXTREME")

elif humidity_score >= 50:
    print("💧 Atmospheric dryness")
    print(f"{humidity_score:.0f}/100 — HIGH")

elif humidity_score >= 25:
    print("💧 Atmospheric dryness")
    print(f"{humidity_score:.0f}/100 — ELEVATED")

else:
    print("💧 Atmospheric dryness")
    print(f"{humidity_score:.0f}/100 — MINIMAL")

print()

# Wind
if wind_score >= 75:
    print("💨 Wind")
    print(f"{wind_score:.0f}/100 — HIGH")
elif wind_score >= 50:
    print("💨 Wind")
    print(f"{wind_score:.0f}/100 — MODERATE")
elif wind_score > 0:
    print("💨 Wind")
    print(f"{wind_score:.0f}/100 — LOW")
else:
    print("💨 Wind")
    print("MINIMAL IMPACT")

print()

# Precipitation
if precipitation == 0:
    print("🌧️ Precipitation")
    print("NO CURRENT PRECIPITATION")
else:
    print("🌧️ Precipitation")
    print(f"{precipitation} mm CURRENTLY RECORDED")

print()
print("--------------------------------")
print("             WHY?")
print("--------------------------------")
print()

if temperature_score >= 50:
    print("Warm temperatures are increasing")
    print("fire-conducive conditions.")
else:
    print("Temperature is currently having")
    print("a minor influence on conditions.")

print()

if humidity_score == 0:
   print("Moist air is currently limiting")
   print("fire-conducive conditions.")
else:
    print("Dry air is increasing")
    print("fire-conducive conditions.")

print()

if wind_score >= 50:
    print("Strong winds are increasing the")
    print("potential for fire spread.")
else:
    print("Relatively low wind is contributing")
    print("little to potential fire spread.")

print()

if precipitation == 0:
    print("No precipitation is currently")
    print("being recorded.")
else:
    print("Precipitation is currently being")
    print("recorded.")

print()
print("--------------------------------")
print("       ORBIS ASSESSMENT")
print("--------------------------------")
print()

print(f"Conditions are currently {risk_level}.")

print()

print("--------------------------------")
print("         ORBIS INSIGHT")
print("--------------------------------")
print()

if max(temperature_score, humidity_score, wind_score) == temperature_score:
    print("• Temperature is currently the dominant")
    print("  environmental factor.")

elif max(temperature_score, humidity_score, wind_score) == humidity_score:
    print("• Atmospheric dryness is currently the")
    print("  dominant environmental factor.")

else:
    print("• Wind is currently the dominant")
    print("  environmental factor.")

print()

if humidity_score == 0:
    print("• Moist air is helping to limit")
    print("  fire-conducive conditions.")

elif humidity_score >= 25:
    print("• Dry atmospheric conditions are")
    print("  increasing fire-conducive conditions.")

print()

if wind_score < 30:
    print("• Relatively light winds are currently")
    print("  limiting potential fire spread.")

elif wind_score >= 50:
    print("• Stronger winds may increase the")
    print("  potential for fire spread.")

print()

if precipitation == 0:
    print("• No precipitation is currently")
    print("  being recorded.")

else:
    print("• Current precipitation may be")
    print("  helping to suppress fire activity.")

print()

if risk_level == "VERY LOW":
    print("Overall, conditions currently appear")
    print("very stable.")

elif risk_level == "LOW":
    print("Overall, conditions currently appear")
    print("relatively stable.")

elif risk_level == "MODERATE":
    print("Overall, conditions warrant monitoring.")

elif risk_level == "HIGH":
    print("Overall, conditions are becoming")
    print("increasingly favourable for wildfire activity.")

else:
    print("Overall, conditions are highly favourable")
    print("for wildfire activity.")

print()

print("⚠️ Experimental index. Not an official")
print("wildfire warning.")