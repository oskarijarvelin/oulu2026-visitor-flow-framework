"""The human-readable report, in Finnish, built from exactly what gets stored.

The renderer reads the same ``config``, ``metrics`` and ``verdicts`` payloads that are
written to disk, so the prose and the JSON can never drift apart. Nothing is recomputed
here.

Two things about the shape of the report are deliberate. The verdict is the first
paragraph and it is plain language: whoever runs the command should not have to open a
table to find out whether the model won. And the worst days come last but they are the
section people actually use — a date, an error and a probable cause is the most direct
statement of what the model does not know yet.
"""

from __future__ import annotations

from typing import Any

REPORT_TITLE = "Ennusteen arviointiraportti"
NA = "–"

VERDICT_PHRASES = {
    "better": "parempi kuin vertailukohta",
    "worse": "huonompi kuin vertailukohta",
    "no_difference": "ei havaittavaa eroa vertailukohtaan",
}
CALIBRATION_PHRASES = {
    "calibrated": "kalibroitu",
    "too_narrow": "liian kapea",
    "too_wide": "liian leveä",
}
BIAS_PHRASES = {
    "unbiased": "ei systemaattista harhaa",
    "over_forecast": "yliarvioi systemaattisesti",
    "under_forecast": "aliarvioi systemaattisesti",
}
WEATHER_LABELS = {
    "perfect": "perfect (toteutunut sää)",
    "operational": "operational (toteutunut vrk 1-16, klimatologia 17+)",
    "climatology": "climatology (klimatologia koko jaksolta)",
}


# --------------------------------------------------------------------------------------
# Number formatting, Finnish conventions
# --------------------------------------------------------------------------------------


def number(value: Any, digits: int = 1) -> str:
    """A number with a decimal comma, or a dash when it is missing."""
    if value is None:
        return NA
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return NA
    if numeric != numeric:
        return NA
    return f"{numeric:,.{digits}f}".replace(",", " ").replace(".", ",")


def signed(value: Any, digits: int = 1) -> str:
    """A number with an explicit sign, so a bias reads as a direction."""
    if value is None:
        return NA
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return NA
    if numeric != numeric:
        return NA
    return ("+" if numeric >= 0 else "") + number(numeric, digits)


def percent(value: Any, digits: int = 1) -> str:
    """A percentage."""
    formatted = number(value, digits)
    return NA if formatted == NA else f"{formatted} %"


def integer(value: Any) -> str:
    """A rounded count with a space as the thousands separator."""
    return number(value, 0)


def _flag(value: Any) -> bool:
    """Truthiness that survives a JSON round trip."""
    return bool(value) if value is not None else False


# --------------------------------------------------------------------------------------
# Window report
# --------------------------------------------------------------------------------------


def render_window_report(
    config: dict[str, Any], metrics: dict[str, Any], verdicts: dict[str, Any]
) -> str:
    """The full markdown report for one window."""
    window = verdicts.get("window", {})
    lines: list[str] = [
        f"# {REPORT_TITLE}: {window.get('test_start')} – {window.get('test_end')}",
        "",
        f"Ajon tunniste: `{verdicts.get('run_id', '')}`",
        "",
        "## 1. Verdikti",
        "",
        verdicts.get("summary_fi", ""),
        "",
    ]
    lines += _setup_section(config, metrics, verdicts)
    for venue_metrics, venue_verdict in _paired_venues(metrics, verdicts):
        lines += _venue_sections(venue_metrics, venue_verdict, verdicts)
    lines += _limitations_section(metrics, verdicts)
    return "\n".join(lines).rstrip() + "\n"


def _paired_venues(
    metrics: dict[str, Any], verdicts: dict[str, Any]
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Line up each venue's metrics with its verdict."""
    by_id = {entry.get("venue_id"): entry for entry in verdicts.get("venues", [])}
    return [
        (entry, by_id.get(entry.get("venue_id"), {})) for entry in metrics.get("venues", [])
    ]


def _setup_section(
    config: dict[str, Any], metrics: dict[str, Any], verdicts: dict[str, Any]
) -> list[str]:
    """Section 2: what was trained on, with what, and what was forecast."""
    window = verdicts.get("window", {})
    lines = [
        "## 2. Ikkuna ja asetelma",
        "",
        f"- Origo (viimeinen koulutuspäivä): **{window.get('origin')}**",
        f"- Testijakso: **{window.get('test_start')} – {window.get('test_end')}** "
        f"({window.get('horizon_days')} vrk, horisontit 1–{window.get('horizon_days')})",
        f"- Koulutusikkuna: `{window.get('train_window')}`",
        f"- Mallit: {', '.join(config.get('models', [])) or NA}",
        f"- Vertailukohdat: {', '.join(config.get('baselines', []))}",
        f"- Päävertailukohdan valinta: `{config.get('reference')}`",
        f"- Sään tilat: {', '.join(config.get('weather_modes', []))} "
        f"(verdikti tilasta `{config.get('primary_weather_mode')}`)",
        f"- Bootstrap: {integer(config.get('n_resamples'))} uudelleenotantaa, "
        f"lohkon pituus 7 vrk, siemen {config.get('seed')}",
        "",
        "| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for entry in metrics.get("venues", []):
        diagnostics = entry.get("diagnostics", {})
        lines.append(
            f"| {entry.get('venue_id')} ({entry.get('venue_name')}) "
            f"| {diagnostics.get('training_start')} "
            f"| {diagnostics.get('training_days')} "
            f"| {diagnostics.get('training_zero_days')} "
            f"| {diagnostics.get('nested_origins')} "
            f"| {number(diagnostics.get('mase_denominator'), 2)} |"
        )
    lines.append("")
    lines.append(
        "Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan "
        "koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten "
        "yksikään sisäennuste ei ylety testijaksoon."
    )
    lines.append("")
    return lines


def _venue_sections(
    venue_metrics: dict[str, Any], venue_verdict: dict[str, Any], verdicts: dict[str, Any]
) -> list[str]:
    """Sections 3 to 7 and 9 for one venue."""
    primary = verdicts.get("primary_weather_mode", "operational")
    title = f"Venue {venue_metrics.get('venue_id')} ({venue_metrics.get('venue_name')})"
    lines = [f"## {title}", ""]
    lines += _totals_section(venue_metrics, primary)
    lines += _daily_metrics_section(venue_metrics, primary)
    lines += _statistics_section(venue_verdict)
    lines += _calibration_section(venue_verdict)
    lines += _weather_section(venue_metrics)
    lines += _worst_days_section(venue_metrics)
    return lines


def _totals_section(venue_metrics: dict[str, Any], primary: str) -> list[str]:
    """Section 3: the number a producer actually asks for."""
    totals = [row for row in venue_metrics.get("totals", []) if row.get("weather_mode") == primary]
    if not totals:
        return []
    lines = [
        "### 3. Jakson kokonaismäärä",
        "",
        "| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in totals:
        lines.append(
            f"| {row.get('model')} | {integer(row.get('predicted'))} | {integer(row.get('actual'))} "
            f"| {signed(row.get('difference'), 0)} | {signed(row.get('difference_pct'), 1)} % "
            f"| {integer(row.get('p10'))} – {integer(row.get('p90'))} "
            f"| {'kyllä' if _flag(row.get('covers_actual')) else 'ei'} "
            f"| {integer(row.get('summed_daily_p10'))} – {integer(row.get('summed_daily_p90'))} |"
        )
    lines += [
        "",
        "Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason "
        "suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu "
        "polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin "
        "päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien "
        "virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.",
        "",
    ]
    drifted = [row for row in totals if _flag(row.get("is_drifted"))]
    if drifted:
        lines += [
            "⚠ **Näiden mallien väli ei ole kalibroitu:** "
            + ", ".join(
                f"{row.get('model')} (suhteellisten virheiden mediaani "
                f"{number(row.get('median_ratio'), 2)})"
                for row in drifted
            )
            + ". Sisäkkäisen backtestin mallit on koulutettu lyhyemmällä ja huonommalla "
            "aineistolla kuin ulompi malli, joten niiden virheissä on tasosiirtymä eikä pelkkää "
            "hajontaa. Väli perii sen. Lue kokonaismäärän ero ja bias erikseen, älä väliä.",
            "",
        ]
    thin = [row for row in totals if _flag(row.get("is_thin"))]
    if thin:
        lines += [
            "⚠ Ohut otos: "
            + ", ".join(f"{row.get('model')} ({row.get('n_ratio_samples')} havaintoa)" for row in thin)
            + ". Väli lepää harvan sisäkkäisen backtestin varassa.",
            "",
        ]
    return lines


def _daily_metrics_section(venue_metrics: dict[str, Any], primary: str) -> list[str]:
    """Section 4: models and baselines side by side, per horizon bucket."""
    scores = [row for row in venue_metrics.get("scores", []) if row.get("weather_mode") == primary]
    if not scores:
        return []
    lines = [
        "### 4. Päivätason mittarit",
        "",
        f"Sään tila `{primary}`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.",
        "",
        "| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 "
        "| Peittävyys 80 % | sMAPE | n |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in scores:
        pinball = row.get("pinball", {})
        smape = number(row.get("smape"), 1)
        if not _flag(row.get("smape_reliable")):
            smape = f"{smape} ⚠"
        lines.append(
            f"| {row.get('model')} | {row.get('bucket')} | {number(row.get('mae'))} "
            f"| {number(row.get('rmse'))} | {number(row.get('mase'), 3)} "
            f"| {signed(row.get('bias'))} | {number(pinball.get('q10'))} "
            f"| {number(pinball.get('q50'))} | {number(pinball.get('q90'))} "
            f"| {number(row.get('coverage_80'), 2)} | {smape} | {row.get('n')} |"
        )
    unreliable = sorted(
        {int(row.get("zero_days", 0)) for row in scores if not _flag(row.get("smape_reliable"))}
    )
    lines.append("")
    if unreliable:
        lines.append(
            "⚠ sMAPE on merkitty epäluotettavaksi: testijaksolla on nollapäiviä "
            f"(enimmillään {max(unreliable)} korissa). Nollapäivällä symmetrinen suhde saavuttaa "
            "kattonsa riippumatta siitä kuinka lähellä ennuste oli. sMAPEa ei käytetä verdiktin "
            "perustana."
        )
    else:
        lines.append("Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.")
    lines.append("")
    return lines


def _statistics_section(venue_verdict: dict[str, Any]) -> list[str]:
    """Section 5: interval, skill score, power, and the secondary DM p-value."""
    models = venue_verdict.get("models", [])
    if not models:
        return []
    reference = venue_verdict.get("reference", NA)
    baseline_mae = venue_verdict.get("baseline_mae", {})
    lines = [
        "### 5. Tilastollinen arvio",
        "",
        f"Päävertailukohta tällä ikkunalla: **{reference}** "
        f"(MAE {number(baseline_mae.get(reference))}). Vertailukohtien MAE: "
        + ", ".join(f"{name} {number(value)}" for name, value in baseline_mae.items())
        + ".",
        "",
        "| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli "
        "| MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in models:
        comparison = entry.get("comparison", {})
        lines.append(
            f"| {entry.get('model')} | {signed(comparison.get('mean_difference'))} "
            f"| {signed(comparison.get('ci_low'))} … {signed(comparison.get('ci_high'))} "
            f"| {VERDICT_PHRASES.get(str(comparison.get('verdict')), NA)} "
            f"| {number(comparison.get('skill_score'), 3)} "
            f"| {number(comparison.get('skill_ci_low'), 3)} … {number(comparison.get('skill_ci_high'), 3)} "
            f"| {number(comparison.get('mde'))} | {percent(comparison.get('mde_pct'))} "
            f"| {number(comparison.get('dm_statistic'), 2)} "
            f"| {number(entry.get('raw_p_value'), 3)} | {number(entry.get('holm_p_value'), 3)} |"
        )
    lines += [
        "",
        "`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen "
        "tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista "
        "(lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.",
        "",
        "**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä "
        "otos olisi sen erottanut. Kun verdikti on \"ei havaittavaa eroa\", MDE erottaa kaksi eri "
        "asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on "
        "tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy "
        "todistamaan vain suuret parannukset.",
        "",
        "**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia "
        "havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset "
        "ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. "
        f"Holm-korjattu p-arvo on laskettu perheelle, jonka koko on "
        f"{venue_verdict.get('family_size', NA)}.",
        "",
    ]
    return lines


def _calibration_section(venue_verdict: dict[str, Any]) -> list[str]:
    """Section 6: coverage and bias, each with an interval."""
    models = venue_verdict.get("models", [])
    if not models:
        return []
    lines = [
        "### 6. Kalibrointi ja bias",
        "",
        "| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli "
        "| Bias % toteumasta | Biasin verdikti |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in models:
        calibration = entry.get("calibration", {})
        bias = entry.get("bias", {})
        lines.append(
            f"| {entry.get('model')} | {number(calibration.get('coverage'), 2)} "
            f"({calibration.get('covered')}/{calibration.get('n')}) "
            f"| {number(calibration.get('ci_low'), 2)} … {number(calibration.get('ci_high'), 2)} "
            f"| {CALIBRATION_PHRASES.get(str(calibration.get('verdict')), NA)} "
            f"| {signed(bias.get('mean_error'))} "
            f"| {signed(bias.get('ci_low'))} … {signed(bias.get('ci_high'))} "
            f"| {signed(bias.get('pct_of_actual'))} % "
            f"| {BIAS_PHRASES.get(str(bias.get('verdict')), NA)} |"
        )
    lines += [
        "",
        "Kalibrointi on \"kalibroitu\", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. "
        "Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, "
        "malli yli- tai aliarvioi systemaattisesti.",
        "",
    ]
    return lines


def _weather_section(venue_metrics: dict[str, Any]) -> list[str]:
    """Section 7: what the model's accuracy owes to knowing the weather."""
    sensitivity = venue_metrics.get("weather_sensitivity", {})
    if not sensitivity:
        return []
    lines = [
        "### 7. Sään kolmen tilan vertailu",
        "",
        "| Malli | perfect MAE | operational MAE | climatology MAE "
        "| Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for model, entry in sensitivity.items():
        lines.append(
            f"| {model} | {number(entry.get('perfect'))} | {number(entry.get('operational'))} "
            f"| {number(entry.get('climatology'))} | {signed(entry.get('gap'))} "
            f"| {percent(entry.get('gap_pct'))} |"
        )
    lines += [
        "",
        "`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. "
        "`climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin "
        "arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus "
        "`perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se "
        "osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.",
        "",
    ]
    negative = [
        entry for entry in sensitivity.values()
        if isinstance(entry.get("gap"), float) and entry["gap"] == entry["gap"] and entry["gap"] < 0.0
    ]
    if negative:
        lines += [
            "⚠ **Parannus on negatiivinen**, eli malli ennustaa tällä ikkunalla *paremmin* "
            "keskiarvosäällä kuin toteutuneella säällä. Se ei ole mittausvirhe vaan tulos: mallin "
            "oppima sääriippuvuus ei yleisty tähän jaksoon, vaan toteutunut sää vie ennustetta "
            "väärään suuntaan. Sääpiirteet sopivat siis koulutusjakson kohinaan enemmän kuin "
            "kävijöiden todelliseen sääkäyttäytymiseen.",
            "",
        ]
    lines += [
        "| Sään tila | Toteutunutta säätä | Klimatologiaa |",
        "| --- | --- | --- |",
    ]
    for mode, counts in venue_metrics.get("diagnostics", {}).get("weather_days", {}).items():
        lines.append(
            f"| {WEATHER_LABELS.get(mode, mode)} | {counts.get('observed')} "
            f"| {counts.get('climatology')} |"
        )
    lines.append("")
    return lines


def _worst_days_section(venue_metrics: dict[str, Any]) -> list[str]:
    """Section 9: the five biggest misses, with a probable cause for each."""
    worst = venue_metrics.get("worst_days", {})
    if not worst:
        return []
    lines = ["### 9. Pahiten menneet päivät", ""]
    for model, rows in worst.items():
        lines += [
            f"**{model}**",
            "",
            "| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in rows:
            lines.append(
                f"| {row.get('date')} | {row.get('weekday')} | {integer(row.get('y_true'))} "
                f"| {integer(row.get('p50'))} | {signed(row.get('error'), 0)} | {row.get('note')} |"
            )
        lines.append("")
    lines += [
        "Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa "
        "sarakkeessa on suora ehdotus seuraavaksi piirteeksi.",
        "",
    ]
    return lines


def _limitations_section(metrics: dict[str, Any], verdicts: dict[str, Any]) -> list[str]:
    """Section 8: sample size and what may not be concluded from this run."""
    window = verdicts.get("window", {})
    horizon = window.get("horizon_days", 0)
    lines = [
        "## 8. Rajoitteet",
        "",
        f"- **Otoskoko.** Yksi ikkuna on {horizon} päivää yhdestä origosta. Ne eivät ole "
        f"{horizon} riippumatonta havaintoa: kaikki jakavat saman koulutusjoukon ja saman "
        "kuukauden sään.",
        "- **Yhden ikkunan verdikti on kuvaileva, ei todistava.** Varsinainen näyttö syntyy usean "
        "ikkunan koosteesta (`--sweep monthly` tai `--sweep rolling`).",
        "- **\"Ei havaittavaa eroa\" ei tarkoita samanveroisuutta.** Lue MDE kohdasta 5 ennen kuin "
        "teet siitä johtopäätöksen.",
        "- **sMAPEa ei käytetä verdiktin perustana**, koska nollapäivät rikkovat sen.",
        "- **Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta.** Vuosikausivaihtelua ei voi "
        "oppia, joten vertailu toiseen vuoteen ei ole mahdollinen.",
        "- **Lippudataa ei käytetä piirteenä**, koska sitä ei ole tulevaisuudelle.",
    ]
    for entry in metrics.get("venues", []):
        diagnostics = entry.get("diagnostics", {})
        leading = int(diagnostics.get("leading_zero_days") or 0)
        if leading:
            lines.append(
                f"- **Venue {entry.get('venue_id')}: koulutusikkunan alussa on {leading} nollapäivää** "
                "sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska "
                "koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. "
                "Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän "
                "suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat "
                "kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa "
                "lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa."
            )
        if diagnostics.get("missing_test_days"):
            lines.append(
                f"- **Venue {entry.get('venue_id')}: testijaksolta puuttuu "
                f"{len(diagnostics['missing_test_days'])} päivää**, joilta ei ole havaintoa."
            )
        if diagnostics.get("default_bands"):
            lines.append(
                f"- **Venue {entry.get('venue_id')}: osa ennustevälejä on oletusarvoja** "
                f"({', '.join(diagnostics['default_bands'])}), koska sisäkkäinen backtest ei "
                "tuottanut tarpeeksi havaintoja kyseiseen horisonttikoriin. Peittävyyslukua ei "
                "pidä lukea niistä."
            )
    lines.append("")
    return lines


# --------------------------------------------------------------------------------------
# Sweep report
# --------------------------------------------------------------------------------------


def render_sweep_report(
    config: dict[str, Any], metrics: dict[str, Any], verdicts: dict[str, Any]
) -> str:
    """The full markdown report for a sweep: pooled verdict first, windows below it."""
    lines: list[str] = [
        f"# {REPORT_TITLE}, kooste: {verdicts.get('sweep')} "
        f"{verdicts.get('first_day')} – {verdicts.get('last_day')}",
        "",
        f"Ajon tunniste: `{verdicts.get('run_id', '')}`",
        "",
        "## 1. Koosteverdikti",
        "",
        verdicts.get("summary_fi", ""),
        "",
        "## 2. Ikkunat",
        "",
        "| # | Testijakso | Origo | Koulutusikkuna | Ajon tunniste |",
        "| --- | --- | --- | --- | --- |",
    ]
    for position, window in enumerate(verdicts.get("windows", []), start=1):
        lines.append(
            f"| {position} | {window.get('test_start')} – {window.get('test_end')} "
            f"| {window.get('origin')} | {window.get('train_window')} | `{window.get('run_id')}` |"
        )
    lines += [
        "",
        f"Sään tila verdiktille: `{verdicts.get('primary_weather_mode')}`. "
        f"Päävertailukohdan valinta: `{verdicts.get('reference_rule')}`. "
        f"Monivertailuperheen koko: {verdicts.get('family_size')}.",
        "",
    ]
    for venue in verdicts.get("venues", []):
        lines += _sweep_venue_section(venue)
    lines += [
        "## Rajoitteet",
        "",
        "- Kooste bootstrapataan **kokonaisina ikkunoina**, koska ikkuna on riippumattomuuden "
        "luonnollinen yksikkö: kaksi saman ikkunan päivää jakavat koulutusjoukon, kaksi eri "
        "ikkunaa eivät.",
        "- Ikkunakohtainen verdikti on kuvaileva. Koosteverdikti on se, joka kantaa näyttöä.",
        "- Raakoja p-arvoja on korjattu Holm-Bonferronilla; perheen koko on kerrottu yllä.",
        "- Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen "
        "otoksen varassa.",
        "",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _sweep_venue_section(venue: dict[str, Any]) -> list[str]:
    """One venue's pooled verdict and its per-window detail."""
    lines = [
        f"## Venue {venue.get('venue_id')} ({venue.get('venue_name')})",
        "",
        "### Koosteverdikti",
        "",
        "| Malli | Vertailukohta | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti "
        "| Puolesta | Vastaan | MDE | MDE / vertailun MAE |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for entry in venue.get("models", []):
        pooled = entry.get("pooled", {})
        lines.append(
            f"| {pooled.get('model')} | {pooled.get('reference')} | {pooled.get('n_windows')} "
            f"| {pooled.get('n_days')} | {signed(pooled.get('mean_difference'))} "
            f"| {signed(pooled.get('ci_low'))} … {signed(pooled.get('ci_high'))} "
            f"| {VERDICT_PHRASES.get(str(pooled.get('verdict')), NA)} "
            f"| {pooled.get('windows_favouring')} | {pooled.get('windows_opposing')} "
            f"| {number(pooled.get('mde'))} | {percent(pooled.get('mde_pct'))} |"
        )
    lines.append("")
    for entry in venue.get("models", []):
        lines += [
            f"### Ikkunakohtaiset tulokset: {entry.get('model')}",
            "",
            "| Testijakso | Vertailukohta | Mallin MAE | Vertailun MAE | Keskiero d | 95 % väli "
            "| Verdikti | MDE | MDE % | DM p (raaka) | DM p (Holm) |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
        ]
        for row in entry.get("per_window", []):
            lines.append(
                f"| {row.get('label')} | {row.get('reference')} | {number(row.get('model_mae'))} "
                f"| {number(row.get('reference_mae'))} | {signed(row.get('mean_difference'))} "
                f"| {signed(row.get('ci_low'))} … {signed(row.get('ci_high'))} "
                f"| {VERDICT_PHRASES.get(str(row.get('verdict')), NA)} "
                f"| {number(row.get('mde'))} | {percent(row.get('mde_pct'))} "
                f"| {number(row.get('raw_p_value'), 3)} | {number(row.get('holm_p_value'), 3)} |"
            )
        lines.append("")
        totals = entry.get("totals", [])
        if totals:
            lines += [
                f"#### Jakson kokonaismäärät: {entry.get('model')}",
                "",
                "| Testijakso | Ennuste | Toteuma | Ero % | 80 % väli | Väli osuu |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
            for row in totals:
                lines.append(
                    f"| {row.get('label')} | {integer(row.get('predicted'))} "
                    f"| {integer(row.get('actual'))} | {signed(row.get('difference_pct'))} % "
                    f"| {integer(row.get('p10'))} – {integer(row.get('p90'))} "
                    f"| {'kyllä' if _flag(row.get('covers_actual')) else 'ei'} |"
                )
            lines.append("")
    return lines
