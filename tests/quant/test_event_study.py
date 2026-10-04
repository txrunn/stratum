from datetime import date

import numpy as np
from scipy import stats as scipy_stats

from stratum.quant.calendar import trading_day_offset
from stratum.quant.event_study import (
    BOOTSTRAP_SEED,
    check_pre_registration,
    detect_overlaps,
    pool_class,
)

# A known trading session to build event dates from. trading_day_offset's
# own validation (it raises on a non-session base) doubles as a check that
# this date really is one.
ANCHOR = trading_day_offset(date(2026, 1, 2), 0)


def test_detect_overlaps_flags_close_events_on_same_instrument():
    event1 = ANCHOR
    event2 = trading_day_offset(ANCHOR, 3)  # 3 sessions later
    window = (-1, 5)  # [t0-1, t0+5]: event1's window runs well past event2's t0
    flags = detect_overlaps({"NVDA": [event1, event2]}, window=window)
    assert flags["NVDA"] == [True, True]


def test_detect_overlaps_no_overlap_when_events_far_apart():
    event1 = ANCHOR
    event2 = trading_day_offset(ANCHOR, 60)
    window = (-1, 5)
    flags = detect_overlaps({"NVDA": [event1, event2]}, window=window)
    assert flags["NVDA"] == [False, False]


def test_detect_overlaps_is_per_instrument():
    # Same close dates on two different instruments must not cross-flag.
    event1 = ANCHOR
    event2 = trading_day_offset(ANCHOR, 3)
    window = (-1, 5)
    flags = detect_overlaps({"NVDA": [event1], "AMD": [event2]}, window=window)
    assert flags["NVDA"] == [False]
    assert flags["AMD"] == [False]


def test_pool_class_underpowered_below_min_events():
    scars = [0.5, -0.2, 0.3]
    result = pool_class("beat_and_fell", scars, min_events=20)
    assert result.underpowered is True
    assert result.n_events == 3
    assert result.t_statistic is None
    assert result.bootstrap_ci is None
    assert result.mean_scar == np.mean(scars)


def test_pool_class_computes_t_statistic_matching_scipy():
    rng = np.random.default_rng(7)
    scars = list(rng.normal(loc=0.4, scale=1.0, size=30))
    result = pool_class("beat_and_fell", scars, min_events=20)
    assert result.underpowered is False
    assert result.n_events == 30

    expected_t, _ = scipy_stats.ttest_1samp(scars, popmean=0.0)
    assert result.t_statistic == expected_t
    assert result.mean_scar == np.mean(scars)


def test_pool_class_bootstrap_ci_contains_mean_and_is_reproducible():
    rng = np.random.default_rng(11)
    scars = list(rng.normal(loc=0.1, scale=0.5, size=50))
    result1 = pool_class("beat_and_fell", scars, min_events=20)
    result2 = pool_class("beat_and_fell", scars, min_events=20)

    assert result1.bootstrap_ci is not None
    lower, upper = result1.bootstrap_ci
    assert lower <= result1.mean_scar <= upper
    # Fixed seed -> identical CI across repeated runs on the same input.
    assert result1.bootstrap_ci == result2.bootstrap_ci


def test_bootstrap_seed_is_fixed_module_constant():
    # Documents the reproducibility contract explicitly, rather than only
    # implying it via the identical-CI test above.
    assert isinstance(BOOTSTRAP_SEED, int)


def test_check_pre_registration_splits_declared_from_exploratory():
    declared = {"beat_and_fell", "beat_and_rose", "miss_and_fell", "miss_and_rose"}
    observed = {"beat_and_fell", "miss_and_rose", "unexpected_class"}
    pre_registered, exploratory = check_pre_registration(declared, observed)
    assert pre_registered == {"beat_and_fell", "miss_and_rose"}
    assert exploratory == {"unexpected_class"}
