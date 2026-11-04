"""
live_scene.py - an animated scene driven by real data.

The sky follows the local time and the live weather (clear, cloudy, rain, night), clouds drift at a speed
set by the wind, the crops sway with it, and the river at the bottom changes colour with the AquaSentinel
status (and pulses red on an alert). A ticker underneath scrolls the facts that matter today.

Everything here is presentation: it only reads numbers the rest of the app already has. The styles live in
assets/theme.css (the .ls-* classes); the motion respects prefers-reduced-motion.
"""

import html as html_mod
import math
from datetime import datetime
from typing import Any, Dict, List, Tuple

_RIVER = {  # status -> (colour 1, colour 2, label)
    "NORMAL": ("#38bdf8", "#0ea5e9", "River normal"),
    "WATCH": ("#b08968", "#8a6b4a", "River muddy"),
    "WARNING": ("#f59e0b", "#d97706", "River warning"),
    "CRITICAL": ("#ef4444", "#b91c1c", "RIVER ALERT"),
}


def _sky(hour: int, cloud: float, rain: bool) -> Tuple[str, str, float, float, float]:
    """(css gradient, extra classes, sun x %, sun y %, brightness of the land)."""
    grey = rain or cloud >= 75
    if hour < 5 or hour >= 19:
        return "linear-gradient(#0b1b3a, #1e3a5f 60%, #28557f)", "night", 78.0, 14.0, 0.5
    if hour < 7:
        return "linear-gradient(#ffd7a8, #f7a8b8 55%, #8ecae6)", "", 12.0 + (hour - 5) * 8, 52.0, 0.85
    if hour >= 17:
        return "linear-gradient(#ff9e7a, #ffc98b 50%, #8fb8e8)", "", 78.0 + (hour - 17) * 7, 50.0, 0.85
    p = (hour - 7) / 10.0                      # 0 at 7:00 -> 1 at 17:00
    x = 10 + 80 * p
    y = 46 - 38 * math.sin(math.pi * p)        # higher at midday
    if rain:
        return "linear-gradient(#7f93a3, #a5b4c0 60%, #cdd8e0)", "grey", x, y + 6, 0.8
    if grey:
        return "linear-gradient(#9fb7c9, #c9d6df 70%, #e4ecf1)", "grey", x, y + 4, 0.92
    return "linear-gradient(#6fc1f5, #b9e3ff 68%, #eaf8ff)", "", x, y, 1.0


def _clouds(cloud: float, wind_kmh: float) -> str:
    n = 2 + int(min(100, max(0, cloud)) / 18)
    base = max(22.0, 74.0 - wind_kmh * 2.6)    # seconds to cross the scene: faster when windy
    parts = []
    for i in range(n):
        w = 90 + (i * 37) % 110
        top = 6 + (i * 23) % 36
        o = 0.55 + ((i * 13) % 40) / 100.0
        dur = base * (0.8 + (i % 4) * 0.18)
        delay = -(i * dur / n)
        parts.append(f"<span class='ls-cloud' style='--w:{w}px;--o:{o:.2f};--dur:{dur:.0f}s;--delay:{delay:.1f}s;top:{top}%'></span>")
    return "".join(parts)


def _rain(on: bool) -> str:
    if not on:
        return ""
    return "".join(f"<span class='ls-drop' style='left:{(i * 2.6) % 100:.1f}%;--rd:{0.7 + (i % 5) * 0.12:.2f}s;--rl:{-(i % 9) * 0.15:.2f}s'></span>" for i in range(38))


def _birds(on: bool) -> str:
    if not on:
        return ""
    return "".join(f"<span class='ls-bird' style='--by:{14 + i * 9}px;--bd:{19 + i * 5}s;--bl:{-i * 6}s'></span>" for i in range(3))


def _field(wind_kmh: float) -> str:
    sway = max(1.6, 4.2 - wind_kmh * 0.12)
    rows = []
    for row, (base_y, top_y, stroke, leaf) in enumerate(((96, 46, "#16a34a", "#4ade80"), (96, 30, "#15803d", "#22c55e"))):
        for i in range(30):
            x = 12 + i * 33 + (row * 16)
            h = top_y + (i * 7) % 10
            delay = -((i * 0.23 + row * 0.5) % sway)
            rows.append(
                f"<g class='stalk' style='--sway:{sway:.1f}s;--d:{delay:.2f}s'>"
                f"<path d='M{x} {base_y} L{x} {h}' stroke='{stroke}' stroke-width='3' stroke-linecap='round' fill='none'/>"
                f"<path d='M{x} {h + 22} q14 -6 20 -20 q-16 2 -20 20z' fill='{leaf}'/>"
                f"<path d='M{x} {h + 36} q-14 -6 -20 -20 q16 2 20 20z' fill='{leaf}'/></g>")
    return "".join(rows)


def _windmill(wind_kmh: float) -> str:
    """A water-pump windmill whose blades turn faster when the wind is stronger."""
    dur = max(1.6, 9.0 - wind_kmh * 0.35)
    return ("<svg class='ls-windmill' viewBox='0 0 60 110' aria-hidden='true'>"
            "<path d='M26 108 L30 40 L34 108Z' fill='#e2e8f0' stroke='#94a3b8' stroke-width='1.2'/>"
            f"<g class='blades' style='animation-duration:{dur:.1f}s'>"
            "<path d='M30 38 L27 4 L33 4Z' fill='#f8fafc' stroke='#94a3b8' stroke-width='1'/>"
            "<path d='M30 38 L58 52 L56 58Z' fill='#f8fafc' stroke='#94a3b8' stroke-width='1'/>"
            "<path d='M30 38 L2 52 L4 58Z' fill='#f8fafc' stroke='#94a3b8' stroke-width='1'/></g>"
            "<circle cx='30' cy='38' r='4' fill='#475569'/></svg>")


def _tractor() -> str:
    """A small tractor that drives across the field on a loop."""
    return ("<div class='ls-tractor' aria-hidden='true'><svg viewBox='0 0 84 52'>"
            "<rect x='34' y='8' width='28' height='20' rx='4' fill='#f59e0b'/><rect x='38' y='12' width='12' height='9' rx='2' fill='#e0f2fe'/>"
            "<rect x='8' y='20' width='40' height='14' rx='4' fill='#16a34a'/><rect x='10' y='14' width='14' height='8' rx='2' fill='#15803d'/>"
            "<rect x='12' y='5' width='3' height='10' fill='#475569'/>"
            "<g class='wheel' style='transform-origin:58px 38px'><circle cx='58' cy='38' r='12' fill='#1f2937'/><circle cx='58' cy='38' r='5' fill='#fbbf24'/>"
            "<path d='M58 28v20M48 38h20' stroke='#fbbf24' stroke-width='1.5'/></g>"
            "<g class='wheel' style='transform-origin:22px 42px'><circle cx='22' cy='42' r='7' fill='#1f2937'/><circle cx='22' cy='42' r='3' fill='#fbbf24'/>"
            "<path d='M22 35v14M15 42h14' stroke='#fbbf24' stroke-width='1.2'/></g></svg></div>")


def _fireflies(on: bool) -> str:
    if not on:
        return ""
    return "".join(f"<span class='ls-ff' style='left:{(i * 7.3 + 5) % 96:.0f}%;bottom:{30 + (i * 13) % 90}px;--ffd:{3.2 + (i % 5) * 0.7:.1f}s;--ffl:{-(i % 7) * 0.6:.1f}s'></span>"
                   for i in range(16))


def _mist() -> str:
    return "<div class='ls-mist m1'></div><div class='ls-mist m2'></div>"


def build(ctx: Dict[str, Any]) -> str:
    """ctx: place, temp_c, humidity, wind_kmh, cloud_pct, desc, rain_prob, river_status, river_demo,
    crop, price, price_demo, live_sources, simulated_sources"""
    hour = ctx.get("hour")
    hour = datetime.now().hour if hour is None else int(hour)
    cloud = float(ctx.get("cloud_pct") or 0)
    wind = float(ctx.get("wind_kmh") or 0)
    desc = str(ctx.get("desc") or "")
    rain = "rain" in desc.lower() or "drizzle" in desc.lower() or "storm" in desc.lower()
    sky, extra, sx, sy, dim = _sky(hour, cloud, rain)
    status = ctx.get("river_status", "NORMAL")
    r1, r2, rlabel = _RIVER.get(status, _RIVER["NORMAL"])
    alert = "alert" if status in ("CRITICAL",) else ""
    demo = " (simulated)" if ctx.get("river_demo", True) else ""
    e = html_mod.escape

    temp = ctx.get("temp_c")
    hum = ctx.get("humidity")
    t_html = f"<span class='cnt' style='--to:{round(temp)}' data-unit='°C'></span>" if temp is not None else "--"
    h_html = f"<span class='cnt' style='--to:{round(hum)}' data-unit='%'></span>" if hum is not None else "--"
    w_html = f"<span class='cnt' style='--to:{round(wind)}' data-unit=' km/h'></span>"
    rp = ctx.get("rain_prob")
    rain_chip = (f"<div class='ls-glass ls-chip'><small>RAIN TOMORROW</small><b><span class='cnt' style='--to:{round(rp)}' data-unit='%'></span></b></div>"
                 if rp is not None else "")

    spray = "open" if wind < 15 else "closed"
    items: List[str] = []
    if ctx.get("price"):
        tag = " (demo price)" if ctx.get("price_demo", True) else ""
        items.append(f"{e(str(ctx.get('crop', 'Crop')))} <em>₹{float(ctx['price']):,.0f}/q</em>{tag}")
    items.append(f"Spray window <em>{spray}</em> · wind {wind:.0f} km/h")
    items.append(f"{e(rlabel)}{demo}")
    if rp is not None:
        items.append(f"Rain chance tomorrow <em>{rp:.0f}%</em>")
    items.append(f"<em>{int(ctx.get('live_sources', 0))}</em> live sources · {int(ctx.get('simulated_sources', 0))} simulated")
    rail = "".join(f"<span>{i}</span>" for i in items)

    aria = (f"Live scene for {ctx.get('place', 'your farm')}: {desc or 'weather unavailable'}, "
            f"{'' if temp is None else f'{temp:.0f} degrees, '}wind {wind:.0f} kilometres per hour, {rlabel.lower()}.")
    hills = ("<svg class='ls-hills' viewBox='0 0 1000 120' preserveAspectRatio='none' aria-hidden='true'>"
             "<path d='M0 70 C180 20 330 90 520 50 S860 10 1000 55 L1000 120 L0 120Z' fill='#86efac'/>"
             "<path d='M0 95 C220 40 360 110 560 70 S880 40 1000 80 L1000 120 L0 120Z' fill='#34d399'/></svg>")
    field = f"<svg class='ls-field' viewBox='0 0 1000 96' preserveAspectRatio='none' aria-hidden='true'>{_field(wind)}</svg>"
    mountains = ("<svg class='ls-mtn' viewBox='0 0 1000 140' preserveAspectRatio='none' aria-hidden='true'>"
                 "<path d='M0 110 L120 40 L210 95 L330 20 L460 100 L590 35 L720 105 L860 30 L1000 90 L1000 140 L0 140Z' fill='#a7d8c0' opacity='.75'/></svg>")
    rays = "<div class='ls-rays'></div>" if (extra == "" and not rain) else ""
    night = extra == "night"
    return (
        f"<div class='ls {extra} {alert}' role='img' aria-label='{e(aria)}' "
        f"style=\"--sky:{sky};--sx:{sx:.0f}%;--sy:{sy:.0f}%;--dim:{dim};--r1:{r1};--r2:{r2}\">"
        f"{rays}<div class='ls-sun'></div>{_clouds(cloud, wind)}{_birds(not rain and not night)}{mountains}{hills}{_windmill(wind)}{field}{_tractor()}"
        f"<div class='ls-river'></div>{_mist()}{_fireflies(night)}{_rain(rain)}"
        f"<div class='ls-hud'><div class='ls-glass'><span class='ls-live'><i></i>LIVE</span>"
        f"<div class='ls-place'>{e(str(ctx.get('place', '')))}</div><div class='ls-temp'>{t_html}</div><div class='ls-desc'>{e(desc.title())}</div></div>"
        f"<div class='ls-chips'><div class='ls-glass ls-chip'><small>HUMIDITY</small><b>{h_html}</b></div>"
        f"<div class='ls-glass ls-chip'><small>WIND</small><b>{w_html}</b></div>{rain_chip}</div></div>"
        f"<div class='ls-status'>{e(rlabel)}{demo}</div></div>"
        f"<div class='ls-ticker' aria-hidden='true'><div class='rail'>{rail}{rail}</div></div>")
