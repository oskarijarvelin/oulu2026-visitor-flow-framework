"""Empirical prediction intervals: relative bands fitted to measured backtest error."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ovf_forecast.intervals import (
    BUCKET_LABELS,
    DEFAULT_BAND,
    MIN_SAMPLES,
    apply_bands,
    bands_to_dict,
    bucket_of,
    fit_bands,
)

MODEL = "baseline"


def _backtest(ratios: dict[int, list[float]], model: str = MODEL) -> pd.DataFrame:
    """A synthetic backtest frame with a chosen ``y_true / y_pred`` ratio per horizon."""
    records = []
    for horizon, values in ratios.items():
        for index, ratio in enumerate(values):
            records.append(
                {
                    "model": model,
                    "venue_id": 1,
                    "origin_date": f"2026-05-{(index % 9) + 1:02d}",
                    "target_date": "2026-05-20",
                    "horizon_days": horizon,
                    "y_pred": 100.0,
                    "y_true": 100.0 * ratio,
                }
            )
    return pd.DataFrame.from_records(records)


@pytest.mark.parametrize(
    ("horizon", "expected"),
    [(1, "1-7"), (7, "1-7"), (8, "8-14"), (14, "8-14"), (15, "15-30"), (30, "15-30")],
)
def test_horizon_buckets(horizon: int, expected: str) -> None:
    """Horizons land in the three buckets the plan defines."""
    assert bucket_of(horizon) == expected


def test_bands_are_the_empirical_quantiles_of_the_error_ratio() -> None:
    """q10 and q90 come straight out of the measured ``y_true / y_pred`` distribution."""
    ratios = [0.5 + step * 0.05 for step in range(21)]
    bands = fit_bands(_backtest({3: ratios}))
    band = bands[MODEL, "1-7"]

    expected = pd.Series(ratios)
    assert band.lower == pytest.approx(float(expected.quantile(0.10)))
    assert band.upper == pytest.approx(float(expected.quantile(0.90)))
    assert band.samples == len(ratios)
    assert not band.is_default


def test_bands_are_fitted_per_horizon_bucket() -> None:
    """A day-2 forecast and a day-27 forecast do not get the same width."""
    narrow = [0.9 + step * 0.01 for step in range(20)]
    wide = [0.3 + step * 0.07 for step in range(20)]
    bands = fit_bands(_backtest({3: narrow, 20: wide}))

    assert bands[MODEL, "15-30"].upper > bands[MODEL, "1-7"].upper
    assert bands[MODEL, "15-30"].lower < bands[MODEL, "1-7"].lower


def test_the_median_always_lies_inside_its_own_band() -> None:
    """A systematically biased model must still export p10 <= p50 <= p90."""
    biased = [1.8 + step * 0.05 for step in range(20)]
    band = fit_bands(_backtest({3: biased}))[MODEL, "1-7"]

    assert band.lower <= 1.0 <= band.upper


def test_too_few_samples_fall_back_to_the_default_band() -> None:
    """A bucket without enough backtest points says so rather than inventing a quantile."""
    bands = fit_bands(_backtest({3: [1.0, 1.1, 0.9]}))
    band = bands[MODEL, "1-7"]

    assert band.is_default
    assert band.samples < MIN_SAMPLES
    assert (band.lower, band.upper) == DEFAULT_BAND


def test_near_zero_forecasts_are_excluded_from_the_ratio() -> None:
    """Dividing by a forecast of 0.01 says nothing about the model's spread."""
    frame = _backtest({3: [1.0] * 20})
    frame.loc[frame.index[:5], "y_pred"] = 0.01
    band = fit_bands(frame)[MODEL, "1-7"]

    assert band.samples == 15


def test_apply_bands_scales_the_median_and_keeps_the_ordering() -> None:
    """Intervals are multiplicative, so the width follows the level."""
    bands = fit_bands(_backtest({3: [0.5 + step * 0.05 for step in range(21)]}))
    p50 = pd.Series([100.0, 1000.0, 0.0])
    horizons = pd.Series([1, 2, 3])
    p10, p90 = apply_bands(p50, horizons, bands, MODEL)

    assert (p10 <= p50).all()
    assert (p50 <= p90).all()
    assert (p10 >= 0).all()
    assert p90.iloc[1] / p50.iloc[1] == pytest.approx(p90.iloc[0] / p50.iloc[0])


def test_apply_bands_uses_the_default_for_an_unknown_model() -> None:
    """An unseen model still gets a usable, ordered interval."""
    p10, p90 = apply_bands(pd.Series([100.0]), pd.Series([1]), {}, "unknown")
    assert p10.iloc[0] == pytest.approx(100.0 * DEFAULT_BAND[0])
    assert p90.iloc[0] == pytest.approx(100.0 * DEFAULT_BAND[1])


def test_bands_serialize_in_bucket_order() -> None:
    """``metrics.json`` lists the buckets in the plan's order."""
    bands = fit_bands(_backtest({3: [1.0] * 20, 10: [1.0] * 20, 20: [1.0] * 20}))
    payload = bands_to_dict(bands, MODEL)
    assert [entry["bucket"] for entry in payload] == list(BUCKET_LABELS)


def test_infinite_ratios_are_dropped() -> None:
    """A zero denominator that slips through must not become an infinite band."""
    frame = _backtest({3: [1.0] * 20})
    frame.loc[frame.index[0], "y_pred"] = 1.0
    frame.loc[frame.index[0], "y_true"] = np.inf
    band = fit_bands(frame)[MODEL, "1-7"]
    assert np.isfinite(band.lower)
    assert np.isfinite(band.upper)
