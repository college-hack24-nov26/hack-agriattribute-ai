"""
scrap_marketplace.py - Farm Waste Market: farmers list crop residue / culls, buyers get matched.

A farmer lists waste (for example strawberry culls) with a photo; the app (1) checks the photo with
Gemini, (2) matches registered buyers by what they accept, distance, capacity and price, and
(3) lets the farmer send an enquiry. Buyers can register themselves and browse listings near them.

Honesty notes
  * Buyers marked DEMO are samples so the flow can be shown; they have no real contact details.
    Real buyers register in the "I'm a buyer" tab and appear alongside them.
  * The app never invents a market price: the price shown is what each buyer states.
  * Photo analysis is an AI estimate and is labelled as such.
"""

import base64
import io
import json
import math
from datetime import date
from typing import Any, Dict, List, Optional


from services import farm_store

# --- catalog ------------------------------------------------------------------------------------
# key -> (emoji, category, perishable, handling tip)
WASTE_CATALOG: Dict[str, Dict[str, Any]] = {
    "Strawberry culls / overripe": {"emoji": "🍓", "cat": "Fruit & vegetable culls", "perishable": True,
                                    "tip": "Pulp or freeze within 24 h; keep in shade and in shallow crates to avoid mould."},
    "Tomato culls": {"emoji": "🍅", "cat": "Fruit & vegetable culls", "perishable": True,
                     "tip": "Sell within 24-48 h; avoid stacking more than 3 crates high."},
    "Onion culls & peels": {"emoji": "🧅", "cat": "Fruit & vegetable culls", "perishable": False,
                            "tip": "Keep dry and ventilated; dehydration units prefer unrotted culls."},
    "Banana pseudostem & culls": {"emoji": "🍌", "cat": "Fruit & vegetable culls", "perishable": True,
                                  "tip": "Cut and collect right after harvest; fibre units want fresh stem."},
    "Mango / grape / pomegranate culls": {"emoji": "🍇", "cat": "Fruit & vegetable culls", "perishable": True,
                                          "tip": "Sort out rotten fruit; processors pay more for sound culls."},
    "Vegetable market waste": {"emoji": "🥬", "cat": "Fruit & vegetable culls", "perishable": True,
                               "tip": "Keep plastic out; biogas and compost units reject mixed plastic."},
    "Sugarcane trash / bagasse": {"emoji": "🎋", "cat": "Crop residue", "perishable": False,
                                  "tip": "Bale or heap dry; do not burn: buyers pay for clean dry trash."},
    "Wheat / rice straw": {"emoji": "🌾", "cat": "Crop residue", "perishable": False,
                           "tip": "Bale after harvest and store under cover; wet straw loses most value."},
    "Soybean straw (bhusa)": {"emoji": "🌱", "cat": "Crop residue", "perishable": False,
                              "tip": "Keep dry; fodder buyers want green-brown, mould-free bhusa."},
    "Cotton stalks": {"emoji": "🪵", "cat": "Crop residue", "perishable": False,
                      "tip": "Uproot and dry in the field; chip or bundle for pellet makers."},
    "Maize stalks & cobs": {"emoji": "🌽", "cat": "Crop residue", "perishable": False,
                            "tip": "Separate cobs from stalks; both have different buyers."},
    "Groundnut shells / haulm": {"emoji": "🥜", "cat": "Crop residue", "perishable": False,
                                 "tip": "Keep dry; shells go to fuel and bedding buyers, haulm to fodder buyers."},
    "Tur / mustard stalks": {"emoji": "🪴", "cat": "Crop residue", "perishable": False,
                             "tip": "Bundle after drying; briquette makers pay by weight."},
    "Rice husk": {"emoji": "🍚", "cat": "Crop residue", "perishable": False,
                  "tip": "Store dry in bags; useful as fuel, bedding and biochar feed."},
    "Cattle dung / FYM": {"emoji": "🐄", "cat": "Livestock", "perishable": False,
                          "tip": "Keep covered; biogas and organic-manure units want it fresh or well-rotted."},
    "Poultry litter": {"emoji": "🐔", "cat": "Livestock", "perishable": False,
                       "tip": "Keep dry; organic-manure units pay for litter free of plastic."},
}

BUYER_TYPES: Dict[str, List[str]] = {
    "Fruit pulp / jam / juice processor": ["Strawberry culls / overripe", "Tomato culls", "Mango / grape / pomegranate culls"],
    "Vinegar / wine / ethanol maker": ["Strawberry culls / overripe", "Mango / grape / pomegranate culls"],
    "Dehydration / flake unit": ["Onion culls & peels", "Tomato culls"],
    "Biogas / compressed-biogas plant": ["Strawberry culls / overripe", "Tomato culls", "Vegetable market waste", "Banana pseudostem & culls",
                                         "Cattle dung / FYM", "Sugarcane trash / bagasse"],
    "Compost / vermicompost unit": ["Strawberry culls / overripe", "Tomato culls", "Onion culls & peels", "Vegetable market waste",
                                    "Banana pseudostem & culls", "Cattle dung / FYM", "Poultry litter", "Sugarcane trash / bagasse"],
    "Cattle-feed / fodder trader": ["Wheat / rice straw", "Soybean straw (bhusa)", "Maize stalks & cobs", "Groundnut shells / haulm",
                                    "Banana pseudostem & culls", "Sugarcane trash / bagasse"],
    "Biomass pellet / briquette maker": ["Cotton stalks", "Tur / mustard stalks", "Groundnut shells / haulm", "Rice husk",
                                         "Maize stalks & cobs", "Sugarcane trash / bagasse", "Wheat / rice straw"],
    "Bio-energy / co-generation plant": ["Sugarcane trash / bagasse", "Rice husk", "Cotton stalks"],
    "Paper / paperboard mill": ["Wheat / rice straw", "Sugarcane trash / bagasse"],
    "Mushroom grower": ["Wheat / rice straw", "Soybean straw (bhusa)"],
    "Biochar maker": ["Cotton stalks", "Tur / mustard stalks", "Groundnut shells / haulm", "Rice husk", "Maize stalks & cobs"],
    "Banana fibre / craft unit": ["Banana pseudostem & culls"],
}

# sample buyers: DEMO ONLY (fictional, no contact details). (name, type, place, lat, lon, min_qty_q, price_min, price_max)
_DEMO_BUYERS = [
    ("Panchgani Berry Pulp Unit", "Fruit pulp / jam / juice processor", "Panchgani, Satara", 17.924, 73.800, 2, 1800, 3200),
    ("Satara Fruit Wine & Vinegar Works", "Vinegar / wine / ethanol maker", "Satara", 17.690, 74.000, 5, 1200, 2200),
    ("Phaltan Bio-CBG Plant", "Biogas / compressed-biogas plant", "Phaltan", 17.991, 74.432, 10, 300, 700),
    ("Pune Organic Compost Hub", "Compost / vermicompost unit", "Pune", 18.520, 73.857, 5, 200, 600),
    ("Kopargaon Agro Compost Unit", "Compost / vermicompost unit", "Kopargaon", 19.884, 74.478, 5, 200, 550),
    ("Ahilyanagar Fodder Traders", "Cattle-feed / fodder trader", "Ahilyanagar", 19.095, 74.748, 20, 250, 600),
    ("Nashik Onion Flake Co.", "Dehydration / flake unit", "Nashik", 19.998, 73.790, 20, 400, 900),
    ("Sangli Briquette Works", "Biomass pellet / briquette maker", "Sangli", 16.855, 74.565, 30, 350, 800),
    ("Kolhapur Co-gen Feedstock Desk", "Bio-energy / co-generation plant", "Kolhapur", 16.705, 74.243, 50, 300, 700),
    ("Baramati Mushroom Growers Group", "Mushroom grower", "Baramati", 18.151, 74.577, 10, 250, 500),
    ("Solapur Paperboard Mill", "Paper / paperboard mill", "Solapur", 17.659, 75.906, 50, 300, 650),
    ("Jalgaon Banana Fibre Cluster", "Banana fibre / craft unit", "Jalgaon", 21.007, 75.566, 10, 150, 450),
    ("Latur Biochar Collective", "Biochar maker", "Latur", 18.408, 76.560, 20, 300, 700),
]


# --- helpers ------------------------------------------------------------------------------------
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(a))


def to_quintal(qty: float, unit: str) -> float:
    return {"kg": qty / 100.0, "quintal": qty, "tonne": qty * 10.0}.get(unit, qty)


def make_thumbnail_b64(image_bytes: bytes, max_side: int = 640) -> str:
    """Resizes to a small JPEG (about 40-80 KB) so it can be stored with the listing."""
    from PIL import Image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=72, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


_DEMO_CHECKED = False


def ensure_demo_buyers() -> None:
    """Inserts the sample buyers once (flagged DEMO). Checked once per server process."""
    global _DEMO_CHECKED
    if _DEMO_CHECKED:
        return
    _DEMO_CHECKED = True
    existing = farm_store.select("scrap_buyers")
    if any(b.get("is_demo") for b in existing):
        return
    for name, btype, place, lat, lon, minq, pmin, pmax in _DEMO_BUYERS:
        farm_store.insert("scrap_buyers", {
            "name": name, "buyer_type": btype, "accepts": ",".join(BUYER_TYPES[btype]), "min_qty_q": minq,
            "price_min": pmin, "price_max": pmax, "lat": lat, "lon": lon, "place": place, "state": "Maharashtra",
            "phone": "", "is_demo": True, "verified": False,
        })


# --- matching -----------------------------------------------------------------------------------
def match_buyers(listing: Dict[str, Any], buyers: List[Dict[str, Any]], radius_km: Optional[float] = None) -> List[Dict[str, Any]]:
    """Buyers that accept this waste type, scored 0-100 on distance, capacity and price fit."""
    qty_q = float(listing.get("quantity_q") or 0)
    ask = float(listing.get("price_expectation") or 0)
    out = []
    for b in buyers:
        accepts = [a.strip() for a in str(b.get("accepts", "")).split(",") if a.strip()]
        if listing["waste_type"] not in accepts:
            continue
        try:
            dist = haversine_km(float(listing["lat"]), float(listing["lon"]), float(b["lat"]), float(b["lon"]))
        except (TypeError, ValueError, KeyError):
            continue
        if radius_km and dist > radius_km:
            continue
        minq = float(b.get("min_qty_q") or 0)
        cap = 1.0 if minq <= 0 or qty_q >= minq else max(0.1, qty_q / minq)
        pmin, pmax = float(b.get("price_min") or 0), float(b.get("price_max") or 0)
        if ask <= 0 or pmax <= 0:
            price = 0.7
        elif pmin <= ask <= pmax:
            price = 1.0
        else:
            gap = (pmin - ask) / pmin if ask < pmin else (ask - pmax) / pmax
            price = max(0.1, 1.0 - gap)
        score = 100.0 * (0.55 * math.exp(-dist / 80.0) + 0.25 * cap + 0.20 * price)
        reasons = [f"{dist:.0f} km away"]
        reasons.append("takes your quantity" if cap >= 1.0 else f"wants at least {minq:g} q (you have {qty_q:g} q)")
        if pmax > 0:
            reasons.append(f"pays Rs {pmin:,.0f}-{pmax:,.0f} / quintal")
        out.append({**b, "distance_km": dist, "score": round(score, 1), "reasons": reasons})
    return sorted(out, key=lambda x: -x["score"])


# --- AI photo check -----------------------------------------------------------------------------
def analyze_photo(image_bytes: bytes, mime: str, claimed_type: Optional[str] = None) -> Dict[str, Any]:
    """Gemini vision: what is it, how good is it, what could it be used for. Never raises."""
    try:
        from services import gemini_service
        key = gemini_service._get_gemini_key()
        if not key:
            return {"error": "AI photo check needs a Gemini key in .env (GEMINI_API_KEY)."}
        types = list(WASTE_CATALOG.keys())
        prompt = (
            "You help Indian farmers sell farm waste. Look at the photo and answer with JSON only, keys: "
            f'"detected_type" (one of {json.dumps(types)} or "Other"), "condition" (Fresh, Slightly overripe, Dry, Wet/rotting), '
            '"quality_grade" (A, B or C), "uses" (list of up to 3 short strings), "advice" (one short sentence for the farmer), '
            '"matches_claim" (true/false/null). '
            f'The farmer says it is: {claimed_type or "not stated"}. Be honest if the photo is unclear or not farm waste.'
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime or "image/jpeg",
                                                                        "data": base64.b64encode(image_bytes).decode("ascii")}}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500, "responseMimeType": "application/json",
                                 "thinkingConfig": {"thinkingBudget": 0}},
        }
        from services import gemini_service
        data, _model = gemini_service.generate_content(payload, timeout=40)
        if not data:
            return {"error": "AI photo check unavailable right now (Gemini quota or network). Your listing still works."}
        text = gemini_service.response_text(data)
        data = json.loads(text)
        return data if isinstance(data, dict) else {"error": "Unexpected AI response."}
    except Exception as exc:  # network, JSON, missing key ...
        return {"error": f"AI photo check unavailable ({type(exc).__name__})."}


# --- persistence --------------------------------------------------------------------------------
def create_listing(**fields: Any) -> Dict[str, Any]:
    fields["status"] = "open"
    return farm_store.insert("scrap_listings", fields)


def create_buyer(**fields: Any) -> Dict[str, Any]:
    fields.setdefault("is_demo", False)
    fields.setdefault("verified", False)
    return farm_store.insert("scrap_buyers", fields)


def send_enquiry(listing_id: str, buyer_id: str, message: str) -> Dict[str, Any]:
    return farm_store.insert("scrap_inquiries", {"listing_id": listing_id, "buyer_id": buyer_id, "message": message, "status": "sent"})


def default_enquiry_text(listing: Dict[str, Any]) -> str:
    return (f"Hello, I have {listing.get('quantity')} {listing.get('unit')} of {listing.get('waste_type')} "
            f"({listing.get('condition', '').lower()}) at {listing.get('place')}, available from "
            f"{listing.get('available_from', 'now')}. Interested? - sent via AgriAttribute AI")


def today_iso() -> str:
    return date.today().isoformat()
