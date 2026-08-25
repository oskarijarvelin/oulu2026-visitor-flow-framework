"""The exact reference numbers, measured on the data committed to this repository.

Every value here was computed from ``data/processed/visitors_daily.csv`` for the window
origin 2026-03-31, test 2026-04-01 to 2026-04-30. They are acceptance criteria, not
regression snapshots: if a change to the baselines moves them, the baselines have
changed meaning and the comparison in every stored report has changed with them.

They also pin the one decision that is easy to make silently. The evaluation reads the
venue series *untrimmed*, leading zero days included, because the training window is
whatever the caller named. Trimming them would move ``climatology_dow`` from 96.20 to
164.73 and the MASE denominator from 141.18 to 123.69.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.evaluation.baselines import (
    BASELINE_NAMES,
    CLIMATOLOGY_DOW,
    MOVING_AVERAGE_28D,
    SEASONAL_NAIVE,
    best_reference,
    leading_zero_days,
    mase_denominator,
    predict_baseline,
    resolve_reference,
)
from ovf_forecast.evaluation.runner import evaluation_history
from ovf_forecast.features import build_training_frame

ORIGIN = date(2026, 3, 31)
TEST_START = date(2026, 4, 1)
TEST_DAYS = 30
TOLERANCE = 0.01

# venue -> baseline -> (MAE, RMSE, bias, predicted total)
EXPECTED: dict[int, dict[str, tuple[float, float, float, float]]] = {
    1: {
        SEASONAL_NAIVE: (129.50, 158.12, 66.10, 15172.0),
        MOVING_AVERAGE_28D: (197.61, 219.80, 138.22, 17336.0),
        CLIMATOLOGY_DOW: (96.20, 122.72, 3.44, 13292.0),
    },
    2: {
        SEASONAL_NAIVE: (138.57, 171.31, 128.83, 7656.0),
        MOVING_AVERAGE_28D: (88.16, 106.26, 67.03, 5802.0),
        CLIMATOLOGY_DOW: (75.14, 95.56, 51.83, 5346.0),
    },
}
EXPECTED_ACTUAL_TOTAL = {1: 13189.0, 2: 3791.0}
EXPECTED_MASE_DENOMINATOR = {1: 141.18, 2: 128.57}
EXPECTED_LEADING_ZEROS = {1: 21, 2: 7}


@dataclass(frozen=True)
class Measured:
    """One venue's April window: what it trained on, what it forecast, what happened."""

    training: pd.DataFrame
    actual: np.ndarray
    forecasts: dict[str, np.ndarray]

    def mae(self) -> dict[str, float]:
        """Each baseline's MAE on the window."""
        return {
            name: float(np.abs(values - self.actual).mean())
            for name, values in self.forecasts.items()
        }


@pytest.fixture(scope="module")
def measured(real_repo: Path) -> dict[int, Measured]:
    """Every baseline's April forecast for both venues, plus the truth it is scored on."""
    data = load_dataset(real_repo)
    test_dates = [TEST_START + timedelta(days=step) for step in range(TEST_DAYS)]
    results: dict[int, Measured] = {}
    for venue_id in (1, 2):
        history = evaluation_history(data, venue_id)
        training = build_training_frame(history, ORIGIN)
        wanted = [pd.Timestamp(day) for day in test_dates]
        actual = history.loc[history["date"].isin(wanted)].sort_values("date")
        results[venue_id] = Measured(
            training=training,
            actual=actual["visitors_total"].to_numpy(dtype="float64"),
            forecasts={
                name: predict_baseline(name, training, ORIGIN, test_dates)
                for name in BASELINE_NAMES
            },
        )
    return results


@pytest.mark.parametrize("venue_id", [1, 2])
@pytest.mark.parametrize("name", BASELINE_NAMES)
def test_baseline_metrics_match_the_acceptance_criteria(
    measured: dict[int, Measured], venue_id: int, name: str
) -> None:
    """MAE, RMSE, bias and the period total of one baseline on the April window."""
    entry = measured[venue_id]
    forecast = entry.forecasts[name]
    error = forecast - entry.actual
    expected_mae, expected_rmse, expected_bias, expected_total = EXPECTED[venue_id][name]

    assert float(np.abs(error).mean()) == pytest.approx(expected_mae, abs=TOLERANCE)
    assert float(np.sqrt((error**2).mean())) == pytest.approx(expected_rmse, abs=TOLERANCE)
    assert float(error.mean()) == pytest.approx(expected_bias, abs=TOLERANCE)
    assert float(forecast.sum()) == pytest.approx(expected_total, abs=1.0)


@pytest.mark.parametrize("venue_id", [1, 2])
def test_the_actual_period_total_is_what_the_criteria_say(
    measured: dict[int, Measured], venue_id: int
) -> None:
    """The truth the totals are measured against."""
    actual = measured[venue_id].actual
    assert len(actual) == TEST_DAYS
    assert float(actual.sum()) == pytest.approx(EXPECTED_ACTUAL_TOTAL[venue_id], abs=0.5)


@pytest.mark.parametrize("venue_id", [1, 2])
def test_the_mase_denominator_comes_from_the_training_window_only(
    measured: dict[int, Measured], venue_id: int
) -> None:
    """MASE divides by the training window's own seasonal naive MAE, never the test's."""
    assert mase_denominator(measured[venue_id].training) == pytest.approx(
        EXPECTED_MASE_DENOMINATOR[venue_id], abs=TOLERANCE
    )


@pytest.mark.parametrize("venue_id", [1, 2])
def test_the_leading_zero_run_is_kept_and_counted(
    measured: dict[int, Measured], venue_id: int
) -> None:
    """The evaluation keeps the sensor-warmup zeros and reports how many there are.

    Production drops them. Here the training window is the one the caller named, so they
    stay in and the report says so instead of the left edge quietly moving.
    """
    assert leading_zero_days(measured[venue_id].training) == EXPECTED_LEADING_ZEROS[venue_id]


@pytest.mark.parametrize("venue_id", [1, 2])
def test_climatology_dow_is_the_hardest_baseline_in_april(
    measured: dict[int, Measured], venue_id: int
) -> None:
    """The default reference is the best baseline on the window, not seasonal naive.

    On this dataset ``climatology_dow`` wins April on both venues, which is exactly why
    a fixed ``seasonal_naive`` reference would be too easy a bar.
    """
    mae = measured[venue_id].mae()
    assert best_reference(mae) == CLIMATOLOGY_DOW
    assert resolve_reference("best", mae) == CLIMATOLOGY_DOW
    assert resolve_reference(SEASONAL_NAIVE, mae) == SEASONAL_NAIVE


def test_an_unknown_reference_is_rejected() -> None:
    """A typo in ``--reference`` fails loudly instead of silently picking a default."""
    with pytest.raises(KeyError):
        resolve_reference("naive", {SEASONAL_NAIVE: 1.0})


def test_the_moving_average_reads_exactly_28_days(measured: dict[int, Measured]) -> None:
    """The window is the 28 days ending at the origin, origin included."""
    training = measured[1].training
    forecast = predict_baseline(MOVING_AVERAGE_28D, training, ORIGIN, [TEST_START])
    window = training.loc[
        (training["date"] > pd.Timestamp(ORIGIN - timedelta(days=28)))
        & (training["date"] <= pd.Timestamp(ORIGIN))
    ]
    assert len(window) == 28
    assert float(forecast[0]) == pytest.approx(float(window["visitors_total"].mean()))
