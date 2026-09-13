"""Load NLRB activity data into labor_activity_series.

Raw file shape (data/raw/nlrb/{metric}/{fetch_date}.json):

    {
      "metric": "nlrb_election_petitions",
      "region": "us",
      "release_date": "2026-08-15",
      "observations": [
        {"period_start": "2026-06-01", "period_end": "2026-06-30", "value": 412},
        ...
      ]
    }

knowledge_time = release_date — the date NLRB published that period's count,
not the period itself. NLRB reporting lags several weeks behind period_end,
so using period_end as knowledge_time would leak information a study
couldn't actually have had at that date.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def load_labor_activity(conn: sqlite3.Connection, raw_path: Path) -> int:
    """Load one metric's NLRB release file. Returns rows inserted."""
    payload = json.loads(raw_path.read_text())
    metric = payload["metric"]
    region = payload.get("region", "us")
    knowledge_time = payload["release_date"]

    rows = [
        (
            metric,
            obs["period_start"],
            obs["period_end"],
            float(obs["value"]),
            region,
            knowledge_time,
            "nlrb",
        )
        for obs in payload["observations"]
    ]

    conn.executemany(
        """
        INSERT OR REPLACE INTO labor_activity_series
            (metric, period_start, period_end, value, region, knowledge_time, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
