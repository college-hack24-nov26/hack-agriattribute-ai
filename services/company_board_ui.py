"""
company_board_ui.py - "Company Needs": food and industrial companies post the raw material they need,
farmers in the same region offer to supply it directly (see direct_demand.py for the engine).

Honesty notes
  * The platform introduces buyer and seller. It does not hold money, guarantee payment or verify companies.
    Companies are UNVERIFIED until checked; the sample companies are fictional and marked DEMO.
  * Big brands can join by posting through the company portal. None is implied to have done so.
"""

import html as html_mod
import urllib.parse
from collections import defaultdict
from typing import Any, Dict, List, Optional

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from services import direct_demand as dd, farm_store, geolocation_service, quick_sell_ui
from services.scrap_marketplace import haversine_km

_SORTS = ["Nearest first", "Highest price first", "Biggest need first"]


def _e(x: Any) -> str:
    return html_mod.escape(str(x if x is not None else ""))


def _badge(text: str, fg: str, bg: str) -> str:
    return f"<span class='aa-chip' style='color:{fg};background:{bg};'>{_e(text)}</span>"


def _wa(phone: str, text: str) -> str:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return f"https://wa.me/{digits}?text=" + urllib.parse.quote(text)


def _mandi_reference(crop_key: str) -> Optional[float]:
    """Local mandi price (a demo file in this build) for the same crop, for comparison."""
    if crop_key not in dd.CROP_KEYS:
        return None
    try:
        from services import agmarknet_engine
        info = agmarknet_engine.get_mandi_intelligence_for_crop(crop_key, True)
        return float(info.get("latest_price")) if info.get("latest_price") else None
    except Exception:
        return None


def _cnt(n: float, unit: str = "") -> str:
    return f"<span class='cnt' style='--to:{int(round(n))}' data-unit='{unit}'></span>"


# ---------------------------------------------------------------------------
# hero
# ---------------------------------------------------------------------------
def _hero(open_d: List[Dict[str, Any]]):
    need = sum(d["remaining_q"] for d in open_d)
    companies = len({d["company"] for d in open_d})
    regions = len({d["region"] for d in open_d})
    kpis = [(len(open_d), "", "open requirements"), (companies, "", "companies buying"),
            (regions, "", "farming regions"), (need, " q", "still needed")]
    cells = "".join(f"<div class='cb-kpi'><b>{_cnt(v, u)}</b><span>{lbl}</span></div>" for v, u, lbl in kpis)
    st.markdown(
        "<div class='cb-hero'>"
        "<div class='cb-eyebrow'>COMPANY NEEDS · REGION WISE</div>"
        "<div class='cb-title'>Companies post what they need.<br>You supply them directly.</div>"
        "<div class='cb-sub'>Chips, ketchup, atta, oil, feed and more: see who is buying your crop in your region, at what price, "
        "for how much, and offer straight to them. No commission agent in between.</div>"
        "<div class='cb-line' aria-hidden='true'><span>🌾</span><i></i><em>🚚</em><i></i><span>🏭</span></div>"
        f"<div class='cb-kpis'>{cells}</div></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# map + supply vs demand
# ---------------------------------------------------------------------------
def _map(rows: List[Dict[str, Any]], lat: float, lon: float, zoomed: bool):
    if not rows:
        st.info("Nothing to show on the map for this filter.")
        return
    data = {"lat": [float(d["lat"]) for d in rows], "lon": [float(d["lon"]) for d in rows],
            "remaining": [d["remaining_q"] for d in rows], "company": [d["company"] for d in rows],
            "crop": [d.get("item") for d in rows], "price": [float(d.get("price_offer") or 0) for d in rows],
            "place": [d.get("place") for d in rows]}
    fig = px.scatter_map(data, lat="lat", lon="lon", size="remaining", color="crop", hover_name="company",
                         hover_data={"crop": False, "place": True, "remaining": ":,.0f", "price": ":,.0f", "lat": False, "lon": False},
                         size_max=34, zoom=7 if zoomed else 4.1, center={"lat": lat if zoomed else 22.0, "lon": lon if zoomed else 79.0},
                         map_style="open-street-map", height=400, color_discrete_sequence=px.colors.qualitative.Safe)
    fig.add_trace(go.Scattermap(lat=[lat], lon=[lon], mode="markers", marker=dict(size=16, color="#064e3b"), name="Your farm",
                                hovertemplate="Your farm<extra></extra>"))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", y=-0.02, font=dict(size=10)),
                      paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, width="stretch")


def _supply_vs_demand(all_open: List[Dict[str, Any]]):
    offers = farm_store.select("demand_offers")
    region_by_demand = {d["id"]: d["region"] for d in all_open}
    need: Dict[str, float] = defaultdict(float)
    offered: Dict[str, float] = defaultdict(float)
    for d in all_open:
        need[d["region"]] += d["remaining_q"]
    for o in offers:
        if o.get("status") in ("offered", "accepted") and o.get("demand_id") in region_by_demand:
            offered[region_by_demand[o["demand_id"]]] += float(o.get("qty_q") or 0)
    regions = sorted(need, key=lambda r: -need[r])
    short = [r.split(" (")[0].replace(" & ", " &\n") for r in regions]
    fig = go.Figure()
    fig.add_bar(x=short, y=[need[r] for r in regions], name="Still needed (q)", marker_color="#10b981")
    fig.add_bar(x=short, y=[offered[r] for r in regions], name="Offered by farmers (q)", marker_color="#f59e0b")
    fig.update_layout(barmode="group", height=400, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      title=dict(text="Supply vs demand by region", font=dict(size=14)), legend=dict(orientation="h", y=-0.2),
                      font=dict(family="Plus Jakarta Sans, Inter, sans-serif", size=11))
    st.plotly_chart(fig, width="stretch")
    st.caption("A tall green bar with no gold beside it is a region where companies need more supply than farmers have offered yet.")


# ---------------------------------------------------------------------------
# requirement card + offer form
# ---------------------------------------------------------------------------
def _card(d: Dict[str, Any], farmer: Dict[str, Any]):
    need, filled = float(d["qty_needed_q"]), float(d.get("qty_filled_q") or 0)
    pct = int(100 * filled / need) if need else 0
    if d.get("is_demo"):
        badge = _badge("DEMO company", "#92400e", "#fef3c7")
    elif d.get("verified"):
        badge = _badge("VERIFIED", "#065f46", "#d1fae5")
    else:
        badge = _badge("UNVERIFIED: check before you deliver", "#9a3412", "#ffedd5")
    price = float(d.get("price_offer") or 0)
    ref = _mandi_reference(d.get("crop_key", ""))
    compare = ""
    if ref and price:
        diff = price - ref
        compare = (f"<div class='aa-sub'>Local mandi price (demo file): ₹{ref:,.0f}/q. This offer is "
                   f"<b>₹{abs(diff):,.0f} {'above' if diff >= 0 else 'below'}</b> it, before mandi fees and transport to the mandi.</div>")
    st.markdown(
        f"<div class='aa-card' style='margin-top:10px;'>"
        f"<div style='display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap;align-items:flex-start;'>"
        f"<div><div class='aa-mid'>{_e(d['company'])}</div><div class='aa-fine' style='margin:0;'>{_e(d.get('company_type'))}</div></div>"
        f"<div class='aa-hero' style='font-size:1.7rem;text-align:right;'>₹{price:,.0f}<span style='font-size:.8rem;color:var(--muted);font-weight:600;'> /q</span></div></div>"
        f"<div style='margin:6px 0;'>{badge} {_badge(d['region'].split(' (')[0], '#065f46', '#d1fae5')}</div>"
        f"<div><b>Needs:</b> {_e(d.get('item'))} · <b>{need:,.0f} q</b> by {_e(d.get('deadline'))}</div>"
        f"<div class='aa-sub'>Quality: {_e(d.get('specs'))}</div>"
        f"<div class='aa-sub'>Deliver to {_e(d.get('place'))}, {d['distance_km']:.0f} km from you.</div>"
        f"<div class='aa-sub'>Terms: {_e(d.get('terms'))}</div>{compare}"
        f"<div style='height:8px;background:#d1fae5;border-radius:999px;margin:10px 0 4px;overflow:hidden;'>"
        f"<div style='height:8px;width:{pct}%;background:linear-gradient(90deg,#10b981,#bef264);border-radius:999px;'></div></div>"
        f"<div class='aa-fine'>{filled:,.0f} of {need:,.0f} q promised · {d['remaining_q']:,.0f} q still needed</div></div>",
        unsafe_allow_html=True)
    with st.expander("Offer to supply"):
        with st.form(f"dd_offer_{d['id']}"):
            c1, c2 = st.columns(2)
            qty = c1.number_input("Quantity you can supply (quintal)", min_value=0.5, max_value=float(d["remaining_q"]),
                                  value=float(min(10.0, d["remaining_q"])), step=1.0, key=f"dd_q_{d['id']}")
            ask = c2.number_input("Your price, ₹ per quintal", min_value=0.0, value=price, step=50.0, key=f"dd_p_{d['id']}")
            n1, n2 = st.columns(2)
            name = n1.text_input("Your name", value=farmer.get("name", ""), key=f"dd_n_{d['id']}")
            phone = n2.text_input("Phone (WhatsApp)", value=farmer.get("phone", ""), key=f"dd_ph_{d['id']}")
            msg = st.text_area("Anything the company should know (variety, harvest date, moisture)", key=f"dd_m_{d['id']}", height=60)
            send = st.form_submit_button("Send my offer", type="primary", width="stretch")
        if send:
            if not name.strip():
                st.error("Please add your name.")
            else:
                dd.make_offer(d, name.strip(), phone.strip(), qty, ask, farmer["place"], msg.strip())
                st.session_state["dd_farmer"] = {"name": name.strip(), "phone": phone.strip()}
                st.session_state.setdefault("dd_my_offers_by", []).append(name.strip())
                st.success("Offer sent. The company will accept or decline it; the status shows under 'Your offers' below.")
        if d.get("contact_phone"):
            st.link_button("Message the company on WhatsApp", _wa(d["contact_phone"], f"Hello, I can supply {d.get('item')} for your requirement on AgriAttribute AI."))
        else:
            st.caption("This company has not shared a phone number; use the offer form.")


# ---------------------------------------------------------------------------
# company portal
# ---------------------------------------------------------------------------
def _company_portal(place: str, lat: float, lon: float, state: str, region_coords: Dict[str, Dict[str, float]]):
    st.markdown("### For companies: post what you need")
    st.caption("Food brands, mills and processors can list a requirement and see farmers' offers from the region. Payment and contract terms are "
               "between you and the farmer; the platform does not hold money.")
    with st.form("dd_post_form"):
        a1, a2 = st.columns(2)
        company = a1.text_input("Company name", key="dd_company")
        ctype = a2.selectbox("Type of company", dd.COMPANY_TYPES, key="dd_ctype")
        b1, b2 = st.columns(2)
        category = b1.selectbox("What do you need?", dd.CATEGORIES, key="dd_cat")
        keys = dd.CROP_KEYS if category == dd.CATEGORIES[0] else dd.waste_keys()
        crop_key = b2.selectbox("Crop or waste type", keys, key="dd_cropkey")
        item = st.text_input("Exact requirement (grade)", placeholder="e.g. Potato, chipping grade", key="dd_item")
        specs = st.text_input("Quality rules", placeholder="e.g. 55-75 mm, low sugar, no sprouts", key="dd_specs")
        c1, c2, c3 = st.columns(3)
        qty = c1.number_input("Quantity needed (quintal)", min_value=1.0, value=500.0, step=10.0, key="dd_qty")
        price = c2.number_input("Price you offer, ₹ per quintal", min_value=1.0, value=2500.0, step=50.0, key="dd_price")
        deadline = c3.text_input("Needed by", placeholder="e.g. 30 Nov", key="dd_deadline")
        d1, d2 = st.columns(2)
        where = d1.text_input("Delivery point (town)", value=place, key="dd_where")
        phone = d2.text_input("Contact phone (optional)", key="dd_cphone")
        e1, e2, e3 = st.columns(3)
        contract = e1.selectbox("Buying style", ["Spot purchase", "Fixed-price contract for the season", "Recurring monthly supply"], key="dd_contract")
        advance = e2.number_input("Advance to farmer (%)", min_value=0, max_value=50, value=0, step=5, key="dd_adv")
        transport = e3.selectbox("Transport", ["Company arranges pickup", "Farmer delivers", "Shared"], key="dd_transport")
        terms_extra = st.text_input("Payment and other terms", placeholder="e.g. payment in 7 days after weighing", key="dd_terms")
        go_btn = st.form_submit_button("Post requirement", type="primary", width="stretch")
    if go_btn:
        if not company.strip() or not item.strip():
            st.error("Company name and the exact requirement are needed.")
        else:
            plat, plon, pstate = lat, lon, state
            found = geolocation_service.search_place(where) if where and where != place else []
            if found:
                plat, plon, pstate = found[0]["lat"], found[0]["lon"], found[0]["state"]
            terms = f"{contract}; advance {advance}%; transport: {transport.lower()}" + (f"; {terms_extra.strip()}" if terms_extra.strip() else "")
            row = dd.post_demand(company=company.strip(), company_type=ctype, category=category, item=item.strip(),
                                 crop_key=crop_key, specs=specs.strip(), qty_needed_q=float(qty), price_offer=float(price),
                                 lat=float(plat), lon=float(plon), place=where.strip() or place, state=pstate,
                                 deadline=deadline.strip(), terms=terms, contact_phone=phone.strip())
            st.session_state.setdefault("dd_my_demands", []).append(row["id"])
            st.session_state["dd_flash"] = ("Posted. Farmers in "
                                            f"{dd.region_of(row, region_coords).split(' (')[0]} can now see it. It is marked UNVERIFIED until our team checks the company.")
            st.rerun()

    mine = [d for d in farm_store.select("buyer_demands") if d["id"] in st.session_state.get("dd_my_demands", [])]
    if mine:
        st.markdown("#### Your requirements and incoming offers")
    for d in mine:
        st.markdown(f"**{_e(d['company'])}** wants {_e(d['item'])}: {float(d.get('qty_filled_q') or 0):,.0f} of {float(d['qty_needed_q']):,.0f} q filled.")
        for o in dd.offers_for(d["id"]):
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.markdown(f"{_e(o['farmer_name'])} ({_e(o.get('place'))}): {o['qty_q']:g} q at ₹{float(o['price_ask']):,.0f}/q [{o['status']}]"
                        + (f" - {_e(o.get('message'))}" if o.get("message") else ""))
            if o["status"] == "offered":
                if c2.button("Accept", key=f"dd_acc_{o['id']}", width="stretch"):
                    dd.respond_to_offer(o, True)
                    st.rerun()
                if c3.button("Decline", key=f"dd_dec_{o['id']}", width="stretch"):
                    dd.respond_to_offer(o, False)
                    st.rerun()
            elif o.get("phone"):
                c2.link_button("WhatsApp", _wa(o["phone"], f"Hello {o['farmer_name']}, we accepted your offer on AgriAttribute AI."))


# ---------------------------------------------------------------------------
def render_company_board(crop: str, lat: float, lon: float, place: str, state: str, region: str,
                         region_coords: Dict[str, Dict[str, float]]):
    dd.ensure_demo_demands()
    if st.session_state.get("dd_flash"):
        st.success(st.session_state.pop("dd_flash"))

    all_d = farm_store.select("buyer_demands")
    open_all: List[Dict[str, Any]] = []
    for d in all_d:
        if d.get("status") != "open" or dd.remaining_q(d) <= 0:
            continue
        try:
            dist = haversine_km(float(lat), float(lon), float(d["lat"]), float(d["lon"]))
        except (TypeError, ValueError, KeyError):
            continue
        open_all.append({**d, "distance_km": dist, "remaining_q": dd.remaining_q(d), "region": dd.region_of(d, region_coords)})

    _hero(open_all)
    quick_sell_ui.render_quick_crop(crop, lat, lon, place, region_coords)
    st.markdown("#### Or browse every requirement")

    my_region = region
    f1, f2, f3 = st.columns([1.4, 1.4, 1])
    region_opts = [f"My region: {my_region.split(' (')[0]}", "All India"] + [r for r in region_coords if r != my_region]
    pick = f1.selectbox("Region", region_opts, key="cb_region")
    crops = sorted({d.get("crop_key") or d.get("item") for d in open_all})
    picked_crops = f2.multiselect("Crop", crops, key="cb_crops", placeholder="All crops")
    sort = f3.selectbox("Sort", _SORTS, key="cb_sort")

    if pick.startswith("My region"):
        sel_region: Optional[str] = my_region
    elif pick == "All India":
        sel_region = None
    else:
        sel_region = pick
    rows = [d for d in open_all if (sel_region is None or d["region"] == sel_region) and (not picked_crops or (d.get("crop_key") or d.get("item")) in picked_crops)]
    key_fn = {"Nearest first": lambda d: d["distance_km"], "Highest price first": lambda d: -float(d.get("price_offer") or 0),
              "Biggest need first": lambda d: -d["remaining_q"]}[sort]
    rows.sort(key=key_fn)

    m1, m2 = st.columns([1.5, 1])
    with m1:
        _map(rows, lat, lon, zoomed=sel_region is not None)
    with m2:
        _supply_vs_demand(open_all)

    if not rows:
        st.info("No open requirement matches these filters. Try 'All India' or clear the crop filter, or ask companies in your region to post here.")
    farmer = {"name": st.session_state.get("dd_farmer", {}).get("name", ""), "phone": st.session_state.get("dd_farmer", {}).get("phone", ""), "place": place}
    st.markdown(f"#### {len(rows)} requirement{'s' if len(rows) != 1 else ''} " + (f"in {sel_region.split(' (')[0]}" if sel_region else "across India"))
    cols = st.columns(2)
    for i, d in enumerate(rows[:12]):
        with cols[i % 2]:
            _card(d, farmer)

    st.markdown("#### Your offers")
    names = {n for n in st.session_state.get("dd_my_offers_by", [])}
    offers = [o for o in farm_store.select("demand_offers") if o.get("farmer_name") in names]
    demands = {d["id"]: d for d in all_d}
    if not offers:
        st.caption("You have not sent any offer in this session.")
    for o in offers[:15]:
        d = demands.get(o["demand_id"], {})
        status = {"offered": "waiting for the company", "accepted": "accepted", "declined": "declined"}.get(o["status"], o["status"])
        st.markdown(f"**{_e(d.get('company', 'Company'))}**: {o['qty_q']:g} q at ₹{float(o['price_ask']):,.0f}/q, {status}.")

    st.markdown("---")
    _company_portal(place, lat, lon, state, region_coords)
    st.caption("Big brands such as national food and snack companies can join by posting here. The companies shown are fictional samples marked DEMO; "
               "none of them represents a real company.")
