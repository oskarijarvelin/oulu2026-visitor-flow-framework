"""The period total, and the interval mistake this feature exists partly to avoid.

Adding up thirty daily p10 values and thirty daily p90 values does not give an interval
for the month. It gives the answer to "what if every single day landed at its own tenth
percentile", which needs all thirty errors to point the same way. The old application
shipped that and its monthly bands were unusable. The tests below pin both halves: the
simulated interval has to be narrower than the naive sum, and it has to be narrower for
the structural reason rather than by accident.
"""

from __future__ import annotations

import numpy as np
import pytest

from ovf_forecast.evaluation.totals import (
    MAX_MEDIAN_DRIFT,
    estimate_total,
    relative_errors,
    simulate_totals,
    summed_interval_is_wider,
)

DAYS = 30
LEVEL = 400.0


def _ratio_pool(seed: int = 1, size: int = 120, spread: float = 0.30) -> np.ndarray:
    """A pool of measured relative errors centred on 1."""
    generator = np.random.default_rng(seed)
    return np.clip(generator.normal(1.0, spread, size=size), 0.05, None)


def _estimate(**overrides: object) -> object:
    """One total estimate on a flat 30 day forecast, with a 0.6-1.6 daily band."""
    p50 = np.full(DAYS, LEVEL)
    arguments: dict[str, object] = {
        "model": "baseline",
        "weather_mode": "operational",
        "daily_p50": p50,
        "daily_p10": p50 * 0.6,
        "daily_p90": p50 * 1.6,
        "actual": p50,
        "ratios": _ratio_pool(),
        "n_resamples": 4000,
    }
    arguments.update(overrides)
    return estimate_total(**arguments)  # type: ignore[arg-type]


def test_the_period_interval_is_narrower_than_summing_the_daily_bands() -> None:
    """The headline of this module. Summing the daily bands is the wrong answer.

    The simulated interval lets a month contain both over- and under-forecast days, which
    cancel in the sum. The naive sum assumes they never cancel.
    """
    estimate = _estimate()
    assert estimate.width < estimate.summed_width  # type: ignore[attr-defined]
    assert summed_interval_is_wider(estimate)  # type: ignore[arg-type]


def test_the_naive_sum_is_exactly_the_sum_of_the_daily_bands() -> None:
    """The comparison column has to be the mistake itself, not an approximation of it."""
    estimate = _estimate()
    assert estimate.summed_p10 == pytest.approx(DAYS * LEVEL * 0.6)  # type: ignore[attr-defined]
    assert estimate.summed_p90 == pytest.approx(DAYS * LEVEL * 1.6)  # type: ignore[attr-defined]


def test_a_wider_error_pool_gives_a_wider_period_interval() -> None:
    """The interval has to respond to the spread it is built from."""
    narrow = _estimate(ratios=_ratio_pool(spread=0.10))
    wide = _estimate(ratios=_ratio_pool(spread=0.50))
    assert wide.width > narrow.width  # type: ignore[attr-defined]


def test_the_point_forecast_lies_inside_its_own_interval() -> None:
    """A band that excludes the number it is a band for cannot be published.

    The level shift it would otherwise show is still reported: as bias, as the difference
    column, and as ``median_ratio`` on the estimate itself.
    """
    biased = np.full(120, 1.8)
    estimate = _estimate(ratios=biased)
    assert estimate.p10 <= estimate.predicted <= estimate.p90  # type: ignore[attr-defined]
    assert estimate.is_drifted  # type: ignore[attr-defined]
    assert estimate.median_ratio == pytest.approx(1.8)  # type: ignore[attr-defined]


def test_a_centred_error_pool_is_not_flagged_as_drifted() -> None:
    """The drift flag has to stay quiet when the nested backtest was well behaved."""
    estimate = _estimate(ratios=_ratio_pool(spread=0.20))
    assert not estimate.is_drifted  # type: ignore[attr-defined]
    assert abs(estimate.median_ratio - 1.0) < MAX_MEDIAN_DRIFT  # type: ignore[attr-defined]


def test_the_difference_from_the_truth_is_reported_in_both_units() -> None:
    """A producer asks for visitors; a report needs the percentage too."""
    estimate = _estimate(actual=np.full(DAYS, 380.0))
    assert estimate.actual == pytest.approx(DAYS * 380.0)  # type: ignore[attr-defined]
    assert estimate.difference == pytest.approx(DAYS * 20.0)  # type: ignore[attr-defined]
    assert estimate.difference_pct == pytest.approx(20.0 / 380.0 * 100.0)  # type: ignore[attr-defined]


def test_a_thin_pool_is_flagged_rather_than_hidden() -> None:
    """Few measured errors still produce an interval, but one marked as thin."""
    estimate = _estimate(ratios=np.array([0.9, 1.0, 1.1]))
    assert estimate.is_thin  # type: ignore[attr-defined]
    assert estimate.n_ratio_samples == 3  # type: ignore[attr-defined]


def test_an_empty_pool_falls_back_instead_of_failing() -> None:
    """A window with no usable nested backtest still gets an interval, marked thin."""
    estimate = _estimate(ratios=np.zeros(0))
    assert estimate.is_thin  # type: ignore[attr-defined]
    assert estimate.p90 > estimate.p10  # type: ignore[attr-defined]


def test_the_simulation_is_deterministic() -> None:
    """Same seed, same interval; the whole run has to be reproducible."""
    pool = _ratio_pool()
    first = simulate_totals(np.full(DAYS, LEVEL), pool, n_resamples=500, seed=42)
    second = simulate_totals(np.full(DAYS, LEVEL), pool, n_resamples=500, seed=42)
    np.testing.assert_array_equal(first, second)


def test_simulated_totals_are_centred_on_the_forecast_times_the_median_ratio() -> None:
    """Sanity: multiplying a flat forecast by errors centred on 1 keeps the level."""
    totals = simulate_totals(np.full(DAYS, LEVEL), _ratio_pool(size=200), n_resamples=4000, seed=7)
    assert float(np.median(totals)) == pytest.approx(DAYS * LEVEL, rel=0.05)


def test_relative_errors_skip_denominators_too_small_to_divide_by() -> None:
    """A near-zero forecast makes the ratio explode and says nothing about spread."""
    ratios = relative_errors(np.array([100.0, 50.0, 10.0]), np.array([100.0, 0.0, 5.0]))
    np.testing.assert_allclose(ratios, [1.0, 2.0])
