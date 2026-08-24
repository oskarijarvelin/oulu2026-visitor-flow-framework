"""Quality gates and manifest construction.

Gates run against the freshly built tables *before* anything is written. A failing
gate diverts its tables to ``<name>.rejected``, leaves the previous version in
place and makes the run exit with code 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd

from . import __version__, log_event
from .config import AppConfig
from .normalize import TRAFFIC_COUNT_COLUMNS, as_int

VISITORS_HOURLY = "visitors_hourly"
VISITORS_DAILY = "visitors_daily"
WEATHER_HOURLY = "weather_hourly"
WEATHER_DAILY = "weather_daily"
TRAFFIC_HOURLY = "traffic_hourly"
TICKETS_DAILY = "tickets_daily"
CALENDAR_DAILY = "calendar_daily"

HOURLY_TABLES = (VISITORS_HOURLY, WEATHER_HOURLY, TRAFFIC_HOURLY)


@dataclass
class SourceReport:
    """One entry of the manifest ``sources`` array."""

    name: str
    status: str
    rows: int = 0
    window: tuple[str, str] | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for the manifest, omitting fields that carry no information."""
        payload: dict[str, Any] = {"name": self.name, "status": self.status, "rows": self.rows}
        if self.window is not None:
            payload["window"] = [self.window[0], self.window[1]]
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass
class GateResult:
    """Outcome of one quality gate."""

    name: str
    passed: bool
    detail: str
    tables: tuple[str, ...] = field(default_factory=tuple)


def run_quality_gates(config: AppConfig, tables: dict[str, pd.DataFrame]) -> list[GateResult]:
    """Run every quality gate against the built tables."""
    gates = config.sources.quality_gates
    results = [
        _gate_visitor_gap(
            tables.get(VISITORS_HOURLY), gates.max_visitor_gap_hours, gates.visitor_gap_lookback_days
        ),
        _gate_weather_coverage(tables.get(WEATHER_HOURLY), gates.min_weather_coverage),
        _gate_daily_capacity(config, tables.get(VISITORS_DAILY)),
        _gate_no_negative_counts(tables),
    ]
    for result in results:
        log_event(
            "info" if result.passed else "error",
            "quality-gate",
            result.detail,
            gate=result.name,
            passed=result.passed,
        )
    return results


def _gate_visitor_gap(hourly: pd.DataFrame | None, max_gap_hours: int, lookback_days: int) -> GateResult:
    """No run of unanswered visitor hours longer than the threshold, within the lookback."""
    name = "visitor_gap"
    tables = (VISITORS_HOURLY, VISITORS_DAILY)
    if hourly is None or hourly.empty:
        return GateResult(name, True, "No visitor rows to check", tables)
    last = _parse_utc(str(hourly["ts_utc"].max()))
    cutoff = last - timedelta(days=lookback_days)
    recent = hourly[hourly["ts_utc"] >= _format_utc(cutoff)]
    worst_venue: int | None = None
    worst_gap = 0
    for venue_id, group in recent.groupby("venue_id"):
        ordered = group.sort_values("ts_utc")
        gap = _longest_true_run(ordered["is_imputed"])
        if gap > worst_gap:
            worst_gap, worst_venue = gap, as_int(venue_id)
    passed = worst_gap <= max_gap_hours
    detail = (
        f"Longest visitor gap in the last {lookback_days} days is {worst_gap} h "
        f"(venue {worst_venue}), limit {max_gap_hours} h"
    )
    return GateResult(name, passed, detail, tables)


def _longest_true_run(flags: pd.Series) -> int:
    """Length of the longest consecutive run of true values."""
    longest = 0
    current = 0
    for flag in flags.fillna(False).astype(bool):
        current = current + 1 if flag else 0
        longest = max(longest, current)
    return longest


def _gate_weather_coverage(hourly: pd.DataFrame | None, minimum: float) -> GateResult:
    """Weather must cover at least the configured fraction of the fetched period."""
    name = "weather_coverage"
    tables = (WEATHER_HOURLY, WEATHER_DAILY)
    if hourly is None or hourly.empty:
        return GateResult(name, True, "No weather rows to check", tables)
    worst = 1.0
    worst_venue: int | None = None
    for venue_id, group in hourly.groupby("venue_id"):
        covered = float(group["temperature_2m"].notna().mean())
        if covered < worst:
            worst, worst_venue = covered, as_int(venue_id)
    passed = worst >= minimum
    detail = f"Lowest weather coverage is {worst:.4f} (venue {worst_venue}), minimum {minimum}"
    return GateResult(name, passed, detail, tables)


def _gate_daily_capacity(config: AppConfig, daily: pd.DataFrame | None) -> GateResult:
    """A day may not exceed ``capacity * 24 * 4`` counted events (obvious sensor fault)."""
    name = "daily_capacity"
    tables = (VISITORS_HOURLY, VISITORS_DAILY)
    if daily is None or daily.empty:
        return GateResult(name, True, "No daily visitor rows to check", tables)
    multiplier = config.sources.quality_gates.daily_total_capacity_multiplier
    offenders: list[str] = []
    for venue_id, group in daily.groupby("venue_id"):
        try:
            limit = config.venue(as_int(venue_id)).capacity * multiplier
        except KeyError:
            continue
        exceeded = group[pd.to_numeric(group["visitors_total"], errors="coerce") > limit]
        offenders.extend(
            f"venue {as_int(venue_id)} {row['date']} = {row['visitors_total']} > {limit}"
            for _, row in exceeded.iterrows()
        )
    passed = not offenders
    detail = (
        "No day exceeds capacity * 24 * 4"
        if passed
        else f"{len(offenders)} day(s) exceed capacity * 24 * 4: {'; '.join(offenders[:5])}"
    )
    return GateResult(name, passed, detail, tables)


def _gate_no_negative_counts(tables: dict[str, pd.DataFrame]) -> GateResult:
    """Counter columns must never be negative once normalization is done."""
    name = "negative_counts"
    checks = {
        VISITORS_HOURLY: ["visitors_in", "visitors_out", "visitors_total"],
        TRAFFIC_HOURLY: TRAFFIC_COUNT_COLUMNS,
    }
    offenders: list[str] = []
    affected: list[str] = []
    for table_name, columns in checks.items():
        frame = tables.get(table_name)
        if frame is None or frame.empty:
            continue
        for column in columns:
            if column not in frame.columns:
                continue
            negatives = int((pd.to_numeric(frame[column], errors="coerce") < 0).sum())
            if negatives:
                offenders.append(f"{table_name}.{column}: {negatives}")
                affected.append(table_name)
    passed = not offenders
    detail = "No negative counter values" if passed else f"Negative counters found: {'; '.join(offenders)}"
    return GateResult(name, passed, detail, tuple(dict.fromkeys(affected)))


def coverage_report(tables: dict[str, pd.DataFrame]) -> dict[str, dict[str, Any]]:
    """First and last covered hour plus the number of unanswered hours per hourly table."""
    coverage: dict[str, dict[str, Any]] = {}
    for name in HOURLY_TABLES:
        frame = tables.get(name)
        if frame is None or frame.empty:
            continue
        coverage[name] = {
            "first": str(frame["ts_utc"].min()),
            "last": str(frame["ts_utc"].max()),
            "missing_hours": _missing_hours(name, frame),
        }
    return coverage


def _missing_hours(name: str, frame: pd.DataFrame) -> int:
    """Count hours a table has a row for but no upstream value."""
    if name == VISITORS_HOURLY:
        return int(frame["is_imputed"].fillna(False).astype(bool).sum())
    if name == WEATHER_HOURLY:
        return int(frame["temperature_2m"].isna().sum())
    present = [column for column in TRAFFIC_COUNT_COLUMNS if column in frame.columns]
    if not present:
        return 0
    return int(frame[present].isna().all(axis=1).sum())


def build_manifest(
    sources: list[SourceReport],
    coverage: dict[str, dict[str, Any]],
    gates: list[GateResult],
    *,
    pipeline: str = "ingest",
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Assemble ``data/processed/manifest.json``."""
    warnings = [f"{gate.name}: {gate.detail}" for gate in gates if not gate.passed]
    warnings.extend(
        f"{report.name} {report.status}" + (f": {report.error}" if report.error else "")
        for report in sources
        if report.status not in {"ok", "skipped"}
    )
    moment = generated_at or datetime.now(UTC)
    return {
        "generated_at": _format_utc(moment),
        "pipeline": pipeline,
        "version": __version__,
        "sources": [report.to_dict() for report in sources],
        "coverage": coverage,
        "quality_gates": {
            "passed": all(gate.passed for gate in gates),
            "warnings": warnings,
        },
    }


MANIFEST_REQUIRED_KEYS = ("generated_at", "pipeline", "version", "sources", "coverage", "quality_gates")


def validate_manifest(manifest: dict[str, Any] | None) -> list[str]:
    """Return a list of structural problems with a manifest. Empty means valid."""
    if manifest is None:
        return ["manifest.json is missing or unreadable"]
    problems = [f"missing key: {key}" for key in MANIFEST_REQUIRED_KEYS if key not in manifest]
    sources = manifest.get("sources")
    if not isinstance(sources, list):
        problems.append("sources must be a list")
    else:
        for index, source in enumerate(sources):
            if not isinstance(source, dict):
                problems.append(f"sources[{index}] must be an object")
                continue
            problems.extend(
                f"sources[{index}] missing key: {key}"
                for key in ("name", "status", "rows")
                if key not in source
            )
    if not isinstance(manifest.get("coverage"), dict):
        problems.append("coverage must be an object")
    gates = manifest.get("quality_gates")
    if not isinstance(gates, dict):
        problems.append("quality_gates must be an object")
    else:
        if not isinstance(gates.get("passed"), bool):
            problems.append("quality_gates.passed must be a boolean")
        if not isinstance(gates.get("warnings"), list):
            problems.append("quality_gates.warnings must be a list")
    return problems


def _parse_utc(text: str) -> datetime:
    """Parse a canonical ``...Z`` timestamp."""
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)


def _format_utc(moment: datetime) -> str:
    """Format an aware datetime as a canonical ``...Z`` timestamp."""
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
