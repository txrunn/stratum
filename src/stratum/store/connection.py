"""SQLite connection + migration runner.

SQLite is the right call for stratum: single user, single writer, no
concurrency, and the entire database is a file you can copy to pin a
snapshot (see ARCHITECTURE.md).

Migrations are plain .sql files in store/schema/, applied in filename order,
each inside its own transaction. A schema_versions table (bootstrapped here,
not from a numbered file, to avoid a chicken-and-egg problem) tracks which
migrations have run and the SHA256 of the file that was applied, so a
modified migration file is caught rather than silently skipped.
"""

from __future__ import annotations

import hashlib
import sqlite3
from importlib import resources
from pathlib import Path

_SCHEMA_PACKAGE = "stratum.store.schema"


class MigrationError(RuntimeError):
    """Raised when a migration file has changed after being applied, or fails to apply."""


def _schema_files() -> list[tuple[str, str]]:
    """Return (filename, sql_text) for every migration, sorted by filename."""
    files = []
    schema_dir = resources.files(_SCHEMA_PACKAGE)
    for entry in schema_dir.iterdir():
        if entry.name.endswith(".sql"):
            files.append((entry.name, entry.read_text()))
    files.sort(key=lambda pair: pair[0])
    return files


def connect(db_path: str | Path = ":memory:") -> sqlite3.Connection:
    """Open a connection and apply any pending migrations."""
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    """Apply all pending migrations in filename order. Idempotent."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_versions (
            filename    TEXT PRIMARY KEY,
            sha256      TEXT NOT NULL,
            applied_at  TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()

    applied = {
        row["filename"]: row["sha256"]
        for row in conn.execute("SELECT filename, sha256 FROM schema_versions")
    }

    for filename, sql_text in _schema_files():
        digest = hashlib.sha256(sql_text.encode("utf-8")).hexdigest()
        if filename in applied:
            if applied[filename] != digest:
                raise MigrationError(
                    f"{filename} has changed since it was applied "
                    f"(recorded sha256={applied[filename][:12]}…, "
                    f"current sha256={digest[:12]}…). Migrations are append-only: "
                    "add a new file rather than editing an applied one."
                )
            continue
        try:
            conn.executescript(sql_text)
        except sqlite3.Error as exc:
            conn.rollback()
            raise MigrationError(f"failed applying {filename}: {exc}") from exc
        conn.execute(
            "INSERT INTO schema_versions (filename, sha256) VALUES (?, ?)",
            (filename, digest),
        )
        conn.commit()
