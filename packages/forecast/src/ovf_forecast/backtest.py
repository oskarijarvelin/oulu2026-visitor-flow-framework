"""Rolling origin backtest and the metrics computed from it.

One origin is one honest question: standing on day *o*, knowing nothing after it, how
wrong is this model 1 to 30 days out? Origins step back a week at a time, each one
refits every model on the data available at that point, and the answers are pooled by
horizon bucket.

The reference implementation measures quality on a single 80/20 time split, which is
one observation of model quality dressed up as a metric. Eight to twelve origins is
still a small sample, and the metrics file says so, but it is a sample.

Two details keep the exercise honest. Training stops at the origin, including for the
level features and the hourly profile. And the weather covariates degrade to
climatology past day 16 exactly as they will in production, so the long-horizon numbers
are measured on the same smoothed weather they will be run on.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from . import log_event
from .dataset import ProcessedData, as_float, as_int, as_timestamp, venue_future
from .features import build_future_frame, build_training_frame
from .intervals import BUCKET_LABELS, Band, apply_bands, bucket_series, fit_bands
from .models.base import ForecastModel

BACKTEST_COLUMNS = [
    "model",
    "venue_id",
    "origin_date",
    "target_date",
    "horizon_days",
    "y_true",
    "y_pred",
    "p10",
    "p90",
]

DEFAULT_HORIZON_DAYS = 30
DEFAULT_STEP_DAYS = 7
DEFAULT_MAX_ORIGINS = 12
MIN_ORIGINS = 8
MIN_TRAINING_DAYS = 60
# sMAPE needs both sides to be non-trivial; a closed day is not a forecasting failure.
SMAPE_MIN_DENOMINATOR = 1.0


@dataclass(frozen=True)
class BacktestConfig:
    """How far back the origins go and how much history each one needs."""

    horizon_days: int = DEFAULT_HORIZON_DAYS
    step_days: int = DEFAULT_STEP_DAYS
    max_origins: int = DEFAULT_MAX_ORIGINS
    min_origins: int = MIN_ORIGINS
    min_training_days: int = MIN_TRAINING_DAYS


def build_origins(history: pd.DataFrame, config: BacktestConfig) -> list[date]:
    """Origins stepping back one week at a time from the last observed day.

    An origin is only used when its training window holds at least
    ``min_training_days`` days. On 4.5 months of data that is the binding constraint,
    not ``max_origins``.
    """
    if history.empty:
        return []
    last = as_timestamp(history["date"].max())
    first = as_timestamp(history["date"].min())
    origins: list[date] = []
    for step in range(1, config.max_origins + 1):
        origin = last - pd.Timedelta(days=config.step_days * step)
        training_days = int((origin - first).days) + 1
        if training_days < config.min_training_days:
            break
        origins.append(origin.date())
    if len(origins) < config.min_origins:
        log_event(
            "warning",
            "backtest",
            "Fewer origins than the plan asks for; the interval quantiles rest on a thin sample",
            origins=len(origins),
            wanted=config.min_origins,
            min_training_days=config.min_training_days,
        )
    return origins


def run_backtest(
    data: ProcessedData,
    venue_id: int,
    history: pd.DataFrame,
    model_factory: Callable[[], list[ForecastModel]],
    config: BacktestConfig,
) -> pd.DataFrame:
    """Fit and score every model on every origin. Returns one row per prediction."""
    origins = build_origins(history, config)
    records: list[dict[str, object]] = []
    actuals = history.set_index("date")["visitors_total"]
    for origin in origins:
        training = build_training_frame(history, origin)
        future_covariates = venue_future(data, venue_id, origin, config.horizon_days)
        future = build_future_frame(history, future_covariates, origin)
        keep = future["date"].isin(actuals.index)
        if not bool(keep.any()):
            continue
        target_days = future["date"].to_numpy()
        horizons = future["horizon_days"].to_numpy()
        scored = np.flatnonzero(keep.to_numpy())
        for model in model_factory():
            model.fit(training)
            predicted = model.predict(future).to_numpy()
            for position in scored:
                target_day = as_timestamp(target_days[position])
                records.append(
                    {
                        "model": model.name,
                        "venue_id": venue_id,
                        "origin_date": origin.isoformat(),
                        "target_date": target_day.date().isoformat(),
                        "horizon_days": as_int(horizons[position]),
                        "y_true": as_float(actuals.loc[target_day]),
                        "y_pred": float(predicted[position]),
                    }
                )
        log_event("debug", "backtest", "Scored one origin", venue_id=venue_id, origin=origin.isoformat())
    if not records:
        return pd.DataFrame(columns=BACKTEST_COLUMNS)
    frame = pd.DataFrame.from_records(records)
    return add_out_of_sample_intervals(frame)


def add_out_of_sample_intervals(backtest: pd.DataFrame) -> pd.DataFrame:
    """Attach p10 and p90 fitted without the origin they are applied to.

    Fitting the band on all origins and then scoring coverage on those same rows would
    return 80 % by construction and prove nothing. Leaving each origin out in turn makes
    the reported coverage a real out-of-sample number.
    """
    frame = backtest.copy()
    frame["p10"] = np.nan
    frame["p90"] = np.nan
    for origin in sorted(frame["origin_date"].unique()):
        bands = fit_bands(frame, exclude_origin=str(origin))
        mask = frame["origin_date"] == origin
        for model in sorted(frame.loc[mask, "model"].unique()):
            rows = frame.loc[mask & (frame["model"] == model)]
            p10, p90 = apply_bands(rows["y_pred"], rows["horizon_days"], bands, str(model))
            frame.loc[rows.index, "p10"] = p10
            frame.loc[rows.index, "p90"] = p90
    return frame[BACKTEST_COLUMNS]


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------


def compute_metrics(backtest: pd.DataFrame) -> dict[str, dict[str, dict[str, float | int]]]:
    """MAE, RMSE, sMAPE, bias and 80 % coverage per model and horizon bucket."""
    if backtest.empty:
        return {}
    frame = backtest.assign(bucket=bucket_series(backtest["horizon_days"]))
    metrics: dict[str, dict[str, dict[str, float | int]]] = {}
    for model in sorted(frame["model"].unique()):
        per_bucket: dict[str, dict[str, float | int]] = {}
        for bucket in BUCKET_LABELS:
            rows = frame.loc[(frame["model"] == model) & (frame["bucket"] == bucket)]
            if rows.empty:
                continue
            per_bucket[bucket] = _bucket_metrics(rows)
        metrics[str(model)] = per_bucket
    return metrics


def _bucket_metrics(rows: pd.DataFrame) -> dict[str, float | int]:
    """Metrics for one model in one horizon bucket."""
    y_true = pd.to_numeric(rows["y_true"], errors="coerce").astype("float64")
    y_pred = pd.to_numeric(rows["y_pred"], errors="coerce").astype("float64")
    error = y_pred - y_true
    covered = pd.to_numeric(rows["p10"], errors="coerce").notna() & pd.to_numeric(
        rows["p90"], errors="coerce"
    ).notna()
    inside = (y_true >= rows["p10"]) & (y_true <= rows["p90"])
    return {
        "mae": _round(error.abs().mean()),
        "rmse": _round(float(np.sqrt(float((error**2).mean())))),
        "smape": _round(_smape(y_true, y_pred)),
        "bias": _round(error.mean()),
        "coverage_80": _round(float(inside.loc[covered].mean()) if bool(covered.any()) else float("nan"), 4),
        "n": len(rows),
    }


def _smape(y_true: pd.Series, y_pred: pd.Series) -> float:
    """Symmetric MAPE in percent, skipping days where both sides are near zero."""
    denominator = (y_true.abs() + y_pred.abs()) / 2.0
    usable = denominator >= SMAPE_MIN_DENOMINATOR
    if not bool(usable.any()):
        return float("nan")
    ratio = (y_pred - y_true).abs().loc[usable] / denominator.loc[usable]
    return float(ratio.mean() * 100.0)


def _round(value: float, digits: int = 3) -> float:
    """Round for the metrics file, keeping NaN as NaN."""
    if value is None or not np.isfinite(value):
        return float("nan")
    return float(round(float(value), digits))


def compare_to_benchmarks(
    metrics: dict[str, dict[str, dict[str, float | int]]],
    models: tuple[str, ...],
    benchmarks: tuple[str, ...],
) -> dict[str, dict[str, dict[str, bool | float]]]:
    """Per model and bucket, whether each benchmark is beaten on MAE and by how much.

    This is the honesty gate from the plan. A model that loses to "same weekday last
    week" is reported as losing, in the metrics file and on the console.
    """
    comparison: dict[str, dict[str, dict[str, bool | float]]] = {}
    for model in models:
        if model not in metrics:
            continue
        per_bucket: dict[str, dict[str, bool | float]] = {}
        for bucket, values in metrics[model].items():
            entry: dict[str, bool | float] = {}
            model_mae = float(values["mae"])
            for benchmark in benchmarks:
                benchmark_mae = metrics.get(benchmark, {}).get(bucket, {}).get("mae")
                if benchmark_mae is None or not np.isfinite(float(benchmark_mae)):
                    continue
                entry[f"beats_{benchmark}"] = bool(model_mae < float(benchmark_mae))
                entry[f"mae_ratio_vs_{benchmark}"] = _round(model_mae / float(benchmark_mae), 4)
            per_bucket[bucket] = entry
        comparison[model] = per_bucket
    return comparison


def backtest_window(backtest: pd.DataFrame) -> tuple[str, str] | None:
    """First and last target day covered by the backtest."""
    if backtest.empty:
        return None
    return str(backtest["target_date"].min()), str(backtest["target_date"].max())


def origin_count(backtest: pd.DataFrame) -> int:
    """Number of distinct origins in a backtest frame."""
    return 0 if backtest.empty else int(backtest["origin_date"].nunique())


def production_bands(backtest: pd.DataFrame) -> dict[tuple[str, str], Band]:
    """The bands used for the exported forecast: every origin, nothing held out."""
    return fit_bands(backtest)


def horizon_span(config: BacktestConfig) -> list[int]:
    """Every horizon the backtest covers."""
    return list(range(1, config.horizon_days + 1))


def origin_of(history: pd.DataFrame) -> date:
    """The production origin: the last observed day."""
    return as_timestamp(history["date"].max()).date()


def next_days(origin: date, horizon_days: int) -> list[date]:
    """The forecast days of the production run."""
    return [origin + timedelta(days=step) for step in range(1, horizon_days + 1)]
