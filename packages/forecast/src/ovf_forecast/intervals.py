"""Prediction intervals from measured out-of-sample error, not from model assumptions.

The band for a horizon is the empirical 10th and 90th percentile of the *ratio*
``y_true / y_pred`` observed in the backtest. Relative rather than absolute is
deliberate: error spread scales with level, so an absolute error distribution pooled
across a 1200-visitor Saturday and a 90-visitor Monday gives the quiet day an
impossibly wide band and the busy day one that is too narrow.

Bands are fitted per horizon bucket, because a day-2 forecast and a day-27 forecast are
not equally uncertain, and per model, because a model's interval has to reflect that
model's own errors.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import log_event

HORIZON_BUCKETS: tuple[tuple[int, int], ...] = ((1, 7), (8, 14), (15, 30))
BUCKET_LABELS: tuple[str, ...] = tuple(f"{low}-{high}" for low, high in HORIZON_BUCKETS)

LOWER_QUANTILE = 0.10
UPPER_QUANTILE = 0.90
# A ratio needs a denominator worth dividing by. Below this the ratio explodes and says
# more about the near-zero forecast than about the model's spread.
MIN_DENOMINATOR = 1.0
MIN_SAMPLES = 12
# Used only when a bucket has too few backtest points to estimate anything.
DEFAULT_BAND = (0.55, 1.75)


@dataclass(frozen=True)
class Band:
    """The multiplicative interval of one model in one horizon bucket."""

    model: str
    bucket: str
    lower: float
    upper: float
    samples: int
    is_default: bool

    def to_dict(self) -> dict[str, float | int | str | bool]:
        """Serialize for ``metrics.json``."""
        return {
            "bucket": self.bucket,
            "q10": round(self.lower, 4),
            "q90": round(self.upper, 4),
            "n": self.samples,
            "is_default": self.is_default,
        }


def bucket_of(horizon: int) -> str:
    """The bucket label a horizon falls in."""
    for (low, high), label in zip(HORIZON_BUCKETS, BUCKET_LABELS, strict=True):
        if low <= horizon <= high:
            return label
    return BUCKET_LABELS[-1]


def bucket_series(horizons: pd.Series) -> pd.Series:
    """Bucket labels for a column of horizons."""
    return horizons.map(lambda value: bucket_of(int(value)))


def fit_bands(backtest: pd.DataFrame, *, exclude_origin: str | None = None) -> dict[tuple[str, str], Band]:
    """Fit one band per (model, bucket) from backtest rows.

    ``exclude_origin`` drops one origin, which is how the backtest file gets intervals
    that were not calibrated on the very rows they are scored against.
    """
    if backtest.empty:
        return {}
    frame = backtest
    if exclude_origin is not None:
        frame = frame.loc[frame["origin_date"] != exclude_origin]
    bands: dict[tuple[str, str], Band] = {}
    frame = frame.assign(bucket=bucket_series(frame["horizon_days"]))
    usable = frame.loc[
        (pd.to_numeric(frame["y_pred"], errors="coerce") >= MIN_DENOMINATOR)
        & pd.to_numeric(frame["y_true"], errors="coerce").notna()
    ]
    for model in sorted(backtest["model"].unique()):
        for bucket in BUCKET_LABELS:
            rows = usable.loc[(usable["model"] == model) & (usable["bucket"] == bucket)]
            bands[model, bucket] = _band_from_ratios(model, bucket, rows)
    return bands


def _band_from_ratios(model: str, bucket: str, rows: pd.DataFrame) -> Band:
    """The 10th and 90th percentile of ``y_true / y_pred``, with a floor on sample size."""
    if len(rows) < MIN_SAMPLES:
        log_event(
            "warning",
            "intervals",
            "Too few backtest points for an empirical band, using the default",
            model=model,
            bucket=bucket,
            samples=len(rows),
            minimum=MIN_SAMPLES,
        )
        return Band(model, bucket, DEFAULT_BAND[0], DEFAULT_BAND[1], len(rows), True)
    ratios = (
        pd.to_numeric(rows["y_true"], errors="coerce") / pd.to_numeric(rows["y_pred"], errors="coerce")
    ).replace([np.inf, -np.inf], np.nan).dropna()
    lower = float(ratios.quantile(LOWER_QUANTILE))
    upper = float(ratios.quantile(UPPER_QUANTILE))
    # The median forecast has to lie inside its own interval. A band that excludes p50
    # would mean the point forecast is biased, which the bias metric reports separately;
    # it must not also produce a p10 above p50 in the exported file.
    return Band(model, bucket, min(lower, 1.0), max(upper, 1.0), len(ratios), False)


def apply_bands(
    p50: pd.Series, horizons: pd.Series, bands: dict[tuple[str, str], Band], model: str
) -> tuple[pd.Series, pd.Series]:
    """Scale a p50 series into p10 and p90 using the model's bands."""
    lower_factors = []
    upper_factors = []
    for horizon in horizons:
        band = bands.get((model, bucket_of(int(horizon))))
        lower_factors.append(band.lower if band else DEFAULT_BAND[0])
        upper_factors.append(band.upper if band else DEFAULT_BAND[1])
    values = pd.to_numeric(p50, errors="coerce").astype("float64")
    p10 = values * pd.Series(lower_factors, index=values.index, dtype="float64")
    p90 = values * pd.Series(upper_factors, index=values.index, dtype="float64")
    return p10.clip(lower=0.0), p90.clip(lower=0.0)


def bands_to_dict(
    bands: dict[tuple[str, str], Band], model: str
) -> list[dict[str, float | int | str | bool]]:
    """The bands of one model, ordered by bucket, for ``metrics.json``."""
    return [bands[model, bucket].to_dict() for bucket in BUCKET_LABELS if (model, bucket) in bands]
