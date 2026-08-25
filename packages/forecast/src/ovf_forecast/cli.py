"""Command line entry point and run orchestration.

``run`` backtests, fits and exports; ``backtest`` validates without writing forecasts;
``report`` prints what the last run measured. Exit codes: 0 all good, 1 a venue could
not be forecast, 2 nothing could be produced at all.

The run is deterministic. Every model has a fixed random state, nothing samples, and the
only value that changes between two runs on identical input is ``generated_at``.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from . import LogLevel, __version__, log_event, set_log_level
from .backtest import (
    BacktestConfig,
    build_origins,
    compare_to_benchmarks,
    compute_metrics,
    origin_count,
    production_bands,
    run_backtest,
)
from .backtest import backtest_window as backtest_window_of
from .dataset import (
    MAX_WEATHER_FORECAST_DAYS,
    WEATHER_SOURCE_CLIMATOLOGY,
    ProcessedData,
    Venue,
    calendar_gap,
    hourly_weather,
    load_dataset,
    venue_future,
    venue_history,
)
from .evaluation import (
    DEFAULT_WEATHER_MODE,
    REFERENCE_CHOICES,
    TRAIN_WINDOW_ALL,
    WEATHER_MODES,
    EvaluationConfig,
    WindowError,
    evaluate,
    history_bounds,
    list_runs,
    load_run,
    make_window,
    monthly_sweep,
    pooled_report,
    resolve_weather_modes,
    rolling_sweep,
    utc_now,
)
from .evaluation.significance import N_RESAMPLES, RANDOM_SEED
from .evaluation.windows import (
    DEFAULT_MAX_WINDOWS,
    DEFAULT_ROLLING_HORIZON_DAYS,
    DEFAULT_ROLLING_STEP_DAYS,
)
from .export import (
    LATEST_DIR,
    METRICS_NAME,
    RunStamp,
    archive_latest,
    build_daily_rows,
    build_hourly_rows,
    build_manifest,
    forecast_root,
    venue_dir,
    write_manifest,
    write_outputs,
)
from .features import build_future_frame, build_training_frame
from .intervals import BUCKET_LABELS, Band, apply_bands, bands_to_dict
from .models.base import BENCHMARK_NAMES, MODEL_NAMES, ForecastModel, resolve_models
from .profile import build_profile

EXIT_OK = 0
EXIT_PARTIAL = 1
EXIT_FAILED = 2

DEFAULT_HORIZON_DAYS = 30
DEFAULT_HOURLY_DAYS = 7
MIN_COVERAGE = 0.70
MAX_COVERAGE = 0.90
NEAR_HORIZON_BUCKET = BUCKET_LABELS[0]

STATIC_DO_NOT_TRUST = (
    "Horizons past 14 days: the weather is climatology and the level is frozen at the origin.",
    "Days with programming or an event the model has never seen.",
    "The first two weeks after a new venue or a new sensor comes online.",
    "Periods where the ingest manifest reports a degraded source.",
    "School holidays and midsummer, of which this dataset holds at most one observation.",
)


# --------------------------------------------------------------------------------------
# One venue
# --------------------------------------------------------------------------------------


def forecast_venue(
    data: ProcessedData,
    venue: Venue,
    model_names: tuple[str, ...],
    config: BacktestConfig,
    stamp: RunStamp,
    *,
    hourly_days: int = DEFAULT_HOURLY_DAYS,
) -> dict[str, Any] | None:
    """Backtest, fit and export one venue. Returns its manifest entry, or ``None``."""
    history = venue_history(data, venue.venue_id)
    if history.empty:
        log_event("error", "run", "No observed history", venue_id=venue.venue_id)
        return None
    origin: date = history["date"].max().date()
    warnings: list[str] = []

    def factory() -> list[ForecastModel]:
        models, _ = resolve_models((*model_names, *BENCHMARK_NAMES))
        return models

    backtest = run_backtest(data, venue.venue_id, history, factory, config)
    metrics = compute_metrics(backtest)
    comparison = compare_to_benchmarks(metrics, model_names, BENCHMARK_NAMES)
    bands = production_bands(backtest)

    models, _ = resolve_models(model_names)
    if not models:
        log_event("error", "run", "No usable model", venue_id=venue.venue_id)
        return None

    training = build_training_frame(history, origin)
    covariates = venue_future(data, venue.venue_id, origin, config.horizon_days)
    future = build_future_frame(history, covariates, origin)

    predictions: dict[str, pd.Series] = {}
    intervals: dict[str, tuple[pd.Series, pd.Series]] = {}
    for model in models:
        model.fit(training)
        predicted = model.predict(future)
        predictions[model.name] = predicted
        intervals[model.name] = apply_bands(predicted, future["horizon_days"], bands, model.name)

    profile = build_profile(data.visitors_hourly, venue.venue_id, origin)
    daily = build_daily_rows(venue.venue_id, future, predictions, intervals, stamp)
    hourly_days_stamps = [
        pd.Timestamp(day) for day in future.loc[future["horizon_days"] <= hourly_days, "date"]
    ]
    hourly = build_hourly_rows(
        venue.venue_id,
        future,
        predictions,
        intervals,
        profile,
        hourly_weather(data, venue.venue_id, hourly_days_stamps),
        stamp,
        days=hourly_days,
    )

    warnings.extend(_venue_warnings(data, venue, metrics, backtest, origin, config, profile.observed_days))
    metrics_payload = _metrics_payload(
        venue=venue,
        origin=origin,
        history=history,
        backtest=backtest,
        metrics=metrics,
        comparison=comparison,
        bands=bands,
        model_names=tuple(predictions),
        profile_days=profile.observed_days,
        open_hours=profile.open_hours,
        future=future,
        warnings=warnings,
        stamp=stamp,
    )
    write_outputs(data.root, venue.venue_id, daily, hourly, metrics_payload, backtest, stamp)
    _log_honesty_gate(venue, metrics, comparison)
    return {
        "venue_id": venue.venue_id,
        "name": venue.name,
        "origin_date": origin.isoformat(),
        "n_training_days": len(history),
        "n_origins": origin_count(backtest),
        "models": sorted(predictions),
        "horizon_days": config.horizon_days,
        "hourly_days": hourly_days,
        "warnings": warnings,
    }


def _venue_warnings(
    data: ProcessedData,
    venue: Venue,
    metrics: dict[str, dict[str, dict[str, float | int]]],
    backtest: pd.DataFrame,
    origin: date,
    config: BacktestConfig,
    profile_days: int,
) -> list[str]:
    """Everything about this run a reader should know before believing the numbers."""
    warnings: list[str] = []
    origins = origin_count(backtest)
    if origins < config.min_origins:
        warnings.append(
            f"Only {origins} backtest origins fit the {config.min_training_days}-day training "
            f"floor; the plan asks for at least {config.min_origins}, so the interval quantiles "
            "rest on a thin sample."
        )
    for model, buckets in metrics.items():
        coverage = buckets.get(NEAR_HORIZON_BUCKET, {}).get("coverage_80")
        if coverage is None or not isinstance(coverage, float) or coverage != coverage:
            continue
        if coverage < MIN_COVERAGE or coverage > MAX_COVERAGE:
            warnings.append(
                f"Model {model} has {coverage:.0%} coverage at horizon {NEAR_HORIZON_BUCKET}, "
                f"outside the acceptable {MIN_COVERAGE:.0%}-{MAX_COVERAGE:.0%} range."
            )
    missing_calendar = calendar_gap(data, origin, config.horizon_days)
    if missing_calendar:
        warnings.append(
            f"The maintained calendar does not reach {missing_calendar[0]}; those days assume "
            "no holiday."
        )
    stale_days = (date.today() - origin).days
    if stale_days > 7:
        warnings.append(
            f"The last observed day is {origin.isoformat()}, {stale_days} days before this run. "
            "The forecast starts from stale data."
        )
    if profile_days < 28:
        warnings.append(
            f"The hourly profile rests on {profile_days} observed days instead of the usual 56."
        )
    degraded = [
        source.get("name")
        for source in (data.ingest_manifest or {}).get("sources", [])
        if source.get("status") not in (None, "ok")
    ]
    if degraded:
        warnings.append(f"The ingest manifest reports degraded sources: {', '.join(map(str, degraded))}.")
    return warnings


def _metrics_payload(
    *,
    venue: Venue,
    origin: date,
    history: pd.DataFrame,
    backtest: pd.DataFrame,
    metrics: dict[str, dict[str, dict[str, float | int]]],
    comparison: dict[str, dict[str, dict[str, bool | float]]],
    bands: dict[tuple[str, str], Band],
    model_names: tuple[str, ...],
    profile_days: int,
    open_hours: tuple[int, ...],
    future: pd.DataFrame,
    warnings: list[str],
    stamp: RunStamp,
) -> dict[str, Any]:
    """Assemble ``metrics.json`` for one venue."""
    window = backtest_window_of(backtest)
    climatology_days = int((future["weather_source"] == WEATHER_SOURCE_CLIMATOLOGY).sum())
    return {
        "venue_id": venue.venue_id,
        "venue_name": venue.name,
        "generated_at": stamp.generated_at,
        "trained_at": stamp.generated_at,
        "origin_date": origin.isoformat(),
        "n_training_days": len(history),
        "training_window": [
            str(history["date"].min().date()),
            str(history["date"].max().date()),
        ],
        "n_origins": origin_count(backtest),
        "backtest_window": list(window) if window else None,
        "horizon_buckets": list(BUCKET_LABELS),
        "models": list(model_names),
        "benchmarks": list(BENCHMARK_NAMES),
        "metrics": metrics,
        "benchmark_comparison": comparison,
        "coverage_method": "leave_one_origin_out",
        "interval_bands": {model: bands_to_dict(bands, model) for model in metrics},
        "hourly_profile": {
            "lookback_days": 56,
            "observed_days": profile_days,
            "open_hours": list(open_hours),
        },
        "weather": {
            "forecast_days": len(future) - climatology_days,
            "climatology_days": climatology_days,
            "max_forecast_days": MAX_WEATHER_FORECAST_DAYS,
        },
        "do_not_trust": list(STATIC_DO_NOT_TRUST),
        "warnings": warnings,
    }


def _log_honesty_gate(
    venue: Venue,
    metrics: dict[str, dict[str, dict[str, float | int]]],
    comparison: dict[str, dict[str, dict[str, bool | float]]],
) -> None:
    """Log, per model, whether the near horizon actually beats the naive benchmarks."""
    for model, buckets in comparison.items():
        entry = buckets.get(NEAR_HORIZON_BUCKET, {})
        beaten = [
            benchmark
            for benchmark in BENCHMARK_NAMES
            if entry.get(f"beats_{benchmark}") is False
        ]
        mae = metrics.get(model, {}).get(NEAR_HORIZON_BUCKET, {}).get("mae")
        if beaten:
            log_event(
                "warning",
                "quality-gate",
                "Model does not beat every benchmark at the near horizon",
                venue_id=venue.venue_id,
                model=model,
                bucket=NEAR_HORIZON_BUCKET,
                mae=mae,
                lost_to=beaten,
            )
        else:
            log_event(
                "info",
                "quality-gate",
                "Model beats every benchmark at the near horizon",
                venue_id=venue.venue_id,
                model=model,
                bucket=NEAR_HORIZON_BUCKET,
                mae=mae,
            )


# --------------------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------------------


def command_run(data: ProcessedData, args: argparse.Namespace) -> int:
    """Backtest, fit and export every selected venue."""
    stamp = RunStamp.now(_parse_moment(args.as_of))
    config = BacktestConfig(horizon_days=args.horizon_days, max_origins=args.origins)
    model_names = _selected_models(args.model)
    _, skipped = resolve_models(model_names)
    usable = tuple(name for name in model_names if name not in skipped)
    if not usable:
        log_event("error", "run", "No model available", requested=list(model_names))
        return EXIT_FAILED
    entries: list[dict[str, Any]] = []
    failed: list[int] = []
    for venue in data.select_venues(args.venue):
        entry = forecast_venue(data, venue, usable, config, stamp, hourly_days=args.hourly_days)
        if entry is None:
            failed.append(venue.venue_id)
        else:
            entries.append(entry)
    if not entries:
        return EXIT_FAILED
    warnings = sorted({warning for entry in entries for warning in entry["warnings"]})
    warnings.extend(
        f"Model {name} was skipped: its optional dependencies are not installed or not usable."
        for name in skipped
    )
    manifest = build_manifest(stamp, entries, list(usable), skipped, warnings, data.ingest_manifest)
    write_manifest(data.root, manifest)
    if not args.no_archive:
        archive_latest(data.root, stamp)
    log_event("info", "run", "Run complete", venues=[entry["venue_id"] for entry in entries])
    return EXIT_PARTIAL if failed else EXIT_OK


def command_backtest(data: ProcessedData, args: argparse.Namespace) -> int:
    """Run the rolling origin backtest and print the metrics, writing nothing."""
    config = BacktestConfig(horizon_days=args.horizon_days, max_origins=args.origins)
    model_names = _selected_models(args.model)
    _, skipped = resolve_models(model_names)
    usable = tuple(name for name in model_names if name not in skipped)
    if not usable:
        return EXIT_FAILED
    produced = 0
    for venue in data.select_venues(args.venue):
        history = venue_history(data, venue.venue_id)
        if history.empty:
            continue

        def factory() -> list[ForecastModel]:
            models, _ = resolve_models((*usable, *BENCHMARK_NAMES))
            return models

        origins = build_origins(history, config)
        backtest = run_backtest(data, venue.venue_id, history, factory, config)
        metrics = compute_metrics(backtest)
        comparison = compare_to_benchmarks(metrics, usable, BENCHMARK_NAMES)
        _print_metrics(venue, metrics, comparison, len(origins))
        _log_honesty_gate(venue, metrics, comparison)
        produced += 1
    return EXIT_OK if produced else EXIT_FAILED


def command_report(data: ProcessedData, args: argparse.Namespace) -> int:
    """Print the metrics of the last run in a readable form."""
    import json

    base = forecast_root(data.root) / LATEST_DIR
    found = 0
    for venue in data.select_venues(args.venue):
        path = venue_dir(base, venue.venue_id) / METRICS_NAME
        if not path.is_file():
            print(f"venue {venue.venue_id}: no metrics yet, run 'python -m ovf_forecast run' first")
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        _print_report(payload)
        found += 1
    return EXIT_OK if found else EXIT_FAILED


def command_evaluate(data: ProcessedData, args: argparse.Namespace) -> int:
    """Train on a chosen period, forecast another, and say whether the difference is real."""
    try:
        config, windows, sweep_kind = _evaluation_plan(data, args)
    except (WindowError, KeyError, ValueError) as exc:
        log_event("error", "evaluation", "Could not build the evaluation", error=str(exc))
        print(f"virhe: {exc}")
        return EXIT_FAILED
    if not config.models:
        log_event("error", "evaluation", "No usable model", requested=list(_evaluate_models(args)))
        return EXIT_FAILED
    result = evaluate(data, windows, config, sweep_kind=sweep_kind, moment=utc_now())
    if not result.produced_anything:
        return EXIT_FAILED
    print()
    print(result.summary)
    print()
    for run_id in result.run_ids:
        print(f"  tallennettu: data/evaluations/{run_id}/")
    if result.sweep_run_id:
        print(f"  kooste:      data/evaluations/{result.sweep_run_id}/")
    return EXIT_PARTIAL if result.failed_venues else EXIT_OK


def command_evaluate_report(data: ProcessedData, args: argparse.Namespace) -> int:
    """Print a stored evaluation report, or the pooled view across every stored run."""
    if args.pooled:
        pooled = pooled_report(data.root, _evaluation_config(data, args, TRAIN_WINDOW_ALL))
        if pooled is None:
            print("ei tallennettuja arviointiajoja, aja ensin 'python -m ovf_forecast evaluate'")
            return EXIT_FAILED
        print(pooled[0])
        return EXIT_OK
    if not args.id:
        print("anna joko --id <run_id> tai --pooled")
        return EXIT_FAILED
    artifacts = load_run(data.root, args.id)
    if artifacts is None:
        print(f"tuntematon ajo: {args.id}")
        return EXIT_FAILED
    print(artifacts.report)
    return EXIT_OK


def command_evaluate_list(data: ProcessedData, args: argparse.Namespace) -> int:
    """List the stored evaluation runs, newest first."""
    runs = list_runs(data.root)
    if not runs:
        print("ei tallennettuja arviointiajoja")
        return EXIT_FAILED
    print(f"{'run_id':<72}{'laji':>8}{'luotu':>22}  verdikti")
    for entry in runs[: args.limit]:
        verdicts = ", ".join(
            f"v{item['venue_id']}/{item['model']} vs {item['reference']}: {item['verdict']}"
            for item in entry.get("verdicts", [])
        )
        print(
            f"{entry.get('run_id', '')!s:<72}{entry.get('kind', '')!s:>8}"
            f"{entry.get('created_at', '')!s:>22}  {verdicts}"
        )
    return EXIT_OK


def _evaluation_plan(
    data: ProcessedData, args: argparse.Namespace
) -> tuple[EvaluationConfig, list[Any], str | None]:
    """Turn the evaluate arguments into a configuration and a list of windows."""
    train_window = args.train_window or TRAIN_WINDOW_ALL
    config = _evaluation_config(data, args, train_window)
    if args.sweep == "monthly":
        if not (args.from_month and args.to_month):
            raise WindowError("--sweep monthly tarvitsee sekä --from että --to (YYYY-MM).")
        _, last_day = history_bounds(data, config.venues)
        return config, monthly_sweep(
            first_month=args.from_month,
            last_month=args.to_month,
            history_last_day=last_day,
            train_window=train_window,
        ), "monthly"
    if args.sweep == "rolling":
        first_day, last_day = history_bounds(data, config.venues)
        return config, rolling_sweep(
            history_first_day=first_day,
            history_last_day=last_day,
            step_days=args.step,
            horizon_days=args.horizon,
            train_window=train_window,
            max_windows=args.max_windows,
        ), "rolling"
    if not args.test:
        raise WindowError(
            "Anna joko --test (esim. --test 2026-04) tai --sweep monthly|rolling."
        )
    window = make_window(test=args.test, train_end=args.train_end, train_window=train_window)
    return config, [window], None


def _evaluation_config(
    data: ProcessedData, args: argparse.Namespace, train_window: str
) -> EvaluationConfig:
    """Build the evaluation configuration, dropping models whose extras are missing."""
    requested = _evaluate_models(args)
    _, skipped = resolve_models(requested)
    usable = tuple(name for name in requested if name not in skipped)
    modes = resolve_weather_modes(_split(getattr(args, "weather", None)))
    primary = DEFAULT_WEATHER_MODE if DEFAULT_WEATHER_MODE in modes else modes[0]
    venues = tuple(args.venue) if args.venue else None
    if venues:
        for venue_id in venues:
            data.venue(venue_id)
    return EvaluationConfig(
        models=usable,
        weather_modes=modes,
        primary_weather_mode=primary,
        reference=args.reference,
        venues=venues,
        train_window=train_window,
        n_resamples=args.resamples,
        seed=args.seed,
    )


def _evaluate_models(args: argparse.Namespace) -> tuple[str, ...]:
    """The models the caller asked for, defaulting to every production model."""
    requested = _split(getattr(args, "models", None))
    return tuple(dict.fromkeys(requested)) if requested else MODEL_NAMES


def _split(text: str | None) -> tuple[str, ...] | None:
    """Split a comma separated CLI value."""
    if not text:
        return None
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _print_metrics(
    venue: Venue,
    metrics: dict[str, dict[str, dict[str, float | int]]],
    comparison: dict[str, dict[str, dict[str, bool | float]]],
    origins: int,
) -> None:
    """Print a metrics table for one venue."""
    print(f"\nvenue {venue.venue_id} ({venue.name}), {origins} origins")
    print(f"{'model':<20}{'horizon':>9}{'MAE':>10}{'RMSE':>10}{'sMAPE':>9}{'bias':>10}{'cover80':>9}{'n':>6}")
    for model, buckets in metrics.items():
        for bucket, values in buckets.items():
            print(
                f"{model:<20}{bucket:>9}{values['mae']:>10.1f}{values['rmse']:>10.1f}"
                f"{values['smape']:>9.1f}{values['bias']:>10.1f}{values['coverage_80']:>9.2f}"
                f"{values['n']:>6}"
            )
    for model, buckets in comparison.items():
        for bucket, entry in buckets.items():
            verdicts = [
                f"{key.removeprefix('beats_')}: {'wins' if value else 'LOSES'}"
                for key, value in entry.items()
                if key.startswith("beats_")
            ]
            if verdicts:
                print(f"  {model} @ {bucket} vs benchmarks -> {', '.join(verdicts)}")


def _print_report(payload: dict[str, Any]) -> None:
    """Print one venue's stored metrics file."""
    print(f"\nvenue {payload['venue_id']} ({payload.get('venue_name')})")
    print(
        f"  origin {payload['origin_date']}, {payload['n_training_days']} training days, "
        f"{payload['n_origins']} backtest origins, generated {payload['generated_at']}"
    )
    print(f"{'model':<20}{'horizon':>9}{'MAE':>10}{'RMSE':>10}{'sMAPE':>9}{'bias':>10}{'cover80':>9}{'n':>6}")
    for model, buckets in payload.get("metrics", {}).items():
        for bucket, values in buckets.items():
            print(
                f"{model:<20}{bucket:>9}{values['mae']:>10.1f}{values['rmse']:>10.1f}"
                f"{values['smape']:>9.1f}{values['bias']:>10.1f}"
                f"{(values['coverage_80'] if values['coverage_80'] is not None else float('nan')):>9.2f}"
                f"{values['n']:>6}"
            )
    for model, buckets in payload.get("benchmark_comparison", {}).items():
        for bucket, entry in buckets.items():
            verdicts = [
                f"{key.removeprefix('beats_')}: {'wins' if value else 'LOSES'}"
                for key, value in entry.items()
                if key.startswith("beats_")
            ]
            if verdicts:
                print(f"  {model} @ {bucket} vs benchmarks -> {', '.join(verdicts)}")
    for warning in payload.get("warnings", []):
        print(f"  warning: {warning}")


def _selected_models(requested: list[str] | None) -> tuple[str, ...]:
    """The models to run, defaulting to both."""
    if not requested:
        return MODEL_NAMES
    return tuple(dict.fromkeys(requested))


def _parse_moment(text: str | None) -> datetime | None:
    """Parse the ``--as-of`` override used to make a run byte-reproducible."""
    if not text:
        return None
    return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(UTC)


def build_parser() -> argparse.ArgumentParser:
    """Build the ``python -m ovf_forecast`` argument parser."""
    parser = argparse.ArgumentParser(prog="ovf_forecast", description="Oulu2026 visitor flow forecast")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument(
        "--log-level", choices=["debug", "info", "warning", "error"], default="info", help="Minimum log level"
    )
    parser.add_argument("--root", type=Path, default=None, help="Repository root (defaults to autodetect)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Backtest, fit and export the forecasts")
    _add_shared_arguments(run_parser)
    run_parser.add_argument(
        "--hourly-days", type=int, default=DEFAULT_HOURLY_DAYS, help="Days covered by the hourly export"
    )
    run_parser.add_argument("--no-archive", action="store_true", help="Skip the dated archive copy")
    run_parser.add_argument("--as-of", default=None, help="Override the run timestamp, for reproducible runs")
    run_parser.set_defaults(handler=command_run)

    backtest_parser = subparsers.add_parser("backtest", help="Validate without writing forecasts")
    _add_shared_arguments(backtest_parser)
    backtest_parser.set_defaults(handler=command_backtest)

    report_parser = subparsers.add_parser("report", help="Print the metrics of the last run")
    report_parser.add_argument("--venue", action="append", type=int, default=None, help="Limit to one venue")
    report_parser.set_defaults(handler=command_report)

    _add_evaluate_parser(subparsers)
    return parser


def _add_evaluate_parser(subparsers: Any) -> None:
    """Wire ``evaluate``, plus its ``report`` and ``list`` sub-actions."""
    parser = subparsers.add_parser(
        "evaluate", help="Measure forecast accuracy on a chosen window and store the result"
    )
    parser.add_argument("--train-end", default=None, help="Last training day, YYYY-MM-DD")
    parser.add_argument(
        "--test", default=None, help="Test period: YYYY-MM, YYYY-MM-DD or YYYY-MM-DD:YYYY-MM-DD"
    )
    parser.add_argument("--sweep", choices=["monthly", "rolling"], default=None, help="Run many windows")
    parser.add_argument("--from", dest="from_month", default=None, help="First month of a monthly sweep")
    parser.add_argument("--to", dest="to_month", default=None, help="Last month of a monthly sweep")
    parser.add_argument(
        "--step", type=int, default=DEFAULT_ROLLING_STEP_DAYS, help="Days between rolling origins"
    )
    parser.add_argument(
        "--horizon", type=int, default=DEFAULT_ROLLING_HORIZON_DAYS, help="Rolling test period length"
    )
    parser.add_argument(
        "--max-windows", type=int, default=DEFAULT_MAX_WINDOWS, help="Cap on rolling windows"
    )
    parser.add_argument(
        "--models", default=None, help=f"Comma separated: {', '.join(MODEL_NAMES)}"
    )
    parser.add_argument(
        "--reference",
        choices=list(REFERENCE_CHOICES),
        default="best",
        help="Reference for the verdict; 'best' picks the hardest baseline per window",
    )
    parser.add_argument(
        "--weather", default=None, help=f"Comma separated weather modes: {', '.join(WEATHER_MODES)}"
    )
    parser.add_argument(
        "--train-window", default=TRAIN_WINDOW_ALL, help="'all' or a number of days"
    )
    parser.add_argument("--venue", action="append", type=int, default=None, help="Limit to one venue")
    parser.add_argument("--resamples", type=int, default=N_RESAMPLES, help="Bootstrap resamples")
    parser.add_argument("--seed", type=int, default=RANDOM_SEED, help="Bootstrap seed")
    parser.set_defaults(handler=command_evaluate, pooled=False, id=None, limit=20)

    actions = parser.add_subparsers(dest="evaluate_action", required=False)
    report_action = actions.add_parser("report", help="Print a stored evaluation report")
    report_action.add_argument("--id", default=None, help="Run id to print")
    report_action.add_argument(
        "--pooled", action="store_true", help="Pool every stored run into one verdict"
    )
    report_action.set_defaults(handler=command_evaluate_report)

    list_action = actions.add_parser("list", help="List the stored evaluation runs")
    list_action.add_argument("--limit", type=int, default=20, help="How many runs to show")
    list_action.set_defaults(handler=command_evaluate_list)


def _add_shared_arguments(parser: argparse.ArgumentParser) -> None:
    """Arguments shared by ``run`` and ``backtest``."""
    parser.add_argument(
        "--model", action="append", default=None, help=f"Limit to one model: {', '.join(MODEL_NAMES)}"
    )
    parser.add_argument("--venue", action="append", type=int, default=None, help="Limit to one venue")
    parser.add_argument(
        "--horizon-days", type=int, default=DEFAULT_HORIZON_DAYS, help="Daily forecast horizon"
    )
    parser.add_argument(
        "--origins", type=int, default=BacktestConfig().max_origins, help="Maximum rolling origins"
    )


def main(argv: list[str] | None = None) -> int:
    """Entry point for ``python -m ovf_forecast``."""
    parser = build_parser()
    args = parser.parse_args(argv)
    level: LogLevel = args.log_level
    set_log_level(level)
    try:
        data = load_dataset(args.root)
        handler: Callable[[ProcessedData, argparse.Namespace], int] = args.handler
        return int(handler(data, args))
    except KeyboardInterrupt:
        log_event("error", "cli", "Interrupted")
        return EXIT_FAILED
    except Exception as exc:
        log_event("error", "cli", "Run failed", error=str(exc), error_type=type(exc).__name__)
        return EXIT_FAILED
