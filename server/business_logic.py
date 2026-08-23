"""
Deterministic business logic for the Portfolio Intelligence system.

Per the blueprint (Section 6 / 11), Claude never performs arithmetic or
authority-ranking itself -- it calls these tested functions and explains
the results. Every function returns plain dicts/lists (JSON-serializable)
with source references so answers can be cited back to documents.
"""
import sqlite3
import os
from datetime import datetime, date
from difflib import SequenceMatcher

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "portfolio.db")

# Source-authority hierarchy (Section 8 of the blueprint). Lower number = higher authority.
AUTHORITY_RANKS = {
    "approved_structured_record": 1,
    "executed_contract_or_invoice": 2,
    "final_inspection_or_service_report": 3,
    "approved_internal_note": 4,
    "vendor_quote": 5,
    "draft_document": 6,
    "unverified_extraction": 7,
    "informal_email_or_note": 8,
}


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _similarity(a, b):
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


# ---------------------------------------------------------------------
# resolve_property
# ---------------------------------------------------------------------

def resolve_property(query: str):
    """
    Resolve a free-text property reference (name, address, ownership entity,
    accounting code, utility account, etc.) to a canonical property.

    Returns a dict with:
      - resolved: bool
      - property (if resolved uniquely)
      - candidates (if ambiguous)
      - message
    """
    conn = _connect()
    cur = conn.cursor()

    query_norm = query.strip().lower()

    # 1. Exact match on canonical name
    cur.execute("SELECT * FROM properties WHERE lower(canonical_name) = ?", (query_norm,))
    row = cur.fetchone()
    if row:
        return _resolved_property_result(cur, row)

    # 2. Exact match on any alias
    cur.execute("""
        SELECT p.*, pa.alias_value, pa.confidence, pa.verified
        FROM property_aliases pa
        JOIN properties p ON p.property_id = pa.property_id
        WHERE lower(pa.alias_value) = ?
    """, (query_norm,))
    rows = cur.fetchall()
    if len(rows) >= 1:
        distinct_props = {r["property_id"] for r in rows}
        if len(distinct_props) > 1:
            return {
                "resolved": False,
                "candidates": [dict(r) for r in rows],
                "message": f"'{query}' matches aliases belonging to more than one property. Disambiguation required."
            }
        best_row = max(rows, key=lambda r: (r["verified"], r["confidence"]))
        if best_row["verified"] and best_row["confidence"] >= 0.85:
            return _resolved_property_result(cur, best_row, matched_alias=best_row["alias_value"])
        # Matched, but on an unverified or low-confidence alias -- surface that plainly
        # rather than resolving silently at "high" confidence.
        cur.execute("SELECT * FROM properties WHERE property_id = ?", (best_row["property_id"],))
        prop = dict(cur.fetchone())
        return {
            "resolved": True,
            "confidence": "low",
            "matched_alias": best_row["alias_value"],
            "property": prop,
            "message": (f"Matched via an unverified or low-confidence alias "
                        f"('{best_row['alias_value']}', confidence={best_row['confidence']}, "
                        f"verified={bool(best_row['verified'])}). Confirm before relying on this.")
        }

    # 3. Fuzzy match across names + aliases (only used to suggest, never to auto-resolve)
    cur.execute("SELECT property_id, canonical_name FROM properties")
    all_props = cur.fetchall()
    cur.execute("SELECT property_id, alias_value FROM property_aliases")
    all_aliases = cur.fetchall()

    scored = []
    for p in all_props:
        scored.append((_similarity(query, p["canonical_name"]), p["property_id"], p["canonical_name"]))
    for a in all_aliases:
        scored.append((_similarity(query, a["alias_value"]), a["property_id"], a["alias_value"]))

    scored.sort(reverse=True, key=lambda x: x[0])
    top = [s for s in scored if s[0] >= 0.6][:5]

    if not top:
        return {
            "resolved": False,
            "candidates": [],
            "message": f"No property could be resolved for '{query}'. It may not yet be in the system."
        }

    if len(top) == 1 or (top[0][0] - (top[1][0] if len(top) > 1 else 0)) > 0.2:
        # Confident single fuzzy match -- still flagged as low-confidence, not silently trusted.
        best = top[0]
        cur.execute("SELECT * FROM properties WHERE property_id = ?", (best[1],))
        prop_row = cur.fetchone()
        return {
            "resolved": True,
            "confidence": "low",
            "matched_on": best[2],
            "property": dict(prop_row),
            "message": (f"No exact match; best fuzzy match was '{best[2]}' "
                        f"(similarity {best[0]:.2f}). Confirm before relying on this.")
        }

    return {
        "resolved": False,
        "candidates": [{"property_id": s[1], "matched_on": s[2], "similarity": round(s[0], 2)} for s in top],
        "message": f"'{query}' is ambiguous among several close matches. Disambiguation required."
    }


def _resolved_property_result(cur, row, matched_alias=None):
    cur.execute("SELECT * FROM properties WHERE property_id = ?", (row["property_id"],))
    prop = dict(cur.fetchone())
    result = {"resolved": True, "confidence": "high", "property": prop}
    if matched_alias:
        result["matched_alias"] = matched_alias
    return result


# ---------------------------------------------------------------------
# get_property_summary
# ---------------------------------------------------------------------

def get_property_summary(property_id: int):
    """
    Return a full property briefing: profile, recent significant expenses,
    open findings, repeat repairs, upcoming contract deadlines, recent
    maintenance events, and source document references.
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("SELECT * FROM properties WHERE property_id = ?", (property_id,))
    prop_row = cur.fetchone()
    if not prop_row:
        return {"error": f"No property with property_id={property_id}"}
    prop = dict(prop_row)

    cur.execute("""
        SELECT * FROM findings WHERE property_id = ? AND status = 'open'
        ORDER BY severity DESC, created_at DESC
    """, (property_id,))
    findings = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT * FROM maintenance_events WHERE property_id = ?
        ORDER BY service_date DESC LIMIT 5
    """, (property_id,))
    recent_maintenance = [dict(r) for r in cur.fetchall()]

    cur.execute("""
        SELECT * FROM invoices WHERE property_id = ? AND approved = 1
        ORDER BY amount DESC LIMIT 5
    """, (property_id,))
    top_expenses = [dict(r) for r in cur.fetchall()]

    deadlines = get_contract_deadlines(property_id, days_ahead=180)

    return {
        "property": prop,
        "open_findings": findings,
        "recent_maintenance_events": recent_maintenance,
        "top_recent_expenses": top_expenses,
        "upcoming_contract_deadlines": deadlines.get("contracts", []),
        "source_note": "All figures derived from approved invoices and structured maintenance records."
    }


# ---------------------------------------------------------------------
# get_expense_history
# ---------------------------------------------------------------------

def get_expense_history(property_id: int, category: str = None, start_date: str = None, end_date: str = None):
    """
    Deterministic expense total for a property, optionally filtered by
    category and date range. Only approved invoices are counted.
    """
    conn = _connect()
    cur = conn.cursor()

    query = "SELECT * FROM invoices WHERE property_id = ? AND approved = 1"
    params = [property_id]
    if category:
        query += " AND category = ?"
        params.append(category)
    if start_date:
        query += " AND invoice_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND invoice_date <= ?"
        params.append(end_date)
    query += " ORDER BY invoice_date"

    cur.execute(query, params)
    rows = [dict(r) for r in cur.fetchall()]

    total = round(sum(r["amount"] for r in rows), 2)

    monthly = {}
    for r in rows:
        month = r["invoice_date"][:7]
        monthly[month] = round(monthly.get(month, 0) + r["amount"], 2)

    # Excluded (unapproved) records, for transparency
    excl_query = "SELECT invoice_id, invoice_date, amount, notes FROM invoices WHERE property_id = ? AND approved = 0"
    cur.execute(excl_query, (property_id,))
    excluded = [dict(r) for r in cur.fetchall()]

    return {
        "property_id": property_id,
        "category": category,
        "start_date": start_date,
        "end_date": end_date,
        "total_cost": total,
        "invoice_count": len(rows),
        "monthly_totals": monthly,
        "approved_invoice_ids": [r["invoice_id"] for r in rows],
        "excluded_records": excluded,
        "source_document_ids": [r["document_id"] for r in rows if r.get("document_id")],
    }


# ---------------------------------------------------------------------
# get_maintenance_history
# ---------------------------------------------------------------------

def get_maintenance_history(property_id: int, equipment_id: int = None,
                             start_date: str = None, end_date: str = None):
    """
    Maintenance event history with repeat-issue detection.
    """
    conn = _connect()
    cur = conn.cursor()

    query = "SELECT * FROM maintenance_events WHERE property_id = ?"
    params = [property_id]
    if equipment_id:
        query += " AND equipment_id = ?"
        params.append(equipment_id)
    if start_date:
        query += " AND service_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND service_date <= ?"
        params.append(end_date)
    query += " ORDER BY service_date"

    cur.execute(query, params)
    events = [dict(r) for r in cur.fetchall()]

    total_cost = round(sum(e["cost"] or 0 for e in events), 2)
    emergency_count = sum(1 for e in events if e["emergency"])

    vendor_ids = sorted({e["vendor_id"] for e in events if e["vendor_id"]})
    vendors = []
    if vendor_ids:
        q_marks = ",".join("?" * len(vendor_ids))
        cur.execute(f"SELECT vendor_id, canonical_name FROM vendors WHERE vendor_id IN ({q_marks})", vendor_ids)
        vendors = [dict(r) for r in cur.fetchall()]

    # Time between events (days) per equipment, for repeat-issue detection
    from collections import defaultdict
    by_equipment = defaultdict(list)
    for e in events:
        if e["equipment_id"]:
            by_equipment[e["equipment_id"]].append(e)

    repeat_issues = []
    for eq_id, evs in by_equipment.items():
        if len(evs) >= 2:
            dates = sorted(datetime.strptime(e["service_date"], "%Y-%m-%d") for e in evs)
            gaps = [(dates[i + 1] - dates[i]).days for i in range(len(dates) - 1)]
            cur.execute("SELECT name, equipment_type FROM equipment WHERE equipment_id = ?", (eq_id,))
            eq_row = cur.fetchone()
            repeat_issues.append({
                "equipment_id": eq_id,
                "equipment_name": eq_row["name"] if eq_row else None,
                "equipment_type": eq_row["equipment_type"] if eq_row else None,
                "event_count": len(evs),
                "total_cost": round(sum(e["cost"] or 0 for e in evs), 2),
                "avg_days_between_events": round(sum(gaps) / len(gaps), 1) if gaps else None,
                "event_ids": [e["event_id"] for e in evs],
            })

    return {
        "property_id": property_id,
        "equipment_id": equipment_id,
        "event_count": len(events),
        "total_cost": total_cost,
        "emergency_event_count": emergency_count,
        "vendors": vendors,
        "repeat_issues": repeat_issues,
        "events": events,
        "source_document_ids": [e["source_document_id"] for e in events if e.get("source_document_id")],
    }


# ---------------------------------------------------------------------
# get_contract_deadlines
# ---------------------------------------------------------------------

def get_contract_deadlines(property_id: int, days_ahead: int = 90):
    """
    Contracts with a termination/notice deadline within `days_ahead` days
    from today (server clock), plus all active contracts for reference.
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.*, v.canonical_name as vendor_name
        FROM contracts c
        LEFT JOIN vendors v ON v.vendor_id = c.vendor_id
        WHERE c.property_id = ?
        ORDER BY c.expiry_date
    """, (property_id,))
    all_contracts = [dict(r) for r in cur.fetchall()]

    today = date.today()
    upcoming = []
    for c in all_contracts:
        deadline_str = c.get("termination_deadline") or c.get("expiry_date")
        if not deadline_str:
            continue
        try:
            deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_until = (deadline - today).days
        if days_until <= days_ahead:
            c["days_until_deadline"] = days_until
            c["deadline_type"] = "termination_notice" if c.get("termination_deadline") else "expiry"
            upcoming.append(c)

    return {
        "property_id": property_id,
        "as_of": today.isoformat(),
        "days_ahead": days_ahead,
        "contracts": upcoming,
        "all_contracts": all_contracts,
    }


# ---------------------------------------------------------------------
# get_utility_anomalies
# ---------------------------------------------------------------------

def get_utility_anomalies(property_id: int, utility_category: str = "water", threshold_pct: float = 15.0):
    """
    Flags billing periods where usage exceeds the trailing baseline average
    by more than threshold_pct. Deterministic, simple moving-baseline method
    (documented, not a black box).
    """
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM utility_readings
        WHERE property_id = ? AND utility_category = ?
        ORDER BY period_start
    """, (property_id, utility_category))
    readings = [dict(r) for r in cur.fetchall()]

    if len(readings) < 4:
        return {
            "property_id": property_id,
            "utility_category": utility_category,
            "anomalies": [],
            "message": "Not enough historical readings to establish a reliable baseline."
        }

    anomalies = []
    baseline_window = 6
    for i in range(baseline_window, len(readings)):
        baseline_vals = [r["usage_amount"] for r in readings[i - baseline_window:i]]
        baseline = sum(baseline_vals) / len(baseline_vals)
        current = readings[i]["usage_amount"]
        pct_over = ((current - baseline) / baseline) * 100
        if pct_over >= threshold_pct:
            anomalies.append({
                "period_start": readings[i]["period_start"],
                "period_end": readings[i]["period_end"],
                "usage_amount": current,
                "baseline": round(baseline, 1),
                "pct_over_baseline": round(pct_over, 1),
                "cost": readings[i]["cost"],
            })

    estimated_annual_exposure = None
    if anomalies:
        avg_excess_cost_per_period = sum(
            (a["cost"] or 0) * (a["pct_over_baseline"] / (100 + a["pct_over_baseline"])) for a in anomalies
        ) / len(anomalies)
        estimated_annual_exposure = round(avg_excess_cost_per_period * 12, 2)

    return {
        "property_id": property_id,
        "utility_category": utility_category,
        "baseline_window_periods": baseline_window,
        "threshold_pct": threshold_pct,
        "anomalies": anomalies,
        "estimated_annual_exposure": estimated_annual_exposure,
        "source": "utility_readings table",
    }


# ---------------------------------------------------------------------
# get_open_anomalies / findings
# ---------------------------------------------------------------------

def get_open_anomalies(property_id: int):
    conn = _connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM findings WHERE property_id = ? AND status = 'open'
        ORDER BY severity DESC, created_at DESC
    """, (property_id,))
    findings = [dict(r) for r in cur.fetchall()]
    return {"property_id": property_id, "open_findings": findings, "count": len(findings)}


# ---------------------------------------------------------------------
# search_property_documents (metadata-filtered keyword search;
# a stand-in for semantic + pgvector search in the pilot)
# ---------------------------------------------------------------------

def search_property_documents(property_id: int, query: str, document_type: str = None, limit: int = 5):
    """
    Metadata-filtered search over document_chunks. In the pilot this is a
    keyword search; production replaces the ranking step with pgvector
    cosine similarity while keeping the same property_id pre-filter to
    prevent cross-property contamination (Section 10 of the blueprint).
    """
    conn = _connect()
    cur = conn.cursor()

    sql = """
        SELECT dc.*, d.title, d.status as document_status, d.authority_rank,
               d.effective_date as doc_effective_date, d.confidence as doc_confidence
        FROM document_chunks dc
        JOIN documents d ON d.document_id = dc.document_id
        WHERE dc.property_id = ?
    """
    params = [property_id]
    if document_type:
        sql += " AND dc.document_type = ?"
        params.append(document_type)

    cur.execute(sql, params)
    all_chunks = [dict(r) for r in cur.fetchall()]

    query_terms = [t.lower() for t in query.split() if len(t) > 2]

    def score(chunk):
        text = chunk["text"].lower()
        return sum(text.count(term) for term in query_terms)

    scored = [(score(c), c) for c in all_chunks]
    scored = [sc for sc in scored if sc[0] > 0]
    # Prioritize authority rank (lower = more authoritative) as a tiebreaker
    scored.sort(key=lambda sc: (-sc[0], sc[1]["authority_rank"]))

    results = [c for _, c in scored[:limit]]

    return {
        "property_id": property_id,
        "query": query,
        "result_count": len(results),
        "results": results,
        "note": "Ranked by keyword relevance and source authority (pilot mode; semantic search not yet enabled).",
    }
