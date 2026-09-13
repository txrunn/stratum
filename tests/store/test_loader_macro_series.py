from stratum.store.loaders.macro_series import load_macro_series
from stratum.store.pit import latest_macro_value, macro_series_asof
from tests.store.conftest import FIXTURES

U6RATE_FIXTURE = FIXTURES / "fred_alfred" / "series_observations" / "U6RATE.json"


def test_load_macro_series_row_count(conn):
    inserted = load_macro_series(conn, U6RATE_FIXTURE)
    assert inserted == 6

    row_count = conn.execute("SELECT COUNT(*) AS n FROM macro_series").fetchone()["n"]
    assert row_count == 6


def test_load_macro_series_parses_missing_sentinel_as_null(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    row = conn.execute(
        "SELECT value FROM macro_series WHERE observation_date = '2024-04-01'"
    ).fetchone()
    assert row["value"] is None


def test_load_macro_series_is_idempotent(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    load_macro_series(conn, U6RATE_FIXTURE)
    row_count = conn.execute("SELECT COUNT(*) AS n FROM macro_series").fetchone()["n"]
    assert row_count == 6


def test_latest_macro_value_before_first_revision(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    # As of 2024-02-15, only the first vintage of the Jan observation existed.
    obs = latest_macro_value(conn, "U6RATE", as_of="2024-02-15")
    assert obs is not None
    assert obs.observation_date == "2024-01-01"
    assert obs.value == 7.2


def test_latest_macro_value_after_revision_uses_revised_value(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    # By 2024-03-06, the Jan value has been revised to 7.1, and Feb hasn't
    # published its first vintage yet (that lands 2024-03-08).
    obs = latest_macro_value(conn, "U6RATE", as_of="2024-03-06")
    assert obs is not None
    assert obs.observation_date == "2024-01-01"
    assert obs.value == 7.1


def test_latest_macro_value_advances_to_new_observation_date(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    obs = latest_macro_value(conn, "U6RATE", as_of="2024-03-10")
    assert obs is not None
    assert obs.observation_date == "2024-02-01"
    assert obs.value == 7.3


def test_latest_macro_value_none_before_any_vintage(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    obs = latest_macro_value(conn, "U6RATE", as_of="2024-01-01")
    assert obs is None


def test_macro_series_asof_reconstructs_pit_series(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    # As of 2024-04-10: Jan is at its revised 7.1 vintage, Feb is at its
    # revised 7.2 vintage (2024-04-05), Mar's only vintage (7.0) has landed.
    # Apr hasn't published yet (lands 2024-05-03), so it's absent.
    series = macro_series_asof(conn, "U6RATE", as_of="2024-04-10")
    by_date = {obs.observation_date: obs.value for obs in series}
    assert by_date == {
        "2024-01-01": 7.1,
        "2024-02-01": 7.2,
        "2024-03-01": 7.0,
    }
    assert "2024-04-01" not in by_date


def test_macro_series_asof_respects_lookback(conn):
    load_macro_series(conn, U6RATE_FIXTURE)
    series = macro_series_asof(conn, "U6RATE", as_of="2024-04-10", lookback_periods=2)
    assert len(series) == 2
    assert series[-1].observation_date == "2024-03-01"
