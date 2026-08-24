"""The production model and the two benchmarks it has to beat.

``BaselineModel`` is one gradient boosted regressor on daily totals with a Poisson
loss. The target is a count: its distribution is right-skewed and it cannot go
negative. A Poisson objective respects both facts, which means the forecast is
non-negative by construction instead of by a clip afterwards, and no log transform is
needed, so there is no retransformation bias to correct.

The benchmarks exist because a model that cannot beat "same weekday last week" is not
worth running. Both are computed on every backtest origin and reported next to the
real models.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor

from .. import log_event
from ..features import (
    CATEGORICAL_FEATURES,
    FEATURE_COLUMNS,
    LEVEL_LONG_DAYS,
    TARGET,
    model_matrix,
)
from .base import BASELINE, MOVING_AVERAGE_28D, RANDOM_STATE, SEASONAL_NAIVE

WEEK_DAYS = 7
MIN_TRAINING_ROWS = 30


class BaselineModel:
    """Poisson gradient boosting on daily totals.

    Hyper-parameters are deliberately conservative. With around 120 training rows the
    risk is a model that memorises the training months, so the trees are shallow, the
    leaves are large and the learning rate is low. ``early_stopping`` is off because an
    internal validation split of a 120-row time series would be both tiny and random.
    """

    name = BASELINE

    def __init__(self, random_state: int = RANDOM_STATE) -> None:
        self._random_state = random_state
        self._model: HistGradientBoostingRegressor | None = None
        self._fallback: float = 0.0

    def fit(self, daily: pd.DataFrame) -> None:
        """Fit on every observed day of the training window."""
        target = pd.to_numeric(daily[TARGET], errors="coerce").astype("float64")
        usable = daily.loc[target.notna()]
        self._fallback = float(target.dropna().tail(LEVEL_LONG_DAYS).mean()) if target.notna().any() else 0.0
        if len(usable) < MIN_TRAINING_ROWS:
            log_event(
                "warning",
                "baseline",
                "Too few training days, falling back to the recent mean",
                rows=len(usable),
                minimum=MIN_TRAINING_ROWS,
            )
            self._model = None
            return
        model = HistGradientBoostingRegressor(
            loss="poisson",
            learning_rate=0.05,
            max_iter=400,
            max_depth=4,
            max_leaf_nodes=15,
            min_samples_leaf=8,
            l2_regularization=1.0,
            early_stopping=False,
            categorical_features=list(CATEGORICAL_FEATURES),
            random_state=self._random_state,
        )
        model.fit(model_matrix(usable), target.loc[usable.index])
        self._model = model

    def predict(self, future: pd.DataFrame) -> pd.Series:
        """Daily p50 for each future row."""
        if self._model is None:
            return pd.Series(np.full(len(future), self._fallback), index=future.index, dtype="float64")
        values = np.asarray(self._model.predict(model_matrix(future)), dtype="float64")
        return pd.Series(np.maximum(values, 0.0), index=future.index, dtype="float64")

    def feature_importance(self, frame: pd.DataFrame) -> dict[str, float]:
        """Permutation importance on the training frame, for the model documentation."""
        if self._model is None:
            return {}
        from sklearn.inspection import permutation_importance

        result = permutation_importance(
            self._model,
            model_matrix(frame),
            pd.to_numeric(frame[TARGET], errors="coerce").astype("float64"),
            n_repeats=5,
            random_state=self._random_state,
            scoring="neg_mean_absolute_error",
        )
        return {
            column: float(value)
            for column, value in zip(FEATURE_COLUMNS, result.importances_mean, strict=True)
        }


class SeasonalNaiveModel:
    """Same weekday, most recent observed occurrence.

    For horizons past one week the literal "a week ago" would be a forecast, not an
    observation, so this steps back in whole weeks until it lands on observed data.
    That keeps the benchmark honest at every horizon instead of quietly turning
    recursive at day 8.
    """

    name = SEASONAL_NAIVE

    def __init__(self) -> None:
        self._by_date: dict[pd.Timestamp, float] = {}
        self._last_date: pd.Timestamp | None = None
        self._fallback = 0.0

    def fit(self, daily: pd.DataFrame) -> None:
        """Remember the observed series."""
        target = pd.to_numeric(daily[TARGET], errors="coerce").astype("float64")
        observed = daily.loc[target.notna()]
        self._by_date = {
            pd.Timestamp(day): float(value)
            for day, value in zip(observed["date"], target.loc[observed.index], strict=True)
        }
        self._last_date = pd.Timestamp(observed["date"].max()) if not observed.empty else None
        self._fallback = float(target.dropna().tail(LEVEL_LONG_DAYS).mean()) if target.notna().any() else 0.0

    def predict(self, future: pd.DataFrame) -> pd.Series:
        """Look each future day back in whole weeks until an observation is found."""
        values: list[float] = []
        for day in future["date"]:
            values.append(self._lookup(pd.Timestamp(day)))
        return pd.Series(values, index=future.index, dtype="float64")

    def _lookup(self, day: pd.Timestamp) -> float:
        if self._last_date is None:
            return self._fallback
        candidate = day
        while candidate > self._last_date:
            candidate -= pd.Timedelta(days=WEEK_DAYS)
        while candidate >= self._last_date - pd.Timedelta(days=365):
            if candidate in self._by_date:
                return self._by_date[candidate]
            candidate -= pd.Timedelta(days=WEEK_DAYS)
        return self._fallback


class MovingAverage28dModel:
    """The mean of the last 28 observed days, flat across the whole horizon."""

    name = MOVING_AVERAGE_28D

    def __init__(self, window_days: int = LEVEL_LONG_DAYS) -> None:
        self._window_days = window_days
        self._level = 0.0

    def fit(self, daily: pd.DataFrame) -> None:
        """Take the mean of the last ``window_days`` observed days."""
        target = pd.to_numeric(daily[TARGET], errors="coerce").astype("float64").dropna()
        self._level = float(target.tail(self._window_days).mean()) if not target.empty else 0.0

    def predict(self, future: pd.DataFrame) -> pd.Series:
        """One constant for every future day."""
        return pd.Series(np.full(len(future), self._level), index=future.index, dtype="float64")


__all__ = [
    "MOVING_AVERAGE_28D",
    "SEASONAL_NAIVE",
    "BaselineModel",
    "MovingAverage28dModel",
    "SeasonalNaiveModel",
]
