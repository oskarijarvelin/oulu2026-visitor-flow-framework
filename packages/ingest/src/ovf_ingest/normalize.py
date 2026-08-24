"""Time zone contract, payload parsing and the canonical table builders.

The single most important rule in this package lives here: every timestamped row
carries both ``ts_utc`` (the join key) and ``ts_local`` (what a user sees), and the
conversion between them always goes through :mod:`zoneinfo`, never a fixed offset.
Daily rows are keyed on ``date``, which is always the *local* calendar day.
"""

from __future__ import annotations

import math
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from datetime import timezone as dt_timezone
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from . import log_event

UTC = UTC
ONE_HOUR = timedelta(hours=1)

VISITOR_TIMESTAMP_FORMAT = "%d/%m/%Y %H:%M:%S"
VISITOR_TIMESTAMP_KEYS = ("categoryName", "timestamp", "date")
VISITOR_COUNT_KEYS = ("visitors", "counts", "count", "value")
TICKET_DATE_FORMATS = ("%d.%m.%Y", "%Y-%m-%d")

WEATHER_CODES: dict[int, str] = {
    0: "clear",
    1: "mainly_clear",
    2: "partly_cloudy",
    3: "overcast",
    45: "fog",
    48: "depositing_rime_fog",
    51: "light_drizzle",
    53: "moderate_drizzle",
    55: "dense_drizzle",
    56: "light_freezing_drizzle",
    57: "dense_freezing_drizzle",
    61: "slight_rain",
    63: "moderate_rain",
    65: "heavy_rain",
    66: "light_freezing_rain",
    67: "heavy_freezing_rain",
    71: "slight_snow_fall",
    73: "moderate_snow_fall",
    75: "heavy_snow_fall",
    77: "snow_grains",
    80: "slight_rain_showers",
    81: "moderate_rain_showers",
    82: "violent_rain_showers",
    85: "slight_snow_showers",
    86: "heavy_snow_showers",
    95: "thunderstorm",
    96: "thunderstorm_with_slight_hail",
    99: "thunderstorm_with_heavy_hail",
}

VISITORS_HOURLY_COLUMNS = [
    "venue_id",
    "ts_utc",
    "ts_local",
    "visitors_in",
    "visitors_out",
    "visitors_total",
    "is_imputed",
]
VISITORS_DAILY_COLUMNS = [
    "venue_id",
    "date",
    "visitors_in",
    "visitors_out",
    "visitors_total",
    "observed_hours",
    "is_complete",
]
WEATHER_HOURLY_COLUMNS = [
    "venue_id",
    "ts_utc",
    "ts_local",
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "relative_humidity_2m",
    "weathercode",
    "weathercode_str",
    "is_precipitation",
    "is_cold",
    "is_windy",
    "source",
]
WEATHER_DAILY_COLUMNS = [
    "venue_id",
    "date",
    "temp_mean",
    "temp_min",
    "temp_max",
    "precip_sum",
    "precip_hours",
    "wind_mean",
    "weathercode_mode",
    "weathercode_str",
    "source",
]
TRAFFIC_HOURLY_COLUMNS = [
    "site_id",
    "site_name",
    "ts_utc",
    "ts_local",
    "jk_in",
    "jk_out",
    "pp_in",
    "pp_out",
]
TICKETS_DAILY_COLUMNS = ["venue_id", "date", "tickets_sold", "groups_sold", "tickets_total"]
CALENDAR_DAILY_COLUMNS = [
    "date",
    "holiday_name",
    "is_holiday",
    "is_weekend",
    "day_of_week",
    "days_before_next_holiday",
    "is_last_workday_before_holiday",
    "week_of_year",
    "month",
    "year",
]

SENSOR_TO_COLUMN = {"JK_IN": "jk_in", "JK_OUT": "jk_out", "PP_IN": "pp_in", "PP_OUT": "pp_out"}
TRAFFIC_COUNT_COLUMNS = ["jk_in", "jk_out", "pp_in", "pp_out"]
NO_HOLIDAY_SENTINEL = 999
SOURCE_PRIORITY = {"archive": 0, "forecast": 1, "climatology": 2}


# --------------------------------------------------------------------------------------
# Time zone contract
# --------------------------------------------------------------------------------------


def tz_of(name: str) -> ZoneInfo:
    """Return the tzdata zone for a configured time zone name."""
    return ZoneInfo(name)


def format_utc(moment: datetime) -> str:
    """Format an aware datetime as ``2026-05-22T04:00:00Z``."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def format_local(moment: datetime, tz: ZoneInfo) -> str:
    """Format an aware datetime as ``2026-05-22T07:00:00+03:00``."""
    return moment.astimezone(tz).isoformat()


def local_midnight(day: date, tz: ZoneInfo) -> datetime:
    """Return the aware datetime for local midnight on ``day``.

    Helsinki never transitions at midnight, so this is always unambiguous.
    """
    return datetime(day.year, day.month, day.day, tzinfo=tz)


def localize_naive(naive: datetime, tz: ZoneInfo) -> datetime | None:
    """Attach ``tz`` to a naive local timestamp.

    Returns ``None`` for local times that do not exist (the hour skipped by the
    spring-forward transition). Ambiguous times during the autumn transition
    resolve to the first, still-DST occurrence.
    """
    attached = naive.replace(tzinfo=tz)
    round_trip = attached.astimezone(UTC).astimezone(tz).replace(tzinfo=None)
    if round_trip != naive:
        return None
    return attached


def local_date_of(moment: datetime, tz: ZoneInfo) -> date:
    """Return the local calendar day an instant belongs to."""
    return moment.astimezone(tz).date()


def utc_hours_for_local_days(first_day: date, last_day: date, tz: ZoneInfo) -> list[datetime]:
    """List every hour of the inclusive local day range, as aware UTC instants.

    The grid is stepped in UTC, so a spring-forward day yields 23 rows and an
    autumn day yields 25. That is the contract, not a bug.
    """
    if last_day < first_day:
        return []
    cursor = local_midnight(first_day, tz).astimezone(UTC)
    stop = local_midnight(last_day + timedelta(days=1), tz).astimezone(UTC)
    hours: list[datetime] = []
    while cursor < stop:
        hours.append(cursor)
        cursor += ONE_HOUR
    return hours


def iter_days(first_day: date, last_day: date) -> Iterator[date]:
    """Yield every calendar day in the inclusive range."""
    cursor = first_day
    while cursor <= last_day:
        yield cursor
        cursor += timedelta(days=1)


def as_int(value: Any) -> int:
    """Coerce a pandas scalar or group key to ``int``."""
    return int(value)


def decode_weathercode(code: Any) -> str:
    """Map a WMO weather code to its textual name."""
    try:
        if code is None or (isinstance(code, float) and math.isnan(code)):
            return "unknown"
        return WEATHER_CODES.get(int(code), "unknown")
    except (TypeError, ValueError):
        return "unknown"


# --------------------------------------------------------------------------------------
# Payload parsing
# --------------------------------------------------------------------------------------


def _extract_numeric(value: Any) -> float | None:
    """Pull one numeric scalar out of a possibly nested API value."""
    if isinstance(value, dict):
        for key in VISITOR_COUNT_KEYS:
            if key in value:
                return _extract_numeric(value[key])
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            extracted = _extract_numeric(item)
            if extracted is not None:
                return extracted
        return None
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_visitor_payload(
    payload: dict[str, Any],
    tz: ZoneInfo,
    *,
    location_hierarchy_id: int | None = None,
) -> dict[datetime, float]:
    """Parse one Jaskaretail response into ``{utc_hour: count}``.

    Rows are summed per hour. Timestamps are naive local time in
    ``%d/%m/%Y %H:%M:%S``; local times that do not exist are dropped with a warning.
    Negative counts are rejected and logged (quality gate 3).
    """
    result = payload.get("result")
    if not isinstance(result, list):
        return {}
    counts: dict[datetime, float] = {}
    skipped_timestamps = 0
    negative_rows = 0
    for row in result:
        if not isinstance(row, dict):
            continue
        raw_timestamp = next((row[key] for key in VISITOR_TIMESTAMP_KEYS if key in row), None)
        if raw_timestamp is None:
            continue
        naive = parse_visitor_timestamp(str(raw_timestamp))
        if naive is None:
            skipped_timestamps += 1
            continue
        moment = localize_naive(naive, tz)
        if moment is None:
            skipped_timestamps += 1
            continue
        if location_hierarchy_id is not None and "locationId" in row:
            location = _extract_numeric(row["locationId"])
            if location is not None and int(location) != location_hierarchy_id:
                continue
        value = _extract_numeric(next((row[key] for key in VISITOR_COUNT_KEYS if key in row), None))
        if value is None:
            continue
        if value < 0:
            negative_rows += 1
            continue
        moment_utc = moment.astimezone(UTC)
        counts[moment_utc] = counts.get(moment_utc, 0.0) + value
    if skipped_timestamps:
        log_event(
            "warning",
            "jaskaretail",
            "Dropped rows with unparseable or non-existent local timestamps",
            rows=skipped_timestamps,
        )
    if negative_rows:
        log_event("warning", "jaskaretail", "Rejected negative visitor counts", rows=negative_rows)
    return counts


def parse_visitor_timestamp(raw: str) -> datetime | None:
    """Parse a visitor API timestamp using the documented format only."""
    try:
        return datetime.strptime(raw, VISITOR_TIMESTAMP_FORMAT)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is None else None


def weather_offset(payload: dict[str, Any]) -> dt_timezone | None:
    """The fixed offset Open-Meteo says it applied to ``hourly.time``.

    Open-Meteo answers a ``timezone=Europe/Helsinki`` request with one constant
    offset for the whole range rather than real wall-clock time: a January window
    still comes back stamped ``GMT+3``. Its own ``utc_offset_seconds`` field is
    therefore the authority on what the labels mean, and honouring it is what keeps
    winter weather from landing an hour late.
    """
    offset = payload.get("utc_offset_seconds")
    if isinstance(offset, bool) or not isinstance(offset, (int, float)):
        return None
    return dt_timezone(timedelta(seconds=int(offset)))


def weather_moment(raw_time: str, offset: dt_timezone | None, tz: ZoneInfo) -> datetime | None:
    """Convert one Open-Meteo hourly label into an aware UTC instant."""
    try:
        naive = datetime.fromisoformat(raw_time)
    except ValueError:
        return None
    if naive.tzinfo is not None:
        return naive.astimezone(UTC)
    if offset is not None:
        return naive.replace(tzinfo=offset).astimezone(UTC)
    localized = localize_naive(naive, tz)
    return localized.astimezone(UTC) if localized is not None else None


def parse_weather_payload(payload: dict[str, Any], tz: ZoneInfo) -> dict[datetime, dict[str, Any]]:
    """Parse one Open-Meteo response into ``{utc_hour: {variable: value}}``."""
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        return {}
    times = hourly.get("time") or []
    variables = [key for key in hourly if key != "time"]
    offset = weather_offset(payload)
    parsed: dict[datetime, dict[str, Any]] = {}
    skipped = 0
    for index, raw_time in enumerate(times):
        moment = weather_moment(str(raw_time), offset, tz)
        if moment is None:
            skipped += 1
            continue
        row: dict[str, Any] = {}
        for variable in variables:
            series = hourly.get(variable) or []
            row[variable] = series[index] if index < len(series) else None
        parsed[moment] = row
    if skipped:
        log_event("warning", "open-meteo", "Dropped unparseable hourly timestamps", rows=skipped)
    return parsed


def parse_ecocounter_payload(payload: dict[str, Any]) -> dict[datetime, float]:
    """Parse one Eco-Counter GraphQL response into ``{utc_hour: count}``.

    Eco-Counter is the only source that already answers in UTC. The reference
    implementation stripped the ``+00:00`` marker without converting, which shifted
    every traffic row two or three hours; here the offset is honoured.
    """
    data = payload.get("data")
    rows = data.get("ecoCounterSiteData") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return {}
    counts: dict[datetime, float] = {}
    negative_rows = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        moment = _parse_ecocounter_timestamp(row.get("date"))
        if moment is None:
            continue
        value = _extract_numeric(row.get("counts"))
        if value is None:
            continue
        if value < 0:
            negative_rows += 1
            continue
        counts[moment] = counts.get(moment, 0.0) + value
    if negative_rows:
        log_event("warning", "eco-counter", "Rejected negative traffic counts", rows=negative_rows)
    return counts


def _parse_ecocounter_timestamp(raw: Any) -> datetime | None:
    """Parse an Eco-Counter ISO 8601 timestamp, which carries an explicit UTC marker."""
    if not isinstance(raw, str) or not raw:
        return None
    text = raw.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


# --------------------------------------------------------------------------------------
# Canonical table builders
# --------------------------------------------------------------------------------------


def empty_table(columns: list[str]) -> pd.DataFrame:
    """Return an empty frame with the canonical column order."""
    return pd.DataFrame({column: pd.Series(dtype="object") for column in columns})


def build_visitors_hourly(
    observations: dict[int, dict[datetime, tuple[float, float]]],
    spans: dict[int, tuple[date, date]],
    tz: ZoneInfo,
) -> pd.DataFrame:
    """Densify per-venue visitor observations onto the full local-day hour grid.

    Hours the API did not answer for are kept as zero rows flagged ``is_imputed``,
    so a genuine zero and a missing hour stay distinguishable.
    """
    frames: list[pd.DataFrame] = []
    for venue_id in sorted(spans):
        first_day, last_day = spans[venue_id]
        hours = utc_hours_for_local_days(first_day, last_day, tz)
        if not hours:
            continue
        venue_observations = observations.get(venue_id, {})
        records: list[dict[str, Any]] = []
        for moment in hours:
            observed = venue_observations.get(moment)
            visitors_in, visitors_out = observed if observed is not None else (0.0, 0.0)
            records.append(
                {
                    "venue_id": venue_id,
                    "ts_utc": format_utc(moment),
                    "ts_local": format_local(moment, tz),
                    "visitors_in": visitors_in,
                    "visitors_out": visitors_out,
                    "visitors_total": visitors_in + visitors_out,
                    "is_imputed": observed is None,
                }
            )
        frames.append(pd.DataFrame.from_records(records))
    if not frames:
        return empty_table(VISITORS_HOURLY_COLUMNS)
    frame = pd.concat(frames, ignore_index=True)
    for column in ("visitors_in", "visitors_out", "visitors_total"):
        frame[column] = to_counts(frame[column])
    frame["venue_id"] = frame["venue_id"].astype("int64")
    frame["is_imputed"] = frame["is_imputed"].astype("boolean")
    return frame[VISITORS_HOURLY_COLUMNS].reset_index(drop=True)


def to_counts(series: pd.Series) -> pd.Series:
    """Coerce a count column to nullable integers, warning about fractional input."""
    numeric = pd.to_numeric(series, errors="coerce")
    present = numeric.dropna()
    if len(present) and not bool((present % 1 == 0).all()):
        log_event("warning", "normalize", "Rounding fractional counts to integers")
    return numeric.round().astype("Int64")


def build_visitors_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly visitors to local calendar days."""
    if hourly.empty:
        return empty_table(VISITORS_DAILY_COLUMNS)
    frame = hourly.copy()
    frame["date"] = local_dates(frame["ts_local"])
    frame["observed"] = (~frame["is_imputed"].astype("boolean").fillna(False)).astype("int64")
    grouped = frame.groupby(["venue_id", "date"], as_index=False).agg(
        visitors_in=("visitors_in", "sum"),
        visitors_out=("visitors_out", "sum"),
        visitors_total=("visitors_total", "sum"),
        observed_hours=("observed", "sum"),
        expected_hours=("observed", "size"),
    )
    grouped["is_complete"] = (grouped["observed_hours"] == grouped["expected_hours"]).astype("boolean")
    for column in ("visitors_in", "visitors_out", "visitors_total", "observed_hours"):
        grouped[column] = grouped[column].astype("Int64")
    grouped = grouped.sort_values(["venue_id", "date"]).reset_index(drop=True)
    return grouped[VISITORS_DAILY_COLUMNS]


def local_dates(ts_local: pd.Series) -> pd.Series:
    """Take the calendar day out of an ISO local timestamp without re-parsing it."""
    return ts_local.astype("string").str.slice(0, 10)


def build_weather_hourly(
    observations: dict[int, dict[datetime, dict[str, Any]]],
    day_sources: dict[int, dict[date, str]],
    spans: dict[int, tuple[date, date]],
    tz: ZoneInfo,
) -> pd.DataFrame:
    """Densify per-venue weather onto the hour grid and derive the boolean flags."""
    frames: list[pd.DataFrame] = []
    for venue_id in sorted(spans):
        first_day, last_day = spans[venue_id]
        hours = utc_hours_for_local_days(first_day, last_day, tz)
        if not hours:
            continue
        venue_observations = observations.get(venue_id, {})
        venue_sources = day_sources.get(venue_id, {})
        records: list[dict[str, Any]] = []
        for moment in hours:
            values = venue_observations.get(moment, {})
            records.append(
                {
                    "venue_id": venue_id,
                    "ts_utc": format_utc(moment),
                    "ts_local": format_local(moment, tz),
                    "temperature_2m": values.get("temperature_2m"),
                    "precipitation": values.get("precipitation"),
                    "wind_speed_10m": values.get("wind_speed_10m"),
                    "relative_humidity_2m": values.get("relative_humidity_2m"),
                    "weathercode": values.get("weathercode"),
                    "source": venue_sources.get(local_date_of(moment, tz)),
                }
            )
        frames.append(pd.DataFrame.from_records(records))
    if not frames:
        return empty_table(WEATHER_HOURLY_COLUMNS)
    frame = pd.concat(frames, ignore_index=True)
    frame["venue_id"] = frame["venue_id"].astype("int64")
    for column in ("temperature_2m", "precipitation", "wind_speed_10m"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
    for column in ("relative_humidity_2m", "weathercode"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").round().astype("Int64")
    frame["weathercode_str"] = _decode_series(frame["weathercode"])
    frame["is_precipitation"] = nullable_compare(frame["precipitation"], 0.0, "gt")
    frame["is_cold"] = nullable_compare(frame["temperature_2m"], 0.0, "lt")
    frame["is_windy"] = nullable_compare(frame["wind_speed_10m"], 10.0, "gt")
    frame["source"] = frame["source"].astype("string")
    return frame[WEATHER_HOURLY_COLUMNS].reset_index(drop=True)


def _decode_series(codes: pd.Series) -> pd.Series:
    """Decode a nullable weather code column, keeping missing values missing."""
    decoded = [pd.NA if pd.isna(code) else decode_weathercode(code) for code in codes]
    return pd.Series(decoded, index=codes.index, dtype="string")


def nullable_compare(series: pd.Series, threshold: float, op: str) -> pd.Series:
    """Compare against a threshold, keeping missing input missing rather than False."""
    compared = series > threshold if op == "gt" else series < threshold
    return compared.astype("boolean").where(series.notna(), pd.NA)


def build_weather_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate hourly weather to local calendar days."""
    if hourly.empty:
        return empty_table(WEATHER_DAILY_COLUMNS)
    frame = hourly.copy()
    frame["date"] = local_dates(frame["ts_local"])
    frame["precip_hour"] = (
        (frame["precipitation"] > 0).astype("float64").where(frame["precipitation"].notna())
    )
    grouped = frame.groupby(["venue_id", "date"], as_index=False).agg(
        temp_mean=("temperature_2m", "mean"),
        temp_min=("temperature_2m", "min"),
        temp_max=("temperature_2m", "max"),
        precip_sum=("precipitation", "sum"),
        precip_hours=("precip_hour", "sum"),
        wind_mean=("wind_speed_10m", "mean"),
        weathercode_mode=("weathercode", mode_or_na),
        source=("source", dominant_source),
    )
    for column in ("temp_mean", "temp_min", "temp_max", "precip_sum", "wind_mean"):
        grouped[column] = pd.to_numeric(grouped[column], errors="coerce").round(3)
    grouped["precip_hours"] = pd.to_numeric(grouped["precip_hours"], errors="coerce").astype("Int64")
    grouped["weathercode_mode"] = pd.to_numeric(grouped["weathercode_mode"], errors="coerce").astype("Int64")
    grouped["weathercode_str"] = _decode_series(grouped["weathercode_mode"])
    grouped["source"] = grouped["source"].astype("string")
    grouped = grouped.sort_values(["venue_id", "date"]).reset_index(drop=True)
    return grouped[WEATHER_DAILY_COLUMNS]


def mode_or_na(values: pd.Series) -> Any:
    """Return the most common value, breaking ties towards the smallest code."""
    present = values.dropna()
    if present.empty:
        return pd.NA
    counted = present.value_counts()
    best = int(counted.max())
    return min(as_int(code) for code, count in counted.items() if as_int(count) == best)


def dominant_source(values: pd.Series) -> Any:
    """Return the source covering most hours of a day, preferring archive on ties."""
    present = values.dropna()
    if present.empty:
        return pd.NA
    counted = present.value_counts()
    best = as_int(counted.max())
    candidates = [str(name) for name, count in counted.items() if as_int(count) == best]
    return min(candidates, key=lambda name: (SOURCE_PRIORITY.get(name, 99), name))


def build_traffic_hourly(
    observations: dict[str, dict[str, dict[datetime, float]]],
    spans: dict[str, tuple[date, date]],
    site_names: dict[str, str],
    tz: ZoneInfo,
) -> pd.DataFrame:
    """Densify per-site Eco-Counter observations onto the hour grid.

    Traffic is keyed on ``site_id``, never on ``venue_id``: Karjasilta is one
    measurement point in Oulu and does not belong to any particular venue.
    """
    frames: list[pd.DataFrame] = []
    for site_id in sorted(spans):
        first_day, last_day = spans[site_id]
        hours = utc_hours_for_local_days(first_day, last_day, tz)
        if not hours:
            continue
        site_observations = observations.get(site_id, {})
        records: list[dict[str, Any]] = []
        for moment in hours:
            record: dict[str, Any] = {
                "site_id": site_id,
                "site_name": site_names.get(site_id, site_id),
                "ts_utc": format_utc(moment),
                "ts_local": format_local(moment, tz),
            }
            for sensor, column in SENSOR_TO_COLUMN.items():
                record[column] = site_observations.get(sensor, {}).get(moment)
            records.append(record)
        frames.append(pd.DataFrame.from_records(records))
    if not frames:
        return empty_table(TRAFFIC_HOURLY_COLUMNS)
    frame = pd.concat(frames, ignore_index=True)
    for column in TRAFFIC_COUNT_COLUMNS:
        frame[column] = to_counts(frame[column])
    frame["site_id"] = frame["site_id"].astype("string")
    frame["site_name"] = frame["site_name"].astype("string")
    return frame[TRAFFIC_HOURLY_COLUMNS].reset_index(drop=True)


def normalize_tickets(frame: pd.DataFrame, venue_id: int) -> pd.DataFrame:
    """Normalize a manually maintained ticket sales CSV.

    Column names are matched case-insensitively against English and Finnish aliases.
    """
    if frame.empty:
        return empty_table(TICKETS_DAILY_COLUMNS)
    aliases = {
        "date": ("date", "pvm", "paiva", "päivä", "päivämäärä", "paivamaara"),
        "tickets_sold": ("tickets", "tickets_sold", "liput", "lippuja"),
        "groups_sold": ("groups", "groups_sold", "ryhmat", "ryhmät", "ryhmaliput", "ryhmäliput"),
        "tickets_total": ("total", "tickets_total", "yhteensa", "yhteensä"),
    }
    lookup = {str(column).strip().lower(): column for column in frame.columns}
    resolved: dict[str, str] = {}
    for target, names in aliases.items():
        for name in names:
            if name in lookup:
                resolved[target] = lookup[name]
                break
    if "date" not in resolved:
        raise ValueError(f"Ticket file for venue {venue_id} has no recognizable date column")
    normalized = pd.DataFrame({"venue_id": venue_id, "date": parse_ticket_dates(frame[resolved["date"]])})
    for target in ("tickets_sold", "groups_sold"):
        column = resolved.get(target)
        values = (
            pd.to_numeric(frame[column], errors="coerce")
            if column
            else pd.Series(pd.NA, index=frame.index, dtype="Float64")
        )
        normalized[target] = values.round().astype("Int64")
    total_column = resolved.get("tickets_total")
    if total_column:
        normalized["tickets_total"] = (
            pd.to_numeric(frame[total_column], errors="coerce").round().astype("Int64")
        )
    else:
        normalized["tickets_total"] = (
            normalized["tickets_sold"].fillna(0) + normalized["groups_sold"].fillna(0)
        ).astype("Int64")
    normalized = normalized.dropna(subset=["date"])
    normalized["venue_id"] = normalized["venue_id"].astype("int64")
    normalized = normalized.sort_values(["venue_id", "date"]).reset_index(drop=True)
    return normalized[TICKETS_DAILY_COLUMNS]


def parse_ticket_dates(series: pd.Series) -> pd.Series:
    """Parse ticket dates with explicit formats only, never by inference."""
    text = series.astype("string").str.strip()
    parsed = pd.Series(pd.NA, index=series.index, dtype="string")
    for fmt in TICKET_DATE_FORMATS:
        remaining = parsed.isna()
        if not bool(remaining.any()):
            break
        attempt = pd.to_datetime(text[remaining], format=fmt, errors="coerce")
        parsed.loc[remaining] = attempt.dt.strftime("%Y-%m-%d").astype("string")
    unparsed = int(parsed.isna().sum())
    if unparsed:
        log_event("warning", "tickets", "Dropped rows with unparseable dates", rows=unparsed)
    return parsed


def build_calendar_daily(first_day: date, last_day: date, holidays: pd.DataFrame) -> pd.DataFrame:
    """Build the daily calendar table over the inclusive local day range."""
    days = list(iter_days(first_day, last_day))
    if not days:
        return empty_table(CALENDAR_DAILY_COLUMNS)
    holiday_names: dict[date, str] = {}
    if not holidays.empty:
        for _, row in holidays.iterrows():
            parsed = datetime.strptime(str(row["date"]).strip(), "%Y-%m-%d").date()
            holiday_names[parsed] = str(row["holiday_name"])
    holiday_days = set(holiday_names)
    records: list[dict[str, Any]] = []
    for day in days:
        records.append(
            {
                "date": day.isoformat(),
                "holiday_name": holiday_names.get(day, pd.NA),
                "is_holiday": day in holiday_days,
                "is_weekend": day.weekday() >= 5,
                "day_of_week": day.weekday(),
                "days_before_next_holiday": days_before_next_holiday(day, holiday_days),
                "is_last_workday_before_holiday": is_last_workday_before_holiday(day, holiday_days),
                "week_of_year": day.isocalendar().week,
                "month": day.month,
                "year": day.year,
            }
        )
    frame = pd.DataFrame.from_records(records)
    frame["date"] = frame["date"].astype("string")
    frame["holiday_name"] = frame["holiday_name"].astype("string")
    for column in ("is_holiday", "is_weekend", "is_last_workday_before_holiday"):
        frame[column] = frame[column].astype("boolean")
    for column in ("day_of_week", "days_before_next_holiday", "week_of_year", "month", "year"):
        frame[column] = frame[column].astype("int64")
    return frame[CALENDAR_DAILY_COLUMNS]


def days_before_next_holiday(day: date, holiday_days: set[date]) -> int:
    """Days until the next known holiday, ``999`` when none is known."""
    future = [holiday for holiday in holiday_days if holiday >= day]
    if not future:
        return NO_HOLIDAY_SENTINEL
    return (min(future) - day).days


def is_last_workday_before_holiday(day: date, holiday_days: set[date]) -> bool:
    """True when the next business day after a weekday is a holiday."""
    if day.weekday() >= 5:
        return False
    candidate = day + timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate += timedelta(days=1)
    return candidate in holiday_days
