import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "server"))
import business_logic as bl


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def show(obj):
    print(json.dumps(obj, indent=2, default=str))


section("resolve_property('Cedar Place')")
r1 = bl.resolve_property("Cedar Place")
show(r1)
assert r1["resolved"] and r1["property"]["canonical_name"] == "Cedar Place"

section("resolve_property('120 Cedar St.') -- alias match")
r2 = bl.resolve_property("120 Cedar St.")
show(r2)
assert r2["resolved"]

section("resolve_property('PROP-004') -- accounting code alias")
r3 = bl.resolve_property("PROP-004")
show(r3)
assert r3["resolved"]

section("resolve_property('cedar plce') -- fuzzy / typo")
r4 = bl.resolve_property("cedar plce")
show(r4)

section("resolve_property('Nonexistent Towers')")
r5 = bl.resolve_property("Nonexistent Towers")
show(r5)
assert not r5["resolved"]

cedar_id = r1["property"]["property_id"]

section("get_property_summary(Cedar Place)")
summary = bl.get_property_summary(cedar_id)
show(summary)

section("get_expense_history(Cedar Place, category='plumbing_hvac')")
exp = bl.get_expense_history(cedar_id, category="plumbing_hvac")
show(exp)
assert exp["total_cost"] == round(1180.00 + 4650.00 + 3590.00, 2)

section("get_expense_history(Cedar Place) -- all categories")
exp_all = bl.get_expense_history(cedar_id)
show(exp_all)

section("get_maintenance_history(Cedar Place) -- repeat issue detection")
maint = bl.get_maintenance_history(cedar_id)
show(maint)
assert len(maint["repeat_issues"]) >= 1
assert maint["repeat_issues"][0]["event_count"] == 3

section("get_contract_deadlines(Cedar Place, days_ahead=400)")
deadlines = bl.get_contract_deadlines(cedar_id, days_ahead=400)
show(deadlines)

section("get_utility_anomalies(Cedar Place, 'water')")
anomalies = bl.get_utility_anomalies(cedar_id, "water")
show(anomalies)
assert len(anomalies["anomalies"]) >= 1

section("get_open_anomalies(Cedar Place)")
findings = bl.get_open_anomalies(cedar_id)
show(findings)
assert findings["count"] == 3

section("search_property_documents(Cedar Place, 'circulation pump')")
search = bl.search_property_documents(cedar_id, "circulation pump")
show(search)
assert search["result_count"] >= 1

section("Cross-property isolation check: search Maple Court for Cedar terms")
maple = bl.resolve_property("Maple Court")
search_maple = bl.search_property_documents(maple["property"]["property_id"], "circulation pump boiler elevator")
show(search_maple)
assert search_maple["result_count"] == 0

print("\n\nALL ASSERTIONS PASSED")
