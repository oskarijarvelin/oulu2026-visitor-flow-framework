"""The two languages every run writes its prose in, and the conventions each one asks for.

A number is not language-neutral. Finnish writes ``1 234,5`` and English ``1,234.5``, and a
report that mixes the two reads as a bug even when the arithmetic is right. The same goes
for a date: ``ma 5.10.`` and ``Mon 5 Oct`` are the same day, and neither is readable in the
other language. Everything that turns a stored value into prose therefore goes through
:class:`Format`, which is bound to one language and knows nothing else.

The phrase tables are dictionaries keyed by language rather than by an if statement at the
call site, so adding a third language is a table row and not a search through the renderers.
Every table is exhaustive over :data:`LANGUAGES`; a lookup that misses falls back to the key
itself, which shows up in the output as a visible untranslated token rather than as silence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

Lang = Literal["fi", "en"]

LANGUAGES: tuple[Lang, ...] = ("fi", "en")
DEFAULT_LANG: Lang = "fi"

#: What a missing number renders as, in both languages.
NA = "–"

WEEKDAY_SHORT: dict[Lang, tuple[str, ...]] = {
    "fi": ("ma", "ti", "ke", "to", "pe", "la", "su"),
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
}

MONTH_NAMES: dict[Lang, tuple[str, ...]] = {
    "fi": (
        "tammikuu",
        "helmikuu",
        "maaliskuu",
        "huhtikuu",
        "toukokuu",
        "kesäkuu",
        "heinäkuu",
        "elokuu",
        "syyskuu",
        "lokakuu",
        "marraskuu",
        "joulukuu",
    ),
    "en": (
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
}

MONTH_SHORT: dict[Lang, tuple[str, ...]] = {
    "fi": tuple(f"{index}." for index in range(1, 13)),
    "en": ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
}

YES_NO: dict[Lang, tuple[str, str]] = {"fi": ("kyllä", "ei"), "en": ("yes", "no")}


def normalise(lang: str | None) -> Lang:
    """Accept whatever a caller passes and return a language this package knows.

    An unknown language is the default rather than an error: a report in the wrong language
    is recoverable, a run that refuses to write one is not.
    """
    candidate = str(lang or "").strip().lower()
    return candidate if candidate in LANGUAGES else DEFAULT_LANG


@dataclass(frozen=True)
class Format:
    """Numbers, dates and booleans in one language's conventions.

    Bound to a language once and passed down through a renderer, so no section builder has
    to remember which language it is rendering. Every method tolerates ``None``, a string
    and a NaN, because these read values straight out of a stored JSON payload.
    """

    lang: Lang

    # -- numbers --------------------------------------------------------------------

    def number(self, value: Any, digits: int = 1) -> str:
        """A number in this language's separators, or a dash when it is missing."""
        numeric = _as_float(value)
        if numeric != numeric:
            return NA
        grouped = f"{numeric:,.{digits}f}"
        if self.lang == "fi":
            # A non-breaking space between thousands and a comma for the decimal, which is
            # what Finnish typography asks for and what the old renderer already produced.
            return grouped.replace(",", " ").replace(".", ",")
        return grouped

    def signed(self, value: Any, digits: int = 1) -> str:
        """A number with an explicit sign, so a bias reads as a direction."""
        numeric = _as_float(value)
        if numeric != numeric:
            return NA
        return ("+" if numeric >= 0 else "") + self.number(numeric, digits)

    def percent(self, value: Any, digits: int = 1) -> str:
        """A percentage, with the space before the sign that both languages use here."""
        formatted = self.number(value, digits)
        return NA if formatted == NA else f"{formatted} %"

    def integer(self, value: Any) -> str:
        """A rounded count."""
        return self.number(value, 0)

    def share_percent(self, value: Any, digits: int = 0) -> str:
        """A 0-1 share rendered as a percentage."""
        numeric = _as_float(value)
        return NA if numeric != numeric else self.percent(numeric * 100.0, digits)

    # -- dates ----------------------------------------------------------------------

    def day(self, value: date | None) -> str:
        """``ma 5.10.`` or ``Mon 5 Oct``: the shape a calendar entry takes."""
        if value is None:
            return NA
        weekday = WEEKDAY_SHORT[self.lang][value.weekday()]
        if self.lang == "fi":
            return f"{weekday} {value.day}.{value.month}."
        return f"{weekday} {value.day} {MONTH_SHORT['en'][value.month - 1]}"

    def month(self, year: int, month: int) -> str:
        """``lokakuu 2026`` or ``October 2026``."""
        return f"{MONTH_NAMES[self.lang][month - 1]} {year}"

    def month_label(self, text: Any) -> str:
        """A stored ``YYYY-MM`` as a month name, or the raw string when it is not one."""
        raw = str(text or "")
        year, _, month = raw.partition("-")
        if year.isdigit() and month.isdigit() and 1 <= int(month) <= 12:
            return self.month(int(year), int(month))
        return raw

    # -- words ----------------------------------------------------------------------

    def yes_no(self, flag: Any) -> str:
        """A stored boolean as a word."""
        yes, no = YES_NO[self.lang]
        return yes if bool(flag) else no

    def phrase(self, table: dict[Lang, dict[str, str]], key: Any) -> str:
        """One phrase from a per-language table, falling back to the raw key."""
        text = str(key)
        return table[self.lang].get(text, text)

    def join(self, items: list[str], empty: str) -> str:
        """A comma-separated list, or a stated fallback when there is nothing to list."""
        return ", ".join(item for item in items if item) or empty


FORMATS: dict[Lang, Format] = {lang: Format(lang) for lang in LANGUAGES}


def formats(lang: str | None = DEFAULT_LANG) -> Format:
    """The formatter for one language."""
    return FORMATS[normalise(lang)]


def _as_float(value: Any) -> float:
    """One stored value as a float, with every missing marker mapping to NaN."""
    if value is None or isinstance(value, bool):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_day(text: Any) -> date | None:
    """Read an ISO day back out of a stored payload."""
    try:
        return date.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None


def table_header(cells: str, align: str = "") -> list[str]:
    """A markdown table's two opening lines from one ``a | b | c`` string.

    The separator row is derived rather than written out, so a translated header cannot end
    up with a different column count from its own rule line. ``align`` is a per-column
    string of ``l`` and ``r``; anything shorter than the header defaults to left.
    """
    names = [cell.strip() for cell in cells.split("|")]
    rules = [
        "---:" if index < len(align) and align[index] == "r" else "---"
        for index in range(len(names))
    ]
    return ["| " + " | ".join(names) + " |", "| " + " | ".join(rules) + " |"]


def bilingual(builder: Any) -> dict[str, str]:
    """Run one prose builder in both languages and key the results by language.

    Used wherever a payload carries the same sentence twice, such as a warning that has to
    survive into a report in either language.
    """
    return {lang: str(builder(lang)) for lang in LANGUAGES}


__all__ = [
    "DEFAULT_LANG",
    "LANGUAGES",
    "MONTH_NAMES",
    "NA",
    "WEEKDAY_SHORT",
    "Format",
    "Lang",
    "bilingual",
    "formats",
    "normalise",
    "parse_day",
    "table_header",
]
