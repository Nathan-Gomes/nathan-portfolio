"""Render the Strata case study from the completed research run.

Every number, table and chart on the page is read from the Strata repository's output
files, so the write-up cannot drift from the published results.

    python scripts/build-investment-case-study.py ../quant-investment-analytics-etl
"""
import argparse
import csv
import math
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
project = parser.parse_args().project.resolve()
site = Path(__file__).resolve().parents[1]
STYLE_SOURCE = site / "public" / "Project-Quant-Portfolio.dc.html"  # shared case-study stylesheet

ORDER = ["Growth", "Balanced", "Income", "Low volatility", "Benchmark"]
LABELS = {"Benchmark": "XIC benchmark"}
COLORS = {
    "Growth": "#eb6834",
    "Balanced": "#1a6f57",
    "Income": "#2a78d6",
    "Low volatility": "#4a3aa7",
    "Benchmark": "#8b96a1",
}


def rows(path):
    with Path(path).open() as stream:
        return list(csv.DictReader(stream))


def by(items, key):
    return {item[key]: item for item in items}


def pct(value, digits=1):
    text = f"{float(value) * 100:.{digits}f}%"
    return "&minus;" + text[1:] if text.startswith("-") else text


def money(value):
    return f"${float(value):,.0f}"


def month(day):
    return date.fromisoformat(day[:10]).strftime("%b %Y")


def label(name):
    return LABELS.get(name, name)


# ---------- charts: static SVG in the case-study idiom ----------

def _ticks(lo, hi, count=5):
    raw = (hi - lo) / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = min(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    first = math.ceil(lo / step) * step
    return [round(first + k * step, 10) for k in range(int((hi - first) / step) + 1)]


def line_chart(series, dates, *, y_format, aria, log=False, baseline=None, height=330):
    width, left, right, top = 760, 62, 690, 16
    bottom = height - 34
    tf = math.log if log else (lambda v: v)
    values = [tf(v) for s in series for v in s["values"]]
    lo, hi = min(values), max(values)
    if baseline is not None:
        lo, hi = min(lo, tf(baseline)), max(hi, tf(baseline))
    pad = (hi - lo) * 0.05
    lo, hi = lo - pad, hi + pad
    sx = lambda i: left + i / (len(dates) - 1) * (right - left)
    sy = lambda v: bottom - (tf(v) - lo) / (hi - lo) * (bottom - top)
    if log:
        ticks = [t for t in (1, 1.5, 2, 3, 4, 6, 8) if lo <= math.log(t) <= hi]
    else:
        ticks = _ticks(lo, hi)
    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{aria}" '
           "style=\"width:100%;height:auto;font-family:'IBM Plex Mono',monospace\">"]
    for t in ticks:
        y = sy(t)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#e6e2db"/>')
        out.append(f'<text x="{left - 8}" y="{y + 3.5:.1f}" text-anchor="end" font-size="10" fill="#686c71">{y_format(t)}</text>')
    seen = {}
    for i, day in enumerate(dates):
        seen.setdefault(day[:4], i)
    for year, i in seen.items():
        if i > 0 or len(seen) < 10:
            out.append(f'<text x="{sx(i):.1f}" y="{bottom + 18}" text-anchor="middle" font-size="10" fill="#686c71">{year}</text>')
    if baseline is not None:
        y = sy(baseline)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#16181a"/>')
    for s in series:
        path = " ".join(f"{'M' if i == 0 else 'L'}{sx(i):.1f},{sy(v):.1f}" for i, v in enumerate(s["values"]))
        dash = ' stroke-dasharray="5 4"' if s.get("dash") else ""
        out.append(f'<path d="{path}" fill="none" stroke="{s["color"]}" stroke-width="{s.get("width", 1.8)}" stroke-linejoin="round"{dash}/>')
        if s.get("end"):
            out.append(f'<text x="{right + 6}" y="{sy(s["values"][-1]) + 3.5:.1f}" font-size="10" fill="#3d4145">{s["end"]}</text>')
    out.append("</svg>")
    return "\n".join(out)


def legend(series):
    items = []
    for s in series:
        style = (f"background:repeating-linear-gradient(90deg,{s['color']} 0 5px,transparent 5px 9px)"
                 if s.get("dash") else f"background:{s['color']}")
        items.append(f'<span><span class="swatch" style="{style}"></span>{s["label"]}</span>')
    return f'<div class="legend">{"".join(items)}</div>'


def fan_chart(bands, color, y_max, aria):
    """Median with 25-75 and 5-95 bands on a shared dollar scale, starting at $100k."""
    width, height, left, right, top, bottom = 380, 250, 54, 364, 12, 222
    n = len(bands)
    sx = lambda i: left + i / (n - 1) * (right - left)
    sy = lambda v: bottom - (v - 0) / y_max * (bottom - top)

    def area(lo_key, hi_key):
        upper = [f"{sx(i):.1f},{sy(float(b[hi_key])):.1f}" for i, b in enumerate(bands)]
        lower = [f"{sx(i):.1f},{sy(float(b[lo_key])):.1f}" for i, b in reversed(list(enumerate(bands)))]
        return "M" + " L".join(upper + lower) + " Z"

    out = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{aria}" '
           "style=\"width:100%;height:auto;font-family:'IBM Plex Mono',monospace\">"]
    for t in range(0, int(y_max) + 1, 200_000):
        y = sy(t)
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#e6e2db"/>')
        out.append(f'<text x="{left - 6}" y="{y + 3.5:.1f}" text-anchor="end" font-size="10" fill="#686c71">${t // 1000:,}k</text>')
    y = sy(100_000)
    out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#16181a" stroke-dasharray="3 3"/>')
    out.append(f'<path d="{area("p05", "p95")}" fill="{color}" fill-opacity="0.14"/>')
    out.append(f'<path d="{area("p25", "p75")}" fill="{color}" fill-opacity="0.28"/>')
    median = " ".join(f"{'M' if i == 0 else 'L'}{sx(i):.1f},{sy(float(b['median'])):.1f}" for i, b in enumerate(bands))
    out.append(f'<path d="{median}" fill="none" stroke="{color}" stroke-width="2"/>')
    for k in range(6):
        out.append(f'<text x="{sx(round(k / 5 * (n - 1))):.1f}" y="{bottom + 18}" text-anchor="middle" font-size="10" fill="#686c71">{"Start" if k == 0 else f"Yr {k}"}</text>')
    end = bands[-1]
    for key in ("p95", "median", "p05"):
        out.append(f'<text x="{right - 2}" y="{sy(float(end[key])) - 5:.1f}" text-anchor="end" font-size="10" fill="#3d4145">${float(end[key]) / 1000:,.0f}k</text>')
    out.append("</svg>")
    return "\n".join(out)


def table_row(cells, css=""):
    head, *rest = cells
    tag = f' class="{css}"' if css else ""
    return f"<tr{tag}><td>{head}</td>" + "".join(f"<td>{cell}</td>" for cell in rest) + "</tr>"


def test_count():
    """Collected pytest cases in the Strata repository, so the page never quotes a stale number."""
    python = project / ".venv" / "bin" / "python"
    result = subprocess.run([str(python if python.exists() else "python3"), "-m", "pytest", "--collect-only", "-q"],
                            cwd=project, capture_output=True, text=True, check=False)
    match = re.search(r"(\d+) tests? collected", result.stdout)
    if not match:
        raise SystemExit("Could not count the Strata tests:\n" + result.stdout[-2000:] + result.stderr[-2000:])
    return int(match.group(1))


# ---------- data ----------

out_dir = project / "output"
summary = by(rows(out_dir / "portfolio_summary.csv"), "portfolio_id")
daily = rows(out_dir / "portfolio_daily_summary.csv")
construction = by(rows(site / "public/investment-analytics/output/construction-comparison.csv"), "rule")
downside = by(rows(out_dir / "scenario_downside.csv"), "portfolio_id")
forward = by(rows(out_dir / "forward_projection_summary.csv"), "portfolio_id")
paired = by(rows(out_dir / "scenario_paired.csv"), "experiment")
sensitivity = {(r["experiment"], r["portfolio_id"]): r for r in rows(out_dir / "scenario_sensitivity.csv")}
bands = rows(out_dir / "forward_projection_bands.csv")

series = {}
for r in daily:
    series.setdefault(r["portfolio_id"], []).append(r)
dates = [r["date"] for r in series["Balanced"]]
step = 5  # weekly points keep the SVG small without changing its shape

sampled = list(range(0, len(dates), step))
if sampled[-1] != len(dates) - 1:
    sampled.append(len(dates) - 1)
chart_dates = [dates[i] for i in sampled]

growth_series, drawdown_series = [], []
for name in ORDER:
    navs = [float(series[name][i]["nav"]) / 100_000 for i in sampled]
    growth_series.append({"label": label(name), "color": COLORS[name], "values": navs,
                          "dash": name == "Benchmark", "end": f"${navs[-1] * 100:,.0f}k",
                          "width": 2.4 if name in ("Growth", "Balanced") else 1.6})
for name in ("Growth", "Balanced", "Benchmark"):
    drawdown_series.append({"label": label(name), "color": COLORS[name], "dash": name == "Benchmark",
                            "values": [float(series[name][i]["drawdown"]) for i in sampled]})

history_rows = "\n".join(
    table_row([
        f'<span class="swatch" style="background:{COLORS[name]}"></span>{label(name)}',
        pct(summary[name]["cumulative_return"], 0), pct(summary[name]["annualized_return"]),
        pct(summary[name]["volatility"]), f"{float(summary[name]['sharpe']):.2f}",
        pct(summary[name]["max_drawdown"]), money(summary[name]["total_cost"]),
    ], css="win" if name == "Balanced" else "bench" if name == "Benchmark" else "")
    for name in ORDER
)
construction_rows = "\n".join(
    table_row([rule, pct(r["annualized_return"]), pct(r["volatility"]), f"{float(r['sharpe']):.2f}",
               f"{float(r['annual_turnover']):.2f}", money(r["total_cost"])], css="win" if rule == "Equal weight" else "bench" if rule == "XIC benchmark" else "")
    for rule, r in construction.items()
)
scenario_rows = "\n".join(
    table_row([
        f'<span class="swatch" style="background:{COLORS[name]}"></span>{label(name)}',
        money(forward[name]["terminal_p05"]), money(forward[name]["terminal_median"]), money(forward[name]["terminal_p95"]),
        pct(downside[name]["probability_terminal_loss"]), pct(downside[name]["probability_ever_below_80pct"]),
        pct(downside[name]["median_max_drawdown"]),
    ], css="bench" if name == "Benchmark" else "")
    for name in ORDER
)

band_rows = {}
for r in bands:
    band_rows.setdefault(r["portfolio_id"], []).append(r)
fan_step = max(1, len(band_rows["Growth"]) // 150)
fan_max = math.ceil(max(float(r["p95"]) for name in ("Growth", "Balanced") for r in band_rows[name]) / 200_000) * 200_000

g, b, x = summary["Growth"], summary["Balanced"], summary["Benchmark"]
mv, ew, rp = construction["Minimum variance"], construction["Equal weight"], construction["Risk parity"]
published, blocks126 = "Published model", "126-session moving blocks"

values = {
    "first": month(dates[0]),
    "last": month(dates[-1]),
    "sessions": f"{len(dates):,}",
    "bal_sharpe": f"{float(b['sharpe']):.2f}",
    "xic_sharpe": f"{float(x['sharpe']):.2f}",
    "bal_ann": pct(b["annualized_return"]),
    "bal_dd": pct(b["max_drawdown"]),
    "xic_ann": pct(x["annualized_return"]),
    "xic_dd": pct(x["max_drawdown"]),
    "xic_vol": pct(x["volatility"]),
    "growth_ann": pct(g["annualized_return"]),
    "growth_vol": pct(g["volatility"]),
    "growth_dd": pct(g["max_drawdown"]),
    "growth_gap": f"{(float(g['annualized_return']) - float(x['annualized_return'])) * 100:.1f}",
    "growth_dd_gap": f"{(float(x['max_drawdown']) - float(g['max_drawdown'])) * 100:.1f}",
    "lv_vol": pct(summary["Low volatility"]["volatility"]),
    "mv_sharpe": f"{float(mv['sharpe']):.2f}",
    "ew_sharpe": f"{float(ew['sharpe']):.2f}",
    "rp_sharpe": f"{float(rp['sharpe']):.2f}",
    "mv_vol": pct(mv["volatility"]),
    "ew_vol": pct(ew["volatility"]),
    "rp_vol": pct(rp["volatility"]),
    "mv_cost": money(mv["total_cost"]),
    "ew_cost": money(ew["total_cost"]),
    "mv_turnover_multiple": f"{float(mv['annual_turnover']) / float(ew['annual_turnover']):.1f}",
    "growth_below80": pct(downside["Growth"]["probability_ever_below_80pct"]),
    "bal_below80": pct(downside["Balanced"]["probability_ever_below_80pct"]),
    "growth_under": pct(paired[published]["probability_underperformance"]),
    "paired_p05": money(abs(float(paired[published]["difference_p05"]))),
    "growth_p05_126": money(sensitivity[(blocks126, "Growth")]["terminal_p05"]),
    "growth_loss_20": pct(sensitivity[(published, "Growth")]["probability_terminal_loss"]),
    "growth_loss_126": pct(sensitivity[(blocks126, "Growth")]["probability_terminal_loss"]),
    "tests": str(test_count()),
    "growth_svg": line_chart(growth_series, chart_dates, log=True, baseline=1,
                             y_format=lambda v: f"${v * 100:,.0f}k",
                             aria="Value of CAD 100,000 in each portfolio and XIC, log scale"),
    "growth_legend": legend(growth_series),
    "drawdown_svg": line_chart(drawdown_series, chart_dates, baseline=0, height=250,
                               y_format=lambda v: f"{v * 100:.0f}%",
                               aria="Drawdown from the running peak for Growth, Balanced and XIC"),
    "drawdown_legend": legend(drawdown_series),
    "history_rows": history_rows,
    "construction_rows": construction_rows,
    "scenario_rows": scenario_rows,
    "fan_growth": fan_chart(band_rows["Growth"][::fan_step] + band_rows["Growth"][-1:], COLORS["Growth"], fan_max,
                            "Growth five-year scenario percentiles from CAD 100,000"),
    "fan_balanced": fan_chart(band_rows["Balanced"][::fan_step] + band_rows["Balanced"][-1:], COLORS["Balanced"], fan_max,
                              "Balanced five-year scenario percentiles from CAD 100,000"),
}
style = re.search(r"<style>.*?</style>", STYLE_SOURCE.read_text(), re.DOTALL).group(0)
page = (site / "scripts/templates/strata-case-study.html").read_text().format(style=style, **values)
(site / "public/Project-Investment-Analytics.dc.html").write_text(page)

published_dir = site / "public/investment-analytics/output"
for name in ["target_weights.csv", "validation_splits.csv", "run_manifest.json", "portfolio_summary.csv",
             "scenario_downside.csv", "scenario_paired.csv", "scenario_sensitivity.csv",
             "forward_projection_summary.csv", "forward_projection_bands.csv"]:
    shutil.copy2(out_dir / name, published_dir / name)
print(f"Rendered the Strata case study ({len(page) // 1024} kB) from {out_dir}")
