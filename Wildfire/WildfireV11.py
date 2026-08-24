import os
import webbrowser
import folium
import requests
from geopy.geocoders import Nominatim
import matplotlib.pyplot as plt
from folium.plugins import HeatMap
import csv

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

        self.geolocator = Nominatim(
            user_agent="orbis_app"
        )

        self.map_object = folium.Map(
            location=[20, 0],
            zoom_start=2,
            tiles="OpenStreetMap"
        )

        folium.TileLayer(
    tiles="Esri WorldImagery",
    attr="Esri"
).add_to(self.map_object)

        folium.TileLayer(
            tiles="CartoDB Positron"
        ).add_to(self.map_object)

        folium.LayerControl().add_to(self.map_object)

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
    def add_nasa_hotspots(self):

        url = (
        "https://firms.modaps.eosdis.nasa.gov/"
        )

        print(
        "🚀 NASA hotspot integration coming soon."
        )
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
        confidence = 100

        if rain_7d == 0:
            confidence -= 10

        if rain_7d > 100:
            confidence -= 5

        if abs(location.latitude) > 60:
            confidence -= 10

        if wind > 40:   
            confidence -= 5

        confidence = max(confidence, 0)
        print(f"Location          {location.address}")
        print(f"Coordinates       {location.latitude:.2f}, {location.longitude:.2f}")
        print(f"Temperature       {temp} °C")
        print(f"Relative humidity {humidity} %")
        print(f"Wind              {wind} km/h")
        print(f"Precipitation     {precip} mm")
        print(f"7-day rainfall    {rain_7d:.1f} mm")
        print(f"Climate zone      {zone}")
        print(f"Land cover        {cover}")
        print(f"Confidence level   {confidence}%")
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
        heat_data = []
        risk_rankings = []
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
            climate_zone = Environment.get_climate_zone(lat)
            land_cover, veg_score = Environment.get_land_cover(lat)

            if mode == "1":
                temp, hum, wind, precip = curr["temperature_2m"], curr["relative_humidity_2m"], curr["wind_speed_10m"], curr["precipitation"]
                mode_name = "CURRENT CONDITIONS"
            elif mode == "2":
                temp, hum, wind, precip = daily["temperature_2m_max"][0], daily["relative_humidity_2m_min"][0], daily["wind_speed_10m_max"][0], daily["precipitation_sum"][0]
                mode_name = "TODAY'S PEAK CONDITIONS"
            else:
                weekly_risk_scores = []
                

                for i in range(7):

                    temp_score = WildfireRiskCalculator.calc_temp_score(
                    daily["temperature_2m_max"][i]
                    )

                    humidity_score = (
                    WildfireRiskCalculator.calc_humidity_score(
                    daily["relative_humidity_2m_min"][i]
                    )
                    )

                    wind_score = WildfireRiskCalculator.calc_wind_score(
                    daily["wind_speed_10m_max"][i]
                    )

                    fuel_score = WildfireRiskCalculator.calc_fuel_dryness(
                    rain_7d
                    )

                    daily_risk = (
                    temp_score * 0.25
                    + humidity_score * 0.20
                    + wind_score * 0.15
                    + fuel_score * 0.20
                    + veg_score * 0.20
                    )

                    weekly_risk_scores.append(daily_risk)

                highest_day = weekly_risk_scores.index(
                max(weekly_risk_scores)
                )
                days = [
                "Today",
                "Tomorrow",
                "Day 3",
                "Day 4",
                "Day 5",
                "Day 6",
                "Day 7"
                ]

                plt.figure()

                plt.plot(
                days,
                weekly_risk_scores,
                marker="o"
                )

                plt.ylabel("Wildfire Risk")

                plt.title(
                f"7-Day Wildfire Outlook: {name}"
                )

                plt.ylim(0, 100)

                plt.savefig(f"{name}_graph.png")
                plt.close()
                graph_file = os.path.realpath(f"{name}_graph.png")

                graphs_folder = "graphs"

                os.makedirs(
    graphs_folder,
    exist_ok=True
)

                filename = os.path.join(
                    graphs_folder,
                    f"{name}_graph.png"
                )

                plt.savefig(filename)
                temp, hum, wind, precip = daily["temperature_2m_max"][highest_day], daily["relative_humidity_2m_min"][highest_day], daily["wind_speed_10m_max"][highest_day], daily["precipitation_sum"][highest_day]
                mode_name = "SEVEN-DAY OUTLOOK"

            
            scores, risk_level, alert, color = WildfireRiskCalculator.evaluate(temp, hum, wind, rain_7d, veg_score)
            risk_rankings.append(
            (
            name,
            scores["overall"]
            )
)
            # Terminal output
            self.display_report(location, mode_name, temp, hum, wind, precip, rain_7d, climate_zone, land_cover, scores, risk_level, alert)
            heat_data.append(
    [
        lat,
        lon,
        scores["overall"] / 100
    ]
)
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
            folium.CircleMarker(
            [lat, lon],
            radius=scores["overall"] / 5,
            popup=popup_text, color=color, fill=True, fill_opacity=0.8).add_to(self.map_object)
        
    
        HeatMap(
        heat_data
        ).add_to(self.map_object)

        if heat_data:

            coordinates = [
            [point[0], point[1]]
            for point in heat_data
            ]

            self.map_object.fit_bounds(
                coordinates
    )
        risk_rankings.sort(
        key=lambda x: x[1],
        reverse=True
        )

        print()
        print("==============================")
        print("     GLOBAL RISK RANKINGS")
        print("==============================")

        for position, (place, score) in enumerate(
            risk_rankings,
            start=1
        ):

            print(
        f"{position}. {place} - {score:.0f}/100"
    )
        self.map_object.save("OrbisMap.html")
        
        webbrowser.open(
                "file://" + os.path.realpath("OrbisMap.html")
        )
        print()

        print("⚠️ Experimental index. Not an official")
        print("wildfire warning.")


if __name__ == "__main__":
    OrbisWildfireApp().run()