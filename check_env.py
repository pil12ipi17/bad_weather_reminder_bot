import os
import requests
from dotenv import load_dotenv

# Загружаем .env
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path)

OWM_KEY = os.getenv("WEATHER_API_KEY")
print("Используемый ключ OWM:", OWM_KEY)

# Проверим прямой запрос
city = "Moscow"
url = "http://api.openweathermap.org/data/2.5/weather"
params = {"q": city, "appid": OWM_KEY, "units": "metric"}

try:
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    print(f"Погода в {city}: {data['weather'][0]['main']}, температура {data['main']['temp']}°C")
except requests.exceptions.HTTPError as e:
    print("Ошибка HTTP:", e)
except Exception as e:
    print("Другая ошибка:", e)
