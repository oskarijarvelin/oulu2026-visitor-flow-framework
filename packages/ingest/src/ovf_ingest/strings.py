"""What a run writes into the manifest, in both languages.

The quality-gate details end up on the published site's data-quality banner, which is
rendered in Finnish and in English. Storing them in one language meant one set of readers
saw untranslated text in the middle of their own page; the site tried to patch that with a
regular expression that matched the English wording, and that broke whenever a sentence
was reworded.

So a gate detail is stored as ``{"fi": ..., "en": ...}`` and every reader picks its key.
The structured log keeps English, because a log line is operator-facing and the rest of
this package logs in English.

This module deliberately duplicates the two-language machinery that ``ovf_forecast`` has
rather than importing it. The parts share no code by design: their only connection is the
file contract in ``docs/FRAMEWORK_PLAN.md``.
"""

from __future__ import annotations

from typing import Literal

Lang = Literal["fi", "en"]

LANGUAGES: tuple[Lang, ...] = ("fi", "en")
DEFAULT_LANG: Lang = "fi"
LOG_LANG: Lang = "en"

FI: dict[str, str] = {
    "visitor_gap_empty": "Ei kävijärivejä tarkistettavaksi",
    "visitor_gap": "Pisin kävijäaukko viimeisten {lookback} päivän aikana on {gap} h "
    "(venue {venue}), raja {limit} h",
    "weather_empty": "Ei säärivejä tarkistettavaksi",
    "weather_coverage": "Heikoin säädatan kattavuus on {coverage} (venue {venue}), "
    "vähimmäisvaatimus {minimum}",
    "capacity_empty": "Ei päivätason kävijärivejä tarkistettavaksi",
    "capacity_ok": "Yksikään päivä ei ylitä rajaa capacity * 24 * 4",
    "capacity_exceeded": "{count} päivää ylittää rajan capacity * 24 * 4: {offenders}",
    "negative_ok": "Ei negatiivisia laskuriarvoja",
    "negative_found": "Negatiivisia laskureita löytyi: {offenders}",
    "gate_warning": "{gate}: {detail}",
    "rejected_tables": "Hylätyt taulut: {tables}",
    "source_warning": "Lähde {source}: {status}",
    "source_warning_error": "Lähde {source}: {status} ({error})",
}

EN: dict[str, str] = {
    "visitor_gap_empty": "No visitor rows to check",
    "visitor_gap": "Longest visitor gap in the last {lookback} days is {gap} h "
    "(venue {venue}), limit {limit} h",
    "weather_empty": "No weather rows to check",
    "weather_coverage": "Lowest weather coverage is {coverage} (venue {venue}), "
    "minimum {minimum}",
    "capacity_empty": "No daily visitor rows to check",
    "capacity_ok": "No day exceeds capacity * 24 * 4",
    "capacity_exceeded": "{count} day(s) exceed capacity * 24 * 4: {offenders}",
    "negative_ok": "No negative counter values",
    "negative_found": "Negative counters found: {offenders}",
    "gate_warning": "{gate}: {detail}",
    "rejected_tables": "rejected tables: {tables}",
    "source_warning": "Source {source}: {status}",
    "source_warning_error": "Source {source}: {status} ({error})",
}

TEXT: dict[Lang, dict[str, str]] = {"fi": FI, "en": EN}


def text(lang: Lang, key: str, **values: object) -> str:
    """One message in one language."""
    template = TEXT[lang].get(key) or TEXT[DEFAULT_LANG].get(key, key)
    return template.format(**values) if values else template


def message(key: str, **values: object) -> dict[str, str]:
    """One message in every language, ready to be stored as it stands."""
    return {lang: text(lang, key, **values) for lang in LANGUAGES}


def log_text(payload: dict[str, str]) -> str:
    """The line the structured log carries for a stored message."""
    return payload.get(LOG_LANG) or payload.get(DEFAULT_LANG) or ""


__all__ = [
    "DEFAULT_LANG",
    "EN",
    "FI",
    "LANGUAGES",
    "LOG_LANG",
    "TEXT",
    "Lang",
    "log_text",
    "message",
    "text",
]
