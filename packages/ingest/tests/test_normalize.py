"""Canonical table construction: imputation flags, aggregation, tickets, calendar."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pandas as pd
import pytest

from ovf_ingest.normalize import (
    build_calendar_daily,
    build_traffic_hourly,
    build_visitors_daily,
    build_visitors_hourly,
    build_weather_daily,
    build_weather_hourly,
    decode_weathercode,
    normalize_tickets,
    tz_of,
)
from support import helsinki_midnight_utc

HELSINKI = tz_of("Europe/Helsinki")
DAY = date(2026, 5, 1)


def _observed_day(values: dict[int, tuple[float, float]]) -> dict[datetime, tuple[float, float]]:
    """Build observations for the given local hours of 1 May 2026."""
    midnight = helsinki_midnight_utc(DAY)
    return {midnight + timedelta(hours=hour): value for hour, value in values.items()}


# --------------------------------------------------------------------------------------
# is_imputed
# --------------------------------------------------------------------------------------


def test_a_genuine_zero_is_not_flagged_as_imputed() -> None:
    frame = build_visitors_hourly({1: _observed_day({0: (0.0, 0.0)})}, {1: (DAY, DAY)}, HELSINKI)
    midnight = frame.iloc[0]
    assert midnight["visitors_total"] == 0
    assert bool(midnight["is_imputed"]) is False


def test_an_hour_the_api_never_answered_is_flagged_as_imputed() -> None:
    frame = build_visitors_hourly({1: _observed_day({0: (5.0, 3.0)})}, {1: (DAY, DAY)}, HELSINKI)
    assert len(frame) == 24
    assert bool(frame.iloc[0]["is_imputed"]) is False
    assert frame.iloc[0]["visitors_total"] == 8
    imputed = frame[frame["is_imputed"].astype(bool)]
    assert len(imputed) == 23
    assert set(imputed["visitors_total"]) == {0}


def test_an_hour_seen_in_one_direction_only_still_counts_as_observed() -> None:
    frame = build_visitors_hourly({1: _observed_day({7: (4.0, 0.0)})}, {1: (DAY, DAY)}, HELSINKI)
    row = frame[frame["ts_local"].str.startswith("2026-05-01T07")].iloc[0]
    assert bool(row["is_imputed"]) is False
    assert row["visitors_in"] == 4
    assert row["visitors_out"] == 0


def test_visitors_total_is_the_sum_of_both_directions() -> None:
    frame = build_visitors_hourly({1: _observed_day({0: (5.0, 3.0)})}, {1: (DAY, DAY)}, HELSINKI)
    assert frame.iloc[0]["visitors_total"] == frame.iloc[0]["visitors_in"] + frame.iloc[0]["visitors_out"]


def test_hourly_rows_carry_both_timestamp_columns() -> None:
    frame = build_visitors_hourly({1: {}}, {1: (DAY, DAY)}, HELSINKI)
    assert frame.iloc[0]["ts_utc"] == "2026-04-30T21:00:00Z"
    assert frame.iloc[0]["ts_local"] == "2026-05-01T00:00:00+03:00"


def test_the_spring_forward_day_yields_23_rows() -> None:
    spring = date(2026, 3, 29)
    frame = build_visitors_hourly({1: {}}, {1: (spring, spring)}, HELSINKI)
    assert len(frame) == 23


# --------------------------------------------------------------------------------------
# Daily aggregation
# --------------------------------------------------------------------------------------


def test_daily_rows_count_observed_hours_and_completeness() -> None:
    hourly = build_visitors_hourly(
        {1: _observed_day({0: (1.0, 1.0), 5: (2.0, 0.0)})}, {1: (DAY, DAY)}, HELSINKI
    )
    daily = build_visitors_daily(hourly)
    row = daily.iloc[0]
    assert row["date"] == "2026-05-01"
    assert row["observed_hours"] == 2
    assert bool(row["is_complete"]) is False
    assert row["visitors_total"] == 4


def test_a_fully_observed_day_is_complete() -> None:
    hourly = build_visitors_hourly(
        {1: _observed_day({hour: (1.0, 1.0) for hour in range(24)})}, {1: (DAY, DAY)}, HELSINKI
    )
    daily = build_visitors_daily(hourly)
    assert daily.iloc[0]["observed_hours"] == 24
    assert bool(daily.iloc[0]["is_complete"]) is True


def test_a_fully_observed_spring_forward_day_is_complete_with_23_hours() -> None:
    spring = date(2026, 3, 29)
    midnight = helsinki_midnight_utc(spring)
    observed = {midnight + timedelta(hours=hour): (1.0, 0.0) for hour in range(23)}
    hourly = build_visitors_hourly({1: observed}, {1: (spring, spring)}, HELSINKI)
    daily = build_visitors_daily(hourly)
    assert daily.iloc[0]["observed_hours"] == 23
    assert bool(daily.iloc[0]["is_complete"]) is True


# --------------------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------------------


def test_weather_flags_are_derived_and_missing_stays_missing() -> None:
    midnight = helsinki_midnight_utc(DAY)
    observations = {
        1: {
            midnight: {
                "temperature_2m": -3.5,
                "precipitation": 0.4,
                "wind_speed_10m": 12.0,
                "relative_humidity_2m": 80,
                "weathercode": 61,
            }
        }
    }
    frame = build_weather_hourly(observations, {1: {DAY: "archive"}}, {1: (DAY, DAY)}, HELSINKI)
    first = frame.iloc[0]
    assert first["weathercode_str"] == "slight_rain"
    assert bool(first["is_precipitation"]) is True
    assert bool(first["is_cold"]) is True
    assert bool(first["is_windy"]) is True
    assert first["source"] == "archive"
    missing = frame.iloc[1]
    assert pd.isna(missing["temperature_2m"])
    assert pd.isna(missing["is_cold"])
    assert missing["source"] == "archive"


def test_weather_daily_aggregates_the_documented_way() -> None:
    midnight = helsinki_midnight_utc(DAY)
    observations = {
        1: {
            midnight + timedelta(hours=hour): {
                "temperature_2m": float(hour),
                "precipitation": 1.0 if hour < 3 else 0.0,
                "wind_speed_10m": 5.0,
                "relative_humidity_2m": 70,
                "weathercode": 3 if hour else 61,
            }
            for hour in range(24)
        }
    }
    hourly = build_weather_hourly(observations, {1: {DAY: "archive"}}, {1: (DAY, DAY)}, HELSINKI)
    daily = build_weather_daily(hourly).iloc[0]
    assert daily["temp_min"] == 0.0
    assert daily["temp_max"] == 23.0
    assert daily["temp_mean"] == 11.5
    assert daily["precip_sum"] == 3.0
    assert daily["precip_hours"] == 3
    assert daily["weathercode_mode"] == 3
    assert daily["weathercode_str"] == "overcast"
    assert daily["source"] == "archive"


@pytest.mark.parametrize(
    ("code", "name"), [(0, "clear"), (3, "overcast"), (95, "thunderstorm"), (7, "unknown")]
)
def test_weather_codes_decode_to_names(code: int, name: str) -> None:
    assert decode_weathercode(code) == name


# --------------------------------------------------------------------------------------
# Traffic
# --------------------------------------------------------------------------------------


def test_traffic_is_keyed_on_site_not_venue() -> None:
    midnight = helsinki_midnight_utc(DAY)
    observations = {"raatti": {"JK_IN": {midnight: 5.0}, "PP_OUT": {midnight: 2.0}}}
    frame = build_traffic_hourly(observations, {"raatti": (DAY, DAY)}, {"raatti": "Karjasilta"}, HELSINKI)
    assert "venue_id" not in frame.columns
    first = frame.iloc[0]
    assert first["site_id"] == "raatti"
    assert first["site_name"] == "Karjasilta"
    assert first["jk_in"] == 5
    assert first["pp_out"] == 2
    assert pd.isna(first["jk_out"])


def test_traffic_local_time_leads_utc_by_three_hours_in_summer() -> None:
    frame = build_traffic_hourly({}, {"raatti": (DAY, DAY)}, {"raatti": "Karjasilta"}, HELSINKI)
    row = frame.iloc[0]
    utc = datetime.strptime(row["ts_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    local = datetime.fromisoformat(row["ts_local"])
    assert local.utcoffset() == timedelta(hours=3)
    assert local.astimezone(UTC) == utc


def test_traffic_local_time_leads_utc_by_two_hours_in_winter() -> None:
    winter = date(2026, 1, 15)
    frame = build_traffic_hourly({}, {"raatti": (winter, winter)}, {"raatti": "Karjasilta"}, HELSINKI)
    local = datetime.fromisoformat(frame.iloc[0]["ts_local"])
    assert local.utcoffset() == timedelta(hours=2)


# --------------------------------------------------------------------------------------
# Tickets
# --------------------------------------------------------------------------------------


def test_tickets_accept_the_english_headers() -> None:
    raw = pd.DataFrame({"DATE": ["14.1.2026"], "TICKETS": ["16"], "GROUPS": ["370"], "TOTAL": ["386"]})
    frame = normalize_tickets(raw, 1)
    row = frame.iloc[0]
    assert row["date"] == "2026-01-14"
    assert row["tickets_sold"] == 16
    assert row["groups_sold"] == 370
    assert row["tickets_total"] == 386


def test_tickets_accept_the_finnish_aliases() -> None:
    raw = pd.DataFrame({"pvm": ["14.1.2026"], "liput": ["16"], "ryhmat": ["370"], "yhteensa": ["386"]})
    frame = normalize_tickets(raw, 2)
    assert frame.iloc[0]["tickets_total"] == 386
    assert frame.iloc[0]["venue_id"] == 2


def test_tickets_total_is_derived_when_the_column_is_absent() -> None:
    raw = pd.DataFrame({"pvm": ["14.1.2026"], "liput": ["16"], "ryhmät": ["4"]})
    assert normalize_tickets(raw, 1).iloc[0]["tickets_total"] == 20


def test_tickets_drop_rows_with_an_unreadable_date() -> None:
    raw = pd.DataFrame({"DATE": ["14.1.2026", "not a date"], "TICKETS": ["1", "2"]})
    assert len(normalize_tickets(raw, 1)) == 1


def test_tickets_without_a_date_column_are_rejected() -> None:
    with pytest.raises(ValueError, match="no recognizable date column"):
        normalize_tickets(pd.DataFrame({"TICKETS": ["1"]}), 1)


# --------------------------------------------------------------------------------------
# Calendar
# --------------------------------------------------------------------------------------


def test_calendar_marks_holidays_weekends_and_the_countdown() -> None:
    holidays = pd.DataFrame({"date": ["2026-05-01", "2026-05-14"], "holiday_name": ["Vappu", "Helatorstai"]})
    frame = build_calendar_daily(date(2026, 4, 29), date(2026, 5, 3), holidays)
    by_date = frame.set_index("date")
    assert bool(by_date.loc["2026-05-01", "is_holiday"]) is True
    assert by_date.loc["2026-05-01", "holiday_name"] == "Vappu"
    assert by_date.loc["2026-04-29", "days_before_next_holiday"] == 2
    assert bool(by_date.loc["2026-04-30", "is_last_workday_before_holiday"]) is True
    assert bool(by_date.loc["2026-05-02", "is_weekend"]) is True
    assert by_date.loc["2026-05-02", "day_of_week"] == 5


def test_calendar_uses_the_sentinel_when_no_holiday_follows() -> None:
    frame = build_calendar_daily(
        date(2026, 5, 1), date(2026, 5, 1), pd.DataFrame(columns=["date", "holiday_name"])
    )
    assert frame.iloc[0]["days_before_next_holiday"] == 999
    assert pd.isna(frame.iloc[0]["holiday_name"])


def test_calendar_reports_iso_week_month_and_year() -> None:
    frame = build_calendar_daily(
        date(2026, 1, 1), date(2026, 1, 1), pd.DataFrame(columns=["date", "holiday_name"])
    )
    row = frame.iloc[0]
    assert row["week_of_year"] == 1
    assert row["month"] == 1
    assert row["year"] == 2026
