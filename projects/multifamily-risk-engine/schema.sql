CREATE TABLE properties (
  property_id TEXT PRIMARY KEY,
  property_name TEXT NOT NULL,
  market TEXT NOT NULL,
  asset_class TEXT NOT NULL,
  units INTEGER NOT NULL,
  acquisition_price REAL NOT NULL,
  acquisition_date TEXT NOT NULL
);

CREATE TABLE monthly_financials (
  property_id TEXT NOT NULL,
  month TEXT NOT NULL,
  occupancy REAL NOT NULL,
  revenue REAL NOT NULL,
  operating_expenses REAL NOT NULL,
  noi REAL NOT NULL,
  FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE TABLE debt (
  property_id TEXT PRIMARY KEY,
  loan_balance REAL NOT NULL,
  interest_rate REAL NOT NULL,
  maturity_year INTEGER NOT NULL,
  amortization_years INTEGER NOT NULL,
  loan_type TEXT NOT NULL,
  rate_type TEXT NOT NULL,
  FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE TABLE valuations (
  property_id TEXT NOT NULL,
  month TEXT NOT NULL,
  property_value REAL NOT NULL,
  cap_rate REAL NOT NULL,
  FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

CREATE TABLE capital_projects (
  project_id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL,
  project_type TEXT NOT NULL,
  capital_required REAL NOT NULL,
  expected_noi_lift REAL NOT NULL,
  expected_value_lift REAL NOT NULL,
  risk_reduction_points REAL NOT NULL,
  priority_note TEXT NOT NULL,
  FOREIGN KEY (property_id) REFERENCES properties(property_id)
);

WITH latest AS (
  SELECT
    mf.*,
    p.property_name,
    p.market,
    p.units,
    d.loan_balance,
    d.interest_rate,
    d.maturity_year,
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
trailing AS (
  SELECT
    property_id,
    month,
    AVG(noi) OVER (
      PARTITION BY property_id
      ORDER BY month
      ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    ) AS trailing_12_noi,
    AVG(occupancy) OVER (
      PARTITION BY property_id
      ORDER BY month
      ROWS BETWEEN 11 PRECEDING AND CURRENT ROW
    ) AS trailing_12_occupancy
  FROM monthly_financials
)
SELECT
  l.property_id,
  l.property_name,
  l.market,
  l.month,
  l.units,
  l.occupancy,
  l.revenue,
  l.operating_expenses,
  l.noi,
  t.trailing_12_noi,
  t.trailing_12_occupancy,
  l.loan_balance,
  l.interest_rate,
  l.maturity_year,
  l.property_value,
  l.cap_rate
FROM latest l
JOIN trailing t ON t.property_id = l.property_id AND t.month = l.month
WHERE l.recency_rank = 1;
