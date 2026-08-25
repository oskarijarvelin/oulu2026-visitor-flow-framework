"""The three reference forecasts every window is measured against.

All three are leak-free by construction: each reads only days at or before the origin,
and each is a single flat rule repeated across the horizon. That last part matters more
than it looks. The obvious seasonal naive, ``y[t-7]``, stops being a benchmark at
horizon 8 and becomes an oracle, because ``t-7`` has moved inside the test period. The
version here freezes the week that ended at the origin and repeats it, so horizon 30 is
as blind as horizon 1.

The default reference for a verdict is the best of the three on that window, not
``seasonal_naive``. On this dataset ``climatology_dow`` beats it in most months, so
picking the seasonal naive would be grading the model against the easiest opponent
available.
"""

from __future__ import annotations

from datetime import date, timedelta

import numpy as np
import pandas as pd

from ..features import TARGET

SEASONAL_NAIVE = "seasonal_naive"
MOVING_AVERAGE_28D = "moving_average_28d"
CLIMATOLOGY_DOW = "climatology_dow"

BASELINE_NAMES: tuple[str, ...] = (SEASONAL_NAIVE, MOVING_AVERAGE_28D, CLIMATOLOGY_DOW)
REFERENCE_BEST = "best"
REFERENCE_CHOICES: tuple[str, ...] = (REFERENCE_BEST, *BASELINE_NAMES)

DAYS_IN_WEEK = 7
MOVING_AVERAGE_DAYS = 28
# How far back the seasonal naive may step when a weekday is missing from the last week.
MAX_WEEK_STEPS = 52


def observed_series(training: pd.DataFrame) -> pd.Series:
    """The target of a training frame, indexed by day, with missing days dropped."""
    values = pd.to_numeric(training[TARGET], errors="coerce").astype("float64")
    series = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(training["date"]))
    return series.dropna().sort_index()


def _weekdays(series: pd.Series) -> pd.Series:
    """The weekday of every row of a day-indexed series."""
    return pd.Series(pd.DatetimeIndex(series.index).dayofweek, index=series.index)


def seasonal_naive(training: pd.DataFrame, origin: date, test_dates: list[date]) -> np.ndarray:
    """Repeat the week that ended at the origin, weekday by weekday.

    The lookup walks back in whole weeks when the last week has a hole in it, so a gap in
    the data degrades the benchmark instead of dropping the day.
    """
    series = observed_series(training)
    by_weekday: dict[int, float] = {}
    for step in range(MAX_WEEK_STEPS):
        window_end = pd.Timestamp(origin) - pd.Timedelta(days=DAYS_IN_WEEK * step)
        window_start = window_end - pd.Timedelta(days=DAYS_IN_WEEK - 1)
        window = series.loc[(series.index >= window_start) & (series.index <= window_end)]
        for weekday, value in zip(_weekdays(window), window, strict=True):
            by_weekday.setdefault(int(weekday), float(value))
        if len(by_weekday) == DAYS_IN_WEEK:
            break
    fallback = float(series.tail(DAYS_IN_WEEK).mean()) if not series.empty else 0.0
    return np.array(
        [by_weekday.get(day.weekday(), fallback) for day in test_dates], dtype="float64"
    )


def moving_average_28d(training: pd.DataFrame, origin: date, test_dates: list[date]) -> np.ndarray:
    """The mean of the 28 days ending at the origin, flat across the horizon."""
    series = observed_series(training)
    window_start = pd.Timestamp(origin) - pd.Timedelta(days=MOVING_AVERAGE_DAYS - 1)
    window = series.loc[(series.index >= window_start) & (series.index <= pd.Timestamp(origin))]
    level = float(window.mean()) if not window.empty else 0.0
    return np.full(len(test_dates), level, dtype="float64")


def climatology_dow(training: pd.DataFrame, origin: date, test_dates: list[date]) -> np.ndarray:
    """The training window's mean for each weekday, flat across the horizon."""
    series = observed_series(training)
    if series.empty:
        return np.zeros(len(test_dates), dtype="float64")
    means = series.groupby(_weekdays(series)).mean()
    overall = float(series.mean())
    return np.array(
        [float(means.get(day.weekday(), overall)) for day in test_dates], dtype="float64"
    )


_BASELINES = {
    SEASONAL_NAIVE: seasonal_naive,
    MOVING_AVERAGE_28D: moving_average_28d,
    CLIMATOLOGY_DOW: climatology_dow,
}


def predict_baseline(
    name: str, training: pd.DataFrame, origin: date, test_dates: list[date]
) -> np.ndarray:
    """One baseline's forecast for the test days."""
    try:
        function = _BASELINES[name]
    except KeyError as exc:
        raise KeyError(
            f"Unknown baseline: {name}. Known baselines: {', '.join(BASELINE_NAMES)}"
        ) from exc
    return function(training, origin, test_dates)


def predict_all(
    training: pd.DataFrame, origin: date, test_dates: list[date]
) -> dict[str, np.ndarray]:
    """Every baseline's forecast for the test days."""
    return {name: predict_baseline(name, training, origin, test_dates) for name in BASELINE_NAMES}


def mase_denominator(training: pd.DataFrame) -> float:
    """The training window's own seasonal naive MAE, the scale MASE divides by.

    Computed on the training days only. Taking it from the test period, which is the
    easy mistake, would make MASE depend on the answer it is meant to grade.
    """
    series = observed_series(training)
    if len(series) <= DAYS_IN_WEEK:
        return float("nan")
    on_grid = series.reindex(
        pd.date_range(series.index.min(), series.index.max(), freq="D")
    )
    differences = (on_grid - on_grid.shift(DAYS_IN_WEEK)).abs().dropna()
    if differences.empty:
        return float("nan")
    return float(differences.mean())


def best_reference(mae_by_name: dict[str, float]) -> str:
    """The baseline with the lowest MAE on this window, ties broken by declared order.

    This is the default opponent. Choosing the *hardest* baseline rather than a fixed
    one is the whole point: it stops a model from looking good by being measured against
    whichever rule happens to fail worst this month.
    """
    candidates = [
        (mae_by_name[name], index, name)
        for index, name in enumerate(BASELINE_NAMES)
        if name in mae_by_name and np.isfinite(mae_by_name[name])
    ]
    if not candidates:
        return SEASONAL_NAIVE
    return min(candidates)[2]


def resolve_reference(requested: str, mae_by_name: dict[str, float]) -> str:
    """Turn ``--reference`` into a concrete baseline name."""
    if requested == REFERENCE_BEST:
        return best_reference(mae_by_name)
    if requested not in BASELINE_NAMES:
        raise KeyError(
            f"Unknown reference: {requested}. Choose one of: {', '.join(REFERENCE_CHOICES)}"
        )
    return requested


def leading_zero_days(training: pd.DataFrame) -> int:
    """Length of the run of zero days at the start of a training window.

    Venue 1 reports nothing before 2026-01-22 and venue 2 nothing before 2026-01-08.
    Those days are in the file and the evaluation keeps them, so the report has to say
    how many of them a training window contains.
    """
    series = observed_series(training)
    if series.empty:
        return 0
    non_zero = np.flatnonzero(series.to_numpy() > 0.0)
    return int(non_zero[0]) if len(non_zero) else len(series)


def week_before(origin: date) -> tuple[date, date]:
    """The seven days the seasonal naive reads, origin included."""
    return origin - timedelta(days=DAYS_IN_WEEK - 1), origin
