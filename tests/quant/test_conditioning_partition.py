import pandas as pd

from stratum.quant.conditioning import partition_events_by_regime
from stratum.quant.regime import INSUFFICIENT_HISTORY


def _regime_series() -> pd.Series:
    # Regime known at three dates: thin from 2020-01-01, normal from
    # 2020-04-01, slack from 2020-07-01.
    index = pd.to_datetime(["2020-01-01", "2020-04-01", "2020-07-01"])
    return pd.Series(["thin_reserve", "normal", "slack_reserve"], index=index)


def test_partition_events_by_regime_uses_backward_asof():
    events = pd.DataFrame(
        {
            "event_id": ["e1", "e2", "e3", "e4"],
            "event_time": [
                "2020-02-15",  # after thin (01-01), before normal (04-01) -> thin
                "2020-05-01",  # after normal (04-01), before slack (07-01) -> normal
                "2020-08-01",  # after slack (07-01) -> slack
                "2020-07-01",  # exactly on the slack transition date -> slack
            ],
        }
    )
    grouped = partition_events_by_regime(events, _regime_series())

    assert set(grouped["thin_reserve"]["event_id"]) == {"e1"}
    assert set(grouped["normal"]["event_id"]) == {"e2"}
    assert set(grouped["slack_reserve"]["event_id"]) == {"e3", "e4"}


def test_partition_events_by_regime_before_first_observation_is_insufficient_history():
    events = pd.DataFrame(
        {
            "event_id": ["early"],
            "event_time": ["2019-01-01"],  # before the regime series' first entry
        }
    )
    grouped = partition_events_by_regime(events, _regime_series())
    assert INSUFFICIENT_HISTORY in grouped
    assert list(grouped[INSUFFICIENT_HISTORY]["event_id"]) == ["early"]


def test_partition_events_by_regime_preserves_other_columns():
    events = pd.DataFrame(
        {
            "event_id": ["e1"],
            "event_time": ["2020-02-15"],
            "instrument_id": ["NVDA"],
        }
    )
    grouped = partition_events_by_regime(events, _regime_series())
    row = grouped["thin_reserve"].iloc[0]
    assert row["instrument_id"] == "NVDA"
    assert "regime" not in grouped["thin_reserve"].columns
