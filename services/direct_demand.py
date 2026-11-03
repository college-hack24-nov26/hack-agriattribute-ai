"""
direct_demand.py - the procurement board: companies post what they need, farmers sell to them directly.

A company (a flour brand, a ketchup maker, a fruit-pulp unit, a feed mill ...) registers and posts a
requirement: what, how much, the price it offers per quintal, where to deliver and by when. Farmers see
the requirements for their crop near them, compare the offered price with their local mandi price,
and offer to supply. The company accepts or declines each offer; accepted quantity fills the requirement.

Honesty notes
  * The platform introduces buyer and seller. It does not hold money, guarantee payment or verify companies.
    Companies are labelled UNVERIFIED until someone checks them; sample companies are labelled DEMO.
  * Sample requirements use FICTIONAL company names. Real firms (for example national flour or food brands)
    can be onboarded only when they agree to post; none is implied to have done so.
"""

from typing import Any, Dict, List, Optional

from services import farm_store
from services.scrap_marketplace import WASTE_CATALOG, haversine_km

CROP_KEYS = [
    "Soybean", "Wheat", "Tomato", "Onion", "Potato", "Maize", "Cotton", "Rice (Paddy)", "Sugarcane",
    "Groundnut (Peanut)", "Mustard / Rapeseed", "Chickpea (Gram / Chana)", "Tur / Pigeon Pea (Arhar)",
]
CATEGORIES = ["Raw material (crop)", "Farm waste / residue"]
COMPANY_TYPES = ["Snack / chips maker", "Sauce, ketchup and pulp maker", "Flour / atta mill", "Rice miller / exporter",
                 "Edible-oil mill", "Feed mill (poultry, cattle)", "Textile / ginning", "Sugar / ethanol",
                 "Spice and dal processor", "Biomass / bio-energy", "Retail / aggregator"]
DEMO_VERSION = 2   # bump to refresh the sample requirements in an existing database

# FICTIONAL sample companies, spread over the five farming belts so the region-wise view has something to show.
# (company, type, category, item, crop_key, specs, qty_q, price/q, place, lat, lon, state, deadline, terms)
_DEMO = [
    ("Demo Chips Co.", "Snack / chips maker", CATEGORIES[0], "Potato, chipping grade", "Potato",
     "55-75 mm, low sugar, no green or sprouted tubers", 900, 1650, "Satara", 17.690, 74.000, "Maharashtra", "30 Nov",
     "Contract: fixed price for the season; 10% advance; company pays transport; weekly pickup"),
    ("Demo Ketchup Works", "Sauce, ketchup and pulp maker", CATEGORIES[0], "Tomato, processing grade", "Tomato",
     "Firm, deep red, 80% colour or better, no rot", 300, 1800, "Nashik", 19.998, 73.790, "Maharashtra", "20 Nov",
     "Spot purchase; payment in 10 days; farmer delivers in crates to the plant"),
    ("Demo Atta Mills", "Flour / atta mill", CATEGORIES[0], "Wheat, chakki-grade", "Wheat",
     "Clean and dry (moisture under 12%), no ergot or live insects", 800, 2900, "Ahilyanagar", 19.095, 74.748, "Maharashtra", "30 Nov",
     "Payment within 7 days of weighing; company arranges pickup above 50 q"),
    ("Demo Berry Pulp Co.", "Sauce, ketchup and pulp maker", CATEGORIES[1], "Strawberry culls (sound, for pulp)", "Strawberry culls / overripe",
     "Cut off rot; deliver within 24 h of picking", 40, 2200, "Panchgani, Satara", 17.924, 73.800, "Maharashtra", "15 Nov",
     "Payment on delivery; company supplies cold-chain crates"),
    ("Demo Edible Oils", "Edible-oil mill", CATEGORIES[0], "Soybean, oil-grade", "Soybean",
     "Moisture under 12%, foreign matter under 2%", 1000, 5750, "Latur", 18.408, 76.560, "Maharashtra", "05 Dec",
     "Payment in 5 days; truck weighbridge at the mill"),
    ("Demo Poultry Feeds", "Feed mill (poultry, cattle)", CATEGORIES[0], "Maize, feed-grade", "Maize",
     "Moisture under 14%, aflatoxin test on delivery", 600, 2100, "Baramati", 18.151, 74.577, "Maharashtra", "25 Nov",
     "Payment in 7 days; farmer pays transport up to 40 km"),
    ("Demo Biomass Energy", "Biomass / bio-energy", CATEGORIES[1], "Cotton stalks, dry", "Cotton stalks",
     "Dry, chipped or bundled, no soil", 500, 450, "Sangli", 16.855, 74.565, "Maharashtra", "10 Dec",
     "Payment on delivery; company arranges pickup above 30 q"),
    ("Demo Basmati Exports", "Rice miller / exporter", CATEGORIES[0], "Basmati paddy, long grain", "Rice (Paddy)",
     "Moisture under 17%, minimum 70% head rice", 1500, 3600, "Ludhiana", 30.901, 75.857, "Punjab", "15 Dec",
     "Contract: price fixed at sowing; 15% advance; company pays transport"),
    ("Demo Snack Foods", "Snack / chips maker", CATEGORIES[0], "Potato, chipping grade", "Potato",
     "Round, 50-70 mm, specific gravity above 1.080", 1200, 1500, "Jalandhar", 31.326, 75.576, "Punjab", "20 Dec",
     "Contract: fixed price; 10% advance; weekly pickup from the farm gate"),
    ("Demo Flour Co.", "Flour / atta mill", CATEGORIES[0], "Wheat, atta-grade", "Wheat",
     "Protein above 11%, moisture under 12%", 2000, 2950, "Karnal", 29.686, 76.990, "Haryana", "10 Dec",
     "Payment in 5 days; mill-gate delivery; moisture and protein tested on arrival"),
    ("Demo Sugar & Ethanol", "Sugar / ethanol", CATEGORIES[0], "Sugarcane, mill supply", "Sugarcane",
     "Fresh-cut within 24 h, free of trash and roots", 5000, 380, "Muzaffarnagar", 29.472, 77.704, "Uttar Pradesh", "31 Jan",
     "Payment fortnightly; company arranges harvesting gangs and transport"),
    ("Demo Potato Flakes", "Snack / chips maker", CATEGORIES[0], "Potato, processing grade", "Potato",
     "Any size above 45 mm, low defects", 1800, 1350, "Agra", 27.177, 78.008, "Uttar Pradesh", "15 Dec",
     "Spot purchase; payment in 7 days; farmer delivers to the plant"),
    ("Demo Spice & Dal Foods", "Spice and dal processor", CATEGORIES[0], "Tur dal, split-grade", "Tur / Pigeon Pea (Arhar)",
     "Clean, moisture under 10%, bold seed", 700, 7100, "Kalaburagi", 17.330, 76.830, "Karnataka", "20 Dec",
     "Payment in 7 days; company pays transport above 20 q"),
    ("Demo Groundnut Oils", "Edible-oil mill", CATEGORIES[0], "Groundnut kernels", "Groundnut (Peanut)",
     "Oil content above 45%, moisture under 8%", 900, 6200, "Hubballi", 15.364, 75.124, "Karnataka", "30 Nov",
     "Payment in 5 days; weighbridge at the mill"),
    ("Demo Tomato Puree Ltd", "Sauce, ketchup and pulp maker", CATEGORIES[0], "Tomato, puree grade", "Tomato",
     "High solids (brix above 4.5), firm, no rot", 800, 1500, "Chittoor", 13.217, 79.100, "Andhra Pradesh", "30 Nov",
     "Contract: fixed price; payment in 10 days; collection centres in the district"),
    ("Demo Cotton Spinners", "Textile / ginning", CATEGORIES[0], "Cotton (kapas), medium staple", "Cotton",
     "Staple 28-30 mm, moisture under 8%", 1500, 7000, "Guntur", 16.306, 80.437, "Andhra Pradesh", "31 Dec",
     "Payment in 7 days; weighing and grading at the gin"),
]


def remaining_q(d: Dict[str, Any]) -> float:
    return max(0.0, float(d.get("qty_needed_q") or 0) - float(d.get("qty_filled_q") or 0))


_DEMO_CHECKED = False


def ensure_demo_demands() -> None:
    """Keeps the fictional sample requirements current (flagged DEMO). Checked once per server process."""
    global _DEMO_CHECKED
    if _DEMO_CHECKED:
        return
    _DEMO_CHECKED = True
    demos = [d for d in farm_store.select("buyer_demands") if d.get("is_demo")]
    if len(demos) == len(_DEMO) and all(d.get("terms") is not None for d in demos) and any(d.get("crop_key") == "Potato" for d in demos):
        return
    if demos:
        farm_store.delete("buyer_demands", is_demo=True)
    for c, ctype, cat, item, crop, specs, qty, price, place, lat, lon, state, deadline, terms in _DEMO:
        farm_store.insert("buyer_demands", {
            "company": c, "company_type": ctype, "category": cat, "item": item, "crop_key": crop, "specs": specs,
            "qty_needed_q": qty, "qty_filled_q": 0, "price_offer": price, "lat": lat, "lon": lon, "place": place,
            "state": state, "deadline": deadline, "terms": terms, "contact_phone": "",
            "is_demo": True, "verified": False, "status": "open",
        })


def region_of(d: Dict[str, Any], region_coords: Dict[str, Dict[str, float]]) -> str:
    """Farming belt of a requirement's delivery point."""
    from services import geolocation_service
    try:
        return geolocation_service.region_for(float(d["lat"]), float(d["lon"]), d.get("state", ""), region_coords)
    except (TypeError, ValueError, KeyError):
        return "Unknown"


def post_demand(**fields: Any) -> Dict[str, Any]:
    fields.setdefault("qty_filled_q", 0)
    fields.setdefault("is_demo", False)
    fields.setdefault("verified", False)
    fields["status"] = "open"
    return farm_store.insert("buyer_demands", fields)


def rank_demands(demands: List[Dict[str, Any]], crop_key: Optional[str], lat: float, lon: float,
                 radius_km: Optional[float] = None) -> List[Dict[str, Any]]:
    """Open requirements, optionally only for one crop / within a radius, nearest and most urgent first."""
    out = []
    for d in demands:
        if d.get("status") != "open" or remaining_q(d) <= 0:
            continue
        if crop_key and d.get("crop_key") != crop_key:
            continue
        try:
            dist = haversine_km(float(lat), float(lon), float(d["lat"]), float(d["lon"]))
        except (TypeError, ValueError, KeyError):
            continue
        if radius_km and dist > radius_km:
            continue
        out.append({**d, "distance_km": dist, "remaining_q": remaining_q(d)})
    return sorted(out, key=lambda x: x["distance_km"])


def make_offer(demand: Dict[str, Any], farmer_name: str, phone: str, qty_q: float, price_ask: float,
               place: str, message: str) -> Dict[str, Any]:
    qty = max(0.0, min(float(qty_q), remaining_q(demand)))
    return farm_store.insert("demand_offers", {
        "demand_id": demand["id"], "farmer_name": farmer_name, "phone": phone, "qty_q": qty,
        "price_ask": float(price_ask), "place": place, "message": message, "status": "offered",
    })


def respond_to_offer(offer: Dict[str, Any], accept: bool) -> bool:
    """Accepting fills the requirement (never beyond what is still needed); declining just closes the offer."""
    if offer.get("status") != "offered":
        return False
    if not accept:
        return farm_store.update("demand_offers", offer["id"], {"status": "declined"})
    demand = next((d for d in farm_store.select("buyer_demands") if d["id"] == offer["demand_id"]), None)
    if demand is None:
        return False
    take = min(float(offer.get("qty_q") or 0), remaining_q(demand))
    if take <= 0:
        return False
    filled = float(demand.get("qty_filled_q") or 0) + take
    farm_store.update("buyer_demands", demand["id"], {
        "qty_filled_q": filled, "status": "filled" if filled >= float(demand["qty_needed_q"]) else "open"})
    return farm_store.update("demand_offers", offer["id"], {"status": "accepted", "qty_q": take})


def offers_for(demand_id: str) -> List[Dict[str, Any]]:
    return [o for o in farm_store.select("demand_offers") if o.get("demand_id") == demand_id]


def waste_keys() -> List[str]:
    return list(WASTE_CATALOG.keys())
