"""Reading ``data/processed/`` and assembling the daily frames the models see.

Two frames matter. *History* is one row per observed local day of one venue, with the
target and the covariates that were actually measured. *Future* is one row per forecast
day, with the same covariate columns filled from the weather forecast for the first
16 days and from climatology after that, because Open-Meteo does not forecast further.

Nothing in this module looks past the origin it is given. That is what makes the
backtest in :mod:`ovf_forecast.backtest` an honest out-of-sample exercise.
"""

from __future__ import annotations

import calendar
import json
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import log_event

ROOT_MARKERS = ("config/venues.json", "data/processed")
LOCAL_TIMEZONE = "Europe/Helsinki"

PROCESSED_DIR = "data/processed"
CLIMATOLOGY_DIR = "data/reference/climatology"
FORECAST_DIR = "data/forecasts"

# Open-Meteo forecasts at most 16 days; days 17-30 fall back to the ten-year normals.
MAX_WEATHER_FORECAST_DAYS = 16
LEAP_DAY_ORDINAL = 60

# A climatological hour counts as a precipitation hour above this mean intensity.
CLIMATOLOGY_PRECIP_HOUR_MM = 0.1
# Daily precipitation at or above this is treated as a rainy day.
RAINY_DAY_MM = 1.0

WEATHER_DAILY_FEATURES = ("temp_mean", "temp_max", "precip_sum", "precip_hours", "wind_mean")
WEATHER_SOURCE_FORECAST = "forecast"
WEATHER_SOURCE_CLIMATOLOGY = "climatology"

CALENDAR_FEATURES = (
    "is_holiday",
    "is_weekend",
    "day_of_week",
    "days_before_next_holiday",
    "is_last_workday_before_holiday",
    "week_of_year",
    "month",
)

# WMO code groups. The daily model sees the group, not the code, because 4.5 months of
# data does not contain enough of any single code to learn from.
WEATHER_GROUPS: dict[str, tuple[int, ...]] = {
    "clear": (0, 1),
    "cloudy": (2, 3, 45, 48),
    "rain": (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99),
    "snow": (71, 73, 75, 77, 85, 86),
}
WEATHER_GROUP_OTHER = "other"
WEATHER_GROUP_ORDER = ("clear", "cloudy", "rain", "snow", WEATHER_GROUP_OTHER)

# Representative codes used when climatology has to stand in for a real observation.
CLIMATOLOGY_CODE_DRY = 3
CLIMATOLOGY_CODE_SNOW = 71

_CODE_TO_GROUP: dict[int, str] = {
    code: group for group, codes in WEATHER_GROUPS.items() for code in codes
}


@dataclass(frozen=True)
class Venue:
    """One venue from ``config/venues.json``."""

    venue_id: int
    name: str
    city: str
    capacity: int


@dataclass(frozen=True)
class ProcessedData:
    """Every canonical table the forecast package reads, loaded once per run."""

    root: Path
    venues: tuple[Venue, ...]
    visitors_daily: pd.DataFrame
    visitors_hourly: pd.DataFrame
    weather_daily: pd.DataFrame
    weather_hourly: pd.DataFrame
    calendar_daily: pd.DataFrame
    climatology: dict[int, pd.DataFrame]
    ingest_manifest: dict[str, Any] | None

    def venue(self, venue_id: int) -> Venue:
        """Return one venue by id."""
        for venue in self.venues:
            if venue.venue_id == venue_id:
                return venue
        raise KeyError(f"Unknown venue_id: {venue_id}")

    def select_venues(self, venue_ids: tuple[int, ...] | None) -> tuple[Venue, ...]:
        """Return the requested venues, or all of them when nothing is requested."""
        if not venue_ids:
            return self.venues
        return tuple(self.venue(venue_id) for venue_id in venue_ids)


def find_repo_root(start: Path | None = None) -> Path:
    """Locate the repository root by walking up until the config and data are found."""
    override = os.environ.get("OVF_ROOT")
    if override:
        return Path(override).resolve()
    candidates: list[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    candidates.extend([Path.cwd().resolve(), Path(__file__).resolve()])
    for candidate in candidates:
        for directory in (candidate, *candidate.parents):
            if all((directory / marker).exists() for marker in ROOT_MARKERS):
                return directory
    raise FileNotFoundError(
        "Could not locate the repository root. Run from inside the repository or set OVF_ROOT."
    )


def load_venues(root: Path) -> tuple[Venue, ...]:
    """Read ``config/venues.json``."""
    raw = json.loads((root / "config" / "venues.json").read_text(encoding="utf-8"))
    return tuple(
        Venue(
            venue_id=int(item["venue_id"]),
            name=str(item["name"]),
            city=str(item["city"]),
            capacity=int(item["capacity"]),
        )
        for item in raw["venues"]
    )


def load_dataset(root: Path | None = None) -> ProcessedData:
    """Load every processed table plus the climatology normals for each venue."""
    resolved = find_repo_root(root)
    processed = resolved / PROCESSED_DIR
    venues = load_venues(resolved)
    climatology: dict[int, pd.DataFrame] = {}
    for venue in venues:
        path = resolved / CLIMATOLOGY_DIR / f"venue_{venue.venue_id}.csv"
        if path.is_file():
            climatology[venue.venue_id] = _daily_climatology(pd.read_csv(path))
        else:
            log_event(
                "warning",
                "dataset",
                "Climatology missing, days 17-30 will have no weather covariates",
                venue_id=venue.venue_id,
                path=str(path),
            )
    data = ProcessedData(
        root=resolved,
        venues=venues,
        visitors_daily=_read_daily(processed / "visitors_daily.csv"),
        visitors_hourly=_read_hourly(processed / "visitors_hourly.csv"),
        weather_daily=_read_daily(processed / "weather_daily.csv"),
        weather_hourly=_read_hourly(processed / "weather_hourly.csv"),
        calendar_daily=_read_daily(processed / "calendar_daily.csv"),
        climatology=climatology,
        ingest_manifest=_read_json(processed / "manifest.json"),
    )
    log_event(
        "info",
        "dataset",
        "Loaded processed tables",
        root=str(resolved),
        venues=[venue.venue_id for venue in venues],
        visitor_days=len(data.visitors_daily),
        weather_days=len(data.weather_daily),
    )
    return data


def _read_json(path: Path) -> dict[str, Any] | None:
    """Read one JSON object, or ``None`` when it is missing or unreadable."""
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _read_daily(path: Path) -> pd.DataFrame:
    """Read one canonical daily table with ``date`` parsed as a naive local day."""
    if not path.is_file():
        raise FileNotFoundError(f"Missing processed table: {path}. Run the ingest pipeline first.")
    frame = pd.read_csv(path)
    frame["date"] = pd.to_datetime(frame["date"], format="%Y-%m-%d")
    return frame


def _read_hourly(path: Path) -> pd.DataFrame:
    """Read one canonical hourly table, adding the local day and hour of every row.

    ``ts_local`` carries mixed UTC offsets across a DST boundary, so the local wall
    clock is derived from ``ts_utc`` instead of parsed out of the local string.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Missing processed table: {path}. Run the ingest pipeline first.")
    frame = pd.read_csv(path)
    local = pd.to_datetime(frame["ts_utc"], utc=True, format="ISO8601").dt.tz_convert(LOCAL_TIMEZONE)
    frame["date"] = local.dt.normalize().dt.tz_localize(None)
    frame["hour"] = local.dt.hour.astype("int64")
    return frame


# --------------------------------------------------------------------------------------
# Weather
# --------------------------------------------------------------------------------------


def as_float(value: Any) -> float:
    """Coerce one pandas scalar to ``float``, mapping every missing marker to NaN.

    Indexing a frame gives back a wide union type, and every call site here wants one
    plain number. Funnelling them through these three helpers keeps that coercion in one
    place instead of scattering casts through the module.
    """
    if value is None or pd.isna(value):
        return float("nan")
    return float(value)


def as_int(value: Any) -> int:
    """Coerce one pandas scalar to ``int``."""
    return int(value)


def as_timestamp(value: Any) -> pd.Timestamp:
    """Coerce one pandas scalar to a ``Timestamp``."""
    return pd.Timestamp(value)


def normalized_day_of_year(day: date) -> int:
    """Day of year on a common-year scale, matching the climatology table's convention."""
    ordinal = day.timetuple().tm_yday
    if calendar.isleap(day.year) and ordinal >= LEAP_DAY_ORDINAL:
        return ordinal - 1
    return ordinal


def weather_group(code: Any) -> str:
    """Map a WMO weather code to one of five coarse groups."""
    if code is None or (isinstance(code, float) and np.isnan(code)) or pd.isna(code):
        return WEATHER_GROUP_OTHER
    return _CODE_TO_GROUP.get(int(code), WEATHER_GROUP_OTHER)


def _daily_climatology(hourly: pd.DataFrame) -> pd.DataFrame:
    """Reduce the ``(day_of_year, hour)`` normals to one row per day of year.

    ``temp_max`` is the warmest *mean* hour rather than the ten-year extreme, so the
    column keeps the same meaning as the observed ``temp_max`` of an average day.
    """
    frame = hourly.copy()
    frame["precip_hour"] = (frame["precip_mean"] >= CLIMATOLOGY_PRECIP_HOUR_MM).astype("float64")
    daily = frame.groupby("day_of_year", as_index=False).agg(
        temp_mean=("temp_mean", "mean"),
        temp_max=("temp_mean", "max"),
        precip_sum=("precip_mean", "sum"),
        precip_hours=("precip_hour", "sum"),
        wind_mean=("wind_mean", "mean"),
    )
    daily["weathercode"] = [
        _climatology_code(precip, temp)
        for precip, temp in zip(daily["precip_sum"], daily["temp_mean"], strict=True)
    ]
    daily["weathercode_str"] = daily["weathercode"].map(_CLIMATOLOGY_CODE_NAMES)
    for column in ("temp_mean", "temp_max", "precip_sum", "wind_mean"):
        daily[column] = daily[column].round(3)
    return daily


_CLIMATOLOGY_CODE_NAMES: dict[int, str] = {
    CLIMATOLOGY_CODE_DRY: "overcast",
    CLIMATOLOGY_CODE_SNOW: "slight_snow_fall",
}


def _climatology_code(precip_sum: float, temp_mean: float) -> int:
    """Pick a representative weather code for an average day.

    A ten-year mean is not a draw from the daily distribution: averaging ten Junes
    leaves 2 mm of drizzle on every single day, so classifying normals by the same
    precipitation thresholds as observations would label the whole second half of the
    horizon rainy. An average Oulu day is overcast, and that is what these rows claim;
    only the sub-zero half of the year is allowed to say snow.
    """
    if temp_mean < 0.0 and precip_sum >= RAINY_DAY_MM:
        return CLIMATOLOGY_CODE_SNOW
    return CLIMATOLOGY_CODE_DRY


def climatology_row(data: ProcessedData, venue_id: int, day: date) -> dict[str, Any]:
    """Climatological covariates for one calendar day, or NaNs when normals are missing."""
    normals = data.climatology.get(venue_id)
    empty: dict[str, Any] = {column: float("nan") for column in WEATHER_DAILY_FEATURES}
    empty["weathercode"] = pd.NA
    empty["weathercode_str"] = pd.NA
    if normals is None or normals.empty:
        return empty
    matches = normals.loc[normals["day_of_year"] == normalized_day_of_year(day)]
    if matches.empty:
        return empty
    row = matches.iloc[0]
    return {
        **{column: as_float(row[column]) for column in WEATHER_DAILY_FEATURES},
        "weathercode": as_int(row["weathercode"]),
        "weathercode_str": str(row["weathercode_str"]),
    }


# --------------------------------------------------------------------------------------
# History
# --------------------------------------------------------------------------------------


def venue_history(
    data: ProcessedData, venue_id: int, *, trim_leading_zeros: bool = True
) -> pd.DataFrame:
    """Observed daily rows for one venue, joined with weather and calendar covariates.

    The leading run of all-zero days is dropped. Venue 1 reports nothing before
    2026-01-22 and venue 2 nothing before 2026-01-08: that is a sensor that was not
    installed yet, not a museum nobody visited, and training on it would drag every
    level feature down.

    ``trim_leading_zeros=False`` keeps them. The evaluation package asks for that,
    because there the training window is whatever the caller named and the series has
    to start where the file starts; see ``docs/EVALUATION.md``.
    """
    visitors = data.visitors_daily.loc[data.visitors_daily["venue_id"] == venue_id].copy()
    if visitors.empty:
        return visitors
    visitors = visitors.sort_values("date").reset_index(drop=True)
    if not trim_leading_zeros:
        return _as_float_targets(_join_covariates(data, visitors, venue_id))
    nonzero = visitors.index[visitors["visitors_total"] > 0]
    if len(nonzero) == 0:
        log_event("warning", "dataset", "Venue has no non-zero day", venue_id=venue_id)
        return visitors.iloc[0:0]
    trimmed = int(nonzero[0])
    if trimmed:
        log_event(
            "info",
            "dataset",
            "Dropped leading zero days before the first observation",
            venue_id=venue_id,
            days=trimmed,
            first_observed=str(as_timestamp(visitors.loc[trimmed, "date"]).date()),
        )
    visitors = visitors.iloc[trimmed:].reset_index(drop=True)
    return _as_float_targets(_join_covariates(data, visitors, venue_id))


def _as_float_targets(frame: pd.DataFrame) -> pd.DataFrame:
    """Force the three target columns to float, whatever the CSV made of them."""
    for column in ("visitors_total", "visitors_in", "visitors_out"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
    return frame


def _join_covariates(data: ProcessedData, frame: pd.DataFrame, venue_id: int) -> pd.DataFrame:
    """Attach the observed weather and calendar columns to a daily frame."""
    weather = data.weather_daily.loc[data.weather_daily["venue_id"] == venue_id]
    weather_columns = ["date", *WEATHER_DAILY_FEATURES, "weathercode_mode", "weathercode_str"]
    merged = frame.merge(
        weather[weather_columns].rename(columns={"weathercode_mode": "weathercode"}),
        on="date",
        how="left",
    )
    calendar_columns = ["date", "holiday_name", *CALENDAR_FEATURES]
    merged = merged.merge(data.calendar_daily[calendar_columns], on="date", how="left")
    return add_derived_weather(merged)


def add_derived_weather(frame: pd.DataFrame) -> pd.DataFrame:
    """Add ``weather_group`` and ``is_rainy_day``, which both models use as features.

    On climatology rows ``is_rainy_day`` is left missing rather than guessed. Whether
    day 25 rains is genuinely unknown, and both models read NaN natively, so saying
    "unknown" costs nothing and inventing a 0 or a 1 would cost accuracy.
    """
    result = frame.copy()
    result["weather_group"] = pd.Categorical(
        [weather_group(code) for code in result["weathercode"]], categories=WEATHER_GROUP_ORDER
    )
    precip = pd.to_numeric(result["precip_sum"], errors="coerce")
    rainy = (precip >= RAINY_DAY_MM).astype("float64").where(precip.notna())
    if "weather_source" in result.columns:
        rainy = rainy.where(result["weather_source"] != WEATHER_SOURCE_CLIMATOLOGY)
    result["is_rainy_day"] = rainy
    return result


# --------------------------------------------------------------------------------------
# Future
# --------------------------------------------------------------------------------------


def venue_future(
    data: ProcessedData,
    venue_id: int,
    origin: date,
    horizon_days: int,
    *,
    max_forecast_days: int = MAX_WEATHER_FORECAST_DAYS,
) -> pd.DataFrame:
    """One row per forecast day with the covariates the models need.

    Days 1 to ``max_forecast_days`` take their weather from ``weather_daily.csv`` and
    days beyond it from the ten-year normals. The backtest applies the same rule, so the
    long horizons are measured on the same smoothed weather they will be run on.
    """
    weather = data.weather_daily.loc[data.weather_daily["venue_id"] == venue_id].set_index("date")
    calendar_frame = data.calendar_daily.set_index("date")
    records: list[dict[str, Any]] = []
    for horizon in range(1, horizon_days + 1):
        day = origin + timedelta(days=horizon)
        stamp = pd.Timestamp(day)
        record: dict[str, Any] = {"date": stamp, "horizon_days": horizon}
        observed = weather.loc[stamp] if stamp in weather.index else None
        if horizon <= max_forecast_days and observed is not None:
            record["weather_source"] = WEATHER_SOURCE_FORECAST
            for column in WEATHER_DAILY_FEATURES:
                record[column] = as_float(observed[column])
            code = observed["weathercode_mode"]
            record["weathercode"] = as_int(code) if pd.notna(code) else pd.NA
            record["weathercode_str"] = observed["weathercode_str"]
        else:
            record["weather_source"] = WEATHER_SOURCE_CLIMATOLOGY
            record.update(climatology_row(data, venue_id, day))
        if stamp in calendar_frame.index:
            calendar_row = calendar_frame.loc[stamp]
            record["holiday_name"] = calendar_row["holiday_name"]
            for column in CALENDAR_FEATURES:
                record[column] = calendar_row[column]
        else:
            record["holiday_name"] = pd.NA
            record.update(_calendar_fallback(day))
        records.append(record)
    frame = pd.DataFrame.from_records(records)
    return add_derived_weather(frame)


def _calendar_fallback(day: date) -> dict[str, Any]:
    """Calendar columns for a day the ingest calendar does not reach.

    Holidays cannot be invented, so the fallback assumes none. It only fires when the
    forecast horizon runs past the maintained calendar, which the run logs as a warning.
    """
    iso = day.isocalendar()
    return {
        "is_holiday": False,
        "is_weekend": day.weekday() >= 5,
        "day_of_week": day.weekday(),
        "days_before_next_holiday": 999,
        "is_last_workday_before_holiday": False,
        "week_of_year": int(iso.week),
        "month": day.month,
    }


def calendar_gap(data: ProcessedData, origin: date, horizon_days: int) -> list[str]:
    """Forecast days the maintained calendar does not cover."""
    known = set(data.calendar_daily["date"])
    missing = [
        (origin + timedelta(days=horizon)).isoformat()
        for horizon in range(1, horizon_days + 1)
        if pd.Timestamp(origin + timedelta(days=horizon)) not in known
    ]
    return missing


def hourly_weather(data: ProcessedData, venue_id: int, days: list[pd.Timestamp]) -> pd.DataFrame:
    """Hourly weather covariates for the hourly export, indexed by ``ts_utc``."""
    frame = data.weather_hourly
    selected = frame.loc[(frame["venue_id"] == venue_id) & frame["date"].isin(days)]
    columns = ["ts_utc", "date", "hour", "temperature_2m", "precipitation", "weathercode_str"]
    return selected[columns].copy()


def last_observed_day(history: pd.DataFrame) -> date:
    """Last local day with an observation in a history frame."""
    if history.empty:
        raise ValueError("Cannot take the last observed day of an empty history")
    return as_timestamp(history["date"].max()).date()
