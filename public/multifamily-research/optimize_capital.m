% Optimization Toolbox required. Compare objective value, not tie-dependent IDs.
root = fileparts(fileparts(mfilename('fullpath')));
folder = fullfile(root, 'research_output');
p = readtable(fullfile(folder, 'optimization_inputs.csv'), 'TextType', 'string');
reference = readtable(fullfile(folder, 'optimization_reference.csv'));
n = height(p);
[~,~,group] = unique(p.property_id);
A = [p.capital_required'; full(sparse(group, (1:n)', 1))];
b = [reference.budget; ones(max(group), 1)];
[x, fval, exitflag] = intlinprog(-p.priority_score, 1:n, A, b, [], [], zeros(n,1), ones(n,1));
assert(exitflag == 1, 'Optimal solution not established');
assert(abs(-fval - reference.objective) < 1e-6, 'Python/MATLAB objective mismatch');
writetable(p(x > .5,:), fullfile(folder, 'matlab_selected_projects.csv'));
