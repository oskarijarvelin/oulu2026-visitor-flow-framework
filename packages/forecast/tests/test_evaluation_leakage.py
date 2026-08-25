"""The tests that decide whether the evaluation is worth anything at all.

An evaluation whose forecast has seen the test period measures nothing. These tests
attack that from the outside: run the pipeline, replace everything after the origin with
random noise, run it again, and demand the forecasts come back bit for bit identical. If
any part of training, feature construction, baseline lookup or interval calibration
reaches past the origin, the noise reaches the output and the comparison fails.

Weather needs one distinction, and it is not a loophole. The *target* after the origin
must never touch a forecast: that is the leak. Post-origin *weather* is a different
thing, because production has a weather forecast and the three weather modes exist
precisely to bracket how much that forecast is worth. So ``climatology`` mode is held to
the strict standard — nothing after the origin, weather included — while ``perfect`` and
``operational`` are held to the standard that matters for them: no future visitor count
may move a prediction, however much the weather is scrambled.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.evaluation.baselines import CLIMATOLOGY_DOW, SEASONAL_NAIVE, predict_baseline
from ovf_forecast.evaluation.runner import (
    WEATHER_CLIMATOLOGY,
    EvaluationConfig,
    evaluation_history,
    run_nested_backtest,
    run_window,
)
from ovf_forecast.evaluation.windows import Window
from ovf_forecast.features import build_training_frame

ORIGIN = date(2026, 4, 30)
TEST_START = date(2026, 5, 1)
TEST_END = date(2026, 5, 30)
VENUE_ID = 1
NOISE_SEED = 4242

FORECAST_COLUMNS = ["venue_id", "date", "horizon_days", "model", "weather_mode", "p10", "p50", "p90"]


@pytest.fixture
def window() -> Window:
    """One ordinary window, with enough history behind it for a nested backtest."""
    return Window(origin=ORIGIN, test_start=TEST_START, test_end=TEST_END)


@pytest.fixture
def config() -> EvaluationConfig:
    """Every weather mode, one model. The bootstrap count is small; nothing here uses it."""
    return EvaluationConfig(models=("baseline",), n_resamples=200)


def corrupt_visitors_after(root: Path, origin: date, *, seed: int = NOISE_SEED) -> None:
    """Replace every observed visitor count after ``origin`` with a random number."""
    generator = np.random.default_rng(seed)
    path = root / "data" / "processed" / "visitors_daily.csv"
    visitors = pd.read_csv(path)
    future = pd.to_datetime(visitors["date"]) > pd.Timestamp(origin)
    for column in ("visitors_in", "visitors_out", "visitors_total"):
        visitors.loc[future, column] = generator.integers(0, 5000, size=int(future.sum()))
    visitors.to_csv(path, index=False, lineterminator="\n")


def corrupt_weather_after(root: Path, origin: date, *, seed: int = NOISE_SEED + 1) -> None:
    """Replace every observed weather value after ``origin`` with a random number."""
    generator = np.random.default_rng(seed)
    path = root / "data" / "processed" / "weather_daily.csv"
    weather = pd.read_csv(path)
    future = pd.to_datetime(weather["date"]) > pd.Timestamp(origin)
    count = int(future.sum())
    for column, low, high in (
        ("temp_mean", -40.0, 40.0),
        ("temp_max", -40.0, 40.0),
        ("precip_sum", 0.0, 90.0),
        ("precip_hours", 0.0, 24.0),
        ("wind_mean", 0.0, 60.0),
    ):
        # ``precip_hours`` round-trips as int64, and assigning floats into it raises.
        weather[column] = weather[column].astype("float64")
        weather.loc[future, column] = generator.uniform(low, high, size=count)
    weather.to_csv(path, index=False, lineterminator="\n")


def test_no_future_visitor_count_can_move_a_forecast(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """The leak test. This is the most important assertion in the feature.

    ``y_true`` is deliberately left out of the comparison: it is the answer being graded,
    so of course it changes when the answers are overwritten. Everything the models and
    the baselines produced — p10, p50, p90, in all three weather modes — must not.
    """
    data = load_dataset(synthetic_repo)
    venue = data.venue(VENUE_ID)
    before = run_window(data, venue, window, config)
    assert before is not None
    assert not before.predictions.empty

    corrupt_visitors_after(synthetic_repo, window.origin)
    after = run_window(load_dataset(synthetic_repo), venue, window, config)
    assert after is not None

    pd.testing.assert_frame_equal(
        before.predictions[FORECAST_COLUMNS], after.predictions[FORECAST_COLUMNS], check_exact=True
    )


def test_climatology_mode_ignores_everything_after_the_origin(
    synthetic_repo: Path, window: Window
) -> None:
    """The strict version: in climatology mode not one post-origin value may be read."""
    config = EvaluationConfig(
        models=("baseline",), weather_modes=(WEATHER_CLIMATOLOGY,),
        primary_weather_mode=WEATHER_CLIMATOLOGY, n_resamples=200,
    )
    data = load_dataset(synthetic_repo)
    venue = data.venue(VENUE_ID)
    before = run_window(data, venue, window, config)
    assert before is not None

    corrupt_visitors_after(synthetic_repo, window.origin)
    corrupt_weather_after(synthetic_repo, window.origin)
    after = run_window(load_dataset(synthetic_repo), venue, window, config)
    assert after is not None

    pd.testing.assert_frame_equal(
        before.predictions[FORECAST_COLUMNS], after.predictions[FORECAST_COLUMNS], check_exact=True
    )


def test_the_nested_backtest_never_sees_the_test_period(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """The same test aimed at the interval quantiles.

    This is the leak that is easiest to ship by accident: a production run calibrates its
    bands on the most recent data available, and in an evaluation the most recent data is
    the test period. Coverage calibrated that way would read 80 % by construction and
    prove nothing. Here both the visitors and the weather after the origin are scrambled,
    because the nested backtest is supposed to read neither.
    """
    data = load_dataset(synthetic_repo)
    before = run_nested_backtest(data, VENUE_ID, evaluation_history(data, VENUE_ID), window, config)
    assert not before.empty

    corrupt_visitors_after(synthetic_repo, window.origin)
    corrupt_weather_after(synthetic_repo, window.origin)
    reloaded = load_dataset(synthetic_repo)
    after = run_nested_backtest(
        reloaded, VENUE_ID, evaluation_history(reloaded, VENUE_ID), window, config
    )

    pd.testing.assert_frame_equal(before, after, check_exact=True)


def test_no_nested_forecast_day_lands_after_the_origin(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """Structural proof of the same thing: the inner horizons stop at the origin."""
    data = load_dataset(synthetic_repo)
    nested = run_nested_backtest(data, VENUE_ID, evaluation_history(data, VENUE_ID), window, config)
    assert not nested.empty
    assert nested["target_date"].max() <= window.origin.isoformat()
    assert nested["origin_date"].max() <= (window.origin - timedelta(days=window.horizon_days)).isoformat()


def test_seasonal_naive_does_not_read_the_test_period_past_horizon_seven(
    synthetic_repo: Path,
) -> None:
    """``y[t-7]`` would stop being a benchmark at horizon 8 and become an oracle.

    Every value the benchmark returns has to come out of the week that ended at the
    origin, whatever the horizon.
    """
    data = load_dataset(synthetic_repo)
    training = build_training_frame(evaluation_history(data, VENUE_ID), ORIGIN)
    test_dates = [TEST_START + timedelta(days=step) for step in range(30)]
    forecast = predict_baseline(SEASONAL_NAIVE, training, ORIGIN, test_dates)

    week = training.loc[
        (training["date"] > pd.Timestamp(ORIGIN) - pd.Timedelta(days=7))
        & (training["date"] <= pd.Timestamp(ORIGIN))
    ]
    allowed = set(week["visitors_total"].astype("float64"))
    assert set(forecast.tolist()) <= allowed
    assert len(forecast[7:]) == 23
    assert set(forecast[7:].tolist()) <= allowed


def test_corrupting_the_future_does_not_move_the_seasonal_naive(synthetic_repo: Path) -> None:
    """The same benchmark, tested the same way the model is."""
    data = load_dataset(synthetic_repo)
    test_dates = [TEST_START + timedelta(days=step) for step in range(30)]
    before = predict_baseline(
        SEASONAL_NAIVE, build_training_frame(evaluation_history(data, VENUE_ID), ORIGIN), ORIGIN, test_dates
    )
    corrupt_visitors_after(synthetic_repo, ORIGIN)
    reloaded = load_dataset(synthetic_repo)
    after = predict_baseline(
        SEASONAL_NAIVE,
        build_training_frame(evaluation_history(reloaded, VENUE_ID), ORIGIN),
        ORIGIN,
        test_dates,
    )
    np.testing.assert_array_equal(before, after)


def test_baselines_are_flat_across_the_horizon(synthetic_repo: Path) -> None:
    """Each baseline repeats one weekly or constant pattern, so horizon 30 is as blind as
    horizon 1."""
    data = load_dataset(synthetic_repo)
    training = build_training_frame(evaluation_history(data, VENUE_ID), ORIGIN)
    test_dates = [TEST_START + timedelta(days=step) for step in range(28)]
    for name in (SEASONAL_NAIVE, CLIMATOLOGY_DOW):
        forecast = predict_baseline(name, training, ORIGIN, test_dates)
        for week in range(1, 4):
            np.testing.assert_array_equal(forecast[week * 7 : (week + 1) * 7], forecast[:7])
