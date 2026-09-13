-- Quantitative labor-activity signals (NLRB election petitions, ULP charges).
-- Counts, not text — deliberately kept out of the articles table, which is
-- shaped for prose + sentiment, not time-series metrics. Feeds a labor-
-- market-tightness proxy alongside the FRED-derived reserve-army composite
-- in #3, and is the quantitative complement to #2's labor-press sentiment.

CREATE TABLE labor_activity_series (
    metric          TEXT NOT NULL,       -- 'nlrb_election_petitions', 'nlrb_ulp_charges'
    period_start    TEXT NOT NULL,
    period_end      TEXT NOT NULL,
    value           REAL NOT NULL,
    region          TEXT NOT NULL DEFAULT 'us',
    knowledge_time  TEXT NOT NULL,        -- NLRB data release date
    source          TEXT NOT NULL DEFAULT 'nlrb',
    PRIMARY KEY (metric, period_start, region)
);

CREATE INDEX idx_labor_activity_pit ON labor_activity_series(metric, knowledge_time);
