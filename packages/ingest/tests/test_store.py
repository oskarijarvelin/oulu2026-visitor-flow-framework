"""Storage behaviour: deterministic writes, manifest stability, config loading."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from ovf_ingest.config import AppConfig, load_config, parse_env_text
from ovf_ingest.store import (
    list_raw_days,
    processed_path,
    read_manifest,
    read_raw_day,
    rejected_path,
    write_manifest,
    write_raw_day,
    write_table,
)


def test_config_loads_the_two_documented_venues(config: AppConfig) -> None:
    assert [venue.venue_id for venue in config.venues] == [1, 2]
    pekuri = config.venue(1)
    assert (pekuri.name, pekuri.city, pekuri.capacity, pekuri.location_hierarchy_id) == (
        "Pekuri",
        "Oulu",
        160,
        178,
    )
    assert (pekuri.latitude, pekuri.longitude) == (65.0120, 25.4688)
    kaupungintalo = config.venue(2)
    assert (
        kaupungintalo.name,
        kaupungintalo.city,
        kaupungintalo.capacity,
        kaupungintalo.location_hierarchy_id,
    ) == ("Kaupungintalo", "Oulu", 20, 183)
    assert (kaupungintalo.latitude, kaupungintalo.longitude) == (65.0140, 25.4726)


def test_config_loads_the_karjasilta_sensor_map(config: AppConfig) -> None:
    site = config.site("raatti")
    assert site.name == "Karjasilta"
    assert site.domain == "Oulu_Kapy"
    assert site.sensors == {
        "JK_IN": "karjasilta_1",
        "JK_OUT": "karjasilta_2",
        "PP_IN": "karjasilta_4",
        "PP_OUT": "karjasilta_3",
    }


def test_selecting_an_unknown_venue_is_an_error(config: AppConfig) -> None:
    with pytest.raises(KeyError):
        config.venue(99)


def test_missing_credentials_are_reported_clearly(config: AppConfig, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JASKARETAIL_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("JASKARETAIL_BASIC_AUTH_PASSWORD", raising=False)
    with pytest.raises(RuntimeError, match="Missing visitor API credentials"):
        _ = config.visitor_credentials


def test_credentials_are_read_from_a_dotenv_file(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("JASKARETAIL_BASIC_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("JASKARETAIL_BASIC_AUTH_PASSWORD", raising=False)
    (repo / ".env").write_text(
        'JASKARETAIL_BASIC_AUTH_USERNAME="alice"\nexport JASKARETAIL_BASIC_AUTH_PASSWORD=secret\n',
        encoding="utf-8",
    )
    assert load_config(repo).visitor_credentials == ("alice", "secret")


def test_env_parsing_tolerates_comments_quotes_and_exports() -> None:
    parsed = parse_env_text('# comment\nexport A="one"\nB=two\n\nBROKEN\n')
    assert parsed == {"A": "one", "B": "two"}


def test_raw_day_files_round_trip_and_are_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "2026-05-01.json"
    payload = {"out": {"result": [2]}, "in": {"result": [1]}}
    write_raw_day(path, payload)
    first = path.read_bytes()
    write_raw_day(path, payload)
    assert path.read_bytes() == first
    assert read_raw_day(path) == payload


def test_raw_day_listing_ignores_unexpected_files(tmp_path: Path) -> None:
    write_raw_day(tmp_path / "2026-05-01.json", {})
    write_raw_day(tmp_path / "2026-05-02.json", {})
    (tmp_path / "notes.json").write_text("{}", encoding="utf-8")
    assert sorted(list_raw_days(tmp_path)) == [date(2026, 5, 1), date(2026, 5, 2)]


def test_tables_are_written_with_lf_endings_and_no_index(tmp_path: Path) -> None:
    frame = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
    path = tmp_path / "table.csv"
    write_table(path, frame)
    assert path.read_bytes() == b"a,b\n1,x\n2,y\n"


def test_a_manifest_that_only_changed_timestamp_is_left_alone(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    base = {"generated_at": "2026-08-23T04:00:00Z", "pipeline": "ingest", "sources": []}
    write_manifest(path, base)
    before = path.read_bytes()
    write_manifest(path, {**base, "generated_at": "2026-08-23T05:00:00Z"})
    assert path.read_bytes() == before


def test_a_manifest_with_real_changes_is_rewritten(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    base = {"generated_at": "2026-08-23T04:00:00Z", "pipeline": "ingest", "sources": []}
    write_manifest(path, base)
    write_manifest(path, {**base, "generated_at": "2026-08-23T05:00:00Z", "sources": [{"name": "x"}]})
    assert read_manifest(path) == {
        "generated_at": "2026-08-23T05:00:00Z",
        "pipeline": "ingest",
        "sources": [{"name": "x"}],
    }


def test_rejected_paths_sit_next_to_the_real_table(config: AppConfig) -> None:
    target = processed_path(config, "visitors_hourly.csv")
    assert rejected_path(target).name == "visitors_hourly.csv.rejected"
    assert rejected_path(target).parent == target.parent


def test_a_partial_write_does_not_replace_a_good_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "table.csv"
    write_table(path, pd.DataFrame({"a": [1]}))
    good = path.read_bytes()

    def explode(*args: object, **kwargs: object) -> str:
        raise OSError("disk full")

    monkeypatch.setattr(pd.DataFrame, "to_csv", explode)
    with pytest.raises(OSError, match="disk full"):
        write_table(path, pd.DataFrame({"a": [2]}))
    assert path.read_bytes() == good
    assert list(tmp_path.glob("*.tmp")) == []


def test_manifest_read_of_broken_json_returns_none(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{not json", encoding="utf-8")
    assert read_manifest(path) is None


def test_written_manifest_is_valid_json_with_a_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    write_manifest(path, {"generated_at": "2026-08-23T04:00:00Z"})
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text)["generated_at"] == "2026-08-23T04:00:00Z"


def test_window_resolution_covers_both_forms(config: AppConfig) -> None:
    from ovf_ingest.cli import resolve_window

    today = date(2026, 5, 21)
    assert resolve_window(config, days_back=7, start=None, end=None, today=today) == (
        date(2026, 5, 14),
        today,
    )
    assert resolve_window(config, days_back=None, start="2026-01-01", end=None, today=today) == (
        date(2026, 1, 1),
        today,
    )
    with pytest.raises(ValueError, match="--end requires --start"):
        resolve_window(config, days_back=None, start=None, end="2026-05-20", today=today)
    with pytest.raises(ValueError, match="must not be after"):
        resolve_window(config, days_back=None, start="2026-06-01", end="2026-05-01", today=today)


def test_chunking_splits_a_long_window(config: AppConfig) -> None:
    from ovf_ingest.cli import chunk_days

    chunks = list(chunk_days(date(2026, 1, 1), date(2026, 3, 1), 31))
    assert chunks[0] == (date(2026, 1, 1), date(2026, 1, 31))
    assert chunks[-1][1] == date(2026, 3, 1)
    assert sum((stop - start).days + 1 for start, stop in chunks) == 60


def test_retry_backs_off_on_server_errors_but_not_client_errors() -> None:
    import requests

    from ovf_ingest.clients import TransientHttpError, request_with_retry
    from ovf_ingest.config import HttpConfig

    http = HttpConfig(timeout_seconds=1, max_attempts=3, backoff_seconds=(0.0, 0.0, 0.0))
    attempts = {"count": 0}

    def server_error() -> requests.Response:
        attempts["count"] += 1
        response = requests.Response()
        response.status_code = 503
        return response

    with pytest.raises(TransientHttpError):
        request_with_retry(server_error, http, source="test", description="boom")
    assert attempts["count"] == 3

    attempts["count"] = 0

    def client_error() -> requests.Response:
        attempts["count"] += 1
        response = requests.Response()
        response.status_code = 404
        response.url = "https://example.invalid"
        return response

    with pytest.raises(requests.HTTPError):
        request_with_retry(client_error, http, source="test", description="boom")
    assert attempts["count"] == 1


def test_retry_recovers_when_a_later_attempt_succeeds() -> None:
    import requests

    from ovf_ingest.clients import request_with_retry
    from ovf_ingest.config import HttpConfig

    http = HttpConfig(timeout_seconds=1, max_attempts=3, backoff_seconds=(0.0, 0.0, 0.0))
    attempts = {"count": 0}

    def flaky() -> requests.Response:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise requests.Timeout("slow")
        response = requests.Response()
        response.status_code = 200
        return response

    assert request_with_retry(flaky, http, source="test", description="ok").status_code == 200
    assert attempts["count"] == 2


def test_backoff_schedule_matches_the_documented_delays(config: AppConfig) -> None:
    assert tuple(config.sources.http.backoff_seconds) == (1.0, 4.0, 16.0)
    assert config.sources.http.max_attempts == 3


def test_hour_grid_length_matches_the_acceptance_criterion() -> None:
    from ovf_ingest.normalize import tz_of, utc_hours_for_local_days

    hours = utc_hours_for_local_days(date(2026, 1, 1), date(2026, 5, 22), tz_of("Europe/Helsinki"))
    assert len(hours) == 3407
    assert hours[-1] + timedelta(hours=1) == datetime(2026, 5, 22, 21, 0, tzinfo=hours[-1].tzinfo)
