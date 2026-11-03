"""
river_watch.py - AquaSentinel River Watch: river water-quality alerts for farmers and government.

AquaSentinel R3 is a solar float on a guide pole that reads pH, conductivity (EC), dissolved oxygen
(DO), turbidity, temperature and river level every 15 minutes and raises an alert when a limit is
crossed (see the AquaSentinel firmware config.h). The float is at design stage, so this module can
run on three kinds of input:

  * a SIMULATOR that reproduces typical pollution events (used for the demo),
  * an uploaded CSV exported from a device,
  * (later) live readings from deployed floats.

It applies the same hard limits as the firmware, then turns findings into

  * a plain-language FARMER alert (English / Marathi / Hindi) with irrigation and livestock advice,
  * a formal GOVERNMENT incident notice with evidence and recommended actions,
  * a logged incident that officers can acknowledge, dispatch and close.

No message is ever sent silently: sharing uses WhatsApp / SMS / e-mail links, and an optional
ALERT_WEBHOOK_URL (Slack, Teams, n8n, Zapier ...) receives the incident JSON when configured.
"""

import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from services import farm_store

# --- AquaSentinel firmware limits (06_ELECTRONICS_AND_FIRMWARE/.../config.h) -----------------------
LIMIT_PH_MIN = 6.0
LIMIT_PH_MAX = 9.0
LIMIT_DO_MIN = 4.0      # mg/L, CPCB Class C/D criterion
LIMIT_EC_MAX = 2250.0   # uS/cm, CPCB Class E limit; also the "very high salinity" class for irrigation water
WARN_PH = (6.5, 8.5)
WARN_DO = 5.0
WARN_EC = 1500.0
WATCH_TURB = 150.0      # NTU - AgriAttribute advisory (drip emitters clog), not a firmware limit

STRETCH = "GODAVARI-KOPARGAON"   # the design pilot site; the app passes the visitor's own location instead
DEVICE_ID = "AQS-DEV-01"
STRETCH_LAT, STRETCH_LON = 19.8825, 74.4785   # approximate

SCENARIOS = {
    "Normal day": "normal",
    "Industrial / saline discharge (EC spike)": "salt",
    "Sewage or organic effluent (oxygen crash)": "sewage",
    "Acid discharge (pH drops)": "acid",
    "Alkaline / lime discharge (pH rises)": "alkali",
    "Monsoon flood pulse (muddy water)": "flood",
}

SEVERITY_RANK = {"NORMAL": 0, "WATCH": 1, "WARNING": 2, "CRITICAL": 3}


# =============================================================================
# 1. DATA: simulator and CSV import
# =============================================================================

def simulate_readings(scenario: str = "normal", hours: int = 48, step_min: int = 15, seed: int = 7) -> pd.DataFrame:
    """Plausible Godavari readings with an optional pollution event in the last ~3 hours."""
    rng = np.random.default_rng(seed)
    n = int(hours * 60 / step_min)
    end = datetime.now().replace(second=0, microsecond=0)
    t = [end - timedelta(minutes=step_min * (n - 1 - i)) for i in range(n)]
    hod = np.array([(x.hour + x.minute / 60.0) for x in t])
    diel = np.sin((hod - 9) / 24.0 * 2 * np.pi)

    ph = 7.6 + 0.12 * diel + rng.normal(0, 0.04, n)
    ec = 680 + 25 * diel + rng.normal(0, 18, n)
    do = 7.4 + 1.3 * diel + rng.normal(0, 0.12, n)
    turb = 28 + rng.normal(0, 3, n)
    temp = 27 + 2.2 * diel + rng.normal(0, 0.1, n)
    level = 2.1 + rng.normal(0, 0.01, n)

    k = 12  # event length in samples (3 h)
    ramp = np.clip(np.arange(n - k, n) - (n - k), 0, None)
    ramp = np.minimum(1.0, (ramp + 1) / 6.0)          # reaches full effect after 6 samples (90 min)
    sl = slice(n - k, n)
    if scenario == "salt":
        ec[sl] += ramp * 2900 + rng.normal(0, 40, k)
        do[sl] -= ramp * 0.8
    elif scenario == "sewage":
        do[sl] -= ramp * 5.6
        turb[sl] += ramp * 95
        ec[sl] += ramp * 650
        ph[sl] -= ramp * 0.5
    elif scenario == "acid":
        ph[sl] -= ramp * 2.9
        ec[sl] += ramp * 1200
    elif scenario == "alkali":
        ph[sl] += ramp * 2.4
        ec[sl] += ramp * 700
    elif scenario == "flood":
        turb[sl] += ramp * 420
        level[sl] += ramp * 1.6
        do[sl] -= ramp * 0.9

    return pd.DataFrame({"time": t, "ph": ph, "ec": ec, "do": do, "turb": turb, "temp": temp, "level_m": level})


_ALIASES = {
    "time": ["time", "timestamp", "datetime", "date_time", "ts"],
    "ph": ["ph"],
    "ec": ["ec", "ec_us_cm", "conductivity", "conductivity_us_cm"],
    "do": ["do", "do_mgl", "do_mg_l", "dissolved_oxygen"],
    "turb": ["turb", "turbidity", "turbidity_ntu", "ntu"],
    "temp": ["temp", "temperature", "water_temp", "temp_c"],
    "level_m": ["level_m", "level", "river_level_m", "stage_m"],
}


def parse_csv(file_like) -> pd.DataFrame:
    """Reads a device CSV; accepts common column names, needs a time column and at least one reading."""
    df = pd.read_csv(file_like)
    df.columns = [str(c).strip().lower().replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_") for c in df.columns]
    out = pd.DataFrame()
    for target, names in _ALIASES.items():
        for n in names:
            if n in df.columns:
                out[target] = df[n]
                break
    if "time" not in out.columns:
        raise ValueError("CSV needs a time column (time, timestamp or datetime).")
    if not any(c in out.columns for c in ("ph", "ec", "do", "turb")):
        raise ValueError("CSV needs at least one of: ph, ec, do, turbidity.")
    out["time"] = pd.to_datetime(out["time"], errors="coerce")
    out = out.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    for c in out.columns:
        if c != "time":
            out[c] = pd.to_numeric(out[c], errors="coerce")
    return out


# =============================================================================
# 2. DETECTION (same hard limits as the firmware + a simple rate-of-change check)
# =============================================================================

def evaluate_row(row: pd.Series) -> List[Dict[str, Any]]:
    """Findings for one reading. Each finding: param, value, limit_text, severity, rule."""
    f: List[Dict[str, Any]] = []

    def add(param, value, limit_text, severity, rule):
        f.append({"param": param, "value": float(value), "limit_text": limit_text, "severity": severity, "rule": rule})

    v = row.get("ph")
    if pd.notna(v):
        if v < LIMIT_PH_MIN or v > LIMIT_PH_MAX:
            add("pH", v, f"{LIMIT_PH_MIN:g}-{LIMIT_PH_MAX:g}", "CRITICAL", "HARD_LIMIT: pH out of range")
        elif v < WARN_PH[0] or v > WARN_PH[1]:
            add("pH", v, f"{WARN_PH[0]:g}-{WARN_PH[1]:g} preferred", "WARNING", "pH approaching limit")
    v = row.get("do")
    if pd.notna(v):
        if v < LIMIT_DO_MIN:
            add("DO", v, f">= {LIMIT_DO_MIN:g} mg/L", "CRITICAL", "HARD_LIMIT: hypoxia")
        elif v < WARN_DO:
            add("DO", v, f">= {WARN_DO:g} mg/L preferred", "WARNING", "dissolved oxygen falling")
    v = row.get("ec")
    if pd.notna(v):
        if v > LIMIT_EC_MAX:
            add("EC", v, f"<= {LIMIT_EC_MAX:,.0f} uS/cm", "CRITICAL", "HARD_LIMIT: conductivity")
        elif v > WARN_EC:
            add("EC", v, f"<= {WARN_EC:,.0f} uS/cm preferred", "WARNING", "conductivity rising")
    v = row.get("turb")
    if pd.notna(v) and v > WATCH_TURB:
        add("Turbidity", v, f"<= {WATCH_TURB:g} NTU for drip use", "WATCH", "muddy water")
    return f


def analyse(df: pd.DataFrame) -> Dict[str, Any]:
    """Overall status from the latest reading, plus when the current event started."""
    if df is None or df.empty:
        return {"status": "NORMAL", "findings": [], "event_start": None, "latest": None, "anomaly": None}
    latest = df.iloc[-1]
    findings = evaluate_row(latest)

    # Rate-of-change check (mirrors the firmware's anomaly engine in spirit): EC +60 % in 30 min.
    anomaly = None
    if "ec" in df.columns and len(df) >= 3 and pd.notna(df["ec"].iloc[-3]) and df["ec"].iloc[-3] > 0:
        jump = df["ec"].iloc[-1] / df["ec"].iloc[-3] - 1.0
        if jump > 0.60:
            anomaly = f"Conductivity jumped {jump * 100:.0f}% in 30 minutes"
            if not any(x["param"] == "EC" for x in findings):
                findings.append({"param": "EC", "value": float(df["ec"].iloc[-1]), "limit_text": "sudden rise",
                                 "severity": "WARNING", "rule": "ANOMALY: rapid rise"})

    status = "NORMAL"
    for x in findings:
        if SEVERITY_RANK[x["severity"]] > SEVERITY_RANK[status]:
            status = x["severity"]

    # event start = first reading of the latest unbroken run in which any finding is active
    event_start = None
    if findings:
        for i in range(len(df) - 1, -1, -1):
            if evaluate_row(df.iloc[i]):
                event_start = df["time"].iloc[i]
            else:
                break
    return {"status": status, "findings": findings, "event_start": event_start, "latest": latest, "anomaly": anomaly}


def probable_cause(findings: List[Dict[str, Any]]) -> str:
    p = {x["param"]: x for x in findings}
    if "pH" in p:
        return ("acidic industrial discharge" if p["pH"]["value"] < 7 else "alkaline / lime-based discharge") + " (indicative)"
    if "DO" in p:
        return "untreated sewage or high-organic effluent such as distillery / sugar-mill wastewater (indicative)"
    if "EC" in p:
        return "saline or industrial effluent, e.g. process wastewater or spent wash (indicative)"
    if "Turbidity" in p:
        return "flood runoff or upstream silt release (indicative)"
    return "no abnormal pattern"


# =============================================================================
# 3. MESSAGES
# =============================================================================

def _lang_code(lang: str) -> str:
    l = (lang or "English").lower()
    return "mr" if l.startswith("mar") else "hi" if l.startswith("hin") else "en"


_FARMER = {
    "en": {
        "head": "RIVER WATER ALERT - {stretch}",
        "EC": "Salt level in the river (EC {v:,.0f} uS/cm) is above the safe limit. Do NOT irrigate {crop} with river water until the all-clear. Use borewell or stored water if you can.",
        "pH": "River water acidity/alkalinity (pH {v:.1f}) is unsafe. Do not irrigate {crop} or water animals from the river until the all-clear.",
        "DO": "Oxygen in the river is very low (DO {v:.1f} mg/L): fish may die and the water may be contaminated. Keep animals and people away from the water and do not use it for irrigation.",
        "Turbidity": "River water is very muddy (turbidity {v:.0f} NTU). Let it settle and filter it before using it in drip lines, or the emitters will clog.",
        "tail": "Do not drink untreated river water. Wait for an all-clear message from the local authority.",
        "ok": "River water is within safe limits right now.",
    },
    "mr": {
        "head": "नदी पाणी इशारा - {stretch}",
        "EC": "नदीतील क्षाराचे प्रमाण (EC {v:,.0f} uS/cm) सुरक्षित मर्यादेपेक्षा जास्त आहे. 'सुरक्षित' संदेश येईपर्यंत {crop} ला नदीच्या पाण्याने पाणी देऊ नका. शक्य असल्यास विहीर/बोअरवेल किंवा साठवलेले पाणी वापरा.",
        "pH": "नदीच्या पाण्याचा आम्लता/क्षारता (pH {v:.1f}) धोकादायक आहे. 'सुरक्षित' संदेश येईपर्यंत {crop} ला पाणी देऊ नका आणि जनावरांना नदीचे पाणी पाजू नका.",
        "DO": "नदीतील ऑक्सिजन खूप कमी आहे (DO {v:.1f} mg/L): मासे मरू शकतात आणि पाणी दूषित असू शकते. जनावरे व माणसांना पाण्यापासून दूर ठेवा; सिंचनासाठी वापरू नका.",
        "Turbidity": "नदीचे पाणी खूप गढूळ आहे (गढूळता {v:.0f} NTU). ठिबक सिंचनात वापरण्यापूर्वी पाणी थिरू द्या व गाळून घ्या, नाहीतर ड्रिपर बंद पडतील.",
        "tail": "नदीचे प्रक्रिया न केलेले पाणी पिऊ नका. स्थानिक प्रशासनाच्या 'सुरक्षित' संदेशाची वाट पाहा.",
        "ok": "नदीचे पाणी सध्या सुरक्षित मर्यादेत आहे.",
    },
    "hi": {
        "head": "नदी जल चेतावनी - {stretch}",
        "EC": "नदी में नमक/क्षार का स्तर (EC {v:,.0f} uS/cm) सुरक्षित सीमा से अधिक है। 'सब ठीक' संदेश आने तक {crop} की सिंचाई नदी के पानी से न करें। हो सके तो बोरवेल या संग्रहित पानी का उपयोग करें।",
        "pH": "नदी के पानी की अम्लीयता/क्षारीयता (pH {v:.1f}) असुरक्षित है। 'सब ठीक' संदेश तक {crop} की सिंचाई न करें और पशुओं को नदी का पानी न पिलाएं।",
        "DO": "नदी में ऑक्सीजन बहुत कम है (DO {v:.1f} mg/L): मछलियां मर सकती हैं और पानी दूषित हो सकता है। पशुओं और लोगों को पानी से दूर रखें; सिंचाई में उपयोग न करें।",
        "Turbidity": "नदी का पानी बहुत गंदला है (गंदलापन {v:.0f} NTU)। ड्रिप में इस्तेमाल से पहले पानी को बैठने दें और छानें, वरना ड्रिपर जाम हो जाएंगे।",
        "tail": "नदी का बिना उपचार वाला पानी न पिएं। स्थानीय प्रशासन के 'सब ठीक' संदेश की प्रतीक्षा करें।",
        "ok": "नदी का पानी अभी सुरक्षित सीमा में है।",
    },
}


def farmer_message(analysis: Dict[str, Any], crop: str, lang: str = "English", stretch: str = STRETCH) -> str:
    code = _lang_code(lang)
    tpl = _FARMER[code]
    findings = analysis.get("findings", [])
    if not findings:
        return tpl["ok"]
    lines = [tpl["head"].format(stretch=stretch)]
    seen = set()
    for x in sorted(findings, key=lambda z: -SEVERITY_RANK[z["severity"]]):
        if x["param"] in seen or x["param"] not in tpl:
            continue
        seen.add(x["param"])
        lines.append("- " + tpl[x["param"]].format(v=x["value"], crop=crop))
    lines.append(tpl["tail"])
    return "\n".join(lines)


AUTHORITIES = [
    "Maharashtra Pollution Control Board - regional office",
    "District Collector / District Disaster Management Authority",
    "Water Resources (Irrigation) Department - lift-irrigation schemes",
    "Municipal council / water-supply scheme operators downstream",
]


def government_notice(analysis: Dict[str, Any], source: str, stretch: str = STRETCH, device_id: str = DEVICE_ID) -> str:
    findings = analysis.get("findings", [])
    latest = analysis.get("latest")
    when = pd.Timestamp(latest["time"]).strftime("%d %b %Y %H:%M") if latest is not None else "n/a"
    start = analysis.get("event_start")
    since = pd.Timestamp(start).strftime("%d %b %Y %H:%M") if start is not None else when
    demo = "[DEMO / SIMULATED DATA - not a real incident]\n" if source.startswith("Simulated") else ""
    lines = [
        demo + "INCIDENT NOTICE - River water-quality exceedance",
        f"Stretch: {stretch}   Device: {device_id}   Severity: {analysis.get('status', 'NORMAL')}",
        f"First detected: {since}   Latest reading: {when}",
        "Findings:",
    ]
    for x in sorted(findings, key=lambda z: -SEVERITY_RANK[z["severity"]]):
        unit = {"EC": " uS/cm", "DO": " mg/L", "Turbidity": " NTU", "pH": ""}.get(x["param"], "")
        lines.append(f"  - {x['param']}: {x['value']:,.1f}{unit} (limit {x['limit_text']}) [{x['severity']}, {x['rule']}]")
    if analysis.get("anomaly"):
        lines.append(f"  - Trend: {analysis['anomaly']}")
    lines += [
        f"Probable cause class: {probable_cause(findings)}",
        "Recommended actions:",
        "  1. Dispatch an inspection team to upstream discharge points (industry, distillery, sewage outfalls).",
        "  2. Collect and seal a lab sample at the monitoring site (the AquaSentinel float bottles one sample at trigger).",
        "  3. Advise downstream lift-irrigation schemes and water-supply intakes to pause abstraction until cleared.",
        "  4. Issue a public advisory to farmers, livestock keepers and fisherfolk along the stretch.",
        "  5. Re-test after 2 hours and record the all-clear time.",
        "Notify: " + "; ".join(AUTHORITIES),
    ]
    return "\n".join(lines)


# =============================================================================
# 4. INCIDENT LOG (government console)
# =============================================================================

def log_incident(analysis: Dict[str, Any], source: str, farmer_msg: str, gov_msg: str, stretch: str = STRETCH) -> Optional[Dict[str, Any]]:
    """Creates one incident per event (de-duplicated by stretch + event start). Returns the row, or None."""
    if analysis["status"] not in ("WARNING", "CRITICAL"):
        return None
    start = analysis.get("event_start")
    event_key = f"{stretch}|{pd.Timestamp(start).isoformat() if start is not None else 'na'}|{source[:9]}"
    for r in farm_store.select("river_incidents"):
        if r.get("event_key") == event_key:
            return r
    top = max(analysis["findings"], key=lambda z: SEVERITY_RANK[z["severity"]])
    row = {
        "event_key": event_key, "stretch": stretch, "device_id": DEVICE_ID,
        "severity": analysis["status"], "parameter": top["param"], "value": top["value"], "limit_text": top["limit_text"],
        "summary": f"{top['param']} {top['value']:,.1f} (limit {top['limit_text']})",
        "farmer_message": farmer_msg, "gov_message": gov_msg, "status": "new", "notes": "", "source": source,
    }
    saved = farm_store.insert("river_incidents", row)
    send_webhook(saved)
    return saved


def send_webhook(incident: Dict[str, Any]) -> bool:
    """POSTs the incident JSON to ALERT_WEBHOOK_URL if set (Slack/Teams/n8n/Zapier). Returns True on 2xx."""
    url = os.getenv("ALERT_WEBHOOK_URL", "").strip()
    if not url:
        return False
    try:
        import requests
        text = f"[{incident.get('severity')}] {incident.get('stretch')}: {incident.get('summary')}"
        r = requests.post(url, json={"text": text, "incident": incident}, timeout=6)
        return 200 <= r.status_code < 300
    except Exception:
        return False


def whatsapp_link(text: str) -> str:
    return "https://wa.me/?text=" + urllib.parse.quote(text)


def sms_link(text: str) -> str:
    return "sms:?body=" + urllib.parse.quote(text)


def mailto_link(to: str, subject: str, body: str) -> str:
    return f"mailto:{urllib.parse.quote(to)}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
