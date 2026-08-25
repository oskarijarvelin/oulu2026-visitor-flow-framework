"""Window parsing and the two sweeps.

The rule these tests exist to defend is that ``test_start`` is always ``origin + 1``. A
gap between them would quietly drop the horizons the forecast is worst at and make every
metric look better than it is, so the window refuses to be built at all.
"""

from __future__ import annotations

from datetime import date
from itertools import pairwise

import pytest

from ovf_forecast.evaluation.windows import (
    TRAIN_WINDOW_ALL,
    Window,
    WindowError,
    make_window,
    monthly_sweep,
    parse_test_spec,
    parse_train_window,
    rolling_sweep,
)

HISTORY_FIRST = date(2026, 1, 1)
HISTORY_LAST = date(2026, 8, 25)


def test_a_month_shorthand_expands_to_the_whole_month() -> None:
    """``--test 2026-04`` means the origin is 31 March and the test is all of April."""
    window = make_window(test="2026-04")
    assert window.origin == date(2026, 3, 31)
    assert window.test_start == date(2026, 4, 1)
    assert window.test_end == date(2026, 4, 30)
    assert window.horizon_days == 30


def test_an_explicit_range_keeps_its_bounds() -> None:
    """``--test 2026-04-01:2026-04-30`` with a matching ``--train-end``."""
    window = make_window(train_end="2026-03-31", test="2026-04-01:2026-04-30")
    assert window.origin == date(2026, 3, 31)
    assert window.horizon_days == 30


def test_a_gap_between_the_origin_and_the_test_period_is_refused() -> None:
    """The test period has to start at horizon 1, or the hard horizons go missing."""
    with pytest.raises(WindowError, match=r"horisontilla 1|horizon 1"):
        make_window(train_end="2026-03-01", test="2026-04-01:2026-04-30")


def test_a_window_built_directly_is_checked_too() -> None:
    """The invariant lives on the dataclass, not only in the CLI parsing."""
    with pytest.raises(WindowError):
        Window(origin=date(2026, 3, 1), test_start=date(2026, 4, 1), test_end=date(2026, 4, 30))
    with pytest.raises(WindowError):
        Window(origin=date(2026, 3, 31), test_start=date(2026, 4, 1), test_end=date(2026, 3, 20))


def test_the_training_window_is_all_or_a_day_count() -> None:
    """``all`` or a positive number of days, and nothing else."""
    assert parse_train_window("all") == TRAIN_WINDOW_ALL
    assert parse_train_window("120") == "120"
    with pytest.raises(WindowError):
        parse_train_window("recent")
    with pytest.raises(WindowError):
        parse_train_window("-5")


def test_a_sliding_training_window_moves_the_left_edge() -> None:
    """``--train-window 120`` trains on the 120 days ending at the origin."""
    window = make_window(test="2026-04", train_window="120")
    # A 120 day window ending 31 March would start 2 December, before the history does,
    # so it is clamped: a sliding window can only slide over days that exist.
    assert window.train_start(date(2025, 1, 1)) == date(2025, 12, 2)
    assert window.train_start(HISTORY_FIRST) == HISTORY_FIRST
    assert window.train_start(date(2026, 2, 1)) == date(2026, 2, 1)
    assert Window(
        origin=date(2026, 3, 31),
        test_start=date(2026, 4, 1),
        test_end=date(2026, 4, 30),
        train_window="60",
    ).training_days(HISTORY_FIRST) == 60


def test_the_full_training_window_starts_where_the_history_does() -> None:
    """``all`` means every day the file has, leading zeros included."""
    window = make_window(test="2026-04")
    assert window.train_start(HISTORY_FIRST) == HISTORY_FIRST
    assert window.training_days(HISTORY_FIRST) == 90


def test_test_spec_forms() -> None:
    """Month, single day and explicit range all parse; anything else does not."""
    assert parse_test_spec("2026-04") == (date(2026, 4, 1), date(2026, 4, 30))
    assert parse_test_spec("2026-02") == (date(2026, 2, 1), date(2026, 2, 28))
    assert parse_test_spec("2026-04-15") == (date(2026, 4, 15), date(2026, 4, 15))
    assert parse_test_spec("2026-04-01:2026-04-10") == (date(2026, 4, 1), date(2026, 4, 10))
    for bad in ("April", "2026", "2026-13", "2026-04-01..2026-04-10"):
        with pytest.raises(WindowError):
            parse_test_spec(bad)


# --------------------------------------------------------------------------------------
# Sweeps
# --------------------------------------------------------------------------------------


def test_the_monthly_sweep_produces_one_window_per_month() -> None:
    """Acceptance criterion: April to August is five windows."""
    windows = monthly_sweep(
        first_month="2026-04", last_month="2026-08", history_last_day=HISTORY_LAST
    )
    assert len(windows) == 5
    assert [window.test_start.month for window in windows] == [4, 5, 6, 7, 8]
    for window in windows:
        assert window.test_start == window.origin.replace(day=1) or window.test_start.day == 1
        assert window.test_start.day == 1


def test_the_monthly_sweep_truncates_the_last_month_at_the_last_observed_day() -> None:
    """A partial August still measures 25 days rather than being dropped."""
    windows = monthly_sweep(
        first_month="2026-04", last_month="2026-08", history_last_day=HISTORY_LAST
    )
    assert windows[-1].test_end == HISTORY_LAST
    assert windows[-1].horizon_days == 25


def test_each_monthly_origin_is_the_last_day_of_the_month_before() -> None:
    """The definition of the monthly sweep, checked directly."""
    windows = monthly_sweep(
        first_month="2026-04", last_month="2026-06", history_last_day=HISTORY_LAST
    )
    assert [window.origin for window in windows] == [
        date(2026, 3, 31),
        date(2026, 4, 30),
        date(2026, 5, 31),
    ]


def test_a_monthly_sweep_entirely_in_the_future_is_refused() -> None:
    """Asking for months with no observations fails loudly."""
    with pytest.raises(WindowError):
        monthly_sweep(first_month="2027-01", last_month="2027-03", history_last_day=HISTORY_LAST)
    with pytest.raises(WindowError, match="after"):
        monthly_sweep(first_month="2026-08", last_month="2026-04", history_last_day=HISTORY_LAST)


def test_the_rolling_sweep_steps_by_the_requested_interval() -> None:
    """Origins 14 days apart, each with a 30 day test period, oldest first."""
    windows = rolling_sweep(
        history_first_day=HISTORY_FIRST,
        history_last_day=HISTORY_LAST,
        step_days=14,
        horizon_days=30,
        max_windows=5,
    )
    assert len(windows) == 5
    assert all(window.horizon_days == 30 for window in windows)
    assert windows[-1].test_end == HISTORY_LAST
    gaps = {(later.origin - earlier.origin).days for earlier, later in pairwise(windows)}
    assert gaps == {14}
    assert windows == sorted(windows, key=lambda window: window.origin)


def test_the_rolling_sweep_stops_at_the_training_floor() -> None:
    """A window whose training side is too short is not produced at all."""
    windows = rolling_sweep(
        history_first_day=HISTORY_FIRST,
        history_last_day=HISTORY_LAST,
        step_days=14,
        horizon_days=30,
        max_windows=100,
        min_training_days=60,
    )
    assert all(window.training_days(HISTORY_FIRST) >= 60 for window in windows)
    assert windows[0].training_days(HISTORY_FIRST) < 60 + 14


def test_a_rolling_sweep_with_no_room_is_refused() -> None:
    """A horizon longer than the history cannot produce a window."""
    with pytest.raises(WindowError):
        rolling_sweep(
            history_first_day=date(2026, 8, 1),
            history_last_day=HISTORY_LAST,
            horizon_days=30,
            min_training_days=60,
        )
    with pytest.raises(WindowError, match="positive"):
        rolling_sweep(history_first_day=HISTORY_FIRST, history_last_day=HISTORY_LAST, step_days=0)


def test_a_window_round_trips_through_its_serialized_form() -> None:
    """The stored ``config.json`` has to rebuild the window it describes."""
    window = make_window(test="2026-04", train_window="120")
    assert Window.from_dict(window.to_dict()) == window
