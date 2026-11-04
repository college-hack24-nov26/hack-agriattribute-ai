"""
check_services.py - one command that says which external services work right now.

Run from the repo root:  python pipeline/check_services.py
Each line: OK / FAIL / SKIP (no key), the service, and what it returned. Keys are read from .env or the
environment and are never printed.
"""

import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(ROOT, ".env"))
except Exception:
    pass

import requests  # noqa: E402

UA = {"User-Agent": "AgriAttribute-AI/1.0 (service check)"}
results = []


def check(name, fn):
    t = time.time()
    try:
        status, detail = fn()
    except Exception as exc:
        status, detail = "FAIL", f"{type(exc).__name__}: {str(exc)[:120]}"
    results.append((status, name, detail, time.time() - t))
    print(f"{status:4s}  {name:32s} {time.time() - t:5.1f}s  {detail}", flush=True)


def openweather():
    k = os.getenv("OPENWEATHER_API_KEY")
    if not k:
        return "SKIP", "no OPENWEATHER_API_KEY"
    r = requests.get("https://api.openweathermap.org/data/2.5/weather",
                     params={"lat": 17.99, "lon": 74.43, "appid": k, "units": "metric"}, timeout=15)
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code}"
    d = r.json()
    return "OK", f"{d.get('name')} {d['main']['temp']:.1f}°C {d['weather'][0]['description']}"


def openweather_forecast():
    k = os.getenv("OPENWEATHER_API_KEY")
    if not k:
        return "SKIP", "no key"
    r = requests.get("https://api.openweathermap.org/data/2.5/forecast",
                     params={"lat": 17.99, "lon": 74.43, "appid": k, "units": "metric"}, timeout=15)
    return ("OK", f"{len(r.json().get('list', []))} forecast steps") if r.status_code == 200 else ("FAIL", f"HTTP {r.status_code}")


def openweather_tiles():
    k = os.getenv("OPENWEATHER_MAPS_KEY") or os.getenv("OPENWEATHER_API_KEY")
    if not k:
        return "SKIP", "no key"
    r = requests.get(f"https://tile.openweathermap.org/map/clouds_new/3/5/3.png?appid={k}", timeout=15)
    return ("OK", f"tile {len(r.content)} bytes") if r.status_code == 200 else ("FAIL", f"HTTP {r.status_code}")


def mcii():
    from services import annam_mcii_service as m
    r = requests.get(m.MCII_PRIMARY_ENDPOINT, timeout=20, headers=UA)
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code}"
    return "OK", f"{len(r.content) // 1024} KB station payload"


def gemini():
    from services import gemini_service as g
    if not g._get_gemini_key():
        return "SKIP", "no GEMINI_API_KEY"
    data, model = g.generate_content({"contents": [{"parts": [{"text": "Reply with the single word: ready"}]}],
                                      "generationConfig": {"temperature": 0, "maxOutputTokens": 20,
                                                           "thinkingConfig": {"thinkingBudget": 0}}}, timeout=30)
    if not data:
        return "FAIL", "no model answered (quota or key)"
    return "OK", f"{model}: {g.response_text(data).strip()[:30]!r}"


def supabase():
    from services import supabase_client as s
    st_ = s._test_supabase_connection_uncached()
    status = str(st_.get("status", "")).upper()
    if status != "LIVE":
        return "FAIL", f"{st_.get('status')} ({st_.get('storage_mode', '')})"
    from services import farm_store
    counts = {t: len(farm_store._fetch(t, {})) for t in ("buyer_demands", "scrap_buyers", "river_incidents")}
    return "OK", f"connected; rows {counts}"


def nominatim():
    r = requests.get("https://nominatim.openstreetmap.org/reverse",
                     params={"lat": 17.99, "lon": 74.43, "format": "jsonv2"}, headers=UA, timeout=15)
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code}"
    a = r.json().get("address", {})
    return "OK", f"{a.get('town') or a.get('city') or a.get('village')}, {a.get('state')}"


def ipwhois():
    r = requests.get("https://ipwhois.app/json/", headers=UA, timeout=10)
    return ("OK", "approximate location service reachable") if r.status_code == 200 else ("FAIL", f"HTTP {r.status_code}")


def rainviewer():
    r = requests.get("https://api.rainviewer.com/public/weather-maps.json", headers=UA, timeout=15)
    if r.status_code != 200:
        return "FAIL", f"HTTP {r.status_code}"
    return "OK", f"{len(r.json().get('radar', {}).get('past', []))} radar frames"


def osm_tiles():
    r = requests.get("https://tile.openstreetmap.org/3/5/3.png", headers=UA, timeout=15)
    return ("OK", "base map tiles") if r.status_code == 200 else ("FAIL", f"HTTP {r.status_code}")


def esri():
    r = requests.get("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/3/3/5", headers=UA, timeout=15)
    return ("OK", "satellite tiles") if r.status_code == 200 else ("FAIL", f"HTTP {r.status_code}")


def local_files():
    need = ["models/model.pkl", "models/feature_schema.json", "models/per_crop_metrics.json", "models/season_normals.json",
            "data/field_trials.csv", "data/agmarknet_daily_report.csv", "data/annam/mcii_cache.json"]
    missing = [p for p in need if not os.path.exists(p)]
    langs = sorted(f[:-5] for f in os.listdir("data/i18n") if f.endswith(".json")) if os.path.isdir("data/i18n") else []
    if missing:
        return "FAIL", f"missing {missing}"
    return "OK", f"model, data and {len(langs)} translation files ({', '.join(langs)})"


if __name__ == "__main__":
    for name, fn in [("Bundled model and data", local_files), ("OpenWeather current", openweather),
                     ("OpenWeather forecast", openweather_forecast), ("OpenWeather map tiles", openweather_tiles),
                     ("ANNAM.AI MCII stations", mcii), ("Gemini (with fallback)", gemini), ("Supabase database", supabase),
                     ("OSM Nominatim geocoding", nominatim), ("ipwhois (GPS fallback)", ipwhois),
                     ("RainViewer radar", rainviewer), ("OSM map tiles", osm_tiles), ("Esri satellite tiles", esri)]:
        check(name, fn)
    bad = [r for r in results if r[0] == "FAIL"]
    print(f"\n{len(results) - len(bad)}/{len(results)} OK or skipped; {len(bad)} failing")
    sys.exit(1 if bad else 0)
