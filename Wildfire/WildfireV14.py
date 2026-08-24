import os
import webbrowser
import folium
import requests
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt
from folium.plugins import HeatMap


# -----------------------------
# CLIMATE & ENVIRONMENT MODEL
# -----------------------------

BIOMES = {
    "TREE COVER": ("FOREST", 90),
    "SHRUBLAND": ("SHRUBLAND", 70),
    "GRASSLAND": ("GRASSLAND", 60),
    "CROPLAND": ("CROPLAND", 50),
    "BUILT-UP": ("URBAN", 20),
    "BARE OR SPARSE VEGETATION": ("DESERT", 5),
    "SNOW AND ICE": ("POLAR", 0),
    "WATER": ("WATER", 0),
    "WETLAND": ("WETLAND", 80),
    "MANGROVE": ("MANGROVE", 95),
    "MOSS AND LICHEN": ("TUNDRA", 15)
}

LAND_COVER_CLASSES = {
    10: ("TREE COVER", 90),
    20: ("SHRUBLAND", 70),
    30: ("GRASSLAND", 60),
    40: ("CROPLAND", 50),
    50: ("BUILT-UP", 20),
    60: ("BARE OR SPARSE VEGETATION", 5),
    70: ("SNOW AND ICE", 0),
    80: ("WATER", 0),
    90: ("WETLAND", 80),
    95: ("MANGROVE", 95),
    100: ("MOSS AND LICHEN", 15)
}
class Environment:
    """Handles classification of climate zones and vegetation profiles."""
    BIOMES = {
    "forest": 90,
    "grassland": 50,
    "savanna": 60,
    "cropland": 40,
    "urban": 10,
    "desert": 5,
    "tundra": 5,
    "polar": 0
}
    @classmethod
    def get_land_cover_from_satellite(cls, latitude, longitude):

        url = (
            "https://api.open-meteo.com/v1/elevation"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
        )

        try:

            response = requests.get(url, timeout=10)

            elevation = response.json()["elevation"][0]

        except Exception:

            return ("UNKNOWN", 50)

        if elevation > 3000:

            return ("MOUNTAIN", 40)

        
    @classmethod
    def get_biome(cls, land_cover):

        return cls.BIOMES.get(
            land_cover,
            ("UNKNOWN", 50)
    )
    
    @classmethod
    def get_climate_zone(cls, latitude):
        abs_lat = abs(latitude)
        if abs_lat >= 66: return "POLAR"
        elif abs_lat >= 55: return "BOREAL"
        elif abs_lat >= 35: return "TEMPERATE"
        elif abs_lat >= 20: return "SUBTROPICAL"
        else: return "TROPICAL"

    @classmethod
    def get_land_cover(cls, latitude):
        abs_lat = abs(latitude)
        return next(
            (cover, veg_score)
            for threshold, cover, veg_score in cls.LAND_COVERS
            if abs_lat < threshold
        )


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
        
        # Fire spread potential requires both wind and vegetation to burn
        spread_score = (w_score * 0.6) * (veg_score / 100)

        # Baseline weather vulnerability score
        weather_vulnerability = (
            t_score * 0.35 +
            h_score * 0.30 +
            w_score * 0.15 +
            f_score * 0.20
        )

        # DESERT FIX: Vegetation acts as a fuel gate.
        # If vegetation score is very low, the overall risk is capped or scaled down dramatically.
        fuel_availability_factor = max(
    veg_score / 100,
    0.05
)

        overall_score = (
        weather_vulnerability
        * fuel_availability_factor
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
        self.geolocator = Nominatim(user_agent="orbis_app_benson")
        self.map_object = folium.Map(
            location=[20, 0],
            zoom_start=2,
            tiles="OpenStreetMap"
        )

        folium.TileLayer(tiles="Esri WorldImagery", attr="Esri").add_to(self.map_object)
        folium.TileLayer(tiles="CartoDB Positron").add_to(self.map_object)

        # Layer group for NASA FIRMS Hotspots
        self.nasa_layer = folium.FeatureGroup(name="NASA Satellite Hotspots (24h)").add_to(self.map_object)
        
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

    def add_nasa_hotspots(self, map_key="YOUR_NASA_MAP_KEY", country_code="USA"):
        """Fetches active satellite detections from NASA FIRMS API."""
        if map_key == "YOUR_NASA_MAP_KEY":
            print("ℹ️ NASA FIRMS API key not provided. Skipping live satellite hotspot overlay.")
            return

        url = f"https://firms.modaps.eosdis.nasa.gov/api/country/csv/{map_key}/VIIRS_NOAA20_NRT/{country_code}/1"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                lines = res.text.strip().split("\n")
                for line in lines[1:100]:  # Cap at 100 markers to prevent map lag
                    parts = line.split(",")
                    if len(parts) >= 3:
                        lat, lon = float(parts[0]), float(parts[1])
                        brightness = parts[2]
                        folium.CircleMarker(
                            location=[lat, lon],
                            radius=3,
                            color="red",
                            fill=True,
                            fill_color="orange",
                            popup=f"🔥 <b>NASA Thermal Detection</b><br>Brightness: {brightness}K"
                        ).add_to(self.nasa_layer)
                print("✅ Added active NASA satellite fire detections to map.")
        except Exception as e:
            print(f"⚠️ NASA FIRMS fetch failed: {e}")

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
        confidence = 100
        if rain_7d == 0: confidence -= 10
        if rain_7d > 100: confidence -= 5
        if abs(location.latitude) > 60: confidence -= 10
        if wind > 40: confidence -= 5
        confidence = max(confidence, 0)

        print("\n================================")
        print("        ORBIS WILDFIRE")
        print(f"        {mode_name}")
        print("================================")
        print(f"Location          {location.address}")
        print(f"Coordinates       {location.latitude:.2f}, {location.longitude:.2f}")
        print(f"Biome             {biome}")
        print(f"Temperature       {temp} °C")
        print(f"Relative humidity {humidity} %")
        print(f"Wind              {wind} km/h")
        print(f"Precipitation     {precip} mm")
        print(f"7-day rainfall    {rain_7d:.1f} mm")
        print(f"Climate zone      {zone}")
        print(f"Land cover        {cover}")
        print(f"Confidence level   {confidence}%")
        print(f"Fire spread potential {scores['spread']:.0f}/100")
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
        print(f"Fire spread potential {scores['spread']:.0f}/100")
        print("--------------------------------\n")

    def run(self):
        heat_data = []
        risk_rankings = []
        locations = self.get_user_locations()
        if not locations:
            print("❌ No locations provided.")
            return

        print("\nSelect a mode:\n1. Current conditions\n2. Today's peak conditions\n3. Seven-day outlook")
        mode = input("Choose a mode (1, 2 or 3): ").strip()
        if mode not in ["1", "2", "3"]:
            mode = "1"

        for name in locations:
            location = self.geolocator.geocode(name)
            if not location:
                print(f"❌ Could not locate: {name}")
                continue

            lat, lon = location.latitude, location.longitude
            weather = self.fetch_weather(lat, lon)
            curr, daily = weather["current"], weather["daily"]
            rain_7d = sum(daily["precipitation_sum"])
            climate_zone = Environment.get_climate_zone(lat)
            land_cover, veg_score = (
    Environment.get_land_cover_from_satellite(
        lat,
        lon
    )
)

            biome, biome_score = (
                Environment.get_biome(
                land_cover
            )
    )

            if mode == "1":
                temp, hum, wind, precip = curr["temperature_2m"], curr["relative_humidity_2m"], curr["wind_speed_10m"], curr["precipitation"]
                mode_name = "CURRENT CONDITIONS"

            elif mode == "2":
                temp, hum, wind, precip = daily["temperature_2m_max"][0], daily["relative_humidity_2m_min"][0], daily["wind_speed_10m_max"][0], daily["precipitation_sum"][0]
                mode_name = "TODAY'S PEAK CONDITIONS"

            else:
                weekly_risk_scores = []
                for i in range(7):
                    t_s = WildfireRiskCalculator.calc_temp_score(daily["temperature_2m_max"][i])
                    h_s = WildfireRiskCalculator.calc_humidity_score(daily["relative_humidity_2m_min"][i])
                    w_s = WildfireRiskCalculator.calc_wind_score(daily["wind_speed_10m_max"][i])
                    f_s = WildfireRiskCalculator.calc_fuel_dryness(rain_7d)

                    daily_risk = (t_s * 0.35 + h_s * 0.30 + w_s * 0.15 + f_s * 0.20) * max(veg_score / 100, 0.05)
                    weekly_risk_scores.append(daily_risk)

                highest_day = weekly_risk_scores.index(max(weekly_risk_scores))
                days = ["Today", "Tomorrow", "Day 3", "Day 4", "Day 5", "Day 6", "Day 7"]

                graphs_folder = "graphs"
                os.makedirs(graphs_folder, exist_ok=True)
                clean_name = name.replace(" ", "_")
                filename = os.path.join(graphs_folder, f"{clean_name}_graph.png")

                plt.figure()
                plt.plot(days, weekly_risk_scores, marker="o")
                plt.ylabel("Wildfire Risk")
                plt.title(f"7-Day Wildfire Outlook: {name}")
                plt.ylim(0, 100)
                plt.savefig(filename)
                plt.close()

                temp, hum, wind, precip = (
                    daily["temperature_2m_max"][highest_day],
                    daily["relative_humidity_2m_min"][highest_day],
                    daily["wind_speed_10m_max"][highest_day],
                    daily["precipitation_sum"][highest_day]
                )
                mode_name = "SEVEN-DAY OUTLOOK"

            scores, risk_level, alert, color = WildfireRiskCalculator.evaluate(temp, hum, wind, rain_7d, veg_score)
            risk_rankings.append((name, scores["overall"]))

            self.display_report(location, mode_name, temp, hum, wind, precip, rain_7d, climate_zone, land_cover, scores, risk_level, alert)
            heat_data.append([lat, lon, scores["overall"] / 100])

            popup_text = f"""
            <b>🔥 Location:</b> {name}<br>
            <b>🔥 Risk Score:</b> {scores['overall']:.0f}/100<br>
            <b>🚨 Alert:</b> {risk_level}<br>
            <b>🌡️ Temp:</b> {temp:.1f}°C<br>
            <b>💧 Humidity:</b> {hum:.0f}%<br>
            <b>💨 Wind:</b> {wind:.1f} km/h<br>
            <b>🌧️ Rainfall:</b> {rain_7d:.1f} mm<br>
            <b>🌿 Land Cover:</b> {land_cover}<br>
            <b>🌍 Climate Zone:</b> {climate_zone}
            """
            
            folium.CircleMarker(
                [lat, lon],
                radius=max(scores["overall"] / 5, 4),
                popup=folium.Popup(popup_text, max_width=300),
                color=color,
                fill=True,
                fill_opacity=0.8
            ).add_to(self.map_object)

        if heat_data:
            HeatMap(heat_data).add_to(self.map_object)
            coordinates = [[point[0], point[1]] for point in heat_data]
            self.map_object.fit_bounds(coordinates)

        # Attempt to pull NASA hotspots if key is configured
        self.add_nasa_hotspots()

        # Add LayerControl at the end so all layers (Esri, NASA, base) can be toggled
        folium.LayerControl().add_to(self.map_object)

        risk_rankings.sort(key=lambda x: x[1], reverse=True)

        print("\n==============================")
        print("     GLOBAL RISK RANKINGS")
        print("==============================")
        for position, (place, score) in enumerate(risk_rankings, start=1):
            print(f"{position}. {place} - {score:.0f}/100")

        map_filename = "OrbisMap.html"
        self.map_object.save(map_filename)
        webbrowser.open("file://" + os.path.realpath(map_filename))

        print("\n⚠️ Experimental index. Not an official wildfire warning.")


if __name__ == "__main__":
    OrbisWildfireApp().run()