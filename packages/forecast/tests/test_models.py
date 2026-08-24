"""Model behaviour: learned rhythm, non-negativity, and a clean skip without prophet."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ovf_forecast.dataset import load_dataset, venue_future, venue_history
from ovf_forecast.features import build_future_frame, build_training_frame
from ovf_forecast.models.base import (
    BASELINE,
    MODEL_NAMES,
    MOVING_AVERAGE_28D,
    PROPHET_XGB,
    SEASONAL_NAIVE,
    ModelUnavailableError,
    build_model,
    resolve_models,
)
from ovf_forecast.models.baseline import BaselineModel, MovingAverage28dModel, SeasonalNaiveModel
from synthetic import DOW_FACTORS

ORIGIN = date(2026, 6, 30)
HORIZON_DAYS = 30


def _frames(repo: Path, venue_id: int = 1) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = load_dataset(repo)
    history = venue_history(data, venue_id)
    training = build_training_frame(history, ORIGIN)
    future = build_future_frame(history, venue_future(data, venue_id, ORIGIN, HORIZON_DAYS), ORIGIN)
    return training, future


def test_baseline_learns_a_known_weekly_rhythm(synthetic_repo: Path) -> None:
    """The fixture has a fixed weekday pattern; the model has to reproduce its shape.

    The test asserts the *ranking* and the relative spread, not exact numbers: a model
    that reproduced the generator exactly would be a sign of leakage, not of skill.
    """
    training, future = _frames(synthetic_repo)
    model = BaselineModel()
    model.fit(training)
    predicted = model.predict(future)

    by_weekday = (
        pd.DataFrame({"dow": future["date"].dt.dayofweek, "p50": predicted})
        .groupby("dow")["p50"]
        .mean()
    )
    normalized = by_weekday / by_weekday.mean()
    truth = pd.Series(DOW_FACTORS, index=range(7)) / pd.Series(DOW_FACTORS).mean()

    assert normalized.idxmax() == truth.idxmax(), "Saturday must come out busiest"
    assert normalized.idxmin() == truth.idxmin(), "Monday must come out quietest"
    assert float(normalized.corr(truth)) > 0.9
    for weekday in range(7):
        assert normalized.loc[weekday] == pytest.approx(truth.loc[weekday], rel=0.35)


def test_baseline_predictions_are_non_negative(synthetic_repo: Path) -> None:
    """The Poisson objective makes this structural, not a clip after the fact."""
    training, future = _frames(synthetic_repo)
    model = BaselineModel()
    model.fit(training)
    assert (model.predict(future) >= 0).all()


def test_baseline_is_deterministic(synthetic_repo: Path) -> None:
    """Two fits on the same data give the same numbers."""
    training, future = _frames(synthetic_repo)
    first, second = BaselineModel(), BaselineModel()
    first.fit(training)
    second.fit(training)
    pd.testing.assert_series_equal(first.predict(future), second.predict(future))


def test_baseline_falls_back_when_history_is_too_short(synthetic_repo: Path) -> None:
    """Fewer than 30 days is not enough to fit; the recent mean stands in."""
    training, future = _frames(synthetic_repo)
    model = BaselineModel()
    model.fit(training.tail(10))
    predicted = model.predict(future)
    assert predicted.nunique() == 1
    assert predicted.iloc[0] == pytest.approx(float(training.tail(10)["visitors_total"].mean()))


def test_seasonal_naive_uses_only_observed_days(synthetic_repo: Path) -> None:
    """At horizon 8 the benchmark steps back two weeks rather than reusing a forecast."""
    training, future = _frames(synthetic_repo)
    model = SeasonalNaiveModel()
    model.fit(training)
    predicted = model.predict(future)
    observed = training.set_index("date")["visitors_total"]

    target_days = future["date"].to_numpy()
    horizons = future["horizon_days"].to_numpy()
    for position in range(len(future)):
        target = pd.Timestamp(target_days[position])
        weeks_back = (int(horizons[position]) + 6) // 7
        assert predicted.iloc[position] == observed.loc[target - pd.Timedelta(days=7 * weeks_back)]


def test_moving_average_is_flat_at_the_28_day_mean(synthetic_repo: Path) -> None:
    """The second benchmark is one number repeated."""
    training, future = _frames(synthetic_repo)
    model = MovingAverage28dModel()
    model.fit(training)
    predicted = model.predict(future)
    assert predicted.nunique() == 1
    assert predicted.iloc[0] == pytest.approx(float(training["visitors_total"].tail(28).mean()))


def test_prophet_xgb_is_skipped_cleanly_when_prophet_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing optional dependency is a warning and a skipped model, never a crash."""
    monkeypatch.delitem(sys.modules, "ovf_forecast.models.prophet_xgb", raising=False)
    monkeypatch.setitem(sys.modules, "prophet", None)

    with pytest.raises(ModelUnavailableError) as raised:
        build_model(PROPHET_XGB)
    assert "prophet" in str(raised.value)

    models, skipped = resolve_models(MODEL_NAMES)
    assert skipped == [PROPHET_XGB]
    assert [model.name for model in models] == [BASELINE]


def test_resolve_models_returns_benchmarks_too() -> None:
    """The benchmarks go through the same registry as the real models."""
    models, skipped = resolve_models((BASELINE, SEASONAL_NAIVE, MOVING_AVERAGE_28D))
    assert skipped == []
    assert [model.name for model in models] == [BASELINE, SEASONAL_NAIVE, MOVING_AVERAGE_28D]


def test_unknown_model_name_is_rejected() -> None:
    """A typo in ``--model`` must not silently do nothing."""
    with pytest.raises(KeyError):
        build_model("xgboost_only")
