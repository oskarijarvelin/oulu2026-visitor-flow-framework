"""The two languages have to say the same things.

A translation breaks in two ways, and neither of them raises. A key can be missing, in
which case that sentence silently falls back to the other language and the reader sees one
Finnish paragraph in an English report. Or a placeholder can be dropped, in which case the
sentence renders without its number and reads as a confident claim with no evidence in it.

These tests are what a type checker would give for a dataclass of translated fields, plus
the placeholder check, which is the half a type checker cannot do.
"""

from __future__ import annotations

import string
from typing import Any

import pytest

from ovf_forecast import cli_strings, notes
from ovf_forecast.evaluation import strings as evaluation_strings
from ovf_forecast.i18n import LANGUAGES, Format, formats, normalise, table_header
from ovf_forecast.quiet import strings as quiet_strings

TABLES = {
    "evaluation": evaluation_strings.TEXT,
    "quiet": quiet_strings.TEXT,
    "notes": notes.TEXT,
    "cli": cli_strings.TEXT,
}

PHRASE_TABLES = {
    "evaluation.verdict": evaluation_strings.VERDICT_PHRASES,
    "evaluation.calibration": evaluation_strings.CALIBRATION_PHRASES,
    "evaluation.bias": evaluation_strings.BIAS_PHRASES,
    "evaluation.weather": evaluation_strings.WEATHER_LABELS,
    "quiet.verdict": quiet_strings.VERDICT_PHRASES,
    "quiet.chance": quiet_strings.CHANCE_PHRASES,
    "quiet.status": quiet_strings.STATUS_PHRASES,
}


def _placeholders(template: str) -> set[str]:
    """The ``{name}`` fields one template expects."""
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


@pytest.mark.parametrize("name", sorted(TABLES))
def test_every_language_defines_every_key(name: str) -> None:
    """A missing key is a sentence one set of readers never gets."""
    table = TABLES[name]
    assert set(table) == set(LANGUAGES), f"{name}: a language table is missing"
    expected = set(table["fi"])
    for lang in LANGUAGES:
        missing = expected - set(table[lang])
        extra = set(table[lang]) - expected
        assert not missing, f"{name}/{lang}: missing keys {sorted(missing)}"
        assert not extra, f"{name}/{lang}: keys with no Finnish original {sorted(extra)}"


@pytest.mark.parametrize("name", sorted(TABLES))
def test_translations_keep_their_placeholders(name: str) -> None:
    """A dropped placeholder renders a claim without the number that supports it."""
    table = TABLES[name]
    for key, template in table["fi"].items():
        expected = _placeholders(template)
        for lang in LANGUAGES:
            found = _placeholders(table[lang][key])
            assert found == expected, f"{name}/{lang}/{key}: placeholders {found} != {expected}"


@pytest.mark.parametrize("name", sorted(PHRASE_TABLES))
def test_phrase_tables_cover_every_language(name: str) -> None:
    """A verdict word that only exists in one language renders as its raw key."""
    table = PHRASE_TABLES[name]
    assert set(table) == set(LANGUAGES), f"{name}: a language is missing"
    expected = set(table["fi"])
    for lang in LANGUAGES:
        assert set(table[lang]) == expected, f"{name}/{lang}: different phrase keys"


def test_no_translation_is_left_as_a_copy_of_the_other() -> None:
    """An untranslated sentence is a placeholder somebody forgot, not a translation.

    Some keys are legitimately identical in both languages: a heading that is only a venue
    name and a number, a lone full stop. Those are short. A long identical string is a
    copy-paste that never got translated.
    """
    for name, table in TABLES.items():
        for key, finnish in table["fi"].items():
            english = table["en"][key]
            if len(finnish) > 40:
                assert finnish != english, f"{name}/{key}: English is a copy of the Finnish"


def test_a_number_reads_the_way_its_language_writes_numbers() -> None:
    """Finnish groups with a space and decimals with a comma; English does the opposite."""
    finnish, english = formats("fi"), formats("en")
    assert finnish.number(1234.5) == "1 234,5"
    assert english.number(1234.5) == "1,234.5"
    assert finnish.signed(-2.0) == "-2,0"
    assert english.percent(12.5) == "12.5 %"
    assert finnish.integer(1000) == "1 000"


def test_a_missing_number_is_a_dash_in_both_languages() -> None:
    """Every formatter reads straight out of JSON, where a missing value is null."""
    for lang in LANGUAGES:
        fmt = formats(lang)
        assert fmt.number(None) == "–"
        assert fmt.signed(float("nan")) == "–"
        assert fmt.percent("not a number") == "–"


def test_a_day_is_written_the_way_each_language_writes_days() -> None:
    """``ma 5.10.`` and ``Mon 5 Oct`` are the same day and neither reads in the other."""
    from datetime import date

    day = date(2026, 10, 5)
    assert formats("fi").day(day) == "ma 5.10."
    assert formats("en").day(day) == "Mon 5 Oct"
    assert formats("fi").month(2026, 10) == "lokakuu 2026"
    assert formats("en").month_label("2026-10") == "October 2026"


def test_an_unknown_language_falls_back_rather_than_failing() -> None:
    """A report in the wrong language is recoverable; a run that writes none is not."""
    assert normalise("sv") == "fi"
    assert normalise(None) == "fi"
    assert normalise("EN") == "en"
    assert isinstance(formats("sv"), Format)


def test_a_table_header_cannot_disagree_with_its_own_rule_line() -> None:
    """The separator is derived, so a translated header keeps its column count."""
    header, rule = table_header("A | B | C", align="lr")
    assert header == "| A | B | C |"
    assert rule == "| --- | ---: | --- |"
    for lang in LANGUAGES:
        cells = evaluation_strings.TEXT[lang]["daily_table"]
        head, line = table_header(cells)
        assert head.count("|") == line.count("|"), f"{lang}: header and rule disagree"


def test_a_caveat_is_written_in_every_language() -> None:
    """``metrics.json`` carries the caveats, and the site renders them in either language."""
    payload: dict[str, str] = notes.note("stale_origin", date="2026-05-22", days=94)
    assert set(payload) == set(LANGUAGES)
    assert "2026-05-22" in payload["fi"] and "2026-05-22" in payload["en"]
    every: list[dict[str, Any]] = list(notes.do_not_trust())
    assert len(every) == len(notes.DO_NOT_TRUST_KEYS)
    assert all(set(item) == set(LANGUAGES) for item in every)
