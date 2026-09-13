import statistics

from stratum.quant.composites.reserve_army import COMPONENTS, compute_composite
from tests.quant.conftest import insert_series, monthly_dates

ALL_SERIES = [c.series_id for c in COMPONENTS]


def _seed_all_series(conn, per_series_values: dict[str, list[float]], dates: list[str]) -> None:
    for series_id, values in per_series_values.items():
        insert_series(conn, series_id, list(zip(dates, values, strict=True)))


def test_compute_composite_returns_none_with_insufficient_history(conn):
    dates = monthly_dates("2020-01-01", 5)  # fewer than MIN_OBSERVATIONS=12
    _seed_all_series(conn, {sid: [5.0] * 5 for sid in ALL_SERIES}, dates)
    result = compute_composite(conn, as_of=dates[-1])
    assert result is None


def test_compute_composite_matches_manual_calculation(conn):
    dates = monthly_dates("2020-01-01", 13)  # 12 history points + 1 latest
    # Distinct, non-degenerate history per series so z-scores are nonzero.
    per_series_values = {
        "U6RATE": [7.0, 7.1, 7.2, 6.9, 7.0, 7.3, 7.1, 6.8, 7.0, 7.2, 7.1, 6.9, 8.5],
        "LNS11300060": [83.0, 83.1, 83.0, 82.9, 83.2, 83.1, 83.0, 82.8, 83.1, 83.2, 83.0, 82.9, 84.0],
        "JTSQUR": [2.3, 2.4, 2.2, 2.5, 2.3, 2.4, 2.6, 2.3, 2.4, 2.2, 2.5, 2.3, 3.0],
        "ECIWAG": [4.0, 4.1, 4.0, 3.9, 4.2, 4.1, 4.0, 3.8, 4.1, 4.2, 4.0, 3.9, 4.8],
        "OPHNFB": [110.0, 110.2, 110.1, 109.9, 110.3, 110.2, 110.0, 109.8, 110.2, 110.3, 110.1, 109.9, 112.0],
    }
    _seed_all_series(conn, per_series_values, dates)

    result = compute_composite(conn, as_of=dates[-1])
    assert result is not None

    expected_composite = 0.0
    for component in COMPONENTS:
        values = per_series_values[component.series_id]
        latest = values[-1]
        history = values[:-1]
        mean = statistics.mean(history)
        stdev = statistics.pstdev(history)
        z = (latest - mean) / stdev
        if not component.higher_is_tighter:
            z = -z
        assert result.component_z_scores[component.series_id] == z
        expected_composite += component.weight * z

    assert abs(result.value - expected_composite) < 1e-9
    assert result.as_of == dates[-1]
    assert result.version == "reserve_army_composite@v1"


def _mild_oscillation(base: float, amplitude: float, n: int) -> list[float]:
    # Small nonzero variance so a held-"flat" component's z-score is near
    # zero but not exactly zero (a truly constant history has stdev=0 and
    # the _z_score guard would return 0.0 regardless of the latest value,
    # which would isolate nothing).
    return [base + amplitude * (1 if i % 2 == 0 else -1) for i in range(n)]


def test_inverted_series_pulls_composite_down_when_it_rises(conn):
    # U6RATE (inverted, weight 0.25) spikes hard on the latest print; every
    # other series only mildly oscillates, so U6RATE's z-score dominates.
    dates = monthly_dates("2021-01-01", 13)
    per_series_values = {
        "U6RATE": _mild_oscillation(7.0, 0.05, 12) + [9.0],  # rising unemployment
        "LNS11300060": _mild_oscillation(83.0, 0.05, 13),
        "JTSQUR": _mild_oscillation(2.4, 0.02, 13),
        "ECIWAG": _mild_oscillation(4.0, 0.02, 13),
        "OPHNFB": _mild_oscillation(110.0, 0.05, 13),
    }
    _seed_all_series(conn, per_series_values, dates)

    result = compute_composite(conn, as_of=dates[-1])
    assert result is not None
    assert result.component_z_scores["U6RATE"] < 0  # inverted: rising slack -> negative z
    assert result.value < 0  # composite reads looser, not tighter


def test_upright_series_pushes_composite_up_when_it_rises(conn):
    # JTSQUR (upright, weight 0.30) spikes hard; everything else mildly
    # oscillates.
    dates = monthly_dates("2021-01-01", 13)
    per_series_values = {
        "U6RATE": _mild_oscillation(7.0, 0.05, 13),
        "LNS11300060": _mild_oscillation(83.0, 0.05, 13),
        "JTSQUR": _mild_oscillation(2.4, 0.02, 12) + [4.0],  # quits surge
        "ECIWAG": _mild_oscillation(4.0, 0.02, 13),
        "OPHNFB": _mild_oscillation(110.0, 0.05, 13),
    }
    _seed_all_series(conn, per_series_values, dates)

    result = compute_composite(conn, as_of=dates[-1])
    assert result is not None
    assert result.component_z_scores["JTSQUR"] > 0
    assert result.value > 0


def test_compute_composite_respects_pit_lookback_window(conn):
    # 11+ years of monthly history with one wildly different point at the
    # very start (2010-01), far outside the trailing-10y window as of the
    # last date. If the lookback_start filter didn't work, that outlier
    # would drag the mean/stdev and change the z-score.
    dates = monthly_dates("2010-01-01", 132)  # 2010-01 .. 2020-12
    values = [50.0] + [7.0 + 0.05 * (i % 5) for i in range(1, 132)]
    per_series_values = {sid: values for sid in ALL_SERIES}
    _seed_all_series(conn, per_series_values, dates)

    as_of = dates[-1]  # 2020-12-01
    result = compute_composite(conn, as_of=as_of)
    assert result is not None

    from stratum.quant.composites.reserve_army import _lookback_start

    cutoff = _lookback_start(as_of)
    assert dates[0] < cutoff  # confirm the outlier date is indeed excluded

    windowed_values = [v for d, v in zip(dates, values, strict=True) if d >= cutoff]
    history = windowed_values[:-1]
    latest = windowed_values[-1]
    mean = statistics.mean(history)
    stdev = statistics.pstdev(history)
    expected_z = -((latest - mean) / stdev)  # U6RATE is inverted

    # Sanity check: had the outlier leaked in, mean/stdev would differ enough
    # to change the z-score materially. This asserts the windowed value,
    # which is what compute_composite should actually produce.
    assert abs(result.component_z_scores["U6RATE"] - expected_z) < 1e-9

    full_history = values[:-1]
    full_mean = statistics.mean(full_history)
    full_stdev = statistics.pstdev(full_history)
    leaked_z = -((latest - full_mean) / full_stdev)
    assert abs(result.component_z_scores["U6RATE"] - leaked_z) > 1e-6
