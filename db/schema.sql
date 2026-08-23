-- Private Real-Estate Portfolio Intelligence Assistant
-- Structured Portfolio Database Schema (Phase 2 pilot)
-- SQLite for pilot; designed to map cleanly onto PostgreSQL later.

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- Core entities
-- ---------------------------------------------------------------------

CREATE TABLE properties (
    property_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name  TEXT NOT NULL,
    address         TEXT,
    units           INTEGER,
    ownership_entity TEXT,
    notes           TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE property_aliases (
    alias_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER NOT NULL REFERENCES properties(property_id),
    alias_type      TEXT NOT NULL CHECK (alias_type IN (
                        'name','address','ownership_company','accounting_code',
                        'utility_account','meter_number','folder_name','email_identifier'
                    )),
    alias_value     TEXT NOT NULL,
    source          TEXT,
    confidence      REAL NOT NULL DEFAULT 1.0,
    verified        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_property_aliases_value ON property_aliases(alias_value);

CREATE TABLE vendors (
    vendor_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name      TEXT NOT NULL,
    service_category    TEXT,
    contact_information TEXT,
    active              INTEGER NOT NULL DEFAULT 1,
    notes               TEXT
);

CREATE TABLE vendor_aliases (
    alias_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id    INTEGER NOT NULL REFERENCES vendors(vendor_id),
    alias_value  TEXT NOT NULL,
    verified     INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_vendor_aliases_value ON vendor_aliases(alias_value);

CREATE TABLE equipment (
    equipment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id       INTEGER NOT NULL REFERENCES properties(property_id),
    equipment_type    TEXT NOT NULL,
    name              TEXT,
    manufacturer      TEXT,
    model             TEXT,
    serial_number     TEXT,
    installation_date TEXT,
    condition         TEXT,
    warranty_expiry   TEXT,
    location          TEXT,
    status            TEXT NOT NULL DEFAULT 'active',
    notes             TEXT
);

-- ---------------------------------------------------------------------
-- Documents (source of truth artifacts + retrieval index)
-- ---------------------------------------------------------------------

CREATE TABLE documents (
    document_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id      INTEGER REFERENCES properties(property_id),
    vendor_id        INTEGER REFERENCES vendors(vendor_id),
    document_type    TEXT NOT NULL CHECK (document_type IN (
                        'invoice','work_order','contract','inspection_report',
                        'quote','internal_note','insurance','acquisition','email','other'
                    )),
    title            TEXT NOT NULL,
    file_path        TEXT,
    sha256_hash      TEXT,
    status           TEXT NOT NULL DEFAULT 'approved' CHECK (status IN (
                        'approved','executed','final','draft','unverified','informal'
                    )),
    authority_rank   INTEGER NOT NULL DEFAULT 7,  -- 1 = highest authority, see business_logic.py AUTHORITY_RANKS
    effective_date   TEXT,
    received_date    TEXT,
    confidence       REAL NOT NULL DEFAULT 1.0,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE document_chunks (
    chunk_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id    INTEGER NOT NULL REFERENCES documents(document_id),
    page_number    INTEGER,
    section        TEXT,
    text           TEXT NOT NULL,
    property_id    INTEGER REFERENCES properties(property_id),
    vendor_id      INTEGER REFERENCES vendors(vendor_id),
    equipment_id   INTEGER REFERENCES equipment(equipment_id),
    document_type  TEXT,
    effective_date TEXT
    -- embedding column intentionally omitted in the SQLite pilot;
    -- production (pgvector) adds: embedding VECTOR(1536)
);

-- ---------------------------------------------------------------------
-- Financial + operational records
-- ---------------------------------------------------------------------

CREATE TABLE invoices (
    invoice_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER NOT NULL REFERENCES properties(property_id),
    vendor_id       INTEGER REFERENCES vendors(vendor_id),
    invoice_number  TEXT,
    invoice_date    TEXT NOT NULL,
    category        TEXT NOT NULL,       -- e.g. plumbing, electrical, utilities, elevator
    amount          REAL NOT NULL,
    approved        INTEGER NOT NULL DEFAULT 1,
    document_id     INTEGER REFERENCES documents(document_id),
    notes           TEXT
);
CREATE INDEX idx_invoices_property_date ON invoices(property_id, invoice_date);

CREATE TABLE maintenance_events (
    event_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id         INTEGER NOT NULL REFERENCES properties(property_id),
    equipment_id        INTEGER REFERENCES equipment(equipment_id),
    vendor_id           INTEGER REFERENCES vendors(vendor_id),
    work_order_number   TEXT,
    service_date        TEXT NOT NULL,
    issue_category      TEXT NOT NULL,   -- e.g. plumbing, HVAC, elevator
    description         TEXT,
    emergency           INTEGER NOT NULL DEFAULT 0,
    status              TEXT NOT NULL DEFAULT 'closed',
    cost                REAL,
    invoice_id          INTEGER REFERENCES invoices(invoice_id),
    source_document_id  INTEGER REFERENCES documents(document_id),
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_maint_property_date ON maintenance_events(property_id, service_date);

CREATE TABLE contracts (
    contract_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id          INTEGER NOT NULL REFERENCES properties(property_id),
    vendor_id            INTEGER REFERENCES vendors(vendor_id),
    contract_type        TEXT NOT NULL,  -- e.g. elevator service, landscaping, insurance
    effective_date       TEXT,
    expiry_date          TEXT,
    renewal_type         TEXT,           -- e.g. auto-renew, manual, month-to-month
    notice_period_days   INTEGER,
    termination_deadline TEXT,
    annual_cost          REAL,
    status               TEXT NOT NULL DEFAULT 'active',
    source_document_id   INTEGER REFERENCES documents(document_id),
    review_status        TEXT NOT NULL DEFAULT 'verified'
);

-- ---------------------------------------------------------------------
-- Utility readings (for anomaly detection)
-- ---------------------------------------------------------------------

CREATE TABLE utility_readings (
    reading_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id      INTEGER NOT NULL REFERENCES properties(property_id),
    utility_category TEXT NOT NULL,  -- water, gas, electricity
    period_start     TEXT NOT NULL,
    period_end       TEXT NOT NULL,
    usage_amount     REAL NOT NULL,
    usage_unit       TEXT NOT NULL,   -- m3, kWh, etc.
    cost             REAL,
    source_document_id INTEGER REFERENCES documents(document_id)
);
CREATE INDEX idx_utility_property_period ON utility_readings(property_id, period_start);

-- ---------------------------------------------------------------------
-- Findings / Anomalies / Actions (open issues surfaced to the owner)
-- ---------------------------------------------------------------------

CREATE TABLE findings (
    finding_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id     INTEGER NOT NULL REFERENCES properties(property_id),
    finding_type    TEXT NOT NULL CHECK (finding_type IN (
                        'utility_anomaly','repeat_repair','contract_deadline',
                        'conflicting_records','data_quality','other'
                    )),
    description     TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'medium' CHECK (severity IN ('low','medium','high')),
    estimated_exposure REAL,
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','resolved')),
    related_equipment_id INTEGER REFERENCES equipment(equipment_id),
    related_contract_id  INTEGER REFERENCES contracts(contract_id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    resolved_at     TEXT
);

CREATE TABLE audit_log (
    log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name    TEXT NOT NULL,
    arguments    TEXT,
    called_at    TEXT NOT NULL DEFAULT (datetime('now')),
    result_summary TEXT
);
