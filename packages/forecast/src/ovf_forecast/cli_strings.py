"""What the command line itself says, in both languages.

The reports are the deliverable, but the command line is what somebody actually reads at
the moment they run something, and half a bilingual tool is a tool that still tells you
"tuntematon ajo" when you asked for English. These are the few sentences the commands print
around a result: the errors, the saved paths and the column headings of the listings.

The verdict paragraphs are not here. Those are built from the run's own numbers and stored
with it, so the command prints back what it wrote rather than composing a second version.
"""

from __future__ import annotations

from .i18n import DEFAULT_LANG, Lang

FI: dict[str, str] = {
    "error": "virhe: {message}",
    "saved": "  tallennettu: {path}",
    "pooled_saved": "  kooste:      {path}",
    "no_eval_runs_hint": "ei tallennettuja arviointiajoja, aja ensin "
    "'python -m ovf_forecast evaluate'",
    "no_eval_runs": "ei tallennettuja arviointiajoja",
    "need_id_or_pooled": "anna joko --id <run_id> tai --pooled",
    "need_id_or_latest": "anna joko --id <run_id> tai --latest",
    "unknown_run": "tuntematon ajo: {run_id}",
    "no_windows_scored": "yhtään ikkunaa ei voitu pisteyttää",
    "no_quiet_runs": "ei tallennettuja hiljaisten päivien ajoja",
    "column_kind": "laji",
    "column_created": "luotu",
    "column_verdict": "verdikti",
    "column_content": "sisältö",
    "no_metrics": "venue {venue_id}: ei vielä mittareita, aja ensin 'python -m ovf_forecast run'",
}

EN: dict[str, str] = {
    "error": "error: {message}",
    "saved": "  saved:  {path}",
    "pooled_saved": "  pooled: {path}",
    "no_eval_runs_hint": "no stored evaluation runs; run 'python -m ovf_forecast evaluate' first",
    "no_eval_runs": "no stored evaluation runs",
    "need_id_or_pooled": "give either --id <run_id> or --pooled",
    "need_id_or_latest": "give either --id <run_id> or --latest",
    "unknown_run": "unknown run: {run_id}",
    "no_windows_scored": "no window could be scored",
    "no_quiet_runs": "no stored quiet-day runs",
    "column_kind": "kind",
    "column_created": "created",
    "column_verdict": "verdict",
    "column_content": "content",
    "no_metrics": "venue {venue_id}: no metrics yet, run 'python -m ovf_forecast run' first",
}

TEXT: dict[Lang, dict[str, str]] = {"fi": FI, "en": EN}


def text(lang: Lang, key: str, **values: object) -> str:
    """One command-line message in one language."""
    template = TEXT[lang].get(key) or TEXT[DEFAULT_LANG].get(key, key)
    return template.format(**values) if values else template


__all__ = ["EN", "FI", "TEXT", "text"]
