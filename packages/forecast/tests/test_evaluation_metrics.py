"""Metrics, the three weather modes, and the report the two of them produce.

The sMAPE assertions matter more than they look. Venue 2 closes on some public holidays,
and a zero actual sends the symmetric ratio to its 200 % ceiling however close the
forecast was. The metric is still computed, because leaving it out invites someone to
ask for it, but it has to arrive flagged and it must never reach a verdict.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.evaluation.metrics import (
    BUCKET_ALL,
    absolute_errors,
    coverage_counts,
    pinball_loss,
    score_window,
    signed_errors,
    smape,
    worst_days,
)
from ovf_forecast.evaluation.runner import (
    WEATHER_CLIMATOLOGY,
    WEATHER_MODES,
    WEATHER_OPERATIONAL,
    WEATHER_PERFECT,
    EvaluationConfig,
    max_forecast_days,
    resolve_weather_modes,
    run_window,
)
from ovf_forecast.evaluation.windows import make_window

MASE_DENOMINATOR = 100.0


def _predictions(y_true: list[float], p50: list[float], *, model: str = "baseline") -> pd.DataFrame:
    """A minimal prediction frame, one weather mode, horizons counting from 1."""
    days = pd.date_range("2026-04-01", periods=len(y_true), freq="D")
    return pd.DataFrame(
        {
            "venue_id": 1,
            "date": [day.date().isoformat() for day in days],
            "horizon_days": range(1, len(y_true) + 1),
            "model": model,
            "weather_mode": WEATHER_OPERATIONAL,
            "y_true": y_true,
            "p10": [value * 0.6 for value in p50],
            "p50": p50,
            "p90": [value * 1.6 for value in p50],
        }
    )


def test_mase_divides_by_the_training_denominator() -> None:
    """MASE is MAE over the training window's own seasonal naive MAE, nothing else."""
    frame = _predictions([100.0] * 10, [150.0] * 10)
    score = score_window(frame, MASE_DENOMINATOR).get(WEATHER_OPERATIONAL, "baseline", BUCKET_ALL)
    assert score is not None
    assert score.mae == pytest.approx(50.0)
    assert score.mase == pytest.approx(0.5)


def test_mase_is_missing_rather_than_infinite_without_a_denominator() -> None:
    """A training window too short to have a denominator reports nothing, not a divide."""
    frame = _predictions([100.0] * 5, [150.0] * 5)
    score = score_window(frame, float("nan")).get(WEATHER_OPERATIONAL, "baseline", BUCKET_ALL)
    assert score is not None
    assert np.isnan(score.mase)


def test_bias_carries_its_sign_and_a_percentage() -> None:
    """Over-forecasting is positive, and the report needs it relative to the level too."""
    frame = _predictions([100.0] * 10, [130.0] * 10)
    score = score_window(frame, MASE_DENOMINATOR).get(WEATHER_OPERATIONAL, "baseline", BUCKET_ALL)
    assert score is not None
    assert score.bias == pytest.approx(30.0)
    assert score.bias_pct == pytest.approx(30.0)


def test_pinball_loss_is_minimised_at_the_true_quantile() -> None:
    """The property that makes it a proper score: a wider p90 cannot be free."""
    generator = np.random.default_rng(3)
    sample = generator.normal(100.0, 20.0, size=20000)
    truth = float(np.quantile(sample, 0.9))
    at_truth = pinball_loss(sample, np.full(sample.shape, truth), 0.9)
    for offset in (-25.0, -10.0, 10.0, 25.0):
        assert pinball_loss(sample, np.full(sample.shape, truth + offset), 0.9) > at_truth


def test_pinball_loss_penalises_the_two_directions_differently() -> None:
    """At q = 0.9, being 10 short costs 9 and being 10 long costs 1."""
    assert pinball_loss(np.array([110.0]), np.array([100.0]), 0.9) == pytest.approx(9.0)
    assert pinball_loss(np.array([90.0]), np.array([100.0]), 0.9) == pytest.approx(1.0)


def test_smape_is_flagged_unreliable_when_the_test_period_has_a_zero_day() -> None:
    """Venue 2 closes on some holidays, and sMAPE cannot survive that."""
    frame = _predictions([100.0, 0.0, 120.0, 90.0], [110.0, 5.0, 115.0, 95.0])
    score = score_window(frame, MASE_DENOMINATOR).get(WEATHER_OPERATIONAL, "baseline", BUCKET_ALL)
    assert score is not None
    assert score.zero_days == 1
    assert score.smape_reliable is False


def test_smape_is_not_flagged_when_no_day_is_zero() -> None:
    """The flag has to stay off when it does not apply, or it stops meaning anything."""
    frame = _predictions([100.0, 110.0, 120.0], [105.0, 115.0, 118.0])
    score = score_window(frame, MASE_DENOMINATOR).get(WEATHER_OPERATIONAL, "baseline", BUCKET_ALL)
    assert score is not None
    assert score.zero_days == 0
    assert score.smape_reliable is True


def test_smape_explodes_on_a_zero_day_which_is_why_it_is_flagged() -> None:
    """The mechanism itself: a near-miss on a zero day still scores the 200 % ceiling."""
    assert smape(np.array([0.0]), np.array([3.0])) == pytest.approx(200.0)
    assert smape(np.array([500.0]), np.array([503.0])) < 1.0


def test_coverage_counts_only_days_with_a_usable_band() -> None:
    """A missing band is not a miss; it is a day that cannot be scored for coverage."""
    frame = _predictions([100.0, 100.0, 100.0], [100.0, 100.0, 100.0])
    frame.loc[2, ["p10", "p90"]] = [np.nan, np.nan]
    covered, total = coverage_counts(frame, WEATHER_OPERATIONAL, "baseline")
    assert (covered, total) == (2, 2)


def test_scores_are_bucketed_by_horizon_and_pooled(  ) -> None:
    """Buckets 1-7, 8-14, 15-30 plus an ``all`` row over the whole period."""
    frame = _predictions([100.0] * 30, [120.0] * 30)
    table = score_window(frame, MASE_DENOMINATOR)
    assert table.get(WEATHER_OPERATIONAL, "baseline", BUCKET_ALL).n == 30  # type: ignore[union-attr]
    assert table.get(WEATHER_OPERATIONAL, "baseline", "1-7").n == 7  # type: ignore[union-attr]
    assert table.get(WEATHER_OPERATIONAL, "baseline", "8-14").n == 7  # type: ignore[union-attr]
    assert table.get(WEATHER_OPERATIONAL, "baseline", "15-30").n == 16  # type: ignore[union-attr]


def test_errors_are_returned_in_date_order() -> None:
    """The block bootstrap resamples runs of days, so the order has to be the calendar's."""
    frame = _predictions([100.0, 200.0, 300.0], [110.0, 180.0, 350.0]).sample(frac=1.0, random_state=1)
    np.testing.assert_allclose(absolute_errors(frame, WEATHER_OPERATIONAL, "baseline"), [10.0, 20.0, 50.0])
    np.testing.assert_allclose(signed_errors(frame, WEATHER_OPERATIONAL, "baseline"), [10.0, -20.0, 50.0])


def test_the_worst_days_are_the_biggest_misses_first() -> None:
    """The most useful section of the report needs the right five days in the right order."""
    frame = _predictions([100.0, 100.0, 100.0, 100.0], [110.0, 400.0, 90.0, 250.0])
    worst = worst_days(frame, WEATHER_OPERATIONAL, "baseline", limit=2)
    assert list(worst["date"]) == ["2026-04-02", "2026-04-04"]
    assert list(worst["abs_error"]) == [300.0, 150.0]


# --------------------------------------------------------------------------------------
# The three weather modes
# --------------------------------------------------------------------------------------


def test_each_weather_mode_gets_the_observed_days_it_should() -> None:
    """perfect the whole period, operational the 16 Open-Meteo forecasts, climatology none."""
    assert max_forecast_days(WEATHER_PERFECT, 30) == 30
    assert max_forecast_days(WEATHER_OPERATIONAL, 30) == 16
    assert max_forecast_days(WEATHER_CLIMATOLOGY, 30) == 0
    with pytest.raises(KeyError):
        max_forecast_days("sunny", 30)


def test_resolving_weather_modes_defaults_to_all_three() -> None:
    """Running all three is the default, because one of them alone would mislead."""
    assert resolve_weather_modes(None) == WEATHER_MODES
    assert resolve_weather_modes(("climatology", "climatology")) == (WEATHER_CLIMATOLOGY,)
    with pytest.raises(KeyError):
        resolve_weather_modes(("sunny",))


def test_a_run_produces_all_three_modes_and_they_differ(synthetic_repo: Path) -> None:
    """The bracket is only informative if the modes actually give different forecasts.

    The synthetic series has a built-in rain response, so knowing the weather has to be
    worth something and the perfect and climatology forecasts must not coincide.
    """
    data = load_dataset(synthetic_repo)
    window = make_window(train_end="2026-04-30", test="2026-05-01:2026-05-30")
    run = run_window(data, data.venue(1), window, EvaluationConfig(models=("baseline",), n_resamples=200))
    assert run is not None
    modes = set(run.predictions["weather_mode"])
    assert modes == set(WEATHER_MODES)

    def forecast(mode: str) -> np.ndarray:
        rows = run.predictions.loc[
            (run.predictions["weather_mode"] == mode) & (run.predictions["model"] == "baseline")
        ].sort_values("date")
        return rows["p50"].to_numpy(dtype="float64")

    assert not np.allclose(forecast(WEATHER_PERFECT), forecast(WEATHER_CLIMATOLOGY))
    assert run.weather_days[WEATHER_PERFECT]["climatology"] == 0
    assert run.weather_days[WEATHER_CLIMATOLOGY]["observed"] == 0
    assert run.weather_days[WEATHER_OPERATIONAL]["observed"] == 16


def test_a_baseline_forecast_does_not_change_with_the_weather_mode(synthetic_repo: Path) -> None:
    """The baselines read only past visitor counts, so all three modes must agree."""
    data = load_dataset(synthetic_repo)
    window = make_window(train_end="2026-04-30", test="2026-05-01:2026-05-14")
    run = run_window(data, data.venue(1), window, EvaluationConfig(models=("baseline",), n_resamples=200))
    assert run is not None
    rows = run.predictions.loc[run.predictions["model"] == "climatology_dow"]
    per_mode = rows.pivot(index="date", columns="weather_mode", values="p50")
    for mode in WEATHER_MODES[1:]:
        np.testing.assert_allclose(per_mode[WEATHER_MODES[0]], per_mode[mode])
