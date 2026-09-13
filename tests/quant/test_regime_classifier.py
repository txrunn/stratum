import pandas as pd

from stratum.quant.regime import (
    INSUFFICIENT_HISTORY,
    MIN_PERIODS_FOR_REGIME,
    NORMAL,
    SLACK_RESERVE,
    THIN_RESERVE,
    classify_regime_series,
)


def _series(values: list[float], start: str = "2015-01-01") -> pd.Series:
    index = pd.date_range(start=start, periods=len(values), freq="MS")
    return pd.Series(values, index=index)


def test_classify_regime_insufficient_history_before_min_periods():
    # Fewer points than MIN_PERIODS_FOR_REGIME anywhere in the series.
    values = [0.0] * (MIN_PERIODS_FOR_REGIME - 1)
    result = classify_regime_series(_series(values), window=40)
    assert (result == INSUFFICIENT_HISTORY).all()


def test_classify_regime_flat_series_ties_resolve_to_thin_reserve():
    # A perfectly flat series: every point ties for percentile rank 1.0
    # (current <= current is trivially true, and so is every prior point
    # since they're all equal) -> rank is always 1.0 -> classified thin.
    # This documents the tie-handling behavior of a degenerate, zero-
    # variance input rather than claiming it's a meaningful "thin" regime.
    values = [5.0] * 50
    result = classify_regime_series(_series(values), window=40)
    determined = result[result != INSUFFICIENT_HISTORY]
    assert len(determined) > 0
    assert (determined == THIN_RESERVE).all()


def test_classify_regime_detects_thin_reserve_spike():
    # 40 points flat, then a clear upward spike -> the spike point should
    # rank at or near the top of its trailing window -> thin_reserve.
    values = [0.0] * 45 + [10.0]
    result = classify_regime_series(_series(values), window=40)
    assert result.iloc[-1] == THIN_RESERVE


def test_classify_regime_detects_slack_reserve_dip():
    values = [0.0] * 45 + [-10.0]
    result = classify_regime_series(_series(values), window=40)
    assert result.iloc[-1] == SLACK_RESERVE


def test_classify_regime_middling_value_is_normal():
    # A window with clear variation where the latest point sits in the
    # middle of the pack, not at either tail.
    values = list(range(40)) + [20]  # latest (20) sits mid-pack among 0..39
    result = classify_regime_series(_series(values), window=40)
    assert result.iloc[-1] == NORMAL


def test_classify_regime_is_backward_looking_only():
    # A future spike must not affect the regime label of an earlier point.
    # Two series identical up to index 45; only the second has a future
    # spike appended. The label at index 44 must be identical in both.
    base = [float(i % 7) for i in range(46)]
    spiked = base + [1000.0]

    result_base = classify_regime_series(_series(base), window=40)
    result_spiked = classify_regime_series(_series(spiked), window=40)

    assert result_base.iloc[44] == result_spiked.iloc[44]
