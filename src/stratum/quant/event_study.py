"""Event-study pooling: the three hygiene rules from ARCHITECTURE.md "quant/".

1. Overlap guard   — events whose windows intersect another event on the
                      same instrument are flagged and excluded by default.
2. Minimum N       — a class below the configured floor reports as
                      underpowered rather than producing a p-value.
3. Pre-registration — event classes are declared in the study config
                      *before* the run; classes added after seeing results
                      are exploratory and reported separately.

That third rule exists because with ~170 events and a dozen candidate
classes you will find significance by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
from scipy import stats as scipy_stats

from stratum.quant.calendar import trading_day_offset

DEFAULT_MIN_EVENTS_PER_CLASS = 20
BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20260101  # fixed: a study's bootstrap CI is reproducible, like its config hash


def detect_overlaps(
    event_t0_by_instrument: dict[str, list[date]], window: tuple[int, int]
) -> dict[str, list[bool]]:
    """Flags, per instrument, which events have a window overlapping another
    event's window on the *same* instrument (hygiene rule #1).

    `window` is (pre, post) trading-day offsets from each event's own t=0,
    e.g. (-1, 5). Overlap is a plain interval intersection test on the
    resulting [t0+pre, t0+post] session-date ranges.
    """
    pre, post = window
    flags: dict[str, list[bool]] = {}
    for instrument_id, t0_dates in event_t0_by_instrument.items():
        windows = [(trading_day_offset(t0, pre), trading_day_offset(t0, post)) for t0 in t0_dates]
        overlap_flags = [False] * len(windows)
        for i, (a_start, a_end) in enumerate(windows):
            for j, (b_start, b_end) in enumerate(windows):
                if i != j and a_start <= b_end and b_start <= a_end:
                    overlap_flags[i] = True
                    break
        flags[instrument_id] = overlap_flags
    return flags


@dataclass(frozen=True)
class PooledResult:
    class_name: str
    n_events: int
    mean_scar: float
    t_statistic: float | None
    bootstrap_ci: tuple[float, float] | None
    underpowered: bool


def pool_class(
    class_name: str, scars: list[float], min_events: int = DEFAULT_MIN_EVENTS_PER_CLASS
) -> PooledResult:
    """Mean SCAR, cross-sectional t-statistic, and a percentile bootstrap CI
    for one pre-registered event class (hygiene rule #2). Below
    `min_events`, reports `underpowered=True` with no t-statistic and no
    CI — a p-value computed on too little data is worse than admitting the
    class can't support inference yet.
    """
    n = len(scars)
    if n < min_events:
        return PooledResult(
            class_name=class_name,
            n_events=n,
            mean_scar=float(np.mean(scars)) if n > 0 else float("nan"),
            t_statistic=None,
            bootstrap_ci=None,
            underpowered=True,
        )

    arr = np.array(scars, dtype=float)
    mean_scar = float(arr.mean())
    t_stat, _ = scipy_stats.ttest_1samp(arr, popmean=0.0)

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    boot_means = np.array(
        [rng.choice(arr, size=n, replace=True).mean() for _ in range(BOOTSTRAP_ITERATIONS)]
    )
    ci = (float(np.percentile(boot_means, 2.5)), float(np.percentile(boot_means, 97.5)))

    return PooledResult(
        class_name=class_name,
        n_events=n,
        mean_scar=mean_scar,
        t_statistic=float(t_stat),
        bootstrap_ci=ci,
        underpowered=False,
    )


def check_pre_registration(
    declared_classes: set[str], observed_classes: set[str]
) -> tuple[set[str], set[str]]:
    """Split observed event classes into (pre_registered, exploratory)
    against a study config's declared classes (hygiene rule #3). A class
    that shows up in results but wasn't declared before the run must be
    reported separately, never folded into the registered findings.
    """
    pre_registered = observed_classes & declared_classes
    exploratory = observed_classes - declared_classes
    return pre_registered, exploratory
