"""End-to-end runs against offline clients: idempotency, manifest, partial failure."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from ovf_ingest.cli import EXIT_ALL_SOURCES_FAILED, EXIT_GATE_FAILED, EXIT_OK, main
from ovf_ingest.validate import validate_manifest
from support import TICKETS_CSV_FINNISH, FakeEcoCounter, FakeJaskaretail, FakeOpenMeteo

RUN_ARGS = ["run", "--start", "2026-05-01", "--end", "2026-05-20", "--today", "2026-05-21"]
PROCESSED = (
    "visitors_hourly.csv",
    "visitors_daily.csv",
    "weather_hourly.csv",
    "weather_daily.csv",
    "traffic_hourly.csv",
    "tickets_daily.csv",
    "calendar_daily.csv",
)


def run(repo: Path, *extra: str) -> int:
    """Run the CLI against a throwaway repository root."""
    return main(["--root", str(repo), *RUN_ARGS, *extra])


def snapshot(repo: Path) -> dict[str, bytes]:
    """Byte-level snapshot of every file the pipeline writes."""
    root = repo / "data"
    return {
        str(path.relative_to(repo)): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()
    }


def manifest_of(repo: Path) -> dict[str, Any]:
    text = (repo / "data" / "processed" / "manifest.json").read_text(encoding="utf-8")
    manifest: dict[str, Any] = json.loads(text)
    return manifest


# --------------------------------------------------------------------------------------
# Idempotency
# --------------------------------------------------------------------------------------


def test_running_twice_produces_identical_files(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert run(repo) == EXIT_OK
    first = snapshot(repo)
    assert run(repo) == EXIT_OK
    second = snapshot(repo)
    assert set(first) == set(second)
    differing = [name for name in first if first[name] != second[name]]
    assert differing == []


def test_a_narrower_rerun_keeps_the_wider_history(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    """Canonical tables are rebuilt from every day file, not just the fetched window."""
    assert run(repo) == EXIT_OK
    rows_after_full = len((repo / "data" / "processed" / "visitors_hourly.csv").read_text().splitlines())
    assert (
        main(
            [
                "--root",
                str(repo),
                "run",
                "--start",
                "2026-05-19",
                "--end",
                "2026-05-20",
                "--today",
                "2026-05-21",
            ]
        )
        == EXIT_OK
    )
    rows_after_narrow = len((repo / "data" / "processed" / "visitors_hourly.csv").read_text().splitlines())
    assert rows_after_narrow == rows_after_full


def test_the_raw_cache_holds_one_file_per_source_and_day(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    assert run(repo) == EXIT_OK
    visitors = sorted((repo / "data" / "raw" / "visitors" / "venue_1").glob("*.json"))
    assert len(visitors) == 20
    assert visitors[0].name == "2026-05-01.json"
    payload = json.loads(visitors[0].read_text(encoding="utf-8"))
    assert set(payload) == {"in", "out"}
    assert len(payload["in"]["result"]) == 24
    assert sorted((repo / "data" / "raw" / "traffic" / "raatti").glob("*.json"))[0].name == "2026-05-01.json"


# --------------------------------------------------------------------------------------
# Canonical tables
# --------------------------------------------------------------------------------------


def test_the_expected_tables_are_written(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert run(repo) == EXIT_OK
    processed = repo / "data" / "processed"
    for name in PROCESSED:
        assert (processed / name).is_file(), name
    assert (processed / "manifest.json").is_file()


def test_hourly_tables_carry_both_timestamp_columns(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert run(repo) == EXIT_OK
    for name in ("visitors_hourly.csv", "weather_hourly.csv", "traffic_hourly.csv"):
        header = (repo / "data" / "processed" / name).read_text(encoding="utf-8").splitlines()[0]
        assert "ts_utc" in header and "ts_local" in header


def test_traffic_and_visitors_agree_on_the_same_hour(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    """The join key has to line up across sources, which is the whole point of ts_utc."""
    import pandas as pd

    assert run(repo) == EXIT_OK
    processed = repo / "data" / "processed"
    visitors = pd.read_csv(processed / "visitors_hourly.csv")
    traffic = pd.read_csv(processed / "traffic_hourly.csv")
    merged = visitors[visitors["venue_id"] == 1].merge(traffic, on="ts_utc", suffixes=("_v", "_t"))
    assert len(merged) == len(traffic)
    assert (merged["ts_local_v"] == merged["ts_local_t"]).all()


def test_weather_rows_are_labelled_with_their_endpoint(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    import pandas as pd

    assert run(repo) == EXIT_OK
    weather = pd.read_csv(repo / "data" / "processed" / "weather_hourly.csv")
    assert set(weather["source"].dropna().unique()) <= {"archive", "forecast"}


def test_finnish_ticket_headers_are_accepted(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    import pandas as pd

    path = repo / "data" / "raw" / "tickets" / "venue_2" / "tickets-venue-2.csv"
    path.write_text(TICKETS_CSV_FINNISH.replace(";", ","), encoding="utf-8")
    assert run(repo) == EXIT_OK
    tickets = pd.read_csv(repo / "data" / "processed" / "tickets_daily.csv")
    venue_2 = tickets[tickets["venue_id"] == 2]
    assert list(venue_2["date"]) == ["2026-01-14", "2026-01-15"]
    assert list(venue_2["tickets_total"]) == [386, 33]


# --------------------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------------------


def test_the_manifest_has_the_documented_shape(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert run(repo) == EXIT_OK
    manifest = manifest_of(repo)
    assert validate_manifest(manifest) == []
    assert manifest["pipeline"] == "ingest"
    assert manifest["generated_at"].endswith("Z")
    names = {source["name"] for source in manifest["sources"]}
    assert {"jaskaretail", "open-meteo", "eco-counter", "tickets", "calendar"} <= names
    for source in manifest["sources"]:
        assert source["status"] in {"ok", "degraded", "failed", "skipped"}
    assert manifest["quality_gates"]["passed"] is True
    assert manifest["coverage"]["visitors_hourly"]["first"] == "2026-04-30T21:00:00Z"


def test_the_manifest_reports_windows_for_fetched_sources(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    assert run(repo) == EXIT_OK
    by_name = {source["name"]: source for source in manifest_of(repo)["sources"]}
    assert by_name["jaskaretail"]["window"] == ["2026-05-01", "2026-05-20"]
    assert by_name["jaskaretail"]["rows"] > 0


def test_a_manifest_missing_keys_is_reported_as_invalid() -> None:
    assert validate_manifest(None) == ["manifest.json is missing or unreadable"]
    problems = validate_manifest({"pipeline": "ingest"})
    assert any("generated_at" in problem for problem in problems)


# --------------------------------------------------------------------------------------
# Partial failure and exit codes
# --------------------------------------------------------------------------------------


def test_an_eco_counter_outage_degrades_but_does_not_stop_the_run(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    FakeEcoCounter.fail = True
    assert run(repo) == EXIT_OK
    by_name = {source["name"]: source for source in manifest_of(repo)["sources"]}
    assert by_name["eco-counter"]["status"] == "failed"
    assert by_name["jaskaretail"]["status"] == "ok"
    assert (repo / "data" / "processed" / "visitors_hourly.csv").is_file()
    warnings = manifest_of(repo)["quality_gates"]["warnings"]
    assert any("eco-counter" in warning["fi"] for warning in warnings)
    assert any("eco-counter" in warning["en"] for warning in warnings)


def test_one_failing_venue_leaves_the_source_degraded(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    FakeJaskaretail.fail_venues = {2}
    assert run(repo) == EXIT_OK
    by_name = {source["name"]: source for source in manifest_of(repo)["sources"]}
    assert by_name["jaskaretail"]["status"] == "degraded"


def test_every_source_failing_exits_with_two(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    FakeJaskaretail.fail_venues = {1, 2}
    FakeOpenMeteo.fail = True
    FakeEcoCounter.fail = True
    assert run(repo) == EXIT_ALL_SOURCES_FAILED


def test_a_skipped_source_is_reported_but_not_counted_as_a_failure(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    assert run(repo, "--source", "weather") == EXIT_OK
    by_name = {source["name"]: source for source in manifest_of(repo)["sources"]}
    assert by_name["jaskaretail"]["status"] == "skipped"
    assert by_name["open-meteo"]["status"] == "ok"


# --------------------------------------------------------------------------------------
# Quality gate failure diverts to .rejected
# --------------------------------------------------------------------------------------


def test_a_failing_gate_writes_rejected_and_keeps_the_previous_table(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    assert run(repo) == EXIT_OK
    good = (repo / "data" / "processed" / "visitors_hourly.csv").read_bytes()

    FakeJaskaretail.counts = {
        (1, direction, f"{day:02d}/05/2026 {hour:02d}:00:00"): 400
        for direction in ("in", "out")
        for day in range(1, 21)
        for hour in range(24)
    }
    assert run(repo) == EXIT_GATE_FAILED
    processed = repo / "data" / "processed"
    assert (processed / "visitors_hourly.csv.rejected").is_file()
    assert (processed / "visitors_hourly.csv").read_bytes() == good
    manifest = manifest_of(repo)
    assert manifest["quality_gates"]["passed"] is False
    warnings = manifest["quality_gates"]["warnings"]
    assert any("daily_capacity" in warning["en"] for warning in warnings)
    assert any("rejected tables" in warning["en"] for warning in warnings)
    assert any("Hylätyt taulut" in warning["fi"] for warning in warnings)


def test_unaffected_tables_are_still_written_when_a_gate_fails(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    FakeJaskaretail.counts = {
        (1, direction, f"{day:02d}/05/2026 {hour:02d}:00:00"): 400
        for direction in ("in", "out")
        for day in range(1, 21)
        for hour in range(24)
    }
    assert run(repo) == EXIT_GATE_FAILED
    assert (repo / "data" / "processed" / "weather_hourly.csv").is_file()
    assert not (repo / "data" / "processed" / "weather_hourly.csv.rejected").exists()


# --------------------------------------------------------------------------------------
# verify
# --------------------------------------------------------------------------------------


def test_verify_passes_after_a_clean_run(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert run(repo) == EXIT_OK
    assert main(["--root", str(repo), "verify"]) == EXIT_OK


def test_verify_fails_without_a_manifest(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert run(repo) == EXIT_OK
    (repo / "data" / "processed" / "manifest.json").unlink()
    assert main(["--root", str(repo), "verify"]) == EXIT_GATE_FAILED


# --------------------------------------------------------------------------------------
# Argument handling
# --------------------------------------------------------------------------------------


def test_end_without_start_is_rejected(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert main(["--root", str(repo), "run", "--end", "2026-05-20"]) == EXIT_ALL_SOURCES_FAILED


def test_an_unknown_source_is_rejected(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert main(["--root", str(repo), "run", "--source", "nonsense"]) == EXIT_ALL_SOURCES_FAILED


def test_days_back_defaults_to_the_configured_window(repo: Path, fake_clients: type[FakeJaskaretail]) -> None:
    assert main(["--root", str(repo), "run", "--today", "2026-05-21", "--source", "visitors"]) == EXIT_OK
    days = sorted(path.stem for path in (repo / "data" / "raw" / "visitors" / "venue_1").glob("*.json"))
    assert days == [f"2026-05-{day:02d}" for day in range(14, 22)]


@pytest.mark.parametrize("argv", [["--version"], ["run", "--help"]])
def test_informational_flags_exit_cleanly(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(argv)
    assert exit_info.value.code == 0


def test_a_day_the_api_answers_nothing_for_becomes_imputed_rows(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    """An empty day still gets a day file, so the hole shows up as is_imputed."""
    from datetime import date as date_type

    import pandas as pd

    FakeJaskaretail.missing_days = {date_type(2026, 5, 10)}
    assert run(repo) == EXIT_OK
    assert (repo / "data" / "raw" / "visitors" / "venue_1" / "2026-05-10.json").is_file()
    hourly = pd.read_csv(repo / "data" / "processed" / "visitors_hourly.csv")
    day = hourly[(hourly["venue_id"] == 1) & hourly["ts_local"].str.startswith("2026-05-10")]
    assert len(day) == 24
    assert day["is_imputed"].all()
    assert (day["visitors_total"] == 0).all()

    daily = pd.read_csv(repo / "data" / "processed" / "visitors_daily.csv")
    row = daily[(daily["venue_id"] == 1) & (daily["date"] == "2026-05-10")].iloc[0]
    assert row["observed_hours"] == 0
    assert bool(row["is_complete"]) is False


def test_raw_weather_files_drop_the_per_request_timing_field(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    """generationtime_ms varies per request and would dirty the cache on every re-run."""
    from ovf_ingest.cli import VOLATILE_WEATHER_KEYS

    assert "generationtime_ms" in VOLATILE_WEATHER_KEYS
    assert run(repo) == EXIT_OK
    payload = json.loads(
        (repo / "data" / "raw" / "weather" / "venue_1" / "2026-05-10.json").read_text(encoding="utf-8")
    )
    response = next(iter(payload.values()))
    assert "generationtime_ms" not in response
    assert "utc_offset_seconds" in response
    assert len(response["hourly"]["time"]) == 24


def test_fetching_one_venue_leaves_the_other_venues_tables_intact(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    import pandas as pd

    assert run(repo) == EXIT_OK
    before = pd.read_csv(repo / "data" / "processed" / "visitors_hourly.csv")
    assert set(before["venue_id"]) == {1, 2}
    assert main(["--root", str(repo), *RUN_ARGS, "--source", "visitors", "--venue", "1"]) == EXIT_OK
    after = pd.read_csv(repo / "data" / "processed" / "visitors_hourly.csv")
    assert set(after["venue_id"]) == {1, 2}
    assert len(after) == len(before)


def test_a_hole_between_two_fetched_windows_becomes_visible_and_trips_the_gate(
    repo: Path, fake_clients: type[FakeJaskaretail]
) -> None:
    """Days that were never fetched are densified as is_imputed, not silently skipped.

    A dense series with a labelled hole is what downstream modelling needs; a series
    that simply omits the missing days would hide the gap from every consumer.
    """
    import pandas as pd

    assert run(repo) == EXIT_OK
    assert (
        main(
            [
                "--root",
                str(repo),
                "run",
                "--start",
                "2026-07-01",
                "--end",
                "2026-07-05",
                "--today",
                "2026-07-06",
            ]
        )
        == EXIT_GATE_FAILED
    )
    rejected = repo / "data" / "processed" / "visitors_hourly.csv.rejected"
    hourly = pd.read_csv(rejected)
    hole = hourly[(hourly["venue_id"] == 1) & hourly["ts_local"].str.startswith("2026-06-15")]
    assert len(hole) == 24
    assert hole["is_imputed"].all()

    manifest = manifest_of(repo)
    assert manifest["quality_gates"]["passed"] is False
    assert any(
        "visitor_gap" in warning["en"] for warning in manifest["quality_gates"]["warnings"]
    )
    assert manifest["coverage"]["visitors_hourly"]["missing_hours"] > 48
