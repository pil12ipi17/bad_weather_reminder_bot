import os
import requests
from dotenv import load_dotenv

load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")


def get_weather(lat, lon):
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"lat": lat, "lon": lon, "appid": WEATHER_API_KEY, "units": "metric"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    temp = data["main"]["temp"]
    temp_min = data["main"]["temp_min"]
    temp_max = data["main"]["temp_max"]
    condition = data["weather"][0]["main"]

    condition_lower = condition.lower()
    if "rain" in condition_lower or "drizzle" in condition_lower:
        precipitation_type = "rain"
    elif "snow" in condition_lower:
        precipitation_type = "snow"
    else:
        precipitation_type = "none"

    return {
        "temp": temp,
        "temp_min": temp_min,
        "temp_max": temp_max,
        "condition": condition,
        "precipitation_type": precipitation_type,
        "pop": 0,
        "raw_json": str(data)
    }
