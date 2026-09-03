"""The manifest says the same thing in both languages.

The quality-gate warnings travel from here to the published site's data-quality banner,
which renders in Finnish and in English. A key missing from one table means one set of
readers sees the other language in the middle of their own page, and a dropped placeholder
means a warning that states a problem without the number that identifies it.
"""

from __future__ import annotations

import string

import pytest

from ovf_ingest.strings import EN, FI, LANGUAGES, TEXT, log_text, message, text


def _placeholders(template: str) -> set[str]:
    """The ``{name}`` fields one template expects."""
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_every_language_defines_every_key() -> None:
    """A missing key is a warning one set of readers never gets."""
    assert set(TEXT) == set(LANGUAGES)
    assert set(FI) == set(EN)


@pytest.mark.parametrize("key", sorted(FI))
def test_translations_keep_their_placeholders(key: str) -> None:
    """A dropped placeholder states a problem without identifying it."""
    expected = _placeholders(FI[key])
    assert _placeholders(EN[key]) == expected, f"{key}: placeholders differ"


def test_a_message_is_written_in_every_language() -> None:
    """This is the shape the manifest stores and the site reads."""
    payload = message("visitor_gap", lookback=30, gap=52, venue=1, limit=48)
    assert set(payload) == set(LANGUAGES)
    assert all("52" in value for value in payload.values())
    assert payload["fi"] != payload["en"]


def test_the_log_keeps_english() -> None:
    """A log line is operator-facing, and the rest of this package logs in English."""
    payload = message("negative_ok")
    assert log_text(payload) == text("en", "negative_ok")


def test_an_unknown_key_renders_as_itself() -> None:
    """A missing template shows up as a visible token rather than as silence."""
    assert text("fi", "no_such_key") == "no_such_key"
