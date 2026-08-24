"""The acceptance criteria, measured on the data actually committed to the repository.

These are slower than the rest of the suite because they run the real backtest. They
exist so that a change which quietly makes the model worse than "same weekday last
week" fails the build instead of shipping.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from ovf_forecast.backtest import BacktestConfig, compute_metrics, origin_count, run_backtest
from ovf_forecast.dataset import load_dataset, venue_history
from ovf_forecast.intervals import BUCKET_LABELS
from ovf_forecast.models.base import BASELINE, MOVING_AVERAGE_28D, SEASONAL_NAIVE, ForecastModel
from ovf_forecast.models.baseline import BaselineModel, MovingAverage28dModel, SeasonalNaiveModel

VENUE_IDS = (1, 2)
NEAR = BUCKET_LABELS[0]
MIN_COVERAGE = 0.70
MAX_COVERAGE = 0.90
MIN_ORIGINS = 8


def _factory() -> list[ForecastModel]:
    return [BaselineModel(), SeasonalNaiveModel(), MovingAverage28dModel()]


@dataclass(frozen=True)
class Measured:
    """One venue's measured backtest: metrics per model and the number of origins."""

    metrics: dict[str, dict[str, dict[str, float | int]]]
    origins: int


@pytest.fixture(scope="module")
def measured(real_repo: Path) -> dict[int, Measured]:
    """Run the real backtest once for both venues and share it across the assertions."""
    data = load_dataset(real_repo)
    config = BacktestConfig()
    results: dict[int, Measured] = {}
    for venue_id in VENUE_IDS:
        frame = run_backtest(data, venue_id, venue_history(data, venue_id), _factory, config)
        results[venue_id] = Measured(metrics=compute_metrics(frame), origins=origin_count(frame))
    return results


@pytest.mark.parametrize("venue_id", VENUE_IDS)
def test_baseline_beats_seasonal_naive_at_the_near_horizon(
    measured: dict[int, Measured], venue_id: int
) -> None:
    """Acceptance criterion 2: the model has to earn its place at horizon 1-7."""
    metrics = measured[venue_id].metrics
    baseline_mae = float(metrics[BASELINE][NEAR]["mae"])
    naive_mae = float(metrics[SEASONAL_NAIVE][NEAR]["mae"])
    assert baseline_mae < naive_mae, (
        f"venue {venue_id}: baseline MAE {baseline_mae:.1f} does not beat seasonal_naive "
        f"{naive_mae:.1f} at horizon {NEAR}"
    )


@pytest.mark.parametrize("venue_id", VENUE_IDS)
def test_coverage_is_within_the_acceptable_range(measured: dict[int, Measured], venue_id: int) -> None:
    """Acceptance criterion 3: the 80 % interval has to cover 70-90 % at horizon 1-7."""
    coverage = float(measured[venue_id].metrics[BASELINE][NEAR]["coverage_80"])
    assert MIN_COVERAGE <= coverage <= MAX_COVERAGE, (
        f"venue {venue_id}: measured coverage {coverage:.2f} is outside "
        f"{MIN_COVERAGE:.2f}-{MAX_COVERAGE:.2f}"
    )


@pytest.mark.parametrize("venue_id", VENUE_IDS)
def test_the_backtest_has_enough_origins(measured: dict[int, Measured], venue_id: int) -> None:
    """The plan asks for at least eight origins, each with 60 days of training data."""
    assert measured[venue_id].origins >= MIN_ORIGINS


@pytest.mark.parametrize("venue_id", VENUE_IDS)
def test_every_model_and_benchmark_is_measured(measured: dict[int, Measured], venue_id: int) -> None:
    """Benchmarks are always computed, so a losing model cannot hide."""
    assert set(measured[venue_id].metrics) == {BASELINE, SEASONAL_NAIVE, MOVING_AVERAGE_28D}
