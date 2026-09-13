"""Load ALFRED (output_type=4, all-vintages) JSON into macro_series.

Raw file shape (data/raw/fred_alfred/series_observations/{series_id}.json),
matching the real ALFRED API response for series/observations with
output_type=4:

    {
      "series_id": "U6RATE",             # optional; falls back to filename stem
      "observations": [
        {"date": "2014-12-01", "realtime_start": "2015-01-02",
         "realtime_end": "2015-02-05", "value": "5.6"},
        ...
      ]
    }

vintage_date = realtime_start, which is exactly knowledge_time: the first
day this observation's value was the officially published one. A value of
"." (ALFRED's missing-data sentinel) is stored as NULL.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def load_macro_series(conn: sqlite3.Connection, raw_path: Path) -> int:
    """Load one series' ALFRED observations file. Returns rows inserted."""
    payload = json.loads(raw_path.read_text())
    series_id = payload.get("series_id") or raw_path.stem

    rows = []
    for obs in payload["observations"]:
        raw_value = obs.get("value")
        value = None if raw_value in (None, ".", "") else float(raw_value)
        rows.append(
            (
                series_id,
                obs["date"],
                obs["realtime_start"],
                value,
                "fred_alfred",
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO macro_series
            (series_id, observation_date, vintage_date, value, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
