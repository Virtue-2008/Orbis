import requests
from geopy.geocoders import Nominatim
import folium
import webbrowser
import os

def get_climate_zone(latitude):

    if abs(latitude) > 66:
        return "POLAR"

    elif abs(latitude) > 55:
        return "BOREAL"

    elif abs(latitude) > 35:
        return "TEMPERATE"

    elif abs(latitude) > 20:
        return "SUBTROPICAL"

    else:
        return "TROPICAL"

def get_land_cover(latitude):

    if abs(latitude) < 15:

        return (
            "TROPICAL VEGETATION",
            90
        )

    elif abs(latitude) < 30:

        return (
            "DESERT OR DRYLAND",
            25
        )

    elif abs(latitude) < 45:

        return (
            "MEDITERRANEAN VEGETATION",
            85
        )

    elif abs(latitude) < 60:

        return (
            "TEMPERATE FOREST",
            70
        )

    elif abs(latitude) < 66:

        return (
            "BOREAL FOREST",
            80
        )

    else:

        return (
            "POLAR ENVIRONMENT",
            10
        )

saved_locations = []

map_object = folium.Map(
    location=[20, 0],
    zoom_start=2
)


hotspots = [
    "Antalya",
    "Malaga",
    "Athens",
    "Los Angeles",
    "Phoenix",
    "Yellowstone",
    "Jakarta",
    "Yakutsk"
]

# -----------------------------
# ORBIS WILDFIRE V4
# -----------------------------

geolocator = Nominatim(user_agent="orbis")

locations = []

while True:

    place = input("Enter a location: ")

    locations.append(place)

    another = input(
        "Add another location? (y/n): "
    ).lower()

    if another != "y":

        break


for location_name in locations:

    location = geolocator.geocode(location_name)

    if location is None:

        continue

    latitude = location.latitude
    longitude = location.longitude

    # Run your wildfire calculations here

print()

print("Select a mode:")
print("1. Current conditions")
print("2. Today's peak conditions")
print("3. Seven-day outlook")

mode = input("Choose a mode (1, 2 or 3): ")

print()

try:

    location = geolocator.geocode(location_name)

except Exception:

    print("❌ Geolocation service unavailable.")
    quit()

if location is None:

    print("❌ Location not found.")
    quit()

if location is None:
    print("❌ Location not found.")
    quit()

latitude = location.latitude
longitude = location.longitude

# -----------------------------
# CLIMATE CLASSIFICATION
# -----------------------------

climate_zone = get_climate_zone(latitude)

land_cover, vegetation_score = get_land_cover(latitude)

# -----------------------------
# ENVIRONMENT CLASSIFICATION
# -----------------------------

location_text = location.address.lower()
if abs(latitude) < 15:

    land_cover = "TROPICAL VEGETATION"
    vegetation_score = 90

elif 15 <= abs(latitude) < 30:

    land_cover = "DESERT OR DRYLAND"
    vegetation_score = 25

elif 30 <= abs(latitude) < 45:

    land_cover = "MEDITERRANEAN VEGETATION"
    vegetation_score = 85

elif 45 <= abs(latitude) < 60:

    land_cover = "TEMPERATE FOREST"
    vegetation_score = 70

elif 60 <= abs(latitude) < 66:

    land_cover = "BOREAL FOREST"
    vegetation_score = 80

else:

    land_cover = "POLAR ENVIRONMENT"
    vegetation_score = 10


url = "https://api.open-meteo.com/v1/forecast"

parameters = {
    "latitude": latitude,

    "longitude": longitude,
    "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
    "daily": "temperature_2m_max,relative_humidity_2m_min,wind_speed_10m_max,precipitation_sum",
    "forecast_days": 7
}

try:

    response = requests.get(
        url,
        params=parameters,
        timeout=10
    )

    response.raise_for_status()

    weather = response.json()

except requests.exceptions.RequestException:

    print("❌ Weather service unavailable.")
    quit()

current = weather["current"]
daily = weather["daily"]
days = [
    "Today",
    "Tomorrow",
    "Day 3",
    "Day 4",
    "Day 5",
    "Day 6",
    "Day 7"
]
rainfall_7_day = sum(daily["precipitation_sum"])

if mode == "1":

    temperature = current["temperature_2m"]
    humidity = current["relative_humidity_2m"]
    wind = current["wind_speed_10m"]
    precipitation = current["precipitation"]

    mode_name = "CURRENT CONDITIONS"

elif mode == "2":

    temperature = daily["temperature_2m_max"][0]
    humidity = daily["relative_humidity_2m_min"][0]
    wind = daily["wind_speed_10m_max"][0]
    precipitation = daily["precipitation_sum"][0]

    mode_name = "TODAY'S PEAK CONDITIONS"

elif mode == "3":

    highest_risk = 0
    highest_day = 0

    for i in range(7):

        temp = daily["temperature_2m_max"][i]
        humidity = daily["relative_humidity_2m_min"][i]
        wind = daily["wind_speed_10m_max"][i]
        rainfall = daily["precipitation_sum"][i]

        # Daily environmental scores

        temp_score = min(max((temp - 15) * 4, 0), 100)

        humidity_score = min(max((50 - humidity) * 2, 0), 100)

        wind_score = min(wind * 4, 100)

        # Daily fuel dryness
        if rainfall == 0:
            daily_fuel_score = 100

        elif rainfall < 2:
            daily_fuel_score = 80

        elif rainfall < 5:
            daily_fuel_score = 60

        elif rainfall < 10:
            daily_fuel_score = 40

        elif rainfall < 20:
            daily_fuel_score = 20

        else:
            daily_fuel_score = 0

        # Daily wildfire score

        daily_risk = (
            temp_score * 0.30
            + humidity_score * 0.25
            + wind_score * 0.20
            + daily_fuel_score * 0.25
        )

        if daily_risk > highest_risk:

            highest_risk = daily_risk
            highest_day = i

    # Use the highest-risk day's conditions

    temperature = daily["temperature_2m_max"][highest_day]
    humidity = daily["relative_humidity_2m_min"][highest_day]
    wind = daily["wind_speed_10m_max"][highest_day]
    precipitation = daily["precipitation_sum"][highest_day]

    mode_name = "SEVEN-DAY OUTLOOK"

else:

    print("❌ Invalid mode selected.")
    quit()

# -----------------------------
# CALCULATE INDIVIDUAL SCORES
# -----------------------------

temperature_score = min(max((temperature - 15) * 4, 0), 100)

humidity_score = min(max((50 - humidity) * 2, 0), 100)

wind_score = min(wind * 4, 100)

# Fuel dryness score

if rainfall_7_day == 0:

    fuel_dryness_score = 100

elif rainfall_7_day < 5:

    fuel_dryness_score = 80

elif rainfall_7_day < 15:

    fuel_dryness_score = 60

elif rainfall_7_day < 30:

    fuel_dryness_score = 40

elif rainfall_7_day < 50:

    fuel_dryness_score = 20

else:

    fuel_dryness_score = 0


# -----------------------------
# COMBINE THE SCORES
# -----------------------------

wildfire_score = (
    temperature_score * 0.25
    + humidity_score * 0.20
    + wind_score * 0.15
    + fuel_dryness_score * 0.20
    + vegetation_score * 0.20
)

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


saved_locations.append(
    {
        "name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "score": wildfire_score,
        "risk": risk_level
    }
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
# ORBIS ALERT SYSTEM
# -----------------------------

if risk_level == "VERY LOW":

    alert_message = "🟢 NO ACTIVE ALERT"

elif risk_level == "LOW":

    alert_message = "🟡 CONDITIONS STABLE"

elif risk_level == "MODERATE":

    alert_message = "🟠 MONITOR CONDITIONS"

elif risk_level == "HIGH":

    alert_message = "🔴 HIGH WILDFIRE ALERT"

else:

    alert_message = "🚨 EXTREME WILDFIRE ALERT"




popup_text = f"""
Location: {location_name}

Risk: {wildfire_score:.0f}/100

Level: {risk_level}

Temperature: {temperature}°C

Humidity: {humidity}%

Wind: {wind} km/h
"""

if risk_level == "VERY LOW":

    marker_colour = "green"

elif risk_level == "LOW":

    marker_colour = "blue"

elif risk_level == "MODERATE":

    marker_colour = "orange"

elif risk_level == "HIGH":

    marker_colour = "red"

else:

    marker_colour = "darkred"

folium.Marker(
    [latitude, longitude],
    popup=popup_text,
    icon=folium.Icon(color=marker_colour)
).add_to(map_object)



for place in hotspots:

    hotspot_location = geolocator.geocode(place)

    if hotspot_location is None:
        continue

    hotspot_latitude = hotspot_location.latitude
    hotspot_longitude = hotspot_location.longitude

    hotspot_weather = requests.get(
        url,
        params={
            "latitude": hotspot_latitude,
            "longitude": hotspot_longitude,
            "current": "temperature_2m"
        }
    ).json()

    hotspot_temperature = (
        hotspot_weather["current"]["temperature_2m"]
    )

    hotspot_score = min(
        max((hotspot_temperature - 15) * 4, 0),
        100
    )

    if hotspot_score >= 80:

        marker_icon = "red"

    elif hotspot_score >= 60:

        marker_icon = "orange"

    elif hotspot_score >= 40:

        marker_icon = "beige"

    else:

        marker_icon = "green"

    folium.Marker(
        [hotspot_latitude, hotspot_longitude],
        popup=f"{place}\nRisk: {hotspot_score:.0f}/100",
        icon=folium.Icon(color=marker_icon)
    ).add_to(map_object)

# -----------------------------
# DISPLAY ORBIS
# -----------------------------

print("================================")
print("        ORBIS WILDFIRE")
print(f"        {mode_name}")
print("================================")
print()

print()

print(f"Location: {location.address}")
print(f"Analysis mode     {mode_name}")
if mode == "3":

    print(f"Highest risk day  {days[highest_day]}")
print(f"Analysis time     {current['time']}")
print(f"Coordinates       {latitude:.2f}, {longitude:.2f}")

print()

print(f"Temperature       {temperature} °C")
print(f"Relative humidity {humidity} %")
print(f"Wind              {wind} km/h")
print(f"Precipitation     {precipitation} mm")
print(f"7-day rainfall    {rainfall_7_day:.1f} mm")
print(f"Climate zone      {climate_zone}")

print()
print("--------------------------------")
print("          ENVIRONMENT")
print("--------------------------------")
print()

print(f"Land cover        {land_cover}")

print()
print("--------------------------------")
print("   WILDFIRE CONDITIONS INDEX")
print("--------------------------------")
print()

print(f"             {wildfire_score:.0f} / 100")
print()
print(f"             {risk_level}")

print()

print(alert_message)

print()
print("--------------------------------")
print("        FACTOR IMPACT")
print("--------------------------------")

print()

print("--------------------------------")
print("        RISK BREAKDOWN")
print("--------------------------------")

print()

print(f"Temperature          {temperature_score:.0f}/100")

print(f"Atmospheric dryness  {humidity_score:.0f}/100")

print(f"Wind                 {wind_score:.0f}/100")

print(f"Fuel dryness         {fuel_dryness_score:.0f}/100")

print(f"Vegetation           {vegetation_score:.0f}/100")

print("--------------------------------")

print(f"Overall risk         {wildfire_score:.0f}/100")

print()

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
    print("NO PRECIPITATION EXPECTED TODAY")

else:
    print("🌧️ Precipitation")
    print(f"{precipitation} mm EXPECTED TODAY")

print()

print("🌿 Fuel dryness")

if fuel_dryness_score >= 75:

    print(f"{fuel_dryness_score:.0f}/100 — HIGH")

elif fuel_dryness_score >= 50:

    print(f"{fuel_dryness_score:.0f}/100 — MODERATE")

else:

    print(f"{fuel_dryness_score:.0f}/100 — LOW")

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

print("--------------------------------")
print("          DATA SOURCES")
print("--------------------------------")
print()

print("Weather data      Open-Meteo")

print()

print()



for place in saved_locations:

    score = place["score"]

    if score >= 80:

        icon_colour = "darkred"

    elif score >= 60:

        icon_colour = "red"

    elif score >= 40:

        icon_colour = "orange"

    elif score >= 20:

        icon_colour = "green"

    else:

        icon_colour = "blue"

    folium.Marker(
        [place["latitude"], place["longitude"]],
        popup=f"{place['name']} ({score:.0f}/100)",
        icon=folium.Icon(color=icon_colour)
    ).add_to(map_object)

map_object.save("OrbisMap.html")

print("🗺️ Interactive map saved as OrbisMap.html")

webbrowser.open(
    "file://" + os.path.realpath("OrbisMap.html")
)

print()

print("⚠️ Experimental index. Not an official")
print("wildfire warning.")