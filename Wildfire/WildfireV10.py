import os
import webbrowser
import folium
import requests
from geopy.geocoders import Nominatim

# -----------------------------
# CLIMATE & ENVIRONMENT MODEL
# -----------------------------
class Environment:
    """Handles classification of climate zones and vegetation profiles."""
    CLIMATE_ZONES = [
        (66, "POLAR"),
        (55, "BOREAL"),
        (35, "TEMPERATE"),
        (20, "SUBTROPICAL"),
        (0, "TROPICAL")
    ]
    
    LAND_COVERS = [
        (15, "TROPICAL VEGETATION", 90),
        (30, "DESERT OR DRYLAND", 25),
        (45, "MEDITERRANEAN VEGETATION", 85),
        (60, "TEMPERATE FOREST", 70),
        (66, "BOREAL FOREST", 80),
        (180, "POLAR ENVIRONMENT", 10)
    ]

class Environment:
    """Handles classification of climate zones and vegetation profiles."""

    CLIMATE_ZONES = [
        (66, "POLAR"),
        (55, "BOREAL"),
        (35, "TEMPERATE"),
        (20, "SUBTROPICAL"),
        (0, "TROPICAL")
    ]

    LAND_COVERS = [
        (15, "TROPICAL VEGETATION", 90),
        (30, "DESERT OR DRYLAND", 25),
        (45, "MEDITERRANEAN VEGETATION", 85),
        (60, "TEMPERATE FOREST", 70),
        (66, "BOREAL FOREST", 80),
        (180, "POLAR ENVIRONMENT", 10)
    ]

    @classmethod
    def get_climate_zone(cls, latitude):

        abs_lat = abs(latitude)

        if abs_lat >= 66:
            return "POLAR"

        elif abs_lat >= 55:
            return "BOREAL"

        elif abs_lat >= 35:
            return "TEMPERATE"

        elif abs_lat >= 20:
            return "SUBTROPICAL"

        else:
            return "TROPICAL"

    @classmethod
    def get_land_cover(cls, latitude):

        abs_lat = abs(latitude)

        return next(
            (cover, veg_score)
            for threshold, cover, veg_score in cls.LAND_COVERS
            if abs_lat < threshold
        )
    
    @classmethod
    def get_land_cover(cls, latitude):
        abs_lat = abs(latitude)
        return next((cover, veg_score) for threshold, cover, veg_score in cls.LAND_COVERS if abs_lat < threshold)


# -----------------------------
# WILDFIRE RISK CALCULATOR
# -----------------------------
class WildfireRiskCalculator:
    """Calculates risk components and overall wildfire scores."""
    
    RISK_LEVELS = [
        (20, "VERY LOW", "🟢 NO ACTIVE ALERT", "green"),
        (40, "LOW", "🟡 CONDITIONS STABLE", "lightgreen"),
        (60, "MODERATE", "🟠 MONITOR CONDITIONS", "orange"),
        (80, "HIGH", "🔴 HIGH WILDFIRE ALERT", "red"),
        (101, "EXTREME", "🚨 EXTREME WILDFIRE ALERT", "darkred")
    ]

    @staticmethod
    def calc_temp_score(temp):
        return min(max((temp - 15) * 4, 0), 100)

    @staticmethod
    def calc_humidity_score(humidity):
        return min(max((50 - humidity) * 2, 0), 100)

    @staticmethod
    def calc_wind_score(wind):
        return min(wind * 4, 100)

    @staticmethod
    def calc_fuel_dryness(rainfall_7_day):
        if rainfall_7_day == 0: return 100
        elif rainfall_7_day < 5: return 80
        elif rainfall_7_day < 15: return 60
        elif rainfall_7_day < 30: return 40
        elif rainfall_7_day < 50: return 20
        return 0

    @classmethod
    def evaluate(cls, temp, humidity, wind, rainfall_7d, veg_score):
        t_score = cls.calc_temp_score(temp)
        h_score = cls.calc_humidity_score(humidity)
        w_score = cls.calc_wind_score(wind)
        f_score = cls.calc_fuel_dryness(rainfall_7d)
        spread_score = (
        w_score * 0.6
        + veg_score * 0.4
        )

        overall_score = (
            t_score * 0.25 +
            h_score * 0.20 +
            w_score * 0.15 +
            f_score * 0.20 +
            veg_score * 0.20
        )

        level, alert, color = next(data[1:] for data in cls.RISK_LEVELS if overall_score < data[0])
        
        scores = {
        "temperature": t_score,
        "humidity": h_score,
        "wind": w_score,
        "fuel": f_score,
        "vegetation": veg_score,
        "spread": spread_score,
        "overall": overall_score
        }
        
        return scores, level, alert, color


# -----------------------------
# MAIN APP ORCHESTRATOR
# -----------------------------
class OrbisWildfireApp:
    def __init__(self):
        self.geolocator = Nominatim(user_agent="orbis_app")
        self.map_object = folium.Map(location=[20, 0], zoom_start=2)
        self.api_url = "https://api.open-meteo.com/v1/forecast"

    def fetch_weather(self, lat, lon):
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "daily": "temperature_2m_max,relative_humidity_2m_min,wind_speed_10m_max,precipitation_sum",
            "forecast_days": 7
        }
        res = requests.get(self.api_url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()

    def get_user_locations(self):
        locations = []
        while True:
            place = input("Enter a location: ").strip()
            if place:
                locations.append(place)
            if input("Add another location? (y/n): ").lower() != "y":
                break
        return locations

    def display_report(self, location, mode_name, temp, humidity, wind, precip, rain_7d, 
                       zone, cover, scores, risk_level, alert):
        print("\n================================")
        print("        ORBIS WILDFIRE")
        print(f"        {mode_name}")
        print("================================")
        print(f"Location          {location.address}")
        print(f"Coordinates       {location.latitude:.2f}, {location.longitude:.2f}")
        print(f"Temperature       {temp} °C")
        print(f"Relative humidity {humidity} %")
        print(f"Wind              {wind} km/h")
        print(f"Precipitation     {precip} mm")
        print(f"7-day rainfall    {rain_7d:.1f} mm")
        print(f"Climate zone      {zone}")
        print(f"Land cover        {cover}")
        print(
        f"Fire spread potential {scores['spread']:.0f}/100"
)
        print("\n--------------------------------")
        print("   WILDFIRE CONDITIONS INDEX")
        print("--------------------------------")
        print(f"              {scores['overall']:.0f} / 100")
        print(f"              {risk_level}")
        print(f"\n{alert}\n")
        print("--------------------------------")
        print("         RISK BREAKDOWN")
        print("--------------------------------")
        print(f"Temperature          {scores['temperature']:.0f}/100")
        print(f"Atmospheric dryness  {scores['humidity']:.0f}/100")
        print(f"Wind                 {scores['wind']:.0f}/100")
        print(f"Fuel dryness         {scores['fuel']:.0f}/100")
        print(f"Vegetation           {scores['vegetation']:.0f}/100")
        print(
            f"Fire spread potential {scores['spread']:.0f}/100")
        print("--------------------------------\n")

    

    def run(self):
        locations = self.get_user_locations()
        if not locations:
            return print("❌ No locations provided.")

        print("\nSelect a mode:\n1. Current conditions\n2. Today's peak conditions\n3. Seven-day outlook")
        mode = input("Choose a mode (1, 2 or 3): ").strip()
        
        for name in locations:
            location = self.geolocator.geocode(name)
            if not location:
                print(f"❌ Could not locate: {name}")
                continue

            lat, lon = location.latitude, location.longitude
            weather = self.fetch_weather(lat, lon)
            curr, daily = weather["current"], weather["daily"]
            rain_7d = sum(daily["precipitation_sum"])

            if mode == "1":
                temp, hum, wind, precip = curr["temperature_2m"], curr["relative_humidity_2m"], curr["wind_speed_10m"], curr["precipitation"]
                mode_name = "CURRENT CONDITIONS"
            elif mode == "2":
                temp, hum, wind, precip = daily["temperature_2m_max"][0], daily["relative_humidity_2m_min"][0], daily["wind_speed_10m_max"][0], daily["precipitation_sum"][0]
                mode_name = "TODAY'S PEAK CONDITIONS"
            else:
                highest_day = max(range(7), key=lambda i: (
                    WildfireRiskCalculator.calc_temp_score(daily["temperature_2m_max"][i]) * 0.3 +
                    WildfireRiskCalculator.calc_humidity_score(daily["relative_humidity_2m_min"][i]) * 0.25 +
                    WildfireRiskCalculator.calc_wind_score(daily["wind_speed_10m_max"][i]) * 0.2
                ))
                temp, hum, wind, precip = daily["temperature_2m_max"][highest_day], daily["relative_humidity_2m_min"][highest_day], daily["wind_speed_10m_max"][highest_day], daily["precipitation_sum"][highest_day]
                mode_name = "SEVEN-DAY OUTLOOK"

            climate_zone = Environment.get_climate_zone(lat)
            land_cover, veg_score = Environment.get_land_cover(lat)
            scores, risk_level, alert, color = WildfireRiskCalculator.evaluate(temp, hum, wind, rain_7d, veg_score)

            # Terminal output
            self.display_report(location, mode_name, temp, hum, wind, precip, rain_7d, climate_zone, land_cover, scores, risk_level, alert)

            # Map marker
        popup_text = f"""
            🔥 {name}

            🔥 Risk: {scores['overall']:.0f}/100

            🚨 Alert: {risk_level}

            🌡️ Temperature: {temp:.1f}°C

            💧 Humidity: {hum:.0f}%

            💨 Wind: {wind:.1f} km/h

            🌧️ Rainfall: {rain_7d:.1f} mm

            🌿 Vegetation: {land_cover}

            🔥 Spread potential: {scores['spread']:.0f}/100

            🌍 Climate zone: {climate_zone}
            """
        folium.Marker([lat, lon], popup=popup_text, icon=folium.Icon(color=color)).add_to(self.map_object)

        self.map_object.save("OrbisMap.html")

        webbrowser.open(
             "file://" + os.path.realpath("OrbisMap.html")
)
        print()

        print("⚠️ Experimental index. Not an official")
        print("wildfire warning.")


if __name__ == "__main__":
    OrbisWildfireApp().run()
