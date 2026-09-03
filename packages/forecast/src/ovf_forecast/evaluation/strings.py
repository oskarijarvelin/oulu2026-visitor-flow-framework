"""Every sentence the evaluation writes, in both languages.

The renderer holds the layout and the numbers; this module holds the words. Keeping them
apart is what makes a second language cheap: a new section is a key here and a lookup
there, and no prose ever appears inline in a f-string where only one language can reach it.

Placeholders are ``str.format`` fields, so a translation may reorder them freely — Finnish
and English disagree about where a subject goes often enough that positional interpolation
would force a stilted word order on one of them.

``test_report_strings.py`` asserts that the two tables have exactly the same keys and the
same placeholders per key. That is the guarantee a type checker would give for a dataclass,
except it also holds for the placeholders, which is where a translation actually breaks.
"""

from __future__ import annotations

from ..i18n import DEFAULT_LANG, Lang

VERDICT_PHRASES: dict[Lang, dict[str, str]] = {
    "fi": {
        "better": "parempi kuin vertailukohta",
        "worse": "huonompi kuin vertailukohta",
        "no_difference": "ei havaittavaa eroa vertailukohtaan",
    },
    "en": {
        "better": "better than the reference",
        "worse": "worse than the reference",
        "no_difference": "no detectable difference from the reference",
    },
}

CALIBRATION_PHRASES: dict[Lang, dict[str, str]] = {
    "fi": {"calibrated": "kalibroitu", "too_narrow": "liian kapea", "too_wide": "liian leveä"},
    "en": {"calibrated": "calibrated", "too_narrow": "too narrow", "too_wide": "too wide"},
}

BIAS_PHRASES: dict[Lang, dict[str, str]] = {
    "fi": {
        "unbiased": "ei systemaattista harhaa",
        "over_forecast": "yliarvioi systemaattisesti",
        "under_forecast": "aliarvioi systemaattisesti",
    },
    "en": {
        "unbiased": "no systematic bias",
        "over_forecast": "systematically overestimates",
        "under_forecast": "systematically underestimates",
    },
}

WEATHER_LABELS: dict[Lang, dict[str, str]] = {
    "fi": {
        "perfect": "perfect (toteutunut sää)",
        "operational": "operational (toteutunut vrk 1-16, klimatologia 17+)",
        "climatology": "climatology (klimatologia koko jaksolta)",
    },
    "en": {
        "perfect": "perfect (the realised weather)",
        "operational": "operational (realised days 1-16, climatology from 17)",
        "climatology": "climatology (climatology for the whole period)",
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
    # -- worst-day causes -------------------------------------------------------------
    "cause_holiday": "pyhäpäivä: {holiday}",
    "cause_rain": "runsas sade {mm} mm",
    "cause_zero": "toteuma 0, venue todennäköisesti kiinni",
    "cause_climatology": "malli sai klimatologiasään (horisontti {horizon} vrk)",
    "cause_weekend": "viikonloppu",
    "cause_unknown": "ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne",
    # -- shared ----------------------------------------------------------------------
    "title": "Ennusteen arviointiraportti",
    "run_id": "Ajon tunniste: `{run_id}`",
    "venue_heading": "## Venue {venue_id} ({venue_name})",
    "none": "ei yhtään",
    # -- window: verdict and setup ----------------------------------------------------
    "window_title": "# {title}: {test_start} – {test_end}",
    "h_verdict": "## 1. Verdikti",
    "h_setup": "## 2. Ikkuna ja asetelma",
    "setup_origin": "- Origo (viimeinen koulutuspäivä): **{origin}**",
    "setup_test": "- Testijakso: **{test_start} – {test_end}** ({days} vrk, horisontit 1–{days})",
    "setup_train_window": "- Koulutusikkuna: `{train_window}`",
    "setup_models": "- Mallit: {models}",
    "setup_baselines": "- Vertailukohdat: {baselines}",
    "setup_reference": "- Päävertailukohdan valinta: `{reference}`",
    "setup_weather": "- Sään tilat: {modes} (verdikti tilasta `{primary}`)",
    "setup_bootstrap": "- Bootstrap: {resamples} uudelleenotantaa, lohkon pituus 7 vrk, siemen {seed}",
    "setup_table": "Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja "
    "| MASE-nimittäjä",
    "setup_note": "Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan "
    "kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten "
    "yksikään sisäennuste ei ylety testijaksoon.",
    # -- window: totals ---------------------------------------------------------------
    "h_totals": "### 3. Jakson kokonaismäärä",
    "totals_table": "Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu "
    "| Naiivi päiväsummaväli",
    "totals_note": "Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin "
    "päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen "
    "simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin "
    "päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden "
    "osuvan samaan suuntaan eikä ole kokonaismäärän väli.",
    "totals_drift_prefix": "⚠ **Näiden mallien väli ei ole kalibroitu:** ",
    "totals_drift_item": "{model} (suhteellisten virheiden mediaani {ratio})",
    "totals_drift_tail": ". Sisäkkäisen backtestin mallit on koulutettu lyhyemmällä ja huonommalla "
    "aineistolla kuin ulompi malli, joten niiden virheissä on tasosiirtymä eikä pelkkää hajontaa. "
    "Väli perii sen. Lue kokonaismäärän ero ja bias erikseen, älä väliä.",
    "totals_thin_prefix": "⚠ Ohut otos: ",
    "totals_thin_item": "{model} ({n} havaintoa)",
    "totals_thin_tail": ". Väli lepää harvan sisäkkäisen backtestin varassa.",
    # -- window: daily metrics --------------------------------------------------------
    "h_daily": "### 4. Päivätason mittarit",
    "daily_intro": "Sään tila `{primary}`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.",
    "daily_table": "Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 "
    "| Pinball 0,9 | Peittävyys 80 % | sMAPE | n",
    "daily_smape_warning": "⚠ sMAPE on merkitty epäluotettavaksi: testijaksolla on nollapäiviä "
    "(enimmillään {zero_days} korissa). Nollapäivällä symmetrinen suhde saavuttaa kattonsa "
    "riippumatta siitä kuinka lähellä ennuste oli. sMAPEa ei käytetä verdiktin perustana.",
    "daily_smape_ok": "Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa "
    "luettavissa.",
    # -- window: statistics -----------------------------------------------------------
    "h_stats": "### 5. Tilastollinen arvio",
    "stats_intro": "Päävertailukohta tällä ikkunalla: **{reference}** (MAE {mae}). "
    "Vertailukohtien MAE: {all_mae}.",
    "stats_table": "Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli "
    "| MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm)",
    "stats_note_difference": "`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden "
    "erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon "
    "bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.",
    "stats_note_mde": "**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt "
    "olla, jotta tämä otos olisi sen erottanut. Kun verdikti on \"ei havaittavaa eroa\", MDE "
    "erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden "
    "ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi "
    "pystyy todistamaan vain suuret parannukset.",
    "stats_note_dm": "**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole "
    "riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten "
    "DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei "
    "t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on {family_size}.",
    # -- window: calibration ----------------------------------------------------------
    "h_calibration": "### 6. Kalibrointi ja bias",
    "calibration_table": "Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias "
    "| Bias 95 % väli | Bias % toteumasta | Biasin verdikti",
    "calibration_note": "Kalibrointi on \"kalibroitu\", jos 0,80 on Clopper-Pearsonin eksaktin "
    "binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei "
    "sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.",
    # -- window: weather --------------------------------------------------------------
    "h_weather": "### 7. Sään kolmen tilan vertailu",
    "weather_table": "Malli | perfect MAE | operational MAE | climatology MAE "
    "| Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta",
    "weather_note": "`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin "
    "täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` "
    "on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n "
    "MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja "
    "se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.",
    "weather_negative": "⚠ **Parannus on negatiivinen**, eli malli ennustaa tällä ikkunalla "
    "*paremmin* keskiarvosäällä kuin toteutuneella säällä. Se ei ole mittausvirhe vaan tulos: "
    "mallin oppima sääriippuvuus ei yleisty tähän jaksoon, vaan toteutunut sää vie ennustetta "
    "väärään suuntaan. Sääpiirteet sopivat siis koulutusjakson kohinaan enemmän kuin kävijöiden "
    "todelliseen sääkäyttäytymiseen.",
    "weather_days_table": "Sään tila | Toteutunutta säätä | Klimatologiaa",
    # -- window: worst days -----------------------------------------------------------
    "h_worst": "### 9. Pahiten menneet päivät",
    "worst_table": "Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy",
    "worst_note": "Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva "
    "syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.",
    # -- window: limitations ----------------------------------------------------------
    "h_limits": "## 8. Rajoitteet",
    "limit_sample": "- **Otoskoko.** Yksi ikkuna on {horizon} päivää yhdestä origosta. Ne eivät "
    "ole {horizon} riippumatonta havaintoa: kaikki jakavat saman koulutusjoukon ja saman kuukauden "
    "sään.",
    "limit_single_window": "- **Yhden ikkunan verdikti on kuvaileva, ei todistava.** Varsinainen "
    "näyttö syntyy usean ikkunan koosteesta (`--sweep monthly` tai `--sweep rolling`).",
    "limit_no_difference": "- **\"Ei havaittavaa eroa\" ei tarkoita samanveroisuutta.** Lue MDE "
    "kohdasta 5 ennen kuin teet siitä johtopäätöksen.",
    "limit_smape": "- **sMAPEa ei käytetä verdiktin perustana**, koska nollapäivät rikkovat sen.",
    "limit_history": "- **Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta.** "
    "Vuosikausivaihtelua ei voi oppia, joten vertailu toiseen vuoteen ei ole mahdollinen.",
    "limit_tickets": "- **Lippudataa ei käytetä piirteenä**, koska sitä ei ole tulevaisuudelle.",
    "limit_leading_zeros": "- **Venue {venue_id}: koulutusikkunan alussa on {days} nollapäivää** "
    "sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on "
    "se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: "
    "vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät "
    "saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. "
    "Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.",
    "limit_missing_days": "- **Venue {venue_id}: testijaksolta puuttuu {days} päivää**, joilta ei "
    "ole havaintoa.",
    "limit_default_bands": "- **Venue {venue_id}: osa ennustevälejä on oletusarvoja** ({buckets}), "
    "koska sisäkkäinen backtest ei tuottanut tarpeeksi havaintoja kyseiseen horisonttikoriin. "
    "Peittävyyslukua ei pidä lukea niistä.",
    # -- sweep ------------------------------------------------------------------------
    "sweep_title": "# {title}, kooste: {kind} {first_day} – {last_day}",
    "h_sweep_verdict": "## 1. Koosteverdikti",
    "h_sweep_windows": "## 2. Ikkunat",
    "sweep_windows_table": "# | Testijakso | Origo | Koulutusikkuna | Ajon tunniste",
    "sweep_meta": "Sään tila verdiktille: `{primary}`. Päävertailukohdan valinta: `{reference}`. "
    "Monivertailuperheen koko: {family_size}.",
    "h_sweep_pooled": "### Koosteverdikti",
    "sweep_pooled_table": "Malli | Vertailukohta | Ikkunoita | Päiviä | Keskiero d | 95 % väli "
    "| Verdikti | Puolesta | Vastaan | MDE | MDE / vertailun MAE",
    "h_sweep_per_window": "### Ikkunakohtaiset tulokset: {model}",
    "sweep_window_table": "Testijakso | Vertailukohta | Mallin MAE | Vertailun MAE | Keskiero d "
    "| 95 % väli | Verdikti | MDE | MDE % | DM p (raaka) | DM p (Holm)",
    "h_sweep_totals": "#### Jakson kokonaismäärät: {model}",
    "sweep_totals_table": "Testijakso | Ennuste | Toteuma | Ero % | 80 % väli | Väli osuu",
    "h_sweep_limits": "## Rajoitteet",
    "sweep_limit_windows": "- Kooste bootstrapataan **kokonaisina ikkunoina**, koska ikkuna on "
    "riippumattomuuden luonnollinen yksikkö: kaksi saman ikkunan päivää jakavat koulutusjoukon, "
    "kaksi eri ikkunaa eivät.",
    "sweep_limit_descriptive": "- Ikkunakohtainen verdikti on kuvaileva. Koosteverdikti on se, "
    "joka kantaa näyttöä.",
    "sweep_limit_holm": "- Raakoja p-arvoja on korjattu Holm-Bonferronilla; perheen koko on "
    "kerrottu yllä.",
    "sweep_limit_history": "- Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös "
    "kooste lepää ohuen otoksen varassa.",
    # -- pooled across every stored run -----------------------------------------------
    "pooled_title": "# Arviointien kooste kaikista tallennetuista ajoista",
    "pooled_runs": "Ajoja mukana: {runs}.",
    "pooled_table": "Venue | Malli | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti "
    "| Puolesta | Vastaan | MDE | MDE %",
    "pooled_note": "Kooste bootstrapataan kokonaisina ikkunoina. Ikkunat tulevat eri ajoista ja "
    "voivat olla päällekkäisiä; päällekkäiset ikkunat eivät ole riippumattomia, joten väli on "
    "tältä osin optimistinen.",
    # -- the verdict paragraph --------------------------------------------------------
    "sum_window_intro": "Ikkuna {test_start}–{test_end} ({days} vrk), koulutus päättyy {origin}, "
    "koulutusikkuna {train_window}, sään tila {primary}.",
    "sum_model_head": "{venue}: malli {model} teki keskimäärin {model_mae} kävijän päivävirheen, "
    "päävertailukohta {reference} {reference_mae}.",
    "sum_model_better": " Malli on tilastollisesti parempi: ero {difference} kävijää päivässä "
    "(95 % väli {ci_low}…{ci_high}), taitopistemäärä {skill}.",
    "sum_model_worse": " Malli häviää vertailukohdalle tilastollisesti: ero {difference} kävijää "
    "päivässä (95 % väli {ci_low}…{ci_high}). Yksinkertainen sääntö {reference} on tällä ikkunalla "
    "parempi kuin malli.",
    "sum_model_none": " Eroa ei havaittu: {difference} kävijää päivässä (95 % väli "
    "{ci_low}…{ci_high}).",
    "sum_power": " Tämä otos ({n} päivää) olisi erottanut vasta {mde} kävijän eron, eli {mde_pct} "
    "% vertailukohdan MAE:sta",
    "sum_power_tail_none": "; \"ei eroa\" ei siis tarkoita samanveroisuutta.",
    "sum_power_tail": ".",
    "sum_total": " Jakson kokonaismäärä: ennuste {predicted}, toteuma {actual}, ero "
    "{difference_pct} %, 80 % väli {p10}–{p90}.",
    "sum_window_tail": "Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy "
    "usean ikkunan koosteesta.",
    "sum_sweep_intro": "Kooste ({kind}): {windows} ikkunaa, {first_day}–{last_day}, sään tila "
    "{primary}, päävertailukohta {reference}.",
    "sum_sweep_head": "{venue}: malli {model} vastaan {reference}, {windows} ikkunaa ({days} "
    "päivää). Malli oli parempi {favouring} ikkunassa ja huonompi {opposing} ikkunassa.",
    "sum_sweep_better": " Kooste puoltaa mallia: keskiero {difference} kävijää päivässä "
    "(95 % väli {ci_low}…{ci_high}).",
    "sum_sweep_worse": " Kooste on mallia vastaan: malli häviää yksinkertaiselle vertailukohdalle, "
    "keskiero {difference} kävijää päivässä (95 % väli {ci_low}…{ci_high}).",
    "sum_sweep_none": " Kooste ei erota malleja: keskiero {difference} kävijää päivässä "
    "(95 % väli {ci_low}…{ci_high}), ja tämä ikkunamäärä olisi erottanut vasta {mde} kävijän eron "
    "({mde_pct} % vertailukohdan MAE:sta). Tulos ei siis todista malleja yhtä hyviksi.",
    "sum_sweep_tail": "Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste "
    "lepää ohuen otoksen varassa. Lisää dataa tai tapahtumakalenteri piirteenä voisi muuttaa "
    "tuloksen.",
}

EN: dict[str, str] = {
    # -- worst-day causes -------------------------------------------------------------
    "cause_holiday": "public holiday: {holiday}",
    "cause_rain": "heavy rain {mm} mm",
    "cause_zero": "actual 0, the venue was probably closed",
    "cause_climatology": "the model got climatology weather (horizon {horizon} days)",
    "cause_weekend": "weekend",
    "cause_unknown": "no identified cause, possibly an event the model does not know about",
    # -- shared ----------------------------------------------------------------------
    "title": "Forecast evaluation report",
    "run_id": "Run id: `{run_id}`",
    "venue_heading": "## Venue {venue_id} ({venue_name})",
    "none": "none",
    # -- window: verdict and setup ----------------------------------------------------
    "window_title": "# {title}: {test_start} – {test_end}",
    "h_verdict": "## 1. Verdict",
    "h_setup": "## 2. The window and the setup",
    "setup_origin": "- Origin (the last training day): **{origin}**",
    "setup_test": "- Test period: **{test_start} – {test_end}** ({days} days, horizons 1–{days})",
    "setup_train_window": "- Training window: `{train_window}`",
    "setup_models": "- Models: {models}",
    "setup_baselines": "- References: {baselines}",
    "setup_reference": "- Main reference rule: `{reference}`",
    "setup_weather": "- Weather modes: {modes} (the verdict comes from `{primary}`)",
    "setup_bootstrap": "- Bootstrap: {resamples} resamples, block length 7 days, seed {seed}",
    "setup_table": "Venue | Training starts | Training days | Zero days | Nested origins "
    "| MASE denominator",
    "setup_note": "The prediction interval quantiles come from a nested backtest run entirely "
    "inside the training window: its last inner origin is the origin minus the horizon, so no "
    "inner forecast reaches into the test period.",
    # -- window: totals ---------------------------------------------------------------
    "h_totals": "### 3. The total for the period",
    "totals_table": "Model | Forecast | Actual | Difference | Difference % | 80 % interval "
    "| Interval covers | Naive daily sum interval",
    "totals_note": "The interval for the total is simulated: the daily relative errors of the "
    "backtest inside the training window are bootstrapped in blocks into whole periods, each "
    "simulated path is summed, and the interval is read from the distribution of those sums. The "
    "last column shows where summing the daily p10 and p90 values would have led; it assumes every "
    "day's error points the same way and is not an interval for the total.",
    "totals_drift_prefix": "⚠ **The interval for these models is not calibrated:** ",
    "totals_drift_item": "{model} (median relative error {ratio})",
    "totals_drift_tail": ". The models of the nested backtest are trained on shorter and poorer "
    "data than the outer model, so their errors carry a level shift rather than mere spread. The "
    "interval inherits it. Read the difference in the total and the bias separately, not the "
    "interval.",
    "totals_thin_prefix": "⚠ Thin sample: ",
    "totals_thin_item": "{model} ({n} observations)",
    "totals_thin_tail": ". The interval rests on a sparse nested backtest.",
    # -- window: daily metrics --------------------------------------------------------
    "h_daily": "### 4. Daily metrics",
    "daily_intro": "Weather mode `{primary}`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.",
    "daily_table": "Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 "
    "| Pinball 0.9 | Coverage 80 % | sMAPE | n",
    "daily_smape_warning": "⚠ sMAPE is flagged unreliable: the test period contains zero days "
    "(at most {zero_days} in a bucket). On a zero day the symmetric ratio hits its ceiling "
    "regardless of how close the forecast was. sMAPE does not ground the verdict.",
    "daily_smape_ok": "The test period has no zero days, so sMAPE is readable in this window.",
    # -- window: statistics -----------------------------------------------------------
    "h_stats": "### 5. Statistical assessment",
    "stats_intro": "The main reference on this window: **{reference}** (MAE {mae}). The references' "
    "MAE: {all_mae}.",
    "stats_table": "Model | Mean difference d | 95 % interval | Verdict | Skill score "
    "| Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm)",
    "stats_note_difference": "`d` is the difference between the model's and the reference's "
    "absolute daily errors; negative means the model is closer. The interval comes from a moving "
    "block bootstrap (block 7 days), which is this assessment's primary method.",
    "stats_note_mde": "**The MDE, the minimum detectable effect,** says how large the difference "
    "would have had to be for this sample to detect it. When the verdict is \"no detectable "
    "difference\", the MDE separates two different things: the models are equally good, or the "
    "sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % "
    "of the reference's MAE, so a month can only prove large improvements.",
    "stats_note_dm": "**Diebold-Mariano is secondary.** The 30 errors from one origin are not "
    "independent observations: they share the same training set and the same state of the world, "
    "so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not "
    "from a t-distribution. The Holm-corrected p-value was computed for a family of size "
    "{family_size}.",
    # -- window: calibration ----------------------------------------------------------
    "h_calibration": "### 6. Calibration and bias",
    "calibration_table": "Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias "
    "| Bias 95 % interval | Bias % of actual | Bias verdict",
    "calibration_note": "Calibration is \"calibrated\" when 0.80 falls inside the Clopper-Pearson "
    "exact binomial interval. Bias is the mean signed error (forecast minus actual); if its "
    "interval does not contain zero, the model systematically over- or underestimates.",
    # -- window: weather --------------------------------------------------------------
    "h_weather": "### 7. The three weather modes",
    "weather_table": "Model | perfect MAE | operational MAE | climatology MAE "
    "| Improvement from the weather (climatology − perfect) | Share of the climatology MAE",
    "weather_note": "`perfect` is the upper bound: what the model could do if the weather were "
    "known exactly. `climatology` is the lower bound: what it can do without a weather forecast. "
    "`operational` is the most realistic estimate and assumes a good weather forecast. The "
    "improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive "
    "figure means that knowing the weather helps**, and it is the share of the model's accuracy "
    "that rests on knowing the weather.",
    "weather_negative": "⚠ **The improvement is negative**, i.e. on this window the model forecasts "
    "*better* on average weather than on the realised weather. That is not a measurement error but "
    "a result: the weather dependence the model learned does not generalise to this period, and "
    "the realised weather pushes the forecast the wrong way. The weather features fit the noise of "
    "the training period more than the visitors' real behaviour in the weather.",
    "weather_days_table": "Weather mode | Realised weather | Climatology",
    # -- window: worst days -----------------------------------------------------------
    "h_worst": "### 9. The worst days",
    "worst_table": "Day | Weekday | Actual | Forecast | Error | Possible cause",
    "worst_note": "This is the most practical part of the report: it says what the model is "
    "missing. A recurring cause in the same column is a direct proposal for the next feature.",
    # -- window: limitations ----------------------------------------------------------
    "h_limits": "## 8. Limitations",
    "limit_sample": "- **Sample size.** One window is {horizon} days from one origin. They are not "
    "{horizon} independent observations: they all share the same training set and the same month "
    "of weather.",
    "limit_single_window": "- **A single window's verdict is descriptive, not probative.** The "
    "actual evidence comes from pooling several windows (`--sweep monthly` or `--sweep rolling`).",
    "limit_no_difference": "- **\"No detectable difference\" does not mean equivalence.** Read the "
    "MDE in section 5 before drawing a conclusion from it.",
    "limit_smape": "- **sMAPE does not ground the verdict**, because zero days break it.",
    "limit_history": "- **There is about eight months of data from a single year.** Year-to-year "
    "seasonality cannot be learned, so a comparison against another year is impossible.",
    "limit_tickets": "- **Ticket data is not used as a feature**, because it does not exist for "
    "the future.",
    "limit_leading_zeros": "- **Venue {venue_id}: the training window opens with {days} zero "
    "days** from before the sensor was installed. The evaluation does not remove them, because the "
    "training window is the one the user named; `--train-window` cuts them out. The zeros do not "
    "stay at the start: the seasonal feature `year_sin` is symmetric about midsummer, so January's "
    "zero days get the same value as the June days that mirror them and the model can read summer "
    "as January. If a forecast collapses towards zero in the middle of summer, this is the first "
    "place to look.",
    "limit_missing_days": "- **Venue {venue_id}: {days} days are missing from the test period**, "
    "with no observation for them.",
    "limit_default_bands": "- **Venue {venue_id}: some prediction intervals are defaults** "
    "({buckets}), because the nested backtest did not produce enough observations for that horizon "
    "bucket. The coverage figure should not be read from them.",
    # -- sweep ------------------------------------------------------------------------
    "sweep_title": "# {title}, pooled: {kind} {first_day} – {last_day}",
    "h_sweep_verdict": "## 1. Pooled verdict",
    "h_sweep_windows": "## 2. The windows",
    "sweep_windows_table": "# | Test period | Origin | Training window | Run id",
    "sweep_meta": "The weather mode for the verdict: `{primary}`. The main reference rule: "
    "`{reference}`. The multiple comparison family size: {family_size}.",
    "h_sweep_pooled": "### Pooled verdict",
    "sweep_pooled_table": "Model | Reference | Windows | Days | Mean difference d | 95 % interval "
    "| Verdict | In favour | Against | MDE | MDE / reference MAE",
    "h_sweep_per_window": "### Per-window results: {model}",
    "sweep_window_table": "Test period | Reference | Model MAE | Reference MAE | Mean difference d "
    "| 95 % interval | Verdict | MDE | MDE % | DM p (raw) | DM p (Holm)",
    "h_sweep_totals": "#### Period totals: {model}",
    "sweep_totals_table": "Test period | Forecast | Actual | Difference % | 80 % interval "
    "| Interval covers",
    "h_sweep_limits": "## Limitations",
    "sweep_limit_windows": "- The pooled result is bootstrapped over **whole windows**, because "
    "the window is the natural unit of independence: two days from the same window share a "
    "training set, two different windows do not.",
    "sweep_limit_descriptive": "- A per-window verdict is descriptive. The pooled verdict is the "
    "one that carries evidence.",
    "sweep_limit_holm": "- The raw p-values are corrected with Holm-Bonferroni; the family size is "
    "stated above.",
    "sweep_limit_history": "- There is about eight months of data from a single year, so the "
    "pooled result rests on a thin sample too.",
    # -- pooled across every stored run -----------------------------------------------
    "pooled_title": "# Evaluations pooled across every stored run",
    "pooled_runs": "Runs included: {runs}.",
    "pooled_table": "Venue | Model | Windows | Days | Mean difference d | 95 % interval | Verdict "
    "| In favour | Against | MDE | MDE %",
    "pooled_note": "The pooled result is bootstrapped over whole windows. The windows come from "
    "different runs and may overlap; overlapping windows are not independent, so the interval is "
    "optimistic to that extent.",
    # -- the verdict paragraph --------------------------------------------------------
    "sum_window_intro": "Window {test_start}–{test_end} ({days} days), training ends {origin}, "
    "training window {train_window}, weather mode {primary}.",
    "sum_model_head": "{venue}: the model {model} made a mean daily error of {model_mae} visitors, "
    "the main reference {reference} {reference_mae}.",
    "sum_model_better": " The model is statistically better: a difference of {difference} visitors "
    "per day (95 % interval {ci_low}…{ci_high}), skill score {skill}.",
    "sum_model_worse": " The model loses to the reference statistically: a difference of "
    "{difference} visitors per day (95 % interval {ci_low}…{ci_high}). The simple rule {reference} "
    "is better than the model on this window.",
    "sum_model_none": " No difference was detected: {difference} visitors per day (95 % interval "
    "{ci_low}…{ci_high}).",
    "sum_power": " This sample ({n} days) would only have resolved a difference of {mde} visitors, "
    "i.e. {mde_pct} % of the reference's MAE",
    "sum_power_tail_none": "; \"no difference\" therefore does not mean equivalence.",
    "sum_power_tail": ".",
    "sum_total": " The total for the period: forecast {predicted}, actual {actual}, difference "
    "{difference_pct} %, 80 % interval {p10}–{p90}.",
    "sum_window_tail": "A single window's result is descriptive, not probative: the actual evidence "
    "comes from pooling several windows.",
    "sum_sweep_intro": "Pooled ({kind}): {windows} windows, {first_day}–{last_day}, weather mode "
    "{primary}, main reference {reference}.",
    "sum_sweep_head": "{venue}: the model {model} against {reference}, {windows} windows ({days} "
    "days). The model was better in {favouring} windows and worse in {opposing}.",
    "sum_sweep_better": " The pooled result favours the model: a mean difference of {difference} "
    "visitors per day (95 % interval {ci_low}…{ci_high}).",
    "sum_sweep_worse": " The pooled result goes against the model: it loses to a simple reference, "
    "a mean difference of {difference} visitors per day (95 % interval {ci_low}…{ci_high}).",
    "sum_sweep_none": " The pooled result does not separate the models: a mean difference of "
    "{difference} visitors per day (95 % interval {ci_low}…{ci_high}), and this many windows would "
    "only have resolved a difference of {mde} visitors ({mde_pct} % of the reference's MAE). The "
    "result therefore does not prove the models equally good.",
    "sum_sweep_tail": "There is about eight months of data from a single year, so the pooled result "
    "rests on a thin sample too. More data, or an events calendar as a feature, could change it.",
}

TEXT: dict[Lang, dict[str, str]] = {"fi": FI, "en": EN}


def text(lang: Lang, key: str, **values: object) -> str:
    """One sentence in one language, with its placeholders filled.

    A key missing from a translation falls back to the default language rather than raising:
    a report with one Finnish sentence in it is worth more than no report at all, and the
    parity test is what stops that from happening quietly.
    """
    template = TEXT[lang].get(key) or TEXT[DEFAULT_LANG].get(key, key)
    return template.format(**values) if values else template


__all__ = [
    "BIAS_PHRASES",
    "CALIBRATION_PHRASES",
    "EN",
    "FI",
    "TEXT",
    "VERDICT_PHRASES",
    "WEATHER_LABELS",
    "WEEKDAY_NAMES",
    "text",
]
