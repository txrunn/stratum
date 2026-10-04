"""Trading-session calendar and event-time alignment.

Owns the single place the am/pm alignment rule lives, and all trading-day
arithmetic: `t-5` means five *sessions* back, not five calendar days (see
ARCHITECTURE.md "quant/").

    report at 2026-02-25, timing = pm   ->   t=0 is 2026-02-26 (next session)
    report at 2026-02-25, timing = am   ->   t=0 is 2026-02-25

NYSE holidays are computed algorithmically (fixed-date-or-nth-weekday rules,
Good Friday via the Gregorian Easter computus), not hardcoded per year, so
this works for any date range a study throws at it without a yearly table
to maintain. No external trading-calendar dependency: this is a small,
fully self-contained, fully testable piece of arithmetic.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Literal

Timing = Literal["am", "pm"]


def _nth_weekday_of_month(year: int, month: int, weekday: int, n: int) -> date:
    """weekday: Mon=0..Sun=6. n=1 for the first occurrence, n=-1 for the last."""
    if n > 0:
        d = date(year, month, 1)
        count = 0
        while True:
            if d.weekday() == weekday:
                count += 1
                if count == n:
                    return d
            d += timedelta(days=1)
    if month == 12:
        d = date(year, 12, 31)
    else:
        d = date(year, month + 1, 1) - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def _easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month = (h + ell - 7 * m + 114) // 31
    day = ((h + ell - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed(d: date) -> date:
    """NYSE observance: a fixed holiday on Saturday moves to the preceding
    Friday; on Sunday, to the following Monday."""
    if d.weekday() == 5:
        return d - timedelta(days=1)
    if d.weekday() == 6:
        return d + timedelta(days=1)
    return d


def nyse_holidays(year: int) -> set[date]:
    """NYSE full-day market holidays for one calendar year."""
    holidays = {
        _observed(date(year, 1, 1)),  # New Year's Day
        _nth_weekday_of_month(year, 1, 0, 3),  # MLK Day
        _nth_weekday_of_month(year, 2, 0, 3),  # Presidents Day
        _easter_sunday(year) - timedelta(days=2),  # Good Friday
        _nth_weekday_of_month(year, 5, 0, -1),  # Memorial Day
        _observed(date(year, 7, 4)),  # Independence Day
        _nth_weekday_of_month(year, 9, 0, 1),  # Labor Day
        _nth_weekday_of_month(year, 11, 3, 4),  # Thanksgiving
        _observed(date(year, 12, 25)),  # Christmas
    }
    if year >= 2022:
        holidays.add(_observed(date(year, 6, 19)))  # Juneteenth, observed from 2022
    return holidays


def is_trading_day(d: date) -> bool:
    if d.weekday() >= 5:
        return False
    return d not in nyse_holidays(d.year)


def next_trading_day(d: date) -> date:
    """The first trading session strictly after `d`."""
    nxt = d + timedelta(days=1)
    while not is_trading_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def previous_trading_day(d: date) -> date:
    """The first trading session strictly before `d`."""
    prev = d - timedelta(days=1)
    while not is_trading_day(prev):
        prev -= timedelta(days=1)
    return prev


def _on_or_after_trading_day(d: date) -> date:
    cur = d
    while not is_trading_day(cur):
        cur += timedelta(days=1)
    return cur


def trading_day_offset(base: date, offset: int) -> date:
    """The trading session `offset` sessions away from `base`.

    `base` must itself be a trading session — callers get one from
    `align_event()`. Positive offsets move forward, negative backward,
    zero returns `base` unchanged. Raises ValueError on a non-session base
    rather than silently picking a nearby date: offsets are only meaningful
    relative to an actual t=0 session.
    """
    if not is_trading_day(base):
        raise ValueError(f"{base} is not a trading session; align it first (see align_event())")
    cur = base
    remaining = abs(offset)
    step_forward = offset > 0
    while remaining > 0:
        cur = next_trading_day(cur) if step_forward else previous_trading_day(cur)
        remaining -= 1
    return cur


def align_event(event_date: date, timing: Timing) -> date:
    """t=0: the session the market first had a chance to react on.

    A `pm` release lands after the close, so t=0 is the next session. An
    `am` release lands before the open, so t=0 is `event_date` itself —
    defensively rolled forward to the next session if `event_date` somehow
    isn't one (real FOMC/CPI/earnings dates always are, but this keeps the
    function total rather than raising on a malformed calendar entry).
    """
    if timing == "pm":
        return next_trading_day(event_date)
    return _on_or_after_trading_day(event_date)
