"""Load normalized RSS-feed JSON into articles.

Raw file shape (data/raw/rss/feeds/{source_id}/{fetch_date}.json), produced
by the agent's RSS ingester per news_capital_press.yaml / news_labor_press.yaml
/ think_tanks.yaml specs:

    {
      "source_id": "wsj_markets",
      "outlet_class": "capital",
      "fetched_at": "2026-09-04T18:40:00Z",
      "entries": [
        {"title": "...", "link": "https://...", "published": "2026-09-04T18:32:00Z",
         "summary": "..."},
        ...
      ]
    }

knowledge_time = fetched_at (when we could first have known the article
existed), never `published`, which the source controls and could in
principle misstate or backdate.

article_id is a stable hash of (source_id, url, body_hash) so re-ingesting
the same feed is idempotent rather than creating duplicate rows.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


def _article_id(source_id: str, url: str, body_hash: str) -> str:
    return hashlib.sha256(f"{source_id}|{url}|{body_hash}".encode()).hexdigest()


def _body_hash(title: str, summary: str | None) -> str:
    return hashlib.sha256(f"{title}|{summary or ''}".encode()).hexdigest()


def load_articles(conn: sqlite3.Connection, raw_path: Path) -> int:
    """Load one feed-fetch file. Returns rows inserted."""
    payload = json.loads(raw_path.read_text())
    source_id = payload["source_id"]
    outlet_class = payload["outlet_class"]
    knowledge_time = payload["fetched_at"]

    rows = []
    for entry in payload["entries"]:
        title = entry["title"]
        url = entry["link"]
        summary = entry.get("summary")
        body_hash = _body_hash(title, summary)
        article_id = _article_id(source_id, url, body_hash)
        rows.append(
            (
                article_id,
                source_id,
                title,
                url,
                entry["published"],
                knowledge_time,
                body_hash,
                outlet_class,
            )
        )

    conn.executemany(
        """
        INSERT OR REPLACE INTO articles
            (article_id, source, title, url, published_at, knowledge_time, body_hash, outlet_class)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)
