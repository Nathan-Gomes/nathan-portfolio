"""
Private Real-Estate Portfolio Intelligence -- MCP Connector (Phase 4)

Exposes exactly the six read-only tools specified in the blueprint:
  - resolve_property
  - get_property_summary
  - search_property_documents
  - get_expense_history
  - get_maintenance_history
  - get_open_anomalies

Plus two supporting tools referenced throughout the blueprint's worked
examples (contract deadlines, utility anomalies) since get_property_summary
and the Cedar Place example both depend on them.

Design constraints followed from the blueprint:
  - Claude never gets raw DB/file-system access -- only these structured tools.
  - Every response is JSON with source document references.
  - All tools are read-only (no writes, no payments, no account changes).
  - Every call is written to audit_log for Nathan to review.

Run modes:
  python3 mcp_server.py            -> stdio transport (for local MCP clients / testing)
  python3 mcp_server.py --http      -> streamable-http transport on :8787 (for remote registration)
"""
import sys
import os
import json
import sqlite3
import argparse

sys.path.insert(0, os.path.dirname(__file__))
import business_logic as bl

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("portfolio-intelligence")

AUDIT_DB_PATH = os.environ.get("MCP_AUDIT_DB_PATH", bl.DB_PATH)


def _ensure_audit_table(path):
    """Create the audit_log table if it doesn't exist yet -- needed when
    AUDIT_DB_PATH points at a fresh file (e.g. Lambda's writable /tmp,
    which starts empty on every cold start)."""
    try:
        conn = sqlite3.connect(path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name    TEXT NOT NULL,
                arguments    TEXT,
                called_at    TEXT NOT NULL DEFAULT (datetime('now')),
                result_summary TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[audit setup warning] {e}", file=sys.stderr)


_ensure_audit_table(AUDIT_DB_PATH)


def _audit(tool_name, arguments, result_summary):
    try:
        conn = sqlite3.connect(AUDIT_DB_PATH)
        conn.execute(
            "INSERT INTO audit_log (tool_name, arguments, result_summary) VALUES (?, ?, ?)",
            (tool_name, json.dumps(arguments, default=str), result_summary[:500]),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # Auditing must never break the tool call itself.
        print(f"[audit warning] {e}", file=sys.stderr)


@mcp.tool()
def resolve_property(query: str) -> dict:
    """
    Resolve a free-text property reference (name, alias, address, ownership
    company, accounting code, or utility account) to a canonical property
    record. Always call this first before any property-specific tool, and
    pass its returned property_id to the other tools -- never guess an id.

    Returns resolved=False with candidates if the reference is ambiguous or
    unknown; Claude should ask the user to disambiguate rather than guessing.
    """
    result = bl.resolve_property(query)
    _audit("resolve_property", {"query": query}, json.dumps(result, default=str))
    return result


@mcp.tool()
def get_property_summary(property_id: int) -> dict:
    """
    Return a full briefing for a resolved property: profile, open findings
    (anomalies/repeat repairs/conflicting records), recent maintenance
    events, top recent expenses, and upcoming contract deadlines. Use this
    for broad questions like "give me an update on X".
    """
    result = bl.get_property_summary(property_id)
    _audit("get_property_summary", {"property_id": property_id}, json.dumps(result, default=str))
    return result


@mcp.tool()
def search_property_documents(property_id: int, query: str, document_type: str = None, limit: int = 5) -> dict:
    """
    Search a specific property's documents (contracts, invoices, inspection
    reports, work orders, notes) for passages relevant to `query`. Always
    scoped to a single property_id -- never searches across the whole
    portfolio -- to prevent cross-property data leakage. Optionally filter
    by document_type: invoice, work_order, contract, inspection_report,
    quote, internal_note, insurance, acquisition, email, other.
    """
    result = bl.search_property_documents(property_id, query, document_type, limit)
    _audit("search_property_documents",
           {"property_id": property_id, "query": query, "document_type": document_type},
           json.dumps(result, default=str))
    return result


@mcp.tool()
def get_expense_history(property_id: int, category: str = None, start_date: str = None, end_date: str = None) -> dict:
    """
    Deterministic total spending for a property, optionally filtered by
    category (e.g. plumbing, plumbing_hvac, landscaping) and date range
    (YYYY-MM-DD). Only counts approved invoices; unapproved/excluded records
    are returned separately for transparency. Use this instead of estimating
    totals from document text.
    """
    result = bl.get_expense_history(property_id, category, start_date, end_date)
    _audit("get_expense_history",
           {"property_id": property_id, "category": category, "start_date": start_date, "end_date": end_date},
           json.dumps(result, default=str))
    return result


@mcp.tool()
def get_maintenance_history(property_id: int, equipment_id: int = None,
                             start_date: str = None, end_date: str = None) -> dict:
    """
    Maintenance event history for a property (optionally scoped to one
    equipment_id), including automatic repeat-issue detection (same
    equipment serviced multiple times) with total cost and average days
    between events. Use this for "what keeps breaking" style questions.
    """
    result = bl.get_maintenance_history(property_id, equipment_id, start_date, end_date)
    _audit("get_maintenance_history",
           {"property_id": property_id, "equipment_id": equipment_id,
            "start_date": start_date, "end_date": end_date},
           json.dumps(result, default=str))
    return result


@mcp.tool()
def get_open_anomalies(property_id: int) -> dict:
    """
    Open findings for a property: utility anomalies, repeat repairs,
    contract deadlines, conflicting records, or data-quality issues that
    have not yet been resolved. Use this to proactively surface issues
    even if the user didn't ask about a specific one.
    """
    result = bl.get_open_anomalies(property_id)
    _audit("get_open_anomalies", {"property_id": property_id}, json.dumps(result, default=str))
    return result


@mcp.tool()
def get_contract_deadlines(property_id: int, days_ahead: int = 90) -> dict:
    """
    Contracts for a property with a termination-notice or expiry deadline
    within `days_ahead` days, plus all active contracts for reference.
    Use this for renewal/cancellation deadline questions.
    """
    result = bl.get_contract_deadlines(property_id, days_ahead)
    _audit("get_contract_deadlines", {"property_id": property_id, "days_ahead": days_ahead},
           json.dumps(result, default=str))
    return result


@mcp.tool()
def get_utility_anomalies(property_id: int, utility_category: str = "water", threshold_pct: float = 15.0) -> dict:
    """
    Detects utility billing periods that exceed the trailing baseline
    average by more than threshold_pct, with an estimated annual cost
    exposure. utility_category: water, gas, or electricity.
    """
    result = bl.get_utility_anomalies(property_id, utility_category, threshold_pct)
    _audit("get_utility_anomalies",
           {"property_id": property_id, "utility_category": utility_category, "threshold_pct": threshold_pct},
           json.dumps(result, default=str))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--http", action="store_true", help="Run as streamable-http server on :8787")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8787)
    else:
        mcp.run(transport="stdio")
