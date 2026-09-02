"""The ranking rules, the residual pool they simulate from, and the leak rules."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pytest

from ovf_forecast.dataset import load_dataset, venue_history
from ovf_forecast.quiet.model import (
    DEFAULT_SCORE_MODEL,
    SCORE_MODELS,
    ScoreRequest,
    residual_origins,
    residual_pool,
    resolve_score_models,
    score_days,
    selection_probabilities,
)
from synthetic import DOW_FACTORS, LAST_OBSERVED_DAY

ORIGIN = LAST_OBSERVED_DAY
JULY = [date(2026, 7, day) for day in range(1, 32)]


def _request(root: Path, venue_id: int = 1, origin: date = ORIGIN) -> ScoreRequest:
    data = load_dataset(root)
    history = venue_history(data, venue_id)
    return ScoreRequest(
        data=data,
        venue_id=venue_id,
        history=history,
        origin=origin,
        days=tuple(day for day in JULY if day > origin),
    )


def test_the_default_rule_learns_the_weekday_rhythm(synthetic_repo: Path) -> None:
    """The synthetic series has a known rhythm; the score has to come back in that order."""
    request = _request(synthetic_repo)
    scores = score_days(DEFAULT_SCORE_MODEL, request)
    by_weekday: dict[int, float] = {}
    for day, score in zip(request.days, scores, strict=True):
        by_weekday.setdefault(day.weekday(), float(score))
    ranked = sorted(by_weekday, key=lambda weekday: by_weekday[weekday])
    expected = sorted(range(7), key=lambda weekday: DOW_FACTORS[weekday])
    assert ranked == expected


def test_every_rule_produces_one_finite_score_per_day(synthetic_repo: Path) -> None:
    request = _request(synthetic_repo)
    for name in SCORE_MODELS:
        scores = score_days(name, request)
        assert scores.shape == (len(request.days),), name
        assert np.isfinite(scores).all(), name


def test_a_score_cannot_see_past_its_origin(synthetic_repo: Path) -> None:
    """Handing the rule a longer history must not change what it says at the origin."""
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    origin = ORIGIN - timedelta(days=40)
    days = tuple(origin + timedelta(days=step) for step in range(1, 31))
    truncated = history.loc[history["date"] <= f"{origin.isoformat()}"]
    for name in SCORE_MODELS:
        full = score_days(name, ScoreRequest(data, 1, history, origin, days))
        cut = score_days(name, ScoreRequest(data, 1, truncated, origin, days))
        assert np.allclose(full, cut, equal_nan=True), name


def test_scoring_a_day_at_or_before_the_origin_is_refused(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1)
    with pytest.raises(ValueError, match="after the origin"):
        ScoreRequest(data, 1, history, ORIGIN, (ORIGIN,))


def test_residual_origins_never_forecast_past_the_outer_origin() -> None:
    origins = residual_origins(date(2026, 6, 30), date(2026, 1, 5), horizon_days=30)
    assert origins
    for origin in origins:
        assert origin + timedelta(days=30) <= date(2026, 6, 30)
    assert origins == sorted(origins, reverse=True)


def test_the_residual_pool_is_measured_and_centred_near_one(synthetic_repo: Path) -> None:
    pool = residual_pool(DEFAULT_SCORE_MODEL, _request(synthetic_repo))
    assert pool.size >= 30
    assert 0.8 < float(np.median(pool)) < 1.25


def test_selection_probabilities_sum_to_the_size_of_the_quiet_set() -> None:
    scores = np.array([100.0, 120.0, 140.0, 160.0, 180.0, 200.0, 220.0, 240.0], dtype="float64")
    residuals = np.array([0.8, 0.9, 1.0, 1.1, 1.2] * 8, dtype="float64")
    probabilities = selection_probabilities(scores, residuals, 3, n_simulations=2000)
    assert probabilities.sum() == pytest.approx(3.0, abs=1e-9)
    assert probabilities[0] > probabilities[-1]


def test_identical_scores_get_identical_probabilities() -> None:
    scores = np.array([100.0, 100.0, 100.0, 400.0, 400.0, 400.0], dtype="float64")
    residuals = np.array([0.7, 0.85, 1.0, 1.15, 1.3] * 6, dtype="float64")
    probabilities = selection_probabilities(scores, residuals, 3, n_simulations=4000)
    assert probabilities[:3] == pytest.approx(probabilities[:3].mean(), abs=0.05)
    assert probabilities[:3].mean() > 0.9
    assert probabilities[3:].mean() < 0.1


def test_an_empty_residual_pool_falls_back_to_the_plain_ranking() -> None:
    scores = np.array([5.0, 1.0, 3.0], dtype="float64")
    probabilities = selection_probabilities(scores, np.zeros(0, dtype="float64"), 1)
    assert probabilities.tolist() == [0.0, 1.0, 0.0]


def test_unknown_rules_are_refused() -> None:
    assert resolve_score_models(None) == (DEFAULT_SCORE_MODEL,)
    assert resolve_score_models(("baseline", "baseline")) == ("baseline",)
    with pytest.raises(KeyError, match="Unknown quiet-day rule"):
        resolve_score_models(("no_such_rule",))
