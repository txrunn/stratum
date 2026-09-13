-- FRED/ALFRED macro series. Vintage-aware by construction: vintage_date IS
-- knowledge_time, taken from ALFRED's realtime_start. A series observation
-- can appear multiple times at different vintages as BLS/BEA revise it;
-- point-in-time queries (see store/pit.py) filter on vintage_date <= as_of
-- and take the latest observation_date known at that vintage.
--
-- Used by: #3 (reserve-army composite), #4 (overaccumulation composite).

CREATE TABLE macro_series (
    series_id         TEXT NOT NULL,
    observation_date  TEXT NOT NULL,
    vintage_date      TEXT NOT NULL,     -- == knowledge_time
    value             REAL,
    source            TEXT NOT NULL DEFAULT 'fred_alfred',
    PRIMARY KEY (series_id, observation_date, vintage_date)
);

CREATE INDEX idx_macro_series_pit ON macro_series(series_id, vintage_date, observation_date);
