"""Weather normals: leap-day folding and the aggregation shape."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from ovf_ingest.climatology import CLIMATOLOGY_COLUMNS, aggregate_climatology, normalized_day_of_year
from ovf_ingest.normalize import tz_of

HELSINKI = tz_of("Europe/Helsinki")


def test_leap_day_folds_into_the_day_before() -> None:
    assert normalized_day_of_year(date(2024, 2, 28)) == 59
    assert normalized_day_of_year(date(2024, 2, 29)) == 59


def test_march_first_is_the_same_day_of_year_in_every_kind_of_year() -> None:
    assert normalized_day_of_year(date(2024, 3, 1)) == normalized_day_of_year(date(2025, 3, 1)) == 60


def test_the_year_ends_on_365_in_leap_and_common_years() -> None:
    assert normalized_day_of_year(date(2024, 12, 31)) == 365
    assert normalized_day_of_year(date(2025, 12, 31)) == 365


def test_aggregation_averages_the_same_hour_across_years() -> None:
    observations = {}
    for year, temperature in ((2024, 0.0), (2025, 10.0)):
        moment = datetime(year, 7, 1, 9, 0, tzinfo=HELSINKI).astimezone(UTC)
        observations[moment] = {
            "temperature_2m": temperature,
            "precipitation": 1.0,
            "wind_speed_10m": 4.0,
        }
    frame = aggregate_climatology(observations, HELSINKI)
    assert list(frame.columns) == CLIMATOLOGY_COLUMNS
    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["day_of_year"] == normalized_day_of_year(date(2025, 7, 1))
    assert row["hour"] == 9
    assert row["temp_mean"] == 5.0
    assert row["temp_min"] == 0.0
    assert row["temp_max"] == 10.0
    assert row["precip_mean"] == 1.0
    assert row["wind_mean"] == 4.0


def test_hours_are_local_not_utc() -> None:
    """A UTC instant of 21:00 in summer is local midnight the next day."""
    moment = datetime(2025, 6, 30, 21, 0, tzinfo=UTC)
    frame = aggregate_climatology({moment: {"temperature_2m": 5.0}}, HELSINKI)
    assert frame.iloc[0]["hour"] == 0
    assert frame.iloc[0]["day_of_year"] == normalized_day_of_year(date(2025, 7, 1))


def test_an_empty_history_yields_an_empty_table() -> None:
    frame = aggregate_climatology({}, HELSINKI)
    assert frame.empty
    assert list(frame.columns) == CLIMATOLOGY_COLUMNS


def test_a_full_local_day_produces_24_rows() -> None:
    start = datetime(2025, 7, 1, 0, 0, tzinfo=HELSINKI).astimezone(UTC)
    observations = {start + timedelta(hours=hour): {"temperature_2m": float(hour)} for hour in range(24)}
    frame = aggregate_climatology(observations, HELSINKI)
    assert len(frame) == 24
    assert sorted(frame["hour"]) == list(range(24))
