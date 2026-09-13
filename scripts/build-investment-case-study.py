"""Render case-study evidence tables and source excerpts from the completed run."""
import argparse
import csv
import html
import json
import shutil
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("project", type=Path)
project = parser.parse_args().project
site = Path(__file__).resolve().parents[1]

def rows(name):
    with (project / name).open() as stream:
        return list(csv.DictReader(stream))

def row(values):
    return '<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in values) + '</tr>'

performance = []
for r in rows('output/portfolio_summary.csv'):
    performance.append(row([r['portfolio_id'].replace('Benchmark', 'XIC benchmark'),
                            f"{float(r['cumulative_return']):.2%}", f"{float(r['annualized_return']):.2%}",
                            f"{float(r['volatility']):.2%}", f"{float(r['sharpe']):.2f}",
                            f"{float(r['max_drawdown']):.2%}", f"${float(r['total_cost']):,.2f}"]))
targets = {(r['portfolio_id'], r['ticker']):float(r['weight']) for r in rows('output/target_weights.csv')}
holdings = []
for r in rows('data/securities.csv'):
    if r['ticker'] == 'XIC.TO':
        continue
    holdings.append(row([f"{r['ticker']} · {r['name']}", r['sector']] +
                        [f"{targets.get((name, r['ticker']), 0):.2%}" for name in ['Growth','Income','Balanced','Low volatility']]))
scores = rows('output/model_scores.csv')
models = []
for r in scores:
    if r['selected_by_cv'] != 'True':
        continue
    baseline = next(x for x in scores if x['portfolio_id'] == r['portfolio_id'] and x['model'] == 'Persistence baseline')
    error, reference = float(r['rmse']), float(baseline['rmse'])
    models.append(row([r['portfolio_id'],f'{error*100:.2f} pp',f'{reference*100:.2f} pp',
                       f'{(1-error/reference)*100:+.1f}%', f"{float(r['r2']):.3f}"]))
template = (site / 'scripts/templates/investment-case-study.html').read_text()
downside = {r['portfolio_id']: r for r in rows('output/scenario_downside.csv')}
paired = next(r for r in rows('output/scenario_paired.csv') if r['experiment'] == 'Published model')
takeaways = {
    'GROWTH_DRAWDOWN': f"{abs(float(downside['Growth']['median_max_drawdown'])):.1%}",
    'BALANCED_DRAWDOWN': f"{abs(float(downside['Balanced']['median_max_drawdown'])):.1%}",
    'GROWTH_BELOW_80': f"{float(downside['Growth']['probability_ever_below_80pct']):.1%}",
    'BALANCED_BELOW_80': f"{float(downside['Balanced']['probability_ever_below_80pct']):.1%}",
    'GROWTH_UNDERPERFORM': f"{float(paired['probability_underperformance']):.1%}",
    'GROWTH_PAIRED_SHORTFALL': f"${abs(float(paired['difference_p05'])):,.0f}",
}
scenario_rows = []
for r in rows('output/forward_projection_summary.csv'):
    scenario_rows.append(row([r['portfolio_id']] +
        [f"${float(r[k]):,.0f}" for k in ['start_value', 'terminal_p05', 'terminal_median', 'terminal_p95']] +
        [f"{float(r['terminal_median']) / float(r['start_value']) - 1:.1%}",
         f"{float(r['probability_terminal_loss']):.1%}", f"{float(r['median_max_drawdown']):.1%}"]))
template = template.replace('{{SCENARIO_ROWS}}', ''.join(scenario_rows))
template = template.replace('{{SCENARIO_RISK}}', (project / 'output/scenario_risk_section.html').read_text())
values = {'PERFORMANCE_ROWS':''.join(performance), 'HOLDING_ROWS':''.join(holdings), 'MODEL_ROWS':''.join(models),
          'SQL':html.escape((project / 'sql/analysis_queries.sql').read_text()),
          'MODEL_CODE':html.escape((project / 'src/models.py').read_text()),
          'TEST_CODE':html.escape((project / 'tests/test_pipeline.py').read_text()),
          'CONFIG':html.escape(json.dumps(json.loads((project / 'config.json').read_text()), indent=2))}
for name, value in values.items():
    template = template.replace('{{' + name + '}}', value)
for name, value in takeaways.items():
    template = template.replace('{{' + name + '}}', value)
assert '{{' not in template
(site / 'public/Project-Investment-Analytics.dc.html').write_text(template)
for name in ['target_weights.csv', 'validation_splits.csv', 'run_manifest.json']:
    shutil.copy2(project / 'output' / name, site / 'public/investment-analytics/output' / name)
print('Rendered case study with source-backed tables and evidence links')
