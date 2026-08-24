"""Writing the forecast files described in ``docs/FRAMEWORK_PLAN.md`` chapter 4.3.

Everything is written twice: to ``data/forecasts/latest/`` for the web build and to
``data/forecasts/{YYYY-MM-DD}/`` as an archive of that run. Output is deterministic —
same input, same bytes — apart from ``generated_at``, so a re-run on unchanged data
does not churn the working tree.

The hourly rounding uses a largest-remainder allocation, so the rounded hourly values in
the exported file sum to the rounded daily value exactly rather than to within a
rounding error. The invariant is meant to survive contact with the CSV.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from . import __version__, log_event
from .dataset import FORECAST_DIR, LOCAL_TIMEZONE
from .profile import HourProfile, spread_over_hours

LATEST_DIR = "latest"
MANIFEST_NAME = "manifest.json"
DAILY_NAME = "daily_30d.csv"
HOURLY_NAME = "hourly_7d.csv"
METRICS_NAME = "metrics.json"
BACKTEST_NAME = "backtest.csv"

DAILY_COLUMNS = [
    "venue_id",
    "date",
    "horizon_days",
    "model",
    "p10",
    "p50",
    "p90",
    "weather_source",
    "temp_mean",
    "precip_sum",
    "weathercode_str",
    "is_holiday",
    "holiday_name",
    "generated_at",
]
HOURLY_COLUMNS = [
    "venue_id",
    "ts_utc",
    "ts_local",
    "horizon_hours",
    "model",
    "p10",
    "p50",
    "p90",
    "hour",
    "weather_source",
    "temperature_2m",
    "precipitation",
    "weathercode_str",
    "generated_at",
]

VALUE_DIGITS = 3
HOURS_PER_DAY = 24
DEFAULT_HOURLY_DAYS = 7


@dataclass(frozen=True)
class RunStamp:
    """The one timestamp a run is allowed to vary by, and the archive day it writes to."""

    generated_at: str
    archive_day: str

    @classmethod
    def now(cls, moment: datetime | None = None) -> RunStamp:
        """Stamp from the current UTC time, or from an injected one for reproducibility."""
        instant = moment or datetime.now(UTC)
        return cls(
            generated_at=instant.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            archive_day=instant.astimezone(UTC).date().isoformat(),
        )


def forecast_root(root: Path) -> Path:
    """``data/forecasts`` under the repository root."""
    return root / FORECAST_DIR


def venue_dir(base: Path, venue_id: int) -> Path:
    """``.../venue_{id}`` under a forecast directory."""
    return base / f"venue_{venue_id}"


# --------------------------------------------------------------------------------------
# Daily
# --------------------------------------------------------------------------------------


def build_daily_rows(
    venue_id: int,
    future: pd.DataFrame,
    predictions: dict[str, pd.Series],
    intervals: dict[str, tuple[pd.Series, pd.Series]],
    stamp: RunStamp,
) -> pd.DataFrame:
    """One row per (model, forecast day), which is 30 x 2 rows for a full run."""
    frames: list[pd.DataFrame] = []
    for model in sorted(predictions):
        p10, p90 = intervals[model]
        frame = pd.DataFrame(
            {
                "venue_id": venue_id,
                "date": future["date"].dt.strftime("%Y-%m-%d"),
                "horizon_days": future["horizon_days"].astype("int64"),
                "model": model,
                "p10": _round_values(p10),
                "p50": _round_values(predictions[model]),
                "p90": _round_values(p90),
                "weather_source": future["weather_source"],
                "temp_mean": _round_values(future["temp_mean"]),
                "precip_sum": _round_values(future["precip_sum"]),
                "weathercode_str": future["weathercode_str"],
                "is_holiday": future["is_holiday"].astype("float64") > 0,
                "holiday_name": future["holiday_name"],
                "generated_at": stamp.generated_at,
            }
        )
        frames.append(frame)
    combined = pd.concat(frames, ignore_index=True)
    return combined[DAILY_COLUMNS].sort_values(["model", "horizon_days"]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# Hourly
# --------------------------------------------------------------------------------------


def local_hours_of_day(day: date, timezone: str = LOCAL_TIMEZONE) -> list[datetime]:
    """Every real hour of one local day, as aware UTC instants.

    A spring-forward day has 23 of them and an autumn day 25. Stepping the grid in UTC
    is what makes that fall out correctly instead of producing a duplicated or missing
    local hour.
    """
    zone = ZoneInfo(timezone)
    start = datetime(day.year, day.month, day.day, tzinfo=zone).astimezone(UTC)
    stop = datetime(day.year, day.month, day.day, tzinfo=zone) + timedelta(days=1)
    end = stop.astimezone(UTC)
    hours: list[datetime] = []
    cursor = start
    while cursor < end:
        hours.append(cursor)
        cursor += timedelta(hours=1)
    return hours


def build_hourly_rows(
    venue_id: int,
    future: pd.DataFrame,
    predictions: dict[str, pd.Series],
    intervals: dict[str, tuple[pd.Series, pd.Series]],
    profile: HourProfile,
    hourly_weather: pd.DataFrame,
    stamp: RunStamp,
    *,
    days: int = DEFAULT_HOURLY_DAYS,
    timezone: str = LOCAL_TIMEZONE,
) -> pd.DataFrame:
    """Spread the first ``days`` daily forecasts over their hours.

    ``intervals`` is the very same p10/p90 the daily file is built from, not a second
    computation of it. The hourly quantiles are the daily ones scaled by each hour's
    share, which is what makes all three quantiles sum across the day exactly.
    """
    zone = ZoneInfo(timezone)
    weather_index = hourly_weather.set_index("ts_utc") if not hourly_weather.empty else None
    records: list[dict[str, Any]] = []
    horizon_hours = 0
    positions = future.index[future["horizon_days"] <= days]
    for position in positions:
        day: date = future.loc[position, "date"].date()
        horizon = int(future.loc[position, "horizon_days"])
        weather_source = str(future.loc[position, "weather_source"])
        instants = local_hours_of_day(day, timezone)
        local_hour_numbers = [instant.astimezone(zone).hour for instant in instants]
        day_of_week = day.weekday()
        for offset, instant in enumerate(instants):
            horizon_hours = (horizon - 1) * HOURS_PER_DAY + offset + 1
            ts_utc = instant.strftime("%Y-%m-%dT%H:%M:%SZ")
            weather = _hourly_weather_row(weather_index, ts_utc)
            for model in sorted(predictions):
                daily_value = float(predictions[model].iloc[position])
                shares = spread_over_hours(profile, day_of_week, local_hour_numbers, daily_value)
                lower, upper = _relative_width(intervals[model], position, daily_value)
                value = float(shares[offset])
                records.append(
                    {
                        "venue_id": venue_id,
                        "ts_utc": ts_utc,
                        "ts_local": instant.astimezone(zone).isoformat(),
                        "horizon_hours": horizon_hours,
                        "model": model,
                        "p10": value * lower,
                        "p50": value,
                        "p90": value * upper,
                        "hour": local_hour_numbers[offset],
                        "weather_source": weather_source,
                        "temperature_2m": weather.get("temperature_2m"),
                        "precipitation": weather.get("precipitation"),
                        "weathercode_str": weather.get("weathercode_str"),
                        "generated_at": stamp.generated_at,
                    }
                )
    if not records:
        return pd.DataFrame(columns=HOURLY_COLUMNS)
    frame = pd.DataFrame.from_records(records)
    frame = _match_hourly_to_daily(frame, future, predictions, intervals)
    return frame[HOURLY_COLUMNS].sort_values(["model", "horizon_hours"]).reset_index(drop=True)


def _hourly_weather_row(index: pd.DataFrame | None, ts_utc: str) -> dict[str, Any]:
    """Weather covariates for one hour, empty when the hourly table does not reach it."""
    if index is None or ts_utc not in index.index:
        return {}
    row = index.loc[ts_utc]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return {
        "temperature_2m": None if pd.isna(row["temperature_2m"]) else float(row["temperature_2m"]),
        "precipitation": None if pd.isna(row["precipitation"]) else float(row["precipitation"]),
        "weathercode_str": None if pd.isna(row["weathercode_str"]) else str(row["weathercode_str"]),
    }


def _relative_width(
    interval: tuple[pd.Series, pd.Series], position: int, daily_value: float
) -> tuple[float, float]:
    """The day's own p10/p50 and p90/p50 ratios, used to shape its hours.

    Reading the ratio off the exported daily interval rather than off the band means the
    two files cannot drift apart by a rounding step.
    """
    if daily_value <= 0.0:
        return 1.0, 1.0
    lower = float(interval[0].iloc[position]) / daily_value
    upper = float(interval[1].iloc[position]) / daily_value
    return lower, upper


def _match_hourly_to_daily(
    hourly: pd.DataFrame,
    future: pd.DataFrame,
    predictions: dict[str, pd.Series],
    intervals: dict[str, tuple[pd.Series, pd.Series]],
) -> pd.DataFrame:
    """Round the hourly quantiles so each day's hours sum to the daily value exactly.

    The totals are the same rounded numbers the daily file carries, so the invariant
    holds at export precision on disk and not merely in memory.
    """
    frame = hourly.copy()
    horizon_of_hour = ((frame["horizon_hours"] - 1) // HOURS_PER_DAY) + 1
    for model in sorted(predictions):
        for horizon in sorted(horizon_of_hour.unique()):
            mask = (frame["model"] == model) & (horizon_of_hour == horizon)
            if not bool(mask.any()):
                continue
            position = future.index[future["horizon_days"] == horizon][0]
            p10_series, p90_series = intervals[model]
            for column, total in (
                ("p10", _round_scalar(float(p10_series.iloc[position]))),
                ("p50", _round_scalar(float(predictions[model].iloc[position]))),
                ("p90", _round_scalar(float(p90_series.iloc[position]))),
            ):
                frame.loc[mask, column] = _round_to_total(frame.loc[mask, column].to_numpy(), total)
    return frame


def _round_to_total(values: np.ndarray, total: float) -> np.ndarray:
    """Round values to the export precision, putting the remainder on the largest one."""
    rounded = np.round(np.asarray(values, dtype="float64"), VALUE_DIGITS)
    if rounded.size == 0:
        return rounded
    residual = round(total - float(rounded.sum()), VALUE_DIGITS)
    if residual:
        largest = int(np.argmax(rounded))
        rounded[largest] = round(float(rounded[largest]) + residual, VALUE_DIGITS)
    return rounded


# --------------------------------------------------------------------------------------
# Files
# --------------------------------------------------------------------------------------


def write_outputs(
    root: Path,
    venue_id: int,
    daily: pd.DataFrame,
    hourly: pd.DataFrame,
    metrics: dict[str, Any],
    backtest: pd.DataFrame,
    stamp: RunStamp,
) -> list[Path]:
    """Write one venue's four files under ``latest/``."""
    target = venue_dir(forecast_root(root) / LATEST_DIR, venue_id)
    target.mkdir(parents=True, exist_ok=True)
    written = [
        _write_csv(target / DAILY_NAME, daily),
        _write_csv(target / HOURLY_NAME, hourly),
        _write_json(target / METRICS_NAME, metrics),
        _write_csv(target / BACKTEST_NAME, backtest),
    ]
    log_event("info", "export", "Wrote venue forecast", venue_id=venue_id, path=str(target))
    return written


def write_manifest(root: Path, manifest: dict[str, Any]) -> Path:
    """Write the run manifest under ``latest/``."""
    path = forecast_root(root) / LATEST_DIR / MANIFEST_NAME
    return _write_json(path, manifest)


def archive_latest(root: Path, stamp: RunStamp) -> Path:
    """Copy ``latest/`` to ``data/forecasts/{YYYY-MM-DD}/``, replacing an earlier copy."""
    source = forecast_root(root) / LATEST_DIR
    target = forecast_root(root) / stamp.archive_day
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    log_event("info", "export", "Archived run", path=str(target))
    return target


def build_manifest(
    stamp: RunStamp,
    venues: list[dict[str, Any]],
    models: list[str],
    skipped: list[str],
    warnings: list[str],
    ingest_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    """The forecast run manifest, mirroring the ingest one's shape."""
    return {
        "generated_at": stamp.generated_at,
        "pipeline": "forecast",
        "version": __version__,
        "models": models,
        "skipped_models": skipped,
        "venues": venues,
        "ingest": {
            "generated_at": (ingest_manifest or {}).get("generated_at"),
            "quality_gates": (ingest_manifest or {}).get("quality_gates"),
        },
        "warnings": warnings,
    }


def _write_csv(path: Path, frame: pd.DataFrame) -> Path:
    """Write one CSV: UTF-8, dot decimals, LF endings, no index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, frame.to_csv(index=False, lineterminator="\n"))
    return path


def _write_json(path: Path, payload: dict[str, Any]) -> Path:
    """Write one JSON file with stable key order."""
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n")
    return path


def _json_default(value: Any) -> Any:
    """Serialize the numpy and pandas scalars that reach the metrics file."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        number = float(value)
        return number if np.isfinite(number) else None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp | datetime | date):
        return str(value)
    return str(value)


def _round_values(values: pd.Series) -> pd.Series:
    """Round a numeric column to the export precision."""
    return pd.to_numeric(values, errors="coerce").astype("float64").round(VALUE_DIGITS)


def _round_scalar(value: float) -> float:
    """Round one number to the export precision."""
    return float(round(float(value), VALUE_DIGITS))


def _atomic_write(path: Path, text: str) -> None:
    """Write a file atomically so a crash cannot leave half a table behind."""
    handle, temporary_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
