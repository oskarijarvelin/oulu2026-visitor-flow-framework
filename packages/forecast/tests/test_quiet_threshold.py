"""What counts as a quiet day, and which days are allowed to be one."""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from ovf_forecast.quiet.threshold import (
    CLOSED_WEEKDAY_SHARE,
    MAX_QUIET_DAYS,
    MIN_QUIET_DAYS,
    REASON_CLOSED_HOLIDAY,
    REASON_CLOSED_WEEKDAY,
    REASON_INCOMPLETE,
    REASON_NO_VISITORS,
    REASON_OPEN,
    Eligibility,
    future_reason,
    observed_reason,
    quiet_count,
    quiet_set,
)

FIRST_DAY = date(2026, 1, 5)


def _series(values_by_weekday: dict[int, float], weeks: int = 12) -> pd.Series:
    """A daily series whose only structure is a weekday level."""
    days = [FIRST_DAY + timedelta(days=step) for step in range(weeks * 7)]
    values = [values_by_weekday[day.weekday()] for day in days]
    return pd.Series(values, index=pd.DatetimeIndex(days), dtype="float64")


def test_quiet_count_is_a_fifth_of_the_month_inside_the_clamp() -> None:
    assert quiet_count(30) == 6
    assert quiet_count(25) == 5


def test_quiet_count_clamps_both_ends() -> None:
    assert quiet_count(10) == MIN_QUIET_DAYS
    assert quiet_count(100) == MAX_QUIET_DAYS
    assert quiet_count(2) == 2, "a set can never be larger than the days it draws from"
    assert quiet_count(0) == 0


def test_quiet_set_takes_the_lowest_days_and_measures_them_against_the_median() -> None:
    days = [date(2026, 4, day) for day in range(1, 11)]
    values = np.array([100.0, 50.0, 200.0, 60.0, 150.0, 90.0, 300.0, 40.0, 120.0, 80.0])
    result = quiet_set(days, values, k=3)
    assert result.dates == (date(2026, 4, 2), date(2026, 4, 4), date(2026, 4, 8))
    assert result.median == pytest.approx(95.0)
    assert result.cut == pytest.approx(60.0)
    assert result.cut_ratio == pytest.approx(60.0 / 95.0)
    assert result.mean_ratio == pytest.approx(50.0 / 95.0)


def test_quiet_set_breaks_ties_in_calendar_order() -> None:
    days = [date(2026, 4, day) for day in range(1, 6)]
    values = np.array([10.0, 10.0, 10.0, 99.0, 99.0])
    assert quiet_set(days, values, k=2).dates == (date(2026, 4, 1), date(2026, 4, 2))


def test_a_flat_month_is_not_material() -> None:
    days = [date(2026, 4, day) for day in range(1, 11)]
    flat = quiet_set(days, np.linspace(98.0, 102.0, 10), k=3)
    assert not flat.is_material
    separated = quiet_set(days, np.linspace(40.0, 140.0, 10), k=3)
    assert separated.is_material


def test_a_weekday_the_venue_shuts_is_not_a_quiet_day() -> None:
    levels = dict.fromkeys(range(7), 200.0)
    levels[0] = 200.0 * CLOSED_WEEKDAY_SHARE / 2.0
    eligibility = Eligibility.from_training(_series(levels))
    assert eligibility.closed_weekdays == (0,)
    assert future_reason(date(2026, 4, 6), eligibility) == REASON_CLOSED_WEEKDAY
    assert future_reason(date(2026, 4, 7), eligibility) == REASON_OPEN


def test_a_merely_quiet_weekday_is_still_a_candidate() -> None:
    """A weekday at 60 % of the rest is the answer, not a filter."""
    levels = dict.fromkeys(range(7), 200.0)
    levels[0] = 120.0
    eligibility = Eligibility.from_training(_series(levels))
    assert eligibility.closed_weekdays == ()
    assert future_reason(date(2026, 4, 6), eligibility) == REASON_OPEN


def test_the_holiday_factor_needs_three_observations() -> None:
    series = _series(dict.fromkeys(range(7), 200.0))
    holidays = pd.Series(False, index=series.index)
    holidays.iloc[[3, 10]] = True
    thin = Eligibility.from_training(series, holidays)
    assert not np.isfinite(thin.holiday_factor)
    assert thin.holiday_observations == 2

    series.iloc[[3, 10, 17]] = 50.0
    holidays.iloc[17] = True
    measured = Eligibility.from_training(series, holidays)
    assert measured.holiday_factor == pytest.approx(50.0 / measured.weekday_means[3], rel=0.2)


def test_a_venue_that_closes_on_holidays_drops_them_from_the_candidates() -> None:
    series = _series(dict.fromkeys(range(7), 200.0))
    holidays = pd.Series(False, index=series.index)
    holidays.iloc[[3, 10, 17]] = True
    series.iloc[[3, 10, 17]] = 1.0
    eligibility = Eligibility.from_training(series, holidays)
    assert eligibility.closes_on_holidays
    assert future_reason(date(2026, 4, 3), eligibility, is_holiday=True) == REASON_CLOSED_HOLIDAY
    assert future_reason(date(2026, 4, 3), eligibility, is_holiday=False) == REASON_OPEN


def test_the_truth_side_drops_closures_and_half_measured_days() -> None:
    eligibility = Eligibility.from_training(_series(dict.fromkeys(range(7), 200.0)))
    day = date(2026, 4, 7)
    assert observed_reason(day, 180.0, eligibility) == REASON_OPEN
    assert observed_reason(day, 0.0, eligibility) == REASON_NO_VISITORS
    assert observed_reason(day, 180.0, eligibility, is_complete=False) == REASON_INCOMPLETE
