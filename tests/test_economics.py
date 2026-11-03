"""Unit tests for the money maths. Run: python -m pytest -q"""

import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services import economics as ec  # noqa: E402


def test_net_roi_matches_the_formula():
    # (12 - 10) q/acre × ₹5,000/q - ₹2,000 = ₹8,000 net, 400% ROI, break-even at 0.4 q/acre
    r = ec.net_roi(12.0, 10.0, 5000.0, 2000.0)
    assert r["lift_q_acre"] == 2.0
    assert r["gross_gain_inr"] == 10000.0
    assert r["net_inr"] == 8000.0
    assert r["roi_pct"] == 400.0
    assert r["breakeven_lift_q_acre"] == 0.4


def test_negative_lift_is_a_loss_not_zero():
    r = ec.net_roi(9.5, 10.0, 5000.0, 1000.0)
    assert r["lift_q_acre"] == -0.5
    assert r["net_inr"] == -3500.0
    assert r["roi_pct"] == -350.0


def test_roi_undefined_without_cost():
    assert ec.net_roi(10.0, 10.0, 5000.0, 0.0)["roi_pct"] is None


def test_treatment_cost_scales_with_dose():
    assert ec.treatment_cost_per_acre(2.0, 850.0, 150.0) == 1850.0
    assert ec.treatment_cost_per_acre(4.0, 850.0, 150.0) == 3550.0
    assert ec.treatment_cost_per_acre(0.0, 850.0, 150.0) == 0.0


def test_fertiliser_kg_per_ha_is_priced_per_acre():
    # 24.711 kg/ha extra at ₹10/kg is ₹100 per acre
    assert ec.fertiliser_cost_per_acre(24.711, 10.0) == pytest.approx(100.0, abs=0.01)
    assert ec.fertiliser_cost_per_acre(-50.0, 10.0) == 0.0


def test_dose_factor_linear_then_flat():
    td = ec.trial_dose("Soybean")
    assert ec.dose_response_factor(0.0, "Soybean") == 0.0
    assert ec.dose_response_factor(td / 2, "Soybean") == pytest.approx(0.5)
    assert ec.dose_response_factor(td, "Soybean") == 1.0
    assert ec.dose_response_factor(td * 4, "Soybean") == 1.0   # no reward for over-dosing


def test_season_inputs_stay_in_trained_range():
    s = ec.season_inputs("Wheat", 48.0)       # a heat-wave reading far outside the training data
    assert s["temp_clipped"] is True
    assert s["temp_c"] < 48.0
    assert 0.3 < s["ndvi"] < 0.95
    assert "not a live reading" in s["source"]


def test_per_crop_error_is_used():
    assert ec.crop_error("Sugarcane") > ec.crop_error("Wheat")   # error follows the crop's yield scale
