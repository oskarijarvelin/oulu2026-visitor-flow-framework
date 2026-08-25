"""Evaluation windows: what was trained on, what was forecast, and how the sweeps step.

A window is three facts and nothing else. ``origin`` is the last day whose data the
model is allowed to see. ``test_start`` and ``test_end`` bound the days it is scored on,
and ``test_start`` is always ``origin + 1`` — a gap between them would silently discard
the horizons the forecast is worst at. ``train_window`` is either the whole history up
to the origin or a fixed number of days ending at it.

Everything downstream reads the window and never the calendar, so a monthly sweep, a
rolling sweep and a hand-written ``--train-end``/``--test`` pair all produce the same
kind of object and go through the same code.
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta

TRAIN_WINDOW_ALL = "all"
DEFAULT_ROLLING_STEP_DAYS = 14
DEFAULT_ROLLING_HORIZON_DAYS = 30
DEFAULT_MAX_WINDOWS = 12
# A window whose training side is shorter than this cannot say anything about a model.
MIN_TRAINING_DAYS = 60

_MONTH_PATTERN = re.compile(r"^(\d{4})-(\d{2})$")
_DAY_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


class WindowError(ValueError):
    """Raised when a window cannot be built from what the caller asked for."""


@dataclass(frozen=True)
class Window:
    """One evaluation window: train up to ``origin``, score ``test_start``-``test_end``."""

    origin: date
    test_start: date
    test_end: date
    train_window: str = TRAIN_WINDOW_ALL

    def __post_init__(self) -> None:
        if self.test_start != self.origin + timedelta(days=1):
            raise WindowError(
                f"The test period has to start the day after the origin: origin {self.origin}, "
                f"test starts {self.test_start}, expected {self.origin + timedelta(days=1)}."
            )
        if self.test_end < self.test_start:
            raise WindowError(f"Empty test period: {self.test_start} to {self.test_end}.")
        parse_train_window(self.train_window)

    @property
    def horizon_days(self) -> int:
        """Length of the test period in days, which is also its longest horizon."""
        return (self.test_end - self.test_start).days + 1

    @property
    def label(self) -> str:
        """Short human label, used in tables and in the run id."""
        return f"{self.test_start.isoformat()}..{self.test_end.isoformat()}"

    def train_start(self, history_start: date) -> date:
        """First training day: the start of the history, or the sliding window's edge."""
        if self.train_window == TRAIN_WINDOW_ALL:
            return history_start
        days = int(self.train_window)
        return max(history_start, self.origin - timedelta(days=days - 1))

    def training_days(self, history_start: date) -> int:
        """How many calendar days the training side spans."""
        return (self.origin - self.train_start(history_start)).days + 1

    def test_dates(self) -> list[date]:
        """Every day in the test period, in order."""
        return [self.test_start + timedelta(days=step) for step in range(self.horizon_days)]

    def to_dict(self) -> dict[str, str | int]:
        """Serialize for ``config.json`` and the index."""
        return {
            "origin": self.origin.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "horizon_days": self.horizon_days,
            "train_window": self.train_window,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, str | int]) -> Window:
        """Rebuild a window from its serialized form."""
        return cls(
            origin=date.fromisoformat(str(payload["origin"])),
            test_start=date.fromisoformat(str(payload["test_start"])),
            test_end=date.fromisoformat(str(payload["test_end"])),
            train_window=str(payload.get("train_window", TRAIN_WINDOW_ALL)),
        )


def parse_train_window(text: str) -> str:
    """Validate ``all`` or a positive day count, returning it normalized."""
    if text == TRAIN_WINDOW_ALL:
        return TRAIN_WINDOW_ALL
    try:
        days = int(text)
    except ValueError as exc:
        raise WindowError(f"--train-window takes 'all' or a number of days, not {text!r}.") from exc
    if days <= 0:
        raise WindowError(f"--train-window has to be positive, got {days}.")
    return str(days)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """First and last day of one calendar month."""
    return date(year, month, 1), date(year, month, calendar.monthrange(year, month)[1])


def parse_month(text: str) -> tuple[int, int]:
    """Parse ``YYYY-MM``."""
    match = _MONTH_PATTERN.match(text.strip())
    if not match:
        raise WindowError(f"Expected a month as YYYY-MM, got {text!r}.")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise WindowError(f"Not a month: {text!r}.")
    return year, month


def parse_test_spec(text: str) -> tuple[date, date]:
    """Parse ``2026-04`` (a whole month) or ``2026-04-01:2026-04-30`` (an explicit range)."""
    cleaned = text.strip()
    if _MONTH_PATTERN.match(cleaned):
        return month_bounds(*parse_month(cleaned))
    if ":" in cleaned:
        start_text, _, end_text = cleaned.partition(":")
        return _parse_day(start_text), _parse_day(end_text)
    if _DAY_PATTERN.match(cleaned):
        day = _parse_day(cleaned)
        return day, day
    raise WindowError(
        f"Expected --test as YYYY-MM, YYYY-MM-DD or YYYY-MM-DD:YYYY-MM-DD, got {text!r}."
    )


def _parse_day(text: str) -> date:
    """Parse one ``YYYY-MM-DD``."""
    cleaned = text.strip()
    if not _DAY_PATTERN.match(cleaned):
        raise WindowError(f"Expected a day as YYYY-MM-DD, got {text!r}.")
    return date.fromisoformat(cleaned)


def make_window(
    *, test: str, train_end: str | None = None, train_window: str = TRAIN_WINDOW_ALL
) -> Window:
    """Build one window from the CLI arguments.

    Without ``--train-end`` the origin is the day before the test period, which is the
    only origin that makes the test period start at horizon 1.
    """
    test_start, test_end = parse_test_spec(test)
    origin = _parse_day(train_end) if train_end else test_start - timedelta(days=1)
    if origin + timedelta(days=1) != test_start:
        raise WindowError(
            f"--train-end {origin.isoformat()} and --test starting {test_start.isoformat()} leave a "
            f"{(test_start - origin).days - 1} day gap. The test period has to start at horizon 1."
        )
    return Window(
        origin=origin,
        test_start=test_start,
        test_end=test_end,
        train_window=parse_train_window(train_window),
    )


def monthly_sweep(
    *,
    first_month: str,
    last_month: str,
    history_last_day: date,
    train_window: str = TRAIN_WINDOW_ALL,
) -> list[Window]:
    """One window per calendar month, each trained up to the end of the month before it.

    The last month is truncated at the last observed day rather than dropped: a partial
    August still measures 25 days of forecast, and the report says how many.
    """
    start_year, start_month = parse_month(first_month)
    end_year, end_month = parse_month(last_month)
    if (end_year, end_month) < (start_year, start_month):
        raise WindowError(f"--from {first_month} is after --to {last_month}.")
    windows: list[Window] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        first_day, last_day = month_bounds(year, month)
        test_end = min(last_day, history_last_day)
        if test_end >= first_day:
            windows.append(
                Window(
                    origin=first_day - timedelta(days=1),
                    test_start=first_day,
                    test_end=test_end,
                    train_window=parse_train_window(train_window),
                )
            )
        month += 1
        if month > 12:
            year, month = year + 1, 1
    if not windows:
        raise WindowError(
            f"No month between {first_month} and {last_month} has observed days on or before "
            f"{history_last_day.isoformat()}."
        )
    return windows


def rolling_sweep(
    *,
    history_first_day: date,
    history_last_day: date,
    step_days: int = DEFAULT_ROLLING_STEP_DAYS,
    horizon_days: int = DEFAULT_ROLLING_HORIZON_DAYS,
    train_window: str = TRAIN_WINDOW_ALL,
    max_windows: int = DEFAULT_MAX_WINDOWS,
    min_training_days: int = MIN_TRAINING_DAYS,
) -> list[Window]:
    """Origins stepping back ``step_days`` at a time, each with a fixed horizon.

    Generated newest first so that trimming to ``max_windows`` keeps the most recent
    evidence, then returned oldest first because that is how a report reads.
    """
    if step_days <= 0 or horizon_days <= 0:
        raise WindowError("--step and --horizon both have to be positive.")
    windows: list[Window] = []
    origin = history_last_day - timedelta(days=horizon_days)
    while len(windows) < max_windows:
        candidate = Window(
            origin=origin,
            test_start=origin + timedelta(days=1),
            test_end=origin + timedelta(days=horizon_days),
            train_window=parse_train_window(train_window),
        )
        if candidate.training_days(history_first_day) < min_training_days:
            break
        windows.append(candidate)
        origin -= timedelta(days=step_days)
    if not windows:
        raise WindowError(
            f"No rolling window fits: a {horizon_days} day horizon needs at least "
            f"{min_training_days} training days, and the history runs "
            f"{history_first_day.isoformat()} to {history_last_day.isoformat()}."
        )
    return list(reversed(windows))
