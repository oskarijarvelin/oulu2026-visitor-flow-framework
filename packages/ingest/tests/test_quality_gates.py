"""Quality gates: what makes them fire, and what they protect."""

from __future__ import annotations

from datetime import date, timedelta

import pandas as pd

from ovf_ingest.config import AppConfig
from ovf_ingest.normalize import build_visitors_daily, build_visitors_hourly, build_weather_hourly, tz_of
from ovf_ingest.validate import (
    TRAFFIC_HOURLY,
    VISITORS_DAILY,
    VISITORS_HOURLY,
    WEATHER_DAILY,
    WEATHER_HOURLY,
    GateResult,
    coverage_report,
    run_quality_gates,
)
from support import helsinki_midnight_utc

HELSINKI = tz_of("Europe/Helsinki")
FIRST = date(2026, 5, 1)
LAST = date(2026, 5, 20)


def _gate(results: list[GateResult], name: str) -> GateResult:
    return next(result for result in results if result.name == name)


def _visitor_tables(missing_hours: set[int], per_hour: float = 1.0) -> dict[str, pd.DataFrame]:
    """Visitor tables over 1-20 May with a chosen set of unanswered hour offsets."""
    midnight = helsinki_midnight_utc(FIRST)
    total_hours = (LAST - FIRST).days * 24 + 24
    observations = {
        1: {
            midnight + timedelta(hours=offset): (per_hour, per_hour)
            for offset in range(total_hours)
            if offset not in missing_hours
        }
    }
    hourly = build_visitors_hourly(observations, {1: (FIRST, LAST)}, HELSINKI)
    return {VISITORS_HOURLY: hourly, VISITORS_DAILY: build_visitors_daily(hourly)}


def _weather_table(coverage: float) -> pd.DataFrame:
    midnight = helsinki_midnight_utc(FIRST)
    total_hours = (LAST - FIRST).days * 24 + 24
    covered = int(total_hours * coverage)
    observations = {
        1: {
            midnight + timedelta(hours=offset): {
                "temperature_2m": 10.0,
                "precipitation": 0.0,
                "wind_speed_10m": 3.0,
                "relative_humidity_2m": 60,
                "weathercode": 0,
            }
            for offset in range(covered)
        }
    }
    return build_weather_hourly(observations, {1: {}}, {1: (FIRST, LAST)}, HELSINKI)


def test_a_short_visitor_gap_passes(config: AppConfig) -> None:
    tables = _visitor_tables(missing_hours=set(range(100, 140)))
    assert _gate(run_quality_gates(config, tables), "visitor_gap").passed is True


def test_a_gap_over_48_hours_fails(config: AppConfig) -> None:
    tables = _visitor_tables(missing_hours=set(range(100, 160)))
    gate = _gate(run_quality_gates(config, tables), "visitor_gap")
    assert gate.passed is False
    assert set(gate.tables) == {VISITORS_HOURLY, VISITORS_DAILY}


def test_a_long_gap_outside_the_lookback_is_ignored(config: AppConfig) -> None:
    """The gate only looks at the most recent 30 days."""
    first = date(2026, 1, 1)
    last = date(2026, 5, 20)
    midnight = helsinki_midnight_utc(first)
    total_hours = 3406
    observations = {
        1: {
            midnight + timedelta(hours=offset): (1.0, 1.0)
            for offset in range(total_hours)
            if not 100 <= offset < 400
        }
    }
    hourly = build_visitors_hourly(observations, {1: (first, last)}, HELSINKI)
    tables = {VISITORS_HOURLY: hourly, VISITORS_DAILY: build_visitors_daily(hourly)}
    assert _gate(run_quality_gates(config, tables), "visitor_gap").passed is True


def test_weather_coverage_below_99_percent_fails(config: AppConfig) -> None:
    tables = {WEATHER_HOURLY: _weather_table(0.95)}
    gate = _gate(run_quality_gates(config, tables), "weather_coverage")
    assert gate.passed is False
    assert set(gate.tables) == {WEATHER_HOURLY, WEATHER_DAILY}


def test_full_weather_coverage_passes(config: AppConfig) -> None:
    tables = {WEATHER_HOURLY: _weather_table(1.0)}
    assert _gate(run_quality_gates(config, tables), "weather_coverage").passed is True


def test_a_day_over_capacity_times_96_fails(config: AppConfig) -> None:
    """Venue 1 has capacity 160, so 15360 counted events in a day is a sensor fault."""
    tables = _visitor_tables(missing_hours=set(), per_hour=400.0)
    gate = _gate(run_quality_gates(config, tables), "daily_capacity")
    assert gate.passed is False
    assert all("15360" in detail for detail in gate.detail.values())


def test_a_plausible_day_passes_the_capacity_gate(config: AppConfig) -> None:
    tables = _visitor_tables(missing_hours=set(), per_hour=100.0)
    assert _gate(run_quality_gates(config, tables), "daily_capacity").passed is True


def test_negative_counters_fail_the_gate(config: AppConfig) -> None:
    tables = _visitor_tables(missing_hours=set())
    tables[VISITORS_HOURLY].loc[0, "visitors_in"] = -1
    gate = _gate(run_quality_gates(config, tables), "negative_counts")
    assert gate.passed is False
    assert VISITORS_HOURLY in gate.tables


def test_gates_pass_when_there_is_nothing_to_check(config: AppConfig) -> None:
    assert all(gate.passed for gate in run_quality_gates(config, {}))


def test_coverage_counts_unanswered_hours() -> None:
    tables = _visitor_tables(missing_hours={5, 6, 7})
    coverage = coverage_report(tables)
    assert coverage[VISITORS_HOURLY]["missing_hours"] == 3
    assert coverage[VISITORS_HOURLY]["first"] == "2026-04-30T21:00:00Z"
    assert coverage[VISITORS_HOURLY]["last"] == "2026-05-20T20:00:00Z"
    assert TRAFFIC_HOURLY not in coverage
