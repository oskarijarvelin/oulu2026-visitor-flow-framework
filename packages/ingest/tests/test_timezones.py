"""The time zone contract, including both 2026 daylight saving transitions."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from itertools import pairwise

from ovf_ingest.normalize import (
    format_local,
    format_utc,
    local_date_of,
    local_midnight,
    localize_naive,
    tz_of,
    utc_hours_for_local_days,
)

HELSINKI = tz_of("Europe/Helsinki")
SPRING_FORWARD = date(2026, 3, 29)
FALL_BACK = date(2026, 10, 25)


def test_format_utc_uses_the_z_suffix() -> None:
    moment = datetime(2026, 5, 22, 4, 0, tzinfo=UTC)
    assert format_utc(moment) == "2026-05-22T04:00:00Z"


def test_format_local_uses_a_real_offset_not_a_fixed_one() -> None:
    summer = datetime(2026, 5, 22, 4, 0, tzinfo=UTC)
    winter = datetime(2026, 1, 22, 4, 0, tzinfo=UTC)
    assert format_local(summer, HELSINKI) == "2026-05-22T07:00:00+03:00"
    assert format_local(winter, HELSINKI) == "2026-01-22T06:00:00+02:00"


def test_spring_forward_day_has_23_hours() -> None:
    hours = utc_hours_for_local_days(SPRING_FORWARD, SPRING_FORWARD, HELSINKI)
    assert len(hours) == 23
    assert format_local(hours[0], HELSINKI) == "2026-03-29T00:00:00+02:00"
    assert format_local(hours[-1], HELSINKI) == "2026-03-29T23:00:00+03:00"
    local_hours = [moment.astimezone(HELSINKI).hour for moment in hours]
    assert 3 not in local_hours


def test_fall_back_day_has_25_hours() -> None:
    hours = utc_hours_for_local_days(FALL_BACK, FALL_BACK, HELSINKI)
    assert len(hours) == 25
    local_hours = [moment.astimezone(HELSINKI).hour for moment in hours]
    assert local_hours.count(3) == 2


def test_full_acceptance_window_loses_exactly_one_hour() -> None:
    hours = utc_hours_for_local_days(date(2026, 1, 1), date(2026, 5, 22), HELSINKI)
    assert len(hours) == 3407
    assert 142 * 24 - len(hours) == 1


def test_hour_grid_is_contiguous_in_utc() -> None:
    hours = utc_hours_for_local_days(date(2026, 3, 28), date(2026, 3, 30), HELSINKI)
    gaps = {second - first for first, second in pairwise(hours)}
    assert gaps == {timedelta(hours=1)}


def test_localize_rejects_the_hour_that_does_not_exist() -> None:
    assert localize_naive(datetime(2026, 3, 29, 3, 0), HELSINKI) is None
    assert localize_naive(datetime(2026, 3, 29, 2, 0), HELSINKI) is not None
    assert localize_naive(datetime(2026, 3, 29, 4, 0), HELSINKI) is not None


def test_localize_resolves_the_repeated_hour_to_the_first_occurrence() -> None:
    ambiguous = localize_naive(datetime(2026, 10, 25, 3, 30), HELSINKI)
    assert ambiguous is not None
    assert format_utc(ambiguous) == "2026-10-25T00:30:00Z"


def test_local_midnight_is_stable_across_the_transitions() -> None:
    assert format_utc(local_midnight(SPRING_FORWARD, HELSINKI)) == "2026-03-28T22:00:00Z"
    assert format_utc(local_midnight(FALL_BACK, HELSINKI)) == "2026-10-24T21:00:00Z"


def test_local_date_of_respects_the_offset() -> None:
    assert local_date_of(datetime(2026, 5, 21, 21, 30, tzinfo=UTC), HELSINKI) == date(2026, 5, 22)
    assert local_date_of(datetime(2026, 1, 21, 21, 30, tzinfo=UTC), HELSINKI) == date(2026, 1, 21)
