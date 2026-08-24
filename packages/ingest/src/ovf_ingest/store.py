"""Reading and writing the raw day cache and the canonical tables.

Raw day files are the unit of storage: one JSON file per source, key and local
calendar day, holding an unmodified copy of the upstream response(s) for that day.
The canonical CSV tables are always rebuilt from every day file on disk, never
appended to, which is what makes a re-run idempotent.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from . import log_event
from .config import AppConfig

RAW_DAY_SUFFIX = ".json"
REJECTED_SUFFIX = ".rejected"
DATE_FILE_FORMAT = "%Y-%m-%d"
MANIFEST_NAME = "manifest.json"
VOLATILE_MANIFEST_KEYS = ("generated_at",)


# --------------------------------------------------------------------------------------
# Raw day cache
# --------------------------------------------------------------------------------------


def raw_dir(config: AppConfig, relative_dir: str, key: str) -> Path:
    """Directory holding the day files for one source key (venue or site)."""
    return config.path(relative_dir) / key


def raw_day_path(config: AppConfig, relative_dir: str, key: str, day: date) -> Path:
    """Path of one raw day file."""
    return raw_dir(config, relative_dir, key) / f"{day.isoformat()}{RAW_DAY_SUFFIX}"


def write_raw_day(path: Path, payload: dict[str, Any]) -> None:
    """Write one raw day file deterministically, so identical data means identical bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    _atomic_write(path, text)


def read_raw_day(path: Path) -> dict[str, Any]:
    """Read one raw day file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Raw day file is not a JSON object: {path}")
    return payload


def list_raw_days(directory: Path) -> dict[date, Path]:
    """Map every ``YYYY-MM-DD.json`` in a directory to its date."""
    if not directory.is_dir():
        return {}
    days: dict[date, Path] = {}
    for path in sorted(directory.glob(f"*{RAW_DAY_SUFFIX}")):
        try:
            day = datetime.strptime(path.stem, DATE_FILE_FORMAT).date()
        except ValueError:
            log_event("warning", "store", "Ignoring unexpected file in raw cache", path=str(path))
            continue
        days[day] = path
    return days


# --------------------------------------------------------------------------------------
# Canonical tables
# --------------------------------------------------------------------------------------


def processed_path(config: AppConfig, name: str) -> Path:
    """Path of one canonical table."""
    return config.path(config.sources.processed_dir) / name


def write_table(path: Path, frame: pd.DataFrame) -> None:
    """Write one canonical CSV: UTF-8, dot decimals, LF endings, no index."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = frame.to_csv(index=False, lineterminator="\n")
    _atomic_write(path, text)
    log_event("info", "store", "Wrote table", path=str(path), rows=len(frame))


def read_table(path: Path) -> pd.DataFrame:
    """Read one canonical CSV back without inferring datetimes."""
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype_backend="numpy_nullable", keep_default_na=True)


def rejected_path(path: Path) -> Path:
    """Path a table is diverted to when a quality gate fails."""
    return path.with_name(path.name + REJECTED_SUFFIX)


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write the run manifest, leaving it untouched when only the timestamp changed.

    Re-running with unchanged upstream data must not dirty the working tree, so a
    manifest that differs only in ``generated_at`` is not rewritten.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            existing = None
        if isinstance(existing, dict) and _without_volatile(existing) == _without_volatile(manifest):
            log_event("info", "store", "Manifest unchanged, keeping existing file", path=str(path))
            return
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    _atomic_write(path, text)
    log_event("info", "store", "Wrote manifest", path=str(path))


def read_manifest(path: Path) -> dict[str, Any] | None:
    """Read the run manifest, or ``None`` when it is missing or unreadable."""
    if not path.is_file():
        return None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return manifest if isinstance(manifest, dict) else None


def _without_volatile(manifest: dict[str, Any]) -> dict[str, Any]:
    """Copy of a manifest without the fields that change on every run."""
    return {key: value for key, value in manifest.items() if key not in VOLATILE_MANIFEST_KEYS}


# --------------------------------------------------------------------------------------
# Supporting inputs
# --------------------------------------------------------------------------------------


def read_holidays(config: AppConfig) -> pd.DataFrame:
    """Read the maintained holiday calendar."""
    path = config.path(config.sources.calendar.holidays_path)
    if not path.is_file():
        log_event("warning", "calendar", "Holiday file missing", path=str(path))
        return pd.DataFrame(columns=["date", "holiday_name"])
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = {"date", "holiday_name"} - set(frame.columns)
    if missing:
        raise ValueError(f"Holiday file {path} is missing columns: {sorted(missing)}")
    return frame


def read_tickets_csv(path: Path) -> pd.DataFrame:
    """Read a manually maintained ticket sales CSV as raw strings."""
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path, dtype=str, keep_default_na=False)


def _atomic_write(path: Path, text: str) -> None:
    """Write a file atomically so a crash cannot leave a half-written table behind."""
    handle, temporary_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name, suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
        os.replace(temporary_name, path)
    except BaseException:
        Path(temporary_name).unlink(missing_ok=True)
        raise
