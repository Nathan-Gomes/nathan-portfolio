from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
CONFIG = json.loads((ROOT / "config.json").read_text())
ANALYTICAL_SQL = """
WITH latest AS (
  SELECT
    mf.*,
    p.property_name,
    p.market,
    p.asset_class,
    p.units,
    d.loan_balance,
    d.interest_rate,
    d.maturity_year,
    d.rate_type,
    v.property_value,
    v.cap_rate,
    ROW_NUMBER() OVER (
      PARTITION BY mf.property_id
      ORDER BY mf.month DESC
    ) AS recency_rank
  FROM monthly_financials mf
  JOIN properties p ON p.property_id = mf.property_id
  JOIN debt d ON d.property_id = mf.property_id
  JOIN valuations v ON v.property_id = mf.property_id AND v.month = mf.month
),
history AS (
  SELECT
    property_id,
    month,
    noi,
    occupancy,
    operating_expenses,
    LAG(noi, 12) OVER (PARTITION BY property_id ORDER BY month) AS noi_12m_ago,
    LAG(occupancy, 12) OVER (PARTITION BY property_id ORDER BY month) AS occupancy_12m_ago,
    LAG(operating_expenses, 12) OVER (PARTITION BY property_id ORDER BY month) AS expenses_12m_ago,
    AVG(noi) OVER (
      PARTITION BY property_id
      ORDER BY month
      ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    ) AS trailing_12_noi
  FROM monthly_financials
)
SELECT
  l.*,
  h.noi_12m_ago,
  h.occupancy_12m_ago,
  h.expenses_12m_ago,
  h.trailing_12_noi
FROM latest l
JOIN history h ON h.property_id = l.property_id AND h.month = l.month
WHERE l.recency_rank = 1
"""


def monthly_debt_service(loan_balance: float, annual_rate: float, amortization_years: int = 25) -> float:
    monthly_rate = annual_rate / 12
    periods = amortization_years * 12
    if monthly_rate == 0:
        return loan_balance / periods
    return loan_balance * monthly_rate * (1 + monthly_rate) ** periods / ((1 + monthly_rate) ** periods - 1)


def generate_sample_data(property_count: int = 24, months: int = 48, seed: int = 17) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    month_index = pd.period_range(end=CONFIG["as_of_month"], periods=months, freq="M").astype(str)
    markets = ["Toronto", "Hamilton", "London", "Windsor", "Kitchener", "Ottawa"]
    classes = ["Garden apartments", "Mid-rise", "Mixed-use", "Student housing"]
    names = [
        "Cedar Place", "Riverside Towers", "Maple Court", "Harbour View", "Park Lane",
        "Oakridge Manor", "King West Lofts", "Lakeside House", "Barton Square",
        "Victoria Gardens", "Mason Heights", "York Mills Residences", "Queenston Court",
        "Forest Hill Apartments", "Bayview Terrace", "Dundas Commons", "Huron House",
        "Elm Street Flats", "Stonebridge Place", "Mill Road Residences", "Albion Gardens",
        "Willow Creek", "Front Street Lofts", "Meadowbrook Court"
    ]

    properties = []
    monthly_rows = []
    debt_rows = []
    valuation_rows = []
    project_rows = []

    stress_names = {"Queenston Court", "Albion Gardens", "Elm Street Flats", "Barton Square", "Huron House"}
    for i in range(property_count):
        property_id = f"P{i + 1:03d}"
        units = int(rng.integers(42, 156))
        market = markets[i % len(markets)]
        asset_class = classes[i % len(classes)]
        avg_rent = rng.uniform(1450, 2350)
        expense_ratio = rng.uniform(0.38, 0.48)
        stabilized_noi = units * avg_rent * 12 * rng.uniform(0.91, 0.98) * (1 - expense_ratio)
        acquisition_price = stabilized_noi / rng.uniform(0.047, 0.062)
        properties.append({
            "property_id": property_id,
            "property_name": names[i],
            "market": market,
            "asset_class": asset_class,
            "units": units,
            "acquisition_price": round(acquisition_price, 2),
            "acquisition_date": f"{2017 + i % 7}-0{1 + i % 9}-15",
        })

        leverage = rng.uniform(0.46, 0.62)
        if names[i] in stress_names:
            leverage += rng.uniform(0.03, 0.08)
        interest_rate = rng.uniform(0.039, 0.061)
        maturity_year = int(rng.choice([2027, 2028, 2029, 2030, 2031, 2032], p=[0.22, 0.24, 0.18, 0.14, 0.12, 0.10]))
        debt_rows.append({
            "property_id": property_id,
            "loan_balance": round(acquisition_price * leverage, 2),
            "interest_rate": round(interest_rate, 4),
            "maturity_year": maturity_year,
            "amortization_years": 25,
            "rate_type": "Variable" if rng.random() < 0.32 else "Fixed",
        })

        occupancy = rng.uniform(0.90, 0.985)
        cap_rate = rng.uniform(0.047, 0.061)
        rent_growth = rng.uniform(0.001, 0.004)
        expense_growth = rng.uniform(0.0015, 0.005)
        for month_number, month in enumerate(month_index):
            is_stress_property = names[i] in stress_names and month_number > months - 15
            seasonal = math.sin(month_number / 12 * math.tau) * rng.uniform(0.004, 0.012)
            occ = occupancy + seasonal + rng.normal(0, 0.008)
            if is_stress_property:
                occ -= 0.018 + (month_number - (months - 15)) * 0.002
                expense_ratio += 0.0014
            occ = float(np.clip(occ, 0.78, 0.995))
            rent = avg_rent * (1 + rent_growth) ** month_number
            revenue = units * occ * rent
            opex = revenue * expense_ratio * (1 + expense_growth) ** month_number
            if is_stress_property:
                opex *= 1.08 + rng.uniform(0.01, 0.06)
            revenue = round(revenue, 2)
            opex = round(opex, 2)
            noi = round(revenue - opex, 2)
            current_cap_rate = cap_rate + (0.000015 * month_number)
            property_value = (noi * 12) / current_cap_rate
            monthly_rows.append({
                "property_id": property_id,
                "month": month,
                "occupancy": round(occ, 4),
                "revenue": revenue,
                "operating_expenses": opex,
                "noi": noi,
            })
            valuation_rows.append({
                "property_id": property_id,
                "month": month,
                "property_value": round(property_value, 2),
                "cap_rate": round(current_cap_rate, 4),
            })

        for project_number in range(1, 3):
            project_type = rng.choice(["Unit renovation", "Debt paydown", "Building systems", "Energy retrofit"])
            capital_required = float(rng.integers(180000, 850000))
            expected_noi_lift = capital_required * rng.uniform(0.055, 0.13)
            risk_reduction = rng.uniform(2.5, 12.0)
            project_rows.append({
                "project_id": f"CAP-{property_id}-{project_number}",
                "property_id": property_id,
                "project_type": project_type,
                "capital_required": round(capital_required, 2),
                "expected_noi_lift": round(expected_noi_lift, 2),
                "expected_value_lift": round(expected_noi_lift / cap_rate, 2),
                "risk_reduction_points": round(risk_reduction, 2),
                "priority_note": f"{project_type} expected to improve NOI and reduce operating risk.",
            })

    return {
        "properties": pd.DataFrame(properties),
        "monthly_financials": pd.DataFrame(monthly_rows),
        "debt": pd.DataFrame(debt_rows),
        "valuations": pd.DataFrame(valuation_rows),
        "capital_projects": pd.DataFrame(project_rows),
    }


def write_sqlite(data: dict[str, pd.DataFrame], db_path: Path) -> None:
    if db_path.exists():
        db_path.unlink()
    with sqlite3.connect(db_path) as conn:
        for table_name, frame in data.items():
            frame.to_sql(table_name, conn, index=False, if_exists="replace")


def analytical_dataset(db_path: Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        frame = pd.read_sql_query(ANALYTICAL_SQL, conn)
    frame["debt_service"] = frame.apply(
        lambda row: monthly_debt_service(row["loan_balance"], row["interest_rate"]), axis=1
    )
    frame["noi_margin"] = frame["noi"] / frame["revenue"]
    frame["cap_rate_actual"] = (frame["noi"] * 12) / frame["property_value"]
    frame["dscr"] = frame["noi"] / frame["debt_service"]
    frame["ltv"] = frame["loan_balance"] / frame["property_value"]
    frame["revenue_per_unit"] = frame["revenue"] / frame["units"]
    frame["opex_per_unit"] = frame["operating_expenses"] / frame["units"]
    frame["noi_per_unit"] = frame["noi"] / frame["units"]
    frame["noi_yoy"] = (frame["noi"] - frame["noi_12m_ago"]) / frame["noi_12m_ago"]
    frame["expense_yoy"] = (frame["operating_expenses"] - frame["expenses_12m_ago"]) / frame["expenses_12m_ago"]
    frame["occupancy_change"] = frame["occupancy"] - frame["occupancy_12m_ago"]
    frame["cash_flow"] = frame["noi"] - frame["debt_service"]
    return frame


def normalize_risk(series: pd.Series, low: float, high: float, inverse: bool = False) -> pd.Series:
    score = ((series - low) / (high - low)).clip(0, 1) * 100
    return 100 - score if inverse else score


def score_properties(frame: pd.DataFrame, weights: dict[str, float] | None = None) -> pd.DataFrame:
    weights = weights or CONFIG["risk_score_weights"]
    scored = frame.copy()
    scored["dscr_risk"] = normalize_risk(scored["dscr"], 1.05, 1.75, inverse=True)
    scored["ltv_risk"] = normalize_risk(scored["ltv"], 0.50, 0.78)
    scored["occupancy_deterioration_risk"] = normalize_risk(-scored["occupancy_change"], 0.00, 0.08)
    scored["noi_deterioration_risk"] = normalize_risk(-scored["noi_yoy"], 0.00, 0.18)
    scored["expense_growth_risk"] = normalize_risk(scored["expense_yoy"], 0.02, 0.20)
    scored["refinancing_exposure_risk"] = normalize_risk(2032 - scored["maturity_year"], 0, 5)
    scored["concentration_risk"] = normalize_risk(scored["property_value"] / scored["property_value"].sum(), 0.02, 0.08)
    scored["risk_score"] = (
        scored["dscr_risk"] * weights["dscr"]
        + scored["ltv_risk"] * weights["ltv"]
        + scored["occupancy_deterioration_risk"] * weights["occupancy_deterioration"]
        + scored["noi_deterioration_risk"] * weights["noi_deterioration"]
        + scored["expense_growth_risk"] * weights["expense_growth"]
        + scored["refinancing_exposure_risk"] * weights["refinancing_exposure"]
        + scored["concentration_risk"] * weights["concentration"]
    ).round(1)
    scored["risk_band"] = pd.cut(
        scored["risk_score"],
        bins=[-0.1, 30, 60, 80, 100],
        labels=["Low", "Moderate", "Elevated", "High"],
    ).astype(str)
    return scored.sort_values("risk_score", ascending=False)


def apply_scenario(frame: pd.DataFrame, scenario: dict[str, float]) -> pd.DataFrame:
    stressed = frame.copy()
    original_revenue_per_occupied_unit = stressed["revenue"] / (stressed["units"] * stressed["occupancy"])
    stressed["occupancy"] = (stressed["occupancy"] + scenario["occupancy_shock"]).clip(0.50, 0.995)
    stressed["revenue"] = stressed["units"] * stressed["occupancy"] * original_revenue_per_occupied_unit
    stressed["operating_expenses"] = stressed["operating_expenses"] * (1 + scenario["expense_shock"])
    stressed["noi"] = stressed["revenue"] - stressed["operating_expenses"]
    stressed["interest_rate"] = stressed["interest_rate"] + scenario["rate_shock_bps"] / 10000
    stressed["cap_rate"] = stressed["cap_rate"] + scenario["cap_rate_shock_bps"] / 10000
    stressed["property_value"] = (stressed["noi"] * 12) / stressed["cap_rate"]
    stressed["debt_service"] = stressed.apply(
        lambda row: monthly_debt_service(row["loan_balance"], row["interest_rate"]), axis=1
    )
    stressed["dscr"] = stressed["noi"] / stressed["debt_service"]
    stressed["ltv"] = stressed["loan_balance"] / stressed["property_value"]
    return stressed


def scenario_summary(frame: pd.DataFrame, scenarios: dict[str, dict[str, float]] | None = None) -> pd.DataFrame:
    scenarios = scenarios or CONFIG["scenarios"]
    rows = []
    base_value = frame["property_value"].sum()
    base_noi = frame["noi"].sum() * 12
    for name, scenario in scenarios.items():
        stressed = apply_scenario(frame, scenario)
        rows.append({
            "scenario": name.replace("_", " ").title(),
            "portfolio_value": stressed["property_value"].sum(),
            "annual_noi": stressed["noi"].sum() * 12,
            "value_change_pct": stressed["property_value"].sum() / base_value - 1,
            "noi_change_pct": stressed["noi"].sum() * 12 / base_noi - 1,
            "properties_below_1_10_dscr": int((stressed["dscr"] < 1.10).sum()),
        })
    return pd.DataFrame(rows)


def concentration_summary(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    by_market = frame.groupby("market", as_index=False)["property_value"].sum()
    by_market["exposure_pct"] = by_market["property_value"] / by_market["property_value"].sum()
    by_maturity = frame.groupby("maturity_year", as_index=False)["loan_balance"].sum()
    by_rate_type = frame.groupby("rate_type", as_index=False)["loan_balance"].sum()
    by_rate_type["exposure_pct"] = by_rate_type["loan_balance"] / by_rate_type["loan_balance"].sum()
    return {
        "market": by_market.sort_values("property_value", ascending=False),
        "maturity": by_maturity.sort_values("maturity_year"),
        "rate_type": by_rate_type.sort_values("loan_balance", ascending=False),
    }


def prioritize_capital(scored: pd.DataFrame, projects: pd.DataFrame, budget: float) -> pd.DataFrame:
    joined = projects.merge(
        scored[["property_id", "property_name", "risk_score", "dscr", "ltv"]],
        on="property_id",
        how="left",
    )
    joined["expected_return_on_capital"] = joined["expected_noi_lift"] / joined["capital_required"]
    joined["priority_score"] = (
        joined["expected_return_on_capital"] * 100
        + joined["risk_reduction_points"] * 2
        + joined["risk_score"] * 0.25
    )
    selected = []
    remaining_budget = budget
    for _, row in joined.sort_values("priority_score", ascending=False).iterrows():
        if row["capital_required"] <= remaining_budget:
            selected.append(row)
            remaining_budget -= row["capital_required"]
    result = pd.DataFrame(selected)
    if result.empty:
        return result
    result["selected_order"] = range(1, len(result) + 1)
    return result


def run_pipeline(output_dir: Path | None = None) -> dict[str, object]:
    output_dir = output_dir or ROOT / "output"
    data_dir = output_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    data = generate_sample_data(CONFIG["property_count"], CONFIG["months"])
    for name, frame in data.items():
        frame.to_csv(data_dir / f"{name}.csv", index=False)
    db_path = output_dir / "multifamily_portfolio.db"
    write_sqlite(data, db_path)
    analytical = analytical_dataset(db_path)
    scored = score_properties(analytical)
    scenarios = scenario_summary(scored)
    concentration = concentration_summary(scored)
    capital = prioritize_capital(scored, data["capital_projects"], CONFIG["capital_budget"])
    summary = {
        "portfolio_value": float(scored["property_value"].sum()),
        "property_count": int(scored["property_id"].nunique()),
        "unit_count": int(scored["units"].sum()),
        "annual_noi": float(scored["noi"].sum() * 12),
        "weighted_ltv": float((scored["ltv"] * scored["property_value"]).sum() / scored["property_value"].sum()),
        "weighted_dscr": float((scored["dscr"] * scored["property_value"]).sum() / scored["property_value"].sum()),
        "elevated_or_high": int(scored["risk_band"].isin(["Elevated", "High"]).sum()),
        "debt_maturing_24m": float(scored.loc[scored["maturity_year"].le(2028), "loan_balance"].sum()),
        "largest_market": concentration["market"].iloc[0]["market"],
        "largest_market_exposure": float(concentration["market"].iloc[0]["exposure_pct"]),
        "capital_budget": CONFIG["capital_budget"],
        "selected_capital": float(capital["capital_required"].sum()) if not capital.empty else 0.0,
    }
    return {
        "summary": summary,
        "scored": scored,
        "scenarios": scenarios,
        "concentration": concentration,
        "capital": capital,
        "data": data,
        "db_path": str(db_path),
    }


if __name__ == "__main__":
    result = run_pipeline(ROOT / "output")
    print(json.dumps(result["summary"], indent=2))
