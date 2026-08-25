"""Is the difference real, or is it thirty days of noise?

The comparison is always paired and always on the same days:

    d_t = |y_t - model_t| - |y_t - reference_t|

A negative mean says the model is closer. The question is whether a mean that negative
could have come out of a model that is exactly as good as the reference, and the answer
comes from a moving block bootstrap with a block length of seven days, because visitor
counts on consecutive days are not independent draws and a day-wise bootstrap would
report a confidence interval roughly a third too narrow.

Three deliberate positions are worth stating.

*The bootstrap interval is primary.* Diebold-Mariano is computed too, with a
Newey-West variance and the Harvey-Leybourne-Newbold small sample correction, but it is
reported as secondary. Thirty errors from one origin are not thirty independent
observations: they share a training set and a month of weather. DM's assumptions are
stretched here and the report says so rather than quietly relying on them.

*The p-value comes from the bootstrap, not from a t table.* There is no scipy in this
package's dependency group and there is no reason to add one: recentring the block
bootstrap gives an honest null distribution for the DM statistic without importing a
distribution function.

*A power number is part of every verdict.* "No detectable difference" and "no
difference" are different claims, and only the minimum detectable effect separates them.
On a one-month window it lands around 30 % of the reference's MAE, which means one month
can only prove large improvements. That number goes in the report whether or not anyone
asked for it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

BLOCK_LENGTH_DAYS = 7
N_RESAMPLES = 10_000
CONFIDENCE = 0.95
RANDOM_SEED = 20260101

VERDICT_BETTER = "better"
VERDICT_WORSE = "worse"
VERDICT_NO_DIFFERENCE = "no_difference"

CALIBRATION_OK = "calibrated"
CALIBRATION_NARROW = "too_narrow"
CALIBRATION_WIDE = "too_wide"

BIAS_NONE = "unbiased"
BIAS_OVER = "over_forecast"
BIAS_UNDER = "under_forecast"

# 2.8 is the two-sided 5 % / 80 % power constant, z(0.975) + z(0.80) = 1.96 + 0.84.
MDE_CONSTANT = 2.8
_TINY_VARIANCE = 1e-12


def rng(seed: int = RANDOM_SEED) -> np.random.Generator:
    """The one random source in the package. Fixed seed, so a run is reproducible."""
    return np.random.default_rng(seed)


# --------------------------------------------------------------------------------------
# Moving block bootstrap
# --------------------------------------------------------------------------------------


def block_bootstrap_indices(
    n: int,
    *,
    source_length: int | None = None,
    block_length: int = BLOCK_LENGTH_DAYS,
    n_resamples: int = N_RESAMPLES,
    generator: np.random.Generator | None = None,
) -> np.ndarray:
    """Index matrix of shape ``(n_resamples, n)`` drawn as overlapping blocks of days.

    Blocks preserve the weekly rhythm inside each resample. Resampling single days would
    treat a quiet Monday and the Saturday after it as independent, which they are not.

    ``source_length`` lets a path of ``n`` days be built out of a pool of a different
    size, which is what :mod:`.totals` needs when it simulates a 30 day month from a
    90 day pool of measured relative errors.
    """
    if n <= 0:
        return np.zeros((n_resamples, 0), dtype="int64")
    pool = n if source_length is None else int(source_length)
    if pool <= 0:
        return np.zeros((n_resamples, 0), dtype="int64")
    source = generator if generator is not None else rng()
    length = max(1, min(block_length, pool))
    n_blocks = math.ceil(n / length)
    starts = source.integers(0, pool - length + 1, size=(n_resamples, n_blocks))
    offsets = np.arange(length, dtype="int64")
    indices = (starts[:, :, None] + offsets[None, None, :]).reshape(n_resamples, n_blocks * length)
    return np.asarray(indices[:, :n], dtype="int64")


def resample(values: np.ndarray, indices: np.ndarray) -> np.ndarray:
    """Apply a bootstrap index matrix to one series."""
    return np.asarray(np.asarray(values)[indices], dtype="float64")


def percentile_interval(samples: np.ndarray, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """Percentile confidence interval of a bootstrap distribution."""
    finite = samples[np.isfinite(samples)]
    if finite.size == 0:
        return float("nan"), float("nan")
    tail = (1.0 - confidence) / 2.0 * 100.0
    return float(np.percentile(finite, tail)), float(np.percentile(finite, 100.0 - tail))


# --------------------------------------------------------------------------------------
# One window: model against one reference
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Comparison:
    """One model against one reference on one window's days."""

    model: str
    reference: str
    n: int
    mean_difference: float
    ci_low: float
    ci_high: float
    verdict: str
    model_mae: float
    reference_mae: float
    skill_score: float
    skill_ci_low: float
    skill_ci_high: float
    mde: float
    mde_pct: float
    dm_statistic: float
    dm_p_value: float
    dm_lag: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``verdicts.json``."""
        return {
            "model": self.model,
            "reference": self.reference,
            "n": self.n,
            "mean_difference": _round(self.mean_difference),
            "ci_low": _round(self.ci_low),
            "ci_high": _round(self.ci_high),
            "verdict": self.verdict,
            "model_mae": _round(self.model_mae),
            "reference_mae": _round(self.reference_mae),
            "skill_score": _round(self.skill_score, 4),
            "skill_ci_low": _round(self.skill_ci_low, 4),
            "skill_ci_high": _round(self.skill_ci_high, 4),
            "mde": _round(self.mde),
            "mde_pct": _round(self.mde_pct, 2),
            "dm_statistic": _round(self.dm_statistic),
            "dm_p_value": _round(self.dm_p_value, 5),
            "dm_lag": self.dm_lag,
            "dm_note": (
                "Secondary. The days of one origin share a training set and a month of "
                "weather, so they are not independent observations."
            ),
        }


def compare(
    model_absolute_errors: np.ndarray,
    reference_absolute_errors: np.ndarray,
    *,
    model: str,
    reference: str,
    n_resamples: int = N_RESAMPLES,
    block_length: int = BLOCK_LENGTH_DAYS,
    confidence: float = CONFIDENCE,
    seed: int = RANDOM_SEED,
) -> Comparison:
    """Bootstrap interval, skill score, power and DM for one paired error series."""
    model_errors = np.asarray(model_absolute_errors, dtype="float64")
    reference_errors = np.asarray(reference_absolute_errors, dtype="float64")
    if model_errors.shape != reference_errors.shape:
        raise ValueError(
            f"Paired comparison needs equal length series, got {model_errors.shape} and "
            f"{reference_errors.shape}."
        )
    difference = model_errors - reference_errors
    n = int(difference.size)
    if n == 0:
        return _empty_comparison(model, reference)

    indices = block_bootstrap_indices(
        n, block_length=block_length, n_resamples=n_resamples, generator=rng(seed)
    )
    difference_samples = resample(difference, indices).mean(axis=1)
    model_mae_samples = resample(model_errors, indices).mean(axis=1)
    reference_mae_samples = resample(reference_errors, indices).mean(axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        skill_samples = 1.0 - model_mae_samples / reference_mae_samples

    ci_low, ci_high = percentile_interval(difference_samples, confidence)
    skill_low, skill_high = percentile_interval(skill_samples, confidence)
    model_mae = float(model_errors.mean())
    reference_mae = float(reference_errors.mean())
    mde = minimum_detectable_effect(difference)
    statistic, lag = diebold_mariano(difference)
    return Comparison(
        model=model,
        reference=reference,
        n=n,
        mean_difference=float(difference.mean()),
        ci_low=ci_low,
        ci_high=ci_high,
        verdict=verdict_from_interval(ci_low, ci_high),
        model_mae=model_mae,
        reference_mae=reference_mae,
        skill_score=1.0 - model_mae / reference_mae if reference_mae > 0 else float("nan"),
        skill_ci_low=skill_low,
        skill_ci_high=skill_high,
        mde=mde,
        mde_pct=mde / reference_mae * 100.0 if reference_mae > 0 else float("nan"),
        dm_statistic=statistic,
        dm_p_value=_bootstrap_dm_p_value(difference, indices, lag),
        dm_lag=lag,
    )


def verdict_from_interval(ci_low: float, ci_high: float) -> str:
    """Better when the whole interval is below zero, worse when all of it is above."""
    if not (np.isfinite(ci_low) and np.isfinite(ci_high)):
        return VERDICT_NO_DIFFERENCE
    if ci_high < 0.0:
        return VERDICT_BETTER
    if ci_low > 0.0:
        return VERDICT_WORSE
    return VERDICT_NO_DIFFERENCE


def minimum_detectable_effect(difference: np.ndarray) -> float:
    """Smallest mean difference this many days could have detected.

    ``MDE = 2.8 * sd(d) / sqrt(n)``. Reported alongside every "no detectable difference"
    verdict, because without it the reader cannot tell a genuine tie from a sample too
    small to resolve one.
    """
    values = np.asarray(difference, dtype="float64")
    if values.size < 2:
        return float("nan")
    return float(MDE_CONSTANT * values.std(ddof=1) / math.sqrt(values.size))


# --------------------------------------------------------------------------------------
# Diebold-Mariano, reported as secondary
# --------------------------------------------------------------------------------------


def newey_west_lag(n: int) -> int:
    """Bartlett truncation lag, ``ceil(1.5 * n**(1/3))``."""
    if n <= 1:
        return 0
    return math.ceil(1.5 * math.pow(n, 1.0 / 3.0))


def diebold_mariano(difference: np.ndarray) -> tuple[float, int]:
    """The HLN-corrected DM statistic and the lag its variance used.

    The Harvey-Leybourne-Newbold factor asks for the forecast horizon *h*. The errors
    here span horizons 1 to 30 from a single origin, so there is no one *h*; the
    truncation lag is what the variance already assumes about their dependence, so
    ``h = lag + 1`` keeps the two halves of the calculation telling the same story.
    """
    values = np.asarray(difference, dtype="float64")
    n = int(values.size)
    if n < 3:
        return float("nan"), 0
    lag = min(newey_west_lag(n), n - 1)
    variance = _newey_west_variance(values, lag)
    if not np.isfinite(variance) or variance <= _TINY_VARIANCE:
        return float("nan"), lag
    statistic = float(values.mean()) / math.sqrt(variance / n)
    return statistic * _harvey_correction(n, lag + 1), lag


def _newey_west_variance(values: np.ndarray, lag: int) -> float:
    """Long-run variance with a Bartlett kernel."""
    n = int(values.size)
    deviation = values - values.mean()
    variance = float((deviation**2).mean())
    for step in range(1, lag + 1):
        weight = 1.0 - step / (lag + 1.0)
        covariance = float((deviation[step:] * deviation[:-step]).sum() / n)
        variance += 2.0 * weight * covariance
    return variance


def _harvey_correction(n: int, horizon: int) -> float:
    """The HLN small sample factor, ``sqrt((n + 1 - 2h + h(h-1)/n) / n)``."""
    inner = n + 1.0 - 2.0 * horizon + horizon * (horizon - 1.0) / n
    if inner <= 0.0:
        return float("nan")
    return math.sqrt(inner / n)


def _bootstrap_dm_p_value(difference: np.ndarray, indices: np.ndarray, lag: int) -> float:
    """Two-sided p-value for the DM statistic, from a recentred block bootstrap.

    Recentring is what turns the bootstrap into a null distribution: subtracting the
    observed mean makes every resample come from a world where the two forecasts are
    equally good, and the p-value is how often that world produces a statistic as
    extreme as the one actually measured.
    """
    values = np.asarray(difference, dtype="float64")
    n = int(values.size)
    if n < 3 or indices.size == 0:
        return float("nan")
    observed, _ = diebold_mariano(values)
    if not np.isfinite(observed):
        return float("nan")
    centred = resample(values - values.mean(), indices)
    means = centred.mean(axis=1)
    deviation = centred - means[:, None]
    variance = (deviation**2).mean(axis=1)
    for step in range(1, min(lag, n - 1) + 1):
        weight = 1.0 - step / (lag + 1.0)
        variance += 2.0 * weight * (deviation[:, step:] * deviation[:, :-step]).sum(axis=1) / n
    usable = variance > _TINY_VARIANCE
    if not bool(usable.any()):
        return float("nan")
    statistics = np.full(means.shape, np.nan, dtype="float64")
    statistics[usable] = means[usable] / np.sqrt(variance[usable] / n)
    statistics *= _harvey_correction(n, lag + 1)
    finite = statistics[np.isfinite(statistics)]
    if finite.size == 0:
        return float("nan")
    return float((np.abs(finite) >= abs(observed)).mean())


# --------------------------------------------------------------------------------------
# Pooling whole windows, the result that actually carries evidence
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PooledComparison:
    """One model against one reference across several windows."""

    model: str
    reference: str
    n_windows: int
    n_days: int
    mean_difference: float
    ci_low: float
    ci_high: float
    verdict: str
    windows_favouring: int
    windows_opposing: int
    windows_neutral: int
    mde: float
    mde_pct: float
    reference_mae: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``verdicts.json``."""
        return {
            "model": self.model,
            "reference": self.reference,
            "n_windows": self.n_windows,
            "n_days": self.n_days,
            "mean_difference": _round(self.mean_difference),
            "ci_low": _round(self.ci_low),
            "ci_high": _round(self.ci_high),
            "verdict": self.verdict,
            "windows_favouring": self.windows_favouring,
            "windows_opposing": self.windows_opposing,
            "windows_neutral": self.windows_neutral,
            "mde": _round(self.mde),
            "mde_pct": _round(self.mde_pct, 2),
            "reference_mae": _round(self.reference_mae),
            "resampling_unit": "window",
        }


def pool_windows(
    differences: list[np.ndarray],
    *,
    model: str,
    reference: str,
    reference_absolute_errors: list[np.ndarray] | None = None,
    n_resamples: int = N_RESAMPLES,
    confidence: float = CONFIDENCE,
    seed: int = RANDOM_SEED,
) -> PooledComparison:
    """Resample whole windows, not days.

    A window is the natural independent unit: two days inside one window share a
    training set and an origin, two windows do not. Bootstrapping days across pooled
    windows would count the same evidence many times and produce an interval that looks
    far more decisive than the data is.
    """
    usable = [np.asarray(values, dtype="float64") for values in differences if len(values) > 0]
    if not usable:
        return PooledComparison(
            model, reference, 0, 0, *(float("nan"),) * 3, VERDICT_NO_DIFFERENCE,
            0, 0, 0, float("nan"), float("nan"), float("nan"),
        )
    per_window = np.array([float(values.mean()) for values in usable], dtype="float64")
    n_windows = int(per_window.size)
    generator = rng(seed)
    if n_windows == 1:
        samples = np.full(n_resamples, per_window[0], dtype="float64")
    else:
        picks = generator.integers(0, n_windows, size=(n_resamples, n_windows))
        samples = per_window[picks].mean(axis=1)
    ci_low, ci_high = percentile_interval(samples, confidence)
    reference_mae = (
        float(np.concatenate(reference_absolute_errors).mean())
        if reference_absolute_errors
        else float("nan")
    )
    mde = minimum_detectable_effect(per_window)
    return PooledComparison(
        model=model,
        reference=reference,
        n_windows=n_windows,
        n_days=int(sum(len(values) for values in usable)),
        mean_difference=float(per_window.mean()),
        ci_low=ci_low,
        ci_high=ci_high,
        verdict=verdict_from_interval(ci_low, ci_high) if n_windows > 1 else VERDICT_NO_DIFFERENCE,
        windows_favouring=int((per_window < 0.0).sum()),
        windows_opposing=int((per_window > 0.0).sum()),
        windows_neutral=int((per_window == 0.0).sum()),
        mde=mde,
        mde_pct=mde / reference_mae * 100.0 if reference_mae > 0 else float("nan"),
        reference_mae=reference_mae,
    )


# --------------------------------------------------------------------------------------
# Bias, calibration, multiplicity
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class BiasEstimate:
    """Mean signed error with a bootstrap interval, and what it means."""

    mean_error: float
    ci_low: float
    ci_high: float
    verdict: str
    mean_actual: float
    pct_of_actual: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``verdicts.json``."""
        return {
            "mean_error": _round(self.mean_error),
            "ci_low": _round(self.ci_low),
            "ci_high": _round(self.ci_high),
            "verdict": self.verdict,
            "mean_actual": _round(self.mean_actual),
            "pct_of_actual": _round(self.pct_of_actual, 2),
        }


def estimate_bias(
    errors: np.ndarray,
    actuals: np.ndarray,
    *,
    n_resamples: int = N_RESAMPLES,
    block_length: int = BLOCK_LENGTH_DAYS,
    confidence: float = CONFIDENCE,
    seed: int = RANDOM_SEED,
) -> BiasEstimate:
    """Bootstrap interval for the mean signed error (forecast minus actual)."""
    values = np.asarray(errors, dtype="float64")
    mean_actual = float(np.asarray(actuals, dtype="float64").mean()) if len(actuals) else float("nan")
    if values.size == 0:
        return BiasEstimate(*(float("nan"),) * 3, BIAS_NONE, mean_actual, float("nan"))
    indices = block_bootstrap_indices(
        values.size, block_length=block_length, n_resamples=n_resamples, generator=rng(seed)
    )
    ci_low, ci_high = percentile_interval(resample(values, indices).mean(axis=1), confidence)
    mean_error = float(values.mean())
    if np.isfinite(ci_low) and ci_low > 0.0:
        verdict = BIAS_OVER
    elif np.isfinite(ci_high) and ci_high < 0.0:
        verdict = BIAS_UNDER
    else:
        verdict = BIAS_NONE
    return BiasEstimate(
        mean_error=mean_error,
        ci_low=ci_low,
        ci_high=ci_high,
        verdict=verdict,
        mean_actual=mean_actual,
        pct_of_actual=mean_error / mean_actual * 100.0 if mean_actual > 0 else float("nan"),
    )


@dataclass(frozen=True)
class Calibration:
    """Measured 80 % coverage with an exact binomial interval."""

    covered: int
    n: int
    coverage: float
    ci_low: float
    ci_high: float
    verdict: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``verdicts.json``."""
        return {
            "covered": self.covered,
            "n": self.n,
            "coverage": _round(self.coverage, 4),
            "ci_low": _round(self.ci_low, 4),
            "ci_high": _round(self.ci_high, 4),
            "target": 0.80,
            "verdict": self.verdict,
        }


def assess_calibration(
    covered: int, n: int, *, target: float = 0.80, confidence: float = CONFIDENCE
) -> Calibration:
    """Clopper-Pearson interval for the coverage rate, and the verdict it implies.

    Exact rather than normal-approximate because 30 days is small and the rate is near
    the edge of the unit interval, where the normal approximation is worst.
    """
    if n <= 0:
        return Calibration(0, 0, float("nan"), float("nan"), float("nan"), CALIBRATION_OK)
    coverage = covered / n
    ci_low, ci_high = clopper_pearson(covered, n, alpha=1.0 - confidence)
    if ci_low <= target <= ci_high:
        verdict = CALIBRATION_OK
    elif ci_high < target:
        verdict = CALIBRATION_NARROW
    else:
        verdict = CALIBRATION_WIDE
    return Calibration(covered, n, coverage, ci_low, ci_high, verdict)


def clopper_pearson(successes: int, n: int, *, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial confidence interval, from beta quantiles computed here."""
    if n <= 0:
        return float("nan"), float("nan")
    lower = 0.0 if successes == 0 else _beta_quantile(alpha / 2.0, successes, n - successes + 1)
    upper = 1.0 if successes == n else _beta_quantile(1.0 - alpha / 2.0, successes + 1, n - successes)
    return lower, upper


def _beta_quantile(probability: float, a: float, b: float, *, iterations: int = 200) -> float:
    """Inverse regularized incomplete beta by bisection.

    Bisection rather than Newton because it cannot diverge, and 200 halvings of the unit
    interval reach machine precision long before they run out.
    """
    low, high = 0.0, 1.0
    for _ in range(iterations):
        middle = (low + high) / 2.0
        if _regularized_incomplete_beta(a, b, middle) < probability:
            low = middle
        else:
            high = middle
    return (low + high) / 2.0


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """``I_x(a, b)`` via the standard continued fraction."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    front = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _beta_continued_fraction(a, b, x) / a
    return 1.0 - front * _beta_continued_fraction(b, a, 1.0 - x) / b


def _beta_continued_fraction(a: float, b: float, x: float, *, iterations: int = 300) -> float:
    """Lentz's algorithm for the beta continued fraction."""
    tiny = 1e-300
    epsilon = 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for step in range(1, iterations + 1):
        even = 2 * step
        numerator = step * (b - step) * x / ((qam + even) * (a + even))
        d = 1.0 + numerator * d
        c = 1.0 + numerator / c
        d, c = (tiny if abs(d) < tiny else d), (tiny if abs(c) < tiny else c)
        d = 1.0 / d
        h *= d * c
        numerator = -(a + step) * (qab + step) * x / ((a + even) * (qap + even))
        d = 1.0 + numerator * d
        c = 1.0 + numerator / c
        d, c = (tiny if abs(d) < tiny else d), (tiny if abs(c) < tiny else c)
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < epsilon:
            break
    return h


def holm_bonferroni(p_values: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment, returned in the input order.

    A sweep of five windows times two models tests ten hypotheses, and at 5 % each about
    one of them comes up significant by luck alone. The raw p-value is reported too, and
    the report names the family size, so a reader can see how much of the correction is
    the price of asking many questions at once.
    """
    finite = [(value, index) for index, value in enumerate(p_values) if np.isfinite(value)]
    adjusted = [float("nan")] * len(p_values)
    if not finite:
        return adjusted
    family = len(finite)
    running = 0.0
    for rank, (value, index) in enumerate(sorted(finite)):
        running = max(running, min(1.0, (family - rank) * value))
        adjusted[index] = running
    return adjusted


def _empty_comparison(model: str, reference: str) -> Comparison:
    """A comparison with nothing in it, so callers do not branch on emptiness."""
    nan = float("nan")
    return Comparison(
        model, reference, 0, nan, nan, nan, VERDICT_NO_DIFFERENCE, nan, nan, nan, nan, nan,
        nan, nan, nan, nan, 0,
    )


def _round(value: float, digits: int = 3) -> float:
    """Round for the verdict file, keeping NaN as NaN."""
    if value is None or not np.isfinite(value):
        return float("nan")
    return float(round(float(value), digits))
