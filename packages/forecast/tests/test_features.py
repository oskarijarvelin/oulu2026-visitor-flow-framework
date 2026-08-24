"""Feature construction: nothing a feature reads may come from after the origin."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ovf_forecast.dataset import load_dataset, venue_future, venue_history
from ovf_forecast.features import (
    FEATURE_COLUMNS,
    HOLIDAY_HORIZON_DAYS,
    TARGET,
    build_future_frame,
    build_training_frame,
    model_matrix,
    origin_levels,
)

ORIGIN = date(2026, 5, 31)
HORIZON_DAYS = 30


def test_future_features_ignore_observations_after_the_origin(synthetic_repo: Path) -> None:
    """Corrupting every observation after the origin must not move a single feature.

    This is the leakage test. The reference implementation cannot pass it, because its
    lag features are rebuilt from a series that already contains its own predictions.
    """
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    future = venue_future(data, 1, ORIGIN, HORIZON_DAYS)

    clean = build_future_frame(history, future, ORIGIN)

    corrupted = history.copy()
    after_origin = corrupted["date"] > pd.Timestamp(ORIGIN)
    assert bool(after_origin.any()), "the fixture must have observations after the origin"
    corrupted.loc[after_origin, TARGET] = 999_999.0
    corrupted.loc[after_origin, "visitors_in"] = 999_999.0
    corrupted.loc[after_origin, "temp_mean"] = -99.0
    dirty = build_future_frame(corrupted, future, ORIGIN)

    pd.testing.assert_frame_equal(model_matrix(clean), model_matrix(dirty))


def test_training_features_ignore_observations_after_the_origin(synthetic_repo: Path) -> None:
    """A training frame cut at the origin must not change when later days change."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)

    clean = build_training_frame(history, ORIGIN)
    corrupted = history.copy()
    corrupted.loc[corrupted["date"] > pd.Timestamp(ORIGIN), TARGET] = 999_999.0
    dirty = build_training_frame(corrupted, ORIGIN)

    assert clean["date"].max() == pd.Timestamp(ORIGIN)
    pd.testing.assert_frame_equal(model_matrix(clean), model_matrix(dirty))


def test_level_features_never_read_their_own_row(synthetic_repo: Path) -> None:
    """``level_7d`` on day t is the mean of t-7..t-1, not of a window containing t."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    training = build_training_frame(history, ORIGIN)
    series = training.set_index("date")[TARGET]
    row = training.iloc[-1]

    expected_short = series.loc[
        pd.Timestamp(ORIGIN) - pd.Timedelta(days=7) : pd.Timestamp(ORIGIN) - pd.Timedelta(days=1)
    ].mean()
    expected_long = series.loc[
        pd.Timestamp(ORIGIN) - pd.Timedelta(days=28) : pd.Timestamp(ORIGIN) - pd.Timedelta(days=1)
    ].mean()

    assert row["level_7d"] == pytest.approx(float(expected_short))
    assert row["level_28d"] == pytest.approx(float(expected_long))


def test_level_is_constant_across_the_horizon(synthetic_repo: Path) -> None:
    """The level features are computed once at the origin and never updated.

    A 30-day forecast is one forecast, not thirty chained one-day forecasts.
    """
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    frame = build_future_frame(history, venue_future(data, 1, ORIGIN, HORIZON_DAYS), ORIGIN)

    assert frame["level_7d"].nunique() == 1
    assert frame["level_28d"].nunique() == 1
    levels = origin_levels(history.loc[history["date"] <= pd.Timestamp(ORIGIN)], ORIGIN)
    assert frame["level_7d"].iloc[0] == levels.level_7d


def test_dow_index_varies_by_weekday(synthetic_repo: Path) -> None:
    """The weekday index is the one level feature that moves across the horizon."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    frame = build_future_frame(history, venue_future(data, 1, ORIGIN, HORIZON_DAYS), ORIGIN)

    by_weekday = frame.groupby(frame["date"].dt.dayofweek)["dow_index_28d"].first()
    assert by_weekday.loc[5] > by_weekday.loc[0], "Saturday is the busy day in the fixture"
    assert frame["dow_index_28d"].nunique() == 7


def test_holiday_distance_is_truncated(synthetic_repo: Path) -> None:
    """Beyond a fortnight the distance to the next holiday carries no signal."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    training = build_training_frame(history, ORIGIN)
    assert training["days_before_next_holiday"].max() <= HOLIDAY_HORIZON_DAYS


def test_training_and_future_matrices_have_the_same_columns(synthetic_repo: Path) -> None:
    """Both frames must present identical columns and dtypes to the estimator."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    training = model_matrix(build_training_frame(history, ORIGIN))
    future = model_matrix(build_future_frame(history, venue_future(data, 1, ORIGIN, HORIZON_DAYS), ORIGIN))

    assert list(training.columns) == list(FEATURE_COLUMNS)
    assert list(future.columns) == list(FEATURE_COLUMNS)
    assert training.dtypes.to_dict() == future.dtypes.to_dict()
