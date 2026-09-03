"""Storage, run ids and the determinism they exist to make testable.

Two runs of the same evaluation on the same data have to write the same bytes. That is
not a nicety: without it, nobody can tell whether a changed report means the model
changed or the run did. The creation time is the one value that varies, and it lives in
``index.json``, which is a registry rather than a result.
"""

from __future__ import annotations

import filecmp
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ovf_forecast.dataset import load_dataset
from ovf_forecast.evaluation import evaluate
from ovf_forecast.evaluation.runner import WEATHER_CLIMATOLOGY, WEATHER_OPERATIONAL, EvaluationConfig
from ovf_forecast.evaluation.store import (
    CONFIG_NAME,
    METRICS_NAME,
    PREDICTIONS_NAME,
    VERDICTS_NAME,
    build_run_id,
    build_sweep_id,
    clean,
    evaluations_root,
    list_runs,
    load_run,
    read_index,
    report_name,
    run_dir,
)
from ovf_forecast.evaluation.windows import Window, make_window

RUN_FILES = (
    CONFIG_NAME,
    PREDICTIONS_NAME,
    METRICS_NAME,
    VERDICTS_NAME,
    report_name("fi"),
    report_name("en"),
)
MOMENT = datetime(2026, 8, 25, 12, 0, tzinfo=UTC)


@pytest.fixture
def window() -> Window:
    """A short window, so the tests that run it stay cheap."""
    return make_window(train_end="2026-04-30", test="2026-05-01:2026-05-14")


@pytest.fixture
def config() -> EvaluationConfig:
    """One model, one weather mode, few resamples: this file tests files, not statistics."""
    return EvaluationConfig(
        models=("baseline",),
        weather_modes=(WEATHER_OPERATIONAL,),
        venues=(1,),
        n_resamples=200,
    )


def test_the_run_id_is_readable_and_deterministic(window: Window) -> None:
    """The id names the window and the models, and nothing else when nothing else varies."""
    config = EvaluationConfig(models=("baseline",))
    assert build_run_id(window, config) == "eval_v1_2026-04-30_2026-05-01_2026-05-14_baseline"
    assert build_run_id(window, config) == build_run_id(window, config)


def test_the_run_id_names_every_choice_that_changes_the_answer() -> None:
    """A venue subset, a sliding window, fewer weather modes and a fixed reference all
    have to reach the id, or two different runs would fight over one directory."""
    window = make_window(test="2026-04", train_window="120")
    config = EvaluationConfig(
        models=("baseline",),
        weather_modes=(WEATHER_CLIMATOLOGY,),
        venues=(2,),
        reference="seasonal_naive",
    )
    run_id = build_run_id(window, config)
    assert run_id.startswith("eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline")
    for fragment in ("_v2", "_tw120", "_wxclim", "_ref-seasonal_naive"):
        assert fragment in run_id


def test_a_sweep_id_spans_its_windows() -> None:
    """The pooled result gets its own readable directory."""
    windows = [
        make_window(test="2026-04"),
        make_window(test="2026-05"),
    ]
    sweep_id = build_sweep_id("monthly", windows, EvaluationConfig(models=("baseline",)))
    assert sweep_id == "eval_v1_sweep_monthly_2026-04-01_2026-05-31_baseline"


def test_two_runs_write_identical_files(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """The determinism criterion, checked on the bytes rather than on the numbers."""
    data = load_dataset(synthetic_repo)
    first = evaluate(data, [window], config, moment=MOMENT)
    assert first.produced_anything
    directory = run_dir(synthetic_repo, first.run_ids[0])
    snapshot = {name: (directory / name).read_bytes() for name in RUN_FILES}

    second = evaluate(load_dataset(synthetic_repo), [window], config, moment=MOMENT)
    assert second.run_ids == first.run_ids
    for name in RUN_FILES:
        assert (directory / name).read_bytes() == snapshot[name], f"{name} changed between runs"


def test_a_rerun_replaces_its_own_directory_instead_of_adding_one(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """Same parameters, same directory: the repository does not fill with near-duplicates."""
    data = load_dataset(synthetic_repo)
    evaluate(data, [window], config, moment=MOMENT)
    evaluate(load_dataset(synthetic_repo), [window], config, moment=MOMENT)
    directories = sorted(path.name for path in evaluations_root(synthetic_repo).iterdir() if path.is_dir())
    assert len(directories) == 1
    assert len(read_index(synthetic_repo)["runs"]) == 1


def test_every_stored_file_is_written(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """All five artefacts, and the predictions carry the columns the contract names."""
    data = load_dataset(synthetic_repo)
    result = evaluate(data, [window], config, moment=MOMENT)
    artifacts = load_run(synthetic_repo, result.run_ids[0])
    assert artifacts is not None
    for name in RUN_FILES:
        assert (run_dir(synthetic_repo, result.run_ids[0]) / name).is_file()
    assert list(artifacts.predictions.columns) == [
        "venue_id", "date", "horizon_days", "model", "weather_mode", "y_true", "p10", "p50", "p90",
    ]
    assert artifacts.report().startswith("# Ennusteen arviointiraportti")
    assert artifacts.report("en").startswith("# Forecast evaluation report")
    assert "MDE" in artifacts.report()


def test_the_index_records_the_window_the_models_and_the_verdict(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """``evaluate list`` reads this, so it has to hold what the listing shows."""
    data = load_dataset(synthetic_repo)
    result = evaluate(data, [window], config, moment=MOMENT)
    entries = list_runs(synthetic_repo)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["run_id"] == result.run_ids[0]
    assert entry["created_at"] == "2026-08-25T12:00:00Z"
    assert entry["window"]["test_start"] == "2026-05-01"
    assert entry["models"] == ["baseline"]
    assert entry["verdicts"][0]["reference"] in (
        "seasonal_naive", "moving_average_28d", "climatology_dow"
    )


def test_a_sweep_stores_every_window_and_a_pooled_run(
    synthetic_repo: Path, config: EvaluationConfig
) -> None:
    """Each window gets its own directory, and the pooled verdict gets one more."""
    windows = [
        make_window(train_end="2026-04-30", test="2026-05-01:2026-05-14"),
        make_window(train_end="2026-05-14", test="2026-05-15:2026-05-28"),
    ]
    data = load_dataset(synthetic_repo)
    result = evaluate(data, windows, config, sweep_kind="custom", moment=MOMENT)
    assert len(result.run_ids) == 2
    assert result.sweep_run_id is not None

    sweep = load_run(synthetic_repo, result.sweep_run_id)
    assert sweep is not None
    assert sweep.verdicts["kind"] == "sweep"
    assert [entry["run_id"] for entry in sweep.verdicts["windows"]] == result.run_ids
    assert "Koosteverdikti" in sweep.report()
    assert "Pooled verdict" in sweep.report("en")
    kinds = {entry["kind"] for entry in list_runs(synthetic_repo)}
    assert kinds == {"window", "sweep"}


def test_the_json_files_hold_no_nan(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """``NaN`` is not JSON. Anything unmeasurable is stored as null."""
    data = load_dataset(synthetic_repo)
    result = evaluate(data, [window], config, moment=MOMENT)
    directory = run_dir(synthetic_repo, result.run_ids[0])
    for name in (CONFIG_NAME, METRICS_NAME, VERDICTS_NAME):
        text = (directory / name).read_text(encoding="utf-8")
        assert "NaN" not in text
        assert "Infinity" not in text
        json.loads(text)


def test_clean_maps_missing_numbers_to_null() -> None:
    """The helper the JSON writer relies on."""
    assert clean({"a": float("nan"), "b": [1.0, float("inf")], "c": (1, 2)}) == {
        "a": None, "b": [1.0, None], "c": [1, 2]
    }


def test_loading_an_unknown_run_returns_nothing(synthetic_repo: Path) -> None:
    """``evaluate report --id typo`` has to fail cleanly."""
    assert load_run(synthetic_repo, "eval_v1_nope") is None
    assert read_index(synthetic_repo)["runs"] == []


def test_predictions_are_written_with_stable_formatting(
    synthetic_repo: Path, window: Window, config: EvaluationConfig
) -> None:
    """Fixed float formatting is what makes the byte comparison above possible."""
    data = load_dataset(synthetic_repo)
    result = evaluate(data, [window], config, moment=MOMENT)
    path = run_dir(synthetic_repo, result.run_ids[0]) / PREDICTIONS_NAME
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "venue_id,date,horizon_days,model,weather_mode,y_true,p10,p50,p90"
    assert all(len(field.split(".")[-1]) == 4 for field in lines[1].split(",")[-4:])
    assert filecmp.cmp(path, path, shallow=False)
