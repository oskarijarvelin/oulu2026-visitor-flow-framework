"""The hourly profile: shares that sum to one, closed hours that stay closed."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.profile import DAYS_PER_WEEK, build_profile, spread_over_hours
from synthetic import OPEN_HOURS

ORIGIN = date(2026, 6, 30)


@pytest.mark.parametrize("venue_id", [1, 2])
def test_shares_sum_to_one_for_every_weekday(synthetic_repo: Path, venue_id: int) -> None:
    """Every ``(venue, day_of_week)`` row of the profile is a proper distribution."""
    data = load_dataset(synthetic_repo)
    profile = build_profile(data.visitors_hourly, venue_id, ORIGIN)

    for weekday in range(DAYS_PER_WEEK):
        assert profile.day_shares(weekday).sum() == pytest.approx(1.0, abs=1e-12)
        assert (profile.day_shares(weekday) >= 0).all()


def test_closed_hours_are_forced_to_zero(synthetic_repo: Path) -> None:
    """Opening hours are read out of the data, not configured."""
    data = load_dataset(synthetic_repo)
    profile = build_profile(data.visitors_hourly, 1, ORIGIN)

    assert set(profile.open_hours) <= set(OPEN_HOURS)
    for weekday in range(DAYS_PER_WEEK):
        shares = profile.day_shares(weekday)
        for hour in range(24):
            if hour not in profile.open_hours:
                assert shares[hour] == 0.0


def test_profile_only_reads_days_up_to_the_origin(synthetic_repo: Path) -> None:
    """A profile built at an earlier origin cannot see the days after it."""
    data = load_dataset(synthetic_repo)
    early = build_profile(data.visitors_hourly, 1, date(2026, 4, 30))
    hourly = data.visitors_hourly.copy()
    later = hourly["date"] > "2026-04-30"
    hourly.loc[later, "visitors_total"] = 999_999
    corrupted = build_profile(hourly, 1, date(2026, 4, 30))

    np.testing.assert_allclose(early.shares, corrupted.shares)


def test_shrinkage_pulls_a_thin_weekday_towards_the_common_profile(synthetic_repo: Path) -> None:
    """With k = 4 and eight observations per weekday the shapes stay close together."""
    data = load_dataset(synthetic_repo)
    strong = build_profile(data.visitors_hourly, 1, ORIGIN, shrink_k=0.0)
    shrunk = build_profile(data.visitors_hourly, 1, ORIGIN, shrink_k=100.0)

    spread_strong = float(np.std(strong.shares, axis=0).sum())
    spread_shrunk = float(np.std(shrunk.shares, axis=0).sum())
    assert spread_shrunk <= spread_strong


def test_spread_over_hours_reproduces_the_daily_value(synthetic_repo: Path) -> None:
    """Splitting a day across its hours conserves the total, DST days included."""
    data = load_dataset(synthetic_repo)
    profile = build_profile(data.visitors_hourly, 1, ORIGIN)

    for hours in (list(range(24)), list(range(23)), [*range(24), 3]):
        spread = spread_over_hours(profile, 5, hours, 500.0)
        assert spread.sum() == pytest.approx(500.0, abs=1e-9)
        assert (spread >= 0).all()


def test_empty_window_falls_back_to_a_flat_profile(synthetic_repo: Path) -> None:
    """A venue with no history still yields a usable, normalized profile."""
    data = load_dataset(synthetic_repo)
    profile = build_profile(data.visitors_hourly, 1, date(2020, 1, 1))

    assert profile.observed_days == 0
    assert profile.day_shares(0).sum() == pytest.approx(1.0)
