"""Which days of next month will be the quiet ones, and what that answer is worth.

The forecast package predicts how many visitors a day will bring. This package answers a
different question with the same data: given a month, which of its days will be the
quietest ones, so that an activation event can be put where it does the most good.

That is a ranking problem, not a level problem, and the distinction is the reason this
package exists rather than a flag on ``run``. A level forecast has to know how busy
October is; a ranking only has to know which Wednesday in October is the slow one, and on
eight months of history the second question is answerable when the first is not. Every
number here is therefore divided by the month's own median day, so an error in the level
cancels instead of accumulating.

One module per question. :mod:`.threshold` decides what counts as a quiet day and which
days are allowed to be one, :mod:`.model` ranks them and attaches a probability to every
pick, :mod:`.forecast` answers for one month, :mod:`.backtest` is the measuring
instrument that says whether the answer has ever been worth anything, :mod:`.store`
persists and :mod:`.report` explains. This module is the conductor.

``docs/QUIET_DAYS.md`` is the description: where the threshold comes from, how to run
both commands, and what the measured results do and do not support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from itertools import pairwise
from typing import Any

import pandas as pd

from .. import log_event
from ..dataset import ProcessedData, venue_history
from ..evaluation.windows import Window, WindowError, monthly_sweep, rolling_sweep
from .backtest import (
    MIN_ELIGIBLE_DAYS,
    PooledQuiet,
    QuietBacktestConfig,
    WindowOutcome,
    pool,
    run_sweep,
)
from .forecast import (
    QuietForecastConfig,
    VenueMonthForecast,
    forecast_month,
    month_days,
    next_month,
)
from .model import (
    DEFAULT_SCORE_MODEL,
    SCORE_MODELS,
    resolve_score_models,
)
from .report import (
    backtest_summary_fi,
    forecast_summary_fi,
    render_backtest_report,
    render_forecast_report,
)
from .store import (
    KIND_BACKTEST,
    KIND_FORECAST,
    SCHEMA_VERSION,
    QuietArtifacts,
    build_backtest_id,
    build_forecast_id,
    id_suffix,
    latest_backtest,
    list_runs,
    load_run,
    quiet_root,
    update_index,
    write_run,
)
from .threshold import DEFAULT_QUIET_SHARE, MATERIAL_GAP, QuietSet, quiet_count

__all__ = [
    "DEFAULT_QUIET_SHARE",
    "DEFAULT_SCORE_MODEL",
    "MATERIAL_GAP",
    "MIN_ELIGIBLE_DAYS",
    "SCORE_MODELS",
    "PooledQuiet",
    "QuietBacktestConfig",
    "QuietForecastConfig",
    "QuietResult",
    "QuietSet",
    "VenueMonthForecast",
    "Window",
    "WindowError",
    "WindowOutcome",
    "list_runs",
    "load_run",
    "month_days",
    "monthly_sweep",
    "next_month",
    "quiet_backtest",
    "quiet_count",
    "quiet_forecast",
    "quiet_history_bounds",
    "resolve_score_models",
    "rolling_sweep",
    "utc_now",
]


@dataclass
class QuietResult:
    """What one invocation produced: the run it wrote and what it concluded."""

    run_id: str | None = None
    summary: str = ""
    failed_venues: list[int] = field(default_factory=list)

    @property
    def produced_anything(self) -> bool:
        """Whether anything was written."""
        return self.run_id is not None


def utc_now() -> datetime:
    """The moment the index records for a run."""
    return datetime.now(UTC)


def quiet_history_bounds(data: ProcessedData, venues: tuple[int, ...] | None) -> tuple[date, date]:
    """First and last day every selected venue actually reports visitors on.

    Taken from the trimmed history, unlike the evaluation package's version. The days
    before a venue's counter was installed are zeros, and a zero is exactly what this
    package looks for: leaving them in would make January the quietest month of every
    venue's first year and would drag every weekday median down with it.
    """
    firsts: list[date] = []
    lasts: list[date] = []
    for venue in data.select_venues(venues):
        history = venue_history(data, venue.venue_id)
        if history.empty:
            continue
        firsts.append(pd.Timestamp(history["date"].min()).date())
        lasts.append(pd.Timestamp(history["date"].max()).date())
    if not firsts:
        raise WindowError("Yhdelläkään kohteella ei ole havaittua historiaa.")
    return max(firsts), min(lasts)


# --------------------------------------------------------------------------------------
# Forecast
# --------------------------------------------------------------------------------------


def quiet_forecast(
    data: ProcessedData,
    year: int,
    month: int,
    config: QuietForecastConfig,
    *,
    moment: datetime | None = None,
) -> QuietResult:
    """Name one month's quiet days for every selected venue, and store the answer."""
    venues = data.select_venues(config.venues)
    forecasts: list[VenueMonthForecast] = []
    result = QuietResult()
    for venue in venues:
        produced = forecast_month(data, venue, year, month, config)
        if produced is None:
            log_event("error", "quiet", "No history to rank a month from", venue_id=venue.venue_id)
            result.failed_venues.append(venue.venue_id)
            continue
        forecasts.append(produced)
    if not forecasts:
        return result

    label = f"{year}-{month:02d}"
    origin = min(item.origin for item in forecasts)
    run_id = build_forecast_id(
        label,
        origin.isoformat(),
        (config.score_model,),
        id_suffix(config.venues, config.quiet_share, config.top_k),
    )
    reliability = _reliability_rows(data, forecasts)
    metrics: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_FORECAST,
        "month": label,
        "origin": origin.isoformat(),
        "venues": [item.to_dict() for item in forecasts],
    }
    verdicts: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_FORECAST,
        "run_id": run_id,
        "month": label,
        "reliability": reliability,
        "summary_fi": "\n\n".join(
            forecast_summary_fi(item.to_dict(), _match(reliability, item)) for item in forecasts
        ),
    }
    stored = {**config.to_dict(), "kind": KIND_FORECAST, "schema_version": SCHEMA_VERSION}
    artifacts = QuietArtifacts(
        run_id=run_id,
        kind=KIND_FORECAST,
        config=stored,
        days=_forecast_days_frame(forecasts),
        metrics=metrics,
        verdicts=verdicts,
        report=render_forecast_report(stored, metrics, verdicts),
    )
    write_run(data.root, artifacts)
    update_index(
        data.root,
        {
            "run_id": run_id,
            "kind": KIND_FORECAST,
            "month": label,
            "origin": origin.isoformat(),
            "score_model": config.score_model,
            "venues": [item.venue_id for item in forecasts],
            "quiet_days": {
                str(item.venue_id): [day.day.isoformat() for day in item.quiet_days]
                for item in forecasts
            },
        },
        moment=moment,
    )
    result.run_id = run_id
    result.summary = str(verdicts["summary_fi"])
    return result


def _forecast_days_frame(forecasts: list[VenueMonthForecast]) -> pd.DataFrame:
    """``days.csv``: every day of the month for every venue, one row each."""
    rows: list[dict[str, Any]] = []
    for item in forecasts:
        for day in item.days:
            rows.append({"venue_id": item.venue_id, "score_model": item.score_model, **day.to_dict()})
    return pd.DataFrame.from_records(rows)


def _reliability_rows(data: ProcessedData, forecasts: list[VenueMonthForecast]) -> list[dict[str, Any]]:
    """What the newest stored sweep measured for each venue and rule in this forecast.

    A forecast that cannot point at a measurement is a guess with a table around it, so
    the answer always carries whichever verdict the repository holds — or says plainly
    that it holds none.
    """
    entry = latest_backtest(data.root)
    if entry is None:
        return []
    artifacts = load_run(data.root, str(entry.get("run_id", "")))
    if artifacts is None:
        return []
    wanted = {(item.venue_id, item.score_model) for item in forecasts}
    return [
        {**row, "run_id": artifacts.run_id}
        for row in artifacts.verdicts.get("pooled", [])
        if (row.get("venue_id"), row.get("model")) in wanted
    ]


def _match(reliability: list[dict[str, Any]], item: VenueMonthForecast) -> dict[str, Any] | None:
    """The reliability row for one venue and rule."""
    for row in reliability:
        if row.get("venue_id") == item.venue_id and row.get("model") == item.score_model:
            return row
    return None


# --------------------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------------------


def quiet_backtest(
    data: ProcessedData,
    windows: list[Window],
    config: QuietBacktestConfig,
    *,
    sweep_kind: str = "custom",
    moment: datetime | None = None,
) -> QuietResult:
    """Run every window, pool them into a verdict per venue and rule, and store it."""
    result = QuietResult()
    outcomes = run_sweep(data, windows, config)
    if not outcomes:
        log_event("error", "quiet", "No window could be scored", windows=len(windows))
        return result
    pooled = pool(outcomes, config)
    scored = sorted({outcome.window.label for outcome in outcomes})
    first = min(outcome.window.test_start for outcome in outcomes)
    last = max(outcome.window.test_end for outcome in outcomes)
    run_id = build_backtest_id(
        first.isoformat(),
        last.isoformat(),
        config.score_models,
        id_suffix(config.venues, config.quiet_share, config.top_k),
    )
    metrics: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_BACKTEST,
        "sweep_kind": sweep_kind,
        "windows": scored,
        "first_test_day": first.isoformat(),
        "last_test_day": last.isoformat(),
        "windows_overlap": _windows_overlap(windows),
        "window_results": [outcome.to_row() for outcome in outcomes],
    }
    verdicts: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "kind": KIND_BACKTEST,
        "run_id": run_id,
        "pooled": [row.to_dict() for row in pooled],
        "summary_fi": backtest_summary_fi([row.to_dict() for row in pooled]),
    }
    stored = {**config.to_dict(), "kind": KIND_BACKTEST, "schema_version": SCHEMA_VERSION}
    artifacts = QuietArtifacts(
        run_id=run_id,
        kind=KIND_BACKTEST,
        config=stored,
        days=pd.DataFrame.from_records(
            [row for outcome in outcomes for row in outcome.day_rows()]
        ),
        metrics=metrics,
        verdicts=verdicts,
        report=render_backtest_report(stored, metrics, verdicts),
        windows=pd.DataFrame.from_records([outcome.to_row() for outcome in outcomes]),
    )
    write_run(data.root, artifacts)
    update_index(
        data.root,
        {
            "run_id": run_id,
            "kind": KIND_BACKTEST,
            "sweep_kind": sweep_kind,
            "n_windows": len(scored),
            "period": [first.isoformat(), last.isoformat()],
            "verdicts": [
                {
                    "venue_id": row.venue_id,
                    "model": row.model,
                    "verdict": row.verdict,
                    "benefit": round(row.benefit, 3) if row.benefit == row.benefit else None,
                }
                for row in pooled
            ],
        },
        moment=moment,
    )
    result.run_id = run_id
    result.summary = str(verdicts["summary_fi"])
    return result


def _windows_overlap(windows: list[Window]) -> bool:
    """Whether any two windows share a test day, which the report has to disclose."""
    ordered = sorted(windows, key=lambda window: window.test_start)
    return any(
        later.test_start <= earlier.test_end
        for earlier, later in pairwise(ordered)
    )


def quiet_dir(data: ProcessedData) -> str:
    """Where runs are stored, relative to the repository root, for CLI messages."""
    return str(quiet_root(data.root).relative_to(data.root))
