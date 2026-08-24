"""The synthetic dataset the forecast tests run on.

The series has a known weekly rhythm, known opening hours and a known weather response,
so a test can assert what the model should have learned instead of asserting whatever it
happens to produce.

This lives outside ``conftest`` because both test packages in this repository have one,
and a bare ``from conftest import ...`` would resolve to whichever was imported first.
"""

from __future__ import annotations

import json
import math
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

REPO_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
REAL_REPO_ROOT = Path(__file__).resolve().parents[3]
LOCAL_ZONE = ZoneInfo("Europe/Helsinki")

FIRST_DAY = date(2026, 1, 5)
LAST_OBSERVED_DAY = date(2026, 6, 30)
LAST_WEATHER_DAY = date(2026, 8, 15)
OPEN_HOURS = tuple(range(10, 19))
VENUE_IDS = (1, 2)

# The rhythm the tests assert the model learns back. Monday to Sunday.
DOW_FACTORS = (0.6, 0.8, 0.9, 1.0, 1.3, 2.0, 1.1)
VENUE_LEVELS = {1: 400.0, 2: 150.0}
RAIN_FACTOR = 0.75
HOLIDAYS = {date(2026, 1, 6): "Loppiainen", date(2026, 4, 3): "Pitk\u00e4perjantai"}


def write_repo(root: Path) -> Path:
    """Write a complete synthetic repository root: config, processed tables, normals."""
    (root / "config").mkdir()
    for name in ("venues.json", "sites.json", "sources.json", "holidays.csv"):
        shutil.copy(REPO_CONFIG_DIR / name, root / "config" / name)
    processed = root / "data" / "processed"
    processed.mkdir(parents=True)

    hourly = build_visitors_hourly()
    hourly.to_csv(processed / "visitors_hourly.csv", index=False, lineterminator="\n")
    build_visitors_daily(hourly).to_csv(processed / "visitors_daily.csv", index=False, lineterminator="\n")
    weather_hourly = build_weather_hourly()
    weather_hourly.to_csv(processed / "weather_hourly.csv", index=False, lineterminator="\n")
    build_weather_daily(weather_hourly).to_csv(
        processed / "weather_daily.csv", index=False, lineterminator="\n"
    )
    build_calendar().to_csv(processed / "calendar_daily.csv", index=False, lineterminator="\n")
    (processed / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-07-01T04:00:00Z",
                "pipeline": "ingest",
                "sources": [{"name": "jaskaretail", "status": "ok", "rows": 1}],
                "quality_gates": {"passed": True, "warnings": []},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    climatology_dir = root / "data" / "reference" / "climatology"
    climatology_dir.mkdir(parents=True)
    climatology = build_climatology()
    for venue_id in VENUE_IDS:
        climatology.to_csv(climatology_dir / f"venue_{venue_id}.csv", index=False, lineterminator="\n")
    return root


def local_hours(day: date) -> list[datetime]:
    """Every real local hour of a day, as aware UTC instants."""
    start = datetime(day.year, day.month, day.day, tzinfo=LOCAL_ZONE).astimezone(UTC)
    end = (datetime(day.year, day.month, day.day, tzinfo=LOCAL_ZONE) + timedelta(days=1)).astimezone(UTC)
    hours: list[datetime] = []
    cursor = start
    while cursor < end:
        hours.append(cursor)
        cursor += timedelta(hours=1)
    return hours


def observed_days() -> list[date]:
    """Every day of the synthetic observed window."""
    span = (LAST_OBSERVED_DAY - FIRST_DAY).days
    return [FIRST_DAY + timedelta(days=step) for step in range(span + 1)]


def weather_days() -> list[date]:
    """Every day the synthetic weather covers, which runs past the observations."""
    span = (LAST_WEATHER_DAY - FIRST_DAY).days
    return [FIRST_DAY + timedelta(days=step) for step in range(span + 1)]


def daily_total(venue_id: int, day: date) -> float:
    """The generating process: level x weekday rhythm x weather, plus a repeatable wobble."""
    level = VENUE_LEVELS[venue_id]
    factor = DOW_FACTORS[day.weekday()]
    wobble = 1.0 + 0.05 * math.sin((day.toordinal() % 17) / 17.0 * 2.0 * math.pi)
    rain = RAIN_FACTOR if is_rainy(day) else 1.0
    holiday = 0.4 if day in HOLIDAYS else 1.0
    return round(level * factor * wobble * rain * holiday, 0)


def is_rainy(day: date) -> bool:
    """A deterministic rain calendar: every fifth day."""
    return day.toordinal() % 5 == 0


def hour_share(hour: int) -> float:
    """A single-peaked opening-hours profile."""
    if hour not in OPEN_HOURS:
        return 0.0
    middle = (OPEN_HOURS[0] + OPEN_HOURS[-1]) / 2.0
    return math.exp(-(((hour - middle) / 3.0) ** 2))


def build_visitors_hourly() -> pd.DataFrame:
    """Hourly visitors whose daily sums match :func:`daily_total` exactly."""
    records = []
    for venue_id in VENUE_IDS:
        for day in observed_days():
            instants = local_hours(day)
            hours = [instant.astimezone(LOCAL_ZONE).hour for instant in instants]
            weights = np.array([hour_share(hour) for hour in hours], dtype="float64")
            weights = weights / weights.sum()
            total = daily_total(venue_id, day)
            counts = np.floor(weights * total).astype("int64")
            counts[int(np.argmax(weights))] += int(total) - int(counts.sum())
            for instant, count in zip(instants, counts, strict=True):
                inbound = int(count) // 2
                records.append(
                    {
                        "venue_id": venue_id,
                        "ts_utc": instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "ts_local": instant.astimezone(LOCAL_ZONE).isoformat(),
                        "visitors_in": inbound,
                        "visitors_out": int(count) - inbound,
                        "visitors_total": int(count),
                        "is_imputed": False,
                    }
                )
    return pd.DataFrame.from_records(records)


def build_visitors_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the synthetic hourly table to local days."""
    frame = hourly.copy()
    local = pd.to_datetime(frame["ts_utc"], utc=True, format="ISO8601").dt.tz_convert(LOCAL_ZONE)
    frame["date"] = local.dt.strftime("%Y-%m-%d")
    daily = frame.groupby(["venue_id", "date"], as_index=False).agg(
        visitors_in=("visitors_in", "sum"),
        visitors_out=("visitors_out", "sum"),
        visitors_total=("visitors_total", "sum"),
        observed_hours=("visitors_total", "size"),
    )
    daily["is_complete"] = True
    return daily


def build_weather_hourly() -> pd.DataFrame:
    """Hourly weather over the whole window, including the forecast days."""
    records = []
    for venue_id in VENUE_IDS:
        for day in weather_days():
            rainy = is_rainy(day)
            for instant in local_hours(day):
                hour = instant.astimezone(LOCAL_ZONE).hour
                seasonal = 20.0 * math.sin(day.timetuple().tm_yday / 365.0 * math.pi)
                diurnal = 3.0 * math.sin(hour / 24.0 * 2.0 * math.pi)
                temperature = round(-5.0 + seasonal + diurnal, 2)
                records.append(
                    {
                        "venue_id": venue_id,
                        "ts_utc": instant.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "ts_local": instant.astimezone(LOCAL_ZONE).isoformat(),
                        "temperature_2m": temperature,
                        "precipitation": 0.4 if rainy else 0.0,
                        "wind_speed_10m": 5.0,
                        "relative_humidity_2m": 70,
                        "weathercode": 61 if rainy else 1,
                        "weathercode_str": "slight_rain" if rainy else "mainly_clear",
                        "is_precipitation": rainy,
                        "is_cold": temperature < 0,
                        "is_windy": False,
                        "source": "archive" if day <= LAST_OBSERVED_DAY else "forecast",
                    }
                )
    return pd.DataFrame.from_records(records)


def build_weather_daily(hourly: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the synthetic hourly weather to local days."""
    frame = hourly.copy()
    local = pd.to_datetime(frame["ts_utc"], utc=True, format="ISO8601").dt.tz_convert(LOCAL_ZONE)
    frame["date"] = local.dt.strftime("%Y-%m-%d")
    frame["precip_hour"] = (frame["precipitation"] > 0).astype("int64")
    daily = frame.groupby(["venue_id", "date"], as_index=False).agg(
        temp_mean=("temperature_2m", "mean"),
        temp_min=("temperature_2m", "min"),
        temp_max=("temperature_2m", "max"),
        precip_sum=("precipitation", "sum"),
        precip_hours=("precip_hour", "sum"),
        wind_mean=("wind_speed_10m", "mean"),
        weathercode_mode=("weathercode", "max"),
        weathercode_str=("weathercode_str", "first"),
        source=("source", "first"),
    )
    for column in ("temp_mean", "temp_min", "temp_max", "precip_sum", "wind_mean"):
        daily[column] = daily[column].round(3)
    return daily


def build_calendar() -> pd.DataFrame:
    """A calendar table covering every synthetic day."""
    records = []
    holiday_days = sorted(HOLIDAYS)
    for day in weather_days():
        upcoming = [holiday for holiday in holiday_days if holiday >= day]
        distance = (upcoming[0] - day).days if upcoming else 999
        iso = day.isocalendar()
        records.append(
            {
                "date": day.isoformat(),
                "holiday_name": HOLIDAYS.get(day, ""),
                "is_holiday": day in HOLIDAYS,
                "is_weekend": day.weekday() >= 5,
                "day_of_week": day.weekday(),
                "days_before_next_holiday": distance,
                "is_last_workday_before_holiday": distance == 1 and day.weekday() < 5,
                "week_of_year": iso.week,
                "month": day.month,
                "year": day.year,
            }
        )
    return pd.DataFrame.from_records(records)


def build_climatology() -> pd.DataFrame:
    """Hourly normals for every day of a common year."""
    records = []
    for day_of_year in range(1, 366):
        for hour in range(24):
            temperature = round(-5.0 + 20.0 * math.sin(day_of_year / 365.0 * math.pi), 2)
            records.append(
                {
                    "day_of_year": day_of_year,
                    "hour": hour,
                    "temp_mean": temperature,
                    "temp_min": temperature - 4.0,
                    "temp_max": temperature + 4.0,
                    "precip_mean": 0.08,
                    "wind_mean": 5.0,
                }
            )
    return pd.DataFrame.from_records(records)
