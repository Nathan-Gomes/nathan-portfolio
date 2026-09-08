from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

import pandas as pd

from risk_engine import CONFIG, concentration_summary, run_pipeline


ROOT = Path(__file__).resolve().parent
SITE_PUBLIC = ROOT.parents[1] / "public"
PUBLIC_PROJECT = SITE_PUBLIC / "multifamily-risk-engine"


def money(value: float) -> str:
    value = float(value)
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value / 1_000:.0f}k"


def pct(value: float) -> str:
    return f"{float(value) * 100:.1f}%"


def safe(text: object) -> str:
    return html.escape(str(text))


def table_html(frame: pd.DataFrame, columns: list[str], labels: list[str]) -> str:
    head = "".join(f"<th>{safe(label)}</th>" for label in labels)
    rows = []
    for _, row in frame.iterrows():
        cells = "".join(f"<td>{safe(row[column])}</td>" for column in columns)
        rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def bar_rows(frame: pd.DataFrame, label_col: str, value_col: str, value_formatter=pct, limit: int = 8) -> str:
    data = frame.head(limit).copy()
    max_value = max(float(data[value_col].abs().max()), 0.01)
    rows = []
    for _, row in data.iterrows():
        value = float(row[value_col])
        width = abs(value) / max_value * 100
        color = "#a23a2c" if value < 0 else "#176b55"
        rows.append(
            f"<div class='bar-row'><span>{safe(row[label_col])}</span>"
            f"<div><i style='width:{width:.1f}%;background:{color}'></i></div><strong>{value_formatter(row[value_col])}</strong></div>"
        )
    return "".join(rows)


def risk_matrix_svg(scored: pd.DataFrame) -> str:
    points = []
    for _, row in scored.iterrows():
        x = min(max((row["ltv"] - 0.45) / 0.4, 0), 1) * 760 + 70
        y = 420 - min(max((row["dscr"] - 0.8) / 1.1, 0), 1) * 340
        radius = min(max(row["property_value"] / scored["property_value"].max() * 24, 8), 24)
        color = {"High": "#a23a2c", "Elevated": "#b9852e", "Moderate": "#26715c", "Low": "#8aa79d"}[row["risk_band"]]
        points.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='{radius:.1f}' fill='{color}' opacity='0.82'>"
            f"<title>{safe(row['property_name'])}: DSCR {row['dscr']:.2f}, LTV {pct(row['ltv'])}, Risk {row['risk_score']:.1f}</title></circle>"
        )
    return f"""
    <svg viewBox="0 0 900 500" role="img" aria-label="Risk matrix showing DSCR against loan to value">
      <rect x="0" y="0" width="900" height="500" fill="#fff"/>
      <line x1="70" y1="420" x2="840" y2="420" stroke="#dfe2e1"/>
      <line x1="70" y1="80" x2="70" y2="420" stroke="#dfe2e1"/>
      <line x1="70" y1="327" x2="840" y2="327" stroke="#a23a2c" stroke-dasharray="5 6" opacity="0.55"/>
      <line x1="358" y1="80" x2="358" y2="420" stroke="#a23a2c" stroke-dasharray="5 6" opacity="0.55"/>
      <text x="450" y="474" text-anchor="middle" fill="#6f7479" font-size="18">Loan-to-value</text>
      <text x="22" y="250" text-anchor="middle" transform="rotate(-90 22 250)" fill="#6f7479" font-size="18">DSCR</text>
      <text x="65" y="450" text-anchor="middle" fill="#6f7479" font-size="13">45%</text>
      <text x="358" y="450" text-anchor="middle" fill="#6f7479" font-size="13">60%</text>
      <text x="840" y="450" text-anchor="middle" fill="#6f7479" font-size="13">85%</text>
      <text x="46" y="425" text-anchor="end" fill="#6f7479" font-size="13">0.8x</text>
      <text x="46" y="332" text-anchor="end" fill="#6f7479" font-size="13">1.1x</text>
      <text x="46" y="84" text-anchor="end" fill="#6f7479" font-size="13">1.9x</text>
      {''.join(points)}
    </svg>
    """


def main() -> None:
    result = run_pipeline(ROOT / "output")
    scored = result["scored"].copy()
    scenarios = result["scenarios"].copy()
    concentration = result["concentration"]
    capital = result["capital"].copy()
    summary = result["summary"]

    PUBLIC_PROJECT.mkdir(parents=True, exist_ok=True)
    (PUBLIC_PROJECT / "data").mkdir(exist_ok=True)
    for csv_file in (ROOT / "output" / "data").glob("*.csv"):
        shutil.copy2(csv_file, PUBLIC_PROJECT / "data" / csv_file.name)

    top_risk = scored.head(6).copy()
    top_risk_display = top_risk.assign(
        risk=lambda df: df["risk_score"].map(lambda value: f"{value:.1f}"),
        dscr_display=lambda df: df["dscr"].map(lambda value: f"{value:.2f}x"),
        ltv_display=lambda df: df["ltv"].map(pct),
        occupancy_display=lambda df: df["occupancy"].map(pct),
        noi_yoy_display=lambda df: df["noi_yoy"].map(pct),
    )
    scenarios_display = scenarios.assign(
        portfolio_value_display=lambda df: df["portfolio_value"].map(money),
        value_change_display=lambda df: df["value_change_pct"].map(pct),
        annual_noi_display=lambda df: df["annual_noi"].map(money),
    )
    maturity_display = concentration["maturity"].assign(
        maturity_year=lambda df: df["maturity_year"].astype(int).astype(str)
    )
    capital_display = capital.head(6).assign(
        capital_display=lambda df: df["capital_required"].map(money),
        noi_lift_display=lambda df: df["expected_noi_lift"].map(money),
        value_lift_display=lambda df: df["expected_value_lift"].map(money),
        roc_display=lambda df: df["expected_return_on_capital"].map(pct),
    )

    export = {
        "summary": summary,
        "top_risk": top_risk[["property_name", "market", "risk_score", "risk_band", "dscr", "ltv", "noi_yoy"]].to_dict("records"),
        "scenarios": scenarios.to_dict("records"),
        "capital": capital.head(8).to_dict("records"),
    }
    (SITE_PUBLIC / "multifamily-risk-report.json").write_text(json.dumps(export, indent=2), encoding="utf-8")

    html_doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Multifamily Portfolio Risk &amp; Capital Allocation Engine</title>
  <meta name="description" content="A property portfolio risk report using Python, pandas, SQL, stress testing, and capital allocation analysis.">
  <link rel="icon" href="data:,">
  <style>
    :root{{--ink:#151719;--muted:#6f7479;--line:#dfe2e1;--green:#176b55;--paper:#f7f8f7;--white:#fff;--amber:#b9852e;--red:#a23a2c}}
    *{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,Arial,sans-serif;line-height:1.5}}a{{color:inherit}}
    .shell{{max-width:1180px;margin:0 auto;padding:0 32px 64px}}.topbar{{display:flex;justify-content:space-between;gap:24px;padding:24px 0;border-bottom:1px solid var(--line);font:12px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;letter-spacing:.08em}}.topbar a{{text-decoration:none;color:var(--muted)}}.hero{{padding:64px 0 44px}}.eyebrow{{color:var(--green);font:12px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase;letter-spacing:.1em}}.hero h1{{max-width:900px;margin:16px 0 18px;font-size:clamp(38px,6vw,72px);line-height:1.02;letter-spacing:0}}.hero p{{max-width:820px;margin:0;color:#42474b;font-size:18px}}.notice{{display:inline-flex;margin-top:24px;padding:9px 12px;border:1px solid #b8d3c9;background:#eaf2ef;color:var(--green);font:11px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase}}
    .metrics{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));border-top:1px solid var(--ink);border-bottom:1px solid var(--line);background:var(--white)}}.metric{{padding:22px 18px;border-right:1px solid var(--line)}}.metric:last-child{{border:0}}.metric span{{display:block;color:var(--muted);font:10px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase}}.metric strong{{display:block;margin-top:9px;font-size:25px;font-weight:600}}.metric small{{color:var(--muted)}}
    section{{padding:48px 0;border-bottom:1px solid var(--line)}}.section-head{{display:flex;justify-content:space-between;gap:30px;align-items:end;margin-bottom:24px}}.section-head h2{{margin:0;font-size:28px}}.section-head p{{max-width:560px;margin:0;color:var(--muted);text-align:right}}.grid{{display:grid;grid-template-columns:1.2fr .8fr;gap:18px}}.panel{{background:var(--white);border:1px solid var(--line);padding:24px;min-width:0}}.panel h3{{margin:0 0 18px;font-size:18px}}.risk-matrix{{min-height:460px;padding:0;overflow:hidden}}.risk-matrix svg{{display:block;width:100%;height:auto}}
    table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{padding:11px 8px;border-bottom:1px solid var(--line);text-align:right}}th:first-child,td:first-child{{text-align:left}}th{{color:var(--muted);font:10px ui-monospace,SFMono-Regular,Menlo,monospace;text-transform:uppercase}}.table-wrap{{overflow-x:auto}}.table-wrap table{{min-width:620px}}
    .bar-list{{display:grid;gap:12px}}.bar-row{{display:grid;grid-template-columns:120px 1fr 70px;gap:12px;align-items:center;font-size:13px}}.bar-row div{{height:10px;background:#edf0ef}}.bar-row i{{display:block;height:100%;background:var(--green)}}.bar-row strong{{text-align:right;font:12px ui-monospace,SFMono-Regular,Menlo,monospace}}.workflow{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line);border:1px solid var(--line)}}.workflow div{{background:var(--white);padding:20px}}.workflow span{{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--green);text-transform:uppercase}}.workflow h3{{margin:9px 0 6px;font-size:16px}}.workflow p{{margin:0;color:var(--muted);font-size:14px}}.callouts{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}.callout{{background:var(--white);border:1px solid var(--line);padding:22px}}.callout span{{font:11px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--green);text-transform:uppercase}}.callout strong{{display:block;margin-top:8px;font-size:24px}}.callout p{{margin:8px 0 0;color:var(--muted);font-size:14px}}.footer{{padding-top:28px;color:var(--muted);font-size:13px}}
    @media(max-width:980px){{.grid,.workflow,.callouts{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,minmax(0,1fr))}}.section-head{{display:block}}.section-head p{{margin-top:8px;text-align:left}}.bar-row{{grid-template-columns:1fr}}.topbar{{align-items:flex-start;flex-direction:column}}}}
  </style>
</head>
<body><div class="shell">
  <header class="topbar"><strong>Nathan Gomes / Real Estate Risk</strong><span style="display:flex;gap:18px;flex-wrap:wrap"><a href="https://nathan-fergo-risk-analyst.onrender.com" target="_blank" rel="noreferrer">Open app</a><a href="Project-Multifamily-Risk-Engine.dc.html">Read the case study</a><a href="multifamily-risk-report.json">View JSON</a><a href="multifamily-risk-engine/data/monthly_financials.csv">Sample data</a></span></header>
  <main>
    <div class="hero"><div class="eyebrow">Portfolio risk and capital allocation</div><h1>Multifamily Portfolio Risk &amp; Capital Allocation Engine</h1><p>A simulated real-estate portfolio system that turns property financials, debt, valuations, and capital project data into risk scores, stress-test results, concentration analysis, and capital-prioritization recommendations.</p><div class="notice">Historical sample data / no client data exposed</div></div>
    <div class="metrics">
      <div class="metric"><span>Portfolio value</span><strong>{money(summary["portfolio_value"])}</strong><small>latest valuation</small></div>
      <div class="metric"><span>Properties</span><strong>{summary["property_count"]}</strong><small>{summary["unit_count"]:,} units</small></div>
      <div class="metric"><span>Annual NOI</span><strong>{money(summary["annual_noi"])}</strong><small>latest run rate</small></div>
      <div class="metric"><span>Weighted DSCR</span><strong>{summary["weighted_dscr"]:.2f}x</strong><small>debt coverage</small></div>
      <div class="metric"><span>CMHC debt share</span><strong>{pct(summary["cmhc_debt_share"])}</strong><small>{money(summary["cmhc_debt"])}</small></div>
      <div class="metric"><span>High watchlist</span><strong>{summary["elevated_or_high"]}</strong><small>elevated or high</small></div>
    </div>
    <section><div class="section-head"><h2>Executive readout</h2><p>The report answers which properties are adding risk, what happens under downside scenarios, and where capital should be prioritized first.</p></div><div class="callouts"><div class="callout"><span>Concentration</span><strong>{summary["largest_market"]} {pct(summary["largest_market_exposure"])}</strong><p>Largest geographic exposure by current property value.</p></div><div class="callout"><span>CMHC exposure</span><strong>{pct(summary["cmhc_debt_share"])}</strong><p>Share of debt balance modeled as CMHC-insured financing.</p></div><div class="callout"><span>Refinancing exposure</span><strong>{money(summary["debt_maturing_24m"])}</strong><p>Debt maturing through 2028, where rate changes matter most.</p></div><div class="callout"><span>Capital plan</span><strong>{money(summary["selected_capital"])}</strong><p>Selected from a {money(summary["capital_budget"])} capital budget based on return and risk reduction.</p></div></div></section>
    <section><div class="section-head"><h2>System architecture</h2><p>The project is structured like a small internal portfolio infrastructure layer rather than a one-off spreadsheet.</p></div><div class="workflow"><div><span>Input</span><h3>Property data</h3><p>Properties, monthly financials, debt, valuations, and capital projects are stored as separate tables.</p></div><div><span>SQL</span><h3>Analytical dataset</h3><p>Joins, CTEs, aggregations, and window functions assemble current and trailing measures.</p></div><div><span>Python</span><h3>Risk engine</h3><p>pandas calculates NOI, DSCR, LTV, YoY trends, cash flow, exposure, and risk scores.</p></div><div><span>Output</span><h3>Report</h3><p>Stress scenarios, risk rankings, concentration views, and capital recommendations are published.</p></div></div></section>
    <section><div class="section-head"><h2>Property risk matrix</h2><p>Lower DSCR and higher LTV move a property toward the vulnerable zone. Bubble size represents property value.</p></div><div class="grid"><div class="panel risk-matrix">{risk_matrix_svg(scored)}</div><div class="panel"><h3>Highest risk properties</h3><div class="table-wrap">{table_html(top_risk_display, ["property_name", "market", "risk", "dscr_display", "ltv_display", "noi_yoy_display"], ["Property", "Market", "Risk", "DSCR", "LTV", "NOI YoY"])}</div></div></div></section>
    <section><div class="section-head"><h2>Scenario stress testing</h2><p>Each scenario recalculates revenue, NOI, value, debt service, DSCR, and LTV so vulnerable assets surface quickly.</p></div><div class="grid"><div class="panel"><h3>Scenario comparison</h3><div class="table-wrap">{table_html(scenarios_display, ["scenario", "portfolio_value_display", "value_change_display", "annual_noi_display", "properties_below_1_10_dscr"], ["Scenario", "Value", "Value change", "Annual NOI", "DSCR < 1.10"])}</div></div><div class="panel"><h3>Downside value impact</h3><div class="bar-list">{bar_rows(scenarios.sort_values("value_change_pct"), "scenario", "value_change_pct", pct, 5)}</div></div></div></section>
    <section><div class="section-head"><h2>Portfolio concentration</h2><p>Risk is not only property-level. The engine also checks exposure by market, maturity year, and debt structure.</p></div><div class="grid"><div class="panel"><h3>Geographic exposure</h3><div class="bar-list">{bar_rows(concentration["market"], "market", "exposure_pct", pct, 6)}</div></div><div class="panel"><h3>Debt maturity schedule</h3><div class="bar-list">{bar_rows(maturity_display, "maturity_year", "loan_balance", money, 8)}</div></div></div></section>
    <section><div class="section-head"><h2>Capital allocation recommendations</h2><p>The model ranks projects by expected NOI lift, value lift, risk reduction, and fit within a limited capital budget.</p></div><div class="panel"><div class="table-wrap">{table_html(capital_display, ["selected_order", "property_name", "project_type", "capital_display", "noi_lift_display", "value_lift_display", "roc_display"], ["Rank", "Property", "Project", "Capital", "NOI lift", "Value lift", "Return on capital"])}</div></div></section>
    <section><div class="section-head"><h2>Validation checks</h2><p>The engine includes tests around formulas and scenario behavior so the analysis is reviewable.</p></div><div class="callouts"><div class="callout"><span>Formula tests</span><strong>NOI, DSCR, LTV</strong><p>Core calculations are checked against direct expected values.</p></div><div class="callout"><span>Stress tests</span><strong>Scenario logic</strong><p>Occupancy drops cannot increase revenue, and cap-rate expansion reduces value when NOI is held constant.</p></div><div class="callout"><span>Portfolio tests</span><strong>Exposure and budget</strong><p>Market exposure sums to 100%, and selected capital projects remain within budget.</p></div></div></section>
  </main><footer class="footer">Generated from deterministic sample data. This is a portfolio demonstration, not investment advice.</footer>
</div></body></html>"""
    (SITE_PUBLIC / "multifamily-risk-report.html").write_text(html_doc, encoding="utf-8")


if __name__ == "__main__":
    main()
