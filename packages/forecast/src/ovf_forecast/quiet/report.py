"""The human-readable output, in Finnish, built from exactly what gets stored.

The renderer reads the same ``config``, ``metrics`` and ``verdicts`` payloads that are
written to disk, so the prose and the JSON cannot drift apart. Nothing is recomputed
here.

The order of a forecast report is the order somebody reads it in. The dates come first,
because that is the question. The probability sits next to every date, because a list of
six dates with no probability invites the reader to treat the first one as certain. The
measured reliability comes before the tables, because a recommendation from a rule that
has never beaten chance on this venue should be read differently from one that has.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from ..evaluation.report import NA, integer, number, percent, signed

FORECAST_TITLE = "Kuukauden hiljaisimmat päivät"
BACKTEST_TITLE = "Hiljaisten päivien ennustemallin luotettavuus"

WEEKDAY_SHORT_FI = ("ma", "ti", "ke", "to", "pe", "la", "su")
MONTH_NAMES_FI = (
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
)

VERDICT_PHRASES = {
    "useful": "hyöty on todennettu",
    "no_detectable_benefit": "hyötyä ei ole todennettu",
    "harmful": "valinta osuu keskimääräistä vilkkaampiin päiviin",
}
CHANCE_PHRASES = {
    "better_than_chance": "osuvuus ylittää satunnaisvalinnan",
    "like_chance": "osuvuus ei eroa satunnaisvalinnasta",
    "worse_than_chance": "osuvuus jää satunnaisvalinnan alle",
}
STATUS_PHRASES = {
    "open": "ehdokas",
    "closed_weekday": "suljettu arkipäivä",
    "closed_holiday": "suljettu pyhäpäivä",
    "no_visitors": "ei kävijöitä",
    "incomplete_day": "vajaa mittauspäivä",
    "unobserved": "ei havaintoa",
}


def fi_month(year: int, month: int) -> str:
    """``lokakuu 2026``."""
    return f"{MONTH_NAMES_FI[month - 1]} {year}"


def fi_day(day: date) -> str:
    """``ma 5.10.``, the shape a Finnish calendar entry takes."""
    return f"{WEEKDAY_SHORT_FI[day.weekday()]} {day.day}.{day.month}."


def parse_day(text: Any) -> date | None:
    """Read an ISO day back out of a stored payload."""
    try:
        return date.fromisoformat(str(text))
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------------------
# Forecast
# --------------------------------------------------------------------------------------


def forecast_summary_fi(venue: dict[str, Any], reliability: dict[str, Any] | None) -> str:
    """The one paragraph the command prints: the dates, the threshold, the confidence."""
    quiet = venue.get("quiet_set", {})
    days = [parse_day(item) for item in quiet.get("dates", [])]
    listed = ", ".join(fi_day(day) for day in days if day is not None) or "ei yhtään ehdokasta"
    month = str(venue.get("month", ""))
    year, _, month_number = month.partition("-")
    label = fi_month(int(year), int(month_number)) if month_number.isdigit() else month
    gap = quiet.get("mean_ratio")
    quieter = percent((1.0 - float(gap)) * 100.0, 0) if isinstance(gap, int | float) else NA
    sentences = [
        f"{venue.get('venue_name')} ({venue.get('venue_id')}), {label}: hiljaisimmat päivät ovat "
        f"{listed}.",
        f"Kynnys on kuukauden hiljaisin viidennes, {integer(quiet.get('k'))} päivää "
        f"{integer(quiet.get('n_eligible'))} ehdokkaasta, ja malli erottaa ne {quieter} "
        "mediaanipäivän alapuolelle.",
    ]
    best = _most_certain(venue)
    if best is not None:
        day, probability = best
        sentences.append(
            f"Varmin valinta on {fi_day(day)}, jonka todennäköisyys kuulua hiljaisimpiin on "
            f"{percent(probability * 100.0, 0)}."
        )
    if not quiet.get("is_material", False):
        sentences.append(
            "Malli ei kuitenkaan erottele kuukauden päiviä merkittävästi: hiljaisin viidennes jää "
            "alle 15 % mediaanipäivän alapuolelle, joten järjestys kannattaa lukea suuntaa "
            "antavana."
        )
    sentences.append(_reliability_sentence(venue, reliability))
    return " ".join(sentences)


def _most_certain(venue: dict[str, Any]) -> tuple[date, float] | None:
    """The quiet day with the highest selection probability."""
    best: tuple[date, float] | None = None
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


def _reliability_sentence(venue: dict[str, Any], reliability: dict[str, Any] | None) -> str:
    """What the stored sweep says about this venue and this rule, if anything."""
    if reliability is None:
        return (
            "Mallin luotettavuutta ei ole mitattu tässä repositoriossa: aja "
            "'python -m ovf_forecast quiet backtest' ennen kuin suositukseen nojataan."
        )
    verdict = str(reliability.get("verdict", ""))
    benefit = _scale(reliability.get("benefit"))
    low = _scale(reliability.get("benefit_ci_low"))
    high = _scale(reliability.get("benefit_ci_high"))
    measured = (
        f"{percent(benefit, 0)} (95 % väli {percent(low, 0)} … {percent(high, 0)})"
        if all(value == value for value in (benefit, low, high))
        else NA
    )
    return (
        f"Mitattu luotettavuus ({integer(reliability.get('n_windows'))} ikkunaa, ajo "
        f"`{reliability.get('run_id', '')}`): valitut päivät olivat keskimäärin {measured} "
        f"mediaanipäivää hiljaisempia, eli {VERDICT_PHRASES.get(verdict, verdict)}."
    )


def render_forecast_report(
    config: dict[str, Any], metrics: dict[str, Any], verdicts: dict[str, Any]
) -> str:
    """The full markdown report for one month."""
    lines: list[str] = [
        f"# {FORECAST_TITLE}: {_month_label(metrics)}",
        "",
        f"Ajon tunniste: `{verdicts.get('run_id', '')}`",
        "",
        "## 1. Vastaus",
        "",
    ]
    for venue in metrics.get("venues", []):
        lines.append(forecast_summary_fi(venue, _reliability_for(verdicts, venue)))
        lines.append("")
    lines += _forecast_method_section(config)
    for venue in metrics.get("venues", []):
        lines += _forecast_venue_section(venue)
    lines += _forecast_limits_section()
    return "\n".join(lines).rstrip() + "\n"


def _month_label(metrics: dict[str, Any]) -> str:
    """``lokakuu 2026`` from the stored month string."""
    month = str(metrics.get("month", ""))
    year, _, number_text = month.partition("-")
    return fi_month(int(year), int(number_text)) if number_text.isdigit() else month


def _reliability_for(verdicts: dict[str, Any], venue: dict[str, Any]) -> dict[str, Any] | None:
    """The stored sweep row matching this venue and rule."""
    for row in verdicts.get("reliability", []):
        matches = row.get("venue_id") == venue.get("venue_id")
        if matches and row.get("model") == venue.get("score_model"):
            return dict(row)
    return None


def _forecast_method_section(config: dict[str, Any]) -> list[str]:
    """How the answer was produced, in enough detail to reproduce it."""
    return [
        "## 2. Miten luku on muodostettu",
        "",
        f"- Pisteytyssääntö: `{config.get('score_model')}`",
        f"- Kynnys: kuukauden hiljaisin {percent(float(config.get('quiet_share', 0.2)) * 100.0, 0)} "
        "ehdokaspäivistä, vähintään 3 ja enintään 10 päivää",
        f"- Simulaatioita todennäköisyyttä kohden: {integer(config.get('n_simulations'))}",
        f"- Siemenluku: {integer(config.get('seed'))}",
        "",
        "Pisteluku on kävijämäärän suuruusluokassa, mutta se on järjestysluku eikä ennuste: "
        "kaikki alla olevat suhdeluvut on jaettu kuukauden mediaanipäivällä, jolloin tason "
        "virhe kumoutuu eikä vaikuta järjestykseen.",
        "",
        "Mallin erottelu ja toteutuva ero ovat kaksi eri lukua, eikä toinen ennusta toista. "
        "Pisteluku on ehdollinen keskiarvo, joten se on aina toteumaa tasaisempi: alla oleva "
        "suhdeluku kertoo, kuinka kauas malli päivät erottaa, ei kuinka hiljaisia ne "
        "toteutuvat olemaan. Toteutuvan eron arvio saadaan vain mittaamalla, ja se on "
        "komennon `quiet backtest` tulos.",
        "",
    ]


def _forecast_venue_section(venue: dict[str, Any]) -> list[str]:
    """One venue's quiet set, whole month table and setup."""
    quiet = venue.get("quiet_set", {})
    eligibility = venue.get("eligibility", {})
    residuals = venue.get("residuals", {})
    lines = [
        f"## 3. {venue.get('venue_name')} ({venue.get('venue_id')})",
        "",
        f"Origo {venue.get('origin')}, sääntö `{venue.get('score_model')}`. "
        f"Ehdokaspäiviä {integer(quiet.get('n_eligible'))}, hiljaisia päiviä "
        f"{integer(quiet.get('k'))}. Kynnysarvo on {number(quiet.get('cut'))} kävijätapahtumaa, "
        f"eli {number(float(quiet.get('cut_ratio', float('nan'))) * 100.0, 0)} % "
        "mediaanipäivästä.",
        "",
        "### Hiljaisimmat päivät",
        "",
        "| Päivä | Sija | Suhde mediaaniin | Todennäköisyys | Samanarvoisia | Pyhä | Lämpötila | "
        "Sade |",
        "| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in venue.get("days", []):
        if not row.get("is_quiet"):
            continue
        lines.append(_day_row(row))
    lines += [
        "",
        "### Koko kuukausi",
        "",
        "| Päivä | Tila | Sija | Suhde mediaaniin | Todennäköisyys |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in venue.get("days", []):
        day = parse_day(row.get("date"))
        status = STATUS_PHRASES.get(str(row.get("status")), str(row.get("status")))
        lines.append(
            f"| {fi_day(day) if day else NA} | {status} | {row.get('rank') or NA} | "
            f"{_ratio(row.get('ratio'))} | {_probability(row.get('probability'))} |"
        )
    closed = eligibility.get("closed_weekdays") or []
    lines += [
        "",
        "### Lähtötiedot",
        "",
        f"- Suljetut arkipäivät: {', '.join(WEEKDAY_SHORT_FI[day] for day in closed) or 'ei yhtään'}",
        f"- Pyhäpäiväkerroin: {number(eligibility.get('holiday_factor'), 2)} "
        f"({integer(eligibility.get('holiday_observations'))} havaintoa)",
        f"- Jäännösjakauma: {'mitattu' if residuals.get('measured') else 'oletushajonta'}, "
        f"{integer(residuals.get('n'))} havaintoa",
        "",
    ]
    warnings = venue.get("warnings", [])
    if warnings:
        lines += ["### Varaukset", ""]
        lines += [f"- {warning}" for warning in warnings]
        lines.append("")
    return lines


def _day_row(row: dict[str, Any]) -> str:
    """One line of the quiet-set table."""
    day = parse_day(row.get("date"))
    tie = row.get("tie_size") or 1
    return (
        f"| {fi_day(day) if day else NA} | {row.get('rank') or NA} | {_ratio(row.get('ratio'))} | "
        f"{_probability(row.get('probability'))} | {integer(tie) if int(tie) > 1 else NA} | "
        f"{row.get('holiday_name') or NA} | {number(row.get('temp_mean'))} | "
        f"{number(row.get('precip_sum'))} |"
    )


def _ratio(value: Any) -> str:
    """A within-month ratio as a percentage of the median day."""
    return NA if not isinstance(value, int | float) else percent(float(value) * 100.0, 0)


def _probability(value: Any) -> str:
    """A selection probability as a percentage."""
    return NA if not isinstance(value, int | float) else percent(float(value) * 100.0, 0)


def _forecast_limits_section() -> list[str]:
    """What the answer does not claim."""
    return [
        "## 4. Mitä tämä ei kerro",
        "",
        "- **Pisteluku ei ole kävijäennuste.** Se on järjestysluku. Tason ennustamiseen on "
        "`python -m ovf_forecast run`, ja sen tarkkuus mitataan erikseen komennolla `evaluate`.",
        "- **Todennäköisyys koskee järjestystä, ei kävijämäärää.** \"70 %\" tarkoittaa, että "
        "päivä päätyi hiljaisimpien joukkoon 70 %:ssa simuloiduista kuukausista.",
        "- **Malli ei tunne tapahtumakalenteria.** Yksittäinen konsertti tai ryhmävaraus "
        "kääntää hiljaisen päivän vilkkaaksi, eikä tässä käytetyssä datassa ole tietoa siitä.",
        "- **Sää on taustatietoa.** Se on taulukossa ihmisen päätöksen tueksi, mutta se ei "
        "vaikuta järjestykseen: mitattuna se ei parantanut sitä.",
        "- **Suljetut päivät eivät ole hiljaisia päiviä.** Ne on rajattu ehdokkaista pois, "
        "koska tapahtumaa ei voi järjestää suljetussa kohteessa.",
        "",
    ]


# --------------------------------------------------------------------------------------
# Backtest
# --------------------------------------------------------------------------------------


def backtest_summary_fi(pooled: list[dict[str, Any]]) -> str:
    """The verdict the sweep prints: one line per venue and rule.

    A list rather than a paragraph, because five rules on two venues is ten verdicts and
    a wall of prose is where a reader stops looking for the one that concerns them.
    """
    if not pooled:
        return "Yhtään ikkunaa ei voitu pisteyttää."
    parts: list[str] = []
    for row in pooled:
        benefit = row.get("benefit")
        low, high = row.get("benefit_ci_low"), row.get("benefit_ci_high")
        verdict = VERDICT_PHRASES.get(str(row.get("verdict")), str(row.get("verdict")))
        parts.append(
            f"- {row.get('venue_name')} ({row.get('venue_id')}) / `{row.get('model')}`: valitut "
            f"päivät olivat {percent(_scale(benefit), 0)} mediaanipäivää hiljaisempia "
            f"(95 % väli {percent(_scale(low), 0)} … {percent(_scale(high), 0)}, "
            f"{integer(row.get('n_windows'))} ikkunaa), {verdict}; osuvuus "
            f"{percent(_scale(row.get('hit_rate')), 0)} kun satunnaisvalinta antaisi "
            f"{percent(_scale(row.get('chance_rate')), 0)}."
        )
    return "\n".join(parts)


def _scale(value: Any) -> float:
    """A share as a percentage, or NaN."""
    return float(value) * 100.0 if isinstance(value, int | float) else float("nan")


def render_backtest_report(
    config: dict[str, Any], metrics: dict[str, Any], verdicts: dict[str, Any]
) -> str:
    """The full markdown report for one sweep."""
    pooled = verdicts.get("pooled", [])
    lines: list[str] = [
        f"# {BACKTEST_TITLE}",
        "",
        f"Ajon tunniste: `{verdicts.get('run_id', '')}`",
        "",
        "## 1. Verdikti",
        "",
        backtest_summary_fi(pooled),
        "",
    ]
    lines += _backtest_method_section(config, metrics)
    lines += _backtest_results_section(pooled)
    lines += _backtest_windows_section(metrics)
    lines += _backtest_calibration_section(pooled)
    lines += _backtest_limits_section(metrics)
    return "\n".join(lines).rstrip() + "\n"


def _backtest_method_section(config: dict[str, Any], metrics: dict[str, Any]) -> list[str]:
    """What was measured and how."""
    windows = metrics.get("windows", [])
    return [
        "## 2. Menetelmä",
        "",
        f"- Ikkunoita: {integer(len(windows))} "
        f"({metrics.get('first_test_day')} – {metrics.get('last_test_day')})",
        f"- Ikkunatyyppi: {metrics.get('sweep_kind', 'custom')}",
        f"- Säännöt: {', '.join(f'`{name}`' for name in config.get('score_models', []))}",
        f"- Kynnys: hiljaisin {percent(float(config.get('quiet_share', 0.2)) * 100.0, 0)} "
        "ehdokaspäivistä",
        f"- Bootstrap-toistoja: {integer(config.get('n_resamples'))}, "
        f"siemenluku {integer(config.get('seed'))}",
        "",
        "Jokainen ikkuna opetetaan origoonsa asti, nimetään sen jälkeen jakson hiljaisimmat "
        "päivät ja avataan vasta sitten toteuma. Luottamusväli arvotaan kokonaisista "
        "ikkunoista, ei päivistä: saman kuukauden päivät jakavat origon, opetusjakson ja "
        "sään, eivätkä ole toisistaan riippumattomia havaintoja.",
        "",
    ]


def _backtest_results_section(pooled: list[dict[str, Any]]) -> list[str]:
    """The pooled table: one line per venue and rule."""
    lines = [
        "## 3. Tulokset",
        "",
        "| Kohde | Sääntö | Ikkunoita | Hyöty | 95 % väli | Osuvuus | Satunnais | Talteen | "
        "Spearman | Verdikti |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in pooled:
        lines.append(
            f"| {row.get('venue_name')} | `{row.get('model')}` | {integer(row.get('n_windows'))} | "
            f"{percent(_scale(row.get('benefit')), 0)} | "
            f"{percent(_scale(row.get('benefit_ci_low')), 0)} … "
            f"{percent(_scale(row.get('benefit_ci_high')), 0)} | "
            f"{percent(_scale(row.get('hit_rate')), 0)} | "
            f"{percent(_scale(row.get('chance_rate')), 0)} | "
            f"{percent(_scale(row.get('capture')), 0)} | {number(row.get('spearman'), 2)} | "
            f"{VERDICT_PHRASES.get(str(row.get('verdict')), '')} |"
        )
    lines += [
        "",
        "**Hyöty** on 1 − (valittujen päivien keskiarvo ÷ kuukauden mediaanipäivä): kuinka "
        "paljon hiljaisempi suositus oli kuin mielivaltainen päivä. **Talteen** vertaa sitä "
        "siihen, mikä olisi ollut mahdollista jälkiviisaasti. **Osuvuus** on osuus nimetyistä "
        "päivistä, jotka todella kuuluivat hiljaisimpiin, ja **satunnais** se, minkä arvaus "
        "antaisi.",
        "",
    ]
    for row in pooled:
        if str(row.get("verdict")) == "no_detectable_benefit":
            lines.append(
                f"- {row.get('venue_name')} / `{row.get('model')}`: pienin havaittava hyöty on "
                f"{percent(_scale(row.get('benefit_mde')), 0)}, joten "
                f"{integer(row.get('n_windows'))} ikkunaa erottaa vain tätä suuremman eron. "
                f"Tulos on \"ei todennettua hyötyä\", ei \"ei hyötyä\". Osuvuudesta verdikti on: "
                f"{CHANCE_PHRASES.get(str(row.get('hit_verdict')), '')}."
            )
    if lines[-1] != "":
        lines.append("")
    return lines


def _backtest_windows_section(metrics: dict[str, Any]) -> list[str]:
    """Every window, so a pooled number can be checked against its parts."""
    lines = [
        "## 4. Ikkunakohtaiset tulokset",
        "",
        "| Kohde | Sääntö | Jakso | Ehdokkaita | k | Hyöty | Paras mahdollinen | Osuvuus | "
        "Hiljaisin valinta |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in metrics.get("window_results", []):
        benefit = 1.0 - float(row["realized_ratio"]) if row.get("realized_ratio") is not None else None
        oracle = 1.0 - float(row["oracle_ratio"]) if row.get("oracle_ratio") is not None else None
        lines.append(
            f"| {row.get('venue_id')} | `{row.get('model')}` | {row.get('test_start')} – "
            f"{row.get('test_end')} | {integer(row.get('n_eligible'))} | {integer(row.get('k'))} | "
            f"{percent(_scale(benefit), 0)} | {percent(_scale(oracle), 0)} | "
            f"{percent(_scale(row.get('hit_rate')), 0)} | "
            f"{percent(_scale(row.get('top1_ratio')), 0)} |"
        )
    lines.append("")
    return lines


def _backtest_calibration_section(pooled: list[dict[str, Any]]) -> list[str]:
    """Do the published probabilities mean what they say."""
    lines = [
        "## 5. Todennäköisyyksien kalibrointi",
        "",
        "Jokainen ehdokaspäivä tuottaa yhden parin: mallin antama todennäköisyys ja se, "
        "kuuluiko päivä lopulta hiljaisimpiin. Hyvin kalibroidussa mallissa sarakkeet ovat "
        "lähellä toisiaan.",
        "",
        "| Kohde | Sääntö | Väli | n | Ennustettu | Toteutunut |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in pooled:
        for bucket in row.get("calibration", []):
            if not bucket.get("n"):
                continue
            lines.append(
                f"| {row.get('venue_name')} | `{row.get('model')}` | {bucket.get('bucket')} | "
                f"{integer(bucket.get('n'))} | {percent(_scale(bucket.get('predicted')), 0)} | "
                f"{percent(_scale(bucket.get('observed')), 0)} |"
            )
    lines.append("")
    return lines


def _backtest_limits_section(metrics: dict[str, Any]) -> list[str]:
    """What the sweep does not prove."""
    overlapping = bool(metrics.get("windows_overlap"))
    lines = [
        "## 6. Mitä tämä ei todista",
        "",
        "- **Ikkunoita on vähän.** Koko historia on yksi vuosi, ja kuukausi-ikkunoita mahtuu "
        "siihen kourallinen. Pienin havaittava hyöty on kussakin verdiktissä mukana juuri "
        "siksi.",
        "- **Yksi kohde ei kerro toisesta.** Verdikti annetaan kohteittain, koska "
        "aukioloajat, pyhäpäiväkäytäntö ja kävijäprofiili eroavat.",
        "- **Sääntövalinta on tehty samalla datalla.** Oletussääntö valittiin näiden samojen "
        "ikkunoiden perusteella, joten sen etu muihin sääntöihin nähden on yliarvio. "
        "Kohdekohtainen hyöty sen sijaan on mitattu opetusjakson ulkopuolelta.",
        "- **Mittaus käyttää kahta jälkiviisautta.** Ehdokasjoukko on ne päivät jotka "
        "toteutuivat havaittuina, täysinä ja nollaa suurempina, ja `k` otetaan toteuman "
        "ehdokasmäärästä. Molemmat pätevät samalla tavalla sääntöön ja satunnaisvalintaan, "
        "mutta sääntöä ei siis rangaista suljetun päivän ehdottamisesta.",
        "- **Menneisyys ei sisällä tapahtumakalenteria.** Jos kohteessa aletaan järjestää "
        "aktivointitapahtumia hiljaisina päivinä, ne muuttavat juuri niitä päiviä, joita malli "
        "ennustaa, ja mittaus on toistettava.",
    ]
    if overlapping:
        lines.append(
            "- **Ikkunat menevät päällekkäin.** Liukuvassa pyyhkäisyssä peräkkäiset ikkunat "
            "jakavat päiviä, joten ne eivät ole riippumattomia ja luottamusväli on todellista "
            "kapeampi. Kuukausipyyhkäisyssä päällekkäisyyttä ei ole."
        )
    lines.append("")
    return lines


__all__ = [
    "backtest_summary_fi",
    "fi_day",
    "fi_month",
    "forecast_summary_fi",
    "render_backtest_report",
    "render_forecast_report",
    "signed",
]
