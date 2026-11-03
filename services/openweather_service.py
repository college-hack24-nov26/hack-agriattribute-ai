"""
openweather_service.py - Production-Grade OpenWeatherMap Ingestion Engine
With Automatic API Key Failover across 3 Active Keys & Agronomic Telemetry Processing
Team 15 - Syngenta & ANNAM.AI Hack Core 2026
"""

import requests
from datetime import datetime, timedelta

import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Active OpenWeatherMap Keys (Loaded securely from environment with failover)
def _clean_key(k: str) -> str:
    if not k or not isinstance(k, str):
        return ""
    k = k.strip()
    if k.startswith("your_") or len(k) < 16:
        return ""
    return k

def _get_api_key(name: str) -> str:
    val = os.getenv(name, "")
    if not val:
        try:
            import streamlit as st
            if hasattr(st, "secrets") and name in st.secrets:
                val = str(st.secrets[name])
        except Exception:
            pass
    return _clean_key(val)

k1 = _get_api_key("OPENWEATHER_API_KEY")
k2 = _get_api_key("OPENWEATHER_MAPS_KEY")
k3 = _get_api_key("OPENWEATHER_GOOGLE_KEY")

OPENWEATHER_KEYS = []
if k1:
    OPENWEATHER_KEYS.append({"name": "primary", "key": k1})
if k2 and k2 != k1:
    OPENWEATHER_KEYS.append({"name": "maps", "key": k2})
if k3 and k3 not in (k1, k2):
    OPENWEATHER_KEYS.append({"name": "telemetry", "key": k3})

BASE_WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
BASE_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"

try:
    import streamlit as st
    cache_weather = st.cache_data(ttl=300, show_spinner=False)
except Exception:
    import streamlit as st
def cache_weather(f):
    return st.cache_data(ttl=900)(f)


@cache_weather
def fetch_live_current_weather(lat: float = 30.9010, lon: float = 75.8573) -> dict:
    """
    Fetches real-time current weather with automatic API key rotation.
    Returns temperature, humidity, pressure, wind, clouds, and agronomic stress indicators.
    """
    for key_info in OPENWEATHER_KEYS:
        key_val = key_info["key"]
        key_name = key_info["name"]
        url = f"{BASE_WEATHER_URL}?lat={lat}&lon={lon}&appid={key_val}&units=metric"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                d = res.json()
                temp = d.get("main", {}).get("temp", 28.5)
                humidity = d.get("main", {}).get("humidity", 65)
                pressure = d.get("main", {}).get("pressure", 1012)
                wind_speed = d.get("wind", {}).get("speed", 3.2)
                clouds = d.get("clouds", {}).get("all", 20)
                desc = d.get("weather", [{}])[0].get("description", "clear sky").title()
                location = d.get("name", "Regional Field Station")
                
                # Agronomic Stress Indicators
                is_heat_stress = temp > 35.0
                is_humidity_disease_risk = humidity > 75.0
                is_high_wind = wind_speed > 6.0
                
                return {
                    "status": "LIVE",
                    "telemetry_source": "OpenWeatherMap API (Live Network)",
                    "active_key_name": key_name,
                    "location": location,
                    "temp_c": temp,
                    "feels_like_c": d.get("main", {}).get("feels_like", temp),
                    "humidity_pct": humidity,
                    "pressure_hpa": pressure,
                    "wind_speed_ms": wind_speed,
                    "wind_speed_kmh": round(wind_speed * 3.6, 1),
                    "cloud_cover_pct": clouds,
                    "description": desc,
                    "icon": d.get("weather", [{}])[0].get("icon", "01d"),
                    "agronomic_indicators": {
                        "is_heat_stress": is_heat_stress,
                        "is_humidity_disease_risk": is_humidity_disease_risk,
                        "is_high_wind": is_high_wind,
                        "heat_index_warning": "🔥 High Heat Stress (>35°C)" if is_heat_stress else "✅ Temperature Optimal",
                        "fungal_disease_warning": "⚠️ Fungal Blight Risk (>75% RH)" if is_humidity_disease_risk else "✅ Disease Risk Low"
                    }
                }
        except Exception:
            continue
            
    # Determine realistic regional default by coordinates
    if 18.0 <= lat <= 21.0 and 73.0 <= lon <= 78.0:
        loc_name = "Deccan Plateau Agro-Met Station, Maharashtra"
        f_temp, f_hum, f_wind = 27.8, 68, 11.4
    elif lat >= 28.0 and lon <= 77.0:
        loc_name = "Indo-Gangetic Agro-Met Station, Punjab"
        f_temp, f_hum, f_wind = 29.2, 58, 9.2
    elif 14.0 <= lat <= 19.0 and 76.0 <= lon <= 82.0:
        loc_name = "Krishna-Godavari Agro-Met Station, AP/Telangana"
        f_temp, f_hum, f_wind = 30.5, 64, 12.0
    else:
        loc_name = "Regional IMD Agro-Met Reference Station"
        f_temp, f_hum, f_wind = 28.5, 62, 10.8

    # Fallback response if all API calls fail or keys not provided
    return {
        "status": "DEMO / SYNTHETIC",
        "telemetry_source": "Fallback / Demo Telemetry (Climatological Normal)",
        "active_key_name": "Offline Reference",
        "location": loc_name,
        "temp_c": f_temp,
        "feels_like_c": round(f_temp + 0.8, 1),
        "humidity_pct": f_hum,
        "pressure_hpa": 1011,
        "wind_speed_ms": round(f_wind / 3.6, 1),
        "wind_speed_kmh": f_wind,
        "cloud_cover_pct": 20,
        "description": "Partly Cloudy (Baseline Normal)",
        "icon": "02d",
        "agronomic_indicators": {
            "is_heat_stress": f_temp > 35.0,
            "is_humidity_disease_risk": f_hum > 75.0,
            "is_high_wind": f_wind > 18.0,
            "heat_index_warning": "🔥 High Heat Stress (>35°C)" if f_temp > 35.0 else "✅ Temperature Optimal",
            "fungal_disease_warning": "⚠️ Fungal Blight Risk (>75% RH)" if f_hum > 75.0 else "✅ Disease Risk Low"
        }
    }


@cache_weather
def fetch_live_5day_forecast(lat: float = 30.9010, lon: float = 75.8573) -> list:
    """
    Fetches 5-day / 3-hour forecast telemetry from OpenWeatherMap.
    Aggregates into daily agronomic predictions (Max Temp, Min Temp, Humidity, Rain probability).
    """
    for key_info in OPENWEATHER_KEYS:
        key_val = key_info["key"]
        url = f"{BASE_FORECAST_URL}?lat={lat}&lon={lon}&appid={key_val}&units=metric"
        try:
            res = requests.get(url, timeout=4)
            if res.status_code == 200:
                data = res.json()
                items = data.get("list", [])
                
                daily_map = {}
                for item in items:
                    dt_txt = item.get("dt_txt", "").split(" ")[0]
                    if not dt_txt: continue
                    temp = item.get("main", {}).get("temp", 25.0)
                    hum = item.get("main", {}).get("humidity", 60)
                    wind = item.get("wind", {}).get("speed", 3.0)
                    pop = item.get("pop", 0.0) * 100 # Probability of precipitation
                    desc = item.get("weather", [{}])[0].get("description", "clear").title()
                    
                    if dt_txt not in daily_map:
                        daily_map[dt_txt] = {
                            "date": datetime.strptime(dt_txt, "%Y-%m-%d").strftime("%b %d (%a)"),
                            "temp_max": temp,
                            "temp_min": temp,
                            "humidity": hum,
                            "wind_kmh": round(wind * 3.6, 1),
                            "rain_prob": round(pop, 0),
                            "desc": desc,
                            "source": "LIVE"
                        }
                    else:
                        daily_map[dt_txt]["temp_max"] = max(daily_map[dt_txt]["temp_max"], temp)
                        daily_map[dt_txt]["temp_min"] = min(daily_map[dt_txt]["temp_min"], temp)
                        daily_map[dt_txt]["humidity"] = int((daily_map[dt_txt]["humidity"] + hum) / 2)
                        
                daily_list = list(daily_map.values())[:5]
                return daily_list
        except Exception:
            continue
            
    # Fallback 5-day structure (with dynamic current calendar dates)
    now = datetime.now()
    return [
        {"date": (now + timedelta(days=1)).strftime("%b %d (%a)"), "temp_max": 33.5, "temp_min": 23.5, "humidity": 62, "wind_kmh": 11.5, "rain_prob": 15, "desc": "Partly Cloudy", "source": "DEMO / SYNTHETIC"},
        {"date": (now + timedelta(days=2)).strftime("%b %d (%a)"), "temp_max": 34.0, "temp_min": 24.0, "humidity": 65, "wind_kmh": 13.0, "rain_prob": 25, "desc": "Scattered Clouds", "source": "DEMO / SYNTHETIC"},
        {"date": (now + timedelta(days=3)).strftime("%b %d (%a)"), "temp_max": 32.5, "temp_min": 22.5, "humidity": 74, "wind_kmh": 16.5, "rain_prob": 55, "desc": "Light Rain / Shower", "source": "DEMO / SYNTHETIC"},
        {"date": (now + timedelta(days=4)).strftime("%b %d (%a)"), "temp_max": 31.0, "temp_min": 22.0, "humidity": 78, "wind_kmh": 14.0, "rain_prob": 45, "desc": "Passing Thundershowers", "source": "DEMO / SYNTHETIC"},
        {"date": (now + timedelta(days=5)).strftime("%b %d (%a)"), "temp_max": 33.0, "temp_min": 23.5, "humidity": 60, "wind_kmh": 10.5, "rain_prob": 10, "desc": "Mostly Sunny", "source": "DEMO / SYNTHETIC"}
    ]

if __name__ == "__main__":
    print("Testing OpenWeather Service Engine...")
    cw = fetch_live_current_weather()
    print("Current Weather Location:", cw.get('location'), "| Temp:", cw.get('temp_c'), "C | Humidity:", cw.get('humidity_pct'), "%")
    fc = fetch_live_5day_forecast()
    print("5-Day Forecast Days Count:", len(fc))
