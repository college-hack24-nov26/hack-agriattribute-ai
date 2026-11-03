"""
geolocation_service.py - real "live location" for the farm.

Why this exists: a Streamlit app runs on a server, so an IP lookup made from Python returns the
*server's* (or ISP's) location, never the farmer's. The only trustworthy source is the browser's
own Geolocation API (GPS / Wi-Fi), which needs the user's permission. This module provides:

  * live_location_button()  - a browser-side button that asks for permission and returns lat/lon
  * reverse_geocode()       - lat/lon -> village / district / state (OpenStreetMap Nominatim)
  * search_place()          - typed village / town name -> candidate places in India (Nominatim)
  * ip_location()           - approximate fallback (network location), clearly flagged as approximate
  * region_for()            - maps a place to one of the app's agro-climatic belts
"""

from typing import Any, Dict, List, Optional

import requests
import streamlit as st

NOMINATIM = "https://nominatim.openstreetmap.org"
HEADERS = {"User-Agent": "AgriAttribute-AI/1.0 (farm advisory app)", "Accept-Language": "en"}

# Indian state -> the agro-climatic belt used by the models.
STATE_TO_REGION = {
    "maharashtra": "Maharashtra & Vidarbha (Deccan)",
    "punjab": "Punjab & Haryana (Indo-Gangetic)",
    "haryana": "Punjab & Haryana (Indo-Gangetic)",
    "andhra pradesh": "Andhra Pradesh & Telangana",
    "telangana": "Andhra Pradesh & Telangana",
    "uttar pradesh": "Uttar Pradesh & Bihar",
    "bihar": "Uttar Pradesh & Bihar",
    "karnataka": "Karnataka & Tamil Nadu",
    "tamil nadu": "Karnataka & Tamil Nadu",
}

# India bounding box (rough): rejects coordinates that are clearly outside the country.
_INDIA = (6.0, 37.5, 68.0, 97.5)  # lat_min, lat_max, lon_min, lon_max


def in_india(lat: float, lon: float) -> bool:
    return _INDIA[0] <= lat <= _INDIA[1] and _INDIA[2] <= lon <= _INDIA[3]


# ---------------------------------------------------------------------------
# Browser geolocation button (st.components.v2: runs in the page, so it can use navigator.geolocation)
# ---------------------------------------------------------------------------

_JS = """
export default function (component) {
    const { data, parentElement, setTriggerValue } = component;
    const wrap = parentElement.querySelector('.wrap');
    const btn = parentElement.querySelector('button');
    const status = parentElement.querySelector('.status');
    const label = (data && data.label) || 'Use my live location';
    btn.querySelector('.txt').textContent = label;
    if (data && data.hidden) { wrap.style.display = 'none'; }

    // Fallback from the BROWSER (not the server), so it is the visitor's network even when the app is hosted elsewhere.
    const networkFallback = async (why) => {
        try {
            const r = await fetch('https://ipwhois.app/json/');
            const j = await r.json();
            if (j && j.success && j.latitude) {
                setTriggerValue('position', { lat: j.latitude, lon: j.longitude, accuracy: null, approx: true, ts: Date.now() });
                return;
            }
        } catch (e) { /* offline or blocked */ }
        setTriggerValue('error', { code: 0, message: why || 'Location unavailable', ts: Date.now() });
    };

    const locate = () => {
        if (!navigator.geolocation) { networkFallback('This browser does not support location access.'); return; }
        btn.disabled = true;
        btn.querySelector('.txt').textContent = 'Locating you...';
        status.textContent = 'Allow the location prompt in your browser';
        navigator.geolocation.getCurrentPosition(
            (pos) => {
                btn.disabled = false; btn.querySelector('.txt').textContent = label; status.textContent = '';
                setTriggerValue('position', { lat: pos.coords.latitude, lon: pos.coords.longitude, accuracy: pos.coords.accuracy, approx: false, ts: Date.now() });
            },
            (err) => {
                btn.disabled = false; btn.querySelector('.txt').textContent = label; status.textContent = '';
                networkFallback(err && err.message);
            },
            { enableHighAccuracy: true, timeout: 12000, maximumAge: 60000 }
        );
    };
    btn.onclick = locate;

    // Once per browser tab, locate automatically on arrival (only when the page asks for it).
    try {
        if (data && data.auto && !sessionStorage.getItem('aa_autolocated')) {
            sessionStorage.setItem('aa_autolocated', '1');
            locate();
        }
    } catch (e) { /* storage blocked: the button still works */ }
}
"""

_HTML = """
<div class="wrap">
  <button type="button" class="aa-live"><span class="txt">Use my live location</span></button>
  <div class="status" role="status" aria-live="polite"></div>
</div>
"""

_CSS = """
.aa-live {
    width: 100%; min-height: 44px; padding: 0 14px; cursor: pointer;
    display: flex; align-items: center; justify-content: center; gap: 8px;
    font: 700 0.95rem 'Plus Jakarta Sans', Inter, system-ui, sans-serif;
    color: #fff; border: none; border-radius: 14px; background: linear-gradient(135deg, #047857, #10b981);
    box-shadow: 0 8px 22px rgba(4, 120, 87, .32); transition: transform .18s ease, filter .18s ease;
}
.aa-live:hover:not(:disabled) { transform: translateY(-2px); filter: brightness(1.06); }
.aa-live:disabled { opacity: .75; cursor: progress; }
.aa-live:focus-visible { outline: 3px solid rgba(183, 121, 31, .6); outline-offset: 2px; }
.status { font: 600 .72rem Inter, system-ui, sans-serif; color: #5d6b62; margin-top: 4px; min-height: 1em; text-align: center; }
"""

_live_component = None


def _component():
    global _live_component
    if _live_component is None:
        _live_component = st.components.v2.component("aa_live_location", html=_HTML, css=_CSS, js=_JS)
    return _live_component


def live_location_button(label: str = "Use my live location", key: str = "aa_live_loc", auto: bool = False, hidden: bool = False):
    """Mounts the browser-side locator. Returns an object with .position / .error (trigger values).

    auto=True asks for the location once on arrival; hidden=True renders no button (auto-locate only)."""
    return _component()(key=key, data={"label": label, "auto": auto, "hidden": hidden},
                        on_position_change=lambda: None, on_error_change=lambda: None)


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

@st.cache_data(ttl=86400, show_spinner=False)
def reverse_geocode(lat: float, lon: float) -> Dict[str, Any]:
    """lat/lon -> {'place','district','state','display'}; never raises (offline -> coordinates only)."""
    fallback = {"place": "My location", "district": "", "state": "", "display": f"{lat:.3f}, {lon:.3f}"}
    try:
        r = requests.get(
            f"{NOMINATIM}/reverse",
            params={"format": "jsonv2", "lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "zoom": 12, "addressdetails": 1},
            headers=HEADERS, timeout=6,
        )
        if r.status_code != 200:
            return fallback
        a = r.json().get("address", {})
        place = (a.get("village") or a.get("town") or a.get("city") or a.get("suburb")
                 or a.get("hamlet") or a.get("county") or "My location")
        district = a.get("state_district") or a.get("county") or ""
        state = a.get("state", "")
        parts = [p for p in (place, district if district != place else "", state) if p]
        return {"place": place, "district": district, "state": state, "display": ", ".join(parts)}
    except Exception:
        return fallback


@st.cache_data(ttl=3600, show_spinner=False)
def search_place(query: str) -> List[Dict[str, Any]]:
    """Typed village / town -> up to 5 candidate places in India."""
    q = (query or "").strip()
    if len(q) < 3:
        return []
    try:
        r = requests.get(
            f"{NOMINATIM}/search",
            params={"format": "jsonv2", "q": q, "countrycodes": "in", "limit": 5, "addressdetails": 1},
            headers=HEADERS, timeout=6,
        )
        out = []
        for it in (r.json() if r.status_code == 200 else []):
            a = it.get("address", {})
            place = (a.get("village") or a.get("town") or a.get("city") or a.get("suburb")
                     or it.get("name") or q)
            state = a.get("state", "")
            district = a.get("state_district") or a.get("county") or ""
            out.append({
                "lat": float(it["lat"]), "lon": float(it["lon"]), "place": place,
                "district": district, "state": state,
                "display": ", ".join(p for p in (place, district if district != place else "", state) if p),
            })
        return out
    except Exception:
        return []


def ip_location() -> Optional[Dict[str, Any]]:
    """
    Approximate location from the network address. Only a fallback when the browser gives no GPS fix:
    city-level at best. HTTPS only. Note this runs on the server, so it is only meaningful when the app
    runs on the farmer's own machine (the browser-side lookup in the locator component covers hosted use).
    """
    for url, parse in (
        ("https://ipwhois.app/json/", lambda d: (d.get("latitude"), d.get("longitude"), d.get("city"), d.get("region"), d.get("success"))),
        ("https://ipapi.co/json/", lambda d: (d.get("latitude"), d.get("longitude"), d.get("city"), d.get("region"), not d.get("error"))),
    ):
        try:
            r = requests.get(url, headers=HEADERS, timeout=4)
            if r.status_code != 200:
                continue
            lat, lon, city, state, ok = parse(r.json())
            if ok and lat is not None and lon is not None and in_india(float(lat), float(lon)):
                return {"lat": float(lat), "lon": float(lon), "place": city or "My area",
                        "district": "", "state": state or "", "display": f"{city or 'My area'}, {state or ''}".strip(", ")}
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Region mapping
# ---------------------------------------------------------------------------

# Coarse state outlines (lat_min, lat_max, lon_min, lon_max), checked in order. Used only when the
# state name is unknown (e.g. a bookmarked URL), because "nearest belt centre" is wrong for places
# such as Kopargaon (the Maharashtra belt is anchored on Nagpur, 480 km away).
_BELT_BOXES = [
    ("Maharashtra & Vidarbha (Deccan)", (16.0, 19.0, 72.6, 77.5)),
    ("Maharashtra & Vidarbha (Deccan)", (19.0, 22.1, 72.6, 80.9)),
    ("Punjab & Haryana (Indo-Gangetic)", (27.6, 32.6, 73.8, 77.6)),
    ("Uttar Pradesh & Bihar", (23.9, 30.5, 77.0, 88.3)),
    ("Andhra Pradesh & Telangana", (13.5, 19.9, 76.7, 84.8)),
    ("Karnataka & Tamil Nadu", (8.0, 18.5, 74.0, 80.4)),
]


def region_for(lat: float, lon: float, state: str, region_coords: Dict[str, Dict[str, float]]) -> str:
    """Agro-climatic belt for a place: by state name, else by state outline, else nearest belt centre."""
    mapped = STATE_TO_REGION.get((state or "").strip().lower())
    if mapped and mapped in region_coords:
        return mapped
    for belt, (la0, la1, lo0, lo1) in _BELT_BOXES:
        if belt in region_coords and la0 <= lat <= la1 and lo0 <= lon <= lo1:
            return belt
    return min(region_coords, key=lambda r: (lat - region_coords[r]["lat"]) ** 2 + (lon - region_coords[r]["lon"]) ** 2)
