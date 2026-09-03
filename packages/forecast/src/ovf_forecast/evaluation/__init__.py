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
from ..i18n import DEFAULT_LANG, LANGUAGES, Lang, formats, normalise, table_header
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
from .strings import VERDICT_PHRASES, WEEKDAY_NAMES, text
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

HEAVY_RAIN_MM = 5.0
WORST_DAY_LIMIT = 5


@dataclass
class EvaluationResult:
    """What one invocation produced: the runs it wrote and what it concluded."""

    run_ids: list[str] = field(default_factory=list)
    sweep_run_id: str | None = None
    summaries: dict[str, str] = field(default_factory=dict)
    failed_venues: list[int] = field(default_factory=list)

    @property
    def produced_anything(self) -> bool:
        """Whether at least one window was evaluated."""
        return bool(self.run_ids)

    def summary(self, lang: str = DEFAULT_LANG) -> str:
        """The verdict paragraph in one language, falling back to whatever exists."""
        code = normalise(lang)
        if self.summaries.get(code):
            return self.summaries[code]
        return next((value for value in self.summaries.values() if value), "")


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
    last_summaries: dict[str, str] = {}
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
        last_summaries = {
            lang: str(artifacts.verdicts.get(f"summary_{lang}", "")) for lang in LANGUAGES
        }
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
        result.summaries = {
            lang: str(sweep.verdicts.get(f"summary_{lang}", "")) for lang in LANGUAGES
        }
    else:
        result.summaries = last_summaries
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
                "weekday": {lang: WEEKDAY_NAMES[lang][weekday] for lang in LANGUAGES},
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


def _explain_day(
    facts: dict[str, Any], y_true: float, weekday: int, horizon: int
) -> dict[str, str]:
    """A short, honest guess at why one day went wrong, in every language.

    Built once per day rather than at render time, because the facts behind it — the
    holiday name, the weather source — are the run's, not the report's, and re-deriving
    them per language is how the two would eventually disagree.
    """
    return {lang: _explain_day_in(lang, facts, y_true, weekday, horizon) for lang in LANGUAGES}


def _explain_day_in(
    lang: Lang, facts: dict[str, Any], y_true: float, weekday: int, horizon: int
) -> str:
    """One day's causes in one language."""
    fmt = formats(lang)
    reasons: list[str] = []
    holiday = facts.get("holiday_name")
    if holiday is not None and not pd.isna(holiday) and str(holiday).strip():
        reasons.append(text(lang, "cause_holiday", holiday=holiday))
    precipitation = _as_float(facts.get("precip_sum"))
    if np.isfinite(precipitation) and precipitation >= HEAVY_RAIN_MM:
        reasons.append(text(lang, "cause_rain", mm=fmt.number(precipitation, 1)))
    if y_true == 0.0:
        reasons.append(text(lang, "cause_zero"))
    if str(facts.get("model_weather_source")) == "climatology":
        reasons.append(text(lang, "cause_climatology", horizon=horizon))
    if weekday >= 5:
        reasons.append(text(lang, "cause_weekend"))
    if not reasons:
        reasons.append(text(lang, "cause_unknown"))
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

    summaries = _summaries(lambda lang: _window_summary(window, config, verdict_venues, lang))
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
        "summary_fi": summaries["fi"],
        "summary_en": summaries["en"],
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
        reports={
            lang: render_window_report(config_payload, metrics_payload, verdicts_payload, lang)
            for lang in LANGUAGES
        },
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
# The verdict paragraphs
# --------------------------------------------------------------------------------------


def _summaries(builder: Any) -> dict[str, str]:
    """One paragraph builder run in every language, keyed by language.

    Both paragraphs are built at run time and stored, rather than one being built now and
    the other translated later. A verdict is the one sentence somebody acts on, and a
    reader in either language should get it from the same numbers on the same day.
    """
    return {lang: builder(lang) for lang in LANGUAGES}


def _window_summary(
    window: Window, config: EvaluationConfig, venues: list[dict[str, Any]], lang: Lang
) -> str:
    """One paragraph, in plain language, that can be read without opening the report."""
    sentences = [
        text(
            lang,
            "sum_window_intro",
            test_start=window.test_start.isoformat(),
            test_end=window.test_end.isoformat(),
            days=window.horizon_days,
            origin=window.origin.isoformat(),
            train_window=window.train_window,
            primary=config.primary_weather_mode,
        )
    ]
    for venue in venues:
        for entry in venue["models"]:
            sentences.append(_model_sentence(venue, entry, lang))
    sentences.append(text(lang, "sum_window_tail"))
    return " ".join(sentences)


def _model_sentence(venue: dict[str, Any], entry: dict[str, Any], lang: Lang) -> str:
    """One sentence per model: how it did, against whom, and what that proves."""
    fmt = formats(lang)
    comparison = entry["comparison"]
    total = entry.get("total", {})
    verdict = comparison["verdict"]
    head = text(
        lang,
        "sum_model_head",
        venue=f"Venue {venue['venue_id']} ({venue['venue_name']})",
        model=entry["model"],
        model_mae=fmt.number(comparison["model_mae"]),
        reference=comparison["reference"],
        reference_mae=fmt.number(comparison["reference_mae"]),
    )
    shared = {
        "difference": fmt.signed(comparison["mean_difference"]),
        "ci_low": fmt.signed(comparison["ci_low"]),
        "ci_high": fmt.signed(comparison["ci_high"]),
    }
    if verdict == VERDICT_BETTER:
        middle = text(
            lang, "sum_model_better", skill=fmt.number(comparison["skill_score"], 3), **shared
        )
    elif verdict == VERDICT_WORSE:
        middle = text(lang, "sum_model_worse", reference=comparison["reference"], **shared)
    else:
        middle = text(lang, "sum_model_none", **shared)
    power = text(
        lang,
        "sum_power",
        n=comparison["n"],
        mde=fmt.number(comparison["mde"]),
        mde_pct=fmt.number(comparison["mde_pct"]),
    )
    power += text(
        lang, "sum_power_tail_none" if verdict == VERDICT_NO_DIFFERENCE else "sum_power_tail"
    )
    tail = ""
    if total:
        tail = text(
            lang,
            "sum_total",
            predicted=fmt.number(total.get("predicted"), 0),
            actual=fmt.number(total.get("actual"), 0),
            difference_pct=fmt.signed(total.get("difference_pct")),
            p10=fmt.number(total.get("p10"), 0),
            p90=fmt.number(total.get("p90"), 0),
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

    summaries = _summaries(lambda lang: _sweep_summary(kind, windows, config, verdict_venues, lang))
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
        "summary_fi": summaries["fi"],
        "summary_en": summaries["en"],
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
        reports={
            lang: render_sweep_report(config_payload, metrics_payload, verdicts_payload, lang)
            for lang in LANGUAGES
        },
        members=[item.run_id for item in executed],
    )


def _sweep_summary(
    kind: str,
    windows: list[Window],
    config: EvaluationConfig,
    venues: list[dict[str, Any]],
    lang: Lang,
) -> str:
    """The headline paragraph of a sweep: the pooled verdict, in plain language."""
    fmt = formats(lang)
    sentences = [
        text(
            lang,
            "sum_sweep_intro",
            kind=kind,
            windows=len(windows),
            first_day=windows[0].test_start.isoformat(),
            last_day=windows[-1].test_end.isoformat(),
            primary=config.primary_weather_mode,
            reference=config.reference,
        )
    ]
    for venue in venues:
        for entry in venue["models"]:
            pooled = entry["pooled"]
            head = text(
                lang,
                "sum_sweep_head",
                venue=f"Venue {venue['venue_id']} ({venue['venue_name']})",
                model=pooled["model"],
                reference=pooled["reference"],
                windows=pooled["n_windows"],
                days=pooled["n_days"],
                favouring=pooled["windows_favouring"],
                opposing=pooled["windows_opposing"],
            )
            shared = {
                "difference": fmt.signed(pooled["mean_difference"]),
                "ci_low": fmt.signed(pooled["ci_low"]),
                "ci_high": fmt.signed(pooled["ci_high"]),
            }
            if pooled["verdict"] == VERDICT_BETTER:
                body = text(lang, "sum_sweep_better", **shared)
            elif pooled["verdict"] == VERDICT_WORSE:
                body = text(lang, "sum_sweep_worse", **shared)
            else:
                body = text(
                    lang,
                    "sum_sweep_none",
                    mde=fmt.number(pooled["mde"]),
                    mde_pct=fmt.number(pooled["mde_pct"]),
                    **shared,
                )
            sentences.append(head + body)
    sentences.append(text(lang, "sum_sweep_tail"))
    return " ".join(sentences)


def pooled_report(
    root: Path, config: EvaluationConfig, lang: str = DEFAULT_LANG
) -> tuple[str, dict[str, Any]] | None:
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
    code = normalise(lang)
    fmt = formats(code)
    lines = [
        text(code, "pooled_title"),
        "",
        text(code, "pooled_runs", runs=len(artifacts)),
        "",
    ]
    lines += table_header(text(code, "pooled_table"))
    payload: dict[str, Any] = {"kind": "pooled", "runs": [item.run_id for item in artifacts], "venues": []}
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
            f"| {pooled.n_days} | {fmt.signed(pooled.mean_difference)} "
            f"| {fmt.signed(pooled.ci_low)} … {fmt.signed(pooled.ci_high)} "
            f"| {fmt.phrase(VERDICT_PHRASES, pooled.verdict)} | {pooled.windows_favouring} "
            f"| {pooled.windows_opposing} | {fmt.number(pooled.mde)} "
            f"| {fmt.percent(pooled.mde_pct)} |"
        )
        payload["venues"].append(
            {"venue_id": venue_id, "model": model, "windows": labels[venue_id, model], **pooled.to_dict()}
        )
    lines += ["", text(code, "pooled_note"), ""]
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
