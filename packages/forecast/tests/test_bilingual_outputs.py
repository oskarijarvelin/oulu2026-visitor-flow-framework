"""Every run writes its prose twice, and the command prints the language it was asked for.

The point of these is not that a translation exists somewhere in the package — the string
tables are checked in ``test_report_strings.py`` — but that a run actually emits both, that
the two files are genuinely different documents, and that the numbers in them agree. A
second language that quietly rendered the first one's text would pass every parity test and
still be useless.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovf_forecast.cli import EXIT_OK, main
from ovf_forecast.evaluation.store import evaluations_root
from ovf_forecast.evaluation.store import read_index as read_evaluation_index
from ovf_forecast.quiet.store import quiet_root
from ovf_forecast.quiet.store import read_index as read_quiet_index

FAST_QUIET = ["--simulations", "300"]
FAST_EVAL = ["--resamples", "300", "--models", "baseline"]


def _run(root: Path, *arguments: str) -> int:
    """Invoke the CLI against one repository root."""
    return main(["--log-level", "error", "--root", str(root), *arguments])


def _evaluation_dir(root: Path) -> Path:
    runs = read_evaluation_index(root)["runs"]
    assert runs, "the evaluation wrote nothing"
    return evaluations_root(root) / str(runs[0]["run_id"])


def _quiet_dir(root: Path) -> Path:
    runs = read_quiet_index(root)["runs"]
    assert runs, "the quiet run wrote nothing"
    return quiet_root(root) / str(runs[0]["run_id"])


def _both_reports(directory: Path) -> tuple[str, str]:
    """The two rendered reports of one run."""
    finnish = (directory / "report.md").read_text(encoding="utf-8")
    english = (directory / "report.en.md").read_text(encoding="utf-8")
    return finnish, english


# --------------------------------------------------------------------------------------
# Evaluation
# --------------------------------------------------------------------------------------


def test_an_evaluation_writes_both_reports(synthetic_repo: Path) -> None:
    """``report.md`` keeps its path; the second language sits beside it."""
    assert _run(synthetic_repo, "evaluate", "--test", "2026-05", *FAST_EVAL) == EXIT_OK
    finnish, english = _both_reports(_evaluation_dir(synthetic_repo))
    assert finnish.startswith("# Ennusteen arviointiraportti")
    assert english.startswith("# Forecast evaluation report")
    assert "## 8. Rajoitteet" in finnish
    assert "## 8. Limitations" in english


def test_both_evaluation_reports_carry_the_same_numbers(synthetic_repo: Path) -> None:
    """A translation may reorder a sentence; it may not change a measurement.

    The two documents are compared on the MAE table of section 4, where the Finnish decimal
    comma is the only difference the language is allowed to make.
    """
    assert _run(synthetic_repo, "evaluate", "--test", "2026-05", *FAST_EVAL) == EXIT_OK
    finnish, english = _both_reports(_evaluation_dir(synthetic_repo))
    assert _mae_cells(finnish, comma=True) == _mae_cells(english, comma=False)


def _mae_cells(report: str, *, comma: bool) -> list[str]:
    """The MAE column of the daily metrics table, normalised to a dot decimal."""
    rows = [line for line in report.splitlines() if line.startswith("| baseline | 1-7 |")]
    cells = [row.split("|")[3].strip() for row in rows]
    return [cell.replace(",", ".") if comma else cell for cell in cells]


def test_the_stored_verdict_exists_in_both_languages(synthetic_repo: Path) -> None:
    """``verdicts.json`` is what the site reads; it may not carry only one language."""
    assert _run(synthetic_repo, "evaluate", "--test", "2026-05", *FAST_EVAL) == EXIT_OK
    verdicts = json.loads((_evaluation_dir(synthetic_repo) / "verdicts.json").read_text())
    assert verdicts["summary_fi"] and verdicts["summary_en"]
    assert verdicts["summary_fi"] != verdicts["summary_en"]
    assert "Ikkuna" in verdicts["summary_fi"]
    assert "Window" in verdicts["summary_en"]


def test_the_worst_days_carry_their_cause_in_both_languages(synthetic_repo: Path) -> None:
    """The most useful section of the report is the one a reader has to understand."""
    assert _run(synthetic_repo, "evaluate", "--test", "2026-05", *FAST_EVAL) == EXIT_OK
    metrics = json.loads((_evaluation_dir(synthetic_repo) / "metrics.json").read_text())
    days = [day for venue in metrics["venues"] for rows in venue["worst_days"].values() for day in rows]
    assert days, "the window produced no worst days"
    for day in days:
        assert set(day["note"]) == {"fi", "en"}
        assert set(day["weekday"]) == {"fi", "en"}


def test_the_command_prints_the_language_it_was_asked_for(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The verdict is what somebody reads at the moment they run it."""
    assert _run(synthetic_repo, "evaluate", "--test", "2026-05", "--lang", "en", *FAST_EVAL) == EXIT_OK
    printed = capsys.readouterr().out
    assert "Window 2026-05-01" in printed
    assert "saved:" in printed
    assert "Ikkuna" not in printed


def test_a_stored_report_can_be_printed_in_either_language(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``evaluate report`` reads the file the run already wrote, not a new rendering."""
    assert _run(synthetic_repo, "evaluate", "--test", "2026-05", *FAST_EVAL) == EXIT_OK
    capsys.readouterr()
    run_id = str(read_evaluation_index(synthetic_repo)["runs"][0]["run_id"])
    assert _run(synthetic_repo, "evaluate", "report", "--id", run_id, "--lang", "en") == EXIT_OK
    assert "# Forecast evaluation report" in capsys.readouterr().out
    assert _run(synthetic_repo, "evaluate", "report", "--id", run_id) == EXIT_OK
    assert "# Ennusteen arviointiraportti" in capsys.readouterr().out


# --------------------------------------------------------------------------------------
# Quiet days
# --------------------------------------------------------------------------------------


def test_a_quiet_forecast_writes_both_reports(synthetic_repo: Path) -> None:
    """The dates are the answer, and both readers get them with the same caveats."""
    assert _run(synthetic_repo, "quiet", "--venue", "1", *FAST_QUIET) == EXIT_OK
    finnish, english = _both_reports(_quiet_dir(synthetic_repo))
    assert finnish.startswith("# Kuukauden hiljaisimmat päivät: heinäkuu 2026")
    assert english.startswith("# The quietest days of the month: July 2026")
    assert "## 4. Mitä tämä ei kerro" in finnish
    assert "## 4. What this does not say" in english


def test_a_quiet_forecast_names_the_same_days_in_both_languages(synthetic_repo: Path) -> None:
    """``ma 6.7.`` and ``Mon 6 Jul`` have to be the same day, not two different answers."""
    assert _run(synthetic_repo, "quiet", "--venue", "1", *FAST_QUIET) == EXIT_OK
    metrics = json.loads((_quiet_dir(synthetic_repo) / "metrics.json").read_text())
    dates = metrics["venues"][0]["quiet_set"]["dates"]
    finnish, english = _both_reports(_quiet_dir(synthetic_repo))
    for iso in dates:
        year, month, day = (int(part) for part in iso.split("-"))
        assert f"{day}.{month}." in finnish, f"{iso} is missing from the Finnish report"
        assert f"{day} Jul" in english, f"{iso} is missing from the English report"
    assert year == 2026


def test_a_quiet_warning_reaches_both_readers(synthetic_repo: Path) -> None:
    """A caveat that only half the readers see is worse than no caveat."""
    assert _run(synthetic_repo, "quiet", "--venue", "1", *FAST_QUIET) == EXIT_OK
    metrics = json.loads((_quiet_dir(synthetic_repo) / "metrics.json").read_text())
    warnings = metrics["venues"][0]["warnings"]
    assert warnings, "the synthetic month produced no warnings to check"
    for warning in warnings:
        assert set(warning) == {"fi", "en"}
        assert warning["fi"] and warning["en"]


def test_a_quiet_sweep_writes_both_reports(synthetic_repo: Path) -> None:
    """The measurement the forecast quotes is the one that decides whether to believe it."""
    assert (
        _run(
            synthetic_repo,
            "quiet",
            "backtest",
            "--venue",
            "1",
            "--models",
            "quiet_calendar",
            "--simulations",
            "200",
            "--resamples",
            "200",
        )
        == EXIT_OK
    )
    finnish, english = _both_reports(_quiet_dir(synthetic_repo))
    assert "## 6. Mitä tämä ei todista" in finnish
    assert "## 6. What this does not prove" in english


# --------------------------------------------------------------------------------------
# The forecast run itself
# --------------------------------------------------------------------------------------


def test_the_forecast_caveats_are_stored_in_both_languages(synthetic_repo: Path) -> None:
    """The site renders these; before this they were English with a regex guessing Finnish."""
    assert _run(synthetic_repo, "run", "--model", "baseline", "--origins", "3", "--no-archive") == EXIT_OK
    metrics = json.loads(
        (synthetic_repo / "data" / "forecasts" / "latest" / "venue_1" / "metrics.json").read_text()
    )
    assert metrics["do_not_trust"], "a run always carries the static caveats"
    for caveat in metrics["do_not_trust"]:
        assert set(caveat) == {"fi", "en"}
        assert caveat["fi"] != caveat["en"]
    for warning in metrics["warnings"]:
        assert set(warning) == {"fi", "en"}
