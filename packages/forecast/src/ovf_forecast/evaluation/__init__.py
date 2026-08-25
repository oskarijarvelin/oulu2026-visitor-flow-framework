"""Systematic accuracy evaluation over arbitrary time windows.

Train on a period you choose, forecast a period you choose, compare against what
happened, and get told whether the difference from a reference forecast is real. Results
accumulate under ``data/evaluations/`` so model development can be followed over time
rather than re-argued each release.

The package is organised around one question per module: :mod:`.windows` defines what is
being evaluated, :mod:`.runner` produces the forecasts without leaking, :mod:`.baselines`
supplies the opponents, :mod:`.metrics` scores, :mod:`.significance` decides whether a
gap is real, :mod:`.totals` answers the period-total question separately from the daily
one, :mod:`.store` persists, and :mod:`.report` explains. This module is the conductor.

Read ``docs/EVALUATION.md`` for how to run it and, more importantly, for what may not be
concluded from a result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .. import log_event
from ..dataset import ProcessedData
from .baselines import BASELINE_NAMES, REFERENCE_CHOICES, resolve_reference
from .metrics import (
    BUCKET_ALL,
    ScoreTable,
    absolute_errors,
    coverage_counts,
    score_window,
    signed_errors,
    worst_days,
)
from .report import render_sweep_report, render_window_report
from .runner import (
    DEFAULT_WEATHER_MODE,
    PREDICTION_COLUMNS,
    WEATHER_MODES,
    EvaluationConfig,
    VenueWindowRun,
    evaluation_history,
    resolve_weather_modes,
    run_window,
)
from .significance import (
    VERDICT_BETTER,
    VERDICT_NO_DIFFERENCE,
    VERDICT_WORSE,
    Comparison,
    assess_calibration,
    compare,
    estimate_bias,
    holm_bonferroni,
    pool_windows,
)
from .store import (
    SCHEMA_VERSION,
    RunArtifacts,
    build_run_id,
    build_sweep_id,
    list_runs,
    load_run,
    load_window_runs,
    update_index,
    write_run,
)
from .totals import estimate_total
from .windows import (
    TRAIN_WINDOW_ALL,
    Window,
    WindowError,
    make_window,
    monthly_sweep,
    rolling_sweep,
)

__all__ = [
    "BASELINE_NAMES",
    "DEFAULT_WEATHER_MODE",
    "REFERENCE_CHOICES",
    "TRAIN_WINDOW_ALL",
    "WEATHER_MODES",
    "EvaluationConfig",
    "EvaluationResult",
    "Window",
    "WindowError",
    "evaluate",
    "list_runs",
    "load_run",
    "make_window",
    "monthly_sweep",
    "pooled_report",
    "resolve_weather_modes",
    "rolling_sweep",
]

WEEKDAY_NAMES_FI = ("maanantai", "tiistai", "keskiviikko", "torstai", "perjantai", "lauantai", "sunnuntai")
HEAVY_RAIN_MM = 5.0
WORST_DAY_LIMIT = 5


@dataclass
class EvaluationResult:
    """What one invocation produced: the runs it wrote and what it concluded."""

    run_ids: list[str] = field(default_factory=list)
    sweep_run_id: str | None = None
    summary: str = ""
    failed_venues: list[int] = field(default_factory=list)

    @property
    def produced_anything(self) -> bool:
        """Whether at least one window was evaluated."""
        return bool(self.run_ids)


# --------------------------------------------------------------------------------------
# Top level
# --------------------------------------------------------------------------------------


def evaluate(
    data: ProcessedData,
    windows: list[Window],
    config: EvaluationConfig,
    *,
    sweep_kind: str | None = None,
    moment: datetime | None = None,
) -> EvaluationResult:
    """Run every window, store each one, and pool them when there is more than one."""
    venues = data.select_venues(config.venues)
    result = EvaluationResult()
    executed: list[ExecutedWindow] = []
    last_summary = ""
    for window in windows:
        runs: list[VenueWindowRun] = []
        for venue in venues:
            run = run_window(data, venue, window, config)
            if run is None:
                result.failed_venues.append(venue.venue_id)
                continue
            runs.append(run)
        if not runs:
            log_event("error", "evaluation", "No venue could be evaluated", window=window.label)
            continue
        run_id = build_run_id(window, config)
        assessments = [_assess(run, config) for run in runs]
        artifacts = _window_artifacts(run_id, window, config, assessments)
        last_summary = str(artifacts.verdicts.get("summary_fi", ""))
        write_run(data.root, artifacts)
        update_index(data.root, _index_entry(artifacts, window, config, kind="window"), moment=moment)
        executed.append(ExecutedWindow(window=window, run_id=run_id, assessments=assessments))
        result.run_ids.append(run_id)
    if not executed:
        return result
    if len(executed) > 1 or sweep_kind:
        sweep = _sweep_artifacts(sweep_kind or "custom", executed, config)
        write_run(data.root, sweep)
        update_index(
            data.root,
            _index_entry(sweep, executed[0].window, config, kind="sweep"),
            moment=moment,
        )
        result.sweep_run_id = sweep.run_id
        result.summary = str(sweep.verdicts.get("summary_fi", ""))
    else:
        result.summary = last_summary
    return result


# --------------------------------------------------------------------------------------
# Assessing one window
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class ExecutedWindow:
    """One window that has been run and scored, ready to be pooled without redoing it."""

    window: Window
    run_id: str
    assessments: list[VenueAssessment]


@dataclass
class VenueAssessment:
    """Everything concluded about one venue in one window."""

    run: VenueWindowRun
    scores: ScoreTable
    reference: str
    baseline_mae: dict[str, float]
    comparisons: dict[str, Comparison]
    differences: dict[str, np.ndarray]
    payload_models: list[dict[str, Any]] = field(default_factory=list)
    totals: list[dict[str, Any]] = field(default_factory=list)
    worst: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    sensitivity: dict[str, dict[str, float]] = field(default_factory=dict)


def _assess(run: VenueWindowRun, config: EvaluationConfig) -> VenueAssessment:
    """Score one venue's window and compare every model to the reference baseline."""
    scores = score_window(run.predictions, run.mase_denominator)
    primary = config.primary_weather_mode
    mae_by_model = scores.mae_by_model(primary, BUCKET_ALL)
    baseline_mae = {name: mae_by_model[name] for name in BASELINE_NAMES if name in mae_by_model}
    reference = resolve_reference(config.reference, baseline_mae)
    model_names = [name for name in scores.models(primary) if name not in BASELINE_NAMES]

    reference_errors = absolute_errors(run.predictions, primary, reference)
    comparisons: dict[str, Comparison] = {}
    differences: dict[str, np.ndarray] = {}
    for model in model_names:
        model_errors = absolute_errors(run.predictions, primary, model)
        comparisons[model] = compare(
            model_errors,
            reference_errors,
            model=model,
            reference=reference,
            n_resamples=config.n_resamples,
            seed=config.seed,
        )
        differences[model] = model_errors - reference_errors

    assessment = VenueAssessment(
        run=run,
        scores=scores,
        reference=reference,
        baseline_mae=baseline_mae,
        comparisons=comparisons,
        differences=differences,
    )
    assessment.totals = _totals_payload(run, scores, config)
    assessment.worst = {
        model: _worst_days_payload(run, primary, model) for model in model_names
    }
    assessment.sensitivity = {
        model: _sensitivity(scores, model, config) for model in model_names
    }
    return assessment


def _totals_payload(
    run: VenueWindowRun, scores: ScoreTable, config: EvaluationConfig
) -> list[dict[str, Any]]:
    """Period totals for every model in every weather mode."""
    payload: list[dict[str, Any]] = []
    for mode in config.weather_modes:
        for model in scores.models(mode):
            rows = run.predictions.loc[
                (run.predictions["weather_mode"] == mode) & (run.predictions["model"] == model)
            ].sort_values("date")
            if rows.empty:
                continue
            estimate = estimate_total(
                model=model,
                weather_mode=mode,
                daily_p50=rows["p50"].to_numpy(dtype="float64"),
                daily_p10=rows["p10"].to_numpy(dtype="float64"),
                daily_p90=rows["p90"].to_numpy(dtype="float64"),
                actual=rows["y_true"].to_numpy(dtype="float64"),
                ratios=run.ratios.get((mode, model), np.zeros(0)),
                n_resamples=config.n_resamples,
                seed=config.seed,
            )
            payload.append(estimate.to_dict())
    return payload


def _sensitivity(scores: ScoreTable, model: str, config: EvaluationConfig) -> dict[str, float]:
    """How much of a model's accuracy rests on knowing the weather."""
    values: dict[str, float] = {}
    for mode in WEATHER_MODES:
        score = scores.get(mode, model, BUCKET_ALL) if mode in config.weather_modes else None
        values[mode] = score.mae if score else float("nan")
    perfect, climatology = values.get("perfect", float("nan")), values.get("climatology", float("nan"))
    gap = climatology - perfect
    values["gap"] = gap
    usable = bool(np.isfinite(climatology)) and climatology > 0
    values["gap_pct"] = gap / climatology * 100.0 if usable else float("nan")
    return values


def _worst_days_payload(run: VenueWindowRun, mode: str, model: str) -> list[dict[str, Any]]:
    """The five biggest misses, annotated with whatever might explain them."""
    rows = worst_days(run.predictions, mode, model, limit=WORST_DAY_LIMIT)
    context = _context_by_day(run.context)
    payload: list[dict[str, Any]] = []
    for record in rows.to_dict(orient="records"):
        day = str(record["date"])
        facts = context.get(day, {})
        weekday = date.fromisoformat(day).weekday()
        y_true, horizon = float(record["y_true"]), int(record["horizon_days"])
        payload.append(
            {
                "date": day,
                "weekday": WEEKDAY_NAMES_FI[weekday],
                "y_true": y_true,
                "p50": float(record["p50"]),
                "error": float(record["error"]),
                "abs_error": float(record["abs_error"]),
                "horizon_days": horizon,
                "note": _explain_day(facts, y_true, weekday, horizon),
            }
        )
    return payload


def _context_by_day(context: pd.DataFrame) -> dict[str, dict[str, Any]]:
    """The day context keyed by ISO date, as plain dicts."""
    if context.empty:
        return {}
    return {
        str(row["date"]): {str(key): value for key, value in row.items()}
        for row in context.to_dict(orient="records")
    }


def _explain_day(facts: dict[str, Any], y_true: float, weekday: int, horizon: int) -> str:
    """A short, honest guess at why one day went wrong."""
    reasons: list[str] = []
    holiday = facts.get("holiday_name")
    if holiday is not None and not pd.isna(holiday) and str(holiday).strip():
        reasons.append(f"pyhäpäivä: {holiday}")
    precipitation = _as_float(facts.get("precip_sum"))
    if np.isfinite(precipitation) and precipitation >= HEAVY_RAIN_MM:
        reasons.append(f"runsas sade {precipitation:.1f} mm")
    if y_true == 0.0:
        reasons.append("toteuma 0, venue todennäköisesti kiinni")
    if str(facts.get("model_weather_source")) == "climatology":
        reasons.append(f"malli sai klimatologiasään (horisontti {horizon} vrk)")
    if weekday >= 5:
        reasons.append("viikonloppu")
    if not reasons:
        reasons.append("ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne")
    return "; ".join(reasons)


# --------------------------------------------------------------------------------------
# Payloads for one window run
# --------------------------------------------------------------------------------------


def _window_artifacts(
    run_id: str, window: Window, config: EvaluationConfig, assessments: list[VenueAssessment]
) -> RunArtifacts:
    """Render one window's assessments into the five files it is stored as."""
    raw_p_values = [
        assessment.comparisons[model].dm_p_value
        for assessment in assessments
        for model in assessment.comparisons
    ]
    adjusted = holm_bonferroni(raw_p_values)
    family_size = len([value for value in raw_p_values if np.isfinite(value)])

    cursor = 0
    metrics_venues: list[dict[str, Any]] = []
    verdict_venues: list[dict[str, Any]] = []
    for assessment in assessments:
        models_payload: list[dict[str, Any]] = []
        for model, comparison in assessment.comparisons.items():
            models_payload.append(
                _model_verdict(assessment, model, comparison, raw_p_values[cursor], adjusted[cursor], config)
            )
            cursor += 1
        metrics_venues.append(_venue_metrics(assessment))
        verdict_venues.append(
            {
                "venue_id": assessment.run.venue_id,
                "venue_name": assessment.run.venue_name,
                "reference": assessment.reference,
                "baseline_mae": {name: round(value, 3) for name, value in assessment.baseline_mae.items()},
                "family_size": family_size,
                "models": models_payload,
            }
        )

    summary = _window_summary(window, config, verdict_venues)
    metrics_payload = {
        "kind": "window",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window": window.to_dict(),
        "venues": metrics_venues,
    }
    verdicts_payload = {
        "kind": "window",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window": window.to_dict(),
        "primary_weather_mode": config.primary_weather_mode,
        "reference_rule": config.reference,
        "family_size": family_size,
        "summary_fi": summary,
        "venues": verdict_venues,
    }
    config_payload = {
        "kind": "window",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "window": window.to_dict(),
        **config.to_dict(),
    }
    return RunArtifacts(
        run_id=run_id,
        config=config_payload,
        predictions=_stacked_predictions([item.run for item in assessments]),
        metrics=metrics_payload,
        verdicts=verdicts_payload,
        report=render_window_report(config_payload, metrics_payload, verdicts_payload),
    )


def _model_verdict(
    assessment: VenueAssessment,
    model: str,
    comparison: Comparison,
    raw_p_value: float,
    holm_p_value: float,
    config: EvaluationConfig,
) -> dict[str, Any]:
    """One model's verdict block: comparison, bias, calibration, total, weather gap."""
    primary = config.primary_weather_mode
    predictions = assessment.run.predictions
    errors = signed_errors(predictions, primary, model)
    actuals = predictions.loc[
        (predictions["weather_mode"] == primary) & (predictions["model"] == model)
    ].sort_values("date")["y_true"].to_numpy(dtype="float64")
    covered, n_covered = coverage_counts(predictions, primary, model)
    total = next(
        (
            row
            for row in assessment.totals
            if row.get("model") == model and row.get("weather_mode") == primary
        ),
        {},
    )
    return {
        "model": model,
        "comparison": comparison.to_dict(),
        "raw_p_value": None if not np.isfinite(raw_p_value) else round(float(raw_p_value), 5),
        "holm_p_value": None if not np.isfinite(holm_p_value) else round(float(holm_p_value), 5),
        "bias": estimate_bias(errors, actuals, n_resamples=config.n_resamples, seed=config.seed).to_dict(),
        "calibration": assess_calibration(covered, n_covered).to_dict(),
        "total": total,
        "weather_sensitivity": assessment.sensitivity.get(model, {}),
    }


def _venue_metrics(assessment: VenueAssessment) -> dict[str, Any]:
    """One venue's metrics block."""
    return {
        "venue_id": assessment.run.venue_id,
        "venue_name": assessment.run.venue_name,
        "diagnostics": assessment.run.diagnostics(),
        "reference": assessment.reference,
        "scores": assessment.scores.to_list(),
        "totals": assessment.totals,
        "worst_days": assessment.worst,
        "weather_sensitivity": assessment.sensitivity,
    }


def _stacked_predictions(runs: list[VenueWindowRun]) -> pd.DataFrame:
    """Every venue's predictions in one frame, in a stable order."""
    frames = [run.predictions for run in runs if not run.predictions.empty]
    if not frames:
        return pd.DataFrame()
    stacked = pd.concat(frames, ignore_index=True)
    return stacked.sort_values(["venue_id", "weather_mode", "model", "date"]).reset_index(drop=True)


# --------------------------------------------------------------------------------------
# The Finnish verdict paragraphs
# --------------------------------------------------------------------------------------


def _window_summary(window: Window, config: EvaluationConfig, venues: list[dict[str, Any]]) -> str:
    """One paragraph, in plain Finnish, that can be read without opening the report."""
    sentences = [
        f"Ikkuna {window.test_start.isoformat()}–{window.test_end.isoformat()} "
        f"({window.horizon_days} vrk), koulutus päättyy {window.origin.isoformat()}, "
        f"koulutusikkuna {window.train_window}, sään tila {config.primary_weather_mode}."
    ]
    for venue in venues:
        for entry in venue["models"]:
            sentences.append(_model_sentence(venue, entry))
    sentences.append(
        "Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan "
        "koosteesta."
    )
    return " ".join(sentences)


def _model_sentence(venue: dict[str, Any], entry: dict[str, Any]) -> str:
    """One sentence per model: how it did, against whom, and what that proves."""
    comparison = entry["comparison"]
    total = entry.get("total", {})
    model = entry["model"]
    reference = comparison["reference"]
    name = f"Venue {venue['venue_id']} ({venue['venue_name']})"
    model_mae, reference_mae = comparison["model_mae"], comparison["reference_mae"]
    verdict = comparison["verdict"]
    head = (
        f"{name}: malli {model} teki keskimäärin {_fi(model_mae)} kävijän päivävirheen, "
        f"päävertailukohta {reference} {_fi(reference_mae)}."
    )
    if verdict == VERDICT_BETTER:
        middle = (
            f" Malli on tilastollisesti parempi: ero {_fi_signed(comparison['mean_difference'])} "
            f"kävijää päivässä (95 % väli {_fi_signed(comparison['ci_low'])}…"
            f"{_fi_signed(comparison['ci_high'])}), taitopistemäärä "
            f"{_fi(comparison['skill_score'], 3)}."
        )
    elif verdict == VERDICT_WORSE:
        middle = (
            f" Malli häviää vertailukohdalle tilastollisesti: ero "
            f"{_fi_signed(comparison['mean_difference'])} kävijää päivässä (95 % väli "
            f"{_fi_signed(comparison['ci_low'])}…{_fi_signed(comparison['ci_high'])}). "
            f"Yksinkertainen sääntö {reference} on tällä ikkunalla parempi kuin malli."
        )
    else:
        middle = (
            f" Eroa ei havaittu: {_fi_signed(comparison['mean_difference'])} kävijää päivässä "
            f"(95 % väli {_fi_signed(comparison['ci_low'])}…{_fi_signed(comparison['ci_high'])})."
        )
    power = (
        f" Tämä otos ({comparison['n']} päivää) olisi erottanut vasta "
        f"{_fi(comparison['mde'])} kävijän eron, eli {_fi(comparison['mde_pct'])} % "
        f"vertailukohdan MAE:sta"
    )
    power += (
        "; \"ei eroa\" ei siis tarkoita samanveroisuutta."
        if verdict == VERDICT_NO_DIFFERENCE
        else "."
    )
    tail = ""
    if total:
        tail = (
            f" Jakson kokonaismäärä: ennuste {_fi(total.get('predicted'), 0)}, toteuma "
            f"{_fi(total.get('actual'), 0)}, ero {_fi_signed(total.get('difference_pct'))} %, "
            f"80 % väli {_fi(total.get('p10'), 0)}–{_fi(total.get('p90'), 0)}."
        )
    return head + middle + power + tail


def _as_float(value: Any) -> float:
    """One context value as a float, with every missing marker mapping to NaN."""
    if value is None or (not isinstance(value, str) and pd.isna(value)):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _fi(value: Any, digits: int = 1) -> str:
    """A number with a decimal comma, for the Finnish prose."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "–"
    if numeric != numeric:
        return "–"
    return f"{numeric:,.{digits}f}".replace(",", " ").replace(".", ",")


def _fi_signed(value: Any, digits: int = 1) -> str:
    """A signed number with a decimal comma."""
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "–"
    if numeric != numeric:
        return "–"
    return ("+" if numeric >= 0 else "") + _fi(numeric, digits)


# --------------------------------------------------------------------------------------
# Pooling across windows
# --------------------------------------------------------------------------------------


def _sweep_artifacts(
    kind: str, executed: list[ExecutedWindow], config: EvaluationConfig
) -> RunArtifacts:
    """Pool the windows of a sweep into one verdict, with the per-window detail below it.

    The assessments are the ones the window runs already produced. Re-deriving them would
    give the same answer — the seed is fixed — but would pay for every bootstrap twice.
    """
    windows = [item.window for item in executed]
    run_id = build_sweep_id(kind, windows, config)
    per_venue: dict[int, list[tuple[Window, VenueAssessment]]] = {}
    for item in executed:
        for assessment in item.assessments:
            per_venue.setdefault(assessment.run.venue_id, []).append((item.window, assessment))

    raw_p_values = [
        assessment.comparisons[model].dm_p_value
        for entries in per_venue.values()
        for _, assessment in entries
        for model in assessment.comparisons
    ]
    adjusted = holm_bonferroni(raw_p_values)
    family_size = len([value for value in raw_p_values if np.isfinite(value)])

    cursor = 0
    verdict_venues: list[dict[str, Any]] = []
    metrics_venues: list[dict[str, Any]] = []
    for venue_id, entries in sorted(per_venue.items()):
        model_names = sorted({model for _, item in entries for model in item.comparisons})
        per_model: list[dict[str, Any]] = []
        window_rows: dict[str, list[dict[str, Any]]] = {model: [] for model in model_names}
        totals_rows: dict[str, list[dict[str, Any]]] = {model: [] for model in model_names}
        for window, assessment in entries:
            for model in sorted(assessment.comparisons):
                comparison = assessment.comparisons[model]
                window_rows[model].append(
                    {
                        "label": window.label,
                        "origin": window.origin.isoformat(),
                        "reference": comparison.reference,
                        "model_mae": round(comparison.model_mae, 3),
                        "reference_mae": round(comparison.reference_mae, 3),
                        "mean_difference": round(comparison.mean_difference, 3),
                        "ci_low": round(comparison.ci_low, 3),
                        "ci_high": round(comparison.ci_high, 3),
                        "verdict": comparison.verdict,
                        "mde": round(comparison.mde, 3),
                        "mde_pct": round(comparison.mde_pct, 2),
                        "raw_p_value": raw_p_values[cursor] if np.isfinite(raw_p_values[cursor]) else None,
                        "holm_p_value": adjusted[cursor] if np.isfinite(adjusted[cursor]) else None,
                    }
                )
                total = next(
                    (
                        row
                        for row in assessment.totals
                        if row.get("model") == model
                        and row.get("weather_mode") == config.primary_weather_mode
                    ),
                    {},
                )
                if total:
                    totals_rows[model].append({"label": window.label, **total})
                cursor += 1
        for model in model_names:
            differences = [
                item.differences[model] for _, item in entries if model in item.differences
            ]
            reference_errors = [
                absolute_errors(item.run.predictions, config.primary_weather_mode, item.reference)
                for _, item in entries
                if model in item.differences
            ]
            references = sorted({item.reference for _, item in entries if model in item.differences})
            pooled = pool_windows(
                differences,
                model=model,
                reference=references[0] if len(references) == 1 else "best-per-window",
                reference_absolute_errors=reference_errors,
                n_resamples=config.n_resamples,
                seed=config.seed,
            )
            per_model.append(
                {
                    "model": model,
                    "pooled": pooled.to_dict(),
                    "per_window": window_rows[model],
                    "totals": totals_rows[model],
                }
            )
        venue_name = entries[0][1].run.venue_name
        verdict_venues.append(
            {
                "venue_id": venue_id,
                "venue_name": venue_name,
                "models": per_model,
            }
        )
        metrics_venues.append(
            {
                "venue_id": venue_id,
                "venue_name": venue_name,
                "windows": [
                    {
                        "label": window.label,
                        "diagnostics": assessment.run.diagnostics(),
                        "scores": [
                            score
                            for score in assessment.scores.to_list()
                            if score["weather_mode"] == config.primary_weather_mode
                            and score["bucket"] == BUCKET_ALL
                        ],
                        "totals": [
                            total
                            for total in assessment.totals
                            if total["weather_mode"] == config.primary_weather_mode
                        ],
                    }
                    for window, assessment in entries
                ],
            }
        )

    summary = _sweep_summary(kind, windows, config, verdict_venues)
    window_payload = [
        {"run_id": item.run_id, **item.window.to_dict()} for item in executed
    ]
    verdicts_payload = {
        "kind": "sweep",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "sweep": kind,
        "first_day": windows[0].test_start.isoformat(),
        "last_day": windows[-1].test_end.isoformat(),
        "primary_weather_mode": config.primary_weather_mode,
        "reference_rule": config.reference,
        "family_size": family_size,
        "summary_fi": summary,
        "windows": window_payload,
        "venues": verdict_venues,
    }
    metrics_payload = {
        "kind": "sweep",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "sweep": kind,
        "windows": window_payload,
        "venues": metrics_venues,
    }
    config_payload = {
        "kind": "sweep",
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "sweep": kind,
        "windows": [window.to_dict() for window in windows],
        **config.to_dict(),
    }
    return RunArtifacts(
        run_id=run_id,
        config=config_payload,
        # A sweep owns no predictions of its own; they live in the member runs it names.
        # The file is still written, with its header, so every run directory has the same
        # five files and a reader never has to special-case one of them.
        predictions=pd.DataFrame(columns=PREDICTION_COLUMNS),
        metrics=metrics_payload,
        verdicts=verdicts_payload,
        report=render_sweep_report(config_payload, metrics_payload, verdicts_payload),
        members=[item.run_id for item in executed],
    )


def _sweep_summary(
    kind: str, windows: list[Window], config: EvaluationConfig, venues: list[dict[str, Any]]
) -> str:
    """The headline paragraph of a sweep: the pooled verdict, in plain Finnish."""
    sentences = [
        f"Kooste ({kind}): {len(windows)} ikkunaa, "
        f"{windows[0].test_start.isoformat()}–{windows[-1].test_end.isoformat()}, "
        f"sään tila {config.primary_weather_mode}, päävertailukohta {config.reference}."
    ]
    for venue in venues:
        for entry in venue["models"]:
            pooled = entry["pooled"]
            name = f"Venue {venue['venue_id']} ({venue['venue_name']})"
            head = (
                f"{name}: malli {pooled['model']} vastaan {pooled['reference']}, "
                f"{pooled['n_windows']} ikkunaa ({pooled['n_days']} päivää). "
                f"Malli oli parempi {pooled['windows_favouring']} ikkunassa ja huonompi "
                f"{pooled['windows_opposing']} ikkunassa."
            )
            if pooled["verdict"] == VERDICT_BETTER:
                body = (
                    f" Kooste puoltaa mallia: keskiero {_fi_signed(pooled['mean_difference'])} "
                    f"kävijää päivässä (95 % väli {_fi_signed(pooled['ci_low'])}…"
                    f"{_fi_signed(pooled['ci_high'])})."
                )
            elif pooled["verdict"] == VERDICT_WORSE:
                body = (
                    f" Kooste on mallia vastaan: malli häviää yksinkertaiselle vertailukohdalle, "
                    f"keskiero {_fi_signed(pooled['mean_difference'])} kävijää päivässä "
                    f"(95 % väli {_fi_signed(pooled['ci_low'])}…{_fi_signed(pooled['ci_high'])})."
                )
            else:
                body = (
                    f" Kooste ei erota malleja: keskiero {_fi_signed(pooled['mean_difference'])} "
                    f"kävijää päivässä (95 % väli {_fi_signed(pooled['ci_low'])}…"
                    f"{_fi_signed(pooled['ci_high'])}), ja tämä ikkunamäärä olisi erottanut vasta "
                    f"{_fi(pooled['mde'])} kävijän eron ({_fi(pooled['mde_pct'])} % vertailukohdan "
                    "MAE:sta). Tulos ei siis todista malleja yhtä hyviksi."
                )
            sentences.append(head + body)
    sentences.append(
        "Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen "
        "otoksen varassa. Lisää dataa tai tapahtumakalenteri piirteenä voisi muuttaa tuloksen."
    )
    return " ".join(sentences)


def pooled_report(root: Path, config: EvaluationConfig) -> tuple[str, dict[str, Any]] | None:
    """Pool every stored window run into one cross-run verdict.

    This is the "follow the model over time" view: evidence from every evaluation ever
    run in this repository, not just the windows of one sweep.
    """
    artifacts = load_window_runs(root)
    if not artifacts:
        return None
    collected: dict[tuple[int, str], list[np.ndarray]] = {}
    references: dict[tuple[int, str], list[np.ndarray]] = {}
    labels: dict[tuple[int, str], list[str]] = {}
    names: dict[int, str] = {}
    for artifact in artifacts:
        predictions = artifact.predictions
        mode = str(artifact.config.get("primary_weather_mode", config.primary_weather_mode))
        window = artifact.verdicts.get("window", {})
        label = f"{window.get('test_start')}..{window.get('test_end')}"
        for venue in artifact.verdicts.get("venues", []):
            venue_id = int(venue["venue_id"])
            names[venue_id] = str(venue.get("venue_name", ""))
            reference = str(venue.get("reference", ""))
            rows = predictions.loc[predictions["venue_id"] == venue_id]
            if rows.empty or not reference:
                continue
            reference_errors = absolute_errors(rows, mode, reference)
            for entry in venue.get("models", []):
                model = str(entry["model"])
                model_errors = absolute_errors(rows, mode, model)
                if model_errors.size == 0 or model_errors.size != reference_errors.size:
                    continue
                key = (venue_id, model)
                collected.setdefault(key, []).append(model_errors - reference_errors)
                references.setdefault(key, []).append(reference_errors)
                labels.setdefault(key, []).append(label)
    if not collected:
        return None
    lines = [
        "# Arviointien kooste kaikista tallennetuista ajoista",
        "",
        f"Ajoja mukana: {len(artifacts)}.",
        "",
        "| Venue | Malli | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti | Puolesta "
        "| Vastaan | MDE | MDE % |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    payload: dict[str, Any] = {"kind": "pooled", "runs": [item.run_id for item in artifacts], "venues": []}
    from .report import VERDICT_PHRASES, number, percent, signed

    for (venue_id, model), differences in sorted(collected.items()):
        pooled = pool_windows(
            differences,
            model=model,
            reference="best-per-window",
            reference_absolute_errors=references[venue_id, model],
            n_resamples=config.n_resamples,
            seed=config.seed,
        )
        lines.append(
            f"| {venue_id} ({names.get(venue_id, '')}) | {model} | {pooled.n_windows} "
            f"| {pooled.n_days} | {signed(pooled.mean_difference)} "
            f"| {signed(pooled.ci_low)} … {signed(pooled.ci_high)} "
            f"| {VERDICT_PHRASES.get(pooled.verdict, '')} | {pooled.windows_favouring} "
            f"| {pooled.windows_opposing} | {number(pooled.mde)} | {percent(pooled.mde_pct)} |"
        )
        payload["venues"].append(
            {"venue_id": venue_id, "model": model, "windows": labels[venue_id, model], **pooled.to_dict()}
        )
    lines += [
        "",
        "Kooste bootstrapataan kokonaisina ikkunoina. Ikkunat tulevat eri ajoista ja voivat olla "
        "päällekkäisiä; päällekkäiset ikkunat eivät ole riippumattomia, joten väli on tältä osin "
        "optimistinen.",
        "",
    ]
    return "\n".join(lines), payload


def _index_entry(
    artifacts: RunArtifacts, window: Window, config: EvaluationConfig, *, kind: str
) -> dict[str, Any]:
    """One line in ``index.json``."""
    verdicts = artifacts.verdicts
    if kind == "sweep":
        headline = [
            {
                "venue_id": venue["venue_id"],
                "model": entry["pooled"]["model"],
                "reference": entry["pooled"]["reference"],
                "verdict": entry["pooled"]["verdict"],
            }
            for venue in verdicts.get("venues", [])
            for entry in venue.get("models", [])
        ]
    else:
        headline = [
            {
                "venue_id": venue["venue_id"],
                "model": entry["model"],
                "reference": entry["comparison"]["reference"],
                "verdict": entry["comparison"]["verdict"],
            }
            for venue in verdicts.get("venues", [])
            for entry in venue.get("models", [])
        ]
    return {
        "run_id": artifacts.run_id,
        "kind": kind,
        "window": window.to_dict() if kind == "window" else None,
        "sweep": verdicts.get("sweep") if kind == "sweep" else None,
        "windows": verdicts.get("windows") if kind == "sweep" else None,
        "models": list(config.models),
        "reference_rule": config.reference,
        "primary_weather_mode": config.primary_weather_mode,
        "verdicts": headline,
        "members": artifacts.members,
    }


def history_bounds(data: ProcessedData, venues: tuple[int, ...] | None) -> tuple[date, date]:
    """The first and last observed day across the selected venues.

    The sweeps need this to know how far they may step, and it has to come from the
    untrimmed series so that ``--train-window all`` starts where the file does.
    """
    firsts: list[date] = []
    lasts: list[date] = []
    for venue in data.select_venues(venues):
        history = evaluation_history(data, venue.venue_id)
        if history.empty:
            continue
        firsts.append(pd.Timestamp(history["date"].min()).date())
        lasts.append(pd.Timestamp(history["date"].max()).date())
    if not firsts:
        raise WindowError("No venue has any observed history.")
    return max(firsts), min(lasts)


def utc_now() -> datetime:
    """The moment the index records for a run."""
    return datetime.now(UTC)
