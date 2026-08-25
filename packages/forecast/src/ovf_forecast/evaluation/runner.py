"""Running one window: train at the origin, forecast the test period, fetch the truth.

This module is where the leak rules are enforced, so it is worth stating them in one
place. For a window with origin *o*:

1. Models see only rows dated ``<= o``.
2. The level features (``level_7d``, ``level_28d``, ``dow_index_28d``) are computed once
   at *o* and held constant across the whole test period.
3. The MASE denominator comes from the training window alone.
4. The prediction interval quantiles come from a nested backtest that runs entirely
   inside the training window: its last inner origin is ``o - horizon``, so no inner
   forecast ever reaches past *o*. This is the rule that is easy to get wrong. A
   production run fits its bands on the most recent data available, which in an
   evaluation would be the test period itself, and coverage measured that way is
   meaningless.
5. Calendar facts — weekdays, public holidays — are allowed, because they are known in
   advance.
6. Ticket data is never a feature, because the future does not have any.

Weather gets three modes rather than one. Production has a weather *forecast*; scoring
against the weather that actually happened flatters the model, and scoring against
climatology alone punishes it for something a forecast would have told it. Running all
three brackets the truth, and the gap between ``perfect`` and ``climatology`` is itself
the answer to "how much of this model's accuracy is really weather knowledge".

The evaluation reads the venue series untrimmed, leading zero days included. Production
drops them, but here the training window is whatever the caller named, and silently
moving its left edge would make ``--train-window all`` mean something other than what it
says. Where those days land inside a window the run says so and the report repeats it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import numpy as np
import pandas as pd

from .. import log_event
from ..dataset import (
    MAX_WEATHER_FORECAST_DAYS,
    WEATHER_SOURCE_CLIMATOLOGY,
    ProcessedData,
    Venue,
    venue_future,
    venue_history,
)
from ..features import TARGET, build_future_frame, build_training_frame
from ..intervals import Band, apply_bands, fit_bands
from ..models.base import BENCHMARK_NAMES, MODEL_NAMES, ForecastModel, resolve_models
from .baselines import BASELINE_NAMES, mase_denominator, predict_all
from .baselines import leading_zero_days as count_leading_zero_days
from .significance import N_RESAMPLES, RANDOM_SEED
from .totals import relative_errors
from .windows import TRAIN_WINDOW_ALL, Window

WEATHER_PERFECT = "perfect"
WEATHER_OPERATIONAL = "operational"
WEATHER_CLIMATOLOGY = "climatology"
WEATHER_MODES: tuple[str, ...] = (WEATHER_PERFECT, WEATHER_OPERATIONAL, WEATHER_CLIMATOLOGY)
DEFAULT_WEATHER_MODE = WEATHER_OPERATIONAL

# The nested backtest steps back a week at a time from ``origin - horizon``.
NESTED_STEP_DAYS = 7
NESTED_MAX_ORIGINS = 12
# Lower than the production backtest's 60. The nested run has to fit entirely inside a
# training window that may itself be only three months long, and a band from three thin
# origins is still better evidence than the hard-coded default band.
NESTED_MIN_TRAINING_DAYS = 45

PREDICTION_COLUMNS = [
    "venue_id",
    "date",
    "horizon_days",
    "model",
    "weather_mode",
    "y_true",
    "p10",
    "p50",
    "p90",
]


@dataclass(frozen=True)
class EvaluationConfig:
    """Everything about a run that is not the window itself."""

    models: tuple[str, ...] = MODEL_NAMES
    weather_modes: tuple[str, ...] = WEATHER_MODES
    primary_weather_mode: str = DEFAULT_WEATHER_MODE
    reference: str = "best"
    venues: tuple[int, ...] | None = None
    train_window: str = TRAIN_WINDOW_ALL
    n_resamples: int = N_RESAMPLES
    seed: int = RANDOM_SEED
    nested_step_days: int = NESTED_STEP_DAYS
    nested_max_origins: int = NESTED_MAX_ORIGINS
    nested_min_training_days: int = NESTED_MIN_TRAINING_DAYS

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``config.json``."""
        return {
            "models": list(self.models),
            "baselines": list(BASELINE_NAMES),
            "weather_modes": list(self.weather_modes),
            "primary_weather_mode": self.primary_weather_mode,
            "reference": self.reference,
            "venues": list(self.venues) if self.venues else None,
            "train_window": self.train_window,
            "n_resamples": self.n_resamples,
            "seed": self.seed,
            "nested_backtest": {
                "step_days": self.nested_step_days,
                "max_origins": self.nested_max_origins,
                "min_training_days": self.nested_min_training_days,
            },
        }


@dataclass
class VenueWindowRun:
    """One venue's result for one window: predictions, and what produced them."""

    venue_id: int
    venue_name: str
    window: Window
    predictions: pd.DataFrame
    mase_denominator: float
    ratios: dict[tuple[str, str], np.ndarray] = field(default_factory=dict)
    nested_origins: int = 0
    training_days: int = 0
    training_start: date | None = None
    training_zero_days: int = 0
    leading_zero_days: int = 0
    missing_test_days: list[str] = field(default_factory=list)
    weather_days: dict[str, dict[str, int]] = field(default_factory=dict)
    default_bands: list[str] = field(default_factory=list)
    context: pd.DataFrame = field(default_factory=pd.DataFrame)

    def diagnostics(self) -> dict[str, Any]:
        """The provenance a reader needs before believing the numbers."""
        return {
            "venue_id": self.venue_id,
            "venue_name": self.venue_name,
            "training_start": self.training_start.isoformat() if self.training_start else None,
            "training_days": self.training_days,
            "training_zero_days": self.training_zero_days,
            "leading_zero_days": self.leading_zero_days,
            "mase_denominator": round(self.mase_denominator, 4)
            if np.isfinite(self.mase_denominator)
            else None,
            "nested_origins": self.nested_origins,
            "missing_test_days": self.missing_test_days,
            "weather_days": self.weather_days,
            "default_bands": self.default_bands,
        }


def evaluation_history(data: ProcessedData, venue_id: int) -> pd.DataFrame:
    """The venue's daily series with covariates, leading zero days kept."""
    return venue_history(data, venue_id, trim_leading_zeros=False)


def max_forecast_days(mode: str, horizon_days: int) -> int:
    """How many of a window's days may use observed weather, per mode.

    ``perfect`` gets the whole period, ``operational`` gets the 16 days Open-Meteo
    actually forecasts and climatology after that, ``climatology`` gets none.
    """
    if mode == WEATHER_PERFECT:
        return horizon_days
    if mode == WEATHER_OPERATIONAL:
        return MAX_WEATHER_FORECAST_DAYS
    if mode == WEATHER_CLIMATOLOGY:
        return 0
    raise KeyError(f"Unknown weather mode: {mode}. Known modes: {', '.join(WEATHER_MODES)}")


def resolve_weather_modes(requested: tuple[str, ...] | None) -> tuple[str, ...]:
    """Validate the requested weather modes, defaulting to all three."""
    if not requested:
        return WEATHER_MODES
    unknown = [mode for mode in requested if mode not in WEATHER_MODES]
    if unknown:
        raise KeyError(
            f"Unknown weather mode(s): {', '.join(unknown)}. Known modes: {', '.join(WEATHER_MODES)}"
        )
    return tuple(dict.fromkeys(requested))


def run_window(
    data: ProcessedData,
    venue: Venue,
    window: Window,
    config: EvaluationConfig,
) -> VenueWindowRun | None:
    """Train at the origin, forecast the test period in every weather mode, score it."""
    history = evaluation_history(data, venue.venue_id)
    if history.empty:
        log_event("error", "evaluation", "No observed history", venue_id=venue.venue_id)
        return None
    history_start = pd.Timestamp(history["date"].min()).date()
    history_end = pd.Timestamp(history["date"].max()).date()
    if window.origin < history_start or window.origin > history_end:
        log_event(
            "error",
            "evaluation",
            "Origin is outside the observed history",
            venue_id=venue.venue_id,
            origin=window.origin.isoformat(),
            history=[history_start.isoformat(), history_end.isoformat()],
        )
        return None

    training_start = window.train_start(history_start)
    train_history = history.loc[history["date"] >= pd.Timestamp(training_start)]
    training = build_training_frame(train_history, window.origin)
    if training.empty:
        log_event("error", "evaluation", "Empty training window", venue_id=venue.venue_id)
        return None

    actuals = _actuals(history)
    test_dates = [day for day in window.test_dates() if pd.Timestamp(day) in actuals.index]
    missing = [
        day.isoformat() for day in window.test_dates() if pd.Timestamp(day) not in actuals.index
    ]
    if not test_dates:
        log_event(
            "error",
            "evaluation",
            "No observed day in the test period",
            venue_id=venue.venue_id,
            window=window.label,
        )
        return None

    nested = run_nested_backtest(data, venue.venue_id, history, window, config)
    records: list[dict[str, Any]] = []
    ratios: dict[tuple[str, str], np.ndarray] = {}
    weather_days: dict[str, dict[str, int]] = {}
    default_bands: list[str] = []
    context = pd.DataFrame()

    models = _fit_models(config.models, training)
    baseline_forecasts = predict_all(training, window.origin, test_dates)
    # What the weather actually did, whatever the model was given. The worst-days table
    # is meant to explain a miss, and "6 mm of rain" has to mean the rain that fell.
    observed = venue_future(
        data, venue.venue_id, window.origin, window.horizon_days, max_forecast_days=window.horizon_days
    )

    for mode in config.weather_modes:
        bands = _bands_for_mode(nested, mode)
        covariates = venue_future(
            data,
            venue.venue_id,
            window.origin,
            window.horizon_days,
            max_forecast_days=max_forecast_days(mode, window.horizon_days),
        )
        future = build_future_frame(train_history, covariates, window.origin)
        weather_days[mode] = _weather_day_counts(covariates)
        if mode == config.primary_weather_mode or context.empty:
            context = _day_context(covariates, observed)
        forecasts: dict[str, pd.Series] = {
            name: model.predict(future) for name, model in models.items()
        }
        scored = future["date"].isin([pd.Timestamp(day) for day in test_dates])
        for name, values in forecasts.items():
            p10, p90 = apply_bands(values, future["horizon_days"], bands, name)
            records.extend(
                _rows(venue.venue_id, future, scored, name, mode, values, p10, p90, actuals)
            )
        for name, array in baseline_forecasts.items():
            series = pd.Series(array, index=range(len(test_dates)), dtype="float64")
            horizons = pd.Series(
                [(day - window.origin).days for day in test_dates], index=series.index
            )
            p10, p90 = apply_bands(series, horizons, bands, name)
            records.extend(
                _baseline_rows(venue.venue_id, test_dates, window, name, mode, series, p10, p90, actuals)
            )
        for name in (*models, *BASELINE_NAMES):
            ratios[mode, name] = _nested_ratios(nested, mode, name)
        default_bands.extend(
            f"{mode}/{name}" for (name, _), band in bands.items() if band.is_default
        )

    predictions = pd.DataFrame.from_records(records, columns=PREDICTION_COLUMNS)
    predictions = predictions.sort_values(["weather_mode", "model", "date"]).reset_index(drop=True)
    target = pd.to_numeric(training[TARGET], errors="coerce")
    return VenueWindowRun(
        venue_id=venue.venue_id,
        venue_name=venue.name,
        window=window,
        predictions=predictions,
        mase_denominator=mase_denominator(training),
        ratios=ratios,
        nested_origins=int(nested["origin_date"].nunique()) if not nested.empty else 0,
        training_days=len(training),
        training_start=training_start,
        training_zero_days=int((target == 0.0).sum()),
        leading_zero_days=count_leading_zero_days(training),
        missing_test_days=missing,
        weather_days=weather_days,
        default_bands=sorted(set(default_bands)),
        context=context,
    )


# --------------------------------------------------------------------------------------
# The nested backtest that calibrates the intervals
# --------------------------------------------------------------------------------------


def nested_origins(window: Window, history_start: date, config: EvaluationConfig) -> list[date]:
    """Inner origins, newest first, none of which can forecast past the outer origin.

    The newest is ``origin - horizon``: one full horizon before the outer origin, so its
    last forecast day lands exactly on the origin and never a day later.
    """
    origins: list[date] = []
    cursor = window.origin - timedelta(days=window.horizon_days)
    while len(origins) < config.nested_max_origins:
        if window.train_window == TRAIN_WINDOW_ALL:
            training_days = (cursor - history_start).days + 1
        else:
            training_days = min((cursor - history_start).days + 1, int(window.train_window))
        if training_days < config.nested_min_training_days:
            break
        origins.append(cursor)
        cursor -= timedelta(days=config.nested_step_days)
    return origins


def run_nested_backtest(
    data: ProcessedData,
    venue_id: int,
    history: pd.DataFrame,
    window: Window,
    config: EvaluationConfig,
) -> pd.DataFrame:
    """Rolling origin backtest confined to the training window, one row per prediction.

    Each inner origin refits every model on its own training slice and forecasts the
    same horizon as the outer window, in every weather mode. The models are fitted once
    per origin and predicted three times, because the training data does not depend on
    which weather the forecast days are given.
    """
    columns = ["model", "weather_mode", "origin_date", "target_date", "horizon_days", "y_true", "y_pred"]
    history_start = pd.Timestamp(history["date"].min()).date()
    origins = nested_origins(window, history_start, config)
    if not origins:
        log_event(
            "warning",
            "evaluation",
            "No nested backtest origin fits inside the training window; intervals fall back to defaults",
            venue_id=venue_id,
            window=window.label,
            min_training_days=config.nested_min_training_days,
        )
        return pd.DataFrame(columns=columns)

    actuals = _actuals(history)
    records: list[dict[str, Any]] = []
    for origin in origins:
        inner = Window(
            origin=origin,
            test_start=origin + timedelta(days=1),
            test_end=origin + timedelta(days=window.horizon_days),
            train_window=window.train_window,
        )
        inner_start = inner.train_start(history_start)
        inner_history = history.loc[history["date"] >= pd.Timestamp(inner_start)]
        training = build_training_frame(inner_history, origin)
        if training.empty:
            continue
        inner_dates = [day for day in inner.test_dates() if pd.Timestamp(day) in actuals.index]
        if not inner_dates:
            continue
        models = _fit_models(config.models, training)
        baseline_forecasts = predict_all(training, origin, inner_dates)
        for mode in config.weather_modes:
            covariates = venue_future(
                data,
                venue_id,
                origin,
                window.horizon_days,
                max_forecast_days=max_forecast_days(mode, window.horizon_days),
            )
            future = build_future_frame(inner_history, covariates, origin)
            wanted = {pd.Timestamp(day) for day in inner_dates}
            for name, model in models.items():
                values = model.predict(future).to_numpy()
                for position, stamp in enumerate(future["date"]):
                    if pd.Timestamp(stamp) not in wanted:
                        continue
                    records.append(
                        _nested_record(
                            name,
                            mode,
                            origin,
                            pd.Timestamp(stamp),
                            int(future["horizon_days"].iloc[position]),
                            float(actuals.loc[pd.Timestamp(stamp)]),
                            float(values[position]),
                        )
                    )
            for name, array in baseline_forecasts.items():
                for position, day in enumerate(inner_dates):
                    records.append(
                        _nested_record(
                            name,
                            mode,
                            origin,
                            pd.Timestamp(day),
                            (day - origin).days,
                            float(actuals.loc[pd.Timestamp(day)]),
                            float(array[position]),
                        )
                    )
    if not records:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame.from_records(records, columns=columns)


def _nested_record(
    model: str,
    weather_mode: str,
    origin: date,
    target: pd.Timestamp,
    horizon: int,
    y_true: float,
    y_pred: float,
) -> dict[str, Any]:
    """One row of the nested backtest."""
    return {
        "model": model,
        "weather_mode": weather_mode,
        "origin_date": origin.isoformat(),
        "target_date": target.date().isoformat(),
        "horizon_days": horizon,
        "y_true": y_true,
        "y_pred": y_pred,
    }


def _bands_for_mode(nested: pd.DataFrame, mode: str) -> dict[tuple[str, str], Band]:
    """Interval bands fitted on the nested backtest rows of one weather mode."""
    if nested.empty:
        return {}
    return fit_bands(nested.loc[nested["weather_mode"] == mode])


def _nested_ratios(nested: pd.DataFrame, mode: str, model: str) -> np.ndarray:
    """The relative daily errors the period total simulation resamples.

    Ordered by inner origin and then by horizon, so a block of consecutive rows is a run
    of consecutive forecast days from one origin and carries their correlation with it.
    """
    if nested.empty:
        return np.zeros(0, dtype="float64")
    rows = nested.loc[(nested["weather_mode"] == mode) & (nested["model"] == model)]
    if rows.empty:
        return np.zeros(0, dtype="float64")
    rows = rows.sort_values(["origin_date", "horizon_days"])
    return relative_errors(rows["y_true"].to_numpy(), rows["y_pred"].to_numpy())


# --------------------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------------------


def _fit_models(names: tuple[str, ...], training: pd.DataFrame) -> dict[str, ForecastModel]:
    """Fit every requested model on one training frame."""
    models, skipped = resolve_models(tuple(name for name in names if name not in BENCHMARK_NAMES))
    for name in skipped:
        log_event("warning", "evaluation", "Model skipped, its extras are not installed", model=name)
    fitted: dict[str, ForecastModel] = {}
    for model in models:
        model.fit(training)
        fitted[model.name] = model
    return fitted


def _actuals(history: pd.DataFrame) -> pd.Series:
    """The observed target indexed by day."""
    values = pd.to_numeric(history[TARGET], errors="coerce").astype("float64")
    return pd.Series(values.to_numpy(), index=pd.DatetimeIndex(history["date"])).dropna()


def _rows(
    venue_id: int,
    future: pd.DataFrame,
    scored: pd.Series,
    model: str,
    mode: str,
    p50: pd.Series,
    p10: pd.Series,
    p90: pd.Series,
    actuals: pd.Series,
) -> list[dict[str, Any]]:
    """Prediction rows for one model in one weather mode."""
    rows: list[dict[str, Any]] = []
    for position in np.flatnonzero(scored.to_numpy()):
        stamp = pd.Timestamp(future["date"].iloc[position])
        rows.append(
            {
                "venue_id": venue_id,
                "date": stamp.date().isoformat(),
                "horizon_days": int(future["horizon_days"].iloc[position]),
                "model": model,
                "weather_mode": mode,
                "y_true": float(actuals.loc[stamp]),
                "p10": float(p10.iloc[position]),
                "p50": float(p50.iloc[position]),
                "p90": float(p90.iloc[position]),
            }
        )
    return rows


def _baseline_rows(
    venue_id: int,
    test_dates: list[date],
    window: Window,
    model: str,
    mode: str,
    p50: pd.Series,
    p10: pd.Series,
    p90: pd.Series,
    actuals: pd.Series,
) -> list[dict[str, Any]]:
    """Prediction rows for one baseline. Its p50 does not vary with the weather mode."""
    return [
        {
            "venue_id": venue_id,
            "date": day.isoformat(),
            "horizon_days": (day - window.origin).days,
            "model": model,
            "weather_mode": mode,
            "y_true": float(actuals.loc[pd.Timestamp(day)]),
            "p10": float(p10.iloc[position]),
            "p50": float(p50.iloc[position]),
            "p90": float(p90.iloc[position]),
        }
        for position, day in enumerate(test_dates)
    ]


def _weather_day_counts(covariates: pd.DataFrame) -> dict[str, int]:
    """How many forecast days took observed weather and how many took climatology."""
    climatology = int((covariates["weather_source"] == WEATHER_SOURCE_CLIMATOLOGY).sum())
    return {"observed": len(covariates) - climatology, "climatology": climatology}


CONTEXT_COLUMNS = (
    "holiday_name",
    "is_holiday",
    "day_of_week",
    "temp_mean",
    "precip_sum",
    "wind_mean",
    "weathercode_str",
)


def _day_context(covariates: pd.DataFrame, observed: pd.DataFrame) -> pd.DataFrame:
    """What was going on each forecast day, for annotating the worst misses.

    The report's most useful section is the five days the model got most wrong, and a
    date on its own says nothing. A holiday name and the day's weather turn "off by 400"
    into "off by 400, and it was Good Friday", which is a sentence somebody can act on.

    The weather here is the weather that *happened*, taken from ``observed``, not the
    weather the model was fed. Past day 16 the model sees climatology, and reporting a
    ten-year average as though it were that day's rain would explain nothing. What the
    model was given is kept separately in ``model_weather_source``, because "it rained
    8 mm and the model was looking at climatology" is two facts, not one.
    """
    frame = pd.DataFrame({"date": [pd.Timestamp(day).date().isoformat() for day in observed["date"]]})
    for column in CONTEXT_COLUMNS:
        frame[column] = observed[column].to_numpy() if column in observed.columns else None
    frame["model_weather_source"] = (
        covariates["weather_source"].to_numpy()
        if "weather_source" in covariates.columns
        else None
    )
    return frame
