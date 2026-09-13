"""Migrations apply cleanly, are idempotent, and detect tampering."""

import sqlite3

import pytest

from stratum.store.connection import MigrationError, connect, migrate


def test_migrate_creates_expected_tables(conn):
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    expected = {
        "schema_versions",
        "instruments",
        "bars",
        "earnings",
        "events",
        "themes",
        "theme_membership",
        "competitor_edges",
        "labels",
        "positions",
        "runs",
        "macro_series",
        "articles",
        "article_labels",
        "labor_activity_series",
    }
    assert expected.issubset(tables)


def test_migrate_is_idempotent(conn):
    # Running migrate() again on an already-migrated connection is a no-op,
    # not an error and not a duplicate application.
    before = conn.execute("SELECT COUNT(*) AS n FROM schema_versions").fetchone()["n"]
    migrate(conn)
    after = conn.execute("SELECT COUNT(*) AS n FROM schema_versions").fetchone()["n"]
    assert before == after


def test_migrate_detects_tampering(conn, monkeypatch):
    # Simulate a migration file changing after being applied: overwrite the
    # recorded hash so it no longer matches what _schema_files() would compute.
    conn.execute(
        "UPDATE schema_versions SET sha256 = 'deadbeef' WHERE filename = '001_core.sql'"
    )
    conn.commit()
    with pytest.raises(MigrationError, match="has changed since it was applied"):
        migrate(conn)


def test_connect_on_file_path(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    tables = {
        row["name"]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    assert "macro_series" in tables
    conn.close()

    # Re-opening the same file re-applies migrate() but should be a no-op.
    conn2 = sqlite3.connect(db_path)
    conn2.row_factory = sqlite3.Row
    migrate(conn2)
    conn2.close()
