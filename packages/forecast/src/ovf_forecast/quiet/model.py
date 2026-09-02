"""The rules that rank a month's days, and the confidence attached to a pick.

A quiet-day forecast is not a visitor forecast with a different label. It only has to
get the *order* of a month's days right, and the order is a much easier thing to know
than the level: the level model has to be right about how busy July is, the ranking only
has to be right about which Wednesday in July is the slow one. Everything here therefore
produces a score whose units are visitors but whose meaning is a rank, and every metric
downstream divides by the month's own median so the level cancels.

Four rules are available. ``quiet_calendar`` is the default: the training window's mean
for each weekday, multiplied by a holiday factor when the calendar says the day is a
public holiday. Four shapes of that rule were measured — mean or median, whole window or
the last eight weeks — and none of them separated from the others; the plain weekday mean
was at the top of all three sweeps and is what this one is built on. The other three
rules are the production level models, scored as ranking rules so that the default has
real opponents rather than a straw man.

Every score comes with a *selection probability*, and on this dataset that number is
worth more than the ranking. Simulating the month many times over from the residuals the
rule has actually made, and counting how often each day lands in the quiet set, is what
separates "the 14th is the quietest day and it is not close" from "these six days are
indistinguishable and the model is guessing between them". Venue 1 mostly produces the
second answer, and a tool that could not say so would be worse than useless.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

from ..dataset import ProcessedData, venue_future
from ..evaluation.baselines import BASELINE_NAMES, predict_baseline
from ..evaluation.significance import RANDOM_SEED, block_bootstrap_indices, rng
from ..features import TARGET, build_future_frame, build_training_frame
from ..models.base import BASELINE, build_model
from .threshold import Eligibility

QUIET_CALENDAR = "quiet_calendar"
SCORE_MODELS: tuple[str, ...] = (QUIET_CALENDAR, *BASELINE_NAMES, BASELINE)
DEFAULT_SCORE_MODEL = QUIET_CALENDAR

# The rolling origins the residual pool is measured on. All of them sit inside the
# training window, so nothing the simulation knows comes from after the origin.
RESIDUAL_STEP_DAYS = 14
RESIDUAL_MAX_ORIGINS = 6
RESIDUAL_MIN_TRAINING_DAYS = 45
MIN_RESIDUALS = 15
# Used only when no origin fits inside the training window. A lognormal spread of 0.25
# is roughly what the measured pools come out at, and the report says when it was used.
DEFAULT_RESIDUAL_SPREAD = 0.25
DEFAULT_RESIDUAL_DRAWS = 200

RESIDUAL_FLOOR = 0.0
RESIDUAL_CEILING = 4.0
BLOCK_LENGTH_DAYS = 7
N_SIMULATIONS = 10_000


@dataclass(frozen=True)
class ScoreRequest:
    """One venue, one origin, and the future days to be ranked."""

    data: ProcessedData
    venue_id: int
    history: pd.DataFrame
    origin: date
    days: tuple[date, ...]

    def __post_init__(self) -> None:
        early = [day for day in self.days if day <= self.origin]
        if early:
            raise ValueError(
                f"Scored days have to lie after the origin {self.origin.isoformat()}; got "
                f"{early[0].isoformat()}. Observed days are supplied by the caller, not scored."
            )

    @property
    def horizon_days(self) -> int:
        """How far the furthest scored day is from the origin."""
        return (max(self.days) - self.origin).days if self.days else 0

    @property
    def training_history(self) -> pd.DataFrame:
        """The history rows the origin allows a model to see."""
        return self.history.loc[self.history["date"] <= pd.Timestamp(self.origin)]


def observed_series(history: pd.DataFrame) -> pd.Series:
    """The daily target of a venue history frame, indexed by day, gaps dropped."""
    values = pd.to_numeric(history[TARGET], errors="coerce").astype("float64")
    series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(history["date"]))
    return series.dropna().sort_index()


def complete_flags(history: pd.DataFrame) -> pd.Series:
    """``is_complete`` per day, defaulting to True when the column is absent."""
    index = pd.DatetimeIndex(history["date"])
    if "is_complete" not in history.columns:
        return pd.Series(True, index=index)
    flags = history["is_complete"]
    if flags.dtype != bool:
        flags = flags.map({True: True, False: False, "True": True, "False": False}).fillna(True)
    return pd.Series(flags.to_numpy(dtype=bool), index=index)


def holiday_flags(data: ProcessedData) -> pd.Series:
    """``is_holiday`` per day from the maintained calendar, as a boolean series."""
    calendar = data.calendar_daily
    flags = calendar["is_holiday"]
    if flags.dtype != bool:
        flags = flags.map({True: True, False: False, "True": True, "False": False}).fillna(False)
    return pd.Series(flags.to_numpy(dtype=bool), index=pd.DatetimeIndex(calendar["date"]))


def is_holiday_on(flags: pd.Series, days: list[date] | tuple[date, ...]) -> np.ndarray:
    """Look each day up in the calendar. Days the calendar does not reach are not holidays."""
    return np.array([bool(flags.get(pd.Timestamp(day), False)) for day in days], dtype=bool)


def build_eligibility(request: ScoreRequest) -> Eligibility:
    """The opening pattern and holiday factor as they stand at the request's origin."""
    series = observed_series(request.training_history)
    return Eligibility.from_training(series, holiday_flags(request.data))


# --------------------------------------------------------------------------------------
# The scoring rules
# --------------------------------------------------------------------------------------


def score_days(name: str, request: ScoreRequest) -> np.ndarray:
    """One rule's score for every day of the request, in visitor units.

    The three level models are asked for a forecast and the forecast is used as a rank
    key. That is a fair way to enter them: no model here is being scored on a job it was
    not built for, because ranking a month is precisely what a daily forecast implies.
    """
    if not request.days:
        return np.zeros(0, dtype="float64")
    if name == QUIET_CALENDAR:
        return _quiet_calendar_scores(request)
    if name in BASELINE_NAMES:
        return _level_baseline_scores(name, request)
    if name == BASELINE:
        return _baseline_model_scores(request)
    raise KeyError(f"Unknown quiet-day rule: {name}. Known rules: {', '.join(SCORE_MODELS)}")


def _quiet_calendar_scores(request: ScoreRequest) -> np.ndarray:
    """The training window's weekday mean, times the venue's holiday factor.

    Without a holiday in the month this is exactly ``climatology_dow``, and that is the
    point: the weekday mean is what measured best, so the default rule is that plus the
    one thing the level baselines do not know, which is that a public holiday is a
    different kind of day. On the committed history the factor changes almost nothing,
    because eight months hold eight holidays and the closures among them are filtered out
    before they can be recommended. It is kept because the mechanism is real and a second
    year of data is what would show it.
    """
    series = observed_series(request.training_history)
    if series.empty:
        return np.full(len(request.days), float("nan"), dtype="float64")
    eligibility = build_eligibility(request)
    levels = np.array([eligibility.weekday_level(day) for day in request.days], dtype="float64")
    factor = eligibility.holiday_factor if np.isfinite(eligibility.holiday_factor) else 1.0
    holidays = is_holiday_on(holiday_flags(request.data), request.days)
    return levels * np.where(holidays, factor, 1.0)


def _training_frame(request: ScoreRequest) -> pd.DataFrame:
    """The feature frame the level models train on at this origin."""
    return build_training_frame(request.training_history, request.origin)


def _level_baseline_scores(name: str, request: ScoreRequest) -> np.ndarray:
    """``seasonal_naive``, ``moving_average_28d`` or ``climatology_dow`` as a rank key."""
    training = _training_frame(request)
    if training.empty:
        return np.full(len(request.days), float("nan"), dtype="float64")
    return predict_baseline(name, training, request.origin, list(request.days))


def _baseline_model_scores(request: ScoreRequest) -> np.ndarray:
    """The production gradient boosting model as a rank key."""
    training = _training_frame(request)
    if training.empty:
        return np.full(len(request.days), float("nan"), dtype="float64")
    covariates = venue_future(request.data, request.venue_id, request.origin, request.horizon_days)
    future = build_future_frame(request.training_history, covariates, request.origin)
    model = build_model(BASELINE)
    model.fit(training)
    predicted = pd.Series(
        model.predict(future).to_numpy(dtype="float64"),
        index=[pd.Timestamp(day) for day in future["date"]],
    )
    return np.array(
        [float(predicted.get(pd.Timestamp(day), float("nan"))) for day in request.days],
        dtype="float64",
    )


# --------------------------------------------------------------------------------------
# How wrong the rule usually is, measured inside the training window
# --------------------------------------------------------------------------------------


def residual_origins(
    origin: date,
    history_start: date,
    *,
    horizon_days: int,
    step_days: int = RESIDUAL_STEP_DAYS,
    max_origins: int = RESIDUAL_MAX_ORIGINS,
    min_training_days: int = RESIDUAL_MIN_TRAINING_DAYS,
) -> list[date]:
    """Inner origins, newest first, none of which can see past ``origin``.

    The newest sits one full horizon before the origin, so its last scored day lands on
    the origin itself and never a day later. This is the same rule the evaluation
    package's nested backtest uses, for the same reason.
    """
    origins: list[date] = []
    cursor = origin - timedelta(days=horizon_days)
    while len(origins) < max_origins and (cursor - history_start).days + 1 >= min_training_days:
        origins.append(cursor)
        cursor -= timedelta(days=step_days)
    return origins


def residual_pool(
    name: str,
    request: ScoreRequest,
    *,
    step_days: int = RESIDUAL_STEP_DAYS,
    max_origins: int = RESIDUAL_MAX_ORIGINS,
    min_training_days: int = RESIDUAL_MIN_TRAINING_DAYS,
) -> np.ndarray:
    """The rule's own out-of-sample ratios ``observed / score``, ordered in time.

    Ordered by inner origin and then by day, so a run of consecutive entries is a run of
    consecutive forecast days and the block bootstrap that reads this pool picks up their
    correlation instead of assuming it away.

    An empty pool is a real outcome on a short history. The caller falls back to a
    default spread and the report says that it did.
    """
    series = observed_series(request.history)
    if series.empty:
        return np.zeros(0, dtype="float64")
    history_start = pd.Timestamp(series.index.min()).date()
    horizon = max(request.horizon_days, 1)
    ratios: list[float] = []
    for inner_origin in residual_origins(
        request.origin,
        history_start,
        horizon_days=horizon,
        step_days=step_days,
        max_origins=max_origins,
        min_training_days=min_training_days,
    ):
        days = [
            inner_origin + timedelta(days=step)
            for step in range(1, horizon + 1)
            if pd.Timestamp(inner_origin + timedelta(days=step)) in series.index
        ]
        if not days:
            continue
        inner = ScoreRequest(
            data=request.data,
            venue_id=request.venue_id,
            history=request.history,
            origin=inner_origin,
            days=tuple(days),
        )
        scores = score_days(name, inner)
        actual = np.array([float(series.loc[pd.Timestamp(day)]) for day in days], dtype="float64")
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = actual / scores
        ratios.extend(float(value) for value in ratio if np.isfinite(value))
    return np.asarray(
        np.clip(np.array(ratios, dtype="float64"), RESIDUAL_FLOOR, RESIDUAL_CEILING), dtype="float64"
    )


def usable_residuals(pool: np.ndarray, *, seed: int = RANDOM_SEED) -> tuple[np.ndarray, bool]:
    """The measured pool, or a default spread when it is too thin to simulate from.

    Returns the ratios and whether they were measured. The flag travels all the way to
    the report, because a probability computed from an assumed spread and one computed
    from six origins of measured error are not the same claim.
    """
    values = np.asarray(pool, dtype="float64")
    if values.size >= MIN_RESIDUALS:
        return values, True
    drawn = rng(seed).lognormal(
        mean=-0.5 * DEFAULT_RESIDUAL_SPREAD**2, sigma=DEFAULT_RESIDUAL_SPREAD, size=DEFAULT_RESIDUAL_DRAWS
    )
    return np.clip(drawn, RESIDUAL_FLOOR, RESIDUAL_CEILING), False


# --------------------------------------------------------------------------------------
# Selection probabilities
# --------------------------------------------------------------------------------------


def selection_probabilities(
    scores: np.ndarray,
    residuals: np.ndarray,
    k: int,
    *,
    fixed: np.ndarray | None = None,
    n_simulations: int = N_SIMULATIONS,
    block_length: int = BLOCK_LENGTH_DAYS,
    seed: int = RANDOM_SEED,
) -> np.ndarray:
    """P(day lands in the month's quiet set), by simulating the month many times over.

    Each simulation multiplies the scores by a block-bootstrapped path of the rule's own
    measured ratios, re-ranks the month and records which days came out lowest. Blocks
    rather than single days, because a week that runs quiet runs quiet for the whole
    week, and a day-wise draw would make every day's fate independent and every
    probability far too confident.

    ``fixed`` marks days that are already observed. Those keep their value in every
    simulation, which is what makes a mid-month run coherent: the days that have happened
    compete against the days that have not, without being given an imaginary error.
    """
    values = np.asarray(scores, dtype="float64")
    n = int(values.size)
    if n == 0 or k <= 0:
        return np.zeros(n, dtype="float64")
    if k >= n:
        return np.ones(n, dtype="float64")
    pool = np.asarray(residuals, dtype="float64")
    if pool.size == 0:
        return np.where(np.argsort(np.argsort(values, kind="stable"), kind="stable") < k, 1.0, 0.0)
    indices = block_bootstrap_indices(
        n,
        source_length=int(pool.size),
        block_length=block_length,
        n_resamples=n_simulations,
        generator=rng(seed),
    )
    draws = pool[indices]
    if fixed is not None:
        draws = np.where(np.asarray(fixed, dtype=bool)[None, :], 1.0, draws)
    simulated = values[None, :] * draws
    ranks = np.argsort(np.argsort(simulated, axis=1, kind="stable"), axis=1)
    return np.asarray((ranks < k).mean(axis=0), dtype="float64")


def resolve_score_models(requested: tuple[str, ...] | None) -> tuple[str, ...]:
    """Validate the requested rules, defaulting to the one that measured best."""
    if not requested:
        return (DEFAULT_SCORE_MODEL,)
    unknown = [name for name in requested if name not in SCORE_MODELS]
    if unknown:
        raise KeyError(
            f"Unknown quiet-day rule(s): {', '.join(unknown)}. Known rules: {', '.join(SCORE_MODELS)}"
        )
    return tuple(dict.fromkeys(requested))
