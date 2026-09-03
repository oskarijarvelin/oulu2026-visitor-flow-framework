"""The human-readable output, in either language, built from exactly what gets stored.

The renderer reads the same ``config``, ``metrics`` and ``verdicts`` payloads that are
written to disk, so the prose and the JSON cannot drift apart. Nothing is recomputed
here.

The order of a forecast report is the order somebody reads it in. The dates come first,
because that is the question. The probability sits next to every date, because a list of
six dates with no probability invites the reader to treat the first one as certain. The
measured reliability comes before the tables, because a recommendation from a rule that
has never beaten chance on this venue should be read differently from one that has.

One renderer serves both languages. The words are in :mod:`.strings`, the numbers and the
dates in :class:`~ovf_forecast.i18n.Format`, and a date is where the two languages differ
most visibly: ``ma 5.10.`` and ``Mon 5 Oct`` are the same day, and neither reads in the
other language.
"""

from __future__ import annotations

from typing import Any

from ..evaluation.report import localised
from ..i18n import DEFAULT_LANG, NA, Format, Lang, formats, normalise, parse_day, table_header
from .strings import CHANCE_PHRASES, STATUS_PHRASES, VERDICT_PHRASES, WEEKDAY_NAMES, text

# --------------------------------------------------------------------------------------
# Forecast
# --------------------------------------------------------------------------------------


def forecast_summary(
    venue: dict[str, Any], reliability: dict[str, Any] | None, lang: Lang = DEFAULT_LANG
) -> str:
    """The one paragraph the command prints: the dates, the threshold, the confidence."""
    fmt = formats(lang)
    quiet = venue.get("quiet_set", {})
    days = [parse_day(item) for item in quiet.get("dates", [])]
    listed = fmt.join(
        [fmt.day(day) for day in days if day is not None], text(lang, "sum_no_candidates")
    )
    gap = quiet.get("mean_ratio")
    quieter = fmt.share_percent(1.0 - float(gap)) if isinstance(gap, int | float) else NA
    sentences = [
        text(
            lang,
            "sum_days",
            venue_name=venue.get("venue_name"),
            venue_id=venue.get("venue_id"),
            month=fmt.month_label(venue.get("month", "")),
            days=listed,
        ),
        text(
            lang,
            "sum_threshold",
            k=fmt.integer(quiet.get("k")),
            n=fmt.integer(quiet.get("n_eligible")),
            gap=quieter,
        ),
    ]
    best = _most_certain(venue)
    if best is not None:
        day, probability = best
        sentences.append(
            text(
                lang,
                "sum_best",
                day=fmt.day(day),
                probability=fmt.share_percent(probability),
            )
        )
    if not quiet.get("is_material", False):
        sentences.append(text(lang, "sum_not_material"))
    sentences.append(_reliability_sentence(reliability, lang, fmt))
    return " ".join(sentences)


def _most_certain(venue: dict[str, Any]) -> tuple[Any, float] | None:
    """The quiet day with the highest selection probability."""
    best: tuple[Any, float] | None = None
    for row in venue.get("days", []):
        if not row.get("is_quiet"):
            continue
        day = parse_day(row.get("date"))
        probability = row.get("probability")
        if day is None or not isinstance(probability, int | float):
            continue
        if best is None or float(probability) > best[1]:
            best = (day, float(probability))
    return best


def _reliability_sentence(
    reliability: dict[str, Any] | None, lang: Lang, fmt: Format
) -> str:
    """What the stored sweep says about this venue and this rule, if anything."""
    if reliability is None:
        return text(lang, "reliability_missing")
    benefit = _scale(reliability.get("benefit"))
    low = _scale(reliability.get("benefit_ci_low"))
    high = _scale(reliability.get("benefit_ci_high"))
    measured = (
        text(
            lang,
            "reliability_value",
            benefit=fmt.percent(benefit, 0),
            low=fmt.percent(low, 0),
            high=fmt.percent(high, 0),
        )
        if all(value == value for value in (benefit, low, high))
        else NA
    )
    return text(
        lang,
        "reliability_measured",
        windows=fmt.integer(reliability.get("n_windows")),
        run_id=reliability.get("run_id", ""),
        measured=measured,
        verdict=fmt.phrase(VERDICT_PHRASES, reliability.get("verdict", "")),
    )


def render_forecast_report(
    config: dict[str, Any],
    metrics: dict[str, Any],
    verdicts: dict[str, Any],
    lang: str = DEFAULT_LANG,
) -> str:
    """The full markdown report for one month."""
    code = normalise(lang)
    fmt = formats(code)
    lines: list[str] = [
        text(
            code,
            "forecast_heading",
            title=text(code, "forecast_title"),
            month=fmt.month_label(metrics.get("month", "")),
        ),
        "",
        text(code, "run_id", run_id=verdicts.get("run_id", "")),
        "",
        text(code, "h_answer"),
        "",
    ]
    for venue in metrics.get("venues", []):
        lines.append(forecast_summary(venue, _reliability_for(verdicts, venue), code))
        lines.append("")
    lines += _forecast_method_section(config, code, fmt)
    for venue in metrics.get("venues", []):
        lines += _forecast_venue_section(venue, code, fmt)
    lines += _forecast_limits_section(code)
    return "\n".join(lines).rstrip() + "\n"


def _reliability_for(verdicts: dict[str, Any], venue: dict[str, Any]) -> dict[str, Any] | None:
    """The stored sweep row matching this venue and rule."""
    for row in verdicts.get("reliability", []):
        matches = row.get("venue_id") == venue.get("venue_id")
        if matches and row.get("model") == venue.get("score_model"):
            return dict(row)
    return None


def _forecast_method_section(config: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """How the answer was produced, in enough detail to reproduce it."""
    return [
        text(lang, "h_method"),
        "",
        text(lang, "method_model", model=config.get("score_model")),
        text(
            lang,
            "method_threshold",
            share=fmt.share_percent(float(config.get("quiet_share", 0.2))),
        ),
        text(lang, "method_simulations", simulations=fmt.integer(config.get("n_simulations"))),
        text(lang, "method_seed", seed=fmt.integer(config.get("seed"))),
        "",
        text(lang, "method_note_score"),
        "",
        text(lang, "method_note_separation"),
        "",
    ]


def _forecast_venue_section(venue: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """One venue's quiet set, whole month table and setup."""
    quiet = venue.get("quiet_set", {})
    eligibility = venue.get("eligibility", {})
    residuals = venue.get("residuals", {})
    lines = [
        text(
            lang,
            "h_venue",
            venue_name=venue.get("venue_name"),
            venue_id=venue.get("venue_id"),
        ),
        "",
        text(
            lang,
            "venue_intro",
            origin=venue.get("origin"),
            model=venue.get("score_model"),
            n=fmt.integer(quiet.get("n_eligible")),
            k=fmt.integer(quiet.get("k")),
            cut=fmt.number(quiet.get("cut")),
            cut_ratio=fmt.number(float(quiet.get("cut_ratio", float("nan"))) * 100.0, 0),
        ),
        "",
        text(lang, "h_quiet_days"),
        "",
    ]
    lines += table_header(text(lang, "quiet_table"), align="lrrrrlrr")
    for row in venue.get("days", []):
        if not row.get("is_quiet"):
            continue
        lines.append(_day_row(row, fmt))
    lines += ["", text(lang, "h_month"), ""]
    lines += table_header(text(lang, "month_table"), align="llrrr")
    for row in venue.get("days", []):
        lines.append(
            f"| {fmt.day(parse_day(row.get('date')))} "
            f"| {fmt.phrase(STATUS_PHRASES, row.get('status'))} | {row.get('rank') or NA} "
            f"| {_ratio(row.get('ratio'), fmt)} | {_ratio(row.get('probability'), fmt)} |"
        )
    closed = eligibility.get("closed_weekdays") or []
    lines += [
        "",
        text(lang, "h_inputs"),
        "",
        text(
            lang,
            "input_closed",
            days=fmt.join([WEEKDAY_NAMES[lang][day] for day in closed], text(lang, "none")),
        ),
        text(
            lang,
            "input_holiday",
            factor=fmt.number(eligibility.get("holiday_factor"), 2),
            n=fmt.integer(eligibility.get("holiday_observations")),
        ),
        text(
            lang,
            "input_residuals",
            kind=text(
                lang,
                "residuals_measured" if residuals.get("measured") else "residuals_default",
            ),
            n=fmt.integer(residuals.get("n")),
        ),
        "",
    ]
    warnings = venue.get("warnings", [])
    if warnings:
        lines += [text(lang, "h_warnings"), ""]
        lines += [f"- {localised(warning, lang)}" for warning in warnings]
        lines.append("")
    return lines


def _day_row(row: dict[str, Any], fmt: Format) -> str:
    """One line of the quiet-set table."""
    tie = row.get("tie_size") or 1
    return (
        f"| {fmt.day(parse_day(row.get('date')))} | {row.get('rank') or NA} "
        f"| {_ratio(row.get('ratio'), fmt)} | {_ratio(row.get('probability'), fmt)} "
        f"| {fmt.integer(tie) if int(tie) > 1 else NA} | {row.get('holiday_name') or NA} "
        f"| {fmt.number(row.get('temp_mean'))} | {fmt.number(row.get('precip_sum'))} |"
    )


def _ratio(value: Any, fmt: Format) -> str:
    """A within-month ratio or probability as a percentage."""
    return NA if not isinstance(value, int | float) else fmt.share_percent(float(value))


def _forecast_limits_section(lang: Lang) -> list[str]:
    """What the answer does not claim."""
    return [
        text(lang, "h_forecast_limits"),
        "",
        text(lang, "forecast_limit_score"),
        text(lang, "forecast_limit_probability"),
        text(lang, "forecast_limit_events"),
        text(lang, "forecast_limit_weather"),
        text(lang, "forecast_limit_closed"),
        "",
    ]


# --------------------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------------------


def backtest_summary(pooled: list[dict[str, Any]], lang: Lang = DEFAULT_LANG) -> str:
    """The verdict the sweep prints: one line per venue and rule.

    A list rather than a paragraph, because five rules on two venues is ten verdicts and
    a wall of prose is where a reader stops looking for the one that concerns them.
    """
    if not pooled:
        return text(lang, "backtest_no_windows")
    fmt = formats(lang)
    parts: list[str] = []
    for row in pooled:
        parts.append(
            text(
                lang,
                "backtest_sum_row",
                venue_name=row.get("venue_name"),
                venue_id=row.get("venue_id"),
                model=row.get("model"),
                benefit=fmt.percent(_scale(row.get("benefit")), 0),
                low=fmt.percent(_scale(row.get("benefit_ci_low")), 0),
                high=fmt.percent(_scale(row.get("benefit_ci_high")), 0),
                windows=fmt.integer(row.get("n_windows")),
                verdict=fmt.phrase(VERDICT_PHRASES, row.get("verdict")),
                hit_rate=fmt.percent(_scale(row.get("hit_rate")), 0),
                chance_rate=fmt.percent(_scale(row.get("chance_rate")), 0),
            )
        )
    return "\n".join(parts)


def _scale(value: Any) -> float:
    """A share as a percentage, or NaN."""
    return float(value) * 100.0 if isinstance(value, int | float) else float("nan")


def render_backtest_report(
    config: dict[str, Any],
    metrics: dict[str, Any],
    verdicts: dict[str, Any],
    lang: str = DEFAULT_LANG,
) -> str:
    """The full markdown report for one sweep."""
    code = normalise(lang)
    fmt = formats(code)
    pooled = verdicts.get("pooled", [])
    lines: list[str] = [
        text(code, "backtest_heading", title=text(code, "backtest_title")),
        "",
        text(code, "run_id", run_id=verdicts.get("run_id", "")),
        "",
        text(code, "h_verdict"),
        "",
        _stored_summary(verdicts, code) or backtest_summary(pooled, code),
        "",
    ]
    lines += _backtest_method_section(config, metrics, code, fmt)
    lines += _backtest_results_section(pooled, code, fmt)
    lines += _backtest_windows_section(metrics, code, fmt)
    lines += _backtest_calibration_section(pooled, code, fmt)
    lines += _backtest_limits_section(metrics, code)
    return "\n".join(lines).rstrip() + "\n"


def _stored_summary(verdicts: dict[str, Any], lang: Lang) -> str:
    """The verdict paragraph the run stored for this language, if it stored one."""
    return str(verdicts.get(f"summary_{lang}", "") or "")


def _backtest_method_section(
    config: dict[str, Any], metrics: dict[str, Any], lang: Lang, fmt: Format
) -> list[str]:
    """What was measured and how."""
    windows = metrics.get("windows", [])
    return [
        text(lang, "h_backtest_method"),
        "",
        text(
            lang,
            "backtest_windows",
            windows=fmt.integer(len(windows)),
            first=metrics.get("first_test_day"),
            last=metrics.get("last_test_day"),
        ),
        text(lang, "backtest_kind", kind=metrics.get("sweep_kind", "custom")),
        text(
            lang,
            "backtest_models",
            models=", ".join(f"`{name}`" for name in config.get("score_models", [])),
        ),
        text(
            lang,
            "backtest_threshold",
            share=fmt.share_percent(float(config.get("quiet_share", 0.2))),
        ),
        text(
            lang,
            "backtest_bootstrap",
            resamples=fmt.integer(config.get("n_resamples")),
            seed=fmt.integer(config.get("seed")),
        ),
        "",
        text(lang, "backtest_method_note"),
        "",
    ]


def _backtest_results_section(
    pooled: list[dict[str, Any]], lang: Lang, fmt: Format
) -> list[str]:
    """The pooled table: one line per venue and rule."""
    lines = [text(lang, "h_results"), ""]
    lines += table_header(text(lang, "results_table"), align="llrrlrrrrl")
    for row in pooled:
        lines.append(
            f"| {row.get('venue_name')} | `{row.get('model')}` "
            f"| {fmt.integer(row.get('n_windows'))} "
            f"| {fmt.percent(_scale(row.get('benefit')), 0)} "
            f"| {fmt.percent(_scale(row.get('benefit_ci_low')), 0)} … "
            f"{fmt.percent(_scale(row.get('benefit_ci_high')), 0)} "
            f"| {fmt.percent(_scale(row.get('hit_rate')), 0)} "
            f"| {fmt.percent(_scale(row.get('chance_rate')), 0)} "
            f"| {fmt.percent(_scale(row.get('capture')), 0)} "
            f"| {fmt.number(row.get('spearman'), 2)} "
            f"| {fmt.phrase(VERDICT_PHRASES, row.get('verdict'))} |"
        )
    lines += ["", text(lang, "results_note"), ""]
    for row in pooled:
        if str(row.get("verdict")) == "no_detectable_benefit":
            lines.append(
                text(
                    lang,
                    "results_mde",
                    venue_name=row.get("venue_name"),
                    model=row.get("model"),
                    mde=fmt.percent(_scale(row.get("benefit_mde")), 0),
                    windows=fmt.integer(row.get("n_windows")),
                    chance_verdict=fmt.phrase(CHANCE_PHRASES, row.get("hit_verdict")),
                )
            )
    if lines[-1] != "":
        lines.append("")
    return lines


def _backtest_windows_section(metrics: dict[str, Any], lang: Lang, fmt: Format) -> list[str]:
    """Every window, so a pooled number can be checked against its parts."""
    lines = [text(lang, "h_backtest_windows"), ""]
    lines += table_header(text(lang, "windows_table"), align="lllrrrrrr")
    for row in metrics.get("window_results", []):
        benefit = (
            1.0 - float(row["realized_ratio"]) if row.get("realized_ratio") is not None else None
        )
        oracle = 1.0 - float(row["oracle_ratio"]) if row.get("oracle_ratio") is not None else None
        lines.append(
            f"| {row.get('venue_id')} | `{row.get('model')}` | {row.get('test_start')} – "
            f"{row.get('test_end')} | {fmt.integer(row.get('n_eligible'))} "
            f"| {fmt.integer(row.get('k'))} | {fmt.percent(_scale(benefit), 0)} "
            f"| {fmt.percent(_scale(oracle), 0)} "
            f"| {fmt.percent(_scale(row.get('hit_rate')), 0)} "
            f"| {fmt.percent(_scale(row.get('top1_ratio')), 0)} |"
        )
    lines.append("")
    return lines


def _backtest_calibration_section(
    pooled: list[dict[str, Any]], lang: Lang, fmt: Format
) -> list[str]:
    """Do the published probabilities mean what they say."""
    lines = [
        text(lang, "h_calibration"),
        "",
        text(lang, "calibration_note"),
        "",
    ]
    lines += table_header(text(lang, "calibration_table"), align="lllrrr")
    for row in pooled:
        for bucket in row.get("calibration", []):
            if not bucket.get("n"):
                continue
            lines.append(
                f"| {row.get('venue_name')} | `{row.get('model')}` | {bucket.get('bucket')} "
                f"| {fmt.integer(bucket.get('n'))} "
                f"| {fmt.percent(_scale(bucket.get('predicted')), 0)} "
                f"| {fmt.percent(_scale(bucket.get('observed')), 0)} |"
            )
    lines.append("")
    return lines


def _backtest_limits_section(metrics: dict[str, Any], lang: Lang) -> list[str]:
    """What the sweep does not prove."""
    lines = [
        text(lang, "h_backtest_limits"),
        "",
        text(lang, "backtest_limit_windows"),
        text(lang, "backtest_limit_venues"),
        text(lang, "backtest_limit_selection"),
        text(lang, "backtest_limit_hindsight"),
        text(lang, "backtest_limit_events"),
    ]
    if bool(metrics.get("windows_overlap")):
        lines.append(text(lang, "backtest_limit_overlap"))
    lines.append("")
    return lines


__all__ = [
    "backtest_summary",
    "forecast_summary",
    "render_backtest_report",
    "render_forecast_report",
]
