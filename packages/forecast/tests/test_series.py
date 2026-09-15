"""The three forecastable series.

What matters here is that a series is genuinely forecast from its own column and not
from the visitor count with a label attached. The synthetic fixture makes the three
series deliberately different in level and in weekday shape, so a pipeline that read the
wrong column would produce numbers of the wrong size and these tests would catch it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ovf_forecast.cli import main
from ovf_forecast.dataset import load_dataset, venue_history
from ovf_forecast.features import TARGET, build_training_frame
from ovf_forecast.series import (
    ALL_SERIES,
    DEFAULT_SERIES,
    SERIES_IDS,
    TICKETS_SOLD,
    VISITOR_ENTRIES,
    VISITOR_EVENTS,
    resolve_series,
    series_by_id,
)

AS_OF = "2026-07-01T04:00:00Z"
LATEST = Path("data") / "forecasts" / "latest"
TEST_ORIGINS = ("--origins", "3")


def _run(root: Path, *args: str) -> int:
    return main(["--root", str(root), *args])


# --- Rekisteri -------------------------------------------------------------


def test_the_default_series_is_the_one_the_tool_always_produced() -> None:
    """Changing this silently would move every existing output path."""
    assert DEFAULT_SERIES is VISITOR_EVENTS
    assert DEFAULT_SERIES.column == "visitors_total"
    assert SERIES_IDS[0] == "visitor_events"


def test_every_series_has_a_distinct_column() -> None:
    columns = {series.column for series in ALL_SERIES}
    assert len(columns) == len(ALL_SERIES)


def test_tickets_have_no_hourly_shape() -> None:
    """Ticket sales are recorded per day; an hourly spread would be invented."""
    assert TICKETS_SOLD.has_hourly is False
    assert VISITOR_EVENTS.has_hourly is True
    assert VISITOR_ENTRIES.has_hourly is True


def test_resolve_series_defaults_to_all_and_keeps_declaration_order() -> None:
    assert resolve_series(None) == ALL_SERIES
    assert resolve_series(("tickets_sold", "visitor_events")) == (VISITOR_EVENTS, TICKETS_SOLD)


def test_an_unknown_series_names_the_known_ones() -> None:
    with pytest.raises(KeyError, match="visitor_events"):
        series_by_id("ei-olemassa")


# --- Historia --------------------------------------------------------------


def test_history_reads_the_series_own_column(synthetic_repo: Path) -> None:
    """The target follows the series, and the raw columns stay beside it."""
    data = load_dataset(synthetic_repo)
    for series in ALL_SERIES:
        history = venue_history(data, 1, series=series)
        assert not history.empty, series.series_id
        assert (history[TARGET] == history[series.column]).all(), series.series_id


def test_the_three_series_are_not_rescalings_of_each_other(synthetic_repo: Path) -> None:
    """A pipeline reading the wrong column would still pass if they were proportional."""
    data = load_dataset(synthetic_repo)
    levels = {
        series.series_id: float(venue_history(data, 1, series=series)[TARGET].mean())
        for series in ALL_SERIES
    }
    assert levels["visitor_events"] > levels["visitor_entries"] > levels["tickets_sold"]
    # Entries are half the events by construction; tickets are not on that ratio at all.
    assert levels["visitor_entries"] == pytest.approx(levels["visitor_events"] / 2, rel=0.05)
    assert levels["tickets_sold"] < levels["visitor_events"] * 0.3


def test_training_frame_targets_the_chosen_series(synthetic_repo: Path) -> None:
    data = load_dataset(synthetic_repo)
    history = venue_history(data, 1, series=TICKETS_SOLD)
    origin = history["date"].max().date()
    training = build_training_frame(history, origin)
    assert (training[TARGET] == training["tickets_sold"]).all()
    assert training[TARGET].notna().all()


def test_a_missing_ticket_table_does_not_break_the_visitor_series(synthetic_repo: Path) -> None:
    """A repository with no hand-maintained ticket file is ordinary, not broken."""
    (synthetic_repo / "data" / "processed" / "tickets_daily.csv").unlink()
    data = load_dataset(synthetic_repo)
    assert data.tickets_daily.empty
    assert not venue_history(data, 1, series=VISITOR_EVENTS).empty
    assert venue_history(data, 1, series=TICKETS_SOLD).empty


# --- Ajo ja tiedostot ------------------------------------------------------


@pytest.fixture(scope="module")
def all_series_run(synthetic_repo_module: Path) -> Path:
    assert _run(synthetic_repo_module, "run", "--as-of", AS_OF, "--no-archive", *TEST_ORIGINS) == 0
    return synthetic_repo_module


def test_every_series_writes_its_own_directory(all_series_run: Path) -> None:
    """The default series keeps the original path; the others sit beneath it."""
    base = all_series_run / LATEST / "venue_1"
    assert (base / "daily_30d.csv").is_file()
    assert (base / "visitor_entries" / "daily_30d.csv").is_file()
    assert (base / "tickets_sold" / "daily_30d.csv").is_file()


def test_the_ticket_series_writes_no_hourly_file(all_series_run: Path) -> None:
    """Absent says "no hourly shape"; empty would invite reading it as zero."""
    base = all_series_run / LATEST / "venue_1"
    assert (base / "hourly_7d.csv").is_file()
    assert (base / "visitor_entries" / "hourly_7d.csv").is_file()
    assert not (base / "tickets_sold" / "hourly_7d.csv").exists()


def test_each_series_forecasts_its_own_level(all_series_run: Path) -> None:
    """The separating test: three forecasts of three different sizes, in the right order."""
    medians = {}
    for series_id in SERIES_IDS:
        base = all_series_run / LATEST / "venue_1"
        path = base / "daily_30d.csv" if series_id == "visitor_events" else base / series_id / "daily_30d.csv"
        frame = pd.read_csv(path)
        medians[series_id] = float(frame["p50"].median())
    assert medians["visitor_events"] > medians["visitor_entries"] > medians["tickets_sold"]
    assert medians["visitor_entries"] == pytest.approx(medians["visitor_events"] / 2, rel=0.2)


def test_metrics_name_the_series_and_its_source(all_series_run: Path) -> None:
    payload = json.loads(
        (all_series_run / LATEST / "venue_1" / "tickets_sold" / "metrics.json").read_text()
    )
    assert payload["series"] == "tickets_sold"
    assert payload["series_source"] == "tickets_daily.tickets_sold"
    assert payload["series_label"]["fi"] and payload["series_label"]["en"]
    assert payload["series_label"]["fi"] != payload["series_label"]["en"]


def test_the_default_series_metrics_keep_their_original_place(all_series_run: Path) -> None:
    """The web build and the archives read this path and must keep reading it."""
    payload = json.loads((all_series_run / LATEST / "venue_1" / "metrics.json").read_text())
    assert payload["series"] == "visitor_events"
    assert payload["venue_id"] == 1


def test_run_can_be_limited_to_one_series(synthetic_repo: Path) -> None:
    assert (
        _run(
            synthetic_repo,
            "run",
            "--as-of",
            AS_OF,
            "--no-archive",
            "--series",
            "tickets_sold",
            "--venue",
            "1",
            *TEST_ORIGINS,
        )
        == 0
    )
    base = synthetic_repo / LATEST / "venue_1"
    assert (base / "tickets_sold" / "daily_30d.csv").is_file()
    assert not (base / "visitor_entries").exists()
    manifest = json.loads((synthetic_repo / LATEST / "manifest.json").read_text())
    assert manifest["series"] == ["tickets_sold"]
