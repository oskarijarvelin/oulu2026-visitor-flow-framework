"""Where an evaluation run is written, and how runs accumulate into a record.

One run is one directory under ``data/evaluations/`` named by a deterministic, readable
id, plus one line in ``index.json``. Re-running the same window with the same parameters
overwrites its own directory instead of creating a second one, so a repository does not
slowly fill with near-identical results and "the April run" always means one thing.

Nothing inside a run directory carries a wall clock time. That is what makes two
consecutive runs byte-identical, which is the only way a determinism test can be written
at all. The creation time lives in ``index.json``, which is a registry rather than a
result.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .. import log_event
from ..i18n import DEFAULT_LANG, LANGUAGES, normalise
from .runner import WEATHER_MODES, EvaluationConfig
from .windows import TRAIN_WINDOW_ALL, Window

EVALUATIONS_DIR = "data/evaluations"
INDEX_NAME = "index.json"
CONFIG_NAME = "config.json"
PREDICTIONS_NAME = "predictions.csv"
METRICS_NAME = "metrics.json"
VERDICTS_NAME = "verdicts.json"
REPORT_NAME = "report.md"


def report_name(lang: str = DEFAULT_LANG) -> str:
    """``report.md`` for the default language, ``report.en.md`` for the others.

    The default language keeps the plain name so that every path already written down —
    in a document, in a script, in somebody's shell history — still resolves.
    """
    code = normalise(lang)
    return REPORT_NAME if code == DEFAULT_LANG else f"report.{code}.md"

SCHEMA_VERSION = "v1"
RUN_PREFIX = "eval"
VALUE_FORMAT = "%.4f"


@dataclass
class RunArtifacts:
    """Everything one stored run consists of."""

    run_id: str
    config: dict[str, Any]
    predictions: pd.DataFrame
    metrics: dict[str, Any]
    verdicts: dict[str, Any]
    reports: dict[str, str]
    members: list[str] = field(default_factory=list)

    def report(self, lang: str = DEFAULT_LANG) -> str:
        """One rendered report, falling back to whichever language the run has."""
        code = normalise(lang)
        if self.reports.get(code):
            return self.reports[code]
        return next((value for value in self.reports.values() if value), "")


def evaluations_root(root: Path) -> Path:
    """The directory every evaluation is written under."""
    return root / EVALUATIONS_DIR


def run_dir(root: Path, run_id: str) -> Path:
    """One run's directory."""
    return evaluations_root(root) / run_id


def build_run_id(window: Window, config: EvaluationConfig) -> str:
    """A deterministic, readable id for one window.

    The shape is ``eval_v1_{origin}_{test_start}_{test_end}_{models}``. Anything that
    changes the answer but is not in that name — a venue subset, a sliding training
    window, a restricted set of weather modes, a fixed reference — is appended as a short
    readable suffix rather than hashed, so the directory listing stays legible.
    """
    models = "-".join(config.models) if config.models else "none"
    parts = [
        RUN_PREFIX,
        SCHEMA_VERSION,
        window.origin.isoformat(),
        window.test_start.isoformat(),
        window.test_end.isoformat(),
        models,
    ]
    return "_".join(parts) + _suffix(window, config)


def build_sweep_id(kind: str, windows: list[Window], config: EvaluationConfig) -> str:
    """A deterministic id for the pooled result of a sweep."""
    models = "-".join(config.models) if config.models else "none"
    first, last = windows[0], windows[-1]
    parts = [
        RUN_PREFIX,
        SCHEMA_VERSION,
        "sweep",
        kind,
        first.test_start.isoformat(),
        last.test_end.isoformat(),
        models,
    ]
    return "_".join(parts) + _suffix(first, config)


def _suffix(window: Window, config: EvaluationConfig) -> str:
    """The non-default parts of a configuration, as readable id fragments."""
    extras: list[str] = []
    if config.venues:
        extras.append("v" + "-".join(str(venue) for venue in sorted(config.venues)))
    if window.train_window != TRAIN_WINDOW_ALL:
        extras.append(f"tw{window.train_window}")
    if tuple(config.weather_modes) != WEATHER_MODES:
        extras.append("wx" + "-".join(mode[:4] for mode in config.weather_modes))
    if config.reference != "best":
        extras.append("ref-" + config.reference)
    return ("_" + "_".join(extras)) if extras else ""


def write_run(root: Path, artifacts: RunArtifacts) -> Path:
    """Write one run's five files, replacing whatever was there before."""
    directory = run_dir(root, artifacts.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / CONFIG_NAME, artifacts.config)
    _write_predictions(directory / PREDICTIONS_NAME, artifacts.predictions)
    _write_json(directory / METRICS_NAME, artifacts.metrics)
    _write_json(directory / VERDICTS_NAME, artifacts.verdicts)
    for lang, rendered in artifacts.reports.items():
        (directory / report_name(lang)).write_text(rendered, encoding="utf-8", newline="\n")
    log_event(
        "info", "evaluation.store", "Wrote evaluation run", run_id=artifacts.run_id, path=str(directory)
    )
    return directory


def _write_predictions(path: Path, predictions: pd.DataFrame) -> None:
    """Write ``predictions.csv`` with fixed formatting, so two runs match byte for byte."""
    predictions.to_csv(path, index=False, lineterminator="\n", float_format=VALUE_FORMAT)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write one JSON file with NaN mapped to null, because NaN is not JSON."""
    path.write_text(
        json.dumps(clean(payload), indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def clean(value: Any) -> Any:
    """Recursively make a payload JSON-safe: no NaN, no numpy scalars, no tuples."""
    if isinstance(value, dict):
        return {str(key): clean(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [clean(item) for item in value]
    if isinstance(value, np.generic):
        return clean(value.item())
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, np.ndarray):
        return [clean(item) for item in value.tolist()]
    return value


# --------------------------------------------------------------------------------------
# The index
# --------------------------------------------------------------------------------------


def read_index(root: Path) -> dict[str, Any]:
    """The run registry, or an empty one when nothing has been evaluated yet."""
    path = evaluations_root(root) / INDEX_NAME
    if not path.is_file():
        return {"schema_version": SCHEMA_VERSION, "runs": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        log_event(
            "warning", "evaluation.store", "Unreadable evaluation index, starting a new one", path=str(path)
        )
        return {"schema_version": SCHEMA_VERSION, "runs": []}
    if not isinstance(payload, dict) or not isinstance(payload.get("runs"), list):
        return {"schema_version": SCHEMA_VERSION, "runs": []}
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
    directory = evaluations_root(root)
    directory.mkdir(parents=True, exist_ok=True)
    _write_json(directory / INDEX_NAME, index)


def list_runs(root: Path) -> list[dict[str, Any]]:
    """Every registered run, newest first."""
    runs = read_index(root)["runs"]
    return sorted(runs, key=lambda run: str(run.get("created_at", "")), reverse=True)


def load_run(root: Path, run_id: str) -> RunArtifacts | None:
    """Read one stored run back, or ``None`` when it is not there."""
    directory = run_dir(root, run_id)
    if not directory.is_dir():
        return None
    predictions = _read_predictions(directory / PREDICTIONS_NAME)
    return RunArtifacts(
        run_id=run_id,
        config=_read_json(directory / CONFIG_NAME),
        predictions=predictions,
        metrics=_read_json(directory / METRICS_NAME),
        verdicts=_read_json(directory / VERDICTS_NAME),
        reports=_read_reports(directory),
    )


def load_window_runs(root: Path) -> list[RunArtifacts]:
    """Every stored single-window run, oldest first.

    This is what ``evaluate report --pooled`` reads: evidence accumulated across every
    evaluation ever run in this repository, not just the windows of one sweep.
    """
    artifacts: list[RunArtifacts] = []
    for entry in sorted(read_index(root)["runs"], key=lambda run: str(run.get("run_id", ""))):
        if entry.get("kind") != "window":
            continue
        loaded = load_run(root, str(entry["run_id"]))
        if loaded is not None and not loaded.predictions.empty:
            artifacts.append(loaded)
    return artifacts


def _read_reports(directory: Path) -> dict[str, str]:
    """Every rendered report a run directory holds, keyed by language."""
    found: dict[str, str] = {}
    for lang in LANGUAGES:
        path = directory / report_name(lang)
        if path.is_file():
            found[lang] = path.read_text(encoding="utf-8")
    return found


def _read_predictions(path: Path) -> pd.DataFrame:
    """Read one ``predictions.csv``, tolerating the header-only file a sweep writes."""
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
