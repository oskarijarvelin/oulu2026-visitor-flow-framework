"""How many visitors in the whole period, and how sure is that number.

A producer asks "how many people in April", not "what was the daily MAE". The two
questions have different answers and neither implies the other: on this dataset the
April ``climatology_dow`` reference lands within 0.8 % of the month's true total while
missing individual days by 96 visitors, about 22 % of an average day. Daily errors of
opposite sign cancel in a sum, so a flat rule can be excellent at the month and poor at
the day at the same time.

The interval is simulated, never summed. Adding up thirty daily p10 values and thirty
daily p90 values answers a different question — "what if every single day landed at its
own tenth percentile" — and that scenario needs all thirty errors to point the same way.
The old application shipped that mistake and its monthly bands were unusable. Here the
relative daily errors measured inside the training window are block-resampled into whole
simulated months, each month is summed, and the interval is read off the distribution of
those sums.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from .. import log_event
from .significance import (
    BLOCK_LENGTH_DAYS,
    CONFIDENCE,
    N_RESAMPLES,
    RANDOM_SEED,
    block_bootstrap_indices,
    rng,
)

LOWER_QUANTILE = 0.10
UPPER_QUANTILE = 0.90
# A relative error needs a denominator worth dividing by.
MIN_DENOMINATOR = 1.0
# Below this the pool of measured errors is too thin to describe a month's spread.
MIN_RATIO_SAMPLES = 14
# A median relative error this far from 1 means the nested backtest's models were in a
# different regime from the outer one, and the simulated interval inherits their level.
MAX_MEDIAN_DRIFT = 0.25
# Used only when the nested backtest produced no usable relative errors at all.
FALLBACK_RATIOS = (0.6, 0.8, 0.9, 1.0, 1.1, 1.25, 1.6)


@dataclass(frozen=True)
class TotalEstimate:
    """One model's forecast for the whole period, against what actually happened."""

    model: str
    weather_mode: str
    predicted: float
    actual: float
    difference: float
    difference_pct: float
    p10: float
    p90: float
    summed_p10: float
    summed_p90: float
    n_ratio_samples: int
    is_thin: bool
    median_ratio: float

    @property
    def is_drifted(self) -> bool:
        """Whether the measured errors carry a level bias, not just a spread."""
        return bool(
            np.isfinite(self.median_ratio) and abs(self.median_ratio - 1.0) > MAX_MEDIAN_DRIFT
        )

    @property
    def covers_actual(self) -> bool:
        """Whether the simulated 80 % interval contains the true total."""
        return bool(self.p10 <= self.actual <= self.p90)

    @property
    def width(self) -> float:
        """Width of the simulated interval."""
        return self.p90 - self.p10

    @property
    def summed_width(self) -> float:
        """Width of the naive interval, the one that adds up the daily bands."""
        return self.summed_p90 - self.summed_p10

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``metrics.json``."""
        return {
            "model": self.model,
            "weather_mode": self.weather_mode,
            "predicted": _round(self.predicted, 1),
            "actual": _round(self.actual, 1),
            "difference": _round(self.difference, 1),
            "difference_pct": _round(self.difference_pct, 2),
            "p10": _round(self.p10, 1),
            "p90": _round(self.p90, 1),
            "covers_actual": self.covers_actual,
            "summed_daily_p10": _round(self.summed_p10, 1),
            "summed_daily_p90": _round(self.summed_p90, 1),
            "interval_method": "block_bootstrap_of_training_window_relative_errors",
            "n_ratio_samples": self.n_ratio_samples,
            "is_thin": self.is_thin,
            "median_ratio": _round(self.median_ratio, 3),
            "is_drifted": self.is_drifted,
        }


def relative_errors(y_true: np.ndarray, y_pred: np.ndarray) -> np.ndarray:
    """``y_true / y_pred`` for the rows where the ratio means something."""
    actual = np.asarray(y_true, dtype="float64")
    predicted = np.asarray(y_pred, dtype="float64")
    usable = np.isfinite(actual) & np.isfinite(predicted) & (predicted >= MIN_DENOMINATOR)
    if not bool(usable.any()):
        return np.zeros(0, dtype="float64")
    return np.asarray(actual[usable] / predicted[usable], dtype="float64")


def estimate_total(
    *,
    model: str,
    weather_mode: str,
    daily_p50: np.ndarray,
    daily_p10: np.ndarray,
    daily_p90: np.ndarray,
    actual: np.ndarray,
    ratios: np.ndarray,
    n_resamples: int = N_RESAMPLES,
    block_length: int = BLOCK_LENGTH_DAYS,
    seed: int = RANDOM_SEED,
) -> TotalEstimate:
    """Period total with an interval simulated from measured relative daily errors."""
    p50 = np.asarray(daily_p50, dtype="float64")
    truth = np.asarray(actual, dtype="float64")
    predicted_total = float(np.nansum(p50))
    actual_total = float(np.nansum(truth))
    pool = np.asarray(ratios, dtype="float64")
    pool = pool[np.isfinite(pool)]
    is_thin = pool.size < MIN_RATIO_SAMPLES
    if is_thin:
        log_event(
            "warning",
            "evaluation.totals",
            "Thin pool of relative errors, the period interval rests on few observations",
            model=model,
            weather_mode=weather_mode,
            samples=int(pool.size),
            minimum=MIN_RATIO_SAMPLES,
        )
    if pool.size == 0:
        pool = np.asarray(FALLBACK_RATIOS, dtype="float64")
    totals = simulate_totals(
        p50, pool, n_resamples=n_resamples, block_length=block_length, seed=seed
    )
    lower = float(np.percentile(totals, LOWER_QUANTILE * 100.0))
    upper = float(np.percentile(totals, UPPER_QUANTILE * 100.0))
    # The point forecast has to lie inside its own interval. A band that excludes the
    # number it is a band for cannot be published, and the daily bands in
    # :mod:`ovf_forecast.intervals` already take the same position for the same reason.
    # It is not a way of hiding the level shift: the shift is reported as bias, as the
    # difference column of the totals table, and as ``median_ratio`` right here.
    lower, upper = min(lower, predicted_total), max(upper, predicted_total)
    median_ratio = float(np.median(pool)) if pool.size else float("nan")
    if abs(median_ratio - 1.0) > MAX_MEDIAN_DRIFT:
        log_event(
            "warning",
            "evaluation.totals",
            "The nested backtest's relative errors carry a level bias; the period interval "
            "inherits it and should not be read as calibrated",
            model=model,
            weather_mode=weather_mode,
            median_ratio=round(median_ratio, 3),
        )
    difference = predicted_total - actual_total
    return TotalEstimate(
        model=model,
        weather_mode=weather_mode,
        predicted=predicted_total,
        actual=actual_total,
        difference=difference,
        difference_pct=difference / actual_total * 100.0 if actual_total > 0 else float("nan"),
        p10=lower,
        p90=upper,
        summed_p10=float(np.nansum(np.asarray(daily_p10, dtype="float64"))),
        summed_p90=float(np.nansum(np.asarray(daily_p90, dtype="float64"))),
        n_ratio_samples=int(np.asarray(ratios, dtype="float64").size),
        is_thin=is_thin,
        median_ratio=median_ratio,
    )


def simulate_totals(
    daily_p50: np.ndarray,
    ratios: np.ndarray,
    *,
    n_resamples: int = N_RESAMPLES,
    block_length: int = BLOCK_LENGTH_DAYS,
    seed: int = RANDOM_SEED,
) -> np.ndarray:
    """One simulated period total per resample.

    Each resample draws a whole path of relative errors in blocks, so a simulated month
    can have a run of over-forecast days followed by a run of under-forecast ones — which
    is what the measured errors do — instead of the perfectly correlated month that
    summing the daily bands assumes.
    """
    p50 = np.asarray(daily_p50, dtype="float64")
    pool = np.asarray(ratios, dtype="float64")
    n_days = int(p50.size)
    if n_days == 0 or pool.size == 0:
        return np.zeros(1, dtype="float64")
    indices = block_bootstrap_indices(
        n_days,
        source_length=int(pool.size),
        block_length=block_length,
        n_resamples=n_resamples,
        generator=rng(seed),
    )
    paths = pool[indices] * np.nan_to_num(p50, nan=0.0)[None, :]
    return np.asarray(paths.sum(axis=1), dtype="float64")


def summed_interval_is_wider(estimate: TotalEstimate) -> bool:
    """Whether the naive summed band is wider than the simulated one, as it should be."""
    if not np.isfinite(estimate.summed_width) or not np.isfinite(estimate.width):
        return False
    return estimate.summed_width > estimate.width


def _round(value: float, digits: int = 3) -> float:
    """Round for the metrics file, keeping NaN as NaN."""
    if value is None or not np.isfinite(value):
        return float("nan")
    return float(round(float(value), digits))


__all__ = [
    "CONFIDENCE",
    "TotalEstimate",
    "estimate_total",
    "relative_errors",
    "simulate_totals",
    "summed_interval_is_wider",
]
