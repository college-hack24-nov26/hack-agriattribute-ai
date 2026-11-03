"""
scrap_market_ui.py - Streamlit interface for the Farm Waste Market tab (see scrap_marketplace.py).
"""

import base64
import html as html_mod
import urllib.parse
from datetime import date
from typing import Any, Dict

import streamlit as st

from services import farm_store, geolocation_service, quick_sell_ui, scrap_marketplace as sm

_CONDITIONS = ["Fresh", "Slightly overripe", "Dry", "Wet / rotting"]
_RADII = {"Within 50 km": 50, "Within 100 km": 100, "Within 250 km": 250, "Within 500 km": 500, "Anywhere": None}


def _e(x: Any) -> str:
    return html_mod.escape(str(x if x is not None else ""))


def _badge(text: str, fg: str = "#047857", bg: str = "#ecfdf5", border: str = "#86efac") -> str:
    return (f"<span style='background:{bg};color:{fg};border:1px solid {border};border-radius:999px;padding:1px 9px;"
            f"font-size:.7rem;font-weight:800;'>{_e(text)}</span>")


def _wa(phone: str, text: str) -> str:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return f"https://wa.me/{digits}?text=" + urllib.parse.quote(text)


def _stats():
    listings = farm_store.select("scrap_listings")
    buyers = farm_store.select("scrap_buyers")
    enquiries = farm_store.select("scrap_inquiries")
    c = st.columns(3)
    for col, (n, label) in zip(c, [(sum(1 for r in listings if r.get("status") == "open"), "open listings"),
                                    (len(buyers), "registered buyers"), (len(enquiries), "enquiries sent")]):
        col.markdown(
            f"<div style='background:rgba(255,255,255,.85);border:1px solid rgba(6,78,59,.12);border-radius:16px;padding:10px 14px;text-align:center;'>"
            f"<div style='font-size:1.5rem;font-weight:900;color:#064e3b;'>{n}</div>"
            f"<div style='font-size:.75rem;font-weight:700;color:#4b6358;'>{label}</div></div>", unsafe_allow_html=True)


def _hero():
    st.markdown(
        """
        <div style="padding:4px 2px 10px;">
          <span style="background:#92400e;color:#fff;font-size:.72rem;font-weight:800;padding:3px 10px;border-radius:999px;letter-spacing:.05em;">NEW</span>
          <div style="font:700 2rem/1.15 var(--serif);color:var(--forest);letter-spacing:-.02em;margin:8px 0 4px;">Farm Waste Market</div>
          <div style="font-size:1rem;color:#334155;font-weight:600;line-height:1.5;">
            Turn culls and crop residue into income. List your waste with a photo (strawberry culls, sugarcane trash, cotton stalks ...),
            and get matched with buyers who actually take it, nearest first.
          </div>
        </div>""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# match cards
# ---------------------------------------------------------------------------
def _show_matches(listing: Dict[str, Any], key_prefix: str, radius_label: str = "Within 250 km", top: int = 6):
    buyers = farm_store.select("scrap_buyers")
    radius = _RADII.get(radius_label)
    matches = sm.match_buyers(listing, buyers, radius)
    cat = sm.WASTE_CATALOG.get(listing["waste_type"], {})
    if cat.get("tip"):
        st.info(f"{cat.get('emoji', '')} Handling tip: {cat['tip']}")
    if not matches:
        st.warning("No registered buyer for this waste type in that range yet. Widen the distance, or share the listing so buyers can find you.")
        return
    st.markdown(f"**{len(matches)} buyer(s) take {_e(listing['waste_type'])}** (best match first)")
    for m in matches[:top]:
        demo = _badge("DEMO", "#92400e", "#fffbeb", "#fcd34d") if m.get("is_demo") else _badge("REGISTERED")
        bar = int(m["score"])
        st.markdown(
            f"""<div style="background:rgba(255,255,255,.92);border:1px solid rgba(6,78,59,.14);border-radius:16px;padding:12px 14px;margin-top:8px;">
            <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:center;">
              <div style="font-weight:900;color:#064e3b;">{_e(m['name'])} {demo}</div>
              <div style="font-weight:900;color:#047857;">{m['score']:.0f}% match</div></div>
            <div style="font-size:.8rem;color:#475569;font-weight:600;">{_e(m.get('buyer_type'))} · {_e(m.get('place'))}</div>
            <div style="height:6px;background:#e2e8f0;border-radius:999px;margin:6px 0;"><div style="height:6px;width:{bar}%;background:linear-gradient(90deg,#10b981,#bef264);border-radius:999px;"></div></div>
            <div style="font-size:.8rem;color:#334155;">{_e(' · '.join(m['reasons']))}</div></div>""", unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("📨 Send enquiry", key=f"{key_prefix}_enq_{m['id']}", width="stretch"):
            sm.send_enquiry(listing["id"], m["id"], sm.default_enquiry_text(listing))
            st.toast(f"Enquiry saved for {m['name']}", icon="📨")
        if m.get("phone"):
            c2.link_button("💬 WhatsApp the buyer", _wa(m["phone"], sm.default_enquiry_text(listing)), width="stretch")
        else:
            c2.caption("Demo buyer: no real contact. Real buyers register in the 'I'm a buyer' tab." if m.get("is_demo") else "No phone on file.")


def _listing_card(r: Dict[str, Any], show_phone_btn: bool = False, key_prefix: str = "lc"):
    cat = sm.WASTE_CATALOG.get(r.get("waste_type"), {})
    c1, c2 = st.columns([1, 3])
    with c1:
        if r.get("photo_b64"):
            try:
                st.image(base64.b64decode(r["photo_b64"]), width="stretch")
            except Exception:
                st.markdown(f"<div style='font-size:3rem;text-align:center'>{cat.get('emoji', '♻️')}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div style='font-size:3rem;text-align:center'>{cat.get('emoji', '♻️')}</div>", unsafe_allow_html=True)
    with c2:
        ask = f" · asking Rs {float(r['price_expectation']):,.0f}/q" if r.get("price_expectation") else " · open to offers"
        st.markdown(
            f"**{_e(r.get('waste_type'))}** · {r.get('quantity')} {_e(r.get('unit'))} · {_e(r.get('condition'))}{ask}  \n"
            f"📍 {_e(r.get('place'))} · available {_e(r.get('available_from'))} · status: {_e(r.get('status'))}")
        if r.get("ai_summary"):
            st.caption("🤖 " + r["ai_summary"])
        if show_phone_btn and r.get("share_phone") and r.get("phone"):
            st.link_button("💬 Contact farmer on WhatsApp", _wa(r["phone"], f"Hello, I saw your {r.get('waste_type')} listing on AgriAttribute AI. Is it still available?"),
                           key=f"{key_prefix}_wa_{r['id']}")


# ---------------------------------------------------------------------------
# tabs
# ---------------------------------------------------------------------------
def _sell_tab(crop: str, lat: float, lon: float, place: str, state: str):
    st.markdown("#### 1 · Add a photo (optional, but buyers trust it)")
    up = st.file_uploader("Photo of your farm waste", type=["jpg", "jpeg", "png", "webp"], key="sm_photo")
    thumb = None
    ai_text = ""
    if up is not None:
        raw = up.getvalue()
        c1, c2 = st.columns([1, 2])
        c1.image(raw, width="stretch")
        try:
            thumb = sm.make_thumbnail_b64(raw)
        except Exception:
            thumb = None
        with c2:
            if st.button("🔍 Check this photo with AI", key="sm_ai_btn", width="stretch"):
                with st.spinner("Looking at your photo..."):
                    st.session_state["sm_ai"] = sm.analyze_photo(raw, up.type, st.session_state.get("sm_type"))
                    st.session_state["sm_ai_for"] = up.name
            ai = st.session_state.get("sm_ai")
            if ai and st.session_state.get("sm_ai_for") == up.name:
                if ai.get("error"):
                    st.warning(ai["error"])
                else:
                    dtype = ai.get("detected_type")
                    uses = ", ".join(ai.get("uses") or [])
                    ai_text = f"AI estimate: {dtype}, {ai.get('condition')}, grade {ai.get('quality_grade')}" + (f". Possible uses: {uses}" if uses else "")
                    st.markdown(f"**AI estimate:** {_e(dtype)} · {_e(ai.get('condition'))} · grade {_e(ai.get('quality_grade'))}")
                    if uses:
                        st.markdown(f"**Possible uses:** {_e(uses)}")
                    if ai.get("advice"):
                        st.caption(ai["advice"])
                    if ai.get("matches_claim") is False:
                        st.warning("The photo may not match the waste type you selected. Please double-check.")
                    if dtype in sm.WASTE_CATALOG and st.button(f"Use '{dtype}' as the waste type", key="sm_use_ai"):
                        st.session_state["sm_type"] = dtype
                        st.rerun()
                    st.caption("AI estimates can be wrong. You decide what to list.")

    st.markdown("#### 2 · Describe it")
    with st.form("sm_form", clear_on_submit=False):
        types = list(sm.WASTE_CATALOG.keys())
        f1, f2 = st.columns(2)
        wtype = f1.selectbox("What are you selling?", types, key="sm_type", format_func=lambda k: f"{sm.WASTE_CATALOG[k]['emoji']} {k}")
        cond = f2.selectbox("Condition", _CONDITIONS, key="sm_cond")
        q1, q2, q3 = st.columns([1.2, 1, 1.2])
        qty = q1.number_input("Quantity", min_value=0.1, value=100.0, step=10.0, key="sm_qty")
        unit = q2.selectbox("Unit", ["kg", "quintal", "tonne"], key="sm_unit")
        ask = q3.number_input("Your price, Rs per quintal (0 = open to offers)", min_value=0.0, value=0.0, step=50.0, key="sm_ask")
        d1, d2 = st.columns(2)
        avail = d1.date_input("Available from", value=date.today(), key="sm_date")
        where = d2.text_input("Where is it?", value=place, key="sm_place")
        n1, n2 = st.columns(2)
        name = n1.text_input("Your name", key="sm_name")
        phone = n2.text_input("Phone (for WhatsApp)", key="sm_phone", placeholder="10-digit mobile")
        share = st.checkbox("Share my phone with buyers who match", value=False, key="sm_share")
        notes = st.text_area("Anything buyers should know", key="sm_notes", height=70)
        go = st.form_submit_button("♻️ List my farm waste", type="primary", width="stretch")

    if go:
        if not name.strip():
            st.error("Please add your name so buyers know who to ask for.")
            return
        listing = sm.create_listing(
            farmer_name=name.strip(), phone=phone.strip(), share_phone=bool(share and phone.strip()),
            waste_type=wtype, quantity=float(qty), unit=unit, quantity_q=sm.to_quintal(float(qty), unit),
            condition=cond, available_from=avail.isoformat(), price_expectation=float(ask),
            lat=float(lat), lon=float(lon), place=where.strip() or place, state=state, notes=notes.strip(),
            photo_b64=thumb or "", ai_summary=ai_text,
        )
        st.session_state.setdefault("sm_my_ids", []).append(listing["id"])
        st.session_state["sm_last"] = listing
        st.success("Listed! Here are the buyers who take it.")

    last = st.session_state.get("sm_last")
    if last:
        st.markdown("#### 3 · Buyers for your listing")
        radius = st.select_slider("How far will you deliver?", options=list(_RADII.keys()), value="Within 250 km", key="sm_radius_sell")
        _show_matches(last, "sell", radius)


def _my_tab():
    ids = st.session_state.get("sm_my_ids", [])
    all_rows = farm_store.select("scrap_listings")
    mine = [r for r in all_rows if r["id"] in ids]
    st.markdown("#### Your listings")
    if not mine:
        st.info("You have not listed anything in this session yet. Use the 'Sell my farm waste' tab.")
    enquiries = farm_store.select("scrap_inquiries")
    for r in mine:
        with st.container(border=True):
            _listing_card(r, key_prefix="mine")
            n = sum(1 for q in enquiries if q.get("listing_id") == r["id"])
            c1, c2 = st.columns(2)
            c1.metric("Enquiries sent", n)
            if r.get("status") == "open" and c2.button("✅ Mark as sold", key=f"sold_{r['id']}", width="stretch"):
                farm_store.update("scrap_listings", r["id"], {"status": "sold"})
                st.rerun()
    st.markdown("#### All open listings near you")
    open_rows = [r for r in all_rows if r.get("status") == "open"][:12]
    if not open_rows:
        st.caption("No open listings yet.")
    for r in open_rows:
        with st.container(border=True):
            _listing_card(r, key_prefix="all")


def _buyer_tab(lat: float, lon: float, place: str):
    st.markdown("#### Register as a buyer")
    with st.form("sm_buyer_form"):
        b1, b2 = st.columns(2)
        bname = b1.text_input("Business / buyer name", key="sm_bname")
        btype = b2.selectbox("What kind of buyer?", list(sm.BUYER_TYPES.keys()), key="sm_btype")
        accepts = st.multiselect("Waste you buy", list(sm.WASTE_CATALOG.keys()), default=sm.BUYER_TYPES[btype], key="sm_baccepts")
        p1, p2, p3 = st.columns(3)
        minq = p1.number_input("Minimum lot (quintal)", min_value=0.0, value=5.0, step=1.0, key="sm_bmin")
        pmin = p2.number_input("Price from, Rs/q", min_value=0.0, value=200.0, step=50.0, key="sm_bpmin")
        pmax = p3.number_input("Price up to, Rs/q", min_value=0.0, value=600.0, step=50.0, key="sm_bpmax")
        l1, l2 = st.columns(2)
        bplace = l1.text_input("Town / village", value=place, key="sm_bplace")
        bphone = l2.text_input("Phone (WhatsApp)", key="sm_bphone")
        reg = st.form_submit_button("🏭 Register", type="primary", width="stretch")
    if reg:
        if not bname.strip() or not accepts:
            st.error("Add a name and at least one waste type.")
        else:
            blat, blon, bstate = lat, lon, ""
            found = geolocation_service.search_place(bplace) if bplace and bplace != place else []
            if found:
                blat, blon, bstate = found[0]["lat"], found[0]["lon"], found[0]["state"]
            row = sm.create_buyer(name=bname.strip(), buyer_type=btype, accepts=",".join(accepts), min_qty_q=float(minq),
                                  price_min=float(pmin), price_max=float(pmax), lat=float(blat), lon=float(blon),
                                  place=bplace.strip() or place, state=bstate, phone=bphone.strip())
            st.session_state["sm_my_buyer_id"] = row["id"]
            st.success(f"Registered {bname}. Farmers near you will now see you in their matches.")

    st.markdown("#### Browse listings")
    rows = [r for r in farm_store.select("scrap_listings") if r.get("status") == "open"]
    if not rows:
        st.info("No open listings yet.")
        return
    types = sorted({r["waste_type"] for r in rows})
    pick = st.multiselect("Filter by waste type", types, key="sm_bfilter")
    for r in [x for x in rows if not pick or x["waste_type"] in pick][:12]:
        with st.container(border=True):
            d = sm.haversine_km(lat, lon, float(r["lat"]), float(r["lon"])) if r.get("lat") else 0
            _listing_card(r, show_phone_btn=True, key_prefix="buy")
            st.caption(f"About {d:.0f} km from you (using your farm location)")
            bid = st.session_state.get("sm_my_buyer_id")
            if bid and st.button("📨 I'm interested", key=f"int_{r['id']}"):
                sm.send_enquiry(r["id"], bid, "A registered buyer is interested in your listing.")
                st.toast("Interest sent to the farmer", icon="📨")


# ---------------------------------------------------------------------------
def render_scrap_market_tab(lang: str, crop: str, lat: float, lon: float, place: str, state: str = ""):
    sm.ensure_demo_buyers()
    _hero()
    _stats()
    st.caption(f"Storage: {'cloud (Supabase) with local backup' if farm_store.backend() == 'supabase' else 'local file (set up Supabase for cloud sync)'}")
    st.caption("Looking for companies that buy raw material straight from farmers, region by region? Open COMPANY NEEDS in the navbar.")
    t1, t2, t3 = st.tabs(["Sell my farm waste", "My listings & marketplace", "I'm a buyer"])
    with t1:
        quick_sell_ui.render_quick_waste(lat, lon, place, state)
        with st.expander("Add a photo, condition and your price (detailed listing)"):
            _sell_tab(crop, lat, lon, place, state)
    with t2:
        _my_tab()
    with t3:
        _buyer_tab(lat, lon, place)
