"""Recompute the site's construction comparison from the frozen Strata inputs."""
import argparse
import csv
import json
import sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
project = parser.parse_args().project.resolve()
sys.path.insert(0, str(project))
from app import marketdata, server

weights = {ticker: 1 for ticker in marketdata.bundled_universe().ticker if ticker != "XIC.TO"}
request = {
    "source": "bundled", "start": "2018-01-02", "end": "2026-08-31",
    "benchmark": "XIC.TO", "paths": 5000, "horizon_years": 5,
    "transaction_cost_bps": 10, "rebalance": "monthly", "initial_capital": 100000,
    "portfolios": [
        {"name": name, "weights": weights, "scheme": scheme, "objective": objective,
         "max_weight": 0.35, "estimation_days": 252, "estimator": "ledoit_wolf"}
        for name, scheme, objective in [
            ("Minimum variance", "optimized", "minimum_variance"),
            ("Risk parity", "optimized", "risk_parity"),
            ("Equal weight", "equal", "minimum_variance"),
        ]
    ],
}
result = server._analyze(server.AnalysisRequest(**request))
output = Path(__file__).resolve().parents[1] / "public/investment-analytics/output"
rows = []
for portfolio in result["portfolios"]:
    summary = portfolio["summary"]
    rows.append({"rule": portfolio["name"].replace("XIC.TO benchmark", "XIC benchmark"),
                 **{key: summary[key] for key in ("annualized_return", "volatility", "sharpe", "total_cost")},
                 "annual_turnover": summary["total_turnover"] / summary["years"]})
with (output / "construction-comparison.csv").open("w") as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
(output / "construction-run.json").write_text(json.dumps(
    {"request": request, "meta": result["meta"], "manifest": result["manifest"]}, indent=2))
print(json.dumps(rows, indent=2))
