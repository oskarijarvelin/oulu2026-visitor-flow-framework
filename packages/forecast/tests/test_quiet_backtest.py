"""The measuring instrument: does a window score what it should, and does pooling hold up."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.evaluation.windows import Window
from ovf_forecast.quiet import quiet_history_bounds
from ovf_forecast.quiet.backtest import (
    VERDICT_BETTER_THAN_CHANCE,
    VERDICT_USEFUL,
    QuietBacktestConfig,
    calibration_table,
    minimum_detectable_effect,
    pool,
    run_sweep,
    run_window,
)
from ovf_forecast.quiet.forecast import month_days
from synthetic import LAST_OBSERVED_DAY

FAST = QuietBacktestConfig(n_resamples=300, n_simulations=400)


def _window(year: int, month: int) -> Window:
    days = month_days(year, month)
    return Window(origin=days[0] - timedelta(days=1), test_start=days[0], test_end=days[-1])


def _windows() -> list[Window]:
    return [_window(2026, month) for month in (4, 5, 6)]


def test_one_window_scores_the_ranking_against_what_happened(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    outcome = run_window(data, data.venue(1), _window(2026, 5), "quiet_calendar", FAST)
    assert outcome is not None
    assert outcome.n_eligible == 31
    assert outcome.k == 7
    assert len(outcome.predicted) == outcome.k == len(outcome.truth)
    assert outcome.chance_rate == pytest.approx(7 / 31)


def test_a_known_weekly_rhythm_is_found_and_pays_off(synthetic_repo: Path) -> None:
    """The synthetic month really is quieter on Mondays, so the rule has to beat chance."""
    data = load_dataset(synthetic_repo)
    outcome = run_window(data, data.venue(1), _window(2026, 5), "quiet_calendar", FAST)
    assert outcome is not None
    assert outcome.hit_rate > outcome.chance_rate
    assert outcome.benefit > 0.1
    assert 0.0 < outcome.capture <= 1.2
    assert outcome.spearman > 0.5


def test_a_window_outside_the_history_is_skipped(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    future = _window(2026, 8)
    assert run_window(data, data.venue(1), future, "quiet_calendar", FAST) is None


def test_pooling_gives_one_verdict_per_venue_and_rule(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    config = QuietBacktestConfig(
        score_models=("quiet_calendar", "seasonal_naive"), n_resamples=300, n_simulations=400
    )
    outcomes = run_sweep(data, _windows(), config)
    pooled = pool(outcomes, config)
    assert {(row.venue_id, row.model) for row in pooled} == {
        (venue.venue_id, model) for venue in data.venues for model in config.score_models
    }
    for row in pooled:
        assert row.n_windows == 3
        assert row.benefit_ci_low <= row.benefit <= row.benefit_ci_high


def test_the_verdict_is_useful_when_the_rhythm_is_real(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    outcomes = run_sweep(data, _windows(), FAST)
    pooled = [row for row in pool(outcomes, FAST) if row.venue_id == 1]
    assert pooled[0].verdict == VERDICT_USEFUL
    assert pooled[0].hit_verdict == VERDICT_BETTER_THAN_CHANCE
    assert pooled[0].hit_rate > pooled[0].chance_rate


def test_the_calibration_table_accounts_for_every_eligible_day(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    outcomes = [
        outcome
        for outcome in run_sweep(data, _windows(), FAST)
        if outcome.venue_id == 1
    ]
    table = calibration_table(outcomes)
    assert sum(int(row["n"]) for row in table) == sum(outcome.n_eligible for outcome in outcomes)


def test_the_minimum_detectable_effect_shrinks_as_windows_are_added() -> None:
    values = np.array([0.10, 0.20, 0.05, 0.15], dtype="float64")
    assert minimum_detectable_effect(values) > minimum_detectable_effect(np.tile(values, 4))
    assert np.isnan(minimum_detectable_effect(np.array([0.1])))


def test_history_bounds_start_where_the_venue_starts_reporting(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    first, last = quiet_history_bounds(data, None)
    assert last == LAST_OBSERVED_DAY
    assert first == date(2026, 1, 5)
