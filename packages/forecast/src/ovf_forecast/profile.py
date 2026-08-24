"""The hourly profile: how a day's visitors are distributed across its open hours.

Both models forecast days. This layer, shared by both, turns a daily number into 24
hourly numbers whose sum is exactly that daily number. That is the point: in the
reference implementation ``visitors_in``, ``visitors_out`` and ``total_visitors`` come
from three separate models, so on 2026-05-23 they read 63.99, 52.12 and 191.31 and the
first two do not add up to the third.

The profile is an average of observed shares, not of observed counts, so a single busy
Saturday cannot dominate the shape. Weekday profiles are shrunk towards the all-week
profile because eight weeks give only eight observations per weekday.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from . import log_event

HOURS_PER_DAY = 24
DAYS_PER_WEEK = 7
LOOKBACK_DAYS = 56
SHRINK_K = 4.0
# An hour whose non-zero rate over the window is below this counts as closed.
CLOSED_THRESHOLD = 0.05


@dataclass(frozen=True)
class HourProfile:
    """Normalized hourly shares for one venue, indexed ``[day_of_week][hour]``."""

    venue_id: int
    shares: np.ndarray
    open_hours: tuple[int, ...]
    observed_days: int
    lookback_days: int
    origin: date

    def day_shares(self, day_of_week: int) -> np.ndarray:
        """The 24 shares of one weekday. They sum to 1."""
        row: np.ndarray = self.shares[day_of_week % DAYS_PER_WEEK]
        return row

    def to_records(self) -> list[dict[str, float | int]]:
        """Flatten to rows, for writing the profile into the metrics file."""
        return [
            {"day_of_week": int(day), "hour": int(hour), "share": float(self.shares[day, hour])}
            for day in range(DAYS_PER_WEEK)
            for hour in range(HOURS_PER_DAY)
        ]


def build_profile(
    hourly: pd.DataFrame,
    venue_id: int,
    origin: date,
    *,
    lookback_days: int = LOOKBACK_DAYS,
    shrink_k: float = SHRINK_K,
    closed_threshold: float = CLOSED_THRESHOLD,
) -> HourProfile:
    """Build the shrunk, opening-hour-aware hourly profile as it stands at ``origin``.

    Only days at or before ``origin`` are read, so a profile built inside a backtest
    cannot see the days it is about to be scored on.
    """
    stamp = pd.Timestamp(origin)
    window_start = stamp - pd.Timedelta(days=lookback_days - 1)
    selected = hourly.loc[
        (hourly["venue_id"] == venue_id) & (hourly["date"] <= stamp) & (hourly["date"] >= window_start)
    ]
    if selected.empty:
        log_event("warning", "profile", "No hourly data in window, using a flat profile", venue_id=venue_id)
        return _flat_profile(venue_id, origin, lookback_days, observed_days=0)

    values = selected.assign(
        visitors_total=pd.to_numeric(selected["visitors_total"], errors="coerce").astype("float64")
    )
    counts = values.pivot_table(
        index="date", columns="hour", values="visitors_total", aggfunc="sum", fill_value=0.0
    ).reindex(columns=range(HOURS_PER_DAY), fill_value=0.0)
    daily_totals = counts.sum(axis=1)
    active = counts.loc[daily_totals > 0]
    if active.empty:
        log_event("warning", "profile", "Every day in the window is empty", venue_id=venue_id)
        return _flat_profile(venue_id, origin, lookback_days, observed_days=0)

    open_mask = _open_hours(active, closed_threshold)
    shares = active.div(active.sum(axis=1), axis=0)
    share_all = shares.mean(axis=0).to_numpy(dtype="float64")
    day_of_week = pd.Series(active.index, index=active.index).dt.dayofweek

    profile = np.zeros((DAYS_PER_WEEK, HOURS_PER_DAY), dtype="float64")
    for weekday in range(DAYS_PER_WEEK):
        rows = shares.loc[day_of_week == weekday]
        count = float(len(rows))
        share_dow = rows.mean(axis=0).to_numpy(dtype="float64") if count else share_all
        shrunk = (count * share_dow + shrink_k * share_all) / (count + shrink_k)
        profile[weekday] = _close_and_normalize(shrunk, open_mask)

    return HourProfile(
        venue_id=venue_id,
        shares=profile,
        open_hours=tuple(int(hour) for hour in np.flatnonzero(open_mask)),
        observed_days=len(active),
        lookback_days=lookback_days,
        origin=origin,
    )


def _open_hours(counts: pd.DataFrame, closed_threshold: float) -> np.ndarray:
    """Hours whose non-zero rate over the window clears the threshold.

    Opening hours are read out of the data rather than configured, so a venue that
    changes its hours is followed automatically eight weeks later.
    """
    non_zero_rate = (counts > 0).mean(axis=0).to_numpy(dtype="float64")
    mask = non_zero_rate >= closed_threshold
    if not mask.any():
        return np.ones(HOURS_PER_DAY, dtype=bool)
    return mask


def _close_and_normalize(shares: np.ndarray, open_mask: np.ndarray) -> np.ndarray:
    """Zero the closed hours, then normalize so the day sums to exactly 1."""
    masked = np.where(open_mask, shares, 0.0)
    masked = np.maximum(masked, 0.0)
    total = float(masked.sum())
    if total <= 0:
        fallback = open_mask.astype("float64")
        normalized: np.ndarray = fallback / fallback.sum()
        return normalized
    scaled: np.ndarray = masked / total
    return scaled


def _flat_profile(venue_id: int, origin: date, lookback_days: int, observed_days: int) -> HourProfile:
    """A uniform profile, used only when a venue has no usable history at all."""
    shares = np.full((DAYS_PER_WEEK, HOURS_PER_DAY), 1.0 / HOURS_PER_DAY, dtype="float64")
    return HourProfile(
        venue_id=venue_id,
        shares=shares,
        open_hours=tuple(range(HOURS_PER_DAY)),
        observed_days=observed_days,
        lookback_days=lookback_days,
        origin=origin,
    )


def spread_over_hours(
    profile: HourProfile, day_of_week: int, hours: list[int], daily_value: float
) -> np.ndarray:
    """Split one daily forecast across the local hours a day actually has.

    ``hours`` is the day's real local wall-clock hours, which is 23 or 25 entries on a
    DST transition day rather than 24. The shares are renormalized over exactly those
    hours, so the hourly forecasts still sum to the daily forecast on those two days a
    year as well.
    """
    shares = profile.day_shares(day_of_week)[np.asarray(hours, dtype="int64")]
    total = shares.sum()
    weights = shares / total if total > 0 else np.full(len(hours), 1.0 / len(hours), dtype="float64")
    return weights * float(daily_value)
