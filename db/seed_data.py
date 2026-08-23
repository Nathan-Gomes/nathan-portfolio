"""
Seed sample data for the Phase 2 pilot: one property (Cedar Place), matching
the worked example in the project blueprint. All data is fictional/sample
data for development purposes only.
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "portfolio.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def build_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())

    cur = conn.cursor()

    # -------------------------------------------------------------
    # Property + aliases
    # -------------------------------------------------------------
    cur.execute("""
        INSERT INTO properties (canonical_name, address, units, ownership_entity, notes)
        VALUES (?, ?, ?, ?, ?)
    """, ("Cedar Place", "120 Cedar Street", 36, "1234567 Ontario Inc.",
          "Sample pilot property (fictional data)."))
    cedar_id = cur.lastrowid

    aliases = [
        ("name", "Cedar Apartments", "assistant filing", 0.95, 1),
        ("address", "120 Cedar St.", "accounting export", 0.98, 1),
        ("ownership_company", "1234567 Ontario Inc.", "legal docs", 1.0, 1),
        ("accounting_code", "PROP-004", "accounting export", 1.0, 1),
        ("utility_account", "W-10842", "utility bill", 0.9, 1),
        ("folder_name", "Cedar", "shared drive", 0.7, 0),
    ]
    for alias_type, value, source, conf, verified in aliases:
        cur.execute("""
            INSERT INTO property_aliases (property_id, alias_type, alias_value, source, confidence, verified)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (cedar_id, alias_type, value, source, conf, verified))

    # A second property so cross-property leakage can be tested.
    cur.execute("""
        INSERT INTO properties (canonical_name, address, units, ownership_entity, notes)
        VALUES (?, ?, ?, ?, ?)
    """, ("Maple Court", "58 Maple Avenue", 24, "7654321 Ontario Inc.",
          "Second sample property, used only to test isolation."))
    maple_id = cur.lastrowid
    cur.execute("""
        INSERT INTO property_aliases (property_id, alias_type, alias_value, source, confidence, verified)
        VALUES (?, 'name', 'Maple Court', 'seed', 1.0, 1)
    """, (maple_id,))

    # -------------------------------------------------------------
    # Vendors + aliases
    # -------------------------------------------------------------
    vendors = [
        ("ABC Plumbing Ltd.", "plumbing", "ops@abcplumbing.example", ["ABC Plumbing", "ABC PLBG", "A.B.C. Plumbing"]),
        ("Reliable Elevator Co.", "elevator", "service@reliableelevator.example", ["Reliable Elevator", "RelElev"]),
        ("Northside Boiler Services", "hvac", "dispatch@northsideboiler.example", ["Northside Boiler", "N. Boiler Svcs"]),
        ("GreenScape Landscaping", "landscaping", "info@greenscape.example", ["Greenscape", "Green Scape Inc."]),
        ("Metro Fire & Safety", "fire_safety", "contracts@metrofiresafety.example", ["Metro Fire Safety", "MetroFire"]),
    ]
    vendor_ids = {}
    for canonical, category, contact, aliases_list in vendors:
        cur.execute("""
            INSERT INTO vendors (canonical_name, service_category, contact_information, active)
            VALUES (?, ?, ?, 1)
        """, (canonical, category, contact))
        vid = cur.lastrowid
        vendor_ids[canonical] = vid
        for a in aliases_list:
            cur.execute("""
                INSERT INTO vendor_aliases (vendor_id, alias_value, verified) VALUES (?, ?, 1)
            """, (vid, a))

    # -------------------------------------------------------------
    # Equipment
    # -------------------------------------------------------------
    cur.execute("""
        INSERT INTO equipment (property_id, equipment_type, name, manufacturer, model,
                                serial_number, installation_date, condition, warranty_expiry,
                                location, status)
        VALUES (?, 'boiler', 'Boiler 2', 'Weil-McLain', 'WM-88', 'SN-88231',
                '2016-03-01', 'fair', '2021-03-01', 'Basement mechanical room', 'active')
    """, (cedar_id,))
    boiler2_id = cur.lastrowid

    cur.execute("""
        INSERT INTO equipment (property_id, equipment_type, name, manufacturer, model,
                                serial_number, installation_date, condition, warranty_expiry,
                                location, status)
        VALUES (?, 'boiler', 'Boiler 1', 'Weil-McLain', 'WM-88', 'SN-88230',
                '2016-03-01', 'good', '2021-03-01', 'Basement mechanical room', 'active')
    """, (cedar_id,))
    boiler1_id = cur.lastrowid

    cur.execute("""
        INSERT INTO equipment (property_id, equipment_type, name, manufacturer, model,
                                serial_number, installation_date, condition, warranty_expiry,
                                location, status)
        VALUES (?, 'elevator', 'Elevator A', 'Otis', 'Gen2', 'SN-OT4471',
                '2012-06-15', 'good', '2017-06-15', 'Main lobby', 'active')
    """, (cedar_id,))
    elevator_id = cur.lastrowid

    # -------------------------------------------------------------
    # Documents (contract, invoices, inspection report)
    # -------------------------------------------------------------
    def add_document(property_id, vendor_id, doc_type, title, status, authority_rank,
                      effective_date=None, received_date=None, confidence=1.0):
        cur.execute("""
            INSERT INTO documents (property_id, vendor_id, document_type, title, file_path,
                                    sha256_hash, status, authority_rank, effective_date,
                                    received_date, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (property_id, vendor_id, doc_type, title,
              f"/sample-files/{title.replace(' ', '_')}.pdf",
              f"sample-hash-{title[:12]}", status, authority_rank,
              effective_date, received_date, confidence))
        return cur.lastrowid

    elevator_contract_doc = add_document(
        cedar_id, vendor_ids["Reliable Elevator Co."], "contract",
        "Elevator Service Agreement - Cedar Place", "executed", 2,
        effective_date="2024-12-01", received_date="2024-11-20"
    )

    boiler_invoice_docs = []
    for i, (svc_date, desc, cost) in enumerate([
        ("2026-01-14", "Boiler 2 - circulation pump inspection, minor leak repair", 1180.00),
        ("2026-03-22", "Boiler 2 - emergency call, pressure relief valve replaced", 4650.00),
        ("2026-06-30", "Boiler 2 - recurring pressure loss, recommend circulation pump replacement", 3590.00),
    ]):
        doc_id = add_document(
            cedar_id, vendor_ids["Northside Boiler Services"], "invoice",
            f"Northside Boiler Invoice {svc_date}", "approved", 2,
            effective_date=svc_date, received_date=svc_date
        )
        boiler_invoice_docs.append((doc_id, svc_date, desc, cost))

    plumbing_invoice_doc = add_document(
        cedar_id, vendor_ids["ABC Plumbing Ltd."], "invoice",
        "ABC Plumbing Invoice - Unit 14 stack leak", "approved", 2,
        effective_date="2026-05-02", received_date="2026-05-02"
    )

    inspection_doc = add_document(
        cedar_id, vendor_ids["Northside Boiler Services"], "inspection_report",
        "Boiler Room Annual Inspection 2026", "final", 3,
        effective_date="2026-02-10", received_date="2026-02-11"
    )

    # A draft amendment that conflicts with the structured contract record,
    # used to exercise the "conflicting records" behavior from the blueprint.
    amendment_doc = add_document(
        cedar_id, vendor_ids["Reliable Elevator Co."], "contract",
        "Elevator Service Agreement Amendment (unverified)", "draft", 6,
        effective_date="2026-06-15", received_date="2026-06-18", confidence=0.55
    )

    # -------------------------------------------------------------
    # Document chunks (minimal, for keyword-based search_property_documents)
    # -------------------------------------------------------------
    chunks = [
        (elevator_contract_doc, 8, "Renewal and Termination",
         "This Agreement renews automatically for successive one-year terms unless "
         "either party provides written notice of termination at least 90 days "
         "prior to the expiry of the then-current term.", cedar_id,
         vendor_ids["Reliable Elevator Co."], elevator_id, "contract", "2024-12-01"),

        (amendment_doc, 1, "Amendment Summary",
         "This amendment proposes to extend the service term to February 28 in "
         "exchange for a 4% rate increase, pending signature by both parties.",
         cedar_id, vendor_ids["Reliable Elevator Co."], elevator_id, "contract", "2026-06-15"),

        (inspection_doc, 3, "Findings - Boiler Room",
         "Boiler 2 shows signs of recurring pressure loss consistent with a failing "
         "circulation pump. Recommend replacement within the next service interval "
         "to avoid unplanned downtime.", cedar_id, None, boiler2_id,
         "inspection_report", "2026-02-10"),

        (boiler_invoice_docs[2][0], 1, "Service Notes",
         "Third service call this year for pressure loss on Boiler 2. Circulation "
         "pump is the likely root cause; temporary seal replaced as a stopgap. "
         "Recommend full pump replacement.", cedar_id,
         vendor_ids["Northside Boiler Services"], boiler2_id, "invoice", "2026-06-30"),
    ]
    for doc_id, page, section, text, prop_id, vend_id, equip_id, dtype, eff_date in chunks:
        cur.execute("""
            INSERT INTO document_chunks (document_id, page_number, section, text,
                                          property_id, vendor_id, equipment_id,
                                          document_type, effective_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (doc_id, page, section, text, prop_id, vend_id, equip_id, dtype, eff_date))

    # -------------------------------------------------------------
    # Invoices (financial records)
    # -------------------------------------------------------------
    invoice_ids = {}

    for doc_id, svc_date, desc, cost in boiler_invoice_docs:
        cur.execute("""
            INSERT INTO invoices (property_id, vendor_id, invoice_number, invoice_date,
                                   category, amount, approved, document_id, notes)
            VALUES (?, ?, ?, ?, 'plumbing_hvac', ?, 1, ?, ?)
        """, (cedar_id, vendor_ids["Northside Boiler Services"],
              f"NBS-{svc_date}", svc_date, cost, doc_id, desc))
        invoice_ids[doc_id] = cur.lastrowid

    cur.execute("""
        INSERT INTO invoices (property_id, vendor_id, invoice_number, invoice_date,
                               category, amount, approved, document_id, notes)
        VALUES (?, ?, 'ABC-2026-0502', '2026-05-02', 'plumbing', 890.00, 1, ?, ?)
    """, (cedar_id, vendor_ids["ABC Plumbing Ltd."], plumbing_invoice_doc,
          "Unit 14 stack leak, repaired section of cast iron stack"))
    plumbing_invoice_id = cur.lastrowid

    # Landscaping (unrelated category, to test filtering)
    cur.execute("""
        INSERT INTO invoices (property_id, vendor_id, invoice_number, invoice_date,
                               category, amount, approved, notes)
        VALUES (?, ?, 'GS-2026-04', '2026-04-15', 'landscaping', 640.00, 1, 'Spring cleanup')
    """, (cedar_id, vendor_ids["GreenScape Landscaping"]))

    # -------------------------------------------------------------
    # Maintenance events (linking equipment, vendor, invoice, document)
    # -------------------------------------------------------------
    for i, (doc_id, svc_date, desc, cost) in enumerate(boiler_invoice_docs):
        emergency = 1 if i == 1 else 0
        cur.execute("""
            INSERT INTO maintenance_events (property_id, equipment_id, vendor_id,
                                             work_order_number, service_date, issue_category,
                                             description, emergency, status, cost,
                                             invoice_id, source_document_id)
            VALUES (?, ?, ?, ?, ?, 'hvac', ?, ?, 'closed', ?, ?, ?)
        """, (cedar_id, boiler2_id, vendor_ids["Northside Boiler Services"],
              f"WO-BLR2-{i+1}", svc_date, desc, emergency, cost,
              invoice_ids[doc_id], doc_id))

    cur.execute("""
        INSERT INTO maintenance_events (property_id, equipment_id, vendor_id,
                                         work_order_number, service_date, issue_category,
                                         description, emergency, status, cost,
                                         invoice_id, source_document_id)
        VALUES (?, ?, ?, 'WO-PLB-1', '2026-05-02', 'plumbing',
                'Unit 14 stack leak repair', 0, 'closed', 890.00, ?, ?)
    """, (cedar_id, None, vendor_ids["ABC Plumbing Ltd."], plumbing_invoice_id, plumbing_invoice_doc))

    # -------------------------------------------------------------
    # Contracts
    # -------------------------------------------------------------
    cur.execute("""
        INSERT INTO contracts (property_id, vendor_id, contract_type, effective_date,
                                expiry_date, renewal_type, notice_period_days,
                                termination_deadline, annual_cost, status,
                                source_document_id, review_status)
        VALUES (?, ?, 'elevator_service', '2024-12-01', '2026-11-30', 'auto-renew',
                90, '2026-09-01', 8400.00, 'active', ?, 'verified')
    """, (cedar_id, vendor_ids["Reliable Elevator Co."], elevator_contract_doc))
    elevator_contract_id = cur.lastrowid

    cur.execute("""
        INSERT INTO contracts (property_id, vendor_id, contract_type, effective_date,
                                expiry_date, renewal_type, notice_period_days,
                                termination_deadline, annual_cost, status,
                                source_document_id, review_status)
        VALUES (?, ?, 'fire_safety_inspection', '2025-01-01', '2026-12-31', 'manual',
                60, '2026-11-01', 2200.00, 'active', NULL, 'verified')
    """, (cedar_id, vendor_ids["Metro Fire & Safety"]))

    # -------------------------------------------------------------
    # Utility readings (water usage anomaly for Cedar Place)
    # -------------------------------------------------------------
    # Baseline ~ 420 m3/month; last 3 periods elevated -> anomaly finding below.
    water_usage = [
        ("2025-09-01", "2025-09-30", 415),
        ("2025-10-01", "2025-10-31", 430),
        ("2025-11-01", "2025-11-30", 405),
        ("2025-12-01", "2025-12-31", 440),
        ("2026-01-01", "2026-01-31", 425),
        ("2026-02-01", "2026-02-28", 418),
        ("2026-03-01", "2026-03-31", 590),   # anomaly begins
        ("2026-04-01", "2026-04-30", 610),
        ("2026-05-01", "2026-05-31", 625),
    ]
    for start, end, usage in water_usage:
        cur.execute("""
            INSERT INTO utility_readings (property_id, utility_category, period_start,
                                           period_end, usage_amount, usage_unit, cost)
            VALUES (?, 'water', ?, ?, ?, 'm3', ?)
        """, (cedar_id, start, end, usage, round(usage * 3.10, 2)))

    # -------------------------------------------------------------
    # Findings (pre-computed open issues; also derivable live by business_logic.py)
    # -------------------------------------------------------------
    cur.execute("""
        INSERT INTO findings (property_id, finding_type, description, severity,
                               estimated_exposure, status, related_equipment_id)
        VALUES (?, 'utility_anomaly', ?, 'high', 11800.00, 'open', NULL)
    """, (cedar_id,
          "Water consumption at Cedar Place has been above its normalized baseline "
          "for three consecutive billing periods (Mar-May 2026)."))

    cur.execute("""
        INSERT INTO findings (property_id, finding_type, description, severity,
                               estimated_exposure, status, related_equipment_id)
        VALUES (?, 'repeat_repair', ?, 'high', 9420.00, 'open', ?)
    """, (cedar_id,
          "Boiler 2 has required three service calls since January 2026, "
          "totalling $9,420.00. Latest report recommends circulation pump replacement.",
          boiler2_id))

    cur.execute("""
        INSERT INTO findings (property_id, finding_type, description, severity,
                               estimated_exposure, status, related_contract_id)
        VALUES (?, 'conflicting_records', ?, 'medium', NULL, 'open', ?)
    """, (cedar_id,
          "Elevator service contract lists expiry 2026-11-30 in the structured "
          "record, but an unverified June 15 amendment proposes extending it to "
          "February 28 with a 4% rate increase. Not yet confirmed.",
          elevator_contract_id))

    conn.commit()
    conn.close()
    print(f"Database built at {DB_PATH}")
    print(f"Cedar Place property_id = {cedar_id}, Maple Court property_id = {maple_id}")


if __name__ == "__main__":
    build_database()
