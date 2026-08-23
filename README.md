# Private Real-Estate Portfolio Intelligence — Pilot Build

This is a working Phase 2–5 pilot of the blueprint you uploaded: **Cedar Place**,
one sample property, running through a real structured database, a deterministic
business-logic layer, and a real MCP (Model Context Protocol) server — the same
protocol Claude uses for custom connectors. All data is fictional/sample data.

Everything below has been built, **tested end-to-end**, and deployed to AWS
Lambda with a public Function URL protected by a shared request header secret.

## What's in here

```
portfolio-intel/
├── db/
│   ├── schema.sql        # Full structured schema (properties, aliases, vendors,
│   │                       equipment, maintenance, contracts, invoices, utility
│   │                       readings, document chunks, findings, audit log)
│   ├── seed_data.py      # Builds portfolio.db with sample data for Cedar Place
│   │                       (+ a second property, Maple Court, to test isolation)
│   └── portfolio.db      # The built SQLite database (regenerate any time)
├── server/
│   ├── business_logic.py # Deterministic calculations — Claude never does math
│   ├── mcp_server.py     # The MCP connector for local use (stdio/HTTP transports)
│   └── lambda_handler.py # Stateless entrypoint for the AWS Lambda deployment
├── deploy/
│   ├── Dockerfile             # Lambda container image build
│   ├── requirements-lambda.txt
│   └── README.md               # Exact AWS CLI commands to deploy for ~$0/month
├── tests/
│   ├── test_business_logic.py  # Direct tests of every calculation
│   ├── test_mcp_client.py      # Real MCP client spawning the server and calling tools
│   ├── test_lambda_handler.py  # Simulated API Gateway/Lambda invocations
│   └── eval_questions.py       # Phase 5 evaluation: 32 checks across every
│                                  required category from the blueprint
└── requirements.txt
```

## Status against your blueprint's roadmap

| Phase | Status |
|---|---|
| Phase 0: Discovery (10 real questions) | **Not done yet** — see "What I need from you" below |
| Phase 1: Claude Project experiment | Skipped — went straight to structured pilot per your instruction |
| Phase 2: Curated database pilot | ✅ Done — Cedar Place fully populated |
| Phase 3: Document retrieval | ✅ Done (pilot-grade keyword search; semantic/pgvector is the production upgrade) |
| Phase 4: MCP connector | ✅ Done — 8 tools, stdio + HTTP transports verified locally |
| Phase 5: Evaluation | ✅ Done — 32/32 checks passing across all required categories |
| **Deployment** | ✅ Live — Lambda Function URL returns all 8 MCP tools |
| Phase 6: Controlled pilot with your brother | **Not started** — needs real documents + Claude connector registration |
| Phase 7: Portfolio rollout | Not started |

## The 8 tools exposed to Claude

The blueprint asked for 6; I added 2 more that `get_property_summary` and the
Cedar Place worked example both depend on:

1. `resolve_property(query)` — name/alias/address/accounting-code/utility-account → property
2. `get_property_summary(property_id)` — full briefing (the "give me an update" tool)
3. `search_property_documents(property_id, query, document_type?, limit?)`
4. `get_expense_history(property_id, category?, start_date?, end_date?)`
5. `get_maintenance_history(property_id, equipment_id?, start_date?, end_date?)`
6. `get_open_anomalies(property_id)`
7. `get_contract_deadlines(property_id, days_ahead?)` *(new)*
8. `get_utility_anomalies(property_id, utility_category?, threshold_pct?)` *(new)*

Every tool call is written to an `audit_log` table so you can review connector
usage, exactly as Section 4 (Layer 6) specifies.

## What's already been verified

Running `tests/eval_questions.py` checks 32 cases across every category the
blueprint's Phase 5 requires:

- **Property identity** (8/8) — canonical name, name alias, address alias, ownership
  entity, accounting code, utility account, and full-summary composition
- **Ambiguous names** (2/2) — unknown properties refuse to resolve; a match on an
  *unverified* alias is flagged as low-confidence rather than silently trusted
  (this is a real bug I found and fixed while testing — see below)
- **Expense totals** (6/6) — category filters, date-range filters, exact sums
- **Maintenance history** (3/3) — repeat-repair detection (Boiler 2 × 3 events,
  $9,420), emergency-call flagging, equipment-scoped filtering
- **Document retrieval** (3/3) — relevant passages found, irrelevant queries
  correctly return zero results, document-type filtering works
- **Contract dates** (2/2) — deadline window logic
- **Missing information** (3/3) — nonexistent equipment/category/utility data
  return explicit empty results, never a fabricated number
- **Conflicting records** (2/2) — the unverified elevator-contract amendment
  surfaces as an open finding rather than silently overriding the contract record
- **Unauthorized/cross-property information** (3/3) — Maple Court (the second
  sample property) cannot see any of Cedar Place's data through any tool

**Bug found and fixed during testing:** the original resolver treated an exact
match on *any* alias as high-confidence, even an unverified one (`"Cedar"` as a
loose folder-name alias). Fixed so unverified/low-confidence alias matches are
returned as `confidence: "low"` with an explicit warning, rather than resolved
silently — directly implementing the blueprint's Section 8 requirement that the
system "avoid silently selecting a value."

## How to run it yourself

```bash
cd nathan-portfolio
pip install -r requirements.txt --break-system-packages

# Rebuild the sample database any time
python3 db/seed_data.py

# Run all tests
python3 tests/test_business_logic.py
python3 tests/eval_questions.py
python3 tests/test_mcp_client.py     # spawns the real MCP server and calls it

# Run the connector itself
python3 server/mcp_server.py                # stdio transport (local MCP clients)
python3 server/mcp_server.py --http         # streamable-http on :8787 (remote connector)
```

## Deployment: why Lambda

You asked for something essentially free, simple, and single-user — Lambda's
**Always Free tier** (1M requests + 400,000 GB-seconds/month) is the only AWS
compute option that never expires regardless of account age; App Runner,
Lightsail, and EC2 all either cost a fixed monthly fee or depend on when your
AWS account was created (their free tiers changed in July 2025). For light,
personal use this stays at $0/month.

One real architectural snag surfaced during testing: the MCP SDK's built-in
`streamable_http_app()` runs a session manager meant for a long-lived server
process — it can't be re-entered per request the way Lambda invocations work,
and raised a `RuntimeError` on the second call. Rather than force that
mismatch, `lambda_handler.py` talks directly to the same registered tools
(`mcp.list_tools()` / `mcp.call_tool()`) and implements just the JSON-RPC
methods a client actually needs. This was verified with simulated API Gateway
events, including a simulated cold start with no prior session state, and a
simulated read-only Lambda filesystem (audit logs correctly fall back to
`/tmp`). See `deploy/README.md` for the full deployment steps and the exact
tradeoffs (no custom domain yet, no persistent audit log across cold starts).

## What I need from you to go further

The blueprint is explicit that **Phase 0 (Discovery) must happen before real
build-out continues** — I skipped straight to the pilot per your instruction,
but the next real milestone needs your brother's input, not more of my code:

1. **Ten real questions** he'd actually ask about a real building.
2. **One real property's real documents** (invoices, a contract, maintenance
   records) to replace Cedar Place's fictional data — this is where the
   ingestion pipeline (OCR, classification, field extraction) actually gets
   built and tested against reality instead of clean synthetic data.
3. **Register the deployed Function URL in Claude** as a custom connector and
   configure the same static request header used by the Lambda environment.

Everything above this line is genuinely done and tested. The honest gap is:
this proves the architecture works end-to-end, including a live Lambda endpoint,
but Phase 6 (his real pilot) can't start until the connector is added to Claude,
there's a real property, and there are real documents.
