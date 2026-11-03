"""
economics.py - the one place where yield, dose, cost and ROI meet.

Everything here is plain arithmetic with explicit units, so it can be unit-tested (tests/test_economics.py)
and reproduced by hand:

    net return (₹/acre) = (treated yield - baseline yield) [q/acre] × price [₹/q] - treatment cost [₹/acre]
    ROI (%)             = net return / treatment cost × 100

Units used across the app: yield in quintal per acre, price in ₹ per quintal, cost in ₹ per acre,
fertiliser in kg per hectare (Soil Health Card convention, converted here), dose in litres per acre.

The model inputs that are not measured for the farm (season rainfall, GDD, NDVI) come from
models/season_normals.json: per-crop medians of the (simulated) training data, so the model is never
asked about conditions it has not seen. The app labels them as "season normal", never as live.
"""

import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional

ACRES_PER_HA = 2.4711
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


@lru_cache(maxsize=1)
def _normals() -> Dict[str, Dict[str, float]]:
    try:
        with open(os.path.join(_ROOT, "models", "season_normals.json"), encoding="utf-8") as f:
            return json.load(f).get("crops", {})
    except Exception:
        return {}


@lru_cache(maxsize=1)
def model_report() -> Dict[str, Any]:
    """Per-crop held-out metrics and treatment-effect recovery (pipeline/evaluate_model.py)."""
    try:
        with open(os.path.join(_ROOT, "models", "per_crop_metrics.json"), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def season_inputs(crop: str, live_temp_c: Optional[float] = None) -> Dict[str, Any]:
    """Season-level model inputs for a crop. Temperature is the live reading clipped to the trained range."""
    n = _normals().get(crop, {})
    lo, hi = n.get("temp_c_p05", 22.0), n.get("temp_c_p95", 34.0)
    temp = live_temp_c if live_temp_c is not None else (lo + hi) / 2.0
    temp_used = min(max(float(temp), lo), hi)
    return {
        "rainfall_mm": n.get("rainfall_mm", 450.0),
        "gdd": n.get("gdd", 1850.0),
        "ndvi": n.get("ndvi", 0.68),
        "temp_c": round(temp_used, 1),
        "temp_clipped": abs(temp_used - float(temp)) > 0.05,
        "trial_dose": n.get("trial_dose", 2.0),
        "source": "Season normal for this crop (median of the simulated training data); not a live reading",
    }


def trial_dose(crop: str) -> float:
    """The single dose per crop used in the trials the model learned from."""
    return float(_normals().get(crop, {}).get("trial_dose", 2.0))


def dose_response_factor(user_dose: float, crop: str) -> float:
    """
    Share of the model's lift we credit at the farmer's dose.

    The trials used one dose per crop, so the model cannot tell what a different dose does. We assume the
    lift grows linearly up to the trial dose and does not grow beyond it (no reward for over-dosing).
    """
    td = trial_dose(crop)
    if user_dose <= 0 or td <= 0:
        return 0.0
    return min(1.0, float(user_dose) / td)


def treatment_cost_per_acre(dose_l_acre: float, price_per_l: float, application_per_acre: float) -> float:
    """Product (dose × price) plus application labour, ₹ per acre. Zero dose means no spray and no cost."""
    if dose_l_acre <= 0:
        return 0.0
    return round(float(dose_l_acre) * float(price_per_l) + float(application_per_acre), 2)


def fertiliser_cost_per_acre(delta_kg_ha: float, price_per_kg: float) -> float:
    """Extra fertiliser (kg/ha, Soil Health Card units) converted to ₹ per acre. Using less costs nothing extra."""
    return round(max(0.0, float(delta_kg_ha)) * float(price_per_kg) / ACRES_PER_HA, 2)


def net_roi(treated_yield: float, baseline_yield: float, price_per_q: float, cost_per_acre: float) -> Dict[str, Optional[float]]:
    """
    Net return and ROI of a treatment, ₹ per acre. The lift is NOT clipped at zero: if the model says the
    treatment lowers yield, the farmer sees a loss.
    """
    lift = float(treated_yield) - float(baseline_yield)
    gross = lift * float(price_per_q)
    net = gross - float(cost_per_acre)
    roi = (net / float(cost_per_acre) * 100.0) if cost_per_acre > 0 else None
    return {
        "lift_q_acre": round(lift, 3),
        "gross_gain_inr": round(gross, 2),
        "cost_inr": round(float(cost_per_acre), 2),
        "net_inr": round(net, 2),
        "roi_pct": round(roi, 1) if roi is not None else None,
        "breakeven_lift_q_acre": round(float(cost_per_acre) / float(price_per_q), 3) if price_per_q > 0 else None,
    }


def crop_error(crop: str, fallback: float = 3.99) -> float:
    """Held-out MAE for this crop (q/acre), used for the ± band instead of one pooled number."""
    pc = model_report().get("per_crop", {}).get(crop)
    return float(pc["mae_q_acre"]) if pc else float(fallback)


def lift_error(crop: str) -> Optional[float]:
    """Held-out error of the model's lift for this crop (q/acre), from paired plots."""
    te = model_report().get("treatment_effect", {}).get(crop)
    return float(te["lift_mae_q_acre"]) if te else None
