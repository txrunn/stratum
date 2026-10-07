from pathlib import Path

import pytest

from stratum.store.connection import connect

FIXTURES = Path(__file__).parent / "fixtures" / "data" / "raw"


@pytest.fixture
def conn():
    connection = connect(":memory:")
    yield connection
    connection.close()


def insert_instrument_stub(conn, instrument_id: str, knowledge_time: str = "2026-01-01T00:00:00Z") -> None:
    """Minimal instruments row to satisfy bars/earnings/events FKs in tests.

    Real instrument resolution (RH symbol <-> IBKR contract_id <-> ISIN) is a
    separate, not-yet-built pipeline (see UNIVERSE.md "Fetch shape" on IBKR
    search_contracts). Until it exists, tests that only need a valid FK
    target use this instead of a full loader.
    """
    conn.execute(
        """
        INSERT OR IGNORE INTO instruments
            (instrument_id, symbol, rh_symbol, resolution_evidence, knowledge_time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (instrument_id, instrument_id, instrument_id, "test stub: unresolved", knowledge_time),
    )
    conn.commit()
