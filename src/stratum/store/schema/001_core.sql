-- Core tables, as documented in ARCHITECTURE.md's "store/" section.
-- Every table carries knowledge_time; tables whose source cannot supply a
-- real one (the theme graph) set pit_unsafe = 1 and studies must set
-- allow_lookahead: true to touch them.

CREATE TABLE instruments (
    instrument_id       TEXT PRIMARY KEY,       -- stable internal id, e.g. "NVDA"
    symbol              TEXT NOT NULL,
    rh_symbol           TEXT,
    ibkr_contract_id    INTEGER,
    isin                TEXT,
    asset_class         TEXT NOT NULL DEFAULT 'equity',
    descriptive_only    INTEGER NOT NULL DEFAULT 0 CHECK (descriptive_only IN (0, 1)),
    resolution_evidence TEXT,                    -- JSON: how symbol/contract_id was resolved
    knowledge_time      TEXT NOT NULL,
    pit_unsafe          INTEGER NOT NULL DEFAULT 0 CHECK (pit_unsafe IN (0, 1))
);

CREATE TABLE bars (
    instrument_id    TEXT NOT NULL REFERENCES instruments(instrument_id),
    date             TEXT NOT NULL,
    open             REAL,
    high             REAL,
    low              REAL,
    close            REAL,
    volume           INTEGER,
    adjustment_type  TEXT NOT NULL DEFAULT 'unadjusted',
    knowledge_time   TEXT NOT NULL,
    PRIMARY KEY (instrument_id, date, adjustment_type)
);

CREATE INDEX idx_bars_instrument_date ON bars(instrument_id, date);

CREATE TABLE earnings (
    instrument_id   TEXT NOT NULL REFERENCES instruments(instrument_id),
    fiscal_year     INTEGER NOT NULL,
    fiscal_quarter  INTEGER NOT NULL,
    report_date     TEXT NOT NULL,
    timing          TEXT NOT NULL CHECK (timing IN ('am', 'pm')),
    eps_estimate    REAL,
    eps_actual      REAL,
    verified        INTEGER NOT NULL DEFAULT 0 CHECK (verified IN (0, 1)),
    knowledge_time  TEXT NOT NULL,
    PRIMARY KEY (instrument_id, fiscal_year, fiscal_quarter)
);

CREATE TABLE events (
    event_id         TEXT PRIMARY KEY,             -- sha256(instrument_id|event_time|event_type|subtype)
    instrument_id    TEXT REFERENCES instruments(instrument_id),  -- nullable: macro events have no single instrument
    event_time       TEXT NOT NULL,
    event_type       TEXT NOT NULL CHECK (event_type IN ('earnings', 'macro_release', 'sanctions_action', 'policy_milestone')),
    subtype          TEXT,                          -- fomc/cpi/nfp/gdp/pce for macro_release
    timing           TEXT CHECK (timing IN ('am', 'pm')),
    metadata         TEXT,                          -- JSON blob, event-type-specific
    knowledge_time   TEXT NOT NULL,
    pit_unsafe       INTEGER NOT NULL DEFAULT 0 CHECK (pit_unsafe IN (0, 1))
);

CREATE INDEX idx_events_instrument_time ON events(instrument_id, event_time);
CREATE INDEX idx_events_type_time ON events(event_type, event_time);

CREATE TABLE themes (
    theme_key    TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    description  TEXT
);

CREATE TABLE theme_membership (
    theme_key       TEXT NOT NULL REFERENCES themes(theme_key),
    instrument_id   TEXT NOT NULL REFERENCES instruments(instrument_id),
    rank            INTEGER NOT NULL,               -- 1 = most central
    knowledge_time  TEXT NOT NULL,                  -- snapshot date (graph has no real history)
    pit_unsafe      INTEGER NOT NULL DEFAULT 1 CHECK (pit_unsafe IN (0, 1)),
    PRIMARY KEY (theme_key, instrument_id)
);

CREATE TABLE competitor_edges (
    from_instrument_id  TEXT NOT NULL REFERENCES instruments(instrument_id),
    to_instrument_id    TEXT NOT NULL REFERENCES instruments(instrument_id),
    rank                INTEGER NOT NULL,
    evidence_text       TEXT,
    knowledge_time      TEXT NOT NULL,               -- snapshot date
    pit_unsafe          INTEGER NOT NULL DEFAULT 1 CHECK (pit_unsafe IN (0, 1)),
    PRIMARY KEY (from_instrument_id, to_instrument_id)
);

CREATE TABLE labels (
    event_id            TEXT NOT NULL REFERENCES events(event_id),
    classifier_version  TEXT NOT NULL,
    label_class         TEXT NOT NULL,
    confidence           REAL CHECK (confidence BETWEEN 0 AND 1),
    evidence             TEXT,
    model_id             TEXT,
    prompt_hash          TEXT,
    knowledge_time       TEXT NOT NULL,
    PRIMARY KEY (event_id, classifier_version)
);

-- positions is documented here for completeness (per ARCHITECTURE.md's core
-- table list) but is never populated by tests or fixtures with real data,
-- is gitignored at the data/ layer, and is out of scope for PR-E's loaders.
CREATE TABLE positions (
    account_id     TEXT NOT NULL,
    symbol         TEXT NOT NULL,
    snapshot_time  TEXT NOT NULL,
    quantity       REAL NOT NULL,
    cost_basis     REAL,
    PRIMARY KEY (account_id, symbol, snapshot_time)
);

CREATE TABLE runs (
    run_id               TEXT PRIMARY KEY,
    study_name           TEXT NOT NULL,
    config_hash          TEXT NOT NULL,
    input_snapshot_hash  TEXT NOT NULL,
    started_at           TEXT NOT NULL,
    completed_at         TEXT,
    results              TEXT                          -- JSON blob
);
