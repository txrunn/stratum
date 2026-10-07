from stratum.store.loaders.bars import load_bars
from tests.store.conftest import FIXTURES, insert_instrument_stub

BATCH_1_FIXTURE = FIXTURES / "robinhood" / "get_equity_historicals" / "batch_1.json"


def _seed_instruments(conn) -> None:
    insert_instrument_stub(conn, "NVDA")
    insert_instrument_stub(conn, "AMD")


def test_load_bars_row_count_drops_interpolated(conn):
    _seed_instruments(conn)
    inserted = load_bars(conn, BATCH_1_FIXTURE)
    # NVDA: 3 bars in the fixture, 1 interpolated -> 2 real. AMD: 2 bars, 0 interpolated.
    assert inserted == 4

    row_count = conn.execute("SELECT COUNT(*) AS n FROM bars").fetchone()["n"]
    assert row_count == 4


def test_load_bars_parses_ohlcv(conn):
    _seed_instruments(conn)
    load_bars(conn, BATCH_1_FIXTURE)
    row = conn.execute(
        "SELECT * FROM bars WHERE instrument_id = 'NVDA' AND date = '2026-09-03'"
    ).fetchone()
    assert row["open"] == 171.90
    assert row["high"] == 174.00
    assert row["low"] == 171.20
    assert row["close"] == 173.50
    assert row["volume"] == 165432100
    assert row["adjustment_type"] == "split"
    assert row["knowledge_time"] == "2026-09-05T21:05:00Z"


def test_load_bars_excludes_interpolated_date(conn):
    _seed_instruments(conn)
    load_bars(conn, BATCH_1_FIXTURE)
    row = conn.execute(
        "SELECT * FROM bars WHERE instrument_id = 'NVDA' AND date = '2026-09-04'"
    ).fetchone()
    assert row is None


def test_load_bars_is_idempotent(conn):
    _seed_instruments(conn)
    load_bars(conn, BATCH_1_FIXTURE)
    load_bars(conn, BATCH_1_FIXTURE)
    row_count = conn.execute("SELECT COUNT(*) AS n FROM bars").fetchone()["n"]
    assert row_count == 4


def test_load_bars_requires_instrument_fk(conn):
    # No instruments row seeded for AMD or NVDA: FK enforcement should reject the insert.
    import sqlite3

    try:
        load_bars(conn, BATCH_1_FIXTURE)
        raised = False
    except sqlite3.IntegrityError:
        raised = True
    assert raised
