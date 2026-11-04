"""
quick_sell_ui.py - selling in a few taps.

The full boards (Company Needs, Farm Waste Market) have filters, maps and long forms. Most farmers just want to say
"I have 25 quintal of soybean" and see who pays what. These two panels do exactly that:

  render_quick_crop()   pick a crop, tap a quantity, add a phone number -> the best-paying companies near you, with one
                        "Offer" button each and an "Offer to all" button
  render_quick_waste()  pick the waste, tap a quantity, add a phone number -> the buyers that take it, with one
                        "Send enquiry" button each

All text goes through the app-wide translator (services/i18n.py), so the panels follow the chosen language.
Both panels are fragments: a tap re-runs only the panel, not the whole app.
"""

import html as html_mod
import urllib.parse
from typing import Any, Dict

import streamlit as st

from services import direct_demand as dd, farm_store
from services import scrap_marketplace as sm

_EMOJI = {"Soybean": "🫘", "Wheat": "🌾", "Tomato": "🍅", "Onion": "🧅", "Potato": "🥔", "Maize": "🌽", "Cotton": "☁️",
          "Rice (Paddy)": "🍚", "Sugarcane": "🎋", "Groundnut (Peanut)": "🥜", "Mustard / Rapeseed": "🌼",
          "Chickpea (Gram / Chana)": "🫛", "Tur / Pigeon Pea (Arhar)": "🫛"}
_QTY_CHIPS = [10, 25, 50, 100, 250]


def _e(x: Any) -> str:
    return html_mod.escape(str(x if x is not None else ""))


def _wa(phone: str, text: str) -> str:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return f"https://wa.me/{digits}?text=" + urllib.parse.quote(text)


def _contact_fields(prefix: str):
    """Name and phone, remembered across the quick panels."""
    saved = st.session_state.get("dd_farmer", {})
    c1, c2 = st.columns(2)
    name = c1.text_input("Your name", value=saved.get("name", ""), key=f"{prefix}_name")
    phone = c2.text_input("Phone (WhatsApp)", value=saved.get("phone", ""), key=f"{prefix}_phone", placeholder="10-digit mobile")
    return name.strip(), phone.strip()


def _qty_picker(key: str, default: int, unit: str):
    """Quick quantity chips that fill a number box, so one tap or a typed number both work."""
    def pick():
        v = st.session_state.get(f"{key}_chip")
        if v:
            st.session_state[key] = int(v)

    st.pills("How much?", options=_QTY_CHIPS, format_func=lambda q: f"{q} {unit}", key=f"{key}_chip", on_change=pick)
    return st.number_input(f"Or type the quantity ({unit})", min_value=1, max_value=100000, value=default, step=5, key=key)


# ---------------------------------------------------------------------------
# crop -> companies
# ---------------------------------------------------------------------------
@st.fragment
def render_quick_crop(crop: str, lat: float, lon: float, place: str, region_coords: Dict[str, Dict[str, float]]):
    dd.ensure_demo_demands()
    all_d = farm_store.select("buyer_demands")
    ranked = dd.rank_demands(all_d, None, lat, lon, None)
    keys = sorted({d["crop_key"] for d in ranked if d.get("crop_key") in _EMOJI})
    if not keys:
        st.info("No company is buying right now. Check back soon, or open the full board below.")
        return
    mine = next((k for k in keys if k.split(" (")[0].lower() == crop.split(" (")[0].lower()), keys[0])
    st.markdown("<div class='aa-card aa-card-accent'><div class='aa-eyebrow'>SELL IN 3 TAPS</div>"
                "<div class='aa-headline'>I want to sell my crop to a company</div>"
                "<div class='aa-sub'>Pick your crop, tap how much you have, add your phone. You will see who pays what, nearest first.</div></div>",
                unsafe_allow_html=True)
    pick = st.pills("What do you want to sell?", options=keys, format_func=lambda k: f"{_EMOJI.get(k, '🌱')} {k.split(' (')[0]}",
                    key="qs_crop", default=mine)
    qty = _qty_picker("qs_qty", 25, "quintal")
    name, phone = _contact_fields("qs_c")
    if not pick:
        return

    options = [d for d in dd.rank_demands(all_d, pick, lat, lon, 800)]
    if not options:
        st.warning("No company is buying this crop within 800 km yet. Try another crop, or open the full board below.")
        return
    options.sort(key=lambda d: (-float(d.get("price_offer") or 0), d["distance_km"]))
    st.markdown(f"**{len(options)} compan{'y' if len(options) == 1 else 'ies'} buying {_e(pick.split(' (')[0])}**, best price first")
    for d in options[:4]:
        take = min(float(qty), d["remaining_q"])
        region = dd.region_of(d, region_coords).split(" (")[0]
        c1, c2, c3 = st.columns([3.2, 1.4, 1.6])
        c1.markdown(f"**{_e(d['company'])}**{' · DEMO' if d.get('is_demo') else ''}  \n"
                    f"<span style='color:#4b6358;font-size:.85rem'>{_e(d.get('place'))}, {_e(region)} · {d['distance_km']:.0f} km · by {_e(d.get('deadline'))}</span>",
                    unsafe_allow_html=True)
        c2.markdown(f"<div class='aa-mid' style='margin:0;'>₹{float(d.get('price_offer') or 0):,.0f}<span style='font-size:.75rem;color:#4b6358;'> /q</span></div>",
                    unsafe_allow_html=True)
        if c3.button(f"Offer {take:,.0f} q", key=f"qs_offer_{d['id']}", type="primary", width="stretch"):
            if not name:
                st.warning("Add your name above so the company knows who is offering.")
            else:
                dd.make_offer(d, name, phone, take, float(d.get("price_offer") or 0), place, "Quick offer from the farmer at the company's price")
                st.session_state["dd_farmer"] = {"name": name, "phone": phone}
                st.session_state.setdefault("dd_my_offers_by", []).append(name)
                st.toast(f"Offer sent to {d['company']}", icon="✅")
    top = options[:4]
    if len(top) > 1 and st.button(f"Offer {qty} q to all {len(top)} companies above", key="qs_offer_all", width="stretch"):
        if not name:
            st.warning("Add your name above so the companies know who is offering.")
        else:
            for d in top:
                dd.make_offer(d, name, phone, min(float(qty), d["remaining_q"]), float(d.get("price_offer") or 0), place, "Quick offer from the farmer")
            st.session_state["dd_farmer"] = {"name": name, "phone": phone}
            st.session_state.setdefault("dd_my_offers_by", []).append(name)
            st.success(f"Sent to {len(top)} companies. Each will accept or decline; the status shows under 'Your offers' on this page.")
    mine_offers = [o for o in farm_store.select("demand_offers") if o.get("farmer_name") == name] if name else []
    if mine_offers:
        accepted = sum(1 for o in mine_offers if o["status"] == "accepted")
        st.caption(f"Your offers so far: {len(mine_offers)} sent, {accepted} accepted.")


# ---------------------------------------------------------------------------
# waste -> buyers
# ---------------------------------------------------------------------------
@st.fragment
def render_quick_waste(lat: float, lon: float, place: str, state: str):
    sm.ensure_demo_buyers()
    st.markdown("<div class='aa-card aa-card-accent'><div class='aa-eyebrow'>SELL IN 3 TAPS</div>"
                "<div class='aa-headline'>I have farm waste to sell</div>"
                "<div class='aa-sub'>Pick what it is, tap how much, add your phone. You will see buyers who take it, nearest first. "
                "Add a photo and more details below if you want.</div></div>", unsafe_allow_html=True)
    types = list(sm.WASTE_CATALOG.keys())
    wtype = st.selectbox("What is it?", types, key="qw_type", format_func=lambda k: f"{sm.WASTE_CATALOG[k]['emoji']} {k}")
    qty = _qty_picker("qw_qty", 100, "kg")
    name, phone = _contact_fields("qw")
    if st.button("Find buyers near me", key="qw_go", type="primary", width="stretch"):
        if not name:
            st.warning("Add your name so buyers know who to ask for.")
        else:
            listing = sm.create_listing(
                farmer_name=name, phone=phone, share_phone=bool(phone), waste_type=wtype, quantity=float(qty), unit="kg",
                quantity_q=sm.to_quintal(float(qty), "kg"), condition="Fresh", available_from=sm.today_iso(), price_expectation=0.0,
                lat=float(lat), lon=float(lon), place=place, state=state, notes="", photo_b64="", ai_summary="")
            st.session_state.setdefault("sm_my_ids", []).append(listing["id"])
            st.session_state["qw_last"] = listing
            st.session_state["dd_farmer"] = {"name": name, "phone": phone}
    last = st.session_state.get("qw_last")
    if not last:
        return
    matches = sm.match_buyers(last, farm_store.select("scrap_buyers"), 300)
    st.markdown(f"**{len(matches)} buyer{'s' if len(matches) != 1 else ''} take {_e(last['waste_type'])}** near you")
    if not matches:
        st.info("No buyer for this waste within 300 km yet. Your listing is saved, so buyers who register later can find it.")
    for m in matches[:4]:
        c1, c2 = st.columns([3.4, 1.6])
        c1.markdown(f"**{_e(m['name'])}**{' · DEMO' if m.get('is_demo') else ''}  \n"
                    f"<span style='color:#4b6358;font-size:.85rem'>{_e(m.get('buyer_type'))} · {m['distance_km']:.0f} km · "
                    f"pays ₹{float(m.get('price_min') or 0):,.0f}-{float(m.get('price_max') or 0):,.0f} /q</span>", unsafe_allow_html=True)
        if c2.button("Send enquiry", key=f"qw_enq_{m['id']}", width="stretch"):
            sm.send_enquiry(last["id"], m["id"], sm.default_enquiry_text(last))
            st.toast(f"Enquiry saved for {m['name']}", icon="📨")
        if m.get("phone"):
            c2.link_button("WhatsApp", _wa(m["phone"], sm.default_enquiry_text(last)), width="stretch")
