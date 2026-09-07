import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from risk_engine import (
    apply_scenario,
    generate_sample_data,
    monthly_debt_service,
    prioritize_capital,
    run_pipeline,
    score_properties,
)


def test_noi_formula_in_generated_data():
    data = generate_sample_data(property_count=4, months=18, seed=3)
    financials = data["monthly_financials"]
    calculated_noi = financials["revenue"] - financials["operating_expenses"]
    assert (calculated_noi.round(2) == financials["noi"].round(2)).all()


def test_monthly_debt_service_is_positive_and_rate_sensitive():
    low_rate = monthly_debt_service(6_000_000, 0.04)
    high_rate = monthly_debt_service(6_000_000, 0.06)
    assert low_rate > 0
    assert high_rate > low_rate


def test_stress_occupancy_drop_does_not_increase_revenue(tmp_path):
    result = run_pipeline(tmp_path)
    base = result["scored"]
    stressed = apply_scenario(base, {
        "occupancy_shock": -0.05,
        "expense_shock": 0,
        "rate_shock_bps": 0,
        "cap_rate_shock_bps": 0,
    })
    assert (stressed["revenue"] <= base["revenue"]).all()


def test_cap_rate_stress_reduces_property_value(tmp_path):
    result = run_pipeline(tmp_path)
    base = result["scored"]
    stressed = apply_scenario(base, {
        "occupancy_shock": 0,
        "expense_shock": 0,
        "rate_shock_bps": 0,
        "cap_rate_shock_bps": 100,
    })
    assert (stressed["property_value"] < base["property_value"]).all()


def test_risk_score_outputs_valid_bands(tmp_path):
    result = run_pipeline(tmp_path)
    scored = result["scored"]
    assert scored["risk_score"].between(0, 100).all()
    assert set(scored["risk_band"]).issubset({"Low", "Moderate", "Elevated", "High"})


def test_capital_selection_respects_budget(tmp_path):
    result = run_pipeline(tmp_path)
    selected = result["capital"]
    assert selected["capital_required"].sum() <= 2_000_000
    assert selected["priority_score"].is_monotonic_decreasing


def test_portfolio_exposure_sums_to_one(tmp_path):
    result = run_pipeline(tmp_path)
    market = result["concentration"]["market"]
    assert round(market["exposure_pct"].sum(), 6) == 1
