"""The command line, end to end on the synthetic repository.

Everything a person actually types: the forecast, the sweep that measures it, the stored
report and the listing. The simulation and bootstrap counts are turned down, because what
these assert is the plumbing rather than the third decimal of a probability.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovf_forecast.cli import EXIT_FAILED, EXIT_OK, main
from ovf_forecast.quiet.store import quiet_root, read_index

FAST = ["--simulations", "300"]
FAST_SWEEP = [*FAST, "--resamples", "300"]


def _run(root: Path, *arguments: str) -> int:
    """Invoke the CLI against one repository root."""
    return main(["--log-level", "error", "--root", str(root), *arguments])


def _files(root: Path, run_id: str) -> set[str]:
    return {path.name for path in (quiet_root(root) / run_id).iterdir()}


def test_the_forecast_defaults_to_the_month_after_the_last_observation(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(synthetic_repo, "quiet", "--venue", "1", *FAST) == EXIT_OK
    output = capsys.readouterr().out
    assert "heinäkuu 2026" in output
    assert "tallennettu: data/quiet/" in output
    runs = read_index(synthetic_repo)["runs"]
    assert len(runs) == 1
    assert runs[0]["kind"] == "forecast"
    assert runs[0]["month"] == "2026-07"
    assert _files(synthetic_repo, runs[0]["run_id"]) == {
        "config.json",
        "days.csv",
        "metrics.json",
        "verdicts.json",
        "report.md",
    }


def test_an_explicit_month_can_be_asked_for(synthetic_repo: Path) -> None:
    assert _run(synthetic_repo, "quiet", "--month", "2026-05", "--venue", "1", *FAST) == EXIT_OK
    assert read_index(synthetic_repo)["runs"][0]["month"] == "2026-05"


def test_a_forecast_without_a_measurement_says_so(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The one thing a recommendation may never do is imply it has been validated."""
    _run(synthetic_repo, "quiet", "--venue", "1", *FAST)
    assert "luotettavuutta ei ole mitattu" in capsys.readouterr().out


def test_a_sweep_measures_the_rule_and_the_next_forecast_quotes_it(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(synthetic_repo, "quiet", "backtest", "--venue", "1", *FAST_SWEEP) == EXIT_OK
    sweep = capsys.readouterr().out
    assert "hyöty on todennettu" in sweep
    assert "satunnaisvalinta" in sweep

    assert _run(synthetic_repo, "quiet", "--venue", "1", *FAST) == EXIT_OK
    forecast = capsys.readouterr().out
    assert "Mitattu luotettavuus" in forecast
    kinds = {run["kind"] for run in read_index(synthetic_repo)["runs"]}
    assert kinds == {"forecast", "backtest"}


def test_a_sweep_stores_every_window_and_every_day(synthetic_repo: Path) -> None:
    _run(synthetic_repo, "quiet", "backtest", "--venue", "1", *FAST_SWEEP)
    entry = read_index(synthetic_repo)["runs"][0]
    assert entry["sweep_kind"] == "monthly"
    assert entry["n_windows"] == 3
    assert _files(synthetic_repo, entry["run_id"]) >= {"windows.csv", "days.csv", "report.md"}
    metrics = json.loads(
        (quiet_root(synthetic_repo) / entry["run_id"] / "metrics.json").read_text(encoding="utf-8")
    )
    assert len(metrics["window_results"]) == 3
    assert metrics["windows_overlap"] is False


def test_a_rolling_sweep_discloses_that_its_windows_overlap(synthetic_repo: Path) -> None:
    _run(
        synthetic_repo, "quiet", "backtest", "--sweep", "rolling", "--step", "14",
        "--horizon", "30", "--max-windows", "3", "--venue", "1", *FAST_SWEEP,
    )
    entry = read_index(synthetic_repo)["runs"][0]
    metrics = json.loads(
        (quiet_root(synthetic_repo) / entry["run_id"] / "metrics.json").read_text(encoding="utf-8")
    )
    assert metrics["windows_overlap"] is True


def test_two_identical_runs_write_identical_files(synthetic_repo: Path) -> None:
    """Nothing inside a run directory may carry a wall clock time."""
    _run(synthetic_repo, "quiet", "--venue", "1", *FAST)
    run_id = read_index(synthetic_repo)["runs"][0]["run_id"]
    directory = quiet_root(synthetic_repo) / run_id
    before = {path.name: path.read_bytes() for path in sorted(directory.iterdir())}
    _run(synthetic_repo, "quiet", "--venue", "1", *FAST)
    after = {path.name: path.read_bytes() for path in sorted(directory.iterdir())}
    assert before == after


def test_the_stored_report_can_be_printed_back(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _run(synthetic_repo, "quiet", "--venue", "1", *FAST)
    capsys.readouterr()
    assert _run(synthetic_repo, "quiet", "report", "--latest") == EXIT_OK
    assert "Kuukauden hiljaisimmat päivät" in capsys.readouterr().out
    assert _run(synthetic_repo, "quiet", "report", "--id", "no_such_run") == EXIT_FAILED


def test_the_listing_names_the_days_and_the_verdicts(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(synthetic_repo, "quiet", "list") == EXIT_FAILED
    capsys.readouterr()
    _run(synthetic_repo, "quiet", "backtest", "--venue", "1", *FAST_SWEEP)
    _run(synthetic_repo, "quiet", "--venue", "1", *FAST)
    capsys.readouterr()
    assert _run(synthetic_repo, "quiet", "list") == EXIT_OK
    listing = capsys.readouterr().out
    assert "forecast" in listing
    assert "backtest" in listing
    assert "2026-07-" in listing


def test_a_nonsense_threshold_is_refused(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert _run(synthetic_repo, "quiet", "--quiet-share", "1.5", *FAST) == EXIT_FAILED
    assert "virhe:" in capsys.readouterr().out
