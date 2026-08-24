"""Long-term weather normals.

Open-Meteo only forecasts 16 days ahead, so days 17-30 of a forecast have to lean on
climatology instead. This module fetches ten years of hourly history per venue and
reduces it to a ``(day_of_year, hour)`` table. February 29th is folded into
February 28th so that every day-of-year has the same meaning in leap and common years.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterable
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd
import requests

from . import log_event
from .clients.openmeteo import OpenMeteoClient
from .config import AppConfig, VenueConfig
from .normalize import parse_weather_payload, tz_of
from .store import write_table

CLIMATOLOGY_COLUMNS = [
    "day_of_year",
    "hour",
    "temp_mean",
    "temp_min",
    "temp_max",
    "precip_mean",
    "wind_mean",
]
LEAP_DAY_ORDINAL = 60


def normalized_day_of_year(day: date) -> int:
    """Day of year on a common-year scale, with February 29th folded into the 28th."""
    ordinal = day.timetuple().tm_yday
    if calendar.isleap(day.year) and ordinal >= LEAP_DAY_ORDINAL:
        return ordinal - 1
    return ordinal


def aggregate_climatology(observations: dict[datetime, dict[str, Any]], tz: ZoneInfo) -> pd.DataFrame:
    """Reduce hourly history to per ``(day_of_year, hour)`` normals in local time."""
    if not observations:
        return pd.DataFrame({column: pd.Series(dtype="float64") for column in CLIMATOLOGY_COLUMNS})
    records: list[dict[str, Any]] = []
    for moment, values in observations.items():
        local = moment.astimezone(tz)
        records.append(
            {
                "day_of_year": normalized_day_of_year(local.date()),
                "hour": local.hour,
                "temperature_2m": values.get("temperature_2m"),
                "precipitation": values.get("precipitation"),
                "wind_speed_10m": values.get("wind_speed_10m"),
            }
        )
    frame = pd.DataFrame.from_records(records)
    for column in ("temperature_2m", "precipitation", "wind_speed_10m"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    grouped = frame.groupby(["day_of_year", "hour"], as_index=False).agg(
        temp_mean=("temperature_2m", "mean"),
        temp_min=("temperature_2m", "min"),
        temp_max=("temperature_2m", "max"),
        precip_mean=("precipitation", "mean"),
        wind_mean=("wind_speed_10m", "mean"),
    )
    for column in ("temp_mean", "temp_min", "temp_max", "precip_mean", "wind_mean"):
        grouped[column] = grouped[column].round(3)
    grouped = grouped.sort_values(["day_of_year", "hour"]).reset_index(drop=True)
    return grouped[CLIMATOLOGY_COLUMNS]


def run_climatology(
    config: AppConfig,
    venues: Iterable[VenueConfig],
    first_year: int,
    last_year: int,
    session: requests.Session | None = None,
) -> int:
    """Fetch and write the weather normals for every requested venue."""
    client = OpenMeteoClient(config, session=session or requests.Session())
    tz = tz_of(config.sources.timezone)
    output_dir = config.path(config.sources.climatology.output_dir)
    attempted = 0
    succeeded = 0
    for venue in venues:
        attempted += 1
        observations: dict[datetime, dict[str, Any]] = {}
        failures = 0
        for year in range(first_year, last_year + 1):
            try:
                payload = client.fetch_archive(
                    venue.latitude, venue.longitude, date(year, 1, 1), date(year, 12, 31)
                )
            except Exception as exc:
                failures += 1
                log_event(
                    "error",
                    "climatology",
                    "Archive fetch failed",
                    venue_id=venue.venue_id,
                    year=year,
                    error=str(exc),
                )
                continue
            observations.update(parse_weather_payload(payload, tz))
        if not observations:
            log_event("error", "climatology", "No history fetched", venue_id=venue.venue_id)
            continue
        normals = aggregate_climatology(observations, tz)
        write_table(output_dir / f"venue_{venue.venue_id}.csv", normals)
        succeeded += 1
        log_event(
            "info",
            "climatology",
            "Wrote weather normals",
            venue_id=venue.venue_id,
            years=f"{first_year}-{last_year}",
            failed_years=failures,
            rows=len(normals),
        )
    if attempted and not succeeded:
        return 2
    return 0
