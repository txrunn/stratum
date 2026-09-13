import pytest

from stratum.store.connection import connect


@pytest.fixture
def conn():
    connection = connect(":memory:")
    yield connection
    connection.close()


def insert_series(conn, series_id: str, dated_values: list[tuple[str, float]]) -> None:
    """Insert single-vintage macro_series rows (vintage_date == observation_date).

    Fine for quant-layer tests: PIT revision semantics are covered in
    tests/store/test_loader_macro_series.py. Here we only need a controlled,
    known-history series to check composite/regime arithmetic.
    """
    rows = [
        (series_id, obs_date, obs_date, value, "fred_alfred") for obs_date, value in dated_values
    ]
    conn.executemany(
        """
        INSERT INTO macro_series (series_id, observation_date, vintage_date, value, source)
        VALUES (?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()


def monthly_dates(start: str, count: int) -> list[str]:
    """count monthly-ish dates starting at start, as YYYY-MM-01 strings."""
    from datetime import date

    y, m, _ = (int(p) for p in start.split("-"))
    out = []
    for i in range(count):
        total = (m - 1) + i
        yy = y + total // 12
        mm = total % 12 + 1
        out.append(date(yy, mm, 1).isoformat())
    return out
