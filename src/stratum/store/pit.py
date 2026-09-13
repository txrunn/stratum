"""Point-in-time query helpers.

Every table carries knowledge_time. These helpers make "what did we know as
of date X" mechanical rather than a matter of writing the filter correctly
every time a study touches the store (see ARCHITECTURE.md "store/").
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class MacroObservation:
    series_id: str
    observation_date: str
    vintage_date: str
    value: float | None


def latest_macro_value(
    conn: sqlite3.Connection, series_id: str, as_of: str
) -> MacroObservation | None:
    """The most recent economic observation of `series_id` knowable as of `as_of`.

    ALFRED semantics: among rows with vintage_date <= as_of, take the one
    with the latest observation_date (most recent data point the world had
    produced), and among ties on observation_date take the latest vintage
    (the freshest revision of that data point known by `as_of`).
    """
    row = conn.execute(
        """
        SELECT series_id, observation_date, vintage_date, value
        FROM macro_series
        WHERE series_id = ? AND vintage_date <= ?
        ORDER BY observation_date DESC, vintage_date DESC
        LIMIT 1
        """,
        (series_id, as_of),
    ).fetchone()
    if row is None:
        return None
    return MacroObservation(
        series_id=row["series_id"],
        observation_date=row["observation_date"],
        vintage_date=row["vintage_date"],
        value=row["value"],
    )


def macro_series_asof(
    conn: sqlite3.Connection,
    series_id: str,
    as_of: str,
    lookback_periods: int | None = None,
    lookback_start: str | None = None,
) -> list[MacroObservation]:
    """The full point-in-time time series of `series_id` knowable as of `as_of`.

    For each distinct observation_date <= as_of (by knowledge), returns the
    latest vintage of that observation known at `as_of`. This is the series
    a composite calculation would have seen had it been computed on `as_of`,
    not the revised series we'd see querying FRED today.

    `lookback_start` bounds by calendar date (e.g. "10 years before as_of") —
    the right choice when combining series of different frequencies (JOLTS
    is monthly, ECI is quarterly), since a fixed observation *count* would
    cover a different span for each. `lookback_periods`, if also given, caps
    the count after the date filter — apply one, both, or neither.
    """
    query = """
        SELECT series_id, observation_date, vintage_date, value
        FROM macro_series m
        WHERE series_id = ?
          AND vintage_date <= ?
          AND vintage_date = (
              SELECT MAX(vintage_date)
              FROM macro_series m2
              WHERE m2.series_id = m.series_id
                AND m2.observation_date = m.observation_date
                AND m2.vintage_date <= ?
          )
        ORDER BY observation_date ASC
    """
    rows = conn.execute(query, (series_id, as_of, as_of)).fetchall()
    obs = [
        MacroObservation(
            series_id=row["series_id"],
            observation_date=row["observation_date"],
            vintage_date=row["vintage_date"],
            value=row["value"],
        )
        for row in rows
    ]
    if lookback_start is not None:
        obs = [o for o in obs if o.observation_date >= lookback_start]
    if lookback_periods is not None:
        obs = obs[-lookback_periods:]
    return obs


def articles_asof(
    conn: sqlite3.Connection,
    as_of_start: str,
    as_of_end: str,
    outlet_class: str | None = None,
    source_in: list[str] | None = None,
) -> list[sqlite3.Row]:
    """Articles whose knowledge_time falls in [as_of_start, as_of_end].

    Filtering on knowledge_time (fetch time), not published_at, is what
    makes this point-in-time safe: an article backdated or slow to index
    cannot leak into a study that runs before we actually had it.
    """
    clauses = ["knowledge_time >= ?", "knowledge_time <= ?"]
    params: list[str] = [as_of_start, as_of_end]
    if outlet_class is not None:
        clauses.append("outlet_class = ?")
        params.append(outlet_class)
    if source_in:
        placeholders = ",".join("?" for _ in source_in)
        clauses.append(f"source IN ({placeholders})")
        params.extend(source_in)
    query = f"SELECT * FROM articles WHERE {' AND '.join(clauses)} ORDER BY published_at ASC"
    return conn.execute(query, params).fetchall()
