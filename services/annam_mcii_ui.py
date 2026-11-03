"""
annam_mcii_ui.py - Human-Centered ANNAM.AI MCII Interface
AgriAttribute AI — Syngenta Biologicals & ANNAM.AI Hack Core 2026 (Problem Statement 07)

Design Philosophy:
- Simple hierarchy, large readable typography, minimal cards, natural spacing.
- Practical information first: Location -> Current Field Conditions -> What This Means -> Recommended Action -> 24h Trend -> Supporting Map -> Provenance.
- Grounded, calm, human agricultural language (no excessive gradients, neon glows, futuristic AI styling, or dashboard bloat).
- Strict separation: RAW MCII SENSOR DATA vs. AGRIATTRIBUTE DERIVED INSIGHTS.
"""

import json
import streamlit as st
import pandas as pd
from services import annam_mcii_service
from services import annam_intelligence_adapter
from services.localization import t


def _generate_clean_leaflet_map_html(map_stations: list, selected_station_id: str = None) -> str:
    """
    Generates a clean, calm Leaflet.js map with standard high-contrast cartography.
    The map serves as supporting visual context rather than dominating the screen.
    """
    stations_json = json.dumps(map_stations)
    sel_id_json = json.dumps(selected_station_id or "")

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; background: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        #mcii-map {{ width: 100%; height: 100%; background: #e2e8f0; border-radius: 8px; }}
        .leaflet-popup-content-wrapper {{
            background: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            padding: 2px;
        }}
        .mcii-popup-title {{ font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 2px; }}
        .mcii-popup-sub {{ font-size: 11px; color: #64748b; margin-bottom: 6px; }}
        .mcii-metric-row {{ display: flex; justify-content: space-between; font-size: 12px; padding: 2px 0; border-bottom: 1px solid #f1f5f9; }}
        .mcii-metric-lbl {{ color: #475569; }}
        .mcii-metric-val {{ font-weight: 600; color: #0f172a; }}
        .mcii-badge {{ display: inline-block; padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700; margin-top: 5px; }}
        .badge-online {{ background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; }}
        .badge-offline {{ background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }}
    </style>
</head>
<body>
    <div id="mcii-map"></div>
    <script>
        var stations = {stations_json};
        var selectedId = {sel_id_json};

        var map = L.map('mcii-map', {{
            center: [22.5, 78.5],
            zoom: 5,
            zoomControl: true,
            attributionControl: false
        }});

        // Standard OpenStreetMap tiles — 100% free, no API key required, zero watermarks
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a> contributors'
        }}).addTo(map);

        var targetMarker = null;

        stations.forEach(function(s) {{
            if (!s.lat || !s.lon) return;

            var isOnline = (s.health === 'ONLINE');
            var isSel = (s.id === selectedId);

            var fillColor = isOnline ? '#059669' : '#dc2626';
            var strokeColor = isSel ? '#1e293b' : (isOnline ? '#047857' : '#991b1b');
            var radius = isSel ? 8 : (isOnline ? 5 : 4);
            var weight = isSel ? 3 : 1;

            var marker = L.circleMarker([s.lat, s.lon], {{
                radius: radius,
                fillColor: fillColor,
                color: strokeColor,
                weight: weight,
                opacity: 0.9,
                fillOpacity: 0.85
            }});

            var tempStr = (s.temp !== null && s.temp !== undefined) ? (s.temp + ' °C') : 'N/A';
            var humStr = (s.humidity !== null && s.humidity !== undefined) ? (s.humidity + ' %') : 'N/A';
            var rainStr = (s.rain_today !== null && s.rain_today !== undefined) ? (s.rain_today + ' mm') : '0 mm';
            var windStr = (s.wind !== null && s.wind !== undefined) ? (s.wind + ' m/s') : 'N/A';

            var badgeClass = isOnline ? 'badge-online' : 'badge-offline';

            var popupContent = '<div style="min-width: 170px;">' +
                '<div class="mcii-popup-title">' + s.city + ' (#' + s.id + ')</div>' +
                '<div class="mcii-popup-sub">' + s.state + ' • Lat: ' + s.lat.toFixed(3) + '°, Lon: ' + s.lon.toFixed(3) + '°</div>' +
                '<div class="mcii-metric-row"><span class="mcii-metric-lbl">Temp</span><span class="mcii-metric-val">' + tempStr + '</span></div>' +
                '<div class="mcii-metric-row"><span class="mcii-metric-lbl">Humidity</span><span class="mcii-metric-val">' + humStr + '</span></div>' +
                '<div class="mcii-metric-row"><span class="mcii-metric-lbl">Rain Today</span><span class="mcii-metric-val">' + rainStr + '</span></div>' +
                '<div class="mcii-metric-row"><span class="mcii-metric-lbl">Wind</span><span class="mcii-metric-val">' + windStr + '</span></div>' +
                '<div style="margin-top: 4px;"><span class="mcii-badge ' + badgeClass + '">' + (isOnline ? 'Active' : 'Offline') + '</span></div>' +
            '</div>';

            marker.bindPopup(popupContent);
            marker.addTo(map);

            if (isSel) {{
                targetMarker = marker;
            }}
        }});

        // Maintain centered India perspective by default so the entire diversified network across India is visible
        map.setView([22.8, 79.0], 5);

        if (targetMarker) {{
            targetMarker.openPopup();
        }}

        // Quick Re-Center India Control
        var CenterControl = L.Control.extend({{
            options: {{ position: 'topright' }},
            onAdd: function(m) {{
                var div = L.DomUtil.create('div', 'leaflet-bar');
                div.innerHTML = '<a href="#" title="Center All-India Overview" style="background:#ffffff; color:#0f172a; font-weight:700; font-size:12px; padding:6px 12px; display:block; text-decoration:none; white-space:nowrap; border-radius:4px; box-shadow:0 1px 4px rgba(0,0,0,0.15); border: 1px solid #cbd5e1;">🇮🇳 Center India</a>';
                div.onclick = function(e) {{
                    e.preventDefault();
                    m.setView([22.8, 79.0], 5);
                }};
                return div;
            }}
        }});
        map.addControl(new CenterControl());
    </script>
</body>
</html>"""


def render_annam_mcii_tab(lang: str = "English", active_crop: str = "Soybean"):
    """
    Renders the calm, human-centric ANNAM.AI Field Intelligence tab.
    Priority: Location -> Current Field Conditions -> What This Means -> Recommended Action -> 24h Trend -> Map -> Provenance.
    """
    # ─────────────────────────────────────────────────────────────────────────
    # 1. CLEAN HEADER (Calm, trustworthy, authentic)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-left: 5px solid #059669; border-radius: 12px; padding: 18px 24px; margin-bottom: 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
                    <span style="font-size: 1.35rem;">🌐</span>
                    <h2 style="margin: 0; color: #0f172a; font-size: 1.42rem; font-weight: 800; letter-spacing: -0.3px;">
                        {t('annam_header', lang)}
                    </h2>
                    <span style="background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; padding: 3px 10px; border-radius: 9999px; font-size: 0.74rem; font-weight: 800; letter-spacing: 0.5px;">
                        LIVE MCII NETWORK
                    </span>
                </div>
                <p style="margin: 0; color: #475569; font-size: 0.92rem; font-weight: 500;">
                    {t('annam_subheading', lang)}
                </p>
            </div>
            <div style="text-align: right; font-size: 0.82rem; color: #64748b; line-height: 1.45;">
                <div style="font-weight: 700; color: #047857;">CoE AI in Agriculture • IIT Ropar</div>
                <div style="color: #64748b; font-weight: 500;">Ministry of Education Initiative • 358 Stations</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 2. STEP 1: LOCATION & STATION PICKER
    # ─────────────────────────────────────────────────────────────────────────
    stations_all = annam_mcii_service.get_mcii_stations()
    if not stations_all:
        st.warning("ANNAM.AI MCII data is temporarily unavailable. Displaying last cached observations.")
        return

    # Build clean, human-readable station dictionary
    station_dict = {}
    for s in stations_all:
        status_tag = "Live" if s['health_status'] == "ONLINE" else "Standby"
        label = f"{s['city']}, {s['state']} (Station #{s['station_id']}) — {status_tag}"
        station_dict[label] = s['station_id']

    # Top selector bar
    col_sel_stn, col_sel_filter = st.columns([3.2, 1.2])
    with col_sel_filter:
        states_list = ["All States"] + sorted(list(set(s['state'] for s in stations_all if s['state'] and s['state'] != "Unknown State")))
        filter_state = st.selectbox("Filter by State:", states_list, key="mcii_human_state_filter")
    
    # Filter station dict if state chosen
    if filter_state != "All States":
        filtered_station_dict = {lbl: sid for lbl, sid in station_dict.items() if filter_state in lbl}
        if not filtered_station_dict:
            filtered_station_dict = station_dict
    else:
        filtered_station_dict = station_dict

    # Find the geographically centered station in India (near Bhopal, MP ~22.5°N, 78.5°E) as default
    def _dist_to_center(s):
        lat = s.get('latitude') or 0.0
        lon = s.get('longitude') or 0.0
        if lat <= 0 or lon <= 0:
            return 9999.0
        return ((lat - 22.5) ** 2 + (lon - 78.5) ** 2) ** 0.5

    centered_station = min(stations_all, key=_dist_to_center)
    centered_default_id = centered_station.get('station_id', '101#SSMet/Forest')

    # Resolve active station selection index
    current_sel_id = st.session_state.get("mcii_active_station_id", centered_default_id)
    default_station_idx = 0
    for idx, (lbl, sid) in enumerate(filtered_station_dict.items()):
        if sid == current_sel_id:
            default_station_idx = idx
            break

    with col_sel_stn:
        chosen_label = st.selectbox(
            "Select Weather Station:",
            options=list(filtered_station_dict.keys()),
            index=default_station_idx,
            key="mcii_human_station_dropdown"
        )
        active_station_id = filtered_station_dict[chosen_label]
        st.session_state["mcii_active_station_id"] = active_station_id

    # Fetch active station observation
    obs = annam_mcii_service.get_latest_observation(active_station_id)
    if not obs:
        st.error("Station telemetry temporarily unavailable.")
        return

    # Metadata & Freshness banner (minimal, clear, human)
    fresh_badge_html = {
        "LIVE": "<span style='background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem;'>🟢 Live Telemetry</span>",
        "RECENT": "<span style='background: #fffbeb; color: #b45309; border: 1px solid #fde68a; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem;'>🟡 Recent (Today)</span>",
        "CACHED": "<span style='background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem;'>⚪ Cached Value</span>",
        "UNAVAILABLE": "<span style='background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; padding: 2px 8px; border-radius: 6px; font-weight: 700; font-size: 0.78rem;'>🔴 Unavailable</span>"
    }.get(obs["freshness"], "<span style='background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 6px; font-size: 0.78rem;'>Cached</span>")

    coord_str = f"{obs['latitude']:.4f}°N, {obs['longitude']:.4f}°E" if obs['latitude'] else "Pending GPS"

    st.markdown(f"""
    <div style="background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 8px 14px; margin-bottom: 18px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; font-size: 0.82rem; color: #475569;">
        <div>
            <strong>{obs['city']}</strong> ({obs['district']}, {obs['state']}) • GPS: <code>{coord_str}</code> • Station #{obs['station_id']}
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            {fresh_badge_html}
            <span style="color: #64748b;">Recorded: {obs['observation_time']}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 3. STEP 2: CURRENT FIELD CONDITIONS (Raw Measurements - 5-Second Glance)
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom: 8px;">
        <span style="font-size: 1.05rem; font-weight: 800; color: #0f172a;">Current field conditions</span>
        <span style="font-size: 0.75rem; color: #64748b; margin-left: 8px; font-weight: 600;">RAW SENSOR READINGS (ANNAM.AI MCII)</span>
    </div>
    """, unsafe_allow_html=True)

    c_temp, c_hum, c_rain, c_wind, c_soil = st.columns(5)
    
    val_temp = f"{obs['temperature']:.1f} °C" if obs['temperature'] is not None else "N/A"
    val_hum = f"{obs['relative_humidity']:.0f} %" if obs['relative_humidity'] is not None else "N/A"
    val_rain = f"{obs['rainfall_daily']:.1f} mm" if obs['rainfall_daily'] is not None else "0.0 mm"
    
    # Wind in km/h for farmer readability
    w_raw = obs['wind_speed']
    if w_raw is not None:
        w_kmh = (w_raw * 3.6) if w_raw < 25 else w_raw
        val_wind = f"{w_kmh:.1f} km/h"
    else:
        val_wind = "N/A"
        
    val_soil = f"{obs['soil_moisture']:.0f} %" if obs['soil_moisture'] is not None else "Standby"

    with c_temp:
        st.metric(label="Air Temperature", value=val_temp)
    with c_hum:
        st.metric(label="Relative Humidity", value=val_hum)
    with c_rain:
        st.metric(label="Rain Today", value=val_rain)
    with c_wind:
        st.metric(label="Wind Speed", value=val_wind)
    with c_soil:
        st.metric(label="Soil Moisture", value=val_soil)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 4. STEP 3: WHAT THIS MEANS (AgriAttribute Practical Derived Interpretation)
    # ─────────────────────────────────────────────────────────────────────────
    signals = annam_intelligence_adapter.compute_derived_signals(obs, target_crop=active_crop)
    spray = signals["spray_suitability"]
    irrig = signals["irrigation_suitability"]
    heat = signals["heat_stress_risk"]
    dis = signals["disease_incubation_risk"]

    st.markdown("""
    <div style="margin-bottom: 10px; margin-top: 6px;">
        <span style="font-size: 1.05rem; font-weight: 800; color: #0f172a;">What this means for your field</span>
        <span style="font-size: 0.75rem; color: #047857; margin-left: 8px; font-weight: 700; background: #ecfdf5; border: 1px solid #a7f3d0; padding: 2px 6px; border-radius: 4px;">AGRIATTRIBUTE INTERPRETATION</span>
    </div>
    """, unsafe_allow_html=True)

    # Plain agricultural label mapping
    # Spray Status
    if "OPTIMAL" in spray["derived_indicator"]:
        spray_badge = ("#ecfdf5", "#047857", "#a7f3d0", "Safe to Spray Today")
        spray_simple = "Wind is calm and leaves can absorb foliar nutrition effectively without wash-off risk."
    elif "MARGINAL" in spray["derived_indicator"]:
        spray_badge = ("#fffbeb", "#b45309", "#fde68a", "Marginal — Spray with Care")
        spray_simple = "Wind or humidity is elevated. If spraying, use coarse drift-reduction nozzles before 10 AM."
    else:
        spray_badge = ("#fef2f2", "#b91c1c", "#fecaca", "Unsafe to Spray Today")
        spray_simple = "High wind or active rain detected. Postpone foliar treatments to avoid chemical drift and wash-off."

    # Water Status
    if "SUSPEND" in irrig["derived_indicator"] or "PAUSE" in irrig["derived_indicator"]:
        irrig_badge = ("#ecfdf5", "#047857", "#a7f3d0", "No Watering Needed")
        irrig_simple = "Recent rainfall or moisture has adequately replenished the root zone."
    elif "REQUIRED" in irrig["derived_indicator"]:
        irrig_badge = ("#fef2f2", "#b91c1c", "#fecaca", "Irrigation Recommended")
        irrig_simple = "Soil water balance is running low. Schedule light irrigation to prevent moisture stress."
    else:
        irrig_badge = ("#ecfdf5", "#047857", "#a7f3d0", "Adequate Soil Moisture")
        irrig_simple = "Root zone moisture is sufficient for normal crop growth."

    # Heat Stress
    if "ACUTE" in heat["derived_indicator"]:
        heat_badge = ("#fef2f2", "#b91c1c", "#fecaca", "High Heat Stress")
        heat_simple = "Temperature exceeds 38°C. Crops face thermal shock and flower drop. Consider anti-transpirant."
    elif "MODERATE" in heat["derived_indicator"]:
        heat_badge = ("#fffbeb", "#b45309", "#fde68a", "Moderate Heat")
        heat_simple = "Daytime heat is elevated. Maintain light soil moisture to buffer vegetative wilting."
    else:
        heat_badge = ("#ecfdf5", "#047857", "#a7f3d0", "Normal Temperature")
        heat_simple = f"Air temperature is favorable for healthy vegetative and reproductive growth of {active_crop}."

    # Disease Risk
    if "CRITICAL" in dis["derived_indicator"]:
        dis_badge = ("#fef2f2", "#b91c1c", "#fecaca", "High Fungal Threat")
        dis_simple = "Humid, warm conditions create prime incubation window for foliar blight and rust spores."
    elif "MODERATE" in dis["derived_indicator"]:
        dis_badge = ("#fffbeb", "#b45309", "#fde68a", "Moderate Disease Risk")
        dis_simple = "Elevated humidity detected. Check underside of leaves for early rust or leaf spot symptoms."
    else:
        dis_badge = ("#ecfdf5", "#047857", "#a7f3d0", "Low Disease Pressure")
        dis_simple = "Air is dry enough to suppress rapid fungal spore germination."

    # Dynamic vernacular translation via AI4Bharat IndicTrans2
    if lang and str(lang).lower() not in ["english", "en"]:
        try:
            from services import indictrans_service
            spray_simple = indictrans_service.translate_en_to_indic(spray_simple, lang)
            irrig_simple = indictrans_service.translate_en_to_indic(irrig_simple, lang)
            heat_simple = indictrans_service.translate_en_to_indic(heat_simple, lang)
            dis_simple = indictrans_service.translate_en_to_indic(dis_simple, lang)
        except Exception:
            pass

    card_c1, card_c2, card_c3, card_c4 = st.columns(4)
    with card_c1:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 14px; min-height: 145px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Spray Conditions</div>
            <div style="margin: 6px 0;">
                <span style="background: {spray_badge[0]}; color: {spray_badge[1]}; border: 1px solid {spray_badge[2]}; font-size: 0.88rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">
                    {spray_badge[3]}
                </span>
            </div>
            <div style="font-size: 0.80rem; color: #334155; line-height: 1.4; margin-top: 6px;">
                {spray_simple}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with card_c2:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 14px; min-height: 145px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Water Status</div>
            <div style="margin: 6px 0;">
                <span style="background: {irrig_badge[0]}; color: {irrig_badge[1]}; border: 1px solid {irrig_badge[2]}; font-size: 0.88rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">
                    {irrig_badge[3]}
                </span>
            </div>
            <div style="font-size: 0.80rem; color: #334155; line-height: 1.4; margin-top: 6px;">
                {irrig_simple}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with card_c3:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 14px; min-height: 145px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Heat Stress</div>
            <div style="margin: 6px 0;">
                <span style="background: {heat_badge[0]}; color: {heat_badge[1]}; border: 1px solid {heat_badge[2]}; font-size: 0.88rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">
                    {heat_badge[3]}
                </span>
            </div>
            <div style="font-size: 0.80rem; color: #334155; line-height: 1.4; margin-top: 6px;">
                {heat_simple}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with card_c4:
        st.markdown(f"""
        <div style="background: #ffffff; border: 1.5px solid #e2e8f0; border-radius: 10px; padding: 14px; min-height: 145px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);">
            <div style="font-size: 0.8rem; font-weight: 700; color: #64748b; text-transform: uppercase;">Disease Risk</div>
            <div style="margin: 6px 0;">
                <span style="background: {dis_badge[0]}; color: {dis_badge[1]}; border: 1px solid {dis_badge[2]}; font-size: 0.88rem; font-weight: 700; padding: 3px 8px; border-radius: 6px;">
                    {dis_badge[3]}
                </span>
            </div>
            <div style="font-size: 0.80rem; color: #334155; line-height: 1.4; margin-top: 6px;">
                {dis_simple}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 5. STEP 4: RECOMMENDED FIELD ACTION (The 5-Second Decision)
    # ─────────────────────────────────────────────────────────────────────────
    if "OPTIMAL" in spray["derived_indicator"] and not ("ACUTE" in heat["derived_indicator"]):
        rec_title = "RECOMMENDED ACTION: Favorable day for field work and foliar applications"
        rec_body = f"Current air conditions in {obs['city']} ({val_temp}, {val_hum} humidity, {val_wind} wind) are suitable for foliar spraying. Stomatal absorption is open, and drift risk is low. Complete applications before peak afternoon heat."
        rec_theme = ("#ecfdf5", "#065f46", "#047857", "✅")
    elif "UNSAFE" in spray["derived_indicator"]:
        rec_title = "RECOMMENDED ACTION: Postpone spraying — high drift or wash-off hazard"
        rec_body = f"Current conditions at {obs['city']} exceed safe thresholds ({spray['explanation']}). Hold off on foliar biostimulant or crop protection sprays until wind calms or rain clears."
        rec_theme = ("#fef2f2", "#991b1b", "#b91c1c", "⚠️")
    else:
        rec_title = "RECOMMENDED ACTION: Monitor field conditions before spraying"
        rec_body = f"Current microclimate at {obs['city']} is marginal ({spray['explanation']}). If applying biostimulants, apply in the early morning using coarse droplet nozzles."
        rec_theme = ("#fffbeb", "#92400e", "#b45309", "ℹ️")

    # Dynamic vernacular translation via AI4Bharat IndicTrans2
    if lang and str(lang).lower() not in ["english", "en"]:
        try:
            from services import indictrans_service
            rec_title = indictrans_service.translate_en_to_indic(rec_title, lang)
            rec_body = indictrans_service.translate_en_to_indic(rec_body, lang)
        except Exception:
            pass

    st.markdown(f"""
    <div style="background: {rec_theme[0]}; border: 1.5px solid {rec_theme[2]}; border-radius: 10px; padding: 16px 20px; margin-bottom: 22px;">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
            <span style="font-size: 1.3rem;">{rec_theme[3]}</span>
            <span style="font-size: 1.02rem; font-weight: 800; color: {rec_theme[1]};">
                {rec_title}
            </span>
        </div>
        <p style="margin: 0; font-size: 0.88rem; color: #1e293b; line-height: 1.5;">
            {rec_body}
        </p>
        <div style="margin-top: 8px; font-size: 0.74rem; color: #64748b; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
            <span>Derived by AgriAttribute AI using biophysical stomatal and drift models on ANNAM.AI Station #{obs['station_id']}.</span>
            <span style="background: #ffffff; border: 1px solid #cbd5e1; padding: 2px 7px; border-radius: 4px; font-weight: 600; color: #1d4ed8;">🌐 AI4Bharat IndicTrans2 Multilingual Layer</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 6. STEP 5: 24-HOUR HISTORICAL TREND (Clean, Simple Chart)
    # ─────────────────────────────────────────────────────────────────────────
    with st.container(border=True):
        t_col_left, t_col_right = st.columns([3, 1.5])
        with t_col_left:
            st.markdown(f"""
            <div style="font-size: 0.98rem; font-weight: 800; color: #0f172a; margin-bottom: 2px;">
                24-Hour Weather Trend at {obs['city']}
            </div>
            <div style="font-size: 0.80rem; color: #64748b;">
                Diurnal changes in temperature, humidity, wind, and pressure over the past 24 hours
            </div>
            """, unsafe_allow_html=True)
        with t_col_right:
            trend_choice = st.selectbox(
                "Parameter:",
                ["Temperature (°C)", "Relative Humidity (%)", "Wind Speed (m/s)", "Pressure (hPa)"],
                key="mcii_human_trend_picker"
            )

        history = annam_mcii_service.get_station_history(active_station_id, hours=24)
        if history:
            df_hist = pd.DataFrame(history)
            df_hist['timestamp'] = pd.to_datetime(df_hist['timestamp'])
            
            metric_map = {
                "Temperature (°C)": "temperature",
                "Relative Humidity (%)": "relative_humidity",
                "Wind Speed (m/s)": "wind_speed",
                "Pressure (hPa)": "pressure"
            }
            target_metric = metric_map[trend_choice]
            df_plot = df_hist.set_index('timestamp')[[target_metric]]
            st.line_chart(df_plot, height=220)
        else:
            st.info("Historical observations currently updating.")

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 7. STEP 6: STATION MAP (Supporting Visual Context)
    # ─────────────────────────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <div>
                <span style="font-size: 0.98rem; font-weight: 800; color: #0f172a;">Weather station network map</span>
                <span style="font-size: 0.80rem; color: #64748b; margin-left: 8px;">358 automatic weather stations across India</span>
            </div>
            <div style="font-size: 0.78rem; color: #475569;">
                <span style="color: #059669; font-weight: 700;">● Active</span> &nbsp; <span style="color: #dc2626; font-weight: 700;">● Offline / Standby</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        map_points = annam_mcii_service.get_station_map_data()
        clean_map_html = _generate_clean_leaflet_map_html(map_points, selected_station_id=active_station_id)
        st.iframe(clean_map_html, height=340)

    st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # 8. STEP 7: DATA SOURCE & GROUND PROVENANCE
    # ─────────────────────────────────────────────────────────────────────────
    with st.container():
        st.markdown("##### 📚 Data source & ground provenance (ANNAM.AI / MCII)")
        st.markdown(f"""
        **Technical Telemetry Attribution:**
        * **Origin Organization:** ANNAM.AI — Center of Excellence for AI in Agriculture, IIT Ropar (Ministry of Education, Govt. of India).
        * **Infrastructure:** Micro-Climate Intelligence Infrastructure (MCII).
        * **Official Source Endpoint:** `https://d1b09mxwt0ho4j.cloudfront.net/default/WS_Device_Activity`
        * **Active Station Inspected:** `{obs['station_name']}` (ID: `#{obs['station_id']}`)
        * **Data Freshness State:** `{obs['freshness']}` • **Quality Flag:** `{obs['quality_flag']}`
        * **Geographic Deployment Boundaries:** Verified strictly within India (Punjab, Haryana, Telangana, Maharashtra, Kerala, and Mizoram). Non-India coverage is not supported or claimed.
        * **Separation Notice:** Raw temperature, humidity, rainfall, wind, solar, and pressure readings are provided directly by ANNAM.AI MCII hardware. Spray safety windows, irrigation advice, and disease incubation risks are calculated independently by AgriAttribute AI.
        """)
