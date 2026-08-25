"""The command line, end to end on the synthetic repository.

Everything a person actually types: a single window, the two sweeps, the report and the
listing, and the shorthand forms. These are the slowest tests in the file set because
each one runs a real evaluation, so the bootstrap count is turned down and the windows
are short.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ovf_forecast.cli import EXIT_FAILED, EXIT_OK, main
from ovf_forecast.evaluation.store import evaluations_root, read_index

FAST = ["--resamples", "200"]


def _run(root: Path, *arguments: str) -> int:
    """Invoke the CLI against one repository root."""
    return main(["--log-level", "error", "--root", str(root), *arguments])


def test_a_single_window_runs_and_stores_a_report(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``evaluate --train-end ... --test ...``: the base case."""
    code = _run(
        synthetic_repo,
        "evaluate", "--train-end", "2026-04-30", "--test", "2026-05-01:2026-05-14",
        "--models", "baseline", "--venue", "1", *FAST,
    )
    assert code == EXIT_OK
    output = capsys.readouterr().out
    assert "MDE" in output or "erottanut" in output
    assert "tallennettu: data/evaluations/" in output
    runs = read_index(synthetic_repo)["runs"]
    assert len(runs) == 1
    assert runs[0]["kind"] == "window"


def test_the_verdict_paragraph_names_the_reference_and_the_power(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Acceptance criterion: the printed verdict always names the reference and the MDE,
    including when no difference was found."""
    _run(
        synthetic_repo, "evaluate", "--test", "2026-05-01:2026-05-14",
        "--models", "baseline", "--venue", "1", *FAST,
    )
    output = capsys.readouterr().out
    assert "päävertailukohta" in output
    assert "olisi erottanut vasta" in output
    assert any(name in output for name in ("climatology_dow", "seasonal_naive", "moving_average_28d"))


def test_the_month_shorthand_works(synthetic_repo: Path) -> None:
    """``--test 2026-05`` means origin 30 April and the whole of May."""
    arguments = ("evaluate", "--test", "2026-05", "--models", "baseline", "--venue", "1", *FAST)
    assert _run(synthetic_repo, *arguments) == EXIT_OK
    window = read_index(synthetic_repo)["runs"][0]["window"]
    assert window["origin"] == "2026-04-30"
    assert window["test_start"] == "2026-05-01"
    assert window["test_end"] == "2026-05-31"


def test_a_monthly_sweep_stores_every_window_and_a_pooled_verdict(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--sweep monthly --from --to``: one run per month plus the pooled one."""
    code = _run(
        synthetic_repo,
        "evaluate", "--sweep", "monthly", "--from", "2026-04", "--to", "2026-05",
        "--models", "baseline", "--venue", "1", "--weather", "operational", *FAST,
    )
    assert code == EXIT_OK
    assert "kooste:" in capsys.readouterr().out
    kinds = [entry["kind"] for entry in read_index(synthetic_repo)["runs"]]
    assert kinds.count("window") == 2
    assert kinds.count("sweep") == 1


def test_a_rolling_sweep_steps_by_the_requested_interval(synthetic_repo: Path) -> None:
    """``--sweep rolling --step --horizon``."""
    code = _run(
        synthetic_repo,
        "evaluate", "--sweep", "rolling", "--step", "14", "--horizon", "14",
        "--max-windows", "2", "--models", "baseline", "--venue", "1",
        "--weather", "operational", *FAST,
    )
    assert code == EXIT_OK
    windows = [entry for entry in read_index(synthetic_repo)["runs"] if entry["kind"] == "window"]
    origins = sorted(entry["window"]["origin"] for entry in windows)
    assert len(origins) == 2


def test_report_prints_a_stored_run(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``evaluate report --id`` reads back what was written."""
    _run(
        synthetic_repo, "evaluate", "--test", "2026-05-01:2026-05-14",
        "--models", "baseline", "--venue", "1", *FAST,
    )
    run_id = read_index(synthetic_repo)["runs"][0]["run_id"]
    capsys.readouterr()
    assert _run(synthetic_repo, "evaluate", "report", "--id", run_id) == EXIT_OK
    report = capsys.readouterr().out
    assert "# Ennusteen arviointiraportti" in report
    assert "## 8. Rajoitteet" in report
    assert "Pahiten menneet päivät" in report


def test_report_pooled_combines_stored_runs(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``evaluate report --pooled`` is the accumulate-over-time view."""
    for spec in ("2026-05-01:2026-05-14", "2026-05-15:2026-05-28"):
        _run(
            synthetic_repo, "evaluate", "--test", spec, "--models", "baseline", "--venue", "1", *FAST
        )
    capsys.readouterr()
    assert _run(synthetic_repo, "evaluate", "report", "--pooled") == EXIT_OK
    output = capsys.readouterr().out
    assert "kooste kaikista tallennetuista ajoista" in output
    assert "baseline" in output


def test_report_pooled_without_any_run_fails_cleanly(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A helpful message rather than a traceback."""
    assert _run(synthetic_repo, "evaluate", "report", "--pooled") == EXIT_FAILED
    assert "aja ensin" in capsys.readouterr().out


def test_list_shows_the_stored_runs(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``evaluate list``."""
    _run(
        synthetic_repo, "evaluate", "--test", "2026-05-01:2026-05-14",
        "--models", "baseline", "--venue", "1", *FAST,
    )
    capsys.readouterr()
    assert _run(synthetic_repo, "evaluate", "list") == EXIT_OK
    listing = capsys.readouterr().out
    assert "run_id" in listing
    assert "eval_v1_2026-04-30_2026-05-01_2026-05-14" in listing


def test_list_without_any_run_fails_cleanly(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Same again for the listing."""
    assert _run(synthetic_repo, "evaluate", "list") == EXIT_FAILED
    assert "ei tallennettuja" in capsys.readouterr().out


def test_a_window_with_a_gap_is_refused(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The leak-adjacent mistake fails before anything is computed."""
    code = _run(
        synthetic_repo, "evaluate", "--train-end", "2026-03-01",
        "--test", "2026-05-01:2026-05-14", "--models", "baseline",
    )
    assert code == EXIT_FAILED
    assert "virhe:" in capsys.readouterr().out


def test_evaluate_without_a_window_is_refused(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Neither ``--test`` nor ``--sweep`` means there is nothing to do."""
    assert _run(synthetic_repo, "evaluate", "--models", "baseline") == EXIT_FAILED
    assert "virhe:" in capsys.readouterr().out


def test_a_monthly_sweep_needs_both_ends(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``--sweep monthly`` without ``--from``/``--to`` says so."""
    assert _run(synthetic_repo, "evaluate", "--sweep", "monthly", "--from", "2026-04") == EXIT_FAILED
    assert "--from" in capsys.readouterr().out


def test_an_unknown_weather_mode_is_refused(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A typo in ``--weather`` fails instead of silently running two modes."""
    code = _run(
        synthetic_repo, "evaluate", "--test", "2026-05-01:2026-05-07",
        "--weather", "sunny", "--models", "baseline",
    )
    assert code == EXIT_FAILED
    assert "virhe:" in capsys.readouterr().out


def test_all_three_weather_modes_are_run_by_default(synthetic_repo: Path) -> None:
    """The three-mode bracket is the default, and the verdict comes from operational."""
    _run(
        synthetic_repo, "evaluate", "--test", "2026-05-01:2026-05-07",
        "--models", "baseline", "--venue", "1", *FAST,
    )
    run_id = read_index(synthetic_repo)["runs"][0]["run_id"]
    path = evaluations_root(synthetic_repo) / run_id / "config.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    assert config["weather_modes"] == ["perfect", "operational", "climatology"]
    assert config["primary_weather_mode"] == "operational"


def test_the_sliding_training_window_reaches_the_stored_config(synthetic_repo: Path) -> None:
    """``--train-window 120`` has to be recorded, because it changes the answer."""
    _run(
        synthetic_repo, "evaluate", "--test", "2026-05-01:2026-05-07", "--train-window", "120",
        "--models", "baseline", "--venue", "1", "--weather", "operational", *FAST,
    )
    entry = read_index(synthetic_repo)["runs"][0]
    assert entry["window"]["train_window"] == "120"
    assert "tw120" in entry["run_id"]
