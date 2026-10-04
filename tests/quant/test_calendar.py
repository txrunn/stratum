from datetime import date, timedelta

import pytest

from stratum.quant.calendar import (
    align_event,
    is_trading_day,
    next_trading_day,
    nyse_holidays,
    previous_trading_day,
    trading_day_offset,
)


@pytest.mark.parametrize("year", [2020, 2024, 2026, 2030])
def test_nyse_holidays_fall_on_expected_weekdays(year):
    holidays = nyse_holidays(year)
    # Nth-weekday-of-month holidays are pinned to their rule's weekday even
    # after observance shifting (none of these ever fall on a weekend by
    # construction, so no shift applies to them).
    mlk = next(h for h in holidays if h.month == 1 and 15 <= h.day <= 21)
    assert mlk.weekday() == 0  # Monday
    thanksgiving = next(h for h in holidays if h.month == 11)
    assert thanksgiving.weekday() == 3  # Thursday
    labor_day = next(h for h in holidays if h.month == 9)
    assert labor_day.weekday() == 0  # Monday


def test_nyse_holidays_fixed_dates_never_land_on_weekend():
    # New Year's, July 4th, Christmas are observed on the nearest weekday
    # when the actual date falls on a Saturday or Sunday.
    for year in range(2015, 2035):
        for h in nyse_holidays(year):
            assert h.weekday() < 5


def test_juneteenth_only_a_holiday_from_2022():
    pre_2022 = nyse_holidays(2021)
    post_2022 = nyse_holidays(2022)
    assert not any(h.month == 6 and h.day in (18, 19, 20) for h in pre_2022)
    assert any(h.month == 6 and h.day in (18, 19, 20) for h in post_2022)


# 2026-10-02 (Fri) / 10-03 (Sat) / 10-05 (Mon) span no NYSE holiday, unlike
# the first Monday of September (Labor Day) — picked deliberately to avoid
# that collision after an earlier draft of these tests hit it.


def test_is_trading_day_weekend_is_false():
    saturday = date(2026, 10, 3)
    assert saturday.weekday() == 5
    assert is_trading_day(saturday) is False


def test_is_trading_day_holiday_is_false():
    holiday = next(iter(nyse_holidays(2026)))
    assert is_trading_day(holiday) is False


def test_next_trading_day_skips_weekend():
    friday = date(2026, 10, 2)
    assert friday.weekday() == 4
    nxt = next_trading_day(friday)
    assert nxt.weekday() == 0  # Monday
    assert nxt == friday + timedelta(days=3)


def test_previous_trading_day_skips_weekend():
    monday = date(2026, 10, 5)
    prev = previous_trading_day(monday)
    assert prev.weekday() == 4  # Friday
    assert prev == monday - timedelta(days=3)


def test_trading_day_offset_counts_sessions_not_calendar_days():
    # Friday + 1 session should be the following Monday, not Saturday.
    friday = date(2026, 10, 2)
    assert is_trading_day(friday)
    one_session_later = trading_day_offset(friday, 1)
    assert one_session_later == next_trading_day(friday)
    assert one_session_later.weekday() == 0


def test_trading_day_offset_zero_returns_base():
    friday = date(2026, 10, 2)
    assert trading_day_offset(friday, 0) == friday


def test_trading_day_offset_negative_moves_backward():
    monday = date(2026, 10, 5)
    assert trading_day_offset(monday, -1) == previous_trading_day(monday)


def test_trading_day_offset_rejects_non_session_base():
    saturday = date(2026, 10, 3)
    with pytest.raises(ValueError, match="not a trading session"):
        trading_day_offset(saturday, 1)


def test_align_event_pm_moves_to_next_session():
    # 2026-10-02 is a Friday trading day; a pm release there means t=0 is
    # the following Monday.
    friday = date(2026, 10, 2)
    t0 = align_event(friday, "pm")
    assert t0 == next_trading_day(friday)
    assert t0.weekday() == 0


def test_align_event_am_same_session():
    friday = date(2026, 10, 2)
    t0 = align_event(friday, "am")
    assert t0 == friday


def test_align_event_am_rolls_forward_from_non_session_date():
    saturday = date(2026, 10, 3)
    t0 = align_event(saturday, "am")
    assert t0 == date(2026, 10, 5)  # the following Monday
    assert is_trading_day(t0)
