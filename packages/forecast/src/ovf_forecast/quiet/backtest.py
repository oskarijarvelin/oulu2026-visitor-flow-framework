"""The test tool: slide a window over the history and ask what the answer was worth.

Every window is one honest rehearsal of the real task. Train on everything up to the end
of a month, name that month's quiet days, then open the month and see what happened. The
sweep repeats that over as many months as the history holds and pools the result, because
one month is one draw and a rule that wins a single month has proved nothing.

Four numbers describe a window, and they answer different questions.

``hit_rate`` is how many of the ``k`` days named turned out to be in the true quiet set,
against ``chance_rate = k / n`` which is what naming days at random would score. It is
the natural accuracy measure and it is the least useful of the four, because it counts a
miss onto the seventh-quietest day the same as a miss onto the busiest day of the month.

``realized_ratio`` is the mean attendance of the named days divided by the month's median
day, and ``benefit = 1 - realized_ratio`` is the headline: how much quieter the
recommendation actually was than an arbitrary day. This is the number the decision rests
on, so it is the one the verdict is built from.

``capture`` puts that benefit next to the best any rule could have done on that month
with hindsight. A capture of 0.3 says the recommendation collected three tenths of the
quietness that was there to collect.

``spearman`` grades the whole ranking rather than the cut, which is what tells a flat
month apart from a mis-ordered one.

The calibration table exists because this package publishes probabilities. A day given a
70 % chance of being in the quiet set has to land there about seven times in ten, and the
only way to know is to collect the pairs and count.

Two pieces of hindsight are used deliberately, and both are disclosed rather than hidden.
The candidate pool is the days that turned out to be observed, complete and non-zero, so a
day the venue unexpectedly shut is dropped from the truth *and* from what the rule is
allowed to name — the rule is never charged for recommending a closure. And ``k`` is taken
from the truth's candidate count, so the named set and the true set are the same size and
the hit rate is defined at all. Both apply identically to the rule and to the chance rate
it is measured against, so neither can flatter one over the other; ``docs/QUIET_DAYS.md``
chapter 6.5 says what they do cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from itertools import pairwise
from typing import Any

import numpy as np
import pandas as pd

from .. import log_event
from ..dataset import ProcessedData, Venue, venue_history
from ..evaluation.significance import CONFIDENCE, N_RESAMPLES, RANDOM_SEED, percentile_interval, rng
from ..evaluation.windows import Window
from .model import (
    DEFAULT_SCORE_MODEL,
    ScoreRequest,
    build_eligibility,
    complete_flags,
    holiday_flags,
    is_holiday_on,
    observed_series,
    residual_pool,
    score_days,
    selection_probabilities,
    usable_residuals,
)
from .threshold import DEFAULT_QUIET_SHARE, Eligibility, quiet_set

VERDICT_USEFUL = "useful"
VERDICT_NO_BENEFIT = "no_detectable_benefit"
VERDICT_HARMFUL = "harmful"

VERDICT_BETTER_THAN_CHANCE = "better_than_chance"
VERDICT_LIKE_CHANCE = "like_chance"
VERDICT_WORSE_THAN_CHANCE = "worse_than_chance"

# 2.8 = z(0.975) + z(0.80), the two-sided 5 % / 80 % power constant, as in the
# evaluation package. Reported so a tie can be told from a sample too small to resolve.
MDE_CONSTANT = 2.8
# A window needs enough eligible days for a fifth of them to mean anything.
MIN_ELIGIBLE_DAYS = 15
# Cheaper than a forecast run: a sweep pays this per window per rule, and three decimals
# of a probability are not what a calibration table is measuring.
SWEEP_SIMULATIONS = 2_000
CALIBRATION_EDGES: tuple[float, ...] = (0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0)


@dataclass(frozen=True)
class QuietBacktestConfig:
    """Everything about a sweep that is not the list of windows."""

    score_models: tuple[str, ...] = (DEFAULT_SCORE_MODEL,)
    quiet_share: float = DEFAULT_QUIET_SHARE
    top_k: int | None = None
    venues: tuple[int, ...] | None = None
    n_resamples: int = N_RESAMPLES
    n_simulations: int = SWEEP_SIMULATIONS
    seed: int = RANDOM_SEED

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``config.json``."""
        return {
            "score_models": list(self.score_models),
            "quiet_share": self.quiet_share,
            "top_k": self.top_k,
            "venues": list(self.venues) if self.venues else None,
            "n_resamples": self.n_resamples,
            "n_simulations": self.n_simulations,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class WindowOutcome:
    """What one rule scored on one venue in one window."""

    venue_id: int
    venue_name: str
    model: str
    window: Window
    n_eligible: int
    k: int
    median: float
    hit_rate: float
    chance_rate: float
    realized_ratio: float
    oracle_ratio: float
    spearman: float
    top1_ratio: float
    predicted: tuple[date, ...]
    truth: tuple[date, ...]
    days: tuple[date, ...]
    actual: np.ndarray
    scores: np.ndarray
    probabilities: np.ndarray
    in_truth: np.ndarray
    residuals_measured: bool

    def day_rows(self) -> list[dict[str, Any]]:
        """One line per eligible day, for ``days.csv``.

        Every published probability is written next to what actually happened, so the
        calibration table in the report can be recomputed from the stored file rather
        than taken on trust.
        """
        return [
            {
                "venue_id": self.venue_id,
                "model": self.model,
                "test_start": self.window.test_start.isoformat(),
                "date": day.isoformat(),
                "score": _round(float(self.scores[index])),
                "y_true": _round(float(self.actual[index])),
                "ratio": _round(float(self.actual[index]) / self.median, 3)
                if self.median > 0
                else None,
                "probability": _round(float(self.probabilities[index]), 3),
                "in_truth": bool(self.in_truth[index]),
                "predicted_quiet": day in self.predicted,
            }
            for index, day in enumerate(self.days)
        ]

    @property
    def benefit(self) -> float:
        """How much quieter the named days were than the month's median day."""
        return 1.0 - self.realized_ratio

    @property
    def oracle_benefit(self) -> float:
        """The most benefit any rule could have collected on this month."""
        return 1.0 - self.oracle_ratio

    @property
    def capture(self) -> float:
        """Share of the available benefit the rule collected."""
        if not np.isfinite(self.oracle_benefit) or self.oracle_benefit <= 0.0:
            return float("nan")
        return self.benefit / self.oracle_benefit

    @property
    def hit_gap(self) -> float:
        """Hit rate above what naming days at random would have scored."""
        return self.hit_rate - self.chance_rate

    def to_row(self) -> dict[str, Any]:
        """One line of ``windows.csv``."""
        return {
            "venue_id": self.venue_id,
            "model": self.model,
            "origin": self.window.origin.isoformat(),
            "test_start": self.window.test_start.isoformat(),
            "test_end": self.window.test_end.isoformat(),
            "n_eligible": self.n_eligible,
            "k": self.k,
            "median": _round(self.median),
            "hit_rate": _round(self.hit_rate, 3),
            "chance_rate": _round(self.chance_rate, 3),
            "realized_ratio": _round(self.realized_ratio, 3),
            "oracle_ratio": _round(self.oracle_ratio, 3),
            "benefit": _round(self.benefit, 3),
            "capture": _round(self.capture, 3),
            "spearman": _round(self.spearman, 3),
            "top1_ratio": _round(self.top1_ratio, 3),
            "predicted_days": " ".join(day.isoformat() for day in self.predicted),
            "truth_days": " ".join(day.isoformat() for day in self.truth),
        }


def run_window(
    data: ProcessedData, venue: Venue, window: Window, model: str, config: QuietBacktestConfig
) -> WindowOutcome | None:
    """Rank one window's days at its origin and score the ranking against what happened.

    Returns ``None`` when the window cannot be scored at all: no history before the
    origin, or too few eligible days inside the test period for a fifth of them to be a
    meaningful set.
    """
    history = venue_history(data, venue.venue_id)
    if history.empty:
        return None
    series = observed_series(history)
    complete = complete_flags(history)
    if series.empty or pd.Timestamp(window.origin) < series.index.min():
        return None
    training = series.loc[series.index <= pd.Timestamp(window.origin)]
    if training.empty:
        return None

    days = window.test_dates()
    request = ScoreRequest(
        data=data,
        venue_id=venue.venue_id,
        history=history.loc[history["date"] <= pd.Timestamp(window.origin)],
        origin=window.origin,
        days=tuple(days),
    )
    eligibility = build_eligibility(request)
    scores = score_days(model, request)
    actual = np.array(
        [float(series.get(pd.Timestamp(day), float("nan"))) for day in days], dtype="float64"
    )
    complete_day = np.array(
        [bool(complete.get(pd.Timestamp(day), True)) for day in days], dtype=bool
    )
    holidays = is_holiday_on(holiday_flags(data), days)

    eligible = [
        index
        for index, day in enumerate(days)
        if _is_candidate(day, eligibility, holidays[index])
        and np.isfinite(actual[index])
        and complete_day[index]
        and actual[index] > 0.0
        and np.isfinite(scores[index])
    ]
    if len(eligible) < MIN_ELIGIBLE_DAYS:
        log_event(
            "warning",
            "quiet.backtest",
            "Too few eligible days to score the window",
            venue_id=venue.venue_id,
            window=window.label,
            eligible=len(eligible),
            minimum=MIN_ELIGIBLE_DAYS,
        )
        return None

    eligible_days = [days[index] for index in eligible]
    eligible_actual = actual[eligible]
    eligible_scores = scores[eligible]
    truth = quiet_set(eligible_days, eligible_actual, share=config.quiet_share, k=config.top_k)
    predicted = quiet_set(eligible_days, eligible_scores, share=config.quiet_share, k=truth.k)

    pool = residual_pool(model, request)
    residuals, measured = usable_residuals(pool, seed=config.seed)
    probabilities = selection_probabilities(
        eligible_scores,
        residuals,
        truth.k,
        n_simulations=config.n_simulations,
        seed=config.seed,
    )
    truth_dates = set(truth.dates)
    scale = truth.median if truth.median > 0 else float("nan")
    quietest = eligible_actual[int(np.argsort(eligible_scores, kind="stable")[0])]
    return WindowOutcome(
        venue_id=venue.venue_id,
        venue_name=venue.name,
        model=model,
        window=window,
        n_eligible=len(eligible),
        k=truth.k,
        median=truth.median,
        hit_rate=len(truth_dates & set(predicted.dates)) / truth.k if truth.k else float("nan"),
        chance_rate=truth.k / len(eligible) if eligible else float("nan"),
        realized_ratio=float(eligible_actual[predicted.positions].mean()) / scale,
        oracle_ratio=truth.mean_ratio,
        spearman=_spearman(eligible_scores, eligible_actual),
        top1_ratio=float(quietest) / scale,
        predicted=predicted.dates,
        truth=truth.dates,
        days=tuple(eligible_days),
        actual=eligible_actual,
        scores=eligible_scores,
        probabilities=probabilities,
        in_truth=np.array([day in truth_dates for day in eligible_days], dtype=bool),
        residuals_measured=measured,
    )


def _is_candidate(day: date, eligibility: Eligibility, is_holiday: bool) -> bool:
    """Whether a day passes the filter that a forecast would have applied in advance.

    The truth side then applies the two filters a forecast could not: a day with no
    visitors at all, and a day the counter did not answer for the whole of. Both are
    handled by the caller, because both need the observation.
    """
    if eligibility.is_closed_weekday(day):
        return False
    return not (is_holiday and eligibility.closes_on_holidays)


def run_sweep(
    data: ProcessedData, windows: list[Window], config: QuietBacktestConfig
) -> list[WindowOutcome]:
    """Every window, every venue, every rule."""
    outcomes: list[WindowOutcome] = []
    for venue in data.select_venues(config.venues):
        for window in windows:
            for model in config.score_models:
                outcome = run_window(data, venue, window, model, config)
                if outcome is not None:
                    outcomes.append(outcome)
    return outcomes


# --------------------------------------------------------------------------------------
# Pooling windows into a verdict
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PooledQuiet:
    """One rule's record on one venue across every window of a sweep."""

    venue_id: int
    venue_name: str
    model: str
    n_windows: int
    n_days: int
    benefit: float
    benefit_ci_low: float
    benefit_ci_high: float
    benefit_mde: float
    verdict: str
    realized_ratio: float
    oracle_ratio: float
    capture: float
    hit_rate: float
    chance_rate: float
    hit_gap_ci_low: float
    hit_gap_ci_high: float
    hit_verdict: str
    spearman: float
    top1_ratio: float
    windows_favouring: int
    windows_opposing: int
    calibration: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``verdicts.json``."""
        return {
            "venue_id": self.venue_id,
            "venue_name": self.venue_name,
            "model": self.model,
            "n_windows": self.n_windows,
            "n_days": self.n_days,
            "benefit": _round(self.benefit, 3),
            "benefit_ci_low": _round(self.benefit_ci_low, 3),
            "benefit_ci_high": _round(self.benefit_ci_high, 3),
            "benefit_mde": _round(self.benefit_mde, 3),
            "verdict": self.verdict,
            "realized_ratio": _round(self.realized_ratio, 3),
            "oracle_ratio": _round(self.oracle_ratio, 3),
            "capture": _round(self.capture, 3),
            "hit_rate": _round(self.hit_rate, 3),
            "chance_rate": _round(self.chance_rate, 3),
            "hit_gap_ci_low": _round(self.hit_gap_ci_low, 3),
            "hit_gap_ci_high": _round(self.hit_gap_ci_high, 3),
            "hit_verdict": self.hit_verdict,
            "spearman": _round(self.spearman, 3),
            "top1_ratio": _round(self.top1_ratio, 3),
            "windows_favouring": self.windows_favouring,
            "windows_opposing": self.windows_opposing,
            "calibration": self.calibration,
            "resampling_unit": "window",
        }


def pool(outcomes: list[WindowOutcome], config: QuietBacktestConfig) -> list[PooledQuiet]:
    """Pool the windows of every (venue, rule) pair into one verdict each.

    Whole windows are resampled, never days. Two days inside one month share an origin, a
    training set and a month of weather; two months do not. Bootstrapping days would
    count the same evidence over and over and produce an interval far more decisive than
    the evidence is.
    """
    pooled: list[PooledQuiet] = []
    keys = dict.fromkeys((outcome.venue_id, outcome.model) for outcome in outcomes)
    for venue_id, model in keys:
        group = [
            outcome
            for outcome in outcomes
            if outcome.venue_id == venue_id and outcome.model == model
        ]
        pooled.append(_pool_group(group, config))
    return sorted(pooled, key=lambda item: (item.venue_id, item.model))


def _pool_group(group: list[WindowOutcome], config: QuietBacktestConfig) -> PooledQuiet:
    """Pool one venue and one rule."""
    benefits = np.array([outcome.benefit for outcome in group], dtype="float64")
    gaps = np.array([outcome.hit_gap for outcome in group], dtype="float64")
    benefit_low, benefit_high = _bootstrap_interval(benefits, config)
    gap_low, gap_high = _bootstrap_interval(gaps, config)
    oracle = _mean([outcome.oracle_benefit for outcome in group])
    benefit = _mean(benefits)
    return PooledQuiet(
        venue_id=group[0].venue_id,
        venue_name=group[0].venue_name,
        model=group[0].model,
        n_windows=len(group),
        n_days=int(sum(outcome.n_eligible for outcome in group)),
        benefit=benefit,
        benefit_ci_low=benefit_low,
        benefit_ci_high=benefit_high,
        benefit_mde=minimum_detectable_effect(benefits),
        verdict=_benefit_verdict(benefit_low, benefit_high),
        realized_ratio=_mean([outcome.realized_ratio for outcome in group]),
        oracle_ratio=_mean([outcome.oracle_ratio for outcome in group]),
        capture=benefit / oracle if np.isfinite(oracle) and oracle > 0 else float("nan"),
        hit_rate=_mean([outcome.hit_rate for outcome in group]),
        chance_rate=_mean([outcome.chance_rate for outcome in group]),
        hit_gap_ci_low=gap_low,
        hit_gap_ci_high=gap_high,
        hit_verdict=_chance_verdict(gap_low, gap_high),
        spearman=_mean([outcome.spearman for outcome in group]),
        top1_ratio=_mean([outcome.top1_ratio for outcome in group]),
        windows_favouring=int((benefits > 0.0).sum()),
        windows_opposing=int((benefits < 0.0).sum()),
        calibration=calibration_table(group),
    )


def _mean(values: list[float] | np.ndarray) -> float:
    """Mean of the finite entries, or NaN when there are none.

    ``np.nanmean`` warns on an all-NaN slice, and a rule with no rank correlation to
    report — ``moving_average_28d`` gives every day the same score — produces exactly
    that. NaN is the right answer there, not a warning.
    """
    array = np.asarray(values, dtype="float64")
    finite = array[np.isfinite(array)]
    return float(finite.mean()) if finite.size else float("nan")


def _bootstrap_interval(values: np.ndarray, config: QuietBacktestConfig) -> tuple[float, float]:
    """Percentile interval of the mean, resampling whole windows."""
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return float("nan"), float("nan")
    if finite.size == 1:
        return float(finite[0]), float(finite[0])
    picks = rng(config.seed).integers(0, finite.size, size=(config.n_resamples, finite.size))
    return percentile_interval(finite[picks].mean(axis=1), CONFIDENCE)


def minimum_detectable_effect(values: np.ndarray) -> float:
    """Smallest mean benefit this many windows could have detected."""
    finite = values[np.isfinite(values)]
    if finite.size < 2:
        return float("nan")
    return float(MDE_CONSTANT * finite.std(ddof=1) / np.sqrt(finite.size))


def _benefit_verdict(ci_low: float, ci_high: float) -> str:
    """Useful when the whole interval is above zero, harmful when all of it is below."""
    if not (np.isfinite(ci_low) and np.isfinite(ci_high)):
        return VERDICT_NO_BENEFIT
    if ci_low > 0.0:
        return VERDICT_USEFUL
    if ci_high < 0.0:
        return VERDICT_HARMFUL
    return VERDICT_NO_BENEFIT


def _chance_verdict(ci_low: float, ci_high: float) -> str:
    """Whether the hit rate clears what naming days at random would score."""
    if not (np.isfinite(ci_low) and np.isfinite(ci_high)):
        return VERDICT_LIKE_CHANCE
    if ci_low > 0.0:
        return VERDICT_BETTER_THAN_CHANCE
    if ci_high < 0.0:
        return VERDICT_WORSE_THAN_CHANCE
    return VERDICT_LIKE_CHANCE


def calibration_table(group: list[WindowOutcome]) -> list[dict[str, Any]]:
    """Predicted probability against observed frequency, in six buckets.

    Every eligible day of every window contributes one pair. A bucket with a handful of
    days says nothing, so ``n`` is reported next to every row and the report refuses to
    draw a conclusion from a thin one.
    """
    if not group:
        return []
    probabilities = np.concatenate([outcome.probabilities for outcome in group])
    observed = np.concatenate([outcome.in_truth for outcome in group])
    rows: list[dict[str, Any]] = []
    for low, high in pairwise(CALIBRATION_EDGES):
        upper = high + 1e-9 if high >= 1.0 else high
        selected = (probabilities >= low) & (probabilities < upper)
        count = int(selected.sum())
        rows.append(
            {
                "bucket": f"{low:.2f}-{high:.2f}",
                "n": count,
                "predicted": _round(float(probabilities[selected].mean()), 3) if count else None,
                "observed": _round(float(observed[selected].mean()), 3) if count else None,
            }
        )
    return rows


def _spearman(predicted: np.ndarray, actual: np.ndarray) -> float:
    """Rank correlation, computed with pandas ranks so no scipy is needed."""
    if predicted.size < 3:
        return float("nan")
    left = pd.Series(predicted).rank().to_numpy()
    right = pd.Series(actual).rank().to_numpy()
    if left.std() == 0.0 or right.std() == 0.0:
        return float("nan")
    return float(np.corrcoef(left, right)[0, 1])


def _round(value: float, digits: int = 1) -> float | None:
    """Round for JSON, mapping every non-finite value to null."""
    return None if value is None or not np.isfinite(value) else round(float(value), digits)
