"""
today_ui.py - the home screen as a bento dashboard: one decision, one number, live gauges, where the crop is
in its season, the forecast, and an honest trust strip.

Everything shown here is computed elsewhere (field context, simulator, river watch, market); this module only
chooses what matters today and says it in plain words. Styles live in assets/theme.css (.bento, .gcard, .journey ...).
"""

import html as html_mod
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from services import farm_store, sources


def _e(x: Any) -> str:
    return html_mod.escape(str(x if x is not None else ""))


def _cnt(n: float, unit: str = "") -> str:
    return f"<span class='cnt' style='--to:{int(round(n))}' data-unit='{unit}'></span>"


# ---------------------------------------------------------------------------
# pieces (each returns an HTML string for the bento grid)
# ---------------------------------------------------------------------------
def _decision(ctx: Dict[str, Any]) -> str:
    ready = ctx["readiness"] >= 70
    product, crop = ctx["product"], ctx["crop"]
    headline = f"Good day to apply {product} on your {crop.lower()}" if ready else f"Better to wait before applying {product}"
    sub = ("Conditions on your farm favour a response today." if ready
           else "Something on your farm is working against a good response. See the reasons below.")
    wind = ctx.get("wind_kmh")
    reasons: List[str] = []
    if wind is not None:
        reasons.append(f"Wind is {wind:.0f} km/h: " + ("calm enough to spray without drift." if wind < 15 else "too strong; wait for it to drop below 15 km/h."))
    for f in ctx.get("favorable", [])[:2]:
        reasons.append(f"{f['dimension']}: {f['condition']}")
    for f in ctx.get("limiting", [])[:2]:
        reasons.append(f"Watch out - {f['dimension']}: {f['condition']}")
    ring = (f"<div class='ring' style='--p:{int(ctx['readiness'])}' title='Readiness score'><svg viewBox='0 0 100 100'>"
            "<defs><linearGradient id='ringg' x1='0' y1='0' x2='1' y2='1'><stop offset='0' stop-color='#10b981'/><stop offset='1' stop-color='#bef264'/></linearGradient></defs>"
            "<circle class='trk' cx='50' cy='50' r='40'/><circle class='bar' cx='50' cy='50' r='40'/></svg>"
            f"<b>{int(ctx['readiness'])}</b></div>")
    return ("<div class='aa-card b-8'><div style='display:flex;gap:14px;justify-content:space-between;align-items:flex-start;'>"
            f"<div><div class='aa-eyebrow'>TODAY'S DECISION</div><div class='aa-headline'>{_e(headline)}</div><div class='aa-sub'>{_e(sub)}</div></div>"
            f"<div style='text-align:center;'>{ring}<div class='aa-fine' style='margin-top:2px;'>readiness</div></div></div>"
            + "".join(f"<div class='aa-reason'>{_e(r)}</div>" for r in reasons) + "</div>")


def _profit(ctx: Dict[str, Any]) -> str:
    sign = "+" if ctx["net_profit"] >= 0 else "-"
    return ("<div class='aa-card aa-card-accent b-4'><div class='aa-eyebrow'>EXPECTED EXTRA PROFIT</div>"
            f"<div class='bigcash'>{sign}₹{_cnt(abs(ctx['net_profit']))}</div>"
            "<div class='aa-sub'>per acre from the biological, after what it costs.</div>"
            f"<div class='aa-sub'>ROI {ctx['roi_pct']:+.0f}% on input cost · lift {ctx['yield_delta']:+.2f} q/acre</div>"
            f"<div class='aa-fine'>{_e(ctx['caveat'])}</div></div>")


def _gauge(label: str, value_html: str, frac: float, color: str, sub: str) -> str:
    frac = max(0.02, min(1.0, frac))
    return (f"<div class='gcard b-3'><div class='gl'>{label}</div>"
            f"<svg class='gauge' viewBox='0 0 100 58' aria-hidden='true'><path class='gtrk' d='M10 50 A40 40 0 0 1 90 50'/>"
            f"<path class='gbar' d='M10 50 A40 40 0 0 1 90 50' style='--f:{frac:.3f};--c:{color}'/></svg>"
            f"<div class='gv'>{value_html}</div><div class='gs'>{_e(sub)}</div></div>")


def _gauges(ctx: Dict[str, Any]) -> str:
    out = []
    t = ctx.get("temp_c")
    if t is not None:
        col = "#10b981" if t <= 32 else ("#f59e0b" if t <= 36 else "#ef4444")
        out.append(_gauge("TEMPERATURE", _cnt(t, "°C"), (t - 5) / 40.0, col,
                          "comfortable for most crops" if t <= 32 else ("getting hot" if t <= 36 else "heat stress risk")))
    h = ctx.get("humidity")
    if h is not None:
        out.append(_gauge("HUMIDITY", _cnt(h, "%"), h / 100.0, "#38bdf8", "disease risk is higher above 85%" if h < 85 else "high: watch for fungal disease"))
    w = ctx.get("wind_kmh")
    if w is not None:
        col = "#10b981" if w < 15 else ("#f59e0b" if w < 25 else "#ef4444")
        out.append(_gauge("WIND", _cnt(w, " km/h"), w / 40.0, col, "good to spray" if w < 15 else "spray drift risk"))
    r = ctx.get("rain_prob")
    if r is not None:
        out.append(_gauge("RAIN TOMORROW", _cnt(r, "%"), r / 100.0, "#6366f1", "plan irrigation and spraying around it" if r >= 40 else "mostly dry"))
    return "".join(out)


_STAGES = [("Sowing", "🌰"), ("Germination", "🌱"), ("Growing", "🌿"), ("Flowering", "🌼"), ("Filling", "🫛"), ("Harvest", "🌾")]


def _stage_index(stage: str) -> int:
    t = (stage or "").lower()
    if any(k in t for k in ("harvest", "matur", "ripen")):
        return 5
    if "flower" in t or "anthesis" in t or "heading" in t:
        return 3
    if any(k in t for k in ("fill", "pod", "grain", "boll", "fruit", "bulb", "tuber")):
        return 4
    if any(k in t for k in ("veget", "tiller", "branch", "grow", "canopy", "elong")):
        return 2
    if any(k in t for k in ("germ", "emerg", "seedling")):
        return 1
    if "sow" in t:
        return 0
    return 3


def _journey(ctx: Dict[str, Any]) -> str:
    idx = _stage_index(ctx.get("crop_stage", ""))
    width = 88.0 * idx / (len(_STAGES) - 1)
    steps = []
    for i, (name, icon) in enumerate(_STAGES):
        cls = "now" if i == idx else ("done" if i < idx else "")
        tag = "<div class='tag'>YOU ARE HERE</div>" if i == idx else ("<div class='tag' style='background:#10b981'>BEST TO APPLY</div>" if i == 3 and idx < 3 else "")
        steps.append(f"<div class='jstep {cls}'><div class='dot'>{icon}</div><div class='nm'>{name.upper()}</div>{tag}</div>")
    return ("<div class='aa-card b-12'><div class='aa-eyebrow'>YOUR CROP'S SEASON JOURNEY</div>"
            f"<div class='aa-sub'>{_e(ctx['crop'])} · now at <b>{_e(ctx.get('crop_stage') or _STAGES[idx][0])}</b>. The flowering stage is when a biostimulant usually responds best.</div>"
            f"<div class='journey' style='--jw:{width:.0f}%'>{''.join(steps)}</div></div>")


def _icon(desc: str) -> str:
    d = (desc or "").lower()
    if "storm" in d or "thunder" in d:
        return "⛈️"
    if "rain" in d or "drizzle" in d or "shower" in d:
        return "🌧️"
    if "clear" in d or "sun" in d:
        return "☀️"
    if "mist" in d or "haze" in d or "fog" in d:
        return "🌫️"
    if "few" in d or "scattered" in d:
        return "⛅"
    return "☁️"


def _forecast(ctx: Dict[str, Any]) -> str:
    days = [d for d in ctx.get("forecast", []) if d.get("temp_max") is not None][:5]
    if not days:
        return ""
    highs = [float(d["temp_max"]) for d in days]
    lo, hi = min(highs), max(highs)
    span = (hi - lo) or 1.0
    pts = [(14 + i * (272 / max(1, len(days) - 1)), 38 - 30 * (v - lo) / span) for i, v in enumerate(highs)]
    path = "M" + " L".join(f"{x:.0f} {y:.0f}" for x, y in pts)
    dots = "".join(f"<circle cx='{x:.0f}' cy='{y:.0f}' r='4'/>" for x, y in pts)
    tiles = "".join(
        f"<div class='fc-day' style='animation-delay:{i * 0.08:.2f}s'><div class='d'>{_e(str(d.get('date', '')).split(' (')[0].upper())}</div>"
        f"<div class='i'>{_icon(d.get('desc', ''))}</div><div class='t'>{float(d['temp_max']):.0f}° <span style='color:#64748b;font-weight:600;'>{float(d.get('temp_min', d['temp_max'])):.0f}°</span></div>"
        f"<div class='r'>{float(d.get('rain_prob') or 0):.0f}% rain</div></div>"
        for i, d in enumerate(days))
    return ("<div class='aa-card b-12'><div class='aa-eyebrow'>NEXT 5 DAYS AT YOUR FARM · LIVE FORECAST</div>"
            f"<svg class='spark' viewBox='0 0 300 46' preserveAspectRatio='none' aria-hidden='true'><path d='{path}'/>{dots}</svg>"
            f"<div class='fc'>{tiles}</div></div>")


def _moments(ctx: Dict[str, Any]) -> str:
    listings = [r for r in farm_store.select("scrap_listings") if r.get("status") == "open"]
    demands = [d for d in farm_store.select("buyer_demands") if d.get("status") == "open"]
    river = ctx["river"]
    river_line = {"NORMAL": "River water is within safe limits.", "WATCH": "River is muddy; filter water for drip lines.",
                  "WARNING": "River water is nearing a limit. Check before irrigating.",
                  "CRITICAL": "River alert: do not irrigate from the river."}.get(river["status"], "")
    demo = " (simulated)" if river["label"].startswith("Simulated") else ""
    cards = [
        ("BEFORE · DECIDE", f"{_e(ctx['crop'])} in the {_e(ctx['region'])} belt",
         f"Readiness {ctx['readiness']}/100. Soil, cost of cultivation and the right biological are in <b>Soil</b>, <b>Management</b> and <b>Biologicals</b>."),
        ("DURING · WATCH", f"{ctx['temp_c']:.0f}°C now" if ctx.get("temp_c") is not None else "Weather",
         f"{_e(river_line)}{_e(demo)} Weather, the river and the leaf scanner live under <b>Weather</b>, <b>Management</b> and <b>River Watch</b>."),
        ("AFTER · PROVE & SELL", f"{len(demands)} company needs open",
         f"{ctx['yield_delta']:+.2f} q/acre lift to prove. Companies want your crop in <b>Company Needs</b>; {len(listings)} farm-waste listings are in <b>Farm Waste Market</b>."),
    ]
    return "".join(f"<div class='aa-card b-4'><div class='aa-eyebrow'>{t}</div><div class='aa-mid'>{big}</div><div class='aa-sub'>{body}</div></div>"
                   for t, big, body in cards)


def _trust(items: List[Dict[str, str]]):
    c = sources.counts(items)
    chips = "".join(
        f"<span class='aa-chip{' live' if i['state'] == sources.LIVE else ''}' style='color:{sources.STATE_STYLE[i['state']][0]};background:{sources.STATE_STYLE[i['state']][1]};' "
        f"title='{_e(i['detail'])}'><b>{_e(i['name'])}</b> · {i['state'].title()}</span>" for i in items)
    st.markdown(
        "<div class='aa-eyebrow' style='margin-top:16px;'>WHERE THESE NUMBERS COME FROM</div>"
        f"<div class='aa-chips'>{chips}</div>"
        f"<div class='aa-fine'>{c[sources.LIVE]} live · {c[sources.SNAPSHOT]} snapshot · {c[sources.SIMULATED]} simulated · {c[sources.OFF]} off. "
        "Live means fetched just now. Snapshot is real reference data that is not live. Simulated means we generated it for the demo.</div>",
        unsafe_allow_html=True)
    with st.expander("What each source is used for"):
        for i in items:
            st.markdown(f"**{i['name']}**: {i['role']}. {i['detail']}.")
    with st.expander("Full source registry (owner, how it is integrated, how far it is validated)"):
        st.dataframe(pd.DataFrame(sources.REGISTRY).rename(columns={
            "name": "Source", "url": "Link", "owner": "Owner", "retrieved": "Retrieved", "frequency": "Updates",
            "coverage": "Coverage", "integration": "Integration", "validation": "Validation"}),
            hide_index=True, width="stretch")


def render_today(ctx: Dict[str, Any]):
    st.markdown(
        f"<div class='aa-place'>{_e(ctx['place_display'])}</div>"
        f"<div class='aa-sub'>{datetime.now().strftime('%A, %d %B')} · {_e(ctx['region'])} belt · source: {_e(ctx['location_source'])}</div>",
        unsafe_allow_html=True)
    grid = _decision(ctx) + _profit(ctx) + _gauges(ctx) + _journey(ctx) + _forecast(ctx) + _moments(ctx)
    st.markdown(f"<div class='bento'>{grid}</div>", unsafe_allow_html=True)
    _trust(ctx["sources"])
