"""Load batched Robinhood get_equity_historicals JSON into bars.

Raw file shape (data/raw/robinhood/get_equity_historicals/{batch_label}.json),
one file per 10-symbol batch call (see ingest/specs/equity_bars.yaml):

    {
      "fetched_at": "2026-09-04T21:05:00Z",
      "adjustment_type": "split",
      "results": [
        {"symbol": "NVDA", "bars": [
            {"begins_at": "2026-09-03T00:00:00Z", "open_price": "...",
             "high_price": "...", "low_price": "...", "close_price": "...",
             "volume": 123456789, "interpolated": false},
            ...
        ]},
        ...
      ]
    }

knowledge_time = fetched_at, for every bar in the file. Bars are not
revised the way macro data is, so a single fetch-time stamp (rather than
ALFRED-style vintages) is sufficient to keep queries point-in-time safe.

Interpolated bars (gap-fill synthesized by the API, per its own docs) carry
no new information and are dropped rather than loaded as if real.

date is stored as the calendar date (YYYY-MM-DD) portion of begins_at: bars
are daily, and date is what PIT joins against event calendars key on.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def load_bars(conn: sqlite3.Connection, raw_path: Path) -> int:
    """Load one batch-call file. Returns rows inserted."""
    payload = json.loads(raw_path.read_text())
    knowledge_time = payload["fetched_at"]
    adjustment_type = payload.get("adjustment_type", "split")

    rows = []
    for result in payload["results"]:
        symbol = result["symbol"]
        for bar in result["bars"]:
            if bar.get("interpolated"):
                continue
            rows.append(
                (
                    symbol,
                    bar["begins_at"][:10],
                    _maybe_float(bar.get("open_price")),
                    _maybe_float(bar.get("high_price")),
                    _maybe_float(bar.get("low_price")),
                    _maybe_float(bar.get("close_price")),
                    bar.get("volume"),
                    adjustment_type,
                    knowledge_time,
                )
            )

    conn.executemany(
        """
        INSERT OR REPLACE INTO bars
            (instrument_id, date, open, high, low, close, volume, adjustment_type, knowledge_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)


def _maybe_float(raw_value: str | float | None) -> float | None:
    return None if raw_value is None else float(raw_value)
