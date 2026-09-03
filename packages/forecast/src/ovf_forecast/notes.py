"""The caveats a forecast run writes into ``metrics.json``, in both languages.

These are not report prose. They travel in the data files, the site renders them in its
own language, and until now they were English only: the Finnish pages carried a regex in
``packages/web/src/lib/labels.ts`` that tried to translate them back by matching their
wording. That shim broke the moment a sentence was reworded, and it silently fell through
to English when it did.

Writing both languages at the source removes the guessing. A warning is stored as
``{"fi": ..., "en": ...}`` and every reader picks the key it wants.
"""

from __future__ import annotations

from .i18n import DEFAULT_LANG, LANGUAGES, Lang

FI: dict[str, str] = {
    "thin_origins": "Vain {origins} backtest-origoa mahtui {training_days} päivän "
    "koulutusrajan sisään; suunnitelma pyytää vähintään {minimum}, joten ennustevälien "
    "kvantiilit lepäävät ohuen otoksen varassa.",
    "coverage_out_of_range": "Mallin {model} peittävyys horisontilla {bucket} on {coverage}, "
    "eli hyväksyttävän välin {low}-{high} ulkopuolella.",
    "calendar_gap": "Ylläpidetty kalenteri ei ulotu päivään {date}; niiltä päiviltä oletetaan "
    "ettei pyhiä ole.",
    "stale_origin": "Viimeisin havaittu päivä on {date}, {days} päivää ennen tätä ajoa. Ennuste "
    "lähtee vanhentuneesta datasta.",
    "thin_profile": "Tuntiprofiili lepää {days} havaitun päivän varassa tavanomaisen 56 sijaan.",
    "degraded_sources": "Ingest-manifesti raportoi heikentyneitä lähteitä: {sources}.",
    "skipped_model": "Malli {model} ohitettiin: sen valinnaisia riippuvuuksia ei ole asennettu "
    "tai ne eivät lataudu.",
    "trust_horizon": "Yli 14 vuorokauden horisontit: sää on klimatologiaa ja taso on lukittu "
    "ennusteen origoon.",
    "trust_events": "Päivät joilla on ohjelmistoa tai tapahtuma, jota malli ei ole nähnyt.",
    "trust_new_sensor": "Kaksi ensimmäistä viikkoa uuden venuen tai uuden sensorin "
    "käyttöönotosta.",
    "trust_degraded": "Jaksot joilla ingest-manifesti raportoi heikentyneen lähteen.",
    "trust_holidays": "Koulujen loma-ajat ja juhannus, joista aineistossa on korkeintaan yksi "
    "havainto.",
}

EN: dict[str, str] = {
    "thin_origins": "Only {origins} backtest origins fit the {training_days}-day training "
    "floor; the plan asks for at least {minimum}, so the interval quantiles rest on a thin "
    "sample.",
    "coverage_out_of_range": "Model {model} has {coverage} coverage at horizon {bucket}, "
    "outside the acceptable {low}-{high} range.",
    "calendar_gap": "The maintained calendar does not reach {date}; those days assume no "
    "holiday.",
    "stale_origin": "The last observed day is {date}, {days} days before this run. The forecast "
    "starts from stale data.",
    "thin_profile": "The hourly profile rests on {days} observed days instead of the usual 56.",
    "degraded_sources": "The ingest manifest reports degraded sources: {sources}.",
    "skipped_model": "Model {model} was skipped: its optional dependencies are not installed or "
    "not usable.",
    "trust_horizon": "Horizons past 14 days: the weather is climatology and the level is frozen "
    "at the origin.",
    "trust_events": "Days with programming or an event the model has never seen.",
    "trust_new_sensor": "The first two weeks after a new venue or a new sensor comes online.",
    "trust_degraded": "Periods where the ingest manifest reports a degraded source.",
    "trust_holidays": "School holidays and midsummer, of which this dataset holds at most one "
    "observation.",
}

TEXT: dict[Lang, dict[str, str]] = {"fi": FI, "en": EN}

#: The caveats that hold for every run, in the order the report and the site list them.
DO_NOT_TRUST_KEYS = (
    "trust_horizon",
    "trust_events",
    "trust_new_sensor",
    "trust_degraded",
    "trust_holidays",
)


def note(key: str, **values: object) -> dict[str, str]:
    """One caveat in every language, ready to be stored as it stands."""
    return {lang: _text(lang, key, **values) for lang in LANGUAGES}


def do_not_trust() -> list[dict[str, str]]:
    """The static caveats every run carries."""
    return [note(key) for key in DO_NOT_TRUST_KEYS]


def _text(lang: Lang, key: str, **values: object) -> str:
    """One caveat in one language."""
    template = TEXT[lang].get(key) or TEXT[DEFAULT_LANG].get(key, key)
    return template.format(**values) if values else template


__all__ = ["DO_NOT_TRUST_KEYS", "EN", "FI", "TEXT", "do_not_trust", "note"]
