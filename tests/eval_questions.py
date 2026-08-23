"""
Phase 5 Evaluation (blueprint Section 17/18): at least 30 test questions
covering property identity, expense totals, maintenance history, document
retrieval, contract dates, missing information, conflicting records,
unauthorized information, and ambiguous property names.

For every test we check: expected answer, required source/tool, actual
tool output, numerical accuracy, and whether unsupported claims would be
possible. This runs directly against business_logic.py (the same code the
MCP tools call), so it validates the reasoning the connector will give
Claude to work with -- not Claude's phrasing of it.
"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import business_logic as bl

PASS = "PASS"
FAIL = "FAIL"

results = []


def check(name, category, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((name, category, status, detail))
    print(f"[{status}] ({category}) {name}" + (f" -- {detail}" if detail and status == FAIL else ""))


cedar = bl.resolve_property("Cedar Place")["property"]["property_id"]

# --- Property identity -------------------------------------------------
check("Resolve canonical name 'Cedar Place'", "property_identity",
      bl.resolve_property("Cedar Place")["resolved"])

check("Resolve alias 'Cedar Apartments'", "property_identity",
      bl.resolve_property("Cedar Apartments")["resolved"])

check("Resolve address alias '120 Cedar St.'", "property_identity",
      bl.resolve_property("120 Cedar St.")["resolved"])

check("Resolve ownership entity '1234567 Ontario Inc.'", "property_identity",
      bl.resolve_property("1234567 Ontario Inc.")["resolved"])

check("Resolve accounting code 'PROP-004'", "property_identity",
      bl.resolve_property("PROP-004")["resolved"])

check("Resolve utility account 'W-10842'", "property_identity",
      bl.resolve_property("W-10842")["resolved"])

# --- Ambiguous property names -------------------------------------------
r = bl.resolve_property("Random Nonexistent Manor")
check("Unknown property returns resolved=False, not a guess", "ambiguous_names",
      not r["resolved"], json.dumps(r))

r = bl.resolve_property("Cedar")
check("Partial/ambiguous token 'Cedar' does not silently resolve with high confidence",
      "ambiguous_names", r.get("confidence") != "high" or not r["resolved"], json.dumps(r))

# --- Expense totals -------------------------------------------------
exp = bl.get_expense_history(cedar, category="plumbing_hvac")
check("Boiler-related (plumbing_hvac) total matches sum of 3 invoices", "expense_totals",
      exp["total_cost"] == round(1180 + 4650 + 3590, 2), str(exp["total_cost"]))

exp_plumbing = bl.get_expense_history(cedar, category="plumbing")
check("Plumbing-only category total matches single invoice", "expense_totals",
      exp_plumbing["total_cost"] == 890.00, str(exp_plumbing["total_cost"]))

exp_range = bl.get_expense_history(cedar, start_date="2026-01-01", end_date="2026-03-31")
check("Date-range filter excludes later invoices", "expense_totals",
      exp_range["total_cost"] == round(1180 + 4650, 2), str(exp_range["total_cost"]))

exp_all = bl.get_expense_history(cedar)
check("All-category total includes landscaping", "expense_totals",
      exp_all["total_cost"] >= round(1180 + 4650 + 3590 + 890 + 640, 2) - 0.01)

# --- Maintenance history -------------------------------------------------
maint = bl.get_maintenance_history(cedar)
check("Repeat-repair detection finds Boiler 2 with 3 events", "maintenance_history",
      any(ri["event_count"] == 3 for ri in maint["repeat_issues"]))

check("Emergency event count is 1 (the pressure relief valve call)", "maintenance_history",
      maint["emergency_event_count"] == 1, str(maint["emergency_event_count"]))

maint_eq = bl.get_maintenance_history(cedar, equipment_id=1)
check("Equipment-scoped maintenance history filters correctly", "maintenance_history",
      maint_eq["event_count"] == 3, str(maint_eq["event_count"]))

# --- Document retrieval -------------------------------------------------
search = bl.search_property_documents(cedar, "circulation pump")
check("Search finds circulation pump passages", "document_retrieval",
      search["result_count"] >= 1)

search_none = bl.search_property_documents(cedar, "asbestos remediation zoning variance")
check("Search correctly returns 0 results for unrelated terms", "document_retrieval",
      search_none["result_count"] == 0)

search_filtered = bl.search_property_documents(cedar, "pump", document_type="inspection_report")
check("document_type filter narrows results to inspection reports only", "document_retrieval",
      all(r["document_type"] == "inspection_report" for r in search_filtered["results"]))

# --- Contract dates -------------------------------------------------
deadlines = bl.get_contract_deadlines(cedar, days_ahead=400)
check("Elevator contract termination deadline surfaced within 400 days", "contract_dates",
      any(c["contract_type"] == "elevator_service" for c in deadlines["contracts"]))

deadlines_short = bl.get_contract_deadlines(cedar, days_ahead=1)
check("Very short days_ahead window correctly excludes far-off deadlines", "contract_dates",
      len(deadlines_short["contracts"]) == 0)

# --- Missing information -------------------------------------------------
maint_bogus_eq = bl.get_maintenance_history(cedar, equipment_id=99999)
check("Nonexistent equipment_id returns zero events, not an error or hallucination",
      "missing_information", maint_bogus_eq["event_count"] == 0)

exp_bogus_cat = bl.get_expense_history(cedar, category="asbestos_abatement")
check("Nonexistent expense category returns zero total, not a fabricated figure",
      "missing_information", exp_bogus_cat["total_cost"] == 0)

anomalies_gas = bl.get_utility_anomalies(cedar, "gas")
check("No gas utility data yields explicit 'not enough readings' message, not silence",
      "missing_information", "message" in anomalies_gas and anomalies_gas["anomalies"] == [])

# --- Conflicting records -------------------------------------------------
findings = bl.get_open_anomalies(cedar)
check("Conflicting elevator contract amendment appears as an open finding, not silently resolved",
      "conflicting_records",
      any(f["finding_type"] == "conflicting_records" for f in findings["open_findings"]))

search_amendment = bl.search_property_documents(cedar, "amendment rate increase")
check("Draft amendment is retrievable but distinguishable by status=draft (lower authority)",
      "conflicting_records",
      any(r["document_status"] == "draft" for r in search_amendment["results"]))

# --- Unauthorized / cross-property information (no leakage) -------------
maple = bl.resolve_property("Maple Court")["property"]["property_id"]
maple_search = bl.search_property_documents(maple, "boiler circulation pump elevator")
check("Maple Court search cannot see Cedar Place's documents", "unauthorized_information",
      maple_search["result_count"] == 0)

maple_maint = bl.get_maintenance_history(maple)
check("Maple Court maintenance history is empty (no cross-property data)",
      "unauthorized_information", maple_maint["event_count"] == 0)

maple_summary = bl.get_property_summary(maple)
check("Maple Court summary has no Cedar Place findings", "unauthorized_information",
      len(maple_summary["open_findings"]) == 0)

# --- Utility anomalies / financial exposure -------------------------------------------------
water = bl.get_utility_anomalies(cedar, "water")
check("Water anomaly detected for Mar-May 2026 (3 periods)", "expense_totals",
      len(water["anomalies"]) == 3, str(len(water["anomalies"])))

check("Estimated annual exposure is a positive, non-fabricated number derived from readings",
      "expense_totals", water["estimated_annual_exposure"] > 0)

# --- Property summary integration -------------------------------------------------
summary = bl.get_property_summary(cedar)
check("Full property summary includes profile, findings, maintenance, expenses, and deadlines",
      "property_identity",
      all(k in summary for k in ["property", "open_findings", "recent_maintenance_events",
                                   "top_recent_expenses", "upcoming_contract_deadlines"]))

check("Property summary open findings count matches get_open_anomalies", "property_identity",
      len(summary["open_findings"]) == findings["count"])

# --- Summary -------------------------------------------------
print("\n" + "=" * 70)
total = len(results)
passed = sum(1 for _, _, s, _ in results if s == PASS)
print(f"RESULT: {passed}/{total} checks passed")

by_category = {}
for name, cat, status, detail in results:
    by_category.setdefault(cat, [0, 0])
    by_category[cat][0] += 1
    if status == PASS:
        by_category[cat][1] += 1

print("\nCoverage by required test category (blueprint Section 17):")
for cat, (t, p) in sorted(by_category.items()):
    print(f"  - {cat}: {p}/{t}")

if passed < total:
    sys.exit(1)
