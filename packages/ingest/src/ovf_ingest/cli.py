"""Command line entry point and run orchestration.

``run`` fetches, caches and rebuilds; ``climatology`` fetches the long-term weather
normals; ``verify`` re-checks what is already on disk. Exit codes: 0 all good,
1 a quality gate failed, 2 every attempted source failed.
"""

from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from . import LogLevel, __version__, log_event, set_log_level
from .clients.ecocounter import EcoCounterClient
from .clients.jaskaretail import JaskaretailClient
from .clients.openmeteo import ARCHIVE, FORECAST, OpenMeteoClient
from .climatology import run_climatology
from .config import AppConfig, SiteConfig, VenueConfig, load_config
from .normalize import (
    SENSOR_TO_COLUMN,
    TICKETS_DAILY_COLUMNS,
    build_calendar_daily,
    build_traffic_hourly,
    build_visitors_daily,
    build_visitors_hourly,
    build_weather_daily,
    build_weather_hourly,
    empty_table,
    local_date_of,
    local_midnight,
    normalize_tickets,
    parse_ecocounter_payload,
    parse_visitor_payload,
    parse_visitor_timestamp,
    parse_weather_payload,
    tz_of,
    weather_moment,
    weather_offset,
)
from .store import (
    MANIFEST_NAME,
    list_raw_days,
    processed_path,
    raw_day_path,
    raw_dir,
    read_holidays,
    read_manifest,
    read_raw_day,
    read_table,
    read_tickets_csv,
    rejected_path,
    write_manifest,
    write_raw_day,
    write_table,
)
from .strings import message
from .validate import (
    CALENDAR_DAILY,
    TICKETS_DAILY,
    TRAFFIC_HOURLY,
    VISITORS_DAILY,
    VISITORS_HOURLY,
    WEATHER_DAILY,
    WEATHER_HOURLY,
    GateResult,
    SourceReport,
    build_manifest,
    coverage_report,
    run_quality_gates,
    validate_manifest,
)

EXIT_OK = 0
EXIT_GATE_FAILED = 1
EXIT_ALL_SOURCES_FAILED = 2

NETWORK_SOURCES = ("visitors", "weather", "traffic")
ALL_SOURCES = (*NETWORK_SOURCES, "tickets", "calendar")

VISITOR_CHUNK_DAYS = 31
ARCHIVE_CHUNK_DAYS = 366
TRAFFIC_CHUNK_DAYS = 62

# Server-side request timing, not data: keeping it would make every re-run dirty the cache.
VOLATILE_WEATHER_KEYS = frozenset({"hourly", "generationtime_ms"})

STATUS_OK = "ok"
STATUS_DEGRADED = "degraded"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"

TABLE_FILES = {
    VISITORS_HOURLY: "visitors_hourly.csv",
    VISITORS_DAILY: "visitors_daily.csv",
    WEATHER_HOURLY: "weather_hourly.csv",
    WEATHER_DAILY: "weather_daily.csv",
    TRAFFIC_HOURLY: "traffic_hourly.csv",
    TICKETS_DAILY: "tickets_daily.csv",
    CALENDAR_DAILY: "calendar_daily.csv",
}


# --------------------------------------------------------------------------------------
# Windows
# --------------------------------------------------------------------------------------


def resolve_window(
    config: AppConfig,
    *,
    days_back: int | None,
    start: str | None,
    end: str | None,
    today: date,
) -> tuple[date, date]:
    """Resolve the inclusive local day window a run covers."""
    if end and not start:
        raise ValueError("--end requires --start")
    if start:
        first_day = date.fromisoformat(start)
        last_day = date.fromisoformat(end) if end else today
    else:
        window = config.sources.default_days_back if days_back is None else days_back
        if window < 0:
            raise ValueError("--days-back must be zero or greater")
        last_day = today
        first_day = today - timedelta(days=window)
    if first_day > last_day:
        raise ValueError("The start of the window must not be after its end")
    return first_day, last_day


def chunk_days(first_day: date, last_day: date, size: int) -> Iterator[tuple[date, date]]:
    """Split an inclusive day range into chunks of at most ``size`` days."""
    cursor = first_day
    while cursor <= last_day:
        stop = min(cursor + timedelta(days=size - 1), last_day)
        yield cursor, stop
        cursor = stop + timedelta(days=1)


def _iter_days(first_day: date, last_day: date) -> Iterator[date]:
    """Yield every day of an inclusive range."""
    cursor = first_day
    while cursor <= last_day:
        yield cursor
        cursor += timedelta(days=1)


def _window(first_day: date, last_day: date) -> tuple[str, str]:
    """Manifest-shaped window tuple."""
    return first_day.isoformat(), last_day.isoformat()


def _status(succeeded: int, failed: int) -> str:
    """Derive a source status from how many of its units succeeded."""
    if failed and succeeded:
        return STATUS_DEGRADED
    if failed:
        return STATUS_FAILED
    return STATUS_OK


# --------------------------------------------------------------------------------------
# Fetching: raw responses land on disk before anything is normalized
# --------------------------------------------------------------------------------------


def fetch_visitors(
    config: AppConfig,
    venues: Iterable[VenueConfig],
    first_day: date,
    last_day: date,
    session: requests.Session,
) -> SourceReport:
    """Fetch both counting directions per venue and cache them as day files."""
    source_name = config.sources.visitors.name
    client = JaskaretailClient(config, session=session)
    rows = 0
    succeeded = 0
    failed = 0
    errors: list[str] = []
    for venue in venues:
        for chunk_first, chunk_last in chunk_days(first_day, last_day, VISITOR_CHUNK_DAYS):
            try:
                by_type = {
                    counting_type: client.fetch(venue, chunk_first, chunk_last, counting_type)
                    for counting_type in config.sources.visitors.counting_types
                }
            except Exception as exc:
                failed += 1
                errors.append(str(exc))
                log_event(
                    "error",
                    source_name,
                    "Visitor fetch failed",
                    venue_id=venue.venue_id,
                    start=chunk_first.isoformat(),
                    end=chunk_last.isoformat(),
                    error=str(exc),
                )
                continue
            succeeded += 1
            rows += sum(len(_result_rows(payload)) for payload in by_type.values())
            _write_visitor_days(config, venue, chunk_first, chunk_last, by_type)
    return SourceReport(
        name=source_name,
        status=_status(succeeded, failed),
        rows=rows,
        window=_window(first_day, last_day),
        error="; ".join(dict.fromkeys(errors)) or None,
    )


def _result_rows(payload: dict[str, Any]) -> list[Any]:
    """Rows of a visitor payload, tolerating an empty or malformed response."""
    result = payload.get("result")
    return result if isinstance(result, list) else []


def _write_visitor_days(
    config: AppConfig,
    venue: VenueConfig,
    first_day: date,
    last_day: date,
    by_type: dict[str, dict[str, Any]],
) -> None:
    """Split visitor responses into one file per local day, writing empty days too."""
    buckets: dict[date, dict[str, list[Any]]] = {
        day: {counting_type: [] for counting_type in by_type} for day in _iter_days(first_day, last_day)
    }
    for counting_type, payload in by_type.items():
        for row in _result_rows(payload):
            if not isinstance(row, dict):
                continue
            raw = next((row[key] for key in ("categoryName", "timestamp", "date") if key in row), None)
            naive = parse_visitor_timestamp(str(raw)) if raw is not None else None
            if naive is None:
                continue
            bucket = buckets.get(naive.date())
            if bucket is not None:
                bucket[counting_type].append(row)
    for day, rows_by_type in buckets.items():
        payload = {counting_type: {"result": rows} for counting_type, rows in rows_by_type.items()}
        write_raw_day(
            raw_day_path(config, config.sources.visitors.raw_dir, f"venue_{venue.venue_id}", day), payload
        )


def fetch_weather(
    config: AppConfig,
    venues: Iterable[VenueConfig],
    first_day: date,
    last_day: date,
    today: date,
    session: requests.Session,
) -> SourceReport:
    """Fetch history from the archive endpoint and the rest from the forecast endpoint."""
    source_name = config.sources.weather.name
    client = OpenMeteoClient(config, session=session)
    tz = tz_of(config.sources.timezone)
    cutoff = client.archive_cutoff(today)
    rows = 0
    succeeded = 0
    failed = 0
    errors: list[str] = []
    for venue in venues:
        for endpoint, chunk_first, chunk_last in _weather_requests(first_day, last_day, today, cutoff):
            padded_first = chunk_first - timedelta(days=1)
            padded_last = min(chunk_last + timedelta(days=1), cutoff) if endpoint == ARCHIVE else chunk_last
            try:
                if endpoint == ARCHIVE:
                    payload = client.fetch_archive(venue.latitude, venue.longitude, padded_first, padded_last)
                else:
                    payload = client.fetch_forecast(
                        venue.latitude, venue.longitude, padded_first, chunk_last, today
                    )
            except Exception as exc:
                failed += 1
                errors.append(str(exc))
                log_event(
                    "error",
                    source_name,
                    "Weather fetch failed",
                    venue_id=venue.venue_id,
                    endpoint=endpoint,
                    start=chunk_first.isoformat(),
                    end=chunk_last.isoformat(),
                    error=str(exc),
                )
                continue
            succeeded += 1
            written = _write_weather_days(config, venue, endpoint, payload, chunk_first, chunk_last, tz)
            rows += written
    return SourceReport(
        name=source_name,
        status=_status(succeeded, failed),
        rows=rows,
        window=_window(first_day, last_day),
        error="; ".join(dict.fromkeys(errors)) or None,
    )


def _weather_requests(
    first_day: date, last_day: date, today: date, cutoff: date
) -> list[tuple[str, date, date]]:
    """Split a weather window into archive chunks and one forecast request."""
    requests_to_make: list[tuple[str, date, date]] = []
    archive_last = min(last_day, cutoff)
    if archive_last >= first_day:
        requests_to_make.extend(
            (ARCHIVE, chunk_first, chunk_last)
            for chunk_first, chunk_last in chunk_days(first_day, archive_last, ARCHIVE_CHUNK_DAYS)
        )
    forecast_first = max(first_day, cutoff + timedelta(days=1))
    if forecast_first <= last_day:
        requests_to_make.append((FORECAST, forecast_first, max(last_day, today)))
    return requests_to_make


def _write_weather_days(
    config: AppConfig,
    venue: VenueConfig,
    endpoint: str,
    payload: dict[str, Any],
    first_day: date,
    last_day: date,
    tz: ZoneInfo,
) -> int:
    """Split one Open-Meteo response into per-local-day files."""
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        return 0
    times = [str(value) for value in hourly.get("time") or []]
    variables = [key for key in hourly if key != "time"]
    envelope = {
        key: value for key, value in payload.items() if key not in VOLATILE_WEATHER_KEYS
    }
    offset = weather_offset(payload)
    indices_by_day: dict[date, list[int]] = {}
    for index, raw_time in enumerate(times):
        moment = weather_moment(raw_time, offset, tz)
        if moment is None:
            continue
        day = local_date_of(moment, tz)
        if day < first_day or day > last_day:
            continue
        indices_by_day.setdefault(day, []).append(index)
    written = 0
    for day, indices in indices_by_day.items():
        day_hourly: dict[str, Any] = {"time": [times[index] for index in indices]}
        for variable in variables:
            series = hourly.get(variable) or []
            day_hourly[variable] = [series[index] if index < len(series) else None for index in indices]
        slice_payload = {**envelope, "hourly": day_hourly}
        path = raw_day_path(config, config.sources.weather.raw_dir, f"venue_{venue.venue_id}", day)
        write_raw_day(path, {endpoint: slice_payload})
        written += len(indices)
    return written


def fetch_traffic(
    config: AppConfig,
    sites: Iterable[SiteConfig],
    first_day: date,
    last_day: date,
    session: requests.Session,
) -> SourceReport:
    """Fetch every sensor of every site and cache the responses as day files."""
    source_name = config.sources.traffic.name
    client = EcoCounterClient(config, session=session)
    tz = tz_of(config.sources.timezone)
    rows = 0
    succeeded = 0
    failed = 0
    errors: list[str] = []
    for site in sites:
        for chunk_first, chunk_last in chunk_days(first_day, last_day, TRAFFIC_CHUNK_DAYS):
            begin_utc = local_midnight(chunk_first, tz).astimezone(UTC)
            end_utc = local_midnight(chunk_last + timedelta(days=1), tz).astimezone(UTC)
            try:
                by_sensor = {
                    sensor_key: client.fetch_sensor(site, sensor_key, begin_utc, end_utc)
                    for sensor_key in site.sensors
                }
            except Exception as exc:
                failed += 1
                errors.append(str(exc))
                log_event(
                    "error",
                    source_name,
                    "Traffic fetch failed",
                    site_id=site.site_id,
                    start=chunk_first.isoformat(),
                    end=chunk_last.isoformat(),
                    error=str(exc),
                )
                continue
            succeeded += 1
            rows += _write_traffic_days(config, site, by_sensor, chunk_first, chunk_last, tz)
    return SourceReport(
        name=source_name,
        status=_status(succeeded, failed),
        rows=rows,
        window=_window(first_day, last_day),
        error="; ".join(dict.fromkeys(errors)) or None,
    )


def _write_traffic_days(
    config: AppConfig,
    site: SiteConfig,
    by_sensor: dict[str, dict[str, Any]],
    first_day: date,
    last_day: date,
    tz: ZoneInfo,
) -> int:
    """Split Eco-Counter responses into per-local-day files, writing empty days too."""
    buckets: dict[date, dict[str, list[Any]]] = {
        day: {sensor_key: [] for sensor_key in by_sensor} for day in _iter_days(first_day, last_day)
    }
    written = 0
    for sensor_key, payload in by_sensor.items():
        data = payload.get("data")
        rows = data.get("ecoCounterSiteData") if isinstance(data, dict) else None
        for row in rows or []:
            if not isinstance(row, dict):
                continue
            moment = _traffic_moment(row.get("date"))
            if moment is None:
                continue
            bucket = buckets.get(local_date_of(moment, tz))
            if bucket is not None:
                bucket[sensor_key].append(row)
                written += 1
    for day, rows_by_sensor in buckets.items():
        payload_by_sensor = {
            sensor_key: {"data": {"ecoCounterSiteData": rows}} for sensor_key, rows in rows_by_sensor.items()
        }
        write_raw_day(
            raw_day_path(config, config.sources.traffic.raw_dir, site.site_id, day), payload_by_sensor
        )
    return written


def _traffic_moment(raw: Any) -> datetime | None:
    """Parse an Eco-Counter timestamp for day bucketing."""
    if not isinstance(raw, str) or not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


# --------------------------------------------------------------------------------------
# Rebuilding: canonical tables always come from every day file on disk
# --------------------------------------------------------------------------------------


def _venue_key(venue_id: int) -> str:
    """Directory name of one venue in the raw cache."""
    return f"venue_{venue_id}"


def build_visitor_tables(config: AppConfig, tz: ZoneInfo) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rebuild the visitor tables from every cached day file."""
    observations: dict[int, dict[datetime, tuple[float, float]]] = {}
    spans: dict[int, tuple[date, date]] = {}
    for venue in config.venues:
        directory = raw_dir(config, config.sources.visitors.raw_dir, _venue_key(venue.venue_id))
        days = list_raw_days(directory)
        if not days:
            continue
        spans[venue.venue_id] = (min(days), max(days))
        merged_in: dict[datetime, float] = {}
        merged_out: dict[datetime, float] = {}
        for path in days.values():
            payload = read_raw_day(path)
            for counting_type, target in (("in", merged_in), ("out", merged_out)):
                part = payload.get(counting_type)
                if not isinstance(part, dict):
                    continue
                parsed = parse_visitor_payload(part, tz, location_hierarchy_id=venue.location_hierarchy_id)
                for moment, value in parsed.items():
                    target[moment] = target.get(moment, 0.0) + value
        venue_observations: dict[datetime, tuple[float, float]] = {}
        for moment in set(merged_in) | set(merged_out):
            venue_observations[moment] = (merged_in.get(moment, 0.0), merged_out.get(moment, 0.0))
        observations[venue.venue_id] = venue_observations
    hourly = build_visitors_hourly(observations, spans, tz)
    return hourly, build_visitors_daily(hourly)


def build_weather_tables(config: AppConfig, tz: ZoneInfo) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rebuild the weather tables from every cached day file."""
    observations: dict[int, dict[datetime, dict[str, Any]]] = {}
    day_sources: dict[int, dict[date, str]] = {}
    spans: dict[int, tuple[date, date]] = {}
    for venue in config.venues:
        directory = raw_dir(config, config.sources.weather.raw_dir, _venue_key(venue.venue_id))
        days = list_raw_days(directory)
        if not days:
            continue
        spans[venue.venue_id] = (min(days), max(days))
        venue_observations: dict[datetime, dict[str, Any]] = {}
        venue_sources: dict[date, str] = {}
        for day, path in days.items():
            payload = read_raw_day(path)
            for endpoint, response in payload.items():
                if not isinstance(response, dict):
                    continue
                venue_sources[day] = str(endpoint)
                venue_observations.update(parse_weather_payload(response, tz))
        observations[venue.venue_id] = venue_observations
        day_sources[venue.venue_id] = venue_sources
    hourly = build_weather_hourly(observations, day_sources, spans, tz)
    return hourly, build_weather_daily(hourly)


def build_traffic_table(config: AppConfig, tz: ZoneInfo) -> pd.DataFrame:
    """Rebuild the traffic table from every cached day file."""
    observations: dict[str, dict[str, dict[datetime, float]]] = {}
    spans: dict[str, tuple[date, date]] = {}
    site_names = {site.site_id: site.name for site in config.sites}
    for site in config.sites:
        directory = raw_dir(config, config.sources.traffic.raw_dir, site.site_id)
        days = list_raw_days(directory)
        if not days:
            continue
        spans[site.site_id] = (min(days), max(days))
        by_sensor: dict[str, dict[datetime, float]] = {key: {} for key in SENSOR_TO_COLUMN}
        for path in days.values():
            payload = read_raw_day(path)
            for sensor_key, response in payload.items():
                if sensor_key not in by_sensor or not isinstance(response, dict):
                    continue
                by_sensor[sensor_key].update(parse_ecocounter_payload(response))
        observations[site.site_id] = by_sensor
    return build_traffic_hourly(observations, spans, site_names, tz)


def build_tickets_table(config: AppConfig) -> pd.DataFrame:
    """Rebuild the ticket sales table from the maintained CSV files."""
    frames: list[pd.DataFrame] = []
    for venue in config.venues:
        path = config.path(venue.tickets_path)
        raw = read_tickets_csv(path)
        if raw.empty:
            log_event(
                "warning", "tickets", "No ticket file for venue", venue_id=venue.venue_id, path=str(path)
            )
            continue
        frames.append(normalize_tickets(raw, venue.venue_id))
    if not frames:
        return empty_table(TICKETS_DAILY_COLUMNS)
    combined = pd.concat(frames, ignore_index=True)
    return combined.sort_values(["venue_id", "date"]).reset_index(drop=True)


def build_calendar_table(config: AppConfig, tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build the calendar over every local day the other tables touch."""
    days: list[date] = []
    for name in (VISITORS_DAILY, WEATHER_DAILY, TICKETS_DAILY):
        frame = tables.get(name)
        if frame is None or frame.empty:
            continue
        days.extend(date.fromisoformat(str(value)) for value in frame["date"].dropna().unique())
    traffic = tables.get(TRAFFIC_HOURLY)
    if traffic is not None and not traffic.empty:
        local_days = traffic["ts_local"].astype("string").str.slice(0, 10).dropna().unique()
        days.extend(date.fromisoformat(str(value)) for value in local_days)
    if not days:
        return build_calendar_daily(date.today(), date.today(), read_holidays(config))
    return build_calendar_daily(min(days), max(days), read_holidays(config))


def build_all_tables(config: AppConfig) -> dict[str, pd.DataFrame]:
    """Rebuild every canonical table from the raw cache and the maintained inputs."""
    tz = tz_of(config.sources.timezone)
    visitors_hourly, visitors_daily = build_visitor_tables(config, tz)
    weather_hourly, weather_daily = build_weather_tables(config, tz)
    tables: dict[str, pd.DataFrame] = {
        VISITORS_HOURLY: visitors_hourly,
        VISITORS_DAILY: visitors_daily,
        WEATHER_HOURLY: weather_hourly,
        WEATHER_DAILY: weather_daily,
        TRAFFIC_HOURLY: build_traffic_table(config, tz),
        TICKETS_DAILY: build_tickets_table(config),
    }
    tables[CALENDAR_DAILY] = build_calendar_table(config, tables)
    return tables


def load_all_tables(config: AppConfig) -> dict[str, pd.DataFrame]:
    """Read the canonical tables back from disk, for ``verify``."""
    return {name: read_table(processed_path(config, filename)) for name, filename in TABLE_FILES.items()}


def write_tables(config: AppConfig, tables: dict[str, pd.DataFrame], gates: list[GateResult]) -> list[str]:
    """Write each table, diverting the ones a failing gate covers to ``.rejected``."""
    blocked: set[str] = set()
    for gate in gates:
        if not gate.passed:
            blocked.update(gate.tables)
    rejected: list[str] = []
    for name, filename in TABLE_FILES.items():
        frame = tables.get(name)
        if frame is None:
            continue
        target = processed_path(config, filename)
        if name in blocked:
            destination = rejected_path(target)
            write_table(destination, frame)
            rejected.append(str(destination.relative_to(config.root)))
            log_event(
                "error",
                "store",
                "Quality gate failed, previous table left in place",
                table=name,
                rejected_path=str(destination),
            )
            continue
        write_table(target, frame)
    return rejected


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------


def command_run(config: AppConfig, args: argparse.Namespace) -> int:
    """Fetch the selected sources, rebuild every table and write the manifest."""
    today = _today(args)
    first_day, last_day = resolve_window(
        config, days_back=args.days_back, start=args.start, end=args.end, today=today
    )
    selected = _selected_sources(args.source)
    venues = config.select_venues(tuple(args.venue) if args.venue else None)
    log_event(
        "info",
        "run",
        "Starting ingest run",
        start=first_day.isoformat(),
        end=last_day.isoformat(),
        sources=sorted(selected),
        venues=[venue.venue_id for venue in venues],
        version=__version__,
    )
    session = requests.Session()
    reports: list[SourceReport] = []
    if "visitors" in selected:
        reports.append(fetch_visitors(config, venues, first_day, last_day, session))
    else:
        reports.append(SourceReport(config.sources.visitors.name, STATUS_SKIPPED))
    if "weather" in selected:
        weather_last = max(last_day, today + timedelta(days=config.sources.weather.max_forecast_days - 1))
        reports.append(fetch_weather(config, venues, first_day, weather_last, today, session))
    else:
        reports.append(SourceReport(config.sources.weather.name, STATUS_SKIPPED))
    if "traffic" in selected:
        reports.append(fetch_traffic(config, config.sites, first_day, last_day, session))
    else:
        reports.append(SourceReport(config.sources.traffic.name, STATUS_SKIPPED))

    tables = build_all_tables(config)
    reports.append(SourceReport(config.sources.tickets.name, STATUS_OK, rows=len(tables[TICKETS_DAILY])))
    reports.append(SourceReport(config.sources.calendar.name, STATUS_OK, rows=len(tables[CALENDAR_DAILY])))

    gates = run_quality_gates(config, tables)
    rejected = write_tables(config, tables, gates)
    manifest = build_manifest(reports, coverage_report(tables), gates)
    if rejected:
        manifest["quality_gates"]["warnings"].append(
            message("rejected_tables", tables=", ".join(rejected))
        )
    write_manifest(processed_path(config, MANIFEST_NAME), manifest)

    attempted = [report for report in reports if report.name in _network_source_names(config)]
    attempted = [report for report in attempted if report.status != STATUS_SKIPPED]
    if attempted and all(report.status == STATUS_FAILED for report in attempted):
        log_event("error", "run", "Every attempted source failed", sources=[r.name for r in attempted])
        return EXIT_ALL_SOURCES_FAILED
    if not all(gate.passed for gate in gates):
        return EXIT_GATE_FAILED
    log_event("info", "run", "Ingest run finished", rejected_tables=rejected)
    return EXIT_OK


def command_verify(config: AppConfig, _args: argparse.Namespace) -> int:
    """Re-run the quality gates and validate the manifest, without fetching anything."""
    tables = load_all_tables(config)
    missing = [name for name, frame in tables.items() if frame.empty]
    if missing:
        log_event("warning", "verify", "Tables missing or empty", tables=sorted(missing))
    gates = run_quality_gates(config, tables)
    manifest_problems = validate_manifest(read_manifest(processed_path(config, MANIFEST_NAME)))
    for problem in manifest_problems:
        log_event("error", "verify", "Manifest problem", problem=problem)
    passed = all(gate.passed for gate in gates) and not manifest_problems
    log_event("info" if passed else "error", "verify", "Verify finished", passed=passed)
    return EXIT_OK if passed else EXIT_GATE_FAILED


def command_climatology(config: AppConfig, args: argparse.Namespace) -> int:
    """Fetch ten years of hourly history and store per-venue weather normals."""
    first_year, last_year = _parse_years(args.years)
    venues = config.select_venues(tuple(args.venue) if args.venue else None)
    return run_climatology(config, venues, first_year, last_year)


def _parse_years(value: str) -> tuple[int, int]:
    """Parse a ``2016-2025`` style year range."""
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("--years must look like 2016-2025")
    first_year, last_year = int(parts[0]), int(parts[1])
    if first_year > last_year:
        raise ValueError("--years must be given in ascending order")
    return first_year, last_year


def _selected_sources(values: list[str] | None) -> set[str]:
    """Resolve ``--source`` into a set, defaulting to every source."""
    if not values:
        return set(ALL_SOURCES)
    selected: set[str] = set()
    for value in values:
        for part in value.split(","):
            name = part.strip().lower()
            if not name:
                continue
            if name not in ALL_SOURCES:
                raise ValueError(f"Unknown source: {name}. Choose from {', '.join(ALL_SOURCES)}")
            selected.add(name)
    return selected


def _network_source_names(config: AppConfig) -> set[str]:
    """Names the network-backed sources report under."""
    return {
        config.sources.visitors.name,
        config.sources.weather.name,
        config.sources.traffic.name,
    }


def _today(args: argparse.Namespace) -> date:
    """Today in the configured local time zone, overridable for reproducible runs."""
    override = getattr(args, "today", None)
    if override:
        return date.fromisoformat(override)
    return datetime.now(UTC).astimezone(tz_of("Europe/Helsinki")).date()


def build_parser() -> argparse.ArgumentParser:
    """Build the ``python -m ovf_ingest`` argument parser."""
    parser = argparse.ArgumentParser(prog="ovf_ingest", description="Oulu2026 visitor flow ingest")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--log-level", choices=["debug", "info", "warning", "error"], default="info", help="Minimum log level"
    )
    parser.add_argument("--root", type=Path, default=None, help="Repository root (defaults to autodetect)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Fetch, cache and rebuild the canonical tables")
    run_parser.add_argument("--days-back", type=int, default=None, help="Incremental window length in days")
    run_parser.add_argument("--start", default=None, help="First local day, YYYY-MM-DD")
    run_parser.add_argument("--end", default=None, help="Last local day, YYYY-MM-DD (requires --start)")
    run_parser.add_argument(
        "--source",
        action="append",
        default=None,
        help=f"Limit fetching to one source: {', '.join(ALL_SOURCES)}",
    )
    run_parser.add_argument(
        "--venue", action="append", type=int, default=None, help="Limit fetching to one venue"
    )
    run_parser.add_argument("--today", default=None, help="Override today's date, for reproducible runs")
    run_parser.set_defaults(handler=command_run)

    climatology_parser = subparsers.add_parser("climatology", help="Fetch long-term weather normals")
    climatology_parser.add_argument(
        "--years", default="2016-2025", help="Inclusive year range, e.g. 2016-2025"
    )
    climatology_parser.add_argument(
        "--venue", action="append", type=int, default=None, help="Limit to one venue"
    )
    climatology_parser.set_defaults(handler=command_climatology)

    verify_parser = subparsers.add_parser("verify", help="Run the quality gates against data/processed")
    verify_parser.set_defaults(handler=command_verify)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m ovf_ingest``."""
    parser = build_parser()
    args = parser.parse_args(argv)
    level: LogLevel = args.log_level
    set_log_level(level)
    try:
        config = load_config(args.root)
        handler = args.handler
        return int(handler(config, args))
    except KeyboardInterrupt:
        log_event("error", "cli", "Interrupted")
        return EXIT_ALL_SOURCES_FAILED
    except Exception as exc:
        log_event("error", "cli", "Run failed", error=str(exc), error_type=type(exc).__name__)
        return EXIT_ALL_SOURCES_FAILED
