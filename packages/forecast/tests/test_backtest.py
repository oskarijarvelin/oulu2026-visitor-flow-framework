"""The rolling origin backtest and the metrics computed from it."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from ovf_forecast.backtest import (
    BACKTEST_COLUMNS,
    BacktestConfig,
    build_origins,
    compare_to_benchmarks,
    compute_metrics,
    origin_count,
    run_backtest,
)
from ovf_forecast.dataset import load_dataset, venue_history
from ovf_forecast.intervals import BUCKET_LABELS, fit_bands
from ovf_forecast.models.base import BASELINE, MOVING_AVERAGE_28D, SEASONAL_NAIVE, ForecastModel
from ovf_forecast.models.baseline import BaselineModel, MovingAverage28dModel, SeasonalNaiveModel

CONFIG = BacktestConfig(max_origins=8)


def _factory() -> list[ForecastModel]:
    return [BaselineModel(), SeasonalNaiveModel(), MovingAverage28dModel()]


@pytest.fixture(scope="module")
def scored(synthetic_repo_module: Path) -> pd.DataFrame:
    """One backtest of venue 1, shared by every assertion that only reads it.

    Fitting eight origins is the expensive part of this suite, so the tests that merely
    inspect the result pay for it once.
    """
    data = load_dataset(synthetic_repo_module)
    return run_backtest(data, 1, venue_history(data, 1), _factory, CONFIG)


def test_origins_step_back_one_week_at_a_time(synthetic_repo: Path) -> None:
    """Origins are weekly and stop when the training window gets too short."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    origins = build_origins(history, CONFIG)

    last = history["date"].max().date()
    assert origins[0] == last - pd.Timedelta(days=7)
    for earlier, later in zip(origins[1:], origins[:-1], strict=True):
        assert (later - earlier).days == 7
    for origin in origins:
        training_days = (pd.Timestamp(origin) - history["date"].min()).days + 1
        assert training_days >= CONFIG.min_training_days


def test_origins_respect_the_training_floor(synthetic_repo: Path) -> None:
    """A 200-day floor leaves fewer origins than a 60-day one, and never a shorter fit."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    strict = build_origins(history, BacktestConfig(min_training_days=170, max_origins=20))
    relaxed = build_origins(history, BacktestConfig(min_training_days=60, max_origins=20))
    assert len(strict) < len(relaxed)


def test_backtest_never_trains_on_data_after_the_origin(synthetic_repo: Path) -> None:
    """Changing the future must not change a prediction made from the past.

    Every observation after the earliest origin is replaced with an absurd value. The
    predictions must be identical, because none of them were allowed to see it.
    """
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    config = BacktestConfig(max_origins=2)
    origins = build_origins(history, config)
    earliest = pd.Timestamp(min(origins))

    clean = run_backtest(data, 1, history, _factory, config)

    corrupted_data = load_dataset(synthetic_repo)
    corrupted = history.copy()
    after = corrupted["date"] > earliest
    corrupted.loc[after, "visitors_total"] = 999_999.0
    dirty = run_backtest(corrupted_data, 1, corrupted, _factory, config)

    merged = clean.merge(dirty, on=["model", "origin_date", "target_date"], suffixes=("", "_dirty"))
    same_origin = merged["origin_date"] == str(earliest.date())
    pd.testing.assert_series_equal(
        merged.loc[same_origin, "y_pred"],
        merged.loc[same_origin, "y_pred_dirty"],
        check_names=False,
    )


def test_backtest_rows_carry_the_full_schema(scored: pd.DataFrame) -> None:
    """``backtest.csv`` is a contract with the web section."""
    frame = scored

    assert list(frame.columns) == BACKTEST_COLUMNS
    assert not frame.empty
    assert (frame["horizon_days"] >= 1).all()
    assert (frame["horizon_days"] <= CONFIG.horizon_days).all()
    assert frame["y_pred"].notna().all()
    assert (frame["p10"] <= frame["p90"]).all()
    for _, group in frame.groupby(["model", "origin_date"]):
        origin = pd.Timestamp(group["origin_date"].iloc[0])
        assert (pd.to_datetime(group["target_date"]) > origin).all()


def test_metrics_cover_every_model_and_bucket(scored: pd.DataFrame) -> None:
    """Metrics are reported per model and per horizon bucket, benchmarks included."""
    metrics = compute_metrics(scored)

    assert set(metrics) == {BASELINE, SEASONAL_NAIVE, MOVING_AVERAGE_28D}
    for buckets in metrics.values():
        assert set(buckets) == set(BUCKET_LABELS)
        for values in buckets.values():
            assert set(values) == {"mae", "rmse", "smape", "bias", "coverage_80", "n"}
            assert values["mae"] >= 0
            assert values["rmse"] >= values["mae"]


def test_benchmarks_are_always_reported_alongside_the_model(scored: pd.DataFrame) -> None:
    """The honesty gate: every bucket says whether each benchmark was beaten."""
    comparison = compare_to_benchmarks(
        compute_metrics(scored), (BASELINE,), (SEASONAL_NAIVE, MOVING_AVERAGE_28D)
    )

    for bucket in BUCKET_LABELS:
        entry = comparison[BASELINE][bucket]
        assert f"beats_{SEASONAL_NAIVE}" in entry
        assert f"beats_{MOVING_AVERAGE_28D}" in entry
        assert isinstance(entry[f"beats_{SEASONAL_NAIVE}"], bool)


def test_baseline_beats_the_benchmarks_on_a_clean_signal(scored: pd.DataFrame) -> None:
    """On data with a real rhythm, the model has to be better than the naive rules."""
    metrics = compute_metrics(scored)

    near = BUCKET_LABELS[0]
    assert metrics[BASELINE][near]["mae"] < metrics[SEASONAL_NAIVE][near]["mae"]
    assert metrics[BASELINE][near]["mae"] < metrics[MOVING_AVERAGE_28D][near]["mae"]


def test_coverage_is_measured_out_of_sample(scored: pd.DataFrame) -> None:
    """The band applied to an origin is fitted without that origin."""
    frame = scored

    assert origin_count(frame) >= 2
    coverage = compute_metrics(frame)[BASELINE][BUCKET_LABELS[0]]["coverage_80"]
    assert 0.0 <= float(coverage) <= 1.0

    # The band applied to each origin must actually differ from the all-origin band,
    # otherwise "leave one origin out" is not happening at all.
    all_origins = fit_bands(frame)
    for origin in sorted(frame["origin_date"].unique()):
        held_out = fit_bands(frame, exclude_origin=str(origin))
        assert held_out[BASELINE, BUCKET_LABELS[0]].samples < all_origins[BASELINE, BUCKET_LABELS[0]].samples
