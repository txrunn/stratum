"""Partition events by a regime state, point-in-time safe.

An event is assigned the regime known *as of* its event_time — the most
recent regime observation dated at or before the event, never a later one.
This is the mechanical piece that lets a study config's
`conditioning_variables:` block (see ARCHITECTURE.md "Study configs") turn
into an actual partition of the events table.
"""

from __future__ import annotations

import pandas as pd

from stratum.quant.regime import INSUFFICIENT_HISTORY


def partition_events_by_regime(
    events: pd.DataFrame,
    regime_series: pd.Series,
    event_time_col: str = "event_time",
) -> dict[str, pd.DataFrame]:
    """Group `events` by the regime in effect at each row's `event_time_col`.

    Uses `pd.merge_asof(..., direction="backward")`: for each event, find the
    latest regime_series entry whose index is <= event_time. An event dated
    before the regime series' first observation has no defined regime and is
    grouped under `INSUFFICIENT_HISTORY` rather than silently dropped, so a
    caller can see how many events were excluded and why.
    """
    events = events.copy()
    events[event_time_col] = pd.to_datetime(events[event_time_col])
    events = events.sort_values(event_time_col)

    regime_df = regime_series.rename("regime").to_frame()
    regime_df.index = pd.to_datetime(regime_df.index)
    regime_df = regime_df.sort_index()

    merged = pd.merge_asof(
        events, regime_df, left_on=event_time_col, right_index=True, direction="backward"
    )
    merged["regime"] = merged["regime"].fillna(INSUFFICIENT_HISTORY)

    return {regime: group.drop(columns=["regime"]) for regime, group in merged.groupby("regime")}
