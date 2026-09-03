"""Naming one month's quietest days, with a probability on every one of them.

The output is a table of the whole month rather than a list of six dates. Somebody
scheduling an activation event has constraints the model knows nothing about — a
performer's availability, a room booking, a school visit — and the sixth-quietest day
being nearly as good as the second is a fact they need in order to trade one against the
other. The quiet set is marked in that table, not extracted from it.

Days of the target month that have already happened are kept and marked ``observed``.
They compete for a place in the quiet set with their real value and no simulated error,
so running this on the 12th gives a coherent answer about the rest of the month instead
of pretending the first eleven days do not exist.

Ties are the other thing this module refuses to hide. The default rule gives every
Sunday of a month the same score, so four Sundays are genuinely interchangeable to it and
a quiet set of six will contain some Mondays and not others for no reason but the
calendar order. Tied days are therefore given the same probability and the same tie group,
and when the cut runs through a group the answer says so out loud: those days are the
model's way of saying "pick whichever suits you".
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import numpy as np
import pandas as pd

from ..dataset import (
    WEATHER_SOURCE_CLIMATOLOGY,
    ProcessedData,
    Venue,
    as_float,
    venue_future,
    venue_history,
)
from ..evaluation.significance import RANDOM_SEED
from ..i18n import LANGUAGES, bilingual, formats
from .model import (
    DEFAULT_SCORE_MODEL,
    N_SIMULATIONS,
    ScoreRequest,
    build_eligibility,
    complete_flags,
    holiday_flags,
    is_holiday_on,
    observed_series,
    residual_pool,
    score_days,
    selection_probabilities,
    usable_residuals,
)
from .strings import WEEKDAY_NAMES, text
from .threshold import (
    DEFAULT_QUIET_SHARE,
    REASON_OPEN,
    Eligibility,
    QuietSet,
    future_reason,
    observed_reason,
    quiet_set,
)

# Past this many days between the last observation and the start of the month, the
# weekday medians the score rests on describe a different season than the one forecast.
STALE_ORIGIN_DAYS = 21


@dataclass(frozen=True)
class QuietForecastConfig:
    """Everything about a forecast run that is not the month itself."""

    score_model: str = DEFAULT_SCORE_MODEL
    quiet_share: float = DEFAULT_QUIET_SHARE
    top_k: int | None = None
    venues: tuple[int, ...] | None = None
    n_simulations: int = N_SIMULATIONS
    seed: int = RANDOM_SEED

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``config.json``."""
        return {
            "score_model": self.score_model,
            "quiet_share": self.quiet_share,
            "top_k": self.top_k,
            "venues": list(self.venues) if self.venues else None,
            "n_simulations": self.n_simulations,
            "seed": self.seed,
        }


@dataclass(frozen=True)
class DayForecast:
    """One day of the target month, as the model sees it."""

    day: date
    weekday: int
    status: str
    is_eligible: bool
    is_observed: bool
    value: float
    ratio: float
    probability: float
    rank: int | None
    tie_size: int
    is_quiet: bool
    holiday_name: str | None
    temp_mean: float
    precip_sum: float
    weather_source: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``days.csv`` and ``forecast.json``."""
        return {
            "date": self.day.isoformat(),
            "weekday": self.weekday,
            # One column per language rather than a nested value: ``days.csv`` is a table,
            # and a spreadsheet cannot open a dict.
            **{f"weekday_{lang}": WEEKDAY_NAMES[lang][self.weekday] for lang in LANGUAGES},
            "status": self.status,
            "is_eligible": self.is_eligible,
            "is_observed": self.is_observed,
            "value": _round(self.value),
            "ratio": _round(self.ratio, 3),
            "probability": _round(self.probability, 3),
            "rank": self.rank,
            "tie_size": self.tie_size,
            "is_quiet": self.is_quiet,
            "holiday_name": self.holiday_name,
            "temp_mean": _round(self.temp_mean),
            "precip_sum": _round(self.precip_sum),
            "weather_source": self.weather_source,
        }


@dataclass
class VenueMonthForecast:
    """One venue's answer for one month."""

    venue_id: int
    venue_name: str
    year: int
    month: int
    origin: date
    score_model: str
    days: list[DayForecast]
    quiet: QuietSet
    eligibility: Eligibility
    residuals_measured: bool
    n_residuals: int
    warnings: list[dict[str, str]] = field(default_factory=list)

    @property
    def label(self) -> str:
        """``YYYY-MM``."""
        return f"{self.year}-{self.month:02d}"

    @property
    def quiet_days(self) -> list[DayForecast]:
        """The quiet set, quietest first."""
        chosen = [day for day in self.days if day.is_quiet]
        return sorted(chosen, key=lambda day: (day.rank if day.rank is not None else 0, day.day))

    def to_dict(self) -> dict[str, Any]:
        """Serialize for ``forecast.json``."""
        return {
            "venue_id": self.venue_id,
            "venue_name": self.venue_name,
            "month": self.label,
            "origin": self.origin.isoformat(),
            "score_model": self.score_model,
            "quiet_set": self.quiet.to_dict(),
            "eligibility": self.eligibility.to_dict(),
            "residuals": {"measured": self.residuals_measured, "n": self.n_residuals},
            "days": [day.to_dict() for day in self.days],
            "warnings": list(self.warnings),
        }


def month_days(year: int, month: int) -> list[date]:
    """Every calendar day of one month."""
    return [date(year, month, day) for day in range(1, calendar.monthrange(year, month)[1] + 1)]


def next_month(day: date) -> tuple[int, int]:
    """The month after the one ``day`` falls in."""
    return (day.year + 1, 1) if day.month == 12 else (day.year, day.month + 1)


def forecast_month(
    data: ProcessedData, venue: Venue, year: int, month: int, config: QuietForecastConfig
) -> VenueMonthForecast | None:
    """Rank one month's days for one venue and mark the quiet set.

    Returns ``None`` when the venue has no history to learn a weekday rhythm from, which
    is the only failure this function has: everything else it can describe.
    """
    history = venue_history(data, venue.venue_id)
    if history.empty:
        return None
    series = observed_series(history)
    complete = complete_flags(history)
    if series.empty:
        return None
    origin = pd.Timestamp(series.index.max()).date()
    days = month_days(year, month)
    holidays = holiday_flags(data)
    holiday_names = _holiday_names(data)
    eligibility = build_eligibility(
        ScoreRequest(data=data, venue_id=venue.venue_id, history=history, origin=origin, days=())
    )

    future_days = [day for day in days if day > origin]
    request = ScoreRequest(
        data=data,
        venue_id=venue.venue_id,
        history=history,
        origin=origin,
        days=tuple(future_days),
    )
    scores = score_days(config.score_model, request) if future_days else np.zeros(0, dtype="float64")
    by_day = dict(zip(future_days, scores, strict=True))
    is_holiday = dict(zip(days, is_holiday_on(holidays, days), strict=True))

    statuses: list[str] = []
    values: list[float] = []
    observed: list[bool] = []
    for day in days:
        if day > origin:
            statuses.append(future_reason(day, eligibility, is_holiday=is_holiday[day]))
            values.append(float(by_day.get(day, float("nan"))))
            observed.append(False)
            continue
        actual = float(series.get(pd.Timestamp(day), float("nan")))
        complete_day = bool(complete.get(pd.Timestamp(day), True))
        statuses.append(observed_reason(day, actual, eligibility, is_complete=complete_day))
        values.append(actual)
        observed.append(True)

    eligible = [
        index
        for index, (status, value) in enumerate(zip(statuses, values, strict=True))
        if status == REASON_OPEN and np.isfinite(value)
    ]
    quiet = quiet_set(
        [days[index] for index in eligible],
        np.array([values[index] for index in eligible], dtype="float64"),
        share=config.quiet_share,
        k=config.top_k,
    )
    pool = residual_pool(config.score_model, request) if future_days else np.zeros(0, dtype="float64")
    residuals, measured = usable_residuals(pool, seed=config.seed)
    probabilities = selection_probabilities(
        np.array([values[index] for index in eligible], dtype="float64"),
        residuals,
        quiet.k,
        fixed=np.array([observed[index] for index in eligible], dtype=bool),
        n_simulations=config.n_simulations,
        seed=config.seed,
    )
    eligible_values = np.array([values[index] for index in eligible], dtype="float64")
    probabilities = _level_ties(eligible_values, probabilities)
    tie_sizes = _tie_sizes(eligible_values)
    ranks = _ranks(list(eligible_values))
    weather = _weather_context(data, venue.venue_id, origin, days)

    forecasts: list[DayForecast] = []
    for position, day in enumerate(days):
        slot = eligible.index(position) if position in eligible else None
        scale = quiet.median if np.isfinite(quiet.median) and quiet.median > 0 else float("nan")
        row = weather.get(day, {})
        forecasts.append(
            DayForecast(
                day=day,
                weekday=day.weekday(),
                status=statuses[position],
                is_eligible=slot is not None,
                is_observed=observed[position],
                value=values[position],
                ratio=values[position] / scale,
                probability=float(probabilities[slot]) if slot is not None else float("nan"),
                rank=int(ranks[slot]) if slot is not None else None,
                tie_size=int(tie_sizes[slot]) if slot is not None else 0,
                is_quiet=day in quiet.dates,
                holiday_name=holiday_names.get(day),
                temp_mean=as_float(row.get("temp_mean")),
                precip_sum=as_float(row.get("precip_sum")),
                weather_source=row.get("weather_source"),
            )
        )
    result = VenueMonthForecast(
        venue_id=venue.venue_id,
        venue_name=venue.name,
        year=year,
        month=month,
        origin=origin,
        score_model=config.score_model,
        days=forecasts,
        quiet=quiet,
        eligibility=eligibility,
        residuals_measured=measured,
        n_residuals=int(np.asarray(pool).size),
        warnings=[],
    )
    result.warnings = _warnings(data, result, days)
    return result


def _level_ties(values: np.ndarray, probabilities: np.ndarray) -> np.ndarray:
    """Give days with an identical score an identical probability.

    Two Sundays that the rule cannot tell apart must not come back with 47 % and 45 %:
    that gap is Monte Carlo noise, and a reader would take it for a preference. Averaging
    within the tie group says what the model actually knows.
    """
    result = probabilities.astype("float64", copy=True)
    for value in np.unique(values[np.isfinite(values)]):
        group = values == value
        if int(group.sum()) > 1:
            result[group] = float(result[group].mean())
    return result


def _tie_sizes(values: np.ndarray) -> np.ndarray:
    """How many eligible days share each day's exact score."""
    sizes = np.ones(values.size, dtype="int64")
    for value in np.unique(values[np.isfinite(values)]):
        group = values == value
        sizes[group] = int(group.sum())
    return sizes


def _split_tie(days: list[DayForecast]) -> tuple[int, int] | None:
    """The tie group the quiet-set cut runs through, as (chosen, size), or ``None``.

    A cut inside a tie group is the one case where the list of dates is arbitrary rather
    than derived, and saying so turns a silently odd answer into a usable one.
    """
    for day in days:
        if day.is_quiet and day.tie_size > 1:
            members = [other for other in days if other.tie_size == day.tie_size and _same(other, day)]
            chosen = sum(1 for other in members if other.is_quiet)
            if 0 < chosen < len(members):
                return chosen, len(members)
    return None


def _same(left: DayForecast, right: DayForecast) -> bool:
    """Whether two eligible days carry the same score, to the resolution stored."""
    if not (left.is_eligible and right.is_eligible):
        return False
    return bool(np.isclose(left.value, right.value, rtol=0.0, atol=1e-9))


def _ranks(values: list[float]) -> np.ndarray:
    """1-based rank of every eligible day, quietest first, ties broken by date."""
    array = np.asarray(values, dtype="float64")
    if array.size == 0:
        return np.zeros(0, dtype="int64")
    order = np.argsort(array, kind="stable")
    ranks = np.empty(array.size, dtype="int64")
    ranks[order] = np.arange(1, array.size + 1, dtype="int64")
    return ranks


def _holiday_names(data: ProcessedData) -> dict[date, str]:
    """Holiday name per day, for annotating the table."""
    calendar_frame = data.calendar_daily
    names: dict[date, str] = {}
    for day, name in zip(calendar_frame["date"], calendar_frame["holiday_name"], strict=True):
        if isinstance(name, str) and name.strip():
            names[pd.Timestamp(day).date()] = name.strip()
    return names


def _weather_context(
    data: ProcessedData, venue_id: int, origin: date, days: list[date]
) -> dict[date, dict[str, Any]]:
    """Temperature and rainfall per day, as context rather than as a feature.

    Weather is deliberately not in the score. It was tested as a multiplicative factor on
    the ranking and did not improve it — ``docs/QUIET_DAYS.md`` chapter 5 has the numbers —
    but a person choosing between two nearly equal days has every reason to know which one
    the forecast says will rain.
    """
    horizon = max((max(days) - origin).days, 0) if days else 0
    if horizon <= 0:
        return {}
    frame = venue_future(data, venue_id, origin, horizon)
    context: dict[date, dict[str, Any]] = {}
    for _, row in frame.iterrows():
        day = pd.Timestamp(row["date"]).date()
        context[day] = {
            "temp_mean": row.get("temp_mean"),
            "precip_sum": row.get("precip_sum"),
            "weather_source": str(row.get("weather_source", "")) or None,
        }
    return context


def _warnings(
    data: ProcessedData, result: VenueMonthForecast, days: list[date]
) -> list[dict[str, str]]:
    """Everything about this answer a reader should know before acting on it.

    Each warning is stored in every language rather than as one string, because the report
    is rendered in both and a caveat that only one reader sees is worse than none: the
    other reader gets a recommendation with the reservation quietly removed.
    """
    warnings: list[dict[str, str]] = []
    tie = _split_tie(result.days)
    if tie is not None:
        chosen, size = tie
        warnings.append(bilingual(lambda lang: text(lang, "warn_tie", size=size, chosen=chosen)))
    if not result.quiet.is_material:
        gap = (1.0 - result.quiet.mean_ratio)
        warnings.append(
            bilingual(
                lambda lang: text(lang, "warn_not_material", gap=formats(lang).share_percent(gap))
            )
        )
    if not result.residuals_measured:
        warnings.append(bilingual(lambda lang: text(lang, "warn_default_residuals")))
    stale = (days[0] - result.origin).days
    if stale > STALE_ORIGIN_DAYS:
        warnings.append(
            bilingual(
                lambda lang: text(
                    lang, "warn_stale_origin", origin=result.origin.isoformat(), days=stale
                )
            )
        )
    known = set(data.calendar_daily["date"])
    missing = [day for day in days if pd.Timestamp(day) not in known]
    if missing:
        first, count = missing[0].isoformat(), len(missing)
        warnings.append(
            bilingual(lambda lang: text(lang, "warn_calendar_gap", first=first, days=count))
        )
    climatology = [
        day.day for day in result.days if day.weather_source == WEATHER_SOURCE_CLIMATOLOGY
    ]
    if climatology:
        count = len(climatology)
        warnings.append(bilingual(lambda lang: text(lang, "warn_climatology", days=count)))
    if result.eligibility.closed_weekdays:
        closed = result.eligibility.closed_weekdays
        warnings.append(
            bilingual(
                lambda lang: text(
                    lang,
                    "warn_closed_weekdays",
                    days=", ".join(WEEKDAY_NAMES[lang][day] for day in closed),
                )
            )
        )
    return warnings


def _round(value: float, digits: int = 1) -> float | None:
    """Round for JSON, mapping every non-finite value to null."""
    return None if not np.isfinite(value) else round(float(value), digits)
