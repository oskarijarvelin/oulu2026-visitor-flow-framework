"""The human-readable report, in either language, built from exactly what gets stored.

The renderer reads the same ``config``, ``metrics`` and ``verdicts`` payloads that are
written to disk, so the prose and the JSON can never drift apart. Nothing is recomputed
here.

Two things about the shape of the report are deliberate. The verdict is the first
paragraph and it is plain language: whoever runs the command should not have to open a
table to find out whether the model won. And the worst days come last but they are the
section people actually use — a date, an error and a probable cause is the most direct
statement of what the model does not know yet.

Both languages come out of one renderer rather than two. A second renderer would drift:
one of them would gain a caveat the other never got, and the reader with the wrong
language would be the last to know. The words live in :mod:`.strings`, the numbers in
:class:`~ovf_forecast.i18n.Format`, and everything below is layout.
"""

from __future__ import annotations

from typing import Any

from ..i18n import DEFAULT_LANG, NA, Format, Lang, formats, normalise, table_header
from .strings import (
    BIAS_PHRASES,
    CALIBRATION_PHRASES,
    VERDICT_PHRASES,
    WEATHER_LABELS,
    text,
)


def _flag(value: Any) -> bool:
    """Truthiness that survives a JSON round trip."""
    return bool(value) if value is not None else False


def localised(value: Any, lang: Lang) -> str:
    """One stored field that carries its own translations, in this language.

    Payload fields the renderer cannot rebuild — a worst-day cause, a weekday name, a
    warning — are stored as ``{"fi": ..., "en": ...}``. A run written before that was true
    stored a bare string; it renders as itself rather than as an error.
    """
    if isinstance(value, dict):
        return str(value.get(lang) or value.get(DEFAULT_LANG) or "")
    return str(value or "")


# --------------------------------------------------------------------------------------
# Window report
# --------------------------------------------------------------------------------------


def render_window_report(
    config: dict[str, Any],
    metrics: dict[str, Any],
    verdicts: dict[str, Any],
    lang: str = DEFAULT_LANG,
) -> str:
    """The full markdown report for one window."""
    code = normalise(lang)
    fmt = formats(code)
    window = verdicts.get("window", {})
    lines: list[str] = [
        text(
            code,
            "window_title",
            title=text(code, "title"),
            test_start=window.get("test_start"),
            test_end=window.get("test_end"),
        ),
        "",
        text(code, "run_id", run_id=verdicts.get("run_id", "")),
        "",
        text(code, "h_verdict"),
        "",
        summary_text(verdicts, code),
        "",
    ]
    lines += _setup_section(config, metrics, verdicts, code, fmt)
    for venue_metrics, venue_verdict in _paired_venues(metrics, verdicts):
        lines += _venue_sections(venue_metrics, venue_verdict, verdicts, code, fmt)
    lines += _limitations_section(metrics, verdicts, code)
    return "\n".join(lines).rstrip() + "\n"


def summary_text(verdicts: dict[str, Any], lang: Lang) -> str:
    """The stored verdict paragraph in one language, falling back to the other.

    A run stored before a language existed has no paragraph for it. Printing the one it
    does have beats printing nothing, and it is visibly the wrong language rather than
    silently missing content.
    """
    stored = str(verdicts.get(f"summary_{lang}", "") or "")
    if stored:
        return stored
    for other in ("fi", "en"):
        fallback = str(verdicts.get(f"summary_{other}", "") or "")
        if fallback:
            return fallback
    return ""


def _paired_venues(
    metrics: dict[str, Any], verdicts: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Line up each venue's metrics with its verdict."""
    by_id = {entry.get("venue_id"): entry for entry in verdicts.get("venues", [])}
    return [
        (entry, by_id.get(entry.get("venue_id"), {})) for entry in metrics.get("venues", [])
    ]


def _setup_section(
    config: dict[str, Any],
    metrics: dict[str, Any],
    verdicts: dict[str, Any],
    lang: Lang,
    fmt: Format,
) -> list[str]:
    """Section 2: what was trained on, with what, and what was forecast."""
    window = verdicts.get("window", {})
    lines = [
        text(lang, "h_setup"),
        "",
        text(lang, "setup_origin", origin=window.get("origin")),
        text(
            lang,
            "setup_test",
            test_start=window.get("test_start"),
            test_end=window.get("test_end"),
            days=window.get("horizon_days"),
        ),
        text(lang, "setup_train_window", train_window=window.get("train_window")),
        text(lang, "setup_models", models=", ".join(config.get("models", [])) or NA),
        text(lang, "setup_baselines", baselines=", ".join(config.get("baselines", []))),
        text(lang, "setup_reference", reference=config.get("reference")),
        text(
            lang,
            "setup_weather",
            modes=", ".join(config.get("weather_modes", [])),
            primary=config.get("primary_weather_mode"),
        ),
        text(
            lang,
            "setup_bootstrap",
            resamples=fmt.integer(config.get("n_resamples")),
            seed=config.get("seed"),
        ),
        "",
    ]
    lines += table_header(text(lang, "setup_table"))
    for entry in metrics.get("venues", []):
        diagnostics = entry.get("diagnostics", {})
        lines.append(
            f"| {entry.get('venue_id')} ({entry.get('venue_name')}) "
            f"| {diagnostics.get('training_start')} "
            f"| {diagnostics.get('training_days')} "
            f"| {diagnostics.get('training_zero_days')} "
            f"| {diagnostics.get('nested_origins')} "
            f"| {fmt.number(diagnostics.get('mase_denominator'), 2)} |"
        )
    lines += ["", text(lang, "setup_note"), ""]
    return lines


def _venue_sections(
    venue_metrics: dict[str, Any],
    venue_verdict: dict[str, Any],
    verdicts: dict[str, Any],
    lang: Lang,
    fmt: Format,
) -> list[str]:
    """Sections 3 to 7 and 9 for one venue."""
    primary = verdicts.get("primary_weather_mode", "operational")
    lines = [
        text(
            lang,
            "venue_heading",
            venue_id=venue_metrics.get("venue_id"),
            venue_name=venue_metrics.get("venue_name"),
        ),
        "",
    ]
    lines += _totals_section(venue_metrics, primary, lang, fmt)
    lines += _daily_metrics_section(venue_metrics, primary, lang, fmt)
    lines += _statistics_section(venue_verdict, lang, fmt)
    lines += _calibration_section(venue_verdict, lang, fmt)
    lines += _weather_section(venue_metrics, lang, fmt)
    lines += _worst_days_section(venue_metrics, lang, fmt)
    return lines


def _totals_section(
    venue_metrics: dict[str, Any], primary: str, lang: Lang, fmt: Format
) -> list[str]:
    """Section 3: the number a producer actually asks for."""
    totals = [row for row in venue_metrics.get("totals", []) if row.get("weather_mode") == primary]
    if not totals:
        return []
    lines = [text(lang, "h_totals"), ""]
    lines += table_header(text(lang, "totals_table"))
    for row in totals:
        lines.append(
            f"| {row.get('model')} | {fmt.integer(row.get('predicted'))} "
            f"| {fmt.integer(row.get('actual'))} "
            f"| {fmt.signed(row.get('difference'), 0)} "
            f"| {fmt.signed(row.get('difference_pct'), 1)} % "
            f"| {fmt.integer(row.get('p10'))} – {fmt.integer(row.get('p90'))} "
            f"| {fmt.yes_no(row.get('covers_actual'))} "
            f"| {fmt.integer(row.get('summed_daily_p10'))} – "
            f"{fmt.integer(row.get('summed_daily_p90'))} |"
        )
    lines += ["", text(lang, "totals_note"), ""]
    drifted = [row for row in totals if _flag(row.get("is_drifted"))]
    if drifted:
        lines += [
            text(lang, "totals_drift_prefix")
            + ", ".join(
                text(
                    lang,
                    "totals_drift_item",
                    model=row.get("model"),
                    ratio=fmt.number(row.get("median_ratio"), 2),
                )
                for row in drifted
            )
            + text(lang, "totals_drift_tail"),
            "",
        ]
    thin = [row for row in totals if _flag(row.get("is_thin"))]
    if thin:
        lines += [
            text(lang, "totals_thin_prefix")
            + ", ".join(
                text(lang, "totals_thin_item", model=row.get("model"), n=row.get("n_ratio_samples"))
                for row in thin
            )
            + text(lang, "totals_thin_tail"),
            "",
        ]
    return lines


def _daily_metrics_section(
    venue_metrics: dict[str, Any], primary: str, lang: Lang, fmt: Format
) -> list[str]:
    """Section 4: models and baselines side by side, per horizon bucket."""
    scores = [row for row in venue_metrics.get("scores", []) if row.get("weather_mode") == primary]
    if not scores:
        return []
    lines = [text(lang, "h_daily"), "", text(lang, "daily_intro", primary=primary), ""]
    lines += table_header(text(lang, "daily_table"))
    for row in scores:
        pinball = row.get("pinball", {})
        smape = fmt.number(row.get("smape"), 1)
        if not _flag(row.get("smape_reliable")):
            smape = f"{smape} ⚠"
        lines.append(
            f"| {row.get('model')} | {row.get('bucket')} | {fmt.number(row.get('mae'))} "
            f"| {fmt.number(row.get('rmse'))} | {fmt.number(row.get('mase'), 3)} "
            f"| {fmt.signed(row.get('bias'))} | {fmt.number(pinball.get('q10'))} "
            f"| {fmt.number(pinball.get('q50'))} | {fmt.number(pinball.get('q90'))} "
            f"| {fmt.number(row.get('coverage_80'), 2)} | {smape} | {row.get('n')} |"
        )
    unreliable = sorted(
        {int(row.get("zero_days", 0)) for row in scores if not _flag(row.get("smape_reliable"))}
    )
    lines.append("")
    if unreliable:
        lines.append(text(lang, "daily_smape_warning", zero_days=max(unreliable)))
    else:
        lines.append(text(lang, "daily_smape_ok"))
    lines.append("")
    return lines


def _statistics_section(venue_verdict: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """Section 5: interval, skill score, power, and the secondary DM p-value."""
    models = venue_verdict.get("models", [])
    if not models:
        return []
    reference = venue_verdict.get("reference", NA)
    baseline_mae = venue_verdict.get("baseline_mae", {})
    lines = [
        text(lang, "h_stats"),
        "",
        text(
            lang,
            "stats_intro",
            reference=reference,
            mae=fmt.number(baseline_mae.get(reference)),
            all_mae=", ".join(f"{name} {fmt.number(value)}" for name, value in baseline_mae.items()),
        ),
        "",
    ]
    lines += table_header(text(lang, "stats_table"))
    for entry in models:
        comparison = entry.get("comparison", {})
        lines.append(
            f"| {entry.get('model')} | {fmt.signed(comparison.get('mean_difference'))} "
            f"| {fmt.signed(comparison.get('ci_low'))} … {fmt.signed(comparison.get('ci_high'))} "
            f"| {fmt.phrase(VERDICT_PHRASES, comparison.get('verdict'))} "
            f"| {fmt.number(comparison.get('skill_score'), 3)} "
            f"| {fmt.number(comparison.get('skill_ci_low'), 3)} … "
            f"{fmt.number(comparison.get('skill_ci_high'), 3)} "
            f"| {fmt.number(comparison.get('mde'))} | {fmt.percent(comparison.get('mde_pct'))} "
            f"| {fmt.number(comparison.get('dm_statistic'), 2)} "
            f"| {fmt.number(entry.get('raw_p_value'), 3)} "
            f"| {fmt.number(entry.get('holm_p_value'), 3)} |"
        )
    lines += [
        "",
        text(lang, "stats_note_difference"),
        "",
        text(lang, "stats_note_mde"),
        "",
        text(lang, "stats_note_dm", family_size=venue_verdict.get("family_size", NA)),
        "",
    ]
    return lines


def _calibration_section(venue_verdict: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """Section 6: coverage and bias, each with an interval."""
    models = venue_verdict.get("models", [])
    if not models:
        return []
    lines = [text(lang, "h_calibration"), ""]
    lines += table_header(text(lang, "calibration_table"))
    for entry in models:
        calibration = entry.get("calibration", {})
        bias = entry.get("bias", {})
        lines.append(
            f"| {entry.get('model')} | {fmt.number(calibration.get('coverage'), 2)} "
            f"({calibration.get('covered')}/{calibration.get('n')}) "
            f"| {fmt.number(calibration.get('ci_low'), 2)} … "
            f"{fmt.number(calibration.get('ci_high'), 2)} "
            f"| {fmt.phrase(CALIBRATION_PHRASES, calibration.get('verdict'))} "
            f"| {fmt.signed(bias.get('mean_error'))} "
            f"| {fmt.signed(bias.get('ci_low'))} … {fmt.signed(bias.get('ci_high'))} "
            f"| {fmt.signed(bias.get('pct_of_actual'))} % "
            f"| {fmt.phrase(BIAS_PHRASES, bias.get('verdict'))} |"
        )
    lines += ["", text(lang, "calibration_note"), ""]
    return lines


def _weather_section(venue_metrics: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """Section 7: what the model's accuracy owes to knowing the weather."""
    sensitivity = venue_metrics.get("weather_sensitivity", {})
    if not sensitivity:
        return []
    lines = [text(lang, "h_weather"), ""]
    lines += table_header(text(lang, "weather_table"))
    for model, entry in sensitivity.items():
        lines.append(
            f"| {model} | {fmt.number(entry.get('perfect'))} "
            f"| {fmt.number(entry.get('operational'))} "
            f"| {fmt.number(entry.get('climatology'))} | {fmt.signed(entry.get('gap'))} "
            f"| {fmt.percent(entry.get('gap_pct'))} |"
        )
    lines += ["", text(lang, "weather_note"), ""]
    negative = [
        entry
        for entry in sensitivity.values()
        if isinstance(entry.get("gap"), float)
        and entry["gap"] == entry["gap"]
        and entry["gap"] < 0.0
    ]
    if negative:
        lines += [text(lang, "weather_negative"), ""]
    lines += table_header(text(lang, "weather_days_table"))
    for mode, counts in venue_metrics.get("diagnostics", {}).get("weather_days", {}).items():
        lines.append(
            f"| {fmt.phrase(WEATHER_LABELS, mode)} | {counts.get('observed')} "
            f"| {counts.get('climatology')} |"
        )
    lines.append("")
    return lines


def _worst_days_section(venue_metrics: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """Section 9: the five biggest misses, with a probable cause for each."""
    worst = venue_metrics.get("worst_days", {})
    if not worst:
        return []
    lines = [text(lang, "h_worst"), ""]
    for model, rows in worst.items():
        lines += [f"**{model}**", ""]
        lines += table_header(text(lang, "worst_table"))
        for row in rows:
            lines.append(
                f"| {row.get('date')} | {localised(row.get('weekday'), lang)} "
                f"| {fmt.integer(row.get('y_true'))} | {fmt.integer(row.get('p50'))} "
                f"| {fmt.signed(row.get('error'), 0)} | {localised(row.get('note'), lang)} |"
            )
        lines.append("")
    lines += [text(lang, "worst_note"), ""]
    return lines


def _limitations_section(
    metrics: dict[str, Any], verdicts: dict[str, Any], lang: Lang
) -> list[str]:
    """Section 8: sample size and what may not be concluded from this run."""
    window = verdicts.get("window", {})
    horizon = window.get("horizon_days", 0)
    lines = [
        text(lang, "h_limits"),
        "",
        text(lang, "limit_sample", horizon=horizon),
        text(lang, "limit_single_window"),
        text(lang, "limit_no_difference"),
        text(lang, "limit_smape"),
        text(lang, "limit_history"),
        text(lang, "limit_tickets"),
    ]
    for entry in metrics.get("venues", []):
        diagnostics = entry.get("diagnostics", {})
        venue_id = entry.get("venue_id")
        leading = int(diagnostics.get("leading_zero_days") or 0)
        if leading:
            lines.append(text(lang, "limit_leading_zeros", venue_id=venue_id, days=leading))
        if diagnostics.get("missing_test_days"):
            lines.append(
                text(
                    lang,
                    "limit_missing_days",
                    venue_id=venue_id,
                    days=len(diagnostics["missing_test_days"]),
                )
            )
        if diagnostics.get("default_bands"):
            lines.append(
                text(
                    lang,
                    "limit_default_bands",
                    venue_id=venue_id,
                    buckets=", ".join(diagnostics["default_bands"]),
                )
            )
    lines.append("")
    return lines


# --------------------------------------------------------------------------------------
# Sweep report
# --------------------------------------------------------------------------------------


def render_sweep_report(
    config: dict[str, Any],
    metrics: dict[str, Any],
    verdicts: dict[str, Any],
    lang: str = DEFAULT_LANG,
) -> str:
    """The full markdown report for a sweep: pooled verdict first, windows below it."""
    code = normalise(lang)
    fmt = formats(code)
    lines: list[str] = [
        text(
            code,
            "sweep_title",
            title=text(code, "title"),
            kind=verdicts.get("sweep"),
            first_day=verdicts.get("first_day"),
            last_day=verdicts.get("last_day"),
        ),
        "",
        text(code, "run_id", run_id=verdicts.get("run_id", "")),
        "",
        text(code, "h_sweep_verdict"),
        "",
        summary_text(verdicts, code),
        "",
        text(code, "h_sweep_windows"),
        "",
    ]
    lines += table_header(text(code, "sweep_windows_table"))
    for position, window in enumerate(verdicts.get("windows", []), start=1):
        lines.append(
            f"| {position} | {window.get('test_start')} – {window.get('test_end')} "
            f"| {window.get('origin')} | {window.get('train_window')} | `{window.get('run_id')}` |"
        )
    lines += [
        "",
        text(
            code,
            "sweep_meta",
            primary=verdicts.get("primary_weather_mode"),
            reference=verdicts.get("reference_rule"),
            family_size=verdicts.get("family_size"),
        ),
        "",
    ]
    for venue in verdicts.get("venues", []):
        lines += _sweep_venue_section(venue, code, fmt)
    lines += [
        text(code, "h_sweep_limits"),
        "",
        text(code, "sweep_limit_windows"),
        text(code, "sweep_limit_descriptive"),
        text(code, "sweep_limit_holm"),
        text(code, "sweep_limit_history"),
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _sweep_venue_section(venue: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """One venue's pooled verdict and its per-window detail."""
    lines = [
        text(
            lang,
            "venue_heading",
            venue_id=venue.get("venue_id"),
            venue_name=venue.get("venue_name"),
        ),
        "",
        text(lang, "h_sweep_pooled"),
        "",
    ]
    lines += table_header(text(lang, "sweep_pooled_table"))
    for entry in venue.get("models", []):
        pooled = entry.get("pooled", {})
        lines.append(
            f"| {pooled.get('model')} | {pooled.get('reference')} | {pooled.get('n_windows')} "
            f"| {pooled.get('n_days')} | {fmt.signed(pooled.get('mean_difference'))} "
            f"| {fmt.signed(pooled.get('ci_low'))} … {fmt.signed(pooled.get('ci_high'))} "
            f"| {fmt.phrase(VERDICT_PHRASES, pooled.get('verdict'))} "
            f"| {pooled.get('windows_favouring')} | {pooled.get('windows_opposing')} "
            f"| {fmt.number(pooled.get('mde'))} | {fmt.percent(pooled.get('mde_pct'))} |"
        )
    lines.append("")
    for entry in venue.get("models", []):
        lines += [text(lang, "h_sweep_per_window", model=entry.get("model")), ""]
        lines += table_header(text(lang, "sweep_window_table"))
        for row in entry.get("per_window", []):
            lines.append(
                f"| {row.get('label')} | {row.get('reference')} "
                f"| {fmt.number(row.get('model_mae'))} | {fmt.number(row.get('reference_mae'))} "
                f"| {fmt.signed(row.get('mean_difference'))} "
                f"| {fmt.signed(row.get('ci_low'))} … {fmt.signed(row.get('ci_high'))} "
                f"| {fmt.phrase(VERDICT_PHRASES, row.get('verdict'))} "
                f"| {fmt.number(row.get('mde'))} | {fmt.percent(row.get('mde_pct'))} "
                f"| {fmt.number(row.get('raw_p_value'), 3)} "
                f"| {fmt.number(row.get('holm_p_value'), 3)} |"
            )
        lines.append("")
        totals = entry.get("totals", [])
        if totals:
            lines += [text(lang, "h_sweep_totals", model=entry.get("model")), ""]
            lines += table_header(text(lang, "sweep_totals_table"))
            for row in totals:
                lines.append(
                    f"| {row.get('label')} | {fmt.integer(row.get('predicted'))} "
                    f"| {fmt.integer(row.get('actual'))} "
                    f"| {fmt.signed(row.get('difference_pct'))} % "
                    f"| {fmt.integer(row.get('p10'))} – {fmt.integer(row.get('p90'))} "
                    f"| {fmt.yes_no(row.get('covers_actual'))} |"
                )
            lines.append("")
    return lines


__all__ = [
    "localised",
    "render_sweep_report",
    "render_window_report",
    "summary_text",
]
