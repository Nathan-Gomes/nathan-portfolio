% Independent finance reconciliation and figures from Python CSV exports.
% Run scripts/export_research.py first, then run this file in MATLAB.
root = fileparts(fileparts(mfilename('fullpath')));
folder = fullfile(root, 'research_output');
m = readtable(fullfile(folder, 'metrics.csv'), 'TextType', 'string');
annualNOI = 12 .* m.noi;
monthlyRate = m.interest_rate ./ 12;
periods = m.amortization_years .* 12;
payment = m.loan_balance .* monthlyRate ./ (1 - (1 + monthlyRate).^(-periods));
zeroRate = monthlyRate == 0;
payment(zeroRate) = m.loan_balance(zeroRate) ./ periods(zeroRate);
assert(max(abs(payment - m.debt_service)) < 0.01, 'Debt service mismatch');
assert(max(abs(m.noi ./ payment - m.dscr)) < 1e-8, 'DSCR mismatch');
dcf = zeros(height(m),1);
for year = 1:5
    dcf = dcf + annualNOI .* 1.02.^year ./ 1.08.^year;
end
dcf = dcf + annualNOI .* 1.02.^6 ./ m.cap_rate .* .98 ./ 1.08.^5;
assert(max(abs(dcf - m.dcf_value)) < 0.01, 'DCF mismatch');
figure('Color', 'w');
tiledlayout(2,1);
nexttile;
scatter(m.ltv.*100, m.dscr, 60, m.risk_score, 'filled');
xlabel('Loan to value (%)'); ylabel('DSCR'); colorbar; grid on;
title('Property debt coverage and leverage');
nexttile;
bar(categorical(m.property_name), m.refinance_gap ./ 1e6);
ylabel('Refinance equity gap (CAD millions)'); grid on;
title('Illustrative underwriting: 65% LTV and 1.25x DSCR');
exportgraphics(gcf, fullfile(folder, 'matlab_credit_review.png'), 'Resolution', 180);
disp('MATLAB finance checks passed.');
