# Investment review methodology

## Business decision

Identify operating deterioration, estimate refinancing equity needs and select a capital plan within a budget. All source properties, financial records and project benefits are synthetic. They demonstrate engineering and financial reasoning, not Fergo client results.

## Financial contracts

Operating statements are monthly CAD. NOI equals revenue less operating expenses; cash after debt excludes capital expenditure and tax. Annualized NOI is latest monthly NOI multiplied by 12, not trailing twelve-month NOI. SQL separately computes a trailing average and the research SQL computes complete twelve-month totals.

Debt service uses a level-payment amortizing loan, monthly rate = nominal annual rate / 12. This is a simplified convention rather than a Canadian mortgage quotation engine. Aggregate DSCR is sum(NOI) / sum(debt service), distinct from the existing value-weighted average of individual DSCRs.

Refinance capacity is the lesser of 65% of value and annual NOI / (1.25 times the mortgage constant). Equity gap is max(existing balance minus capacity, 0). These are illustrative analyst assumptions, not CMHC rules. Every asset is assessed as if refinanced at its scenario rate; this is capacity analysis, not a dated cash-flow forecast. Existing rate-shock multipliers by loan type and maturity are heuristic assumptions, not insurer guarantees.

The five-year unlevered DCF discounts annual NOI growing at 2%, plus year-six NOI capitalized at the current scenario cap rate and reduced by 2% sale costs. Discount rate is 8%. It omits recurring capital expenditure, taxes and lease-level detail, so it is an illustrative income valuation, not a full investment appraisal or equity IRR.

## Statistical model

Pandas aligns monthly NOI changes across all assets without forward filling. The sample covariance matrix estimates how operating changes move together. Current scenario value weights form w. Portfolio variance is w' Cov w; property contributions are w_i (Cov w)_i and reconcile to total variance. This uses fixed current weights and historical synthetic observations, not investable portfolio returns or out-of-sample forecasting.

Historical 95% NOI VaR is the 95th percentile of negative monthly changes; expected shortfall averages observations at or beyond that threshold. With 47 observations, tail estimates are unstable and descriptive. HHI equals sum(weight squared); its inverse is the effective number of equally sized assets. Negative variance contributions can indicate diversification.

## Optimization

SciPy HiGHS solves a binary mixed-integer program maximizing sum(priority times selection). Selection is zero or one, total cost cannot exceed budget, and no more than one project is chosen per property. The objective retains explicit analyst preferences: annual NOI yield in percentage points + twice supplied risk-reduction points + one quarter of current property risk score. It is not a maximum-NPV objective. Project benefits are supplied synthetic assumptions, not estimated treatment effects; selected projects do not automatically alter the operating portfolio. Optimality applies to this declared objective and candidate set.

## Reproducibility and review

Run `python -m pytest -q`, then `python scripts/export_research.py`. The CSV package is suitable for Tableau import and includes optimization reference inputs. Run `matlab/validate_portfolio.m` for independent debt/DSCR/DCF checks and MATLAB figures; `matlab/optimize_capital.m` requires Optimization Toolbox and reconciles the optimal objective. MATLAB execution must be verified in a licensed environment; Python tests do not prove MATLAB execution. No Databricks deployment or Tableau workbook is claimed.

The SQL research query uses joins, CTEs, LAG, rolling windows, NULLIF and market-level ranking. Data checks reject duplicated property-months, non-finite values, invalid occupancy and unreconciled NOI. Unit tests compare optimization with exhaustive enumeration and verify stress recalculation, credit math, DCF and covariance attribution.
