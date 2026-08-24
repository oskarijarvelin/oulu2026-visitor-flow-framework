"""Daily feature construction for both models.

Every feature here is a function of the calendar, the weather covariates, or of
observations *strictly before* the row it belongs to. Nothing is a function of a
prediction. That is the single design decision that separates this package from the
reference implementation, which feeds its own hourly output back into ``lag_24h`` and
``lag_168h`` and watches the error compound for thirty days.

The level features are the subtle case. In training they are causal rolling means: the
row for day t sees the seven days before t. At forecast time they are computed once at
the origin and held constant across the whole horizon, so the day-30 forecast is a
single forecast made from the origin, not thirty chained one-day forecasts. The price
is a level that cannot react to anything happening inside the horizon, which is a known
and documented weakness rather than a hidden one.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

import numpy as np
import pandas as pd

TARGET = "visitors_total"

CALENDAR_FEATURES = (
    "day_of_week",
    "is_weekend",
    "is_holiday",
    "days_before_next_holiday",
    "is_last_workday_before_holiday",
    "month",
    "week_of_year",
)
SEASONAL_FEATURES = ("year_sin", "year_cos", "half_year_sin", "half_year_cos")
TREND_FEATURES = ("days_since_start",)
WEATHER_FEATURES = (
    "temp_mean",
    "temp_max",
    "precip_sum",
    "precip_hours",
    "wind_mean",
    "is_rainy_day",
    "weather_group",
)
LEVEL_FEATURES = ("level_7d", "level_28d", "dow_index_28d")

FEATURE_COLUMNS: tuple[str, ...] = (
    *CALENDAR_FEATURES,
    *SEASONAL_FEATURES,
    *TREND_FEATURES,
    *WEATHER_FEATURES,
    *LEVEL_FEATURES,
)
CATEGORICAL_FEATURES = ("day_of_week", "weather_group")
# Prophet takes only the three continuous regressors; the rest is its own seasonality.
PROPHET_REGRESSORS = ("temp_mean", "precip_sum", "wind_mean")

DAYS_IN_YEAR = 365.0
HOLIDAY_HORIZON_DAYS = 14
LEVEL_SHORT_DAYS = 7
LEVEL_LONG_DAYS = 28
MIN_LEVEL_SHORT_DAYS = 3
MIN_LEVEL_LONG_DAYS = 7
DOW_OCCURRENCES = LEVEL_LONG_DAYS // 7


def build_training_frame(history: pd.DataFrame, origin: date) -> pd.DataFrame:
    """Feature matrix and target for every observed day up to and including ``origin``.

    The frame is reindexed onto a gap-free daily grid first, so the rolling windows mean
    "the last seven days" and not "the last seven rows that happen to exist".
    """
    observed = history.loc[history["date"] <= pd.Timestamp(origin)].copy()
    if observed.empty:
        return observed
    frame = _on_daily_grid(observed)
    frame = _add_calendar(frame)
    frame = _add_seasonal(frame)
    frame = _add_trend(frame, anchor=_anchor(history))
    frame = _add_causal_levels(frame)
    frame = _as_float_weather(frame)
    frame = frame.loc[frame[TARGET].notna()].reset_index(drop=True)
    return frame


def build_future_frame(history: pd.DataFrame, future: pd.DataFrame, origin: date) -> pd.DataFrame:
    """Feature matrix for the forecast days, with the level frozen at ``origin``.

    ``history`` is truncated at the origin before anything is read from it, so passing a
    longer history than the model was trained on cannot leak a future observation into a
    feature.
    """
    observed = history.loc[history["date"] <= pd.Timestamp(origin)]
    frame = future.copy()
    frame = _add_seasonal(frame)
    frame = _add_trend(frame, anchor=_anchor(history))
    levels = origin_levels(observed, origin)
    frame["level_7d"] = levels.level_7d
    frame["level_28d"] = levels.level_28d
    frame["dow_index_28d"] = [
        levels.dow_index.get(int(day_of_week), 1.0)
        for day_of_week in pd.to_numeric(frame["day_of_week"], errors="coerce")
    ]
    frame["days_before_next_holiday"] = _clip_holiday_distance(frame["days_before_next_holiday"])
    frame["day_of_week"] = pd.Categorical(frame["day_of_week"].astype("int64"), categories=range(7))
    for column in ("is_weekend", "is_holiday", "is_last_workday_before_holiday"):
        frame[column] = _as_float_flag(frame[column])
    for column in ("month", "week_of_year"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("float64")
    return _as_float_weather(frame).reset_index(drop=True)


@dataclass(frozen=True)
class OriginLevels:
    """The level features as they stand at one origin, held constant across the horizon."""

    level_7d: float
    level_28d: float
    dow_index: dict[int, float]


def origin_levels(observed: pd.DataFrame, origin: date) -> OriginLevels:
    """The level features as they stand at the origin: two means and a weekday index.

    ``dow_index`` is the mean of that weekday over the last 28 observed days divided by
    the mean of all 28. A weekday with no observation in the window falls back to 1.0,
    which is the same as saying "no weekday effect known".
    """
    stamp = pd.Timestamp(origin)
    window = observed.loc[
        (observed["date"] <= stamp) & (observed["date"] > stamp - pd.Timedelta(days=LEVEL_LONG_DAYS))
    ]
    short = observed.loc[
        (observed["date"] <= stamp) & (observed["date"] > stamp - pd.Timedelta(days=LEVEL_SHORT_DAYS))
    ]
    level_28d = float(window[TARGET].mean()) if not window.empty else float("nan")
    level_7d = float(short[TARGET].mean()) if not short.empty else float("nan")
    dow_index: dict[int, float] = {}
    if not window.empty and level_28d and np.isfinite(level_28d) and level_28d > 0:
        by_dow = window.groupby(window["date"].dt.dayofweek)[TARGET].mean()
        dow_index = {int(str(day)): float(value) / level_28d for day, value in by_dow.items()}
    return OriginLevels(level_7d=level_7d, level_28d=level_28d, dow_index=dow_index)


def model_matrix(frame: pd.DataFrame) -> pd.DataFrame:
    """The feature columns in a stable order, ready for scikit-learn or XGBoost."""
    return frame[list(FEATURE_COLUMNS)]


def _anchor(history: pd.DataFrame) -> pd.Timestamp:
    """First observed day, the origin of ``days_since_start``.

    Taken from the untruncated history so that the trend feature keeps the same zero
    point in training and in prediction, and across every backtest origin.
    """
    return pd.Timestamp(history["date"].min())


def _on_daily_grid(frame: pd.DataFrame) -> pd.DataFrame:
    """Reindex onto a complete daily range so rolling windows count days, not rows."""
    full = pd.date_range(frame["date"].min(), frame["date"].max(), freq="D")
    return frame.set_index("date").reindex(full).rename_axis("date").reset_index()


def _add_calendar(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize the calendar columns that arrive from ``calendar_daily.csv``."""
    result = frame.copy()
    day_of_week = pd.to_numeric(result["day_of_week"], errors="coerce")
    day_of_week = day_of_week.fillna(pd.Series(result["date"].dt.dayofweek, index=result.index))
    result["day_of_week"] = pd.Categorical(day_of_week.astype("int64"), categories=range(7))
    result["is_weekend"] = _as_float_flag(
        result["is_weekend"].where(result["is_weekend"].notna(), result["date"].dt.dayofweek >= 5)
    )
    result["is_holiday"] = _as_float_flag(result["is_holiday"])
    result["is_last_workday_before_holiday"] = _as_float_flag(result["is_last_workday_before_holiday"])
    result["days_before_next_holiday"] = _clip_holiday_distance(result["days_before_next_holiday"])
    result["month"] = pd.to_numeric(
        result["month"].where(result["month"].notna(), result["date"].dt.month), errors="coerce"
    ).astype("float64")
    result["week_of_year"] = pd.to_numeric(
        result["week_of_year"].where(
            result["week_of_year"].notna(), result["date"].dt.isocalendar().week.astype("float64")
        ),
        errors="coerce",
    ).astype("float64")
    return result


def _add_seasonal(frame: pd.DataFrame) -> pd.DataFrame:
    """Annual and semi-annual Fourier terms.

    With 4.5 months of history these cannot separate season from trend. They are kept
    because they cost nothing and because a second year of data makes them work.
    """
    result = frame.copy()
    day_of_year = result["date"].dt.dayofyear.astype("float64")
    angle = 2.0 * np.pi * day_of_year / DAYS_IN_YEAR
    result["year_sin"] = np.sin(angle)
    result["year_cos"] = np.cos(angle)
    result["half_year_sin"] = np.sin(2.0 * angle)
    result["half_year_cos"] = np.cos(2.0 * angle)
    return result


def _add_trend(frame: pd.DataFrame, *, anchor: pd.Timestamp) -> pd.DataFrame:
    """Days since the first observed day of the venue."""
    result = frame.copy()
    result["days_since_start"] = (result["date"] - anchor).dt.days.astype("float64")
    return result


def _add_causal_levels(frame: pd.DataFrame) -> pd.DataFrame:
    """Rolling level features that only ever look backwards.

    Everything is shifted by one day before the window is taken, so the row for day t
    never contains day t's own target.
    """
    result = frame.copy()
    target = pd.to_numeric(result[TARGET], errors="coerce").astype("float64")
    previous = target.shift(1)
    result["level_7d"] = previous.rolling(LEVEL_SHORT_DAYS, min_periods=MIN_LEVEL_SHORT_DAYS).mean()
    result["level_28d"] = previous.rolling(LEVEL_LONG_DAYS, min_periods=MIN_LEVEL_LONG_DAYS).mean()
    day_of_week = result["date"].dt.dayofweek
    # Shift inside the weekday group, so the mean covers t-7, t-14, t-21 and t-28 and
    # never the day being predicted.
    same_dow = target.groupby(day_of_week).transform(
        lambda values: values.shift(1).rolling(DOW_OCCURRENCES, min_periods=1).mean()
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        index = same_dow / result["level_28d"]
    result["dow_index_28d"] = index.replace([np.inf, -np.inf], np.nan)
    return result


def _clip_holiday_distance(values: pd.Series) -> pd.Series:
    """Distance to the next holiday, truncated at two weeks.

    The ingest table uses 999 when no holiday is known ahead. Beyond a fortnight the
    distance carries no behavioural signal, so both cases collapse to the same value.
    """
    numeric = pd.to_numeric(values, errors="coerce").astype("float64")
    return numeric.clip(upper=float(HOLIDAY_HORIZON_DAYS))


def _as_float_weather(frame: pd.DataFrame) -> pd.DataFrame:
    """Force the numeric weather columns to float, so training and future frames match."""
    result = frame.copy()
    for column in ("temp_mean", "temp_max", "precip_sum", "precip_hours", "wind_mean", "is_rainy_day"):
        result[column] = pd.to_numeric(result[column], errors="coerce").astype("float64")
    return result


def _as_float_flag(values: pd.Series) -> pd.Series:
    """Coerce a boolean-ish column to 0.0/1.0, keeping missing values missing."""
    if values.dtype == bool:
        return values.astype("float64")
    # CSV round-trips booleans as the strings "True"/"False"; numeric 1/0 already
    # coerce cleanly, and True/1 hash alike so they need only one entry.
    mapped = values.map({True: 1.0, False: 0.0, "True": 1.0, "False": 0.0})
    return pd.to_numeric(mapped.where(mapped.notna(), values), errors="coerce").astype("float64")


def horizon_dates(origin: date, horizon_days: int) -> list[date]:
    """The forecast days of one origin."""
    return [origin + timedelta(days=horizon) for horizon in range(1, horizon_days + 1)]
