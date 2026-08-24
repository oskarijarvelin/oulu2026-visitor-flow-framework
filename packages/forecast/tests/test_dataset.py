"""Reading ``data/processed``: covariate joins, the weather fallback, and DST."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ovf_forecast.dataset import (
    MAX_WEATHER_FORECAST_DAYS,
    WEATHER_GROUP_ORDER,
    WEATHER_SOURCE_CLIMATOLOGY,
    WEATHER_SOURCE_FORECAST,
    calendar_gap,
    load_dataset,
    normalized_day_of_year,
    venue_future,
    venue_history,
    weather_group,
)
from ovf_forecast.export import local_hours_of_day

ORIGIN = date(2026, 6, 30)


def test_history_carries_target_weather_and_calendar(synthetic_repo: Path) -> None:
    """One row per observed day, with everything a feature needs already joined."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)

    assert history["date"].is_monotonic_increasing
    assert not history["date"].duplicated().any()
    for column in ("visitors_total", "temp_mean", "precip_sum", "is_holiday", "day_of_week"):
        assert column in history.columns
    assert history["visitors_total"].notna().all()


def test_leading_zero_days_are_dropped(synthetic_repo: Path) -> None:
    """A sensor that was not installed yet is not a venue nobody visited."""
    data = load_dataset(synthetic_repo)
    daily = data.visitors_daily
    padded = daily.copy()
    first = padded["date"].min()
    blanks = pd.DataFrame(
        {
            "venue_id": 1,
            "date": pd.date_range(first - pd.Timedelta(days=10), first - pd.Timedelta(days=1), freq="D"),
            "visitors_in": 0,
            "visitors_out": 0,
            "visitors_total": 0,
            "observed_hours": 24,
            "is_complete": True,
        }
    )
    object.__setattr__(data, "visitors_daily", pd.concat([blanks, padded], ignore_index=True))

    history = venue_history(data, 1)
    assert history["date"].min() == first
    assert float(history["visitors_total"].iloc[0]) > 0


def test_weather_falls_back_to_climatology_past_day_16(synthetic_repo: Path) -> None:
    """Open-Meteo forecasts 16 days; days 17-30 use the ten-year normals."""
    data = load_dataset(synthetic_repo)
    future = venue_future(data, 1, ORIGIN, 30)

    early = future.loc[future["horizon_days"] <= MAX_WEATHER_FORECAST_DAYS]
    late = future.loc[future["horizon_days"] > MAX_WEATHER_FORECAST_DAYS]
    assert set(early["weather_source"]) == {WEATHER_SOURCE_FORECAST}
    assert set(late["weather_source"]) == {WEATHER_SOURCE_CLIMATOLOGY}
    assert late["temp_mean"].notna().all()


def test_climatology_rows_admit_they_do_not_know_about_rain(synthetic_repo: Path) -> None:
    """``is_rainy_day`` stays missing on normals rather than being guessed."""
    data = load_dataset(synthetic_repo)
    future = venue_future(data, 1, ORIGIN, 30)

    late = future.loc[future["weather_source"] == WEATHER_SOURCE_CLIMATOLOGY]
    assert late["is_rainy_day"].isna().all()
    early = future.loc[future["weather_source"] == WEATHER_SOURCE_FORECAST]
    assert early["is_rainy_day"].notna().all()


def test_horizon_is_contiguous_and_starts_the_day_after_the_origin(synthetic_repo: Path) -> None:
    """No gaps, no off-by-one at the origin."""
    data = load_dataset(synthetic_repo)
    future = venue_future(data, 1, ORIGIN, 30)

    assert list(future["horizon_days"]) == list(range(1, 31))
    assert future["date"].iloc[0] == pd.Timestamp(ORIGIN) + pd.Timedelta(days=1)
    assert (future["date"].diff().dropna() == pd.Timedelta(days=1)).all()


@pytest.mark.parametrize(
    ("code", "expected"),
    [(0, "clear"), (3, "cloudy"), (61, "rain"), (71, "snow"), (None, "other"), (12345, "other")],
)
def test_weather_codes_map_to_groups(code: int | None, expected: str) -> None:
    """The model sees five coarse groups, not 28 sparse codes."""
    assert weather_group(code) == expected
    assert expected in WEATHER_GROUP_ORDER


def test_leap_day_folds_into_february_28() -> None:
    """The climatology table is built on a common-year scale."""
    assert normalized_day_of_year(date(2026, 3, 1)) == 60
    assert normalized_day_of_year(date(2024, 2, 29)) == 59
    assert normalized_day_of_year(date(2024, 3, 1)) == 60


def test_calendar_gap_reports_days_the_calendar_does_not_reach(synthetic_repo: Path) -> None:
    """Holidays cannot be invented, so a short calendar has to be flagged."""
    data = load_dataset(synthetic_repo)
    assert calendar_gap(data, ORIGIN, 30) == []
    assert calendar_gap(data, date(2026, 8, 1), 30) != []


def test_spring_forward_day_has_23_hours() -> None:
    """23 or 25 hours on a transition day is the contract, not a bug."""
    assert len(local_hours_of_day(date(2026, 3, 29))) == 23
    assert len(local_hours_of_day(date(2026, 10, 25))) == 25
    assert len(local_hours_of_day(date(2026, 6, 15))) == 24


def test_hourly_tables_derive_the_local_hour_from_utc(synthetic_repo: Path) -> None:
    """``ts_local`` carries mixed offsets, so the wall clock comes from ``ts_utc``."""
    data = load_dataset(synthetic_repo)
    frame = data.visitors_hourly
    local = pd.to_datetime(frame["ts_local"], utc=True, format="ISO8601").dt.tz_convert("Europe/Helsinki")

    assert (frame["hour"] == local.dt.hour).all()
    assert (frame["date"] == local.dt.normalize().dt.tz_localize(None)).all()
