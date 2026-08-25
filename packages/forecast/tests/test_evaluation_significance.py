"""Whether the statistics do what they claim.

The interesting test here is the coverage simulation. A confidence interval that is not
actually 95 % confident is worse than no interval, because it is quoted as though it
were. So a known difference is generated 200 times and the interval is asked how often
it contains the truth. The answer has to be close to 95 %, not merely non-empty.

The rest pin the arithmetic: MDE against a hand computation, Holm-Bonferroni against the
step-down definition, Clopper-Pearson against textbook values, and the block bootstrap's
structure against what a block bootstrap is supposed to be.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from ovf_forecast.evaluation.significance import (
    BIAS_OVER,
    BIAS_UNDER,
    BLOCK_LENGTH_DAYS,
    CALIBRATION_NARROW,
    CALIBRATION_OK,
    CALIBRATION_WIDE,
    VERDICT_BETTER,
    VERDICT_NO_DIFFERENCE,
    VERDICT_WORSE,
    assess_calibration,
    block_bootstrap_indices,
    clopper_pearson,
    compare,
    diebold_mariano,
    estimate_bias,
    holm_bonferroni,
    minimum_detectable_effect,
    newey_west_lag,
    pool_windows,
    rng,
    verdict_from_interval,
)

MONTE_CARLO_REPEATS = 200
MONTE_CARLO_DAYS = 60
MONTE_CARLO_RESAMPLES = 400
TRUE_DIFFERENCE = -12.0


def test_the_minimum_detectable_effect_matches_a_hand_computation() -> None:
    """``MDE = 2.8 * sd(d) / sqrt(n)``, computed by hand on a series with a known sd.

    The series is 1, 2, 3, 4, 5: mean 3, sample sd sqrt(2.5) = 1.5811..., n = 5. So the
    MDE is 2.8 * 1.5811 / sqrt(5) = 1.9799.
    """
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    expected = 2.8 * math.sqrt(2.5) / math.sqrt(5.0)
    assert expected == pytest.approx(1.97989, abs=1e-5)
    assert minimum_detectable_effect(values) == pytest.approx(expected, abs=1e-12)


def test_the_minimum_detectable_effect_is_zero_width_on_a_constant_series() -> None:
    """No spread means any difference at all would have been detectable."""
    assert minimum_detectable_effect(np.full(10, 4.0)) == pytest.approx(0.0)
    assert math.isnan(minimum_detectable_effect(np.array([1.0])))


def test_the_bootstrap_interval_covers_the_truth_about_95_percent_of_the_time() -> None:
    """Monte Carlo check that the 95 % interval is actually 95 % confident.

    Each repeat builds a paired error series whose true mean difference is known, then
    asks whether the bootstrap interval contains it. Anything far below 0.95 means the
    interval is too narrow and every verdict built on it is overconfident.
    """
    generator = np.random.default_rng(20260101)
    hits = 0
    for repeat in range(MONTE_CARLO_REPEATS):
        reference_errors = np.abs(generator.normal(120.0, 40.0, size=MONTE_CARLO_DAYS))
        model_errors = reference_errors + TRUE_DIFFERENCE + generator.normal(0.0, 30.0, size=MONTE_CARLO_DAYS)
        result = compare(
            model_errors,
            reference_errors,
            model="m",
            reference="r",
            n_resamples=MONTE_CARLO_RESAMPLES,
            seed=repeat,
        )
        if result.ci_low <= TRUE_DIFFERENCE <= result.ci_high:
            hits += 1
    coverage = hits / MONTE_CARLO_REPEATS
    assert 0.88 <= coverage <= 1.0, f"bootstrap coverage {coverage:.3f} is not near 0.95"


def test_a_clear_improvement_is_called_better() -> None:
    """A large, consistent gap has to produce an interval entirely below zero."""
    reference_errors = np.full(60, 200.0)
    model_errors = np.full(60, 100.0)
    result = compare(model_errors, reference_errors, model="m", reference="r", n_resamples=500)
    assert result.verdict == VERDICT_BETTER
    assert result.ci_high < 0.0
    assert result.skill_score == pytest.approx(0.5)


def test_a_clear_regression_is_called_worse() -> None:
    """And the same gap in the other direction has to be called what it is."""
    result = compare(np.full(60, 300.0), np.full(60, 100.0), model="m", reference="r", n_resamples=500)
    assert result.verdict == VERDICT_WORSE
    assert result.ci_low > 0.0
    assert result.skill_score == pytest.approx(-2.0)


def test_a_tiny_difference_in_a_noisy_series_is_not_called_a_difference() -> None:
    """The case the MDE exists for: a real but unresolvable gap reads as no difference."""
    generator = np.random.default_rng(7)
    reference_errors = np.abs(generator.normal(150.0, 60.0, size=30))
    model_errors = reference_errors - 1.0 + generator.normal(0.0, 60.0, size=30)
    result = compare(model_errors, reference_errors, model="m", reference="r", n_resamples=2000)
    assert result.verdict == VERDICT_NO_DIFFERENCE
    assert result.mde > 1.0, "a sample that cannot resolve 1 visitor must report an MDE above it"


def test_the_verdict_rule_is_the_sign_of_the_whole_interval() -> None:
    """Better below zero, worse above it, undecided when it straddles."""
    assert verdict_from_interval(-5.0, -1.0) == VERDICT_BETTER
    assert verdict_from_interval(1.0, 5.0) == VERDICT_WORSE
    assert verdict_from_interval(-1.0, 5.0) == VERDICT_NO_DIFFERENCE
    assert verdict_from_interval(float("nan"), 5.0) == VERDICT_NO_DIFFERENCE


def test_comparison_requires_paired_series() -> None:
    """Comparing forecasts made on different days is not a comparison."""
    with pytest.raises(ValueError, match="equal length"):
        compare(np.ones(10), np.ones(9), model="m", reference="r")


# --------------------------------------------------------------------------------------
# The block bootstrap itself
# --------------------------------------------------------------------------------------


def test_the_bootstrap_draws_contiguous_blocks() -> None:
    """Every block has to be a run of consecutive days, or the autocorrelation is lost."""
    indices = block_bootstrap_indices(28, block_length=7, n_resamples=50, generator=rng(1))
    assert indices.shape == (50, 28)
    for row in indices:
        for start in range(0, 28, 7):
            block = row[start : start + 7]
            np.testing.assert_array_equal(block, np.arange(block[0], block[0] + len(block)))


def test_the_bootstrap_can_draw_a_path_longer_than_its_pool() -> None:
    """The period total simulates 30 days out of however many measured errors exist."""
    indices = block_bootstrap_indices(30, source_length=90, block_length=7, n_resamples=10, generator=rng(2))
    assert indices.shape == (10, 30)
    assert indices.max() < 90


def test_the_bootstrap_is_deterministic_for_a_given_seed() -> None:
    """Same seed, same resamples, same verdict."""
    first = block_bootstrap_indices(30, n_resamples=100, generator=rng(5))
    second = block_bootstrap_indices(30, n_resamples=100, generator=rng(5))
    np.testing.assert_array_equal(first, second)


# --------------------------------------------------------------------------------------
# Diebold-Mariano
# --------------------------------------------------------------------------------------


def test_the_newey_west_lag_follows_the_stated_rule() -> None:
    """``ceil(1.5 * n**(1/3))``: 5 at n = 30, 7 at n = 100."""
    assert newey_west_lag(30) == 5
    assert newey_west_lag(100) == 7
    assert newey_west_lag(1) == 0


def test_the_dm_statistic_has_the_sign_of_the_difference() -> None:
    """Negative mean difference, negative statistic: the model is the better one."""
    generator = np.random.default_rng(3)
    statistic, lag = diebold_mariano(generator.normal(-20.0, 10.0, size=40))
    assert statistic < 0.0
    assert lag == newey_west_lag(40)


def test_the_dm_p_value_is_high_when_there_is_no_difference() -> None:
    """A series centred on zero must not produce a significant p-value."""
    generator = np.random.default_rng(11)
    result = compare(
        np.abs(generator.normal(100.0, 30.0, size=40)),
        np.abs(generator.normal(100.0, 30.0, size=40)),
        model="m",
        reference="r",
        n_resamples=2000,
    )
    assert result.dm_p_value > 0.05


# --------------------------------------------------------------------------------------
# Multiplicity, bias, calibration
# --------------------------------------------------------------------------------------


def test_holm_bonferroni_steps_down_and_stays_monotone() -> None:
    """The smallest p is multiplied by k, the next by k-1, and the sequence never falls."""
    adjusted = holm_bonferroni([0.01, 0.04, 0.03])
    assert adjusted[0] == pytest.approx(0.03)
    assert adjusted[2] == pytest.approx(0.06)
    assert adjusted[1] == pytest.approx(0.06)
    assert all(value <= 1.0 for value in adjusted)
    # Adjusted p-values must not decrease as the raw ones increase.
    by_raw = [adjusted[index] for index in np.argsort([0.01, 0.04, 0.03])]
    assert by_raw == sorted(by_raw)
    assert holm_bonferroni([0.9, 0.9])[0] == pytest.approx(1.0)


def test_holm_bonferroni_ignores_missing_p_values() -> None:
    """A comparison that could not produce a p-value must not shrink the family."""
    adjusted = holm_bonferroni([0.01, float("nan"), 0.02])
    assert math.isnan(adjusted[1])
    assert adjusted[0] == pytest.approx(0.02)


def test_clopper_pearson_matches_textbook_values() -> None:
    """The exact binomial interval, checked against published values."""
    low, high = clopper_pearson(24, 30, alpha=0.05)
    assert low == pytest.approx(0.6143, abs=1e-3)
    assert high == pytest.approx(0.9229, abs=1e-3)
    assert clopper_pearson(0, 10)[0] == 0.0
    assert clopper_pearson(10, 10)[1] == 1.0


def test_calibration_verdicts_follow_the_interval() -> None:
    """Calibrated when 0.80 is inside, otherwise too narrow or too wide."""
    assert assess_calibration(24, 30).verdict == CALIBRATION_OK
    assert assess_calibration(10, 30).verdict == CALIBRATION_NARROW
    assert assess_calibration(30, 30).verdict == CALIBRATION_WIDE


def test_bias_is_called_only_when_the_interval_excludes_zero() -> None:
    """A consistent over-forecast is named; noise around zero is not."""
    over = estimate_bias(np.full(40, 50.0), np.full(40, 400.0), n_resamples=500)
    assert over.verdict == BIAS_OVER
    assert over.pct_of_actual == pytest.approx(12.5)

    under = estimate_bias(np.full(40, -50.0), np.full(40, 400.0), n_resamples=500)
    assert under.verdict == BIAS_UNDER


def test_bias_is_rarely_claimed_when_there_is_none() -> None:
    """The false positive rate of the bias verdict, measured rather than assumed.

    One unbiased draw can still look biased — that is what a 5 % test means — so the
    check is over many draws. Asserting on a single seed would be asserting that one
    sample happened to behave, which is not a property of the estimator.
    """
    claimed = 0
    for seed in range(60):
        generator = np.random.default_rng(seed)
        estimate = estimate_bias(
            generator.normal(0.0, 80.0, size=60), np.full(60, 400.0), n_resamples=400, seed=seed
        )
        claimed += estimate.verdict in (BIAS_OVER, BIAS_UNDER)
    assert claimed / 60 <= 0.20, f"bias claimed on {claimed}/60 unbiased samples"


# --------------------------------------------------------------------------------------
# Pooling
# --------------------------------------------------------------------------------------


def test_pooling_resamples_windows_and_counts_them() -> None:
    """The pooled unit is the window, and the tally of for and against is reported."""
    windows = [np.full(30, -20.0), np.full(30, -25.0), np.full(30, 5.0), np.full(30, -18.0)]
    pooled = pool_windows(windows, model="m", reference="r", n_resamples=2000)
    assert pooled.n_windows == 4
    assert pooled.n_days == 120
    assert pooled.windows_favouring == 3
    assert pooled.windows_opposing == 1
    assert pooled.mean_difference == pytest.approx(-14.5)


def test_pooling_one_window_refuses_to_call_a_verdict() -> None:
    """One window cannot be bootstrapped across windows, so it decides nothing."""
    pooled = pool_windows([np.full(30, -50.0)], model="m", reference="r", n_resamples=100)
    assert pooled.n_windows == 1
    assert pooled.verdict == VERDICT_NO_DIFFERENCE


def test_pooling_nothing_is_safe() -> None:
    """An empty sweep produces an empty verdict rather than an exception."""
    pooled = pool_windows([], model="m", reference="r")
    assert pooled.n_windows == 0
    assert pooled.verdict == VERDICT_NO_DIFFERENCE


def test_the_default_block_length_is_a_week() -> None:
    """Seven days, so a resample keeps the weekly rhythm the series actually has."""
    assert BLOCK_LENGTH_DAYS == 7
