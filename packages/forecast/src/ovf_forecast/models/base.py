"""The interface both models and both benchmarks implement, and the registry.

Every model predicts one number per *day*. The hourly shape comes from the shared
profile in :mod:`ovf_forecast.profile` and the intervals from the shared backtest in
:mod:`ovf_forecast.intervals`, which is what makes two very different models
comparable and what makes the hourly forecasts sum to the daily one exactly.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd

from .. import log_event

BASELINE = "baseline"
PROPHET_XGB = "prophet_xgb"
SEASONAL_NAIVE = "seasonal_naive"
MOVING_AVERAGE_28D = "moving_average_28d"

MODEL_NAMES: tuple[str, ...] = (BASELINE, PROPHET_XGB)
BENCHMARK_NAMES: tuple[str, ...] = (SEASONAL_NAIVE, MOVING_AVERAGE_28D)
ALL_NAMES: tuple[str, ...] = (*MODEL_NAMES, *BENCHMARK_NAMES)

RANDOM_STATE = 20260101


@runtime_checkable
class ForecastModel(Protocol):
    """A daily forecaster: fit on observed days, predict the median of future days."""

    name: str

    def fit(self, daily: pd.DataFrame) -> None:
        """Fit on a feature frame that includes the target column."""

    def predict(self, future: pd.DataFrame) -> pd.Series:
        """Return the p50 daily forecast, in visitor events, for each future row."""


class ModelUnavailableError(RuntimeError):
    """Raised when a model's optional dependencies are not installed."""


def build_model(name: str) -> ForecastModel:
    """Instantiate one model or benchmark by name.

    Raises :class:`ModelUnavailableError` when the optional prophet dependency group is
    missing, so the caller can skip that model instead of failing the whole run.
    """
    from .baseline import BaselineModel, MovingAverage28dModel, SeasonalNaiveModel

    if name == BASELINE:
        return BaselineModel()
    if name == SEASONAL_NAIVE:
        return SeasonalNaiveModel()
    if name == MOVING_AVERAGE_28D:
        return MovingAverage28dModel()
    if name == PROPHET_XGB:
        try:
            from .prophet_xgb import ProphetXgbModel
        except Exception as exc:
            # Not just ImportError: an installed xgboost whose OpenMP runtime is missing
            # raises XGBoostError at import time, and prophet's cmdstan backend has its
            # own ways of failing. All of them mean the same thing to the caller.
            raise ModelUnavailableError(
                "prophet_xgb is not usable: "
                f"{type(exc).__name__}: {str(exc).strip().splitlines()[0] if str(exc).strip() else exc}. "
                'Install the optional group with pip install -e ".[prophet]" '
                "(macOS also needs an OpenMP runtime: brew install libomp). "
                "The baseline model needs none of this."
            ) from exc
        return ProphetXgbModel()
    raise KeyError(f"Unknown model: {name}. Known models: {', '.join(ALL_NAMES)}")


def resolve_models(names: tuple[str, ...]) -> tuple[list[ForecastModel], list[str]]:
    """Instantiate every requested model, skipping the ones whose extras are missing.

    Returns the usable models and the names that were skipped. A missing prophet install
    is a warning, never a failed run.
    """
    models: list[ForecastModel] = []
    skipped: list[str] = []
    for name in names:
        try:
            models.append(build_model(name))
        except ModelUnavailableError as exc:
            skipped.append(name)
            log_event("warning", "models", str(exc), model=name)
    return models, skipped
