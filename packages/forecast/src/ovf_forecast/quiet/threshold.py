"""What counts as a quiet day, and which days are allowed to be one.

Three decisions live here and nowhere else, because every other module in this package
reads them rather than restating them.

*Which days can be chosen.* A day the venue is closed is the quietest day of every month
and is useless for an activation event, so it is not a candidate at all. Venue 2 takes
almost no visitors on Mondays; that is an opening-hours fact, not an insight.

*Where the line falls.* The quiet set is the lowest ``share`` of a month's eligible
days, ``share`` defaulting to 0.20. On the committed history that line sits at roughly
0.66 x the month's median day, and the days below it average about 0.50 x. The choice is
measured rather than assumed, and ``docs/QUIET_DAYS.md`` chapter 3 has the table that
supports it.

*Whether the answer is worth acting on.* A month whose days are all alike still has a
lowest fifth, and naming it would be a recommendation with nothing behind it. So a quiet
set carries ``is_material``: the set has to sit at least 15 % below the month median
before anything downstream is allowed to call it a recommendation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import pandas as pd

DEFAULT_QUIET_SHARE = 0.20
MIN_QUIET_DAYS = 3
MAX_QUIET_DAYS = 10

# A weekday whose median sits below this share of the venue's own median is an opening
# hours fact rather than a quiet day. Venue 2's Mondays land at 0.14.
CLOSED_WEEKDAY_SHARE = 0.15
MIN_WEEKDAY_OBSERVATIONS = 3

# The quiet set has to be at least this far below the month median to be a finding.
MATERIAL_GAP = 0.15

# A holiday factor from a handful of observations can be wild, so it is clipped before
# anything multiplies a score by it.
MIN_HOLIDAY_OBSERVATIONS = 3
HOLIDAY_FACTOR_FLOOR = 0.05
HOLIDAY_FACTOR_CEILING = 2.0

REASON_OPEN = "open"
REASON_CLOSED_WEEKDAY = "closed_weekday"
REASON_CLOSED_HOLIDAY = "closed_holiday"
REASON_NO_VISITORS = "no_visitors"
REASON_INCOMPLETE = "incomplete_day"
REASON_UNOBSERVED = "unobserved"

REASON_ORDER: tuple[str, ...] = (
    REASON_OPEN,
    REASON_CLOSED_WEEKDAY,
    REASON_CLOSED_HOLIDAY,
    REASON_NO_VISITORS,
    REASON_INCOMPLETE,
    REASON_UNOBSERVED,
)


@dataclass(frozen=True)
class Eligibility:
    """How a venue's calendar behaves, as it stood at one origin.

    Derived from the training window only, so applying it to a future month leaks
    nothing. It is deliberately blunt: one median per weekday and one factor for public
    holidays, no seasonal opening hours, because four weekly observations per weekday
    cannot support anything finer.

    ``holiday_factor`` is shared on purpose. The same number decides whether a holiday is
    a closure the filter has to drop and how far a holiday pushes a score down, and those
    two answers must never disagree.

    Two weekday statistics, because they answer different questions. The median decides
    whether a weekday is a closure, where one busy Monday must not overturn twenty empty
    ones. The mean is what the score ranks on, where an occasional busy Saturday is
    exactly the information that keeps Saturday out of the quiet set. Measured over the
    committed history the mean ranks better; the table is in ``docs/QUIET_DAYS.md``
    chapter 5.
    """

    closed_weekdays: tuple[int, ...]
    weekday_medians: dict[int, float]
    venue_median: float
    weekday_means: dict[int, float] = field(default_factory=dict)
    venue_mean: float = float("nan")
    holiday_factor: float = float("nan")
    holiday_observations: int = 0

    @classmethod
    def from_training(cls, series: pd.Series, holidays: pd.Series | None = None) -> Eligibility:
        """Read the opening pattern and the holiday factor out of a day-indexed series."""
        if series.empty:
            return cls(closed_weekdays=(), weekday_medians={}, venue_median=float("nan"))
        weekdays = pd.Series(pd.DatetimeIndex(series.index).dayofweek, index=series.index)
        grouped = series.groupby(weekdays)
        medians = {int(str(day)): float(value) for day, value in grouped.median().items()}
        means = {int(str(day)): float(value) for day, value in grouped.mean().items()}
        counts = {int(str(day)): int(value) for day, value in grouped.size().items()}
        venue_median = float(series.median())
        closed = tuple(
            day
            for day, value in sorted(medians.items())
            if counts.get(day, 0) >= MIN_WEEKDAY_OBSERVATIONS
            and venue_median > 0.0
            and value < CLOSED_WEEKDAY_SHARE * venue_median
        )
        factor, observations = _holiday_factor(series, weekdays, means, holidays)
        return cls(
            closed_weekdays=closed,
            weekday_medians=medians,
            venue_median=venue_median,
            weekday_means=means,
            venue_mean=float(series.mean()),
            holiday_factor=factor,
            holiday_observations=observations,
        )

    @property
    def closes_on_holidays(self) -> bool:
        """Whether public holidays are closures at this venue rather than quiet days."""
        return bool(np.isfinite(self.holiday_factor) and self.holiday_factor < CLOSED_WEEKDAY_SHARE)

    def is_closed_weekday(self, day: date) -> bool:
        """Whether the venue is structurally closed on this day's weekday."""
        return day.weekday() in self.closed_weekdays

    def weekday_level(self, day: date) -> float:
        """The level the score ranks on: this weekday's training mean.

        Falls back to the venue mean for a weekday the training window never saw. Falling
        back rather than dropping the day matters: a day with no score would silently
        never be recommended, which is not the same statement as "this day is not quiet".
        """
        return self.weekday_means.get(day.weekday(), self.venue_mean)

    def to_dict(self) -> dict[str, object]:
        """Serialize for ``config.json``."""
        return {
            "closed_weekdays": list(self.closed_weekdays),
            "weekday_medians": {
                str(day): round(value, 1) for day, value in sorted(self.weekday_medians.items())
            },
            "weekday_means": {
                str(day): round(value, 1) for day, value in sorted(self.weekday_means.items())
            },
            "venue_median": None if math.isnan(self.venue_median) else round(self.venue_median, 1),
            "venue_mean": None if math.isnan(self.venue_mean) else round(self.venue_mean, 1),
            "closed_weekday_share": CLOSED_WEEKDAY_SHARE,
            "holiday_factor": _round(self.holiday_factor, 3),
            "holiday_observations": self.holiday_observations,
            "closes_on_holidays": self.closes_on_holidays,
        }


def _holiday_factor(
    series: pd.Series,
    weekdays: pd.Series,
    levels: dict[int, float],
    holidays: pd.Series | None,
) -> tuple[float, int]:
    """What a public holiday does to a day, as a multiple of its weekday's mean.

    Measured against the same weekday statistic the score is built from, so multiplying
    one by the other stays dimensionally honest.

    The median rather than the mean, and only when at least three holidays have been
    observed: on eight months of history this rests on a handful of days and a single
    closed Good Friday would otherwise drag the factor to zero.
    """
    if holidays is None:
        return float("nan"), 0
    flags = holidays.reindex(series.index).fillna(False).astype(bool).to_numpy()
    observations = int(flags.sum())
    if observations < MIN_HOLIDAY_OBSERVATIONS:
        return float("nan"), observations
    level = np.array([levels.get(int(day), float("nan")) for day in weekdays], dtype="float64")
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = series.to_numpy(dtype="float64") / level
    values = ratio[flags & np.isfinite(ratio)]
    if values.size == 0:
        return float("nan"), observations
    factor = float(np.median(values))
    return float(np.clip(factor, HOLIDAY_FACTOR_FLOOR, HOLIDAY_FACTOR_CEILING)), observations


def future_reason(day: date, eligibility: Eligibility, *, is_holiday: bool = False) -> str:
    """Why a *future* day is or is not a candidate.

    Two rules can be applied ahead of time, and only two: the weekday the venue is shut,
    and public holidays at a venue that closes on them. Whether the venue happens to take
    zero visitors on some Tuesday in October is exactly what the model is trying to
    predict, so it cannot also be an input to the filter.
    """
    if eligibility.is_closed_weekday(day):
        return REASON_CLOSED_WEEKDAY
    if is_holiday and eligibility.closes_on_holidays:
        return REASON_CLOSED_HOLIDAY
    return REASON_OPEN


def observed_reason(
    day: date, value: float, eligibility: Eligibility, *, is_complete: bool = True
) -> str:
    """Why an *observed* day does or does not belong in the truth set.

    Three exclusions, in order. A closed weekday is not a quiet day. A day with no
    visitors at all was a closure, an outage or a public holiday the venue took off, and
    scoring a model on its ability to predict a closure is scoring the holiday calendar.
    A day the counter did not answer for the whole of looks quiet for a reason that has
    nothing to do with visitors.
    """
    if eligibility.is_closed_weekday(day):
        return REASON_CLOSED_WEEKDAY
    if not np.isfinite(value):
        return REASON_UNOBSERVED
    if not is_complete:
        return REASON_INCOMPLETE
    if value <= 0.0:
        return REASON_NO_VISITORS
    return REASON_OPEN


def quiet_count(n_eligible: int, share: float = DEFAULT_QUIET_SHARE) -> int:
    """How many days the quiet set holds, clamped to a usable range.

    The clamp matters at both ends. Below three days the set is one bad Tuesday away
    from being empty and the measured hit rate stops meaning anything; above ten it
    stops being a recommendation and becomes a third of the month.
    """
    if n_eligible <= 0:
        return 0
    wanted = math.ceil(share * n_eligible)
    return min(n_eligible, max(MIN_QUIET_DAYS, min(MAX_QUIET_DAYS, wanted)))


@dataclass(frozen=True)
class QuietSet:
    """The lowest ``k`` of a month's eligible days, and how far below normal they sit.

    The same object describes an observed month and a forecast one. For an observed
    month ``values`` are visitor counts; for a forecast one they are the model's daily
    scores, which are on the same scale but are not predictions anybody should quote as
    counts. Everything downstream compares ratios, never levels.
    """

    dates: tuple[date, ...]
    values: np.ndarray
    positions: np.ndarray
    n_eligible: int
    k: int
    median: float
    cut: float
    cut_ratio: float
    mean_ratio: float

    @property
    def is_material(self) -> bool:
        """Whether the set is far enough below the month median to be worth naming."""
        return bool(np.isfinite(self.mean_ratio) and self.mean_ratio <= 1.0 - MATERIAL_GAP)

    def to_dict(self) -> dict[str, object]:
        """Serialize for ``metrics.json``."""
        return {
            "dates": [day.isoformat() for day in self.dates],
            "k": self.k,
            "n_eligible": self.n_eligible,
            "median": _round(self.median),
            "cut": _round(self.cut),
            "cut_ratio": _round(self.cut_ratio, 3),
            "mean_ratio": _round(self.mean_ratio, 3),
            "is_material": self.is_material,
            "material_gap": MATERIAL_GAP,
        }


def quiet_set(
    days: list[date], values: np.ndarray, *, share: float = DEFAULT_QUIET_SHARE, k: int | None = None
) -> QuietSet:
    """Rank one month's eligible days and take the lowest ``k`` of them.

    Ties are broken by date, which is what ``kind="stable"`` buys: two days with the
    same score always come back in calendar order, so a run is reproducible and the
    earlier of two equally quiet days is the one offered first.
    """
    array = np.asarray(values, dtype="float64")
    if array.size != len(days):
        raise ValueError(f"Got {len(days)} days and {array.size} values.")
    n = int(array.size)
    size = quiet_count(n, share) if k is None else max(0, min(k, n))
    if n == 0:
        empty = np.zeros(0, dtype="float64")
        return QuietSet((), empty, np.zeros(0, dtype="int64"), 0, 0, *(float("nan"),) * 4)
    order = np.argsort(array, kind="stable")[:size]
    order = np.sort(order)
    median = float(np.median(array))
    chosen = array[order]
    cut = float(chosen.max()) if size else float("nan")
    scale = median if median > 0.0 else float("nan")
    return QuietSet(
        dates=tuple(days[position] for position in order),
        values=chosen,
        positions=order.astype("int64"),
        n_eligible=n,
        k=size,
        median=median,
        cut=cut,
        cut_ratio=cut / scale,
        mean_ratio=float(chosen.mean()) / scale if size else float("nan"),
    )


def _round(value: float, digits: int = 1) -> float | None:
    """Round for JSON, mapping every non-finite value to null."""
    return None if not np.isfinite(value) else round(float(value), digits)
