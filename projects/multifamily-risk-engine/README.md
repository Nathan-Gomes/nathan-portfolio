# Multifamily Portfolio Risk & Capital Allocation Engine

This project simulates a multifamily real-estate portfolio and turns raw operating data into a management-style risk report.

It is designed to answer three questions:

- Which properties are contributing the most financial risk?
- What happens under occupancy, expense, interest-rate, and cap-rate stress?
- Where should limited capital be prioritized first?

## Data Model

The project uses separate tables instead of one flat spreadsheet:

- `properties`
- `monthly_financials`
- `debt`
- `valuations`
- `capital_projects`

The pipeline builds an analytical dataset with SQL joins, CTEs, and window functions.

## Financial Metrics

The engine calculates:

- NOI
- NOI margin
- Cap rate
- DSCR
- LTV
- Revenue per unit
- OpEx per unit
- NOI per unit
- YoY NOI movement
- YoY expense growth
- Occupancy deterioration
- Cash flow after debt service

## Stress Testing

The report includes:

- Base case
- Occupancy downside
- Expense pressure
- Refinancing shock
- Combined downside

Each scenario recalculates revenue, NOI, property value, debt service, DSCR, and LTV.

## Capital Prioritization

Capital projects are ranked by expected return on capital, expected NOI lift, expected value lift, current property risk, and risk reduction. The final selection respects the configured capital budget.

## Run It

```bash
python3 projects/multifamily-risk-engine/generate_report.py
python3 -m pytest projects/multifamily-risk-engine/tests -q
```

The generated report is published at:

```text
public/multifamily-risk-report.html
```
