"""Every sentence the quiet-day package writes, in both languages.

Same split as :mod:`ovf_forecast.evaluation.strings` and for the same reason: the renderer
owns the layout and the numbers, this module owns the words, and a second language costs a
table row rather than a second renderer that will drift.

The verdict wording is worth reading closely. ``no_detectable_benefit`` says the benefit has
not been verified, not that there is none — five windows cannot tell those apart, and the
translation has to keep that distinction rather than collapsing it into "no benefit".
"""

from __future__ import annotations

from ..i18n import DEFAULT_LANG, Lang

VERDICT_PHRASES: dict[Lang, dict[str, str]] = {
    "fi": {
        "useful": "hyöty on todennettu",
        "no_detectable_benefit": "hyötyä ei ole todennettu",
        "harmful": "valinta osuu keskimääräistä vilkkaampiin päiviin",
    },
    "en": {
        "useful": "the benefit is verified",
        "no_detectable_benefit": "the benefit is not verified",
        "harmful": "the choice lands on busier days than average",
    },
}

CHANCE_PHRASES: dict[Lang, dict[str, str]] = {
    "fi": {
        "better_than_chance": "osuvuus ylittää satunnaisvalinnan",
        "like_chance": "osuvuus ei eroa satunnaisvalinnasta",
        "worse_than_chance": "osuvuus jää satunnaisvalinnan alle",
    },
    "en": {
        "better_than_chance": "the hit rate beats a random choice",
        "like_chance": "the hit rate does not differ from a random choice",
        "worse_than_chance": "the hit rate falls below a random choice",
    },
}

STATUS_PHRASES: dict[Lang, dict[str, str]] = {
    "fi": {
        "open": "ehdokas",
        "closed_weekday": "suljettu arkipäivä",
        "closed_holiday": "suljettu pyhäpäivä",
        "no_visitors": "ei kävijöitä",
        "incomplete_day": "vajaa mittauspäivä",
        "unobserved": "ei havaintoa",
    },
    "en": {
        "open": "candidate",
        "closed_weekday": "closed weekday",
        "closed_holiday": "closed public holiday",
        "no_visitors": "no visitors",
        "incomplete_day": "incomplete measurement day",
        "unobserved": "no observation",
    },
}

WEEKDAY_NAMES: dict[Lang, tuple[str, ...]] = {
    "fi": (
        "maanantai",
        "tiistai",
        "keskiviikko",
        "torstai",
        "perjantai",
        "lauantai",
        "sunnuntai",
    ),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}

FI: dict[str, str] = {
    # -- shared ----------------------------------------------------------------------
    "forecast_title": "Kuukauden hiljaisimmat päivät",
    "backtest_title": "Hiljaisten päivien ennustemallin luotettavuus",
    "run_id": "Ajon tunniste: `{run_id}`",
    "none": "ei yhtään",
    # -- forecast: the answer ----------------------------------------------------------
    "forecast_heading": "# {title}: {month}",
    "h_answer": "## 1. Vastaus",
    "sum_days": "{venue_name} ({venue_id}), {month}: hiljaisimmat päivät ovat {days}.",
    "sum_no_candidates": "ei yhtään ehdokasta",
    "sum_threshold": "Kynnys on kuukauden hiljaisin viidennes, {k} päivää {n} ehdokkaasta, ja "
    "malli erottaa ne {gap} mediaanipäivän alapuolelle.",
    "sum_best": "Varmin valinta on {day}, jonka todennäköisyys kuulua hiljaisimpiin on "
    "{probability}.",
    "sum_not_material": "Malli ei kuitenkaan erottele kuukauden päiviä merkittävästi: hiljaisin "
    "viidennes jää alle 15 % mediaanipäivän alapuolelle, joten järjestys kannattaa lukea suuntaa "
    "antavana.",
    "reliability_missing": "Mallin luotettavuutta ei ole mitattu tässä repositoriossa: aja "
    "'python -m ovf_forecast quiet backtest' ennen kuin suositukseen nojataan.",
    "reliability_value": "{benefit} (95 % väli {low} … {high})",
    "reliability_measured": "Mitattu luotettavuus ({windows} ikkunaa, ajo `{run_id}`): valitut "
    "päivät olivat keskimäärin {measured} mediaanipäivää hiljaisempia, eli {verdict}.",
    # -- forecast: method --------------------------------------------------------------
    "h_method": "## 2. Miten luku on muodostettu",
    "method_model": "- Pisteytyssääntö: `{model}`",
    "method_threshold": "- Kynnys: kuukauden hiljaisin {share} ehdokaspäivistä, vähintään 3 ja "
    "enintään 10 päivää",
    "method_simulations": "- Simulaatioita todennäköisyyttä kohden: {simulations}",
    "method_seed": "- Siemenluku: {seed}",
    "method_note_score": "Pisteluku on kävijämäärän suuruusluokassa, mutta se on järjestysluku "
    "eikä ennuste: kaikki alla olevat suhdeluvut on jaettu kuukauden mediaanipäivällä, jolloin "
    "tason virhe kumoutuu eikä vaikuta järjestykseen.",
    "method_note_separation": "Mallin erottelu ja toteutuva ero ovat kaksi eri lukua, eikä toinen "
    "ennusta toista. Pisteluku on ehdollinen keskiarvo, joten se on aina toteumaa tasaisempi: "
    "alla oleva suhdeluku kertoo, kuinka kauas malli päivät erottaa, ei kuinka hiljaisia ne "
    "toteutuvat olemaan. Toteutuvan eron arvio saadaan vain mittaamalla, ja se on komennon "
    "`quiet backtest` tulos.",
    # -- forecast: venue ---------------------------------------------------------------
    "h_venue": "## 3. {venue_name} ({venue_id})",
    "venue_intro": "Origo {origin}, sääntö `{model}`. Ehdokaspäiviä {n}, hiljaisia päiviä {k}. "
    "Kynnysarvo on {cut} kävijätapahtumaa, eli {cut_ratio} % mediaanipäivästä.",
    "h_quiet_days": "### Hiljaisimmat päivät",
    "quiet_table": "Päivä | Sija | Suhde mediaaniin | Todennäköisyys | Samanarvoisia | Pyhä "
    "| Lämpötila | Sade",
    "h_month": "### Koko kuukausi",
    "month_table": "Päivä | Tila | Sija | Suhde mediaaniin | Todennäköisyys",
    "h_inputs": "### Lähtötiedot",
    "input_closed": "- Suljetut arkipäivät: {days}",
    "input_holiday": "- Pyhäpäiväkerroin: {factor} ({n} havaintoa)",
    "input_residuals": "- Jäännösjakauma: {kind}, {n} havaintoa",
    "residuals_measured": "mitattu",
    "residuals_default": "oletushajonta",
    "h_warnings": "### Varaukset",
    # -- forecast: limits --------------------------------------------------------------
    "h_forecast_limits": "## 4. Mitä tämä ei kerro",
    "forecast_limit_score": "- **Pisteluku ei ole kävijäennuste.** Se on järjestysluku. Tason "
    "ennustamiseen on `python -m ovf_forecast run`, ja sen tarkkuus mitataan erikseen komennolla "
    "`evaluate`.",
    "forecast_limit_probability": "- **Todennäköisyys koskee järjestystä, ei kävijämäärää.** "
    "\"70 %\" tarkoittaa, että päivä päätyi hiljaisimpien joukkoon 70 %:ssa simuloiduista "
    "kuukausista.",
    "forecast_limit_events": "- **Malli ei tunne tapahtumakalenteria.** Yksittäinen konsertti tai "
    "ryhmävaraus kääntää hiljaisen päivän vilkkaaksi, eikä tässä käytetyssä datassa ole tietoa "
    "siitä.",
    "forecast_limit_weather": "- **Sää on taustatietoa.** Se on taulukossa ihmisen päätöksen "
    "tueksi, mutta se ei vaikuta järjestykseen: mitattuna se ei parantanut sitä.",
    "forecast_limit_closed": "- **Suljetut päivät eivät ole hiljaisia päiviä.** Ne on rajattu "
    "ehdokkaista pois, koska tapahtumaa ei voi järjestää suljetussa kohteessa.",
    # -- backtest ----------------------------------------------------------------------
    "backtest_heading": "# {title}",
    "h_verdict": "## 1. Verdikti",
    "backtest_no_windows": "Yhtään ikkunaa ei voitu pisteyttää.",
    "backtest_sum_row": "- {venue_name} ({venue_id}) / `{model}`: valitut päivät olivat {benefit} "
    "mediaanipäivää hiljaisempia (95 % väli {low} … {high}, {windows} ikkunaa), {verdict}; "
    "osuvuus {hit_rate} kun satunnaisvalinta antaisi {chance_rate}.",
    "h_backtest_method": "## 2. Menetelmä",
    "backtest_windows": "- Ikkunoita: {windows} ({first} – {last})",
    "backtest_kind": "- Ikkunatyyppi: {kind}",
    "backtest_models": "- Säännöt: {models}",
    "backtest_threshold": "- Kynnys: hiljaisin {share} ehdokaspäivistä",
    "backtest_bootstrap": "- Bootstrap-toistoja: {resamples}, siemenluku {seed}",
    "backtest_method_note": "Jokainen ikkuna opetetaan origoonsa asti, nimetään sen jälkeen jakson "
    "hiljaisimmat päivät ja avataan vasta sitten toteuma. Luottamusväli arvotaan kokonaisista "
    "ikkunoista, ei päivistä: saman kuukauden päivät jakavat origon, opetusjakson ja sään, eivätkä "
    "ole toisistaan riippumattomia havaintoja.",
    "h_results": "## 3. Tulokset",
    "results_table": "Kohde | Sääntö | Ikkunoita | Hyöty | 95 % väli | Osuvuus | Satunnais "
    "| Talteen | Spearman | Verdikti",
    "results_note": "**Hyöty** on 1 − (valittujen päivien keskiarvo ÷ kuukauden mediaanipäivä): "
    "kuinka paljon hiljaisempi suositus oli kuin mielivaltainen päivä. **Talteen** vertaa sitä "
    "siihen, mikä olisi ollut mahdollista jälkiviisaasti. **Osuvuus** on osuus nimetyistä "
    "päivistä, jotka todella kuuluivat hiljaisimpiin, ja **satunnais** se, minkä arvaus antaisi.",
    "results_mde": "- {venue_name} / `{model}`: pienin havaittava hyöty on {mde}, joten {windows} "
    "ikkunaa erottaa vain tätä suuremman eron. Tulos on \"ei todennettua hyötyä\", ei \"ei "
    "hyötyä\". Osuvuudesta verdikti on: {chance_verdict}.",
    "h_backtest_windows": "## 4. Ikkunakohtaiset tulokset",
    "windows_table": "Kohde | Sääntö | Jakso | Ehdokkaita | k | Hyöty | Paras mahdollinen "
    "| Osuvuus | Hiljaisin valinta",
    "h_calibration": "## 5. Todennäköisyyksien kalibrointi",
    "calibration_note": "Jokainen ehdokaspäivä tuottaa yhden parin: mallin antama todennäköisyys "
    "ja se, kuuluiko päivä lopulta hiljaisimpiin. Hyvin kalibroidussa mallissa sarakkeet ovat "
    "lähellä toisiaan.",
    "calibration_table": "Kohde | Sääntö | Väli | n | Ennustettu | Toteutunut",
    "h_backtest_limits": "## 6. Mitä tämä ei todista",
    "backtest_limit_windows": "- **Ikkunoita on vähän.** Koko historia on yksi vuosi, ja "
    "kuukausi-ikkunoita mahtuu siihen kourallinen. Pienin havaittava hyöty on kussakin verdiktissä "
    "mukana juuri siksi.",
    "backtest_limit_venues": "- **Yksi kohde ei kerro toisesta.** Verdikti annetaan kohteittain, "
    "koska aukioloajat, pyhäpäiväkäytäntö ja kävijäprofiili eroavat.",
    "backtest_limit_selection": "- **Sääntövalinta on tehty samalla datalla.** Oletussääntö "
    "valittiin näiden samojen ikkunoiden perusteella, joten sen etu muihin sääntöihin nähden on "
    "yliarvio. Kohdekohtainen hyöty sen sijaan on mitattu opetusjakson ulkopuolelta.",
    "backtest_limit_hindsight": "- **Mittaus käyttää kahta jälkiviisautta.** Ehdokasjoukko on ne "
    "päivät jotka toteutuivat havaittuina, täysinä ja nollaa suurempina, ja `k` otetaan toteuman "
    "ehdokasmäärästä. Molemmat pätevät samalla tavalla sääntöön ja satunnaisvalintaan, mutta "
    "sääntöä ei siis rangaista suljetun päivän ehdottamisesta.",
    "backtest_limit_events": "- **Menneisyys ei sisällä tapahtumakalenteria.** Jos kohteessa "
    "aletaan järjestää aktivointitapahtumia hiljaisina päivinä, ne muuttavat juuri niitä päiviä, "
    "joita malli ennustaa, ja mittaus on toistettava.",
    "backtest_limit_overlap": "- **Ikkunat menevät päällekkäin.** Liukuvassa pyyhkäisyssä "
    "peräkkäiset ikkunat jakavat päiviä, joten ne eivät ole riippumattomia ja luottamusväli on "
    "todellista kapeampi. Kuukausipyyhkäisyssä päällekkäisyyttä ei ole.",
    # -- warnings ----------------------------------------------------------------------
    "warn_tie": "Kynnys osuu tasapisteryhmän sisään: {size} päivää saa saman pistearvon ja niistä "
    "{chosen} mahtui hiljaisimpiin. Malli ei erottele näitä päiviä toisistaan, joten valinta "
    "niiden kesken on päivämääräjärjestyksessä ja voidaan tehdä muilla perusteilla.",
    "warn_not_material": "Kuukauden hiljaisin viidennes on vain {gap} mediaanipäivää hiljaisempi, "
    "joten kuukausi on tasainen eikä suositus erottele päiviä merkittävästi.",
    "warn_default_residuals": "Todennäköisyydet on laskettu oletushajonnalla, koska opetusjaksolle "
    "ei mahtunut yhtään sisäistä origoa. Ne kertovat mallin järjestyksestä, eivät mitatusta "
    "epävarmuudesta.",
    "warn_stale_origin": "Viimeinen havainto on {origin}, {days} päivää ennen kuukauden alkua. "
    "Arkipäivämediaanit kuvaavat eri jaksoa kuin ennustettava kuukausi.",
    "warn_calendar_gap": "Ylläpidetty kalenteri ei kata päivää {first} eteenpäin ({days} päivää), "
    "joten niiltä oletetaan ettei pyhäpäiviä ole.",
    "warn_climatology": "Säätiedot ovat klimatologiaa {days} päivälle; ne ovat taustatietoa "
    "eivätkä vaikuta pisteytykseen.",
    "warn_closed_weekdays": "Suljetut arkipäivät jätetty ehdokkaista pois: {days}.",
}

EN: dict[str, str] = {
    # -- shared ----------------------------------------------------------------------
    "forecast_title": "The quietest days of the month",
    "backtest_title": "The reliability of the quiet-day model",
    "run_id": "Run id: `{run_id}`",
    "none": "none",
    # -- forecast: the answer ----------------------------------------------------------
    "forecast_heading": "# {title}: {month}",
    "h_answer": "## 1. The answer",
    "sum_days": "{venue_name} ({venue_id}), {month}: the quietest days are {days}.",
    "sum_no_candidates": "no candidates at all",
    "sum_threshold": "The threshold is the quietest fifth of the month, {k} days out of {n} "
    "candidates, and the model separates them to {gap} below the median day.",
    "sum_best": "The most certain choice is {day}, whose probability of belonging to the quietest "
    "days is {probability}.",
    "sum_not_material": "The model does not, however, separate the month's days materially: the "
    "quietest fifth stays less than 15 % below the median day, so the ranking is best read as "
    "indicative.",
    "reliability_missing": "The model's reliability has not been measured in this repository: run "
    "'python -m ovf_forecast quiet backtest' before leaning on the recommendation.",
    "reliability_value": "{benefit} (95 % interval {low} … {high})",
    "reliability_measured": "Measured reliability ({windows} windows, run `{run_id}`): the chosen "
    "days were on average {measured} quieter than the median day, i.e. {verdict}.",
    # -- forecast: method --------------------------------------------------------------
    "h_method": "## 2. How the figure was produced",
    "method_model": "- Scoring rule: `{model}`",
    "method_threshold": "- Threshold: the quietest {share} of the candidate days, at least 3 and "
    "at most 10 days",
    "method_simulations": "- Simulations per probability: {simulations}",
    "method_seed": "- Seed: {seed}",
    "method_note_score": "The score is on the same order of magnitude as a visitor count, but it "
    "is a ranking number and not a forecast: every ratio below is divided by the month's median "
    "day, so an error in the level cancels out and does not affect the ranking.",
    "method_note_separation": "The model's separation and the realised difference are two "
    "different numbers, and neither predicts the other. The score is a conditional mean, so it is "
    "always flatter than the actual values: the ratio below says how far apart the model pulls the "
    "days, not how quiet they turn out to be. An estimate of the realised difference comes only "
    "from measuring, and that is the result of `quiet backtest`.",
    # -- forecast: venue ---------------------------------------------------------------
    "h_venue": "## 3. {venue_name} ({venue_id})",
    "venue_intro": "Origin {origin}, rule `{model}`. Candidate days {n}, quiet days {k}. The "
    "threshold value is {cut} visitor events, i.e. {cut_ratio} % of the median day.",
    "h_quiet_days": "### The quietest days",
    "quiet_table": "Day | Rank | Ratio to the median | Probability | Ties | Holiday | Temperature "
    "| Rain",
    "h_month": "### The whole month",
    "month_table": "Day | Status | Rank | Ratio to the median | Probability",
    "h_inputs": "### Inputs",
    "input_closed": "- Closed weekdays: {days}",
    "input_holiday": "- Public holiday factor: {factor} ({n} observations)",
    "input_residuals": "- Residual distribution: {kind}, {n} observations",
    "residuals_measured": "measured",
    "residuals_default": "default spread",
    "h_warnings": "### Caveats",
    # -- forecast: limits --------------------------------------------------------------
    "h_forecast_limits": "## 4. What this does not say",
    "forecast_limit_score": "- **The score is not a visitor forecast.** It is a ranking number. "
    "For forecasting the level there is `python -m ovf_forecast run`, and its accuracy is measured "
    "separately with `evaluate`.",
    "forecast_limit_probability": "- **The probability concerns the ranking, not the visitor "
    "count.** \"70 %\" means the day ended up among the quietest in 70 % of the simulated months.",
    "forecast_limit_events": "- **The model does not know the events calendar.** A single concert "
    "or group booking turns a quiet day busy, and the data used here holds nothing about that.",
    "forecast_limit_weather": "- **The weather is background.** It is in the table to support a "
    "human decision, but it does not affect the ranking: measured, it did not improve it.",
    "forecast_limit_closed": "- **Closed days are not quiet days.** They are excluded from the "
    "candidates, because an event cannot be held in a closed venue.",
    # -- backtest ----------------------------------------------------------------------
    "backtest_heading": "# {title}",
    "h_verdict": "## 1. Verdict",
    "backtest_no_windows": "No window could be scored.",
    "backtest_sum_row": "- {venue_name} ({venue_id}) / `{model}`: the chosen days were {benefit} "
    "quieter than the median day (95 % interval {low} … {high}, {windows} windows), {verdict}; the "
    "hit rate is {hit_rate} where a random choice would give {chance_rate}.",
    "h_backtest_method": "## 2. Method",
    "backtest_windows": "- Windows: {windows} ({first} – {last})",
    "backtest_kind": "- Window type: {kind}",
    "backtest_models": "- Rules: {models}",
    "backtest_threshold": "- Threshold: the quietest {share} of the candidate days",
    "backtest_bootstrap": "- Bootstrap resamples: {resamples}, seed {seed}",
    "backtest_method_note": "Every window is trained up to its own origin, then names the quietest "
    "days of the period, and only then are the actual values opened. The confidence interval is "
    "drawn over whole windows rather than days: days from the same month share the origin, the "
    "training period and the weather, and are not independent observations.",
    "h_results": "## 3. Results",
    "results_table": "Venue | Rule | Windows | Benefit | 95 % interval | Hit rate | Chance "
    "| Capture | Spearman | Verdict",
    "results_note": "**Benefit** is 1 − (the mean of the chosen days ÷ the month's median day): "
    "how much quieter the recommendation was than an arbitrary day. **Capture** compares that "
    "against what would have been possible with hindsight. **Hit rate** is the share of the named "
    "days that genuinely belonged to the quietest, and **chance** is what a guess would give.",
    "results_mde": "- {venue_name} / `{model}`: the minimum detectable benefit is {mde}, so "
    "{windows} windows only resolve a difference larger than that. The result is \"no verified "
    "benefit\", not \"no benefit\". On the hit rate the verdict is: {chance_verdict}.",
    "h_backtest_windows": "## 4. Per-window results",
    "windows_table": "Venue | Rule | Period | Candidates | k | Benefit | Best possible | Hit rate "
    "| Quietest choice",
    "h_calibration": "## 5. Calibration of the probabilities",
    "calibration_note": "Every candidate day produces one pair: the probability the model gave and "
    "whether the day ended up among the quietest. In a well-calibrated model the columns are close "
    "to each other.",
    "calibration_table": "Venue | Rule | Bucket | n | Predicted | Observed",
    "h_backtest_limits": "## 6. What this does not prove",
    "backtest_limit_windows": "- **There are few windows.** The whole history is one year, and it "
    "holds a handful of monthly windows. The minimum detectable benefit is included in every "
    "verdict for precisely that reason.",
    "backtest_limit_venues": "- **One venue says nothing about another.** The verdict is given per "
    "venue, because the opening hours, the public holiday practice and the visitor profile differ.",
    "backtest_limit_selection": "- **The rule was chosen on the same data.** The default rule was "
    "chosen on the basis of these same windows, so its advantage over the other rules is an "
    "overestimate. The per-venue benefit, on the other hand, is measured outside the training "
    "period.",
    "backtest_limit_hindsight": "- **The measurement uses two pieces of hindsight.** The candidate "
    "set is the days that turned out observed, complete and above zero, and `k` is taken from the "
    "number of candidates in the actuals. Both apply equally to the rule and to a random choice, "
    "but the rule is therefore not punished for proposing a closed day.",
    "backtest_limit_events": "- **The past holds no events calendar.** If activation events start "
    "being held at the venue on quiet days, they will change exactly the days the model forecasts, "
    "and the measurement has to be repeated.",
    "backtest_limit_overlap": "- **The windows overlap.** In a rolling sweep, successive windows "
    "share days, so they are not independent and the confidence interval is narrower than it "
    "really is. A monthly sweep has no overlap.",
    # -- warnings ----------------------------------------------------------------------
    "warn_tie": "The cut falls inside a tie group: {size} days get the same score and {chosen} of "
    "them fitted into the quietest set. The model does not separate these days from each other, so "
    "the choice among them is in date order and can be made on other grounds.",
    "warn_not_material": "The quietest fifth of the month is only {gap} quieter than the median "
    "day, so the month is flat and the recommendation does not separate the days materially.",
    "warn_default_residuals": "The probabilities were computed with a default spread, because no "
    "inner origin fitted inside the training period. They describe the model's ranking, not "
    "measured uncertainty.",
    "warn_stale_origin": "The last observation is {origin}, {days} days before the start of the "
    "month. The weekday medians describe a different period from the month being forecast.",
    "warn_calendar_gap": "The maintained calendar does not cover {first} onwards ({days} days), so "
    "those days assume there are no public holidays.",
    "warn_climatology": "The weather is climatology for {days} days; it is background and does not "
    "affect the scoring.",
    "warn_closed_weekdays": "Closed weekdays excluded from the candidates: {days}.",
}

TEXT: dict[Lang, dict[str, str]] = {"fi": FI, "en": EN}


def text(lang: Lang, key: str, **values: object) -> str:
    """One sentence in one language, with its placeholders filled."""
    template = TEXT[lang].get(key) or TEXT[DEFAULT_LANG].get(key, key)
    return template.format(**values) if values else template


__all__ = [
    "CHANCE_PHRASES",
    "EN",
    "FI",
    "STATUS_PHRASES",
    "TEXT",
    "VERDICT_PHRASES",
    "WEEKDAY_NAMES",
    "text",
]
