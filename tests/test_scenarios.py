"""End-to-end checks of the scenario simulator against the real model. Run: python -m pytest -q"""

import os
import sys

import joblib
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from services import decision_simulator, economics, field_context, pricing_and_soil_engine  # noqa: E402

REGION = "Maharashtra & Vidarbha (Deccan)"


@pytest.fixture(scope="module")
def model():
    m = joblib.load(os.path.join(ROOT, "models", "model.pkl"))
    m.n_jobs = 1
    return m


def _ctx(crop, dose, price=5000.0):
    pricing = pricing_and_soil_engine.calculate_algorithmic_market_pricing(crop, True)
    ctx = field_context.build_field_context(
        region=REGION, crop=crop, lat=18.5, lon=73.8, location_name="Pune",
        ow_live={"temp_c": 29.0, "status": "LIVE"},
        shc_data=pricing_and_soil_engine.get_regional_soil_health_card(REGION),
        mandi_info={"realizable_price": price, "msp": 0.0, "price_vs_msp_delta": 0.0},
        bio_dosage=dose, product_price_per_l=pricing["unit_rate_l"], application_cost_per_acre=pricing["labor_cost"])
    ctx.crop_price = price
    return ctx


@pytest.mark.parametrize("crop", ["Soybean", "Wheat", "Sugarcane", "Tomato"])
def test_overdosing_never_raises_yield(model, crop):
    td = economics.trial_dose(crop)
    at_trial = decision_simulator.simulate_5_scenarios(_ctx(crop, td), model, dosage_override=td)["scenarios"][0]
    at_4x = decision_simulator.simulate_5_scenarios(_ctx(crop, td * 4), model, dosage_override=td * 4)["scenarios"][0]
    assert at_4x["expected_yield_q_acre"] == pytest.approx(at_trial["expected_yield_q_acre"])
    assert at_4x["total_input_cost_inr"] > at_trial["total_input_cost_inr"]
    assert at_4x["net_profit_inr"] < at_trial["net_profit_inr"]


def test_soybean_stays_in_a_plausible_range(model):
    # The original bug: soybean jumped from ~11 to 113 q/acre at 3 L because of dose extrapolation
    for dose in (0.5, 2.0, 3.0, 8.0):
        y = decision_simulator.simulate_5_scenarios(_ctx("Soybean", dose), model, dosage_override=dose)["scenarios"][0]
        assert 5.0 < y["expected_yield_q_acre"] < 20.0


def test_scenario_net_matches_economics(model):
    sim = decision_simulator.simulate_5_scenarios(_ctx("Wheat", 1.5), model, dosage_override=1.5)
    base = sim["scenarios"][1]["expected_yield_q_acre"]
    for s in sim["scenarios"]:
        # lift is relative to the no-biological baseline (rounding: yields to 0.01 q, lift to 0.001 q)
        assert s["incremental_yield_q_acre"] == pytest.approx(s["expected_yield_q_acre"] - base, abs=0.01)
        expect = s["incremental_yield_q_acre"] * 5000.0 - s["total_input_cost_inr"]
        assert s["net_profit_inr"] == pytest.approx(expect, abs=5.0)


def test_baseline_scenario_has_no_cost(model):
    s = decision_simulator.simulate_5_scenarios(_ctx("Wheat", 1.5), model)["scenarios"][1]
    assert s["total_input_cost_inr"] == 0.0 and s["incremental_yield_q_acre"] == 0.0


def test_uncertainty_band_is_crop_specific(model):
    w = decision_simulator.simulate_5_scenarios(_ctx("Wheat", 1.5), model)
    s = decision_simulator.simulate_5_scenarios(_ctx("Sugarcane", 3.0), model)
    assert s["yield_error_q_acre"] > w["yield_error_q_acre"]
