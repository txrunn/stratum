"""Composite value -> categorical regime, and the composite time series that
feeds it.

Kept separate from composites/reserve_army.py so the regime boundary
(deciles, window length) can be retuned independently of the composite
formula itself — each half is independently versioned and independently
testable.
"""

from __future__ import annotations

import pandas as pd

from stratum.quant.composites.reserve_army import compute_composite

REGIME_VERSION = "reserve_army_regime@v1"

ROLLING_WINDOW_PERIODS = 40  # ~10y of quarterly-or-denser composite points
MIN_PERIODS_FOR_REGIME = 12  # below this, regime is undetermined, not "normal"

THIN_QUANTILE = 0.90
SLACK_QUANTILE = 0.10

INSUFFICIENT_HISTORY = "insufficient_history"
THIN_RESERVE = "thin_reserve"
SLACK_RESERVE = "slack_reserve"
NORMAL = "normal"


def build_composite_series(conn, as_of_dates: list[str]) -> pd.Series:
    """The reserve-army composite evaluated at each of `as_of_dates`.

    `as_of_dates` should be ascending. Dates where compute_composite returns
    None (insufficient component history) are omitted, not filled with NaN —
    a caller iterating this series never sees a phantom zero.
    """
    values: dict[str, float] = {}
    for as_of in as_of_dates:
        result = compute_composite(conn, as_of)
        if result is not None:
            values[as_of] = result.value
    series = pd.Series(values, dtype=float)
    series.index = pd.to_datetime(series.index)
    return series.sort_index()


def _percentile_rank_of_last(window: pd.Series) -> float:
    if len(window) < MIN_PERIODS_FOR_REGIME:
        return float("nan")
    current = window.iloc[-1]
    return float((window <= current).mean())


def classify_regime_series(
    composite_series: pd.Series, window: int = ROLLING_WINDOW_PERIODS
) -> pd.Series:
    """Bucket each point into thin/normal/slack by its percentile rank within
    the trailing `window` (itself included). Backward-looking only — pandas
    `.rolling()` never includes future points, so this is look-ahead-free by
    construction, not by discipline.
    """
    ranks = composite_series.rolling(window=window, min_periods=MIN_PERIODS_FOR_REGIME).apply(
        _percentile_rank_of_last, raw=False
    )

    def _bucket(rank: float) -> str:
        if pd.isna(rank):
            return INSUFFICIENT_HISTORY
        if rank >= THIN_QUANTILE:
            return THIN_RESERVE
        if rank <= SLACK_QUANTILE:
            return SLACK_RESERVE
        return NORMAL

    return ranks.apply(_bucket)
