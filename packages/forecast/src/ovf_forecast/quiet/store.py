"""Where a quiet-day run is written, and how runs accumulate into a record.

The layout copies ``data/evaluations/`` deliberately, down to the file names: one
directory per run under ``data/quiet/``, named by a deterministic and readable id, plus
one line in ``index.json``. Re-running the same month or the same sweep overwrites its
own directory, so a repository does not fill with near-identical answers and "the October
forecast" always means one thing.

Nothing inside a run directory carries a wall clock time, which is what lets two
consecutive runs be compared byte for byte. The creation time lives in ``index.json``,
which is a registry rather than a result.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .. import log_event
from ..evaluation.store import clean
from ..i18n import DEFAULT_LANG, LANGUAGES, normalise

QUIET_DIR = "data/quiet"
INDEX_NAME = "index.json"
CONFIG_NAME = "config.json"
DAYS_NAME = "days.csv"
WINDOWS_NAME = "windows.csv"
METRICS_NAME = "metrics.json"
VERDICTS_NAME = "verdicts.json"
REPORT_NAME = "report.md"


def report_name(lang: str = DEFAULT_LANG) -> str:
    """``report.md`` for the default language, ``report.en.md`` for the others."""
    code = normalise(lang)
    return REPORT_NAME if code == DEFAULT_LANG else f"report.{code}.md"

SCHEMA_VERSION = "v1"
RUN_PREFIX = "quiet"
KIND_FORECAST = "forecast"
KIND_BACKTEST = "backtest"
VALUE_FORMAT = "%.4f"


@dataclass
class QuietArtifacts:
    """Everything one stored run consists of."""

    run_id: str
    kind: str
    config: dict[str, Any]
    days: pd.DataFrame
    metrics: dict[str, Any]
    verdicts: dict[str, Any]
    reports: dict[str, str]
    windows: pd.DataFrame | None = None
    members: list[str] = field(default_factory=list)

    def report(self, lang: str = DEFAULT_LANG) -> str:
        """One rendered report, falling back to whichever language the run has."""
        code = normalise(lang)
        if self.reports.get(code):
            return self.reports[code]
        return next((value for value in self.reports.values() if value), "")


def quiet_root(root: Path) -> Path:
    """The directory every quiet-day run is written under."""
    return root / QUIET_DIR


def run_dir(root: Path, run_id: str) -> Path:
    """One run's directory."""
    return quiet_root(root) / run_id


def build_forecast_id(month_label: str, origin: str, models: tuple[str, ...], suffix: str = "") -> str:
    """``quiet_v1_forecast_{month}_{origin}_{rules}``."""
    parts = [RUN_PREFIX, SCHEMA_VERSION, KIND_FORECAST, month_label, origin, "-".join(models)]
    return "_".join(parts) + suffix


def build_backtest_id(first: str, last: str, models: tuple[str, ...], suffix: str = "") -> str:
    """``quiet_v1_backtest_{first_test_day}_{last_test_day}_{rules}``."""
    parts = [RUN_PREFIX, SCHEMA_VERSION, KIND_BACKTEST, first, last, "-".join(models)]
    return "_".join(parts) + suffix


def id_suffix(venues: tuple[int, ...] | None, quiet_share: float, top_k: int | None) -> str:
    """The non-default parts of a configuration, as readable id fragments.

    Appended rather than hashed so a directory listing stays legible: a run on venue 1
    with a tenth of the month as its quiet set reads ``_v1_q10``, not ``_9f3ac1``.
    """
    extras: list[str] = []
    if venues:
        extras.append("v" + "-".join(str(venue) for venue in sorted(venues)))
    if top_k is not None:
        extras.append(f"k{top_k}")
    elif abs(quiet_share - 0.20) > 1e-9:
        extras.append(f"q{round(quiet_share * 100)}")
    return ("_" + "_".join(extras)) if extras else ""


def write_run(root: Path, artifacts: QuietArtifacts) -> Path:
    """Write one run's files, replacing whatever was there before."""
    directory = run_dir(root, artifacts.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / CONFIG_NAME, artifacts.config)
    _write_csv(directory / DAYS_NAME, artifacts.days)
    if artifacts.windows is not None:
        _write_csv(directory / WINDOWS_NAME, artifacts.windows)
    _write_json(directory / METRICS_NAME, artifacts.metrics)
    _write_json(directory / VERDICTS_NAME, artifacts.verdicts)
    for lang, rendered in artifacts.reports.items():
        (directory / report_name(lang)).write_text(rendered, encoding="utf-8", newline="\n")
    log_event(
        "info", "quiet.store", "Wrote quiet-day run", run_id=artifacts.run_id, path=str(directory)
    )
    return directory


def _write_csv(path: Path, frame: pd.DataFrame) -> None:
    """Write one table with fixed formatting, so two runs match byte for byte."""
    frame.to_csv(path, index=False, lineterminator="\n", float_format=VALUE_FORMAT)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write one JSON file with NaN mapped to null, because NaN is not JSON."""
    path.write_text(
        json.dumps(clean(payload), indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


# --------------------------------------------------------------------------------------
# The index
# --------------------------------------------------------------------------------------


def read_index(root: Path) -> dict[str, Any]:
    """The run registry, or an empty one when nothing has been run yet."""
    path = quiet_root(root) / INDEX_NAME
    empty: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "runs": []}
    if not path.is_file():
        return empty
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log_event("warning", "quiet.store", "Unreadable quiet index, starting a new one", path=str(path))
        return empty
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return empty
    return payload


def update_index(root: Path, entry: dict[str, Any], *, moment: datetime | None = None) -> None:
    """Add or replace one run's line in the registry, newest last."""
    index = read_index(root)
    runs = [run for run in index["runs"] if run.get("run_id") != entry["run_id"]]
    stamped = dict(entry)
    stamped["created_at"] = (moment or datetime.now(UTC)).astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    runs.append(stamped)
    index["schema_version"] = SCHEMA_VERSION
    index["runs"] = runs
    directory = quiet_root(root)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / INDEX_NAME, index)


def list_runs(root: Path) -> list[dict[str, Any]]:
    """Every registered run, newest first."""
    runs = read_index(root)["runs"]
    return sorted(runs, key=lambda run: str(run.get("created_at", "")), reverse=True)


def load_run(root: Path, run_id: str) -> QuietArtifacts | None:
    """Read one stored run back, or ``None`` when it is not there."""
    directory = run_dir(root, run_id)
    if not directory.is_dir():
        return None
    windows_path = directory / WINDOWS_NAME
    return QuietArtifacts(
        run_id=run_id,
        kind=str(_read_json(directory / CONFIG_NAME).get("kind", KIND_FORECAST)),
        config=_read_json(directory / CONFIG_NAME),
        days=_read_csv(directory / DAYS_NAME),
        metrics=_read_json(directory / METRICS_NAME),
        verdicts=_read_json(directory / VERDICTS_NAME),
        reports=_read_reports(directory),
        windows=_read_csv(windows_path) if windows_path.is_file() else None,
    )


def latest_backtest(root: Path) -> dict[str, Any] | None:
    """The newest stored sweep, which is what a forecast quotes its reliability from.

    A forecast that cannot point at a measurement is a guess with a nice table around it,
    so the forecast command looks this up and prints what it finds — including finding
    nothing, which it says out loud.
    """
    for entry in list_runs(root):
        if entry.get("kind") == KIND_BACKTEST:
            return entry
    return None


def _read_reports(directory: Path) -> dict[str, str]:
    """Every rendered report a run directory holds, keyed by language."""
    found: dict[str, str] = {}
    for lang in LANGUAGES:
        path = directory / report_name(lang)
        if path.is_file():
            found[lang] = path.read_text(encoding="utf-8")
    return found


def _read_csv(path: Path) -> pd.DataFrame:
    """Read one stored table, tolerating a header-only file."""
    if not path.is_file():
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _read_json(path: Path) -> dict[str, Any]:
    """Read one JSON object, or an empty dict."""
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}
