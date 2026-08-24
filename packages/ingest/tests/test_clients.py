"""Client parsing, checked against responses captured from the real APIs."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest

from conftest import load_fixture
from ovf_ingest.clients.ecocounter import build_site_data_query, validate_enum
from ovf_ingest.normalize import (
    format_local,
    format_utc,
    parse_ecocounter_payload,
    parse_visitor_payload,
    parse_visitor_timestamp,
    parse_weather_payload,
    tz_of,
    weather_offset,
)

HELSINKI = tz_of("Europe/Helsinki")


# --------------------------------------------------------------------------------------
# Jaskaretail
# --------------------------------------------------------------------------------------


def test_visitor_payload_parses_a_full_local_day() -> None:
    payload = load_fixture("jaskaretail_venue1_in.json")
    counts = parse_visitor_payload(payload, HELSINKI, location_hierarchy_id=178)
    assert len(counts) == 24
    first = min(counts)
    assert format_utc(first) == "2026-04-30T21:00:00Z"
    assert format_local(first, HELSINKI) == "2026-05-01T00:00:00+03:00"


def test_visitor_payload_drops_the_hour_the_clock_skips() -> None:
    payload = load_fixture("jaskaretail_venue1_dst_spring_in.json")
    assert len(payload["result"]) == 24
    counts = parse_visitor_payload(payload, HELSINKI, location_hierarchy_id=178)
    assert len(counts) == 23
    local_hours = sorted(moment.astimezone(HELSINKI).hour for moment in counts)
    assert 3 not in local_hours


def test_visitor_payload_ignores_other_locations() -> None:
    payload = {
        "result": [
            {"categoryName": "01/05/2026 08:00:00", "locationId": 178, "visitors": 12},
            {"categoryName": "01/05/2026 08:00:00", "locationId": 183, "visitors": 99},
        ]
    }
    counts = parse_visitor_payload(payload, HELSINKI, location_hierarchy_id=178)
    assert list(counts.values()) == [12.0]


def test_visitor_payload_sums_duplicate_rows_for_one_hour() -> None:
    payload = {
        "result": [
            {"categoryName": "01/05/2026 08:00:00", "locationId": 178, "visitors": 12},
            {"categoryName": "01/05/2026 08:00:00", "locationId": 178, "visitors": 3},
        ]
    }
    counts = parse_visitor_payload(payload, HELSINKI, location_hierarchy_id=178)
    assert list(counts.values()) == [15.0]


@pytest.mark.parametrize("key", ["visitors", "counts", "count", "value"])
def test_visitor_payload_accepts_every_documented_count_key(key: str) -> None:
    payload = {"result": [{"categoryName": "01/05/2026 08:00:00", "locationId": 178, key: 7}]}
    assert list(parse_visitor_payload(payload, HELSINKI).values()) == [7.0]


def test_visitor_payload_rejects_negative_counts() -> None:
    payload = {"result": [{"categoryName": "01/05/2026 08:00:00", "locationId": 178, "visitors": -4}]}
    assert parse_visitor_payload(payload, HELSINKI) == {}


def test_visitor_timestamp_uses_the_documented_format() -> None:
    assert parse_visitor_timestamp("01/05/2026 08:00:00") == datetime(2026, 5, 1, 8, 0)
    assert parse_visitor_timestamp("not a timestamp") is None


def test_visitor_payload_handles_an_empty_result() -> None:
    assert parse_visitor_payload({"result": []}, HELSINKI) == {}
    assert parse_visitor_payload({}, HELSINKI) == {}


# --------------------------------------------------------------------------------------
# Open-Meteo
# --------------------------------------------------------------------------------------


def test_weather_payload_honours_the_reported_offset() -> None:
    payload = load_fixture("openmeteo_archive_venue1.json")
    assert payload["utc_offset_seconds"] == 10800
    parsed = parse_weather_payload(payload, HELSINKI)
    assert len(parsed) == 24
    first = min(parsed)
    assert format_utc(first) == "2026-04-30T21:00:00Z"


def test_weather_payload_ignores_the_label_when_the_offset_disagrees() -> None:
    """A January window still comes back stamped GMT+3, so the label alone lies."""
    payload = {
        "utc_offset_seconds": 10800,
        "hourly": {"time": ["2026-01-01T00:00"], "temperature_2m": [-5.0]},
    }
    parsed = parse_weather_payload(payload, HELSINKI)
    moment = next(iter(parsed))
    assert format_utc(moment) == "2025-12-31T21:00:00Z"
    assert format_local(moment, HELSINKI) == "2025-12-31T23:00:00+02:00"


def test_weather_payload_falls_back_to_zone_rules_without_an_offset() -> None:
    payload = {"hourly": {"time": ["2026-01-01T00:00"], "temperature_2m": [-5.0]}}
    parsed = parse_weather_payload(payload, HELSINKI)
    assert format_utc(next(iter(parsed))) == "2025-12-31T22:00:00Z"


def test_weather_payload_keeps_every_requested_variable() -> None:
    payload = load_fixture("openmeteo_forecast_venue1.json")
    parsed = parse_weather_payload(payload, HELSINKI)
    sample = next(iter(parsed.values()))
    assert {
        "temperature_2m",
        "precipitation",
        "wind_speed_10m",
        "relative_humidity_2m",
        "weathercode",
    } <= set(sample)


def test_weather_offset_rejects_a_non_numeric_field() -> None:
    assert weather_offset({"utc_offset_seconds": "10800"}) is None
    assert weather_offset({}) is None


# --------------------------------------------------------------------------------------
# Eco-Counter
# --------------------------------------------------------------------------------------


def test_ecocounter_payload_keeps_utc_timestamps_as_utc() -> None:
    payloads = load_fixture("ecocounter_raatti_2026-05-01.json")
    counts = parse_ecocounter_payload(payloads["JK_IN"])
    first = min(counts)
    assert format_utc(first) == "2026-04-30T21:00:00Z"
    assert format_local(first, HELSINKI) == "2026-05-01T00:00:00+03:00"


def test_ecocounter_local_time_leads_utc_by_the_seasonal_offset() -> None:
    payloads = load_fixture("ecocounter_raatti_2026-05-01.json")
    for moment in parse_ecocounter_payload(payloads["PP_IN"]):
        local = moment.astimezone(HELSINKI)
        assert local.utcoffset() == timedelta(hours=3)


def test_ecocounter_window_is_inclusive_at_both_ends() -> None:
    payloads = load_fixture("ecocounter_raatti_2026-05-01.json")
    counts = parse_ecocounter_payload(payloads["JK_OUT"])
    assert len(counts) == 25
    assert format_utc(max(counts)) == "2026-05-01T21:00:00Z"


def test_ecocounter_payload_rejects_negative_counts() -> None:
    payload = {"data": {"ecoCounterSiteData": [{"date": "2026-05-01T00:00:00.000Z", "counts": -1}]}}
    assert parse_ecocounter_payload(payload) == {}


def test_ecocounter_payload_handles_an_empty_response() -> None:
    assert parse_ecocounter_payload({"data": {"ecoCounterSiteData": []}}) == {}
    assert parse_ecocounter_payload({"data": None}) == {}


def test_query_inlines_enums_and_quotes_strings() -> None:
    query = build_site_data_query(
        "karjasilta_1", "Oulu_Kapy", "hour", "2026-05-01T00:00:00", "2026-05-22T00:00:00"
    )
    assert 'id: "karjasilta_1"' in query
    assert "domain: Oulu_Kapy" in query
    assert "step: hour" in query
    assert '"Oulu_Kapy"' not in query
    assert "{ date counts }" in query


def test_query_refuses_an_injected_enum() -> None:
    with pytest.raises(ValueError, match="Invalid GraphQL enum"):
        validate_enum("domain", "Oulu_Kapy) { x } mutation {")


def test_ecocounter_timestamp_without_a_marker_is_treated_as_utc() -> None:
    payload = {"data": {"ecoCounterSiteData": [{"date": "2026-05-01T05:00:00", "counts": 3}]}}
    moment = next(iter(parse_ecocounter_payload(payload)))
    assert moment == datetime(2026, 5, 1, 5, 0, tzinfo=UTC)


def test_captured_fixture_covers_all_four_sensors() -> None:
    payloads = load_fixture("ecocounter_raatti_2026-05-01.json")
    assert set(payloads) == {"JK_IN", "JK_OUT", "PP_IN", "PP_OUT"}
    assert date(2026, 5, 1) == min(parse_ecocounter_payload(payloads["JK_IN"])).astimezone(HELSINKI).date()
