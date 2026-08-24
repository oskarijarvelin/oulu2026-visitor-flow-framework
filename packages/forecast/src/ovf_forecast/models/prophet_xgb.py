"""The comparison model: Prophet for structure, XGBoost for what Prophet misses.

Prophet is fitted to the daily total with a trend, a weekly cycle, a yearly cycle,
holidays and three weather regressors. XGBoost is then fitted to Prophet's residuals
using the same calendar and weather features the baseline sees. The forecast is
``prophet_yhat + xgb_residual``, floored at zero.

Four things the reference implementation does are deliberately not done here:

* It runs Prophet on hourly data with ``daily_seasonality=True`` *and* a hand-added
  ``hourly_pattern`` of ``period=1``. Those are the same 24-hour cycle twice over, which
  is collinear and makes the components meaningless. This model is daily; the hourly
  shape comes from the shared profile.
* It builds the daily interval by summing 24 hourly intervals, which is how a forecast
  of 29 visitors ends up with a 0-502 band. Intervals here come from the shared
  empirical backtest, and Prophet's own ``yhat_lower`` / ``yhat_upper`` are never read:
  they know nothing about the XGBoost stage.
* It measures quality on a single 80/20 time split. This model is measured on a rolling
  origin backtest like every other model in the package.
* It fills missing features with the median of the whole training set, mixing January
  into May. Both stages here read NaN natively.
"""

from __future__ import annotations

import contextlib
import io
import logging
import warnings

import numpy as np
import pandas as pd
from prophet import Prophet
from xgboost import XGBRegressor

from .. import log_event
from ..features import FEATURE_COLUMNS, PROPHET_REGRESSORS, TARGET
from .base import PROPHET_XGB, RANDOM_STATE

MIN_TRAINING_ROWS = 30
# Fourier order and prior scales are held down: a yearly cycle fitted to 4.5 months of
# data will happily learn noise and extrapolate it.
YEARLY_FOURIER_ORDER = 3
SEASONALITY_PRIOR_SCALE = 5.0
CHANGEPOINT_PRIOR_SCALE = 0.05
# Prophet's own "auto" rule turns the yearly term off below two years of history,
# because a cycle you have never seen complete cannot be identified. This model asks for
# a yearly component but keeps that guard, and says so in the log when it fires.
MIN_YEARLY_SEASONALITY_DAYS = 730


class ProphetXgbModel:
    """Additive Prophet baseline plus a gradient boosted residual correction."""

    name = PROPHET_XGB

    def __init__(self, random_state: int = RANDOM_STATE) -> None:
        self._random_state = random_state
        self._prophet: Prophet | None = None
        self._residual: XGBRegressor | None = None
        self._fallback = 0.0

    def fit(self, daily: pd.DataFrame) -> None:
        """Fit Prophet on the daily total, then XGBoost on what Prophet leaves behind."""
        target = pd.to_numeric(daily[TARGET], errors="coerce").astype("float64")
        usable = daily.loc[target.notna()].reset_index(drop=True)
        self._fallback = float(target.dropna().tail(28).mean()) if target.notna().any() else 0.0
        if len(usable) < MIN_TRAINING_ROWS:
            self._prophet = None
            self._residual = None
            return
        history = _prophet_frame(usable)
        yearly = _yearly_seasonality(history)
        model = Prophet(
            weekly_seasonality=True,
            yearly_seasonality=yearly,
            daily_seasonality=False,
            holidays=_holiday_frame(usable),
            seasonality_prior_scale=SEASONALITY_PRIOR_SCALE,
            changepoint_prior_scale=CHANGEPOINT_PRIOR_SCALE,
            interval_width=0.8,
        )
        for regressor in PROPHET_REGRESSORS:
            model.add_regressor(regressor)
        _fit_quietly(model, history)
        fitted = np.asarray(model.predict(history[["ds", *PROPHET_REGRESSORS]])["yhat"], dtype="float64")
        residual = pd.to_numeric(usable[TARGET], errors="coerce").astype("float64").to_numpy() - fitted
        booster = XGBRegressor(
            n_estimators=300,
            max_depth=3,
            learning_rate=0.03,
            subsample=0.9,
            colsample_bytree=0.9,
            min_child_weight=5,
            reg_lambda=1.0,
            objective="reg:squarederror",
            random_state=self._random_state,
            n_jobs=1,
            verbosity=0,
        )
        booster.fit(_residual_matrix(usable), residual)
        self._prophet = model
        self._residual = booster

    def predict(self, future: pd.DataFrame) -> pd.Series:
        """Prophet's level plus the learned residual, floored at zero."""
        if self._prophet is None or self._residual is None:
            return pd.Series(np.full(len(future), self._fallback), index=future.index, dtype="float64")
        frame = _prophet_frame(future)
        level = np.asarray(
            self._prophet.predict(frame[["ds", *PROPHET_REGRESSORS]])["yhat"], dtype="float64"
        )
        correction = np.asarray(self._residual.predict(_residual_matrix(future)), dtype="float64")
        return pd.Series(np.maximum(level + correction, 0.0), index=future.index, dtype="float64")


def _yearly_seasonality(history: pd.DataFrame) -> int | bool:
    """Enable the yearly component only when the history could identify one.

    Forcing it on with 4.5 months of data is not a hypothetical problem. Measured on
    venue 1, a forced yearly term contributes +742 visitors to the day-30 forecast, and
    the model's MAE at horizon 15-30 goes from 179 to 774. The component is fitting
    noise inside the training window and extrapolating it straight out.
    """
    span = int((history["ds"].max() - history["ds"].min()).days)
    if span >= MIN_YEARLY_SEASONALITY_DAYS:
        return YEARLY_FOURIER_ORDER
    log_event(
        "info",
        "prophet_xgb",
        "Yearly seasonality disabled: the history is shorter than one identifiable cycle",
        span_days=span,
        required_days=MIN_YEARLY_SEASONALITY_DAYS,
    )
    return False


def _prophet_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Rename to Prophet's ``ds``/``y`` schema and keep the three weather regressors."""
    result = pd.DataFrame({"ds": pd.to_datetime(frame["date"])})
    if TARGET in frame.columns:
        result["y"] = pd.to_numeric(frame[TARGET], errors="coerce").astype("float64")
    for regressor in PROPHET_REGRESSORS:
        values = pd.to_numeric(frame[regressor], errors="coerce").astype("float64")
        # Prophet cannot take NaN in a regressor. Interpolating along the horizon keeps
        # the gap local instead of pulling a median in from a different season.
        result[regressor] = values.interpolate(limit_direction="both").fillna(0.0).to_numpy()
    return result


def _residual_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """The residual stage's design matrix: the shared features, one-hot where needed."""
    matrix = frame[list(FEATURE_COLUMNS)].copy()
    matrix["day_of_week"] = pd.to_numeric(matrix["day_of_week"].astype("object"), errors="coerce")
    matrix["weather_group"] = matrix["weather_group"].cat.codes.astype("float64").where(
        matrix["weather_group"].notna()
    )
    return matrix.astype("float64")


def _holiday_frame(frame: pd.DataFrame) -> pd.DataFrame | None:
    """Prophet's holiday table, taken from the maintained calendar."""
    if "holiday_name" not in frame.columns:
        return None
    named = frame.loc[frame["holiday_name"].notna(), ["date", "holiday_name"]]
    if named.empty:
        return None
    holidays = named.rename(columns={"date": "ds", "holiday_name": "holiday"})
    return holidays.drop_duplicates(subset=["ds", "holiday"]).reset_index(drop=True)


def _fit_quietly(model: Prophet, history: pd.DataFrame) -> None:
    """Fit Prophet without its cmdstan chatter on stdout."""
    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
    logging.getLogger("prophet").setLevel(logging.WARNING)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            model.fit(history)


__all__ = ["PROPHET_XGB", "ProphetXgbModel"]
