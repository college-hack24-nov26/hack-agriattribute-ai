"""
river_watch_ui.py - Streamlit interface for the AquaSentinel River Watch tab (see river_watch.py).
"""

import html as html_mod
import os
from typing import Any, Dict, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from services import farm_store, river_watch as rw

_ASSETS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "aquasentinel"))
SITE_URL = "https://soham0777.github.io/AquaSentinel/"

_STATUS_STYLE = {
    "NORMAL": ("#047857", "#ecfdf5", "#86efac", "Water is within safe limits"),
    "WATCH": ("#0369a1", "#eff6ff", "#93c5fd", "Watch: water is muddy"),
    "WARNING": ("#b45309", "#fffbeb", "#fcd34d", "Warning: a limit is being approached"),
    "CRITICAL": ("#b91c1c", "#fef2f2", "#fca5a5", "Critical: a safety limit is crossed"),
}


def stretch_name() -> str:
    """River stretch label that follows the farm location (so Phaltan shows Phaltan, not Kopargaon)."""
    place = st.session_state.get("farm_location_name") or "your area"
    return f"RIVER NEAR {str(place).upper()}"


def _img(name: str) -> Optional[str]:
    p = os.path.join(_ASSETS, name)
    return p if os.path.exists(p) else None


# ---------------------------------------------------------------------------
# state shared with the rest of the app (global alert banner)
# ---------------------------------------------------------------------------
def current_state() -> Tuple[pd.DataFrame, Dict[str, Any], str]:
    """Readings, analysis and a source label, based on the user's choices in session_state."""
    source = st.session_state.get("rw_source", "Simulated demo")
    if source == "Upload device CSV" and st.session_state.get("rw_csv_df") is not None:
        df = st.session_state["rw_csv_df"]
        label = "Uploaded device CSV"
    else:
        code = rw.SCENARIOS.get(st.session_state.get("rw_scenario", "Normal day"), "normal")
        df = rw.simulate_readings(code)
        label = "Simulated demo"
    return df, rw.analyse(df), label


def banner_html() -> Optional[str]:
    """Red/amber strip shown at the top of the whole app while a river alert is active."""
    try:
        _, analysis, label = current_state()
    except Exception:
        return None
    status = analysis["status"]
    if status not in ("WARNING", "CRITICAL"):
        return None
    fg, bg, border, _ = _STATUS_STYLE[status]
    top = max(analysis["findings"], key=lambda z: rw.SEVERITY_RANK[z["severity"]])
    demo = " (demo data)" if label.startswith("Simulated") else ""
    return (f"<div role='alert' style='background:{bg};border:1.5px solid {border};color:{fg};border-radius:14px;padding:10px 16px;"
            f"margin:6px 0 10px;font-weight:800;display:flex;gap:10px;align-items:center;'>"
            f"<span style='font-size:1.3rem;'>🚨</span><span>River alert{demo}: {html_mod.escape(top['param'])} "
            f"{top['value']:,.1f} on the {html_mod.escape(stretch_name())} stretch ({status}). "
            f"Open the <b>RIVER WATCH</b> tab for what to do.</span></div>")


# ---------------------------------------------------------------------------
# pieces
# ---------------------------------------------------------------------------
def _hero():
    c1, c2 = st.columns([1.15, 1])
    with c1:
        st.markdown(
            """
            <div style="padding:6px 2px;">
              <span style="background:#064e3b;color:#fff;font-size:.72rem;font-weight:800;padding:3px 10px;border-radius:999px;letter-spacing:.05em;">AQUASENTINEL R3</span>
              <div style="font-size:2rem;font-weight:900;color:#064e3b;letter-spacing:-.02em;line-height:1.15;margin:8px 0 4px;">River Watch</div>
              <div style="font-size:1rem;color:#334155;font-weight:600;line-height:1.5;">
                A solar float on a guide pole that reads the river every 15 minutes and raises an alarm when a spill passes.
                This tab turns that alarm into <b>advice for farmers</b> and an <b>incident notice for the authorities</b>.
              </div>
              <div style="margin-top:10px;background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;padding:8px 12px;font-size:.82rem;color:#92400e;font-weight:600;">
                Status, honestly: AquaSentinel R3 is designed, calculated and simulated, not yet built or tested in water.
                The readings below come from a simulator that uses the same alarm limits as the float's firmware.
              </div>
              <div style="margin-top:8px;font-size:.82rem;color:#5d6b62;font-weight:600;">
                The design pilot is the Godavari at Kopargaon. Here the demo simulates a river stretch near <b>__PLACE__</b>, so the alerts you see are for your own location.
              </div>
            </div>
            """.replace("__PLACE__", html_mod.escape(str(st.session_state.get("farm_location_name") or "your area"))), unsafe_allow_html=True)
    with c2:
        p = _img("hero-river.jpg")
        if p:
            st.image(p, width="stretch")


def _controls():
    c1, c2 = st.columns([1, 1.4])
    with c1:
        st.selectbox("Data source", ["Simulated demo", "Upload device CSV"], key="rw_source",
                     help="A deployed float would post readings every 15 minutes. Until then, use the simulator or upload a CSV.")
    with c2:
        if st.session_state.get("rw_source") == "Upload device CSV":
            up = st.file_uploader("Device CSV (time, ph, ec, do, turbidity ...)", type=["csv"], key="rw_csv_file")
            if up is not None:
                try:
                    st.session_state["rw_csv_df"] = rw.parse_csv(up)
                except Exception as exc:
                    st.session_state["rw_csv_df"] = None
                    st.error(f"Could not read that CSV: {exc}")
            elif st.session_state.get("rw_csv_df") is None:
                st.info("Upload a CSV to analyse real readings. Until then the simulator is shown.")
        else:
            st.selectbox("Simulate a river event", list(rw.SCENARIOS.keys()), key="rw_scenario",
                         help="Injects a pollution event into the last 3 hours of readings so you can see the alerts.")


def _status_card(analysis: Dict[str, Any], source: str):
    status = analysis["status"]
    fg, bg, border, headline = _STATUS_STYLE[status]
    pulse = "animation:aa-pulse 1.4s infinite;" if status == "CRITICAL" else ""
    latest = analysis["latest"]
    when = pd.Timestamp(latest["time"]).strftime("%d %b, %H:%M") if latest is not None else "n/a"
    st.markdown(
        f"""<style>@keyframes aa-pulse {{0%{{box-shadow:0 0 0 0 rgba(185,28,28,.45)}}70%{{box-shadow:0 0 0 14px rgba(185,28,28,0)}}100%{{box-shadow:0 0 0 0 rgba(185,28,28,0)}}}}</style>
        <div style="background:{bg};border:2px solid {border};border-radius:18px;padding:14px 18px;margin:8px 0;{pulse}display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;align-items:center;">
          <div><div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;color:{fg};">{html_mod.escape(stretch_name())} · {html_mod.escape(rw.DEVICE_ID)}</div>
          <div style="font-size:1.5rem;font-weight:900;color:{fg};">{status}: {headline}</div></div>
          <div style="text-align:right;font-size:.8rem;color:#475569;font-weight:600;">Latest reading {when}<br>Source: {html_mod.escape(source)}</div>
        </div>""", unsafe_allow_html=True)


def _tiles(analysis: Dict[str, Any]):
    latest = analysis["latest"]
    if latest is None:
        return
    by_param = {f["param"]: f["severity"] for f in analysis["findings"]}
    spec = [
        ("pH", "ph", "", "6.0 - 9.0", "{:.2f}"),
        ("EC", "ec", " uS/cm", "max 2,250", "{:,.0f}"),
        ("DO", "do", " mg/L", "min 4.0", "{:.2f}"),
        ("Turbidity", "turb", " NTU", "drip use < 150", "{:,.0f}"),
        ("Temp", "temp", " °C", "", "{:.1f}"),
    ]
    cols = st.columns(len(spec))
    for col, (label, key, unit, limit, fmt) in zip(cols, spec):
        v = latest.get(key)
        if v is None or pd.isna(v):
            continue
        sev = by_param.get(label, "NORMAL")
        fg, bg, border, _ = _STATUS_STYLE[sev]
        with col:
            st.markdown(
                f"""<div style="background:{bg};border:1.5px solid {border};border-radius:16px;padding:10px 12px;text-align:center;">
                <div style="font-size:.7rem;font-weight:800;color:{fg};letter-spacing:.06em;">{label.upper()}</div>
                <div style="font-size:1.45rem;font-weight:900;color:#0f172a;">{fmt.format(v)}<span style="font-size:.75rem;color:#64748b;">{unit}</span></div>
                <div style="font-size:.68rem;color:#64748b;font-weight:600;">{limit}</div></div>""", unsafe_allow_html=True)


def _charts(df: pd.DataFrame, analysis: Dict[str, Any]):
    panels = [
        ("ph", "pH", (rw.LIMIT_PH_MIN, rw.LIMIT_PH_MAX), "range"),
        ("ec", "Conductivity (uS/cm)", rw.LIMIT_EC_MAX, "max"),
        ("do", "Dissolved oxygen (mg/L)", rw.LIMIT_DO_MIN, "min"),
        ("turb", "Turbidity (NTU)", rw.WATCH_TURB, "max"),
    ]
    start = analysis.get("event_start")
    c = st.columns(2)
    for i, (key, title, limit, kind) in enumerate(panels):
        if key not in df.columns or df[key].dropna().empty:
            continue
        fig = go.Figure(go.Scatter(x=df["time"], y=df[key], mode="lines", line=dict(color="#047857", width=2.2), name=title))
        if kind == "range":
            fig.add_hrect(y0=limit[0], y1=limit[1], fillcolor="rgba(16,185,129,.10)", line_width=0)
            fig.add_hline(y=limit[0], line=dict(color="#b91c1c", dash="dash", width=1))
            fig.add_hline(y=limit[1], line=dict(color="#b91c1c", dash="dash", width=1))
        else:
            fig.add_hline(y=limit, line=dict(color="#b91c1c", dash="dash", width=1.2),
                          annotation_text=("limit" if key != "turb" else "drip limit"), annotation_position="top left")
        if start is not None:
            fig.add_vrect(x0=start, x1=df["time"].iloc[-1], fillcolor="rgba(185,28,28,.10)", line_width=0)
        fig.update_layout(title=dict(text=title, font=dict(size=13)), height=240, margin=dict(l=8, r=8, t=34, b=8),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", showlegend=False,
                          font=dict(family="Plus Jakarta Sans, Inter, sans-serif", size=11))
        with c[i % 2]:
            st.plotly_chart(fig, width="stretch")


def _alerts(analysis: Dict[str, Any], source: str, crop_name: str, lang: str):
    findings = analysis["findings"]
    if not findings:
        st.success("No alert: all readings are inside the safe limits. Pick a simulated event above to see how the alerts work.")
        return

    langs = {"English": "English", "मराठी": "Marathi", "हिन्दी": "Hindi"}
    default = {"Marathi": "मराठी", "Hindi": "हिन्दी"}.get(lang, "English")
    c1, c2 = st.columns(2)

    farmer_ctx: Dict[str, str] = {}
    with c1:
        st.markdown("<div style='font-size:1.1rem;font-weight:900;color:#064e3b;'>👨‍🌾 Alert for farmers</div>", unsafe_allow_html=True)
        pick = st.radio("Language", list(langs.keys()), index=list(langs.keys()).index(default), horizontal=True, key="rw_farmer_lang",
                        label_visibility="collapsed")
        fmsg = rw.farmer_message(analysis, crop_name, langs[pick], stretch=stretch_name())
        st.code(fmsg, language=None, wrap_lines=True)
        b1, b2 = st.columns(2)
        b1.link_button("📲 Send on WhatsApp", rw.whatsapp_link(fmsg), width="stretch")
        b2.link_button("💬 Send as SMS", rw.sms_link(fmsg), width="stretch")
        farmer_ctx["msg"] = fmsg
        st.caption("Links open your WhatsApp / SMS app with the text ready. Nothing is sent automatically.")

    with c2:
        st.markdown("<div style='font-size:1.1rem;font-weight:900;color:#7f1d1d;'>🏛️ Notice for the authorities</div>", unsafe_allow_html=True)
        gmsg = rw.government_notice(analysis, source, stretch=stretch_name())
        st.code(gmsg, language=None, wrap_lines=True)
        to = st.text_input("Authority e-mail (optional)", key="rw_gov_email", placeholder="officer@example.gov.in")
        g1, g2 = st.columns(2)
        g1.link_button("✉️ Open e-mail", rw.mailto_link(to or "", f"River water alert: {stretch_name()} ({analysis['status']})", gmsg),
                       width="stretch", disabled=not to)
        if g2.button("📌 Log incident now", key="rw_log_btn", width="stretch", help="Adds this event to the government action console"):
            row = rw.log_incident(analysis, source, farmer_ctx["msg"], gmsg, stretch=stretch_name())
            st.toast("Incident logged" if row else "Nothing to log", icon="📌")

    # CRITICAL events are logged automatically (once per event) so the console never misses one.
    if analysis["status"] == "CRITICAL":
        row = rw.log_incident(analysis, source, farmer_ctx["msg"], gmsg, stretch=stretch_name())
        if row and not st.session_state.get(f"rw_logged_{row['id']}"):
            st.session_state[f"rw_logged_{row['id']}"] = True
            st.toast("Critical incident logged for the authorities", icon="🚨")
    if os.getenv("ALERT_WEBHOOK_URL"):
        st.caption("A webhook is configured: logged incidents are also posted to it.")
    else:
        st.caption("Optional: set ALERT_WEBHOOK_URL in .env to push every logged incident to Slack, Teams, n8n or Zapier.")


_STATUSES = [("new", "New"), ("acknowledged", "Acknowledged"), ("team_dispatched", "Team dispatched"), ("resolved", "Resolved")]


def _console():
    with st.expander("🏛️ Government action console", expanded=False):
        pin = os.getenv("GOV_CONSOLE_PIN", "").strip()
        if pin:
            entered = st.text_input("Officer PIN", type="password", key="rw_gov_pin")
            if entered != pin:
                st.info("Enter the officer PIN to view and update incidents.")
                return
        else:
            st.caption("Demo mode: no officer PIN is set (GOV_CONSOLE_PIN in .env). A real deployment needs officer sign-in.")
        rows = farm_store.select("river_incidents")
        if not rows:
            st.info("No incidents logged yet. Simulate a river event above to create one.")
            return
        counts = {k: sum(1 for r in rows if r.get("status") == k) for k, _ in _STATUSES}
        cols = st.columns(len(_STATUSES))
        for col, (k, label) in zip(cols, _STATUSES):
            col.metric(label, counts[k])
        flt = st.multiselect("Show", [k for k, _ in _STATUSES], default=["new", "acknowledged", "team_dispatched"],
                             format_func=dict(_STATUSES).get, key="rw_console_filter")
        for r in [x for x in rows if x.get("status") in flt][:25]:
            fg, bg, border, _ = _STATUS_STYLE.get(r.get("severity", "WARNING"), _STATUS_STYLE["WARNING"])
            demo = " · DEMO" if str(r.get("source", "")).startswith("Simulated") else ""
            st.markdown(
                f"<div style='background:{bg};border:1.5px solid {border};border-radius:14px;padding:10px 14px;margin-top:8px;'>"
                f"<b style='color:{fg}'>{html_mod.escape(str(r.get('severity')))}</b> · {html_mod.escape(str(r.get('stretch')))}{demo} · "
                f"<span style='color:#475569'>{html_mod.escape(str(r.get('created_at', ''))[:16].replace('T', ' '))}</span><br>"
                f"{html_mod.escape(str(r.get('summary')))}</div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1.1, 2, 0.8])
            idx = [k for k, _ in _STATUSES].index(r.get("status", "new"))
            new_status = c1.selectbox("Status", [k for k, _ in _STATUSES], index=idx, format_func=dict(_STATUSES).get,
                                      key=f"rw_st_{r['id']}", label_visibility="collapsed")
            note = c2.text_input("Note", value=r.get("notes", "") or "", key=f"rw_note_{r['id']}", label_visibility="collapsed",
                                 placeholder="Action taken, sample ID, contact made ...")
            if c3.button("Update", key=f"rw_upd_{r['id']}", width="stretch"):
                farm_store.update("river_incidents", r["id"], {"status": new_status, "notes": note})
                st.rerun()
        df = pd.DataFrame(rows)[["created_at", "severity", "stretch", "summary", "status", "notes", "source"]]
        st.download_button("⬇️ Download incident log (CSV)", df.to_csv(index=False).encode("utf-8"), "river_incidents.csv",
                           "text/csv", key="rw_dl_incidents")


def _about():
    st.markdown("### Meet AquaSentinel R3")
    cols = st.columns(4)
    gallery = [("studio-bow.jpg", "The float, seen from the bow"), ("alert-red.jpg", "Beacon turns red when a spill passes"),
               ("underwater.jpg", "Sensors under the hull"), ("exploded.jpg", "Exploded view of the assembly")]
    for col, (name, cap) in zip(cols, gallery):
        p = _img(name)
        if p:
            col.image(p, caption=cap, width="stretch")
    st.markdown(
        """
        - **Reads** pH, conductivity, dissolved oxygen, turbidity, temperature and river level every 15 minutes.
        - **Decides on board** (ESP32): hard limits pH outside 6-9, DO below 4 mg/L, conductivity above 2,250 uS/cm.
        - **Acts:** red beacon, LTE alert, and one bottled sample kept for the lab.
        - **No drive motor:** the river lifts the float up and down a stainless guide pole on a bridge pier.
        - **Design figures:** 48.5 kg, about 12 days without sun, prototype cost about ₹1.87 lakh (estimates from the project dossier).
        """)
    st.link_button("Open the AquaSentinel project site", SITE_URL)


# ---------------------------------------------------------------------------
def render_river_watch_tab(lang: str = "English", crop_name: str = "your crop"):
    _hero()
    st.markdown("<br>", unsafe_allow_html=True)
    _controls()
    df, analysis, source = current_state()
    _status_card(analysis, source)
    _tiles(analysis)
    _charts(df, analysis)
    st.markdown("---")
    _alerts(analysis, source, crop_name, lang)
    st.markdown("---")
    _console()
    st.markdown("---")
    _about()
