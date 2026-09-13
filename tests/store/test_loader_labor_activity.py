from stratum.store.loaders.labor_activity import load_labor_activity
from tests.store.conftest import FIXTURES

NLRB_FIXTURE = FIXTURES / "nlrb" / "nlrb_election_petitions" / "2026-08-15.json"


def test_load_labor_activity_row_count(conn):
    inserted = load_labor_activity(conn, NLRB_FIXTURE)
    assert inserted == 2
    row_count = conn.execute(
        "SELECT COUNT(*) AS n FROM labor_activity_series"
    ).fetchone()["n"]
    assert row_count == 2


def test_load_labor_activity_knowledge_time_is_release_date_not_period_end(conn):
    load_labor_activity(conn, NLRB_FIXTURE)
    row = conn.execute(
        """
        SELECT knowledge_time, period_end FROM labor_activity_series
        WHERE period_start = '2026-06-01'
        """
    ).fetchone()
    # Release date (2026-08-15) is well after period_end (2026-06-30) — NLRB
    # reporting lag. A study using period_end as knowledge_time would leak
    # ~6 weeks of look-ahead.
    assert row["knowledge_time"] == "2026-08-15"
    assert row["period_end"] == "2026-06-30"
    assert row["knowledge_time"] > row["period_end"]


def test_load_labor_activity_is_idempotent(conn):
    load_labor_activity(conn, NLRB_FIXTURE)
    load_labor_activity(conn, NLRB_FIXTURE)
    row_count = conn.execute(
        "SELECT COUNT(*) AS n FROM labor_activity_series"
    ).fetchone()["n"]
    assert row_count == 2
