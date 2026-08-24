"""End-to-end runs. Every invariant here is asserted on the files that were written."""

from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ovf_forecast.cli import main
from ovf_forecast.export import DAILY_COLUMNS, HOURLY_COLUMNS
from ovf_forecast.models.base import BASELINE, BENCHMARK_NAMES, PROPHET_XGB

AS_OF = "2026-07-01T04:00:00Z"
LATEST = Path("data") / "forecasts" / "latest"
STAMP_PATTERN = re.compile(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ")
VENUE_IDS = (1, 2)


# Three origins is enough to exercise every code path; the number of origins itself is
# asserted against the real data in test_acceptance.py.
TEST_ORIGINS = ("--origins", "3")


def _run(repo: Path, *args: str) -> int:
    return main(["--log-level", "error", "--root", str(repo), *args])


def _read_daily(repo: Path, venue_id: int) -> pd.DataFrame:
    return pd.read_csv(repo / LATEST / f"venue_{venue_id}" / "daily_30d.csv")


def _read_hourly(repo: Path, venue_id: int) -> pd.DataFrame:
    return pd.read_csv(repo / LATEST / f"venue_{venue_id}" / "hourly_7d.csv")


@pytest.fixture(scope="module")
def baseline_run(synthetic_repo_module: Path) -> Path:
    """One completed baseline-only run, shared by every assertion that only reads it."""
    assert _run(synthetic_repo_module, "run", "--model", BASELINE, "--as-of", AS_OF, *TEST_ORIGINS) == 0
    return synthetic_repo_module


def test_run_writes_every_promised_file(baseline_run: Path) -> None:
    """Chapter 4.3 of the plan lists five files; all of them have to appear."""
    assert (baseline_run / LATEST / "manifest.json").is_file()
    for venue_id in VENUE_IDS:
        venue = baseline_run / LATEST / f"venue_{venue_id}"
        assert (venue / "daily_30d.csv").is_file()
        assert (venue / "hourly_7d.csv").is_file()
        assert (venue / "metrics.json").is_file()
        assert (venue / "backtest.csv").is_file()


def test_run_archives_a_dated_copy(baseline_run: Path) -> None:
    """The archive holds the same structure as ``latest``."""
    archive = baseline_run / "data" / "forecasts" / "2026-07-01"
    assert (archive / "manifest.json").is_file()
    for venue_id in VENUE_IDS:
        assert (archive / f"venue_{venue_id}" / "daily_30d.csv").is_file()


def test_daily_schema_and_horizon(baseline_run: Path) -> None:
    """One row per model and forecast day, in the documented column order."""
    for venue_id in VENUE_IDS:
        daily = _read_daily(baseline_run, venue_id)
        assert list(daily.columns) == DAILY_COLUMNS
        assert len(daily) == 30
        assert sorted(daily["horizon_days"]) == list(range(1, 31))
        assert (daily["venue_id"] == venue_id).all()


def test_hourly_schema(baseline_run: Path) -> None:
    """The hourly file covers seven days and carries both timestamps."""
    for venue_id in VENUE_IDS:
        hourly = _read_hourly(baseline_run, venue_id)
        assert list(hourly.columns) == HOURLY_COLUMNS
        assert len(hourly) == 7 * 24
        assert hourly["ts_utc"].str.endswith("Z").all()
        assert hourly["ts_local"].str.contains(r"\+0[23]:00", regex=True).all()
        assert set(hourly["hour"]) <= set(range(24))


def test_hourly_forecasts_sum_to_the_daily_forecast(baseline_run: Path) -> None:
    """The invariant the reference implementation breaks: the parts add up.

    Checked on the exported files, at export precision, not on in-memory floats.
    """
    for venue_id in VENUE_IDS:
        daily = _read_daily(baseline_run, venue_id)
        hourly = _read_hourly(baseline_run, venue_id)
        hourly["horizon_days"] = ((hourly["horizon_hours"] - 1) // 24) + 1
        summed = hourly.groupby(["model", "horizon_days"], as_index=False)[["p10", "p50", "p90"]].sum()

        merged = summed.merge(daily, on=["model", "horizon_days"], suffixes=("_hourly", "_daily"))
        assert len(merged) == len(summed) > 0
        for column in ("p10", "p50", "p90"):
            difference = (merged[f"{column}_hourly"] - merged[f"{column}_daily"]).abs()
            assert difference.max() < 1e-6


def test_quantiles_are_ordered_and_non_negative(baseline_run: Path) -> None:
    """p10 <= p50 <= p90 and nothing below zero, in both files."""
    for venue_id in VENUE_IDS:
        for frame in (_read_daily(baseline_run, venue_id), _read_hourly(baseline_run, venue_id)):
            assert (frame["p10"] <= frame["p50"]).all()
            assert (frame["p50"] <= frame["p90"]).all()
            assert (frame[["p10", "p50", "p90"]] >= 0).all().all()


def test_weather_source_switches_to_climatology_after_day_16(baseline_run: Path) -> None:
    """Open-Meteo stops at 16 days, and the file says so on every later row."""
    for venue_id in VENUE_IDS:
        daily = _read_daily(baseline_run, venue_id)
        early = daily.loc[daily["horizon_days"] <= 16, "weather_source"]
        late = daily.loc[daily["horizon_days"] > 16, "weather_source"]
        assert set(early) == {"forecast"}
        assert set(late) == {"climatology"}


def test_metrics_report_the_benchmarks_next_to_the_model(baseline_run: Path) -> None:
    """A model is never reported without the naive rules it has to beat."""
    for venue_id in VENUE_IDS:
        payload = json.loads((baseline_run / LATEST / f"venue_{venue_id}" / "metrics.json").read_text())
        assert set(payload["metrics"]) == {BASELINE, *BENCHMARK_NAMES}
        assert payload["benchmarks"] == list(BENCHMARK_NAMES)
        assert payload["n_origins"] >= 1
        assert payload["coverage_method"] == "leave_one_origin_out"
        assert payload["do_not_trust"]
        comparison = payload["benchmark_comparison"][BASELINE]
        for entry in comparison.values():
            assert isinstance(entry[f"beats_{BENCHMARK_NAMES[0]}"], bool)


def test_backtest_file_carries_its_own_intervals(baseline_run: Path) -> None:
    """``backtest.csv`` lets the web section plot quality without recomputing it."""
    for venue_id in VENUE_IDS:
        frame = pd.read_csv(baseline_run / LATEST / f"venue_{venue_id}" / "backtest.csv")
        assert list(frame.columns) == [
            "model",
            "venue_id",
            "origin_date",
            "target_date",
            "horizon_days",
            "y_true",
            "y_pred",
            "p10",
            "p90",
        ]
        assert (frame["p10"] <= frame["p90"]).all()
        assert (pd.to_datetime(frame["target_date"]) > pd.to_datetime(frame["origin_date"])).all()


def test_two_runs_differ_only_in_the_timestamp(synthetic_repo: Path) -> None:
    """Same input, same bytes. ``generated_at`` is the one thing allowed to move."""
    args = ("run", "--model", BASELINE, "--no-archive", *TEST_ORIGINS)
    assert _run(synthetic_repo, *args, "--as-of", AS_OF) == 0
    first = {
        path.relative_to(synthetic_repo): path.read_text()
        for path in sorted((synthetic_repo / LATEST).rglob("*"))
        if path.is_file()
    }
    assert _run(synthetic_repo, *args, "--as-of", "2026-08-09T23:11:02Z") == 0
    second = {
        path.relative_to(synthetic_repo): path.read_text()
        for path in sorted((synthetic_repo / LATEST).rglob("*"))
        if path.is_file()
    }

    assert set(first) == set(second)
    for name, text in first.items():
        assert STAMP_PATTERN.sub("<stamp>", text) == STAMP_PATTERN.sub("<stamp>", second[name])
    assert first != second, "the timestamp itself must have changed"


def test_run_can_be_limited_to_one_venue_and_a_shorter_horizon(synthetic_repo: Path) -> None:
    """``--venue`` and ``--horizon-days`` do what they say."""
    assert _run(synthetic_repo, "run", "--model", BASELINE, "--venue", "1", "--horizon-days", "14",
                "--as-of", AS_OF, "--no-archive", *TEST_ORIGINS) == 0
    daily = _read_daily(synthetic_repo, 1)
    assert len(daily) == 14
    assert not (synthetic_repo / LATEST / "venue_2").exists()


def test_missing_prophet_leaves_a_usable_run(synthetic_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without the optional group the run still produces the baseline forecast."""
    import sys

    monkeypatch.delitem(sys.modules, "ovf_forecast.models.prophet_xgb", raising=False)
    monkeypatch.setitem(sys.modules, "prophet", None)

    assert _run(synthetic_repo, "run", "--as-of", AS_OF, "--no-archive", *TEST_ORIGINS) == 0
    daily = _read_daily(synthetic_repo, 1)
    assert set(daily["model"]) == {BASELINE}

    manifest = json.loads((synthetic_repo / LATEST / "manifest.json").read_text())
    assert manifest["skipped_models"] == [PROPHET_XGB]
    assert any("prophet_xgb" in warning for warning in manifest["warnings"])


def test_backtest_command_writes_nothing(synthetic_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``backtest`` validates and prints; it must not touch the forecast files."""
    assert _run(synthetic_repo, "backtest", "--model", BASELINE, *TEST_ORIGINS) == 0
    assert not (synthetic_repo / "data" / "forecasts").exists()
    printed = capsys.readouterr().out
    assert "MAE" in printed
    assert "seasonal_naive" in printed


def test_report_command_reads_the_last_run(baseline_run: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``report`` prints the stored metrics without recomputing anything."""
    assert _run(baseline_run, "report") == 0
    printed = capsys.readouterr().out
    assert "venue 1" in printed
    assert "cover80" in printed


def test_report_without_a_run_is_reported_not_crashed(
    synthetic_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A missing metrics file is a message, not a traceback."""
    assert _run(synthetic_repo, "report") == 2
    assert "no metrics yet" in capsys.readouterr().out


def test_manifest_records_the_run(baseline_run: Path) -> None:
    """The manifest is what the web build checks before it trusts the files."""
    manifest = json.loads((baseline_run / LATEST / "manifest.json").read_text())
    assert manifest["pipeline"] == "forecast"
    assert manifest["generated_at"] == AS_OF
    assert manifest["models"] == [BASELINE]
    assert [entry["venue_id"] for entry in manifest["venues"]] == list(VENUE_IDS)
    assert manifest["ingest"]["quality_gates"] == {"passed": True, "warnings": []}


def test_origin_is_the_last_observed_day(baseline_run: Path) -> None:
    """The forecast starts the day after the last observation, not the day after today."""
    payload = json.loads((baseline_run / LATEST / "venue_1" / "metrics.json").read_text())
    assert payload["origin_date"] == "2026-06-30"
    daily = _read_daily(baseline_run, 1)
    assert daily["date"].min() == "2026-07-01"
    assert date.fromisoformat(daily["date"].max()) == date(2026, 7, 30)
