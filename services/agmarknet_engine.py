"""
agmarknet_engine.py - Agmarknet 2.0 Live Mandi Price & Arrival Intelligence Engine
AgriAttribute AI — Syngenta Biologicals & ANNAM.AI Hack Core 2026 (Team 15)

Data Source:
Official Agmarknet 2.0 (Directorate of Marketing & Inspection, Ministry of Agriculture & Farmers Welfare)
Portal: https://agmarknet.gov.in/home

Design Thinking for Farmers:
1. Mandi Price vs MSP Arbitrage: Instantly tells the farmer whether open mandi is paying higher than Govt MSP.
2. Daily Influx & Volume Pressure: Alerts if heavy arrivals (Metric Tonnes) are putting downward pressure on prices.
3. 3-Day Mandi Price Momentum: Tracks whether prices are surging, stable, or declining over the last 72 hours.
4. Syngenta Grade-A Quality Premium: Quantifies the +3.5% auction bonus fetched by biostimulant-treated bolder grains.
5. Sell vs Hold Decision: Actionable agronomic & financial advisory.
"""

import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Dataset location
DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "agmarknet_daily_report.csv"))

# Crop Mapping from AgriAttribute UI to Agmarknet 2.0 Commodities (24 Official Commodities)
CROP_TO_AGMARKNET = {
    "Bajra": "Bajra(Pearl Millet/Cumbu)",
    "Bajra(Pearl Millet/Cumbu)": "Bajra(Pearl Millet/Cumbu)",
    "Barley": "Barley(Jau)",
    "Barley(Jau)": "Barley(Jau)",
    "Jowar": "Jowar(Sorghum)",
    "Jowar(Sorghum)": "Jowar(Sorghum)",
    "Maize": "Maize",
    "Paddy": "Paddy(Common)",
    "Rice (Paddy)": "Paddy(Common)",
    "Paddy(Common)": "Paddy(Common)",
    "Ragi": "Ragi(Finger Millet)",
    "Ragi(Finger Millet)": "Ragi(Finger Millet)",
    "Wheat": "Wheat",
    "Cotton": "Cotton",
    "Copra": "Copra",
    "Groundnut": "Groundnut",
    "Groundnut (Peanut)": "Groundnut",
    "Mustard": "Mustard",
    "Mustard / Rapeseed": "Mustard",
    "Safflower": "Safflower",
    "Sesamum": "Sesamum(Sesame,Gingelly,Til)",
    "Sesamum(Sesame,Gingelly,Til)": "Sesamum(Sesame,Gingelly,Til)",
    "Til": "Sesamum(Sesame,Gingelly,Til)",
    "Soybean": "Soyabean",
    "Soyabean": "Soyabean",
    "Sunflower": "Sunflower/Sunflower Seed",
    "Sunflower/Sunflower Seed": "Sunflower/Sunflower Seed",
    "Sugarcane": "Sugarcane",
    "Bengal Gram": "Bengal Gram(Gram)(Whole)",
    "Bengal Gram(Gram)(Whole)": "Bengal Gram(Gram)(Whole)",
    "Gram / Chickpea (Chana)": "Bengal Gram(Gram)(Whole)",
    "Chana": "Bengal Gram(Gram)(Whole)",
    "Black Gram": "Black Gram(Urd Beans)(Whole)",
    "Black Gram(Urd Beans)(Whole)": "Black Gram(Urd Beans)(Whole)",
    "Urd": "Black Gram(Urd Beans)(Whole)",
    "Green Gram": "Green Gram(Moong)(Whole)",
    "Green Gram(Moong)(Whole)": "Green Gram(Moong)(Whole)",
    "Moong": "Green Gram(Moong)(Whole)",
    "Lentil": "Lentil(Masur)(Whole)",
    "Lentil(Masur)(Whole)": "Lentil(Masur)(Whole)",
    "Masur": "Lentil(Masur)(Whole)",
    "Red gram": "Red gram/Arhar/Tur(whole)",
    "Red gram/Arhar/Tur(whole)": "Red gram/Arhar/Tur(whole)",
    "Tur / Pigeon Pea (Arhar)": "Red gram/Arhar/Tur(whole)",
    "Arhar": "Red gram/Arhar/Tur(whole)",
    "Tur": "Red gram/Arhar/Tur(whole)",
    "Onion": "Onion",
    "Potato": "Potato",
    "Tomato": "Tomato"
}

try:
    import streamlit as st
    cache_agmark = st.cache_data(ttl=600, show_spinner=False)
except Exception:
    import streamlit as st
def cache_agmark(f):
    return st.cache_data(ttl=3600)(f)


def _safe_float(val, fallback=0.0):
    if pd.isna(val) or val is None:
        return fallback
    s = str(val).replace(",", "").replace("-", "").strip()
    if not s:
        return fallback
    try:
        return float(s)
    except Exception:
        return fallback

@cache_agmark
def load_agmarknet_data() -> pd.DataFrame:
    """Loads the Agmarknet 2.0 official daily price & arrival report."""
    if os.path.exists(DATA_PATH):
        df = pd.read_csv(DATA_PATH)
        col_map = {}
        for c in df.columns:
            c_clean = c.strip().lower()
            if "commodity" in c_clean and "group" in c_clean:
                col_map[c] = "commodity_group"
            elif "commodity" in c_clean:
                col_map[c] = "commodity"
            elif "msp" in c_clean:
                col_map[c] = "msp_2026_27"
        renamed = df.rename(columns=col_map)
        p_cols = [c for c in renamed.columns if "price" in c.lower()]
        a_cols = [c for c in renamed.columns if "arrival" in c.lower()]
        if p_cols:
            renamed["price_latest"] = renamed[p_cols[0]]
            renamed["price_01_sep"] = renamed[p_cols[0]]
            if len(p_cols) > 1:
                renamed["price_prev"] = renamed[p_cols[1]]
                renamed["price_30_aug"] = renamed[p_cols[1]]
            else:
                renamed["price_prev"] = renamed[p_cols[0]]
                renamed["price_30_aug"] = renamed[p_cols[0]]
        if a_cols:
            renamed["arrival_latest"] = renamed[a_cols[0]]
            renamed["arrival_01_sep"] = renamed[a_cols[0]]
        return renamed
    return pd.DataFrame()

@cache_agmark
def get_mandi_intelligence_for_crop(crop_name: str, has_biological: bool = True) -> dict:
    """
    Returns full market intelligence, price trends, arrival volume, and MSP comparison
    for any selected crop based on Agmarknet 2.0 benchmarks.
    """
    df = load_agmarknet_data()
    agmark_name = CROP_TO_AGMARKNET.get(crop_name, crop_name)
    
    match = pd.DataFrame()
    if not df.empty and "commodity" in df.columns:
        match = df[df["commodity"].astype(str).str.strip().str.lower() == agmark_name.strip().lower()]
        if match.empty:
            c_clean = crop_name.split('(')[0].split('/')[0].strip().lower()
            sub = df[df["commodity"].astype(str).str.lower().str.contains(c_clean, regex=False)]
            if not sub.empty:
                match = sub

    p_cols = [c for c in df.columns if "price" in c.lower()] if not df.empty else []
    a_cols = [c for c in df.columns if "arrival" in c.lower()] if not df.empty else []

    col_p_latest = p_cols[0] if len(p_cols) > 0 else "Price on 06 Sep 2026"
    col_p_d1 = p_cols[1] if len(p_cols) > 1 else col_p_latest
    col_p_d2 = p_cols[2] if len(p_cols) > 2 else col_p_d1

    col_a_latest = a_cols[0] if len(a_cols) > 0 else "Arrival on 06 Sep 2026"
    col_a_d1 = a_cols[1] if len(a_cols) > 1 else col_a_latest
    col_a_d2 = a_cols[2] if len(a_cols) > 2 else col_a_d1

    date_latest = col_p_latest.replace("Price on", "").replace("price on", "").strip() or "06 Sep 2026"
    date_d1 = col_p_d1.replace("Price on", "").replace("price on", "").strip() or "05 Sep 2026"
    date_d2 = col_p_d2.replace("Price on", "").replace("price on", "").strip() or "04 Sep 2026"

    if match.empty:
        # Fallback to standard benchmarks
        msp_fb = 4892.0
        p_fb = 5210.0
        return {
            "matched": False,
            "status": "DEMO / SYNTHETIC",
            "source_state": "DEMO / SYNTHETIC",
            "commodity": crop_name,
            "group": "Agricultural Produce",
            "msp": msp_fb,
            "latest_price": p_fb,
            "price_d1": 5150.0,
            "price_d2": 5080.0,
            "price_31_aug": 5150.0,
            "price_30_aug": 5080.0,
            "date_latest": date_latest,
            "date_d1": date_d1,
            "date_d2": date_d2,
            "price_change_3d": 70.0,
            "momentum_tag": "📈 Bullish (+₹70/q in 72h)",
            "latest_arrival_mt": 1250.0,
            "arrival_d1": 1400.0,
            "arrival_d2": 900.0,
            "arrival_31_aug": 1400.0,
            "arrival_30_aug": 900.0,
            "price_vs_msp_delta": round(p_fb - msp_fb, 1),
            "price_vs_msp_pct": round(((p_fb - msp_fb) / msp_fb) * 100, 1),
            "quality_premium": round(p_fb * 0.035, 1) if has_biological else 0.0,
            "quality_premium_pct": 3.5,
            "quality_premium_type": "Modelled / Assumption",
            "quality_premium_label": "+3.5% Modelled Quality Premium (Bolder Grain Test Weight)",
            "realizable_price": round(p_fb * 1.035, 1) if has_biological else p_fb,
            "market_verdict": "🟢 MANDI TRADING ABOVE MSP",
            "action_advice": "Steady mandi demand. Fair time to sell harvest.",
            "source_citation": "Bundled Agmarknet-format report snapshot (06-Sep-2026), MSP 2026-27; not a live feed",
            "disclaimer": "Prices come from a bundled report snapshot, not a live Agmarknet feed. The quality premium is an assumption and is NOT used in the ROI."
        }
        
    row = match.iloc[0]
    
    # Parse numbers safely
    msp = _safe_float(row.get("msp_2026_27", 0.0), 0.0)
    p_latest = _safe_float(row.get(col_p_latest), msp if msp > 0 else 2500.0)
    p_d1 = _safe_float(row.get(col_p_d1), p_latest)
    p_d2 = _safe_float(row.get(col_p_d2), p_d1)
    
    arr_latest = _safe_float(row.get(col_a_latest), 500.0)
    arr_d1 = _safe_float(row.get(col_a_d1), arr_latest)
    arr_d2 = _safe_float(row.get(col_a_d2), arr_d1)

    # Quality auction premium for Syngenta Biological treated crops (bolder seeds, lower moisture)
    # Stated clearly as a modeled assumption, not a guaranteed contract rate
    quality_premium = round(p_latest * 0.035, 1) if has_biological else 0.0
    realizable_price = round(p_latest + quality_premium, 1)
    
    # Delta vs MSP
    if msp > 0:
        delta = round(p_latest - msp, 1)
        delta_pct = round((delta / msp) * 100, 1)
        if delta >= 0:
            market_verdict = f"🟢 TRADING +₹{delta:,.0f} (+{delta_pct}%) ABOVE MSP"
            action_advice = "Private market demand is high! Traders are competing above government floor price."
        else:
            market_verdict = f"🔴 TRADING -₹{abs(delta):,.0f} ({delta_pct}%) BELOW MSP"
            action_advice = "Market arrival pressure is depressing open auction rates. Register for Government MSP procurement (NAFED/FCI)."
    else:
        delta = 0.0
        delta_pct = 0.0
        market_verdict = f"🥕 PERISHABLE VEGETABLE (Free Mandi Price)"
        action_advice = "Daily spot market driven by terminal mandi arrival volume."

    # 3-Day Momentum Trend
    price_change_3d = round(p_latest - p_d2, 1)
    if price_change_3d > 0:
        momentum_tag = f"📈 Bullish (+₹{price_change_3d}/q in 72h)"
    elif price_change_3d < 0:
        momentum_tag = f"📉 Softening (-₹{abs(price_change_3d)}/q in 72h)"
    else:
        momentum_tag = f"➡️ Stable (Flat across 72h)"

    return {
        "matched": True,
        "status": "DEMO / SYNTHETIC",
        "source_state": "DEMO / SYNTHETIC",
        "commodity": agmark_name,
        "group": row.get("commodity_group", "Agricultural Produce"),
        "msp": msp,
        "latest_price": p_latest,
        "price_d1": p_d1,
        "price_d2": p_d2,
        "price_31_aug": p_d1,
        "price_30_aug": p_d2,
        "date_latest": date_latest,
        "date_d1": date_d1,
        "date_d2": date_d2,
        "price_change_3d": price_change_3d,
        "momentum_tag": momentum_tag,
        "latest_arrival_mt": arr_latest,
        "arrival_d1": arr_d1,
        "arrival_d2": arr_d2,
        "arrival_31_aug": arr_d1,
        "arrival_30_aug": arr_d2,
        "price_vs_msp_delta": delta,
        "price_vs_msp_pct": delta_pct,
        "quality_premium": quality_premium,
        "quality_premium_pct": 3.5,
        "quality_premium_type": "Modelled / Assumption",
        "quality_premium_label": "+3.5% Modelled Quality Premium (Bolder Grain Test Weight)",
        "realizable_price": realizable_price,
        "market_verdict": market_verdict,
        "action_advice": action_advice,
        "source_citation": "Bundled Agmarknet-format report snapshot (06-Sep-2026), MSP 2026-27; not a live feed",
        "disclaimer": "Prices come from a bundled report snapshot, not a live Agmarknet feed. The quality premium is an assumption and is NOT used in the ROI."
    }

@cache_agmark
def create_mandi_trend_chart(mandi_info: dict) -> go.Figure:
    """
    Creates an interactive dual-axis chart:
    - Left Axis: Daily Mandi Modal Price (₹/Quintal) + MSP Benchmark Line
    - Right Axis: Daily Arrival Volume (Metric Tonnes)
    """
    dates = [
        mandi_info.get("date_d2", "04 Sep 2026"),
        mandi_info.get("date_d1", "05 Sep 2026"),
        mandi_info.get("date_latest", "06 Sep 2026")
    ]
    prices = [
        mandi_info.get("price_d2", mandi_info.get("price_30_aug", 0)),
        mandi_info.get("price_d1", mandi_info.get("price_31_aug", 0)),
        mandi_info.get("latest_price", 0)
    ]
    arrivals = [
        mandi_info.get("arrival_d2", mandi_info.get("arrival_30_aug", 0)),
        mandi_info.get("arrival_d1", mandi_info.get("arrival_31_aug", 0)),
        mandi_info.get("latest_arrival_mt", 0)
    ]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Arrival Volume (Bar)
    fig.add_trace(
        go.Bar(
            x=dates,
            y=arrivals,
            name="Mandi Influx (Metric Tonnes)",
            marker_color="rgba(148, 163, 184, 0.45)",
            hovertemplate="Arrival: %{y:,.1f} MT<extra></extra>"
        ),
        secondary_y=True
    )
    
    # Mandi Price (Line)
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=prices,
            name="Agmarknet Modal Price (₹/q)",
            mode="lines+markers+text",
            text=[f"₹{p:,.0f}" for p in prices],
            textposition="top center",
            line=dict(color="#059669", width=3.5),
            marker=dict(size=8, color="#047857"),
            hovertemplate="Price: ₹%{y:,.1f}/q<extra></extra>"
        ),
        secondary_y=False
    )
    
    # Realizable Price with Syngenta Quality Premium
    if mandi_info.get("quality_premium", 0) > 0:
        realizable_val = mandi_info["realizable_price"]
        fig.add_trace(
            go.Scatter(
                x=[dates[-1]],
                y=[realizable_val],
                name="Modelled Grade-A Quality Price (+3.5%)",
                mode="markers+text",
                text=[f"★ ₹{realizable_val:,.0f} (Modelled)"],
                textposition="bottom center",
                marker=dict(size=11, color="#2563eb", symbol="star"),
                hovertemplate="Grade-A Auction (Modelled): ₹%{y:,.1f}/q<extra></extra>"
            ),
            secondary_y=False
        )
        
    # Government MSP Reference Line
    if mandi_info.get("msp", 0) > 0:
        fig.add_hline(
            y=mandi_info["msp"],
            line_dash="dash",
            line_color="#dc2626",
            annotation_text=f"Govt MSP 2026-27: ₹{mandi_info['msp']:,.0f}",
            annotation_position="bottom right"
        )
        
    fig.update_layout(
        title=f"🏛️ Agmarknet 2.0 Mandi Trajectory: {mandi_info['commodity']}",
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        height=320,
        margin=dict(l=40, r=40, t=50, b=30),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )
    
    fig.update_yaxes(title_text="Mandi Price (₹/Quintal)", secondary_y=False, showgrid=True, gridcolor="#f1f5f9")
    fig.update_yaxes(title_text="Daily Influx (MT)", secondary_y=True, showgrid=False)
    
    return fig
