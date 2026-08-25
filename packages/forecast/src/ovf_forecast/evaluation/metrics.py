"""The scoreboard: point accuracy, quantile accuracy and interval coverage.

Everything is computed per venue, per model, per weather mode and per horizon bucket,
plus an ``all`` row over the whole test period. MAE is the headline. MASE makes two
venues with a 460-visitor and a 166-visitor mean comparable. Pinball loss is the only
proper score here for a quantile forecast, so a model cannot buy coverage by widening
its band for free.

sMAPE is computed and immediately flagged. Venue 2 closes on some public holidays, and a
zero actual sends the symmetric ratio to its 200 % ceiling regardless of how close the
forecast was. It stays in the table because leaving it out invites someone to ask for
it; it never decides a verdict.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..intervals import BUCKET_LABELS, bucket_of

BUCKET_ALL = "all"
REPORT_BUCKETS: tuple[str, ...] = (BUCKET_ALL, *BUCKET_LABELS)

PINBALL_QUANTILES: tuple[float, ...] = (0.1, 0.5, 0.9)
COVERAGE_LEVEL = 0.80
# sMAPE needs both sides to be non-trivial; a closed venue is not a forecasting failure.
SMAPE_MIN_DENOMINATOR = 1.0
ROUND_DIGITS = 3


@dataclass(frozen=True)
class Score:
    """Every metric of one model, in one weather mode, in one horizon bucket."""

    model: str
    weather_mode: str
    bucket: str
    n: int
    mae: float
    rmse: float
    mase: float
    bias: float
    bias_pct: float
    pinball: dict[str, float]
    coverage_80: float
    smape: float
    smape_reliable: bool
    zero_days: int
    mean_actual: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``metrics.json``."""
        return {
            "model": self.model,
            "weather_mode": self.weather_mode,
            "bucket": self.bucket,
            "n": self.n,
            "mae": _round(self.mae),
            "rmse": _round(self.rmse),
            "mase": _round(self.mase),
            "bias": _round(self.bias),
            "bias_pct": _round(self.bias_pct),
            "pinball": {key: _round(value) for key, value in self.pinball.items()},
            "coverage_80": _round(self.coverage_80, 4),
            "smape": _round(self.smape),
            "smape_reliable": self.smape_reliable,
            "zero_days": self.zero_days,
            "mean_actual": _round(self.mean_actual),
        }


@dataclass
class ScoreTable:
    """Every score of one window, addressable by (weather mode, model, bucket)."""

    scores: dict[tuple[str, str, str], Score] = field(default_factory=dict)

    def add(self, score: Score) -> None:
        """Store one score."""
        self.scores[score.weather_mode, score.model, score.bucket] = score

    def get(self, weather_mode: str, model: str, bucket: str = BUCKET_ALL) -> Score | None:
        """One score, or ``None`` when that combination was not measured."""
        return self.scores.get((weather_mode, model, bucket))

    def mae_by_model(self, weather_mode: str, bucket: str = BUCKET_ALL) -> dict[str, float]:
        """MAE of every model in one weather mode, for picking the best reference."""
        return {
            model: score.mae
            for (mode, model, key), score in self.scores.items()
            if mode == weather_mode and key == bucket
        }

    def models(self, weather_mode: str) -> list[str]:
        """Every model measured in one weather mode, in insertion order."""
        seen: list[str] = []
        for mode, model, _ in self.scores:
            if mode == weather_mode and model not in seen:
                seen.append(model)
        return seen

    def to_list(self) -> list[dict[str, Any]]:
        """Flatten for ``metrics.json``, in a stable order."""
        return [score.to_dict() for score in self.scores.values()]


def score_window(predictions: pd.DataFrame, mase_denominator: float) -> ScoreTable:
    """Score every (weather mode, model, bucket) combination of one window."""
    table = ScoreTable()
    frame = predictions.assign(
        bucket=[bucket_of(int(value)) for value in predictions["horizon_days"]]
    )
    for weather_mode in _unique(frame["weather_mode"]):
        for model in _unique(frame.loc[frame["weather_mode"] == weather_mode, "model"]):
            selected = frame.loc[
                (frame["weather_mode"] == weather_mode) & (frame["model"] == model)
            ]
            for bucket in REPORT_BUCKETS:
                rows = selected if bucket == BUCKET_ALL else selected.loc[selected["bucket"] == bucket]
                if rows.empty:
                    continue
                table.add(_score_rows(rows, model, weather_mode, bucket, mase_denominator))
    return table


def _score_rows(
    rows: pd.DataFrame, model: str, weather_mode: str, bucket: str, mase_denominator: float
) -> Score:
    """Every metric for one group of scored days."""
    y_true = _floats(rows["y_true"])
    p50 = _floats(rows["p50"])
    p10 = _floats(rows["p10"])
    p90 = _floats(rows["p90"])
    error = p50 - y_true
    absolute = np.abs(error)
    mae = float(absolute.mean())
    mean_actual = float(y_true.mean())
    zero_days = int((y_true == 0.0).sum())
    inside = (y_true >= p10) & (y_true <= p90)
    valid_band = np.isfinite(p10) & np.isfinite(p90)
    return Score(
        model=model,
        weather_mode=weather_mode,
        bucket=bucket,
        n=len(rows),
        mae=mae,
        rmse=float(np.sqrt(float((error**2).mean()))),
        mase=_mase(mae, mase_denominator),
        bias=float(error.mean()),
        bias_pct=float(error.mean()) / mean_actual * 100.0 if mean_actual > 0 else float("nan"),
        pinball={
            f"q{round(quantile * 100):02.0f}": pinball_loss(
                y_true, _quantile_series(quantile, p10, p50, p90), quantile
            )
            for quantile in PINBALL_QUANTILES
        },
        coverage_80=float(inside[valid_band].mean()) if bool(valid_band.any()) else float("nan"),
        smape=smape(y_true, p50),
        smape_reliable=zero_days == 0,
        zero_days=zero_days,
        mean_actual=mean_actual,
    )


def _mase(mae: float, denominator: float) -> float:
    """MAE divided by the training window's own seasonal naive MAE."""
    if not np.isfinite(denominator) or denominator <= 0.0:
        return float("nan")
    return mae / denominator


def _quantile_series(
    quantile: float, p10: np.ndarray, p50: np.ndarray, p90: np.ndarray
) -> np.ndarray:
    """Which forecast column a pinball quantile is scored against."""
    if quantile < 0.5:
        return p10
    if quantile > 0.5:
        return p90
    return p50


def pinball_loss(y_true: np.ndarray, forecast: np.ndarray, quantile: float) -> float:
    """Mean pinball loss, the proper score for one quantile forecast.

    Under-forecasting costs ``q`` per visitor and over-forecasting ``1-q``, so the loss
    is minimised by the true quantile and by nothing else. That is what makes it
    impossible to improve a p90 by simply raising it.
    """
    usable = np.isfinite(forecast) & np.isfinite(y_true)
    if not bool(usable.any()):
        return float("nan")
    difference = y_true[usable] - forecast[usable]
    loss = np.where(difference >= 0.0, quantile * difference, (quantile - 1.0) * difference)
    return float(loss.mean())


def smape(y_true: np.ndarray, forecast: np.ndarray) -> float:
    """Symmetric MAPE in percent, skipping days where both sides are near zero."""
    denominator = (np.abs(y_true) + np.abs(forecast)) / 2.0
    usable = denominator >= SMAPE_MIN_DENOMINATOR
    if not bool(usable.any()):
        return float("nan")
    ratio = np.abs(forecast[usable] - y_true[usable]) / denominator[usable]
    return float(ratio.mean() * 100.0)


def absolute_errors(predictions: pd.DataFrame, weather_mode: str, model: str) -> np.ndarray:
    """One model's absolute daily errors, ordered by date.

    Order matters: the block bootstrap in :mod:`.significance` resamples runs of
    consecutive days, and a shuffled series would destroy the weekly autocorrelation it
    exists to preserve.
    """
    rows = _model_rows(predictions, weather_mode, model)
    return np.asarray(np.abs(_floats(rows["p50"]) - _floats(rows["y_true"])), dtype="float64")


def signed_errors(predictions: pd.DataFrame, weather_mode: str, model: str) -> np.ndarray:
    """One model's signed daily errors (forecast minus actual), ordered by date."""
    rows = _model_rows(predictions, weather_mode, model)
    return np.asarray(_floats(rows["p50"]) - _floats(rows["y_true"]), dtype="float64")


def coverage_counts(predictions: pd.DataFrame, weather_mode: str, model: str) -> tuple[int, int]:
    """How many actuals fell inside p10-p90, and how many days had a usable band."""
    rows = _model_rows(predictions, weather_mode, model)
    y_true, p10, p90 = _floats(rows["y_true"]), _floats(rows["p10"]), _floats(rows["p90"])
    valid = np.isfinite(p10) & np.isfinite(p90)
    inside = (y_true >= p10) & (y_true <= p90) & valid
    return int(inside.sum()), int(valid.sum())


def worst_days(
    predictions: pd.DataFrame, weather_mode: str, model: str, limit: int = 5
) -> pd.DataFrame:
    """The days this model got most wrong, largest absolute error first."""
    rows = _model_rows(predictions, weather_mode, model).copy()
    rows["error"] = _floats(rows["p50"]) - _floats(rows["y_true"])
    rows["abs_error"] = rows["error"].abs()
    return rows.sort_values("abs_error", ascending=False).head(limit).reset_index(drop=True)


def _model_rows(predictions: pd.DataFrame, weather_mode: str, model: str) -> pd.DataFrame:
    """One model's rows in one weather mode, sorted by date."""
    rows = predictions.loc[
        (predictions["weather_mode"] == weather_mode) & (predictions["model"] == model)
    ]
    return rows.sort_values("date")


def _unique(values: pd.Series) -> list[str]:
    """Distinct values in first-seen order, so output ordering is stable."""
    return list(dict.fromkeys(str(value) for value in values))


def _floats(values: pd.Series) -> np.ndarray:
    """One column as a float array."""
    return np.asarray(
        pd.to_numeric(values, errors="coerce").astype("float64").to_numpy(), dtype="float64"
    )


def _round(value: float, digits: int = ROUND_DIGITS) -> float:
    """Round for the metrics file, keeping NaN as NaN."""
    if value is None or not np.isfinite(value):
        return float("nan")
    return float(round(float(value), digits))
