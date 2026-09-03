"""Naming one month's quiet days on a series whose rhythm is known."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.quiet.forecast import (
    QuietForecastConfig,
    VenueMonthForecast,
    forecast_month,
    next_month,
)
from ovf_forecast.quiet.threshold import REASON_OPEN, quiet_count
from synthetic import DOW_FACTORS, LAST_OBSERVED_DAY

QUIET_WEEKDAYS = tuple(sorted(range(7), key=lambda weekday: DOW_FACTORS[weekday])[:2])


def _forecast(
    root: Path, year: int = 2026, month: int = 7, *, top_k: int | None = None
) -> VenueMonthForecast:
    data = load_dataset(root)
    config = QuietForecastConfig(n_simulations=2000, top_k=top_k)
    result = forecast_month(data, data.venue(1), year, month, config)
    assert result is not None
    return result


def test_next_month_wraps_the_year() -> None:
    assert next_month(date(2026, 8, 25)) == (2026, 9)
    assert next_month(date(2026, 12, 31)) == (2027, 1)


def test_every_day_of_the_month_comes_back(synthetic_repo: Path) -> None:
    result = _forecast(synthetic_repo)
    assert [day.day for day in result.days] == [date(2026, 7, number) for number in range(1, 32)]
    assert result.origin == LAST_OBSERVED_DAY
    assert result.label == "2026-07"


def test_the_quiet_set_is_a_fifth_of_the_month(synthetic_repo: Path) -> None:
    result = _forecast(synthetic_repo)
    assert result.quiet.n_eligible == 31
    assert result.quiet.k == quiet_count(31)
    assert len(result.quiet_days) == result.quiet.k


def test_the_quiet_days_fall_on_the_quietest_weekdays(synthetic_repo: Path) -> None:
    """The generating process makes Monday and Tuesday the slow days; so must the answer."""
    result = _forecast(synthetic_repo)
    assert {day.day.weekday() for day in result.quiet_days} <= set(QUIET_WEEKDAYS)


def test_a_fixed_size_answer_can_be_asked_for(synthetic_repo: Path) -> None:
    result = _forecast(synthetic_repo, top_k=3)
    assert result.quiet.k == 3
    assert len(result.quiet_days) == 3


def test_probabilities_are_shared_inside_a_tie_and_sum_to_the_set_size(synthetic_repo: Path) -> None:
    result = _forecast(synthetic_repo)
    eligible = [day for day in result.days if day.is_eligible]
    assert sum(day.probability for day in eligible) == pytest.approx(result.quiet.k, abs=0.05)
    mondays = [day.probability for day in eligible if day.day.weekday() == QUIET_WEEKDAYS[0]]
    assert len(set(np.round(mondays, 9))) == 1
    assert min(mondays) > max(
        day.probability for day in eligible if day.day.weekday() not in QUIET_WEEKDAYS
    )


def test_a_split_tie_is_reported_rather_than_hidden(synthetic_repo: Path) -> None:
    """Four Mondays and a set of six means two of the next weekday get in by date order."""
    result = _forecast(synthetic_repo)
    assert any(day.tie_size > 1 for day in result.quiet_days)
    assert any("tasapisteryhmän" in warning["fi"] for warning in result.warnings)
    assert any("tie group" in warning["en"] for warning in result.warnings)


def test_days_already_observed_keep_their_real_value(synthetic_repo: Path) -> None:
    """Running mid-month ranks what happened against what is still to come."""
    result = _forecast(synthetic_repo, year=2026, month=6)
    observed = [day for day in result.days if day.is_observed]
    assert len(observed) == 30, "the whole of June is behind the origin"
    assert all(day.probability in (0.0, 1.0) for day in observed if day.status == REASON_OPEN)
    assert result.quiet.k == quiet_count(30)


def test_the_answer_is_deterministic(synthetic_repo: Path) -> None:
    first = _forecast(synthetic_repo)
    second = _forecast(synthetic_repo)
    assert first.to_dict() == second.to_dict()
