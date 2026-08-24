# Claude Code -promptit: Oulu2026 Visitor Flow Framework

Neljä valmista promptia: kolme päälle osiolle ja yksi apuvälineelle. Kukin on itsenäinen
ja ajetaan omassa Claude Code -istunnossaan repon juuressa.

## Käyttöohje

**Suoritusjärjestys**: Osio 1 → Osio 3 → Osio 2. Web-osio tarvitsee valmiit datatiedostot,
ja ennusteosio tarvitsee ingestin tuotokset.

**Prompti 4 (lipputyökalu) on riippumaton** muista ja voidaan ajaa milloin tahansa, myös
ennen osioita 2 ja 3. Se ei ole osa päivittäistä automaattiajoa vaan korvaa manuaalisen
työvaiheen, jossa lippudata syötetään käsin.

**Ennen ensimmäistä promptia**, luo repo ja kopioi dokumentaatio:

```bash
mkdir -p ~/Documents/GitHub/oulu2026-visitor-flow-framework
cd ~/Documents/GitHub/oulu2026-visitor-flow-framework
git init
mkdir -p docs
cp ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/docs/DATA_MODEL.md docs/
cp ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/docs/FRAMEWORK_PLAN.md docs/
cp ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/docs/CLAUDE_CODE_PROMPTS.md docs/
claude
```

**Vinkkejä**:

- Aja jokainen prompti tuoreessa istunnossa, jotta konteksti pysyy puhtaana
- Anna Claude Codelle lupa ajaa testit ja lint automaattisesti
- Jokaisen osion lopussa on hyväksymiskriteerit, pyydä Claude Codea tarkistamaan ne
- Jos jokin osio jää kesken, jatka samassa istunnossa: dokumentit ovat repossa

---

## Prompti 1 / 3: ingest-osio (Python)

````text
Rakennat Oulu2026 Visitor Flow Frameworkin ensimmäisen osion: datan hakevan
ingest-paketin. Olet uuden, tyhjän repon juuressa.

# Lue ensin

- docs/DATA_MODEL.md: kuvaa kaikki ulkoiset rajapinnat, niiden parametrit, vastausten
  rakenteet ja nykyisen sovelluksen datan skeemat. Luku 2 on rajapintojen osalta
  autoritatiivinen, luku 7 kuvaa nykyiset tunnetut virheet jotka nyt korjataan.
- docs/FRAMEWORK_PLAN.md: luvut 3, 4 ja 5 ovat tämän osion spesifikaatio.

Referenssitoteutus on luettavissa polusta
~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool. Erityisesti
visitor_forecast/iot_sensors.py, weather.py ja traffic.py. Lue ne rajapintakutsujen
yksityiskohtien varmistamiseksi, mutta ÄLÄ kopioi arkkitehtuuria: uusi toteutus on
rakenteeltaan erilainen ja korjaa referenssin virheet.

# Tehtävä

Toteuta paketti packages/ingest (Python 3.12), joka hakee kolmesta rajapinnasta datan,
normalisoi sen ja kirjoittaa kanonisiksi tiedostoiksi. Ei mallinnusta, ei visualisointia.

# Repo-runko jonka luot

pyproject.toml juureen, riippuvuusryhmät: ingest (pandas, requests, pydantic,
python-dateutil, pyarrow), dev (pytest, ruff, mypy). Prophetia EI tähän osioon.

packages/ingest/src/ovf_ingest/
  __init__.py, cli.py, config.py, normalize.py, store.py, validate.py, climatology.py
  clients/jaskaretail.py, clients/openmeteo.py, clients/ecocounter.py
packages/ingest/tests/
config/venues.json, config/sources.json, config/sites.json, config/holidays.csv
data/raw/, data/processed/, data/reference/   (.gitkeep-tiedostoilla)
Makefile, README.md, .gitignore, .env.example

Kopioi config/holidays.csv suoraan referenssirepon
visitor_forecast/config/holidays.csv -tiedostosta. Muunna referenssin
settings.json:in venues-, iot_sensors-, weather-, eco_counters- ja
eco_counter_sites-osiot tiedostoihin config/venues.json, config/sources.json ja
config/sites.json. Älä keksi venue-arvoja: ne ovat venue 1 Pekuri (Oulu, 65.0134,
25.4756, capacity 160, locationHierarchyId 178) ja venue 2 Kaupungintalo (Espoo,
60.2055, 24.6558, capacity 20, locationHierarchyId 183).

# Rajapinnat

1. Jaskaretail IoT, kävijälaskenta
   POST https://oulu.jaskaretail.com:443/ext/sensor/visitor
   Query-parametrit: locationHierarchyIdList, startDate, endDate (YYYY-MM-DD),
   interval=60min, countingTypeId (haetaan erikseen arvoilla "in" ja "out").
   HTTP Basic auth ympäristömuuttujista JASKARETAIL_BASIC_AUTH_USERNAME ja
   JASKARETAIL_BASIC_AUTH_PASSWORD, ladataan .env-tiedostosta jos ympäristössä ei ole.
   Vastaus: {"result": [{"categoryName": "01/05/2026 08:00:00", "locationId": 178,
   "visitors": 12}, ...]}. Aikaleiman formaatti %d/%m/%Y %H:%M:%S, paikallista aikaa.
   Lukuarvo voi olla avaimissa visitors, counts, count tai value.

2. Open-Meteo, sää
   Historia: GET https://archive-api.open-meteo.com/v1/archive
   Ennuste:  GET https://api.open-meteo.com/v1/forecast, forecast_days enintään 16
   Parametrit: latitude, longitude, hourly=temperature_2m,precipitation,
   wind_speed_10m,relative_humidity_2m,weathercode, timezone=Europe/Helsinki
   Ei autentikointia. Johda lisäkentät: weathercode_str (WMO-koodikartta, katso
   referenssin weather.py WEATHER_CODES), is_precipitation (precipitation > 0),
   is_cold (temperature_2m < 0), is_windy (wind_speed_10m > 10).

3. Oulun liikenne Eco-Counter, jalankulku ja pyöräily
   POST https://api.oulunliikenne.fi/proxy/graphql
   Kysely per sensori:
   query { ecoCounterSiteData(id: "karjasilta_1", domain: Oulu_Kapy, step: hour,
           begin: "2026-05-01T00:00:00", end: "2026-05-22T00:00:00") { date counts } }
   domain ja step ovat enumeja (ei lainausmerkkejä), id, begin ja end merkkijonoja.
   Sivusto raatti (näyttönimi Karjasilta, domain Oulu_Kapy), sensorit:
   JK_IN=karjasilta_1, JK_OUT=karjasilta_2, PP_IN=karjasilta_4, PP_OUT=karjasilta_3.
   HUOM: vastauksen aikaleimat ovat UTC:ssä, toisin kuin muissa lähteissä.

# Aikavyöhykesopimus, ehdoton vaatimus

Nykyisen sovelluksen vakavin bugi on aikavyöhykkeiden sekoittuminen: Eco-Counterin
UTC-aikaleimoista poistetaan vyöhykemerkintä muuntamatta, joten liikennedata osuu
2-3 tuntia väärään tuntiin.

Uusi sopimus: jokaisella aikaleimallisella rivillä on KAKSI saraketta.
- ts_utc: ISO 8601 UTC, esim. 2026-05-22T04:00:00Z
- ts_local: ISO 8601 Europe/Helsinki offsetilla, esim. 2026-05-22T07:00:00+03:00
ts_utc on kaikkien liitosten avain. Päivätason rivit käyttävät date-saraketta, joka on
paikallinen kalenteripäivä. Käytä zoneinfo-moduulia, älä kiinteää offsettia.
Kesäaikasiirtymän päivinä tuntisarjassa on 23 tai 25 riviä, tämä on oikein.

# Tuotokset

Raakacache, muuttumaton kopio vastauksesta:
  data/raw/visitors/venue_{id}/{YYYY-MM-DD}.json
  data/raw/weather/venue_{id}/{YYYY-MM-DD}.json
  data/raw/traffic/{site_id}/{YYYY-MM-DD}.json

Kanoniset taulut (CSV, UTF-8, piste desimaalierottimena):
  data/processed/visitors_hourly.csv
    venue_id, ts_utc, ts_local, visitors_in, visitors_out, visitors_total, is_imputed
  data/processed/visitors_daily.csv
    venue_id, date, visitors_in, visitors_out, visitors_total, observed_hours, is_complete
  data/processed/weather_hourly.csv
    venue_id, ts_utc, ts_local, temperature_2m, precipitation, wind_speed_10m,
    relative_humidity_2m, weathercode, weathercode_str, is_precipitation, is_cold,
    is_windy, source
  data/processed/weather_daily.csv
    venue_id, date, temp_mean, temp_min, temp_max, precip_sum, precip_hours,
    wind_mean, weathercode_mode, weathercode_str, source
  data/processed/traffic_hourly.csv
    site_id, site_name, ts_utc, ts_local, jk_in, jk_out, pp_in, pp_out
  data/processed/tickets_daily.csv
    venue_id, date, tickets_sold, groups_sold, tickets_total
  data/processed/calendar_daily.csv
    date, holiday_name, is_holiday, is_weekend, day_of_week,
    days_before_next_holiday, is_last_workday_before_holiday, week_of_year, month, year
  data/processed/manifest.json
    ajon metatiedot: generated_at, pipeline, version, sources[] (name, status, rows,
    window, error), coverage{} (first, last, missing_hours per taulu),
    quality_gates{passed, warnings[]}

Tärkeät erot referenssiin:
- is_imputed erottaa aidon nollan puuttuvasta datasta. Referenssi täyttää puuttuvat
  tunnit nollilla eikä eroa voi enää havaita. Merkitse rivi is_imputed=true jos se
  luotiin tiheytyksessä eikä rajapinta palauttanut sille arvoa.
- Liikennedata on sivustokohtaista (site_id), EI venuekohtaista. Referenssi monistaa
  saman Karjasillan mittauspisteen molemmille venueille, mikä on harhaanjohtavaa.
- weather_hourly.source on archive, forecast tai climatology.
- visitors_total on visitors_in + visitors_out, kuten referenssissäkin. Dokumentoi
  tämä README:hen selvästi: se ei ole uniikkien kävijöiden määrä.

Lipunmyynti: lue referenssirepon data/raw/tickets/venue_{id}/tickets.csv, sarakkeet
DATE (muoto d.m.YYYY), TICKETS, GROUPS, TOTAL. Kopioi tiedostot uuteen repoon polkuun
data/raw/tickets/venue_{id}/tickets.csv ja normalisoi ne tickets_daily.csv:ksi.
Tue sarakenimien aliaksia myös suomeksi: pvm, liput, ryhmat, yhteensa.

# Toimintaperiaate

1. Inkrementaalinen ikkuna, oletus --days-back 7. Täysi haku --start 2026-01-01.
2. Raakavastaus levylle ENNEN normalisointia.
3. Idempotenssi: saman päivän uudelleenajo tuottaa saman tuloksen. Kanoniset taulut
   rakennetaan aina uudelleen kaikista päivätiedostoista, ei liitetä perään.
4. Osittainen epäonnistuminen ei kaada ajoa. Jos Eco-Counter on alhaalla, muut haetaan
   silti ja manifestiin merkitään status=degraded.
5. Retry: 3 yritystä eksponentiaalisella viiveellä (1s, 4s, 16s) HTTP 5xx ja
   timeout -tilanteissa. 4xx ei uudelleenyritetä.
6. Laatuportit ennen kanonisten tiedostojen kirjoitusta:
   - kävijäsarjassa ei yli 48 tunnin aukkoa viimeisen 30 vrk sisällä
   - säädatan kattavuus vähintään 99 % haetulla jaksolla
   - negatiiviset laskurit hylätään ja lokitetaan
   - päivän kokonaismäärä ei saa ylittää capacity * 24 * 4
   Portin pettäessä kirjoita uusi tiedosto .rejected-päätteellä, jätä vanha voimaan,
   merkitse manifestiin ja palauta exit code 1.

# Klimatologia

Erillinen komento, ajetaan kerran: hakee Open-Meteo archivesta kunkin venuen
koordinaateille 10 vuoden tuntidatan ja tallentaa keskiarvot muodossa
data/reference/climatology/venue_{id}.csv sarakkeilla
day_of_year, hour, temp_mean, temp_min, temp_max, precip_mean, wind_mean.
Karkauspäivä 29.2. liitetään edelliseen päivään. Tätä tarvitaan myöhemmin
vuorokausien 17-30 ennusteisiin, koska Open-Meteo antaa enintään 16 vrk ennustetta.

# CLI

python -m ovf_ingest run --days-back 7
python -m ovf_ingest run --start 2026-01-01 --end 2026-08-22
python -m ovf_ingest run --source weather --venue 1
python -m ovf_ingest climatology --years 2016-2025
python -m ovf_ingest verify

Exit codet: 0 kaikki ok, 1 laatuportti petti, 2 kaikki lähteet epäonnistuivat.
Lokitus stdout:iin rakenteisena (taso, aikaleima, lähde, viesti).

# Testit

pytest, ei verkkoyhteyttä testeissä. Tallenna oikeat vastausrakenteet
tests/fixtures/*.json -tiedostoiksi ja testaa niitä vasten:
- kunkin clientin parsinta fixture-syötteestä
- aikavyöhykemuunnos, mukaan lukien kesäaikasiirtymä (29.3.2026 ja 25.10.2026)
- is_imputed-logiikka
- laatuporttien laukeaminen
- idempotenssi: sama ajo kahdesti tuottaa identtiset tiedostot
- manifestin rakenne

# Hyväksymiskriteerit

1. python -m ovf_ingest run --start 2026-01-01 --end 2026-05-22 tuottaa
   visitors_hourly.csv:n jossa on 3407 riviä per venue. Laskutoimitus: 142 vuorokautta
   x 24 tuntia = 3408, miinus yksi tunti joka katoaa kesäaikasiirtymässä 29.3.2026.
   Referenssirepon venue_N_features.csv on 3408 riviä, koska se ei huomioi kesäaikaa
   lainkaan. Ero on odotettu ja on merkki siitä että aikavyöhykekäsittely on oikein.
2. Eco-Counterin ts_local on tasan 2 tuntia (talvi) tai 3 tuntia (kesä) ts_utc:tä
   edellä, ja sama tunti liittyy oikein kävijädataan.
3. python -m ovf_ingest verify menee läpi ja manifest.json on validi.
4. Ajo kahdesti peräkkäin tuottaa identtiset tiedostot (git diff on tyhjä).
5. ruff check ja mypy menevät läpi, pytest on vihreä.
6. README.md kertoo asennuksen, ympäristömuuttujat ja komennot.

# Älä tee näitä

- Älä käytä pandasin oletusarvoista aikaleimojen parsintaa ilman formaattia
- Älä täytä puuttuvia arvoja mediaaneilla, käytä NaN
- Älä kirjoita salaisuuksia repoon, .env on .gitignoressa ja .env.example on malli
- Älä toteuta ennustelogiikkaa tähän osioon
- Älä lisää Prophetia tai xgboostia riippuvuuksiin
````

---

## Prompti 2 / 3: forecast-osio (Python)

````text
Rakennat Oulu2026 Visitor Flow Frameworkin kolmannen osion: ennustepaketin. Repossa on
jo toimiva ingest-osio, joka on tuottanut kanoniset datatiedostot hakemistoon
data/processed/.

# Lue ensin

- docs/FRAMEWORK_PLAN.md luku 8 kokonaisuudessaan. Se on tämän osion spesifikaatio ja
  sisältää mallien tarkat rakenteet, piirteet, vahvuudet ja heikkoudet.
- docs/FRAMEWORK_PLAN.md luku 4.3: tulostiedostojen skeemat.
- docs/DATA_MODEL.md luku 7: nykyisen toteutuksen tunnetut ongelmat.
- packages/ingest/src/ovf_ingest/: mistä data tulee ja missä muodossa.

Referenssitoteutus: ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/
visitor_forecast/modeling.py. Lue se ymmärtääksesi mitä EI tehdä. Sen konkreettiset
virheet on lueteltu FRAMEWORK_PLAN.md luvussa 8.5.

# Tehtävä

Toteuta paketti packages/forecast, joka lukee data/processed/ ja tuottaa venuekohtaiset
7 vuorokauden tuntiennusteet ja 30 vuorokauden päiväennusteet kahdella mallilla, sekä
niiden laatumittarit. Ei rajapintakutsuja.

# Rakenne

packages/forecast/src/ovf_forecast/
  cli.py, dataset.py, features.py, profile.py, backtest.py, intervals.py, export.py
  models/base.py, models/baseline.py, models/prophet_xgb.py
packages/forecast/tests/

Riippuvuusryhmä forecast: pandas, numpy, scikit-learn, pyarrow.
Riippuvuusryhmä prophet: prophet, xgboost. Erillinen, koska Prophet vaatii cmdstanin.
Jos prophet-ryhmää ei ole asennettu, prophet_xgb-malli ohitetaan selkeällä varoituksella,
ei kaadeta ajoa.

# Mallien yhteinen rajapinta

class ForecastModel(Protocol):
    name: str
    def fit(self, daily: pd.DataFrame) -> None: ...
    def predict(self, future: pd.DataFrame) -> pd.Series: ...

MOLEMMAT mallit ennustavat päivätasolla. Tuntitaso johdetaan yhteisellä
profiilikomponentilla. Näin mallit ovat vertailukelpoisia ja tuntiennusteiden summa on
täsmälleen päiväennuste. Referenssitoteutus ennustaa visitors_in, visitors_out ja
total_visitors erillisillä malleilla, jolloin ne eivät summaudu (esim. 63,99 + 52,12
ei ole 191,31). Tätä ei toisteta.

# Perusmalli, nimi "baseline"

Kerros 1, päivätason taso:
  sklearn.ensemble.HistGradientBoostingRegressor(loss="poisson")
  Kohde: visitors_total päivätasolla, venuekohtaisesti.
  Poisson-tappio koska kohde on laskurisuure, jakauma on vino ja ennusteen on oltava
  ei-negatiivinen ilman jälkikäteistä leikkausta.

  Piirteet:
  - Kalenteri: day_of_week (kategorinen), is_weekend, is_holiday,
    days_before_next_holiday (katkaistu 14:ään), is_last_workday_before_holiday,
    month, week_of_year
  - Vuodenaika: sin(2*pi*d/365), cos(2*pi*d/365), sin(4*pi*d/365), cos(4*pi*d/365)
  - Trendi: days_since_start
  - Sää: temp_mean, temp_max, precip_sum, precip_hours, wind_mean, is_rainy_day,
    weather_group (clear/cloudy/rain/snow/other, johdettu weathercodesta)
  - Taso: level_7d, level_28d, dow_index_28d

  level_7d ja level_28d ovat viimeisten 7 ja 28 HAVAITUN päivän keskiarvot ennusteen
  origossa, ja ne ovat VAKIOITA koko horisontin ajan. dow_index_28d on kyseisen
  viikonpäivän keskiarvon suhde 28 vrk keskiarvoon.

  KRIITTINEN: mallissa ei saa olla autoregressiivisiä viiveitä jotka päivittyisivät
  ennusteen edetessä. Referenssitoteutus syöttää omat ennusteensa takaisin lag_24h- ja
  lag_168h-piirteisiin, jolloin virhe kumuloituu. Tässä 30 vrk ennuste ei saa olla
  30 kertaa ketjutettu yhden päivän ennuste.

  Lippudataa ei käytetä piirteenä, koska sitä ei ole tulevaisuudelle.

Kerros 2, tuntiprofiili (profile.py, yhteinen molemmille malleille):
  share[venue][dow][hour] = keskiarvo osuuksista visitors_hour / visitors_day
  niiltä päiviltä joilla visitors_day > 0, viimeiset 8 viikkoa.
  Kutistus: share_final = (n_dow * share_dow + k * share_all) / (n_dow + k), k = 4
  Aukioloajat datasta: tunti on suljettu jos sen ei-nolla-osuus viimeisen 8 viikon
  aikana on alle 5 %. Suljettujen tuntien osuus pakotetaan nollaan ennen normalisointia.
  Normalisoi lopuksi niin että päivän osuuksien summa on tasan 1.
  Tuntiennuste = daily_p50 * share_final.

Kerros 3, epävarmuus (intervals.py, yhteinen):
  1. Aja rolling origin -backtest.
  2. Laske suhteellinen virhe r = y_true / y_pred jokaiselle (origo, horisontti).
  3. Laske r-jakauman kvantiilit q10 ja q90 horisonttikoreittain: 1-7, 8-14, 15-30.
  4. p10 = p50 * q10(h), p90 = p50 * q90(h).
  Suhteellinen muotoilu on tarkoituksellinen: virheen hajonta skaalautuu tason mukana.
  Tuntitasolla käytetään samaa suhteellista leveyttä kuin päivätasolla.

# Vertailumalli, nimi "prophet_xgb"

1. Prophet päivätason kohteeseen: trendi + viikkokausi + vuosikausi + pyhäpäivät +
   sääregressorit (temp_mean, precip_sum, wind_mean).
2. XGBoost Prophetin residuaaleihin kalenteri- ja sääpiirteillä.
3. Lopullinen ennuste prophet_yhat + xgb_residual, leikattuna nollaan.
4. Tuntitaso ja epävarmuus samoista yhteisistä kerroksista 2 ja 3. Prophetin omia
   yhat_lower ja yhat_upper -arvoja EI käytetä.

Referenssin virheet joita ei toisteta:
- Tuntitason Prophet jossa on sekä daily_seasonality=True että oma hourly_pattern-kausi
  period=1. Nämä ovat sama vuorokausikausi kahdesti, mikä on kollineaarinen.
- Päivätason ennusteväli laskettuna 24 tuntivälin summana. Se tuottaa absurdeja
  välejä, esimerkiksi ennuste 29 kävijää välillä 0-502.
- Yksi 80/20 aikajakosplit mittareiden laskentaan.
- Puuttuvien piirteiden mediaanitäyttö.

# Sää yli 16 vuorokauden

Open-Meteo antaa enintään 16 vrk ennustetta, mutta horisontti on 30 vrk.
  Vuorokaudet 1-16:  data/processed/weather_daily.csv, source=forecast
  Vuorokaudet 17-30: data/reference/climatology/venue_{id}.csv, source=climatology
Merkitse jokaiselle ennusteriville weather_source-sarake. Klimatologia tasoittaa
ennustetta, ja tämä on tehtävä näkyväksi käyttöliittymälle.

# Validointi (backtest.py)

Rolling origin:
  origo o = viimeisin havaittu päivä miinus (n * 7 vrk), n = 1..N
  koulutus = kaikki data <= o
  ennuste = o+1 .. o+30
Origoja niin monta kuin dataa riittää, vähintään 8, ja jokaisessa koulutusjoukossa
vähintään 60 päivää.

Mittarit horisonttikoreittain (1-7, 8-14, 15-30) ja mallikohtaisesti:
MAE, RMSE, sMAPE, bias (keskivirhe etumerkillä), peittävyys 80 %
(osuus toteumista p10-p90 välillä, tavoite 0,80).

Vertailukohdat, jotka on AINA laskettava ja raportoitava mallien rinnalla:
- seasonal_naive: sama viikonpäivä viikko sitten
- moving_average_28d: viimeisten 28 päivän keskiarvo
Jos kumpikaan varsinainen malli ei voita näitä, se on raportoitava selkeästi.

# Tuotokset

data/forecasts/latest/manifest.json
data/forecasts/latest/venue_{id}/daily_30d.csv
  venue_id, date, horizon_days, model, p10, p50, p90, weather_source,
  temp_mean, precip_sum, weathercode_str, is_holiday, holiday_name, generated_at
  Rivit MOLEMMILLE malleille, eli 60 riviä per venue.
data/forecasts/latest/venue_{id}/hourly_7d.csv
  venue_id, ts_utc, ts_local, horizon_hours, model, p10, p50, p90, hour,
  weather_source, temperature_2m, precipitation, weathercode_str, generated_at
data/forecasts/latest/venue_{id}/metrics.json
  mallikohtaiset ja vertailukohtakohtaiset mittarit horisonttikoreittain,
  lisäksi n_origins, backtest_window, trained_at, n_training_days
data/forecasts/latest/venue_{id}/backtest.csv
  model, venue_id, origin_date, target_date, horizon_days, y_true, y_pred, p10, p90
data/forecasts/{YYYY-MM-DD}/...  arkistokopio samasta rakenteesta

# CLI

python -m ovf_forecast run
python -m ovf_forecast run --model baseline
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12
python -m ovf_forecast report

Ajon on oltava deterministinen: kiinteä random_state, ei aikaan sidottuja
satunnaisuuksia. Sama syöte tuottaa saman tuloksen.

# Testit

- Piirteiden rakennus ei vuoda tulevaisuutta: testi joka varmistaa että origon jälkeisiä
  havaintoja ei käytetä minkään piirteen laskennassa
- Tuntiennusteiden summa on tasan päiväennuste (toleranssi 1e-6)
- p10 <= p50 <= p90 aina
- Ennusteet ovat ei-negatiivisia
- Profiilin osuuksien summa on 1 jokaiselle (venue, dow)
- Backtest ei käytä koulutuksessa origon jälkeistä dataa
- prophet_xgb ohitetaan siististi jos prophet puuttuu
- Synteettinen data jossa on tunnettu viikkorytmi: malli oppii sen

# Hyväksymiskriteerit

1. python -m ovf_forecast run tuottaa kaikki luvun "Tuotokset" tiedostot molemmille
   venueille ja molemmille malleille.
2. Perusmalli voittaa seasonal_naive-vertailukohdan MAE:ssa horisonteilla 1-7.
   Jos ei voita, raportoi tämä selkeästi ja kerro mitä piirteitä kannattaisi lisätä.
3. 80 % peittävyys on välillä 0,70-0,90 horisonteilla 1-7.
4. Kaksi peräkkäistä ajoa tuottaa identtiset tiedostot pois lukien generated_at.
5. Koko ajo ilman prophetia kestää alle 60 sekuntia molemmille venueille.
6. ruff, mypy ja pytest menevät läpi.
7. Kirjoita docs/FORECAST_MODEL.md joka dokumentoi molemmat mallit: rakenne, piirteet,
   vahvuudet, heikkoudet, milloin ennustetta ei pidä uskoa, ja MITATUT backtest-luvut.
   Pohjana docs/FRAMEWORK_PLAN.md luku 8, mutta korvaa arviot todellisilla luvuilla.

# Älä tee näitä

- Älä syötä ennusteita takaisin viivepiirteisiin
- Älä käytä Prophetin omia ennustevälejä
- Älä summaa tuntivälejä päiväväliksi
- Älä ennusta visitors_in ja visitors_out erillisillä malleilla, jaa ne historiallisella
  suhteella päiväennusteesta
- Älä hae mitään rajapinnasta tässä osiossa
- Älä piilota huonoja tuloksia: jos malli häviää vertailukohdalle, se raportoidaan
````

---

## Prompti 3 / 3: web-osio (Astro)

````text
Rakennat Oulu2026 Visitor Flow Frameworkin toisen osion: staattisen web-käyttöliittymän.
Repossa on jo ingest- ja forecast-osiot, jotka ovat tuottaneet tiedostot hakemistoihin
data/processed/ ja data/forecasts/latest/.

# Lue ensin

- docs/FRAMEWORK_PLAN.md luku 7: tämän osion spesifikaatio, sivut ja näkymät
- docs/FRAMEWORK_PLAN.md luvut 4.2 ja 4.3: syötetiedostojen tarkat skeemat
- docs/FORECAST_MODEL.md: mitä ennuste tarkoittaa ja mitkä sen rajoitteet ovat
- data/processed/*.csv ja data/forecasts/latest/: katso oikeat tiedostot ennen koodausta

# Tehtävä

Toteuta packages/web: Astro 5 -projekti, joka paketoi datan build-aikana ja
visualisoi sen. Täysin staattinen, julkaistaan Cloudflare Pagesiin.

# Teknologiat

- Astro 5, output: 'static'
- TypeScript strict-tilassa
- Tailwind CSS 4
- Observable Plot kaavioihin (@observablehq/plot)
- Ei React-, Vue- tai Svelte-integraatiota. Kaaviot ovat vanilla TS -saarekkeita,
  ladataan client:visible-direktiivillä.

# Build-aikainen datan paketointi

scripts/build-data.ts ajetaan ennen astro buildia (npm-skripti prebuild). Se lukee
../../data/processed/ ja ../../data/forecasts/latest/, laskee aggregaatit ja kirjoittaa
src/data/-hakemistoon (gitignore):

  meta.json     venuet, viimeisin päivitys, datan kattavuus, laatuvaroitukset  < 5 kB
  daily.json    venuekohtainen päiväsarja: kävijät, sää, liput, pyhät          ~60 kB
  hourly.json   tuntisarja, vain viimeiset 120 vrk, pyöristettynä              ~250 kB
  profile.json  viikonpäivä x tunti -matriisi, keskiarvo ja mediaani           ~10 kB
  forecast.json 7 vrk tunti ja 30 vrk päivä, molemmat mallit                   ~40 kB
  quality.json  backtest-mittarit ja ennuste vs. toteuma -sarja                ~30 kB

Yhteensä alle 400 kB. Pyöristä liukuluvut yhteen desimaaliin.

Buildin laatuportit, jotka kaatavat buildin selkeällä virheellä:
- data/processed/manifest.json puuttuu tai on yli 48 tuntia vanha
- ennustetiedostot puuttuvat
- skeema ei vastaa odotettua (tarkista sarakkeet, älä oleta)
Mieluummin epäonnistunut build kuin vanhaa dataa esittävä sivusto.

Tyypitä datasopimus src/lib/types.ts -tiedostoon ja validoi se buildissa.

# Sivut

/                 Yleiskuva: molemmat venuet rinnakkain, viimeiset 30 vrk, seuraavat
                  7 vrk, avainluvut, datan tuoreus
/venue/[id]       Venuekohtainen: aikasarja tunti- ja päivätasolla, viikonpäivä x tunti
                  -lämpökartta, kapasiteetin käyttöaste, lippuvertailu
/weather          Sään ja kävijämäärien suhde: hajontakuvio, sateiset vs. poutaiset,
                  säätilaluokittainen jakauma
/forecast         7 vrk tunti ja 30 vrk päivä, p10-p90 vyöhyke, mallien vertailu,
                  sään lähde merkittynä
/quality          Backtest: ennuste vs. toteuma horisonteittain, MAE ja peittävyys,
                  vertailu seasonal naiveen, tunnetut rajoitteet
/about            Mistä data tulee, mitä luvut tarkoittavat, mitä ne eivät tarkoita

# Näkymien vaatimukset

Aikasarja: x paikallista aikaa, y kävijätapahtumia. Historia yhtenäisenä viivana,
ennuste katkoviivana, p10-p90 vaaleana alueena. Pyhäpäivät pystyviivoina, sadetunnit
taustavärinä. Rajausvalitsin: 7 / 30 / 90 vrk / kaikki.

Lämpökartta: rivit viikonpäivä ma-su, sarakkeet tunti 0-23, arvo keskimääräinen
visitors_total. Sekventiaalinen väriskaala. Nolla-arvot on erotettava puuttuvista
visuaalisesti.

Sääkorrelaatio: hajontakuvio, x päivän keskilämpötila, y päivän kävijät, väri
säätilaluokka, koko sademäärä. Lineaarinen sovite ja selkeä huomautus siitä että
korrelaatio ei ole syysuhde.

Ennustenäkymä: mallivalitsin (baseline / prophet_xgb / molemmat), oletuksena vain
baseline. Legenda kertoo kummankin backtest-MAE:n. Vuorokaudet 17-30 merkitään
visuaalisesti erottuvasti, koska niiden sää on tilastollinen keskiarvo
(weather_source = climatology).

Datan laatu -banneri: jokaisella sivulla, kertoo viimeisen ajon ajan ja mahdolliset
degraded-lähteet manifestista.

# Esitystavan vaatimukset

- Kaikki päivämäärät ja kellonajat Suomen aikaa, muoto 22.5.2026 ja 14:00
- Luvut yksikön kanssa: "1 234 kävijätapahtumaa", ei pelkkä numero
- Selkeä huomautus jokaisella kävijäluvulla: visitors_total on sisään- ja ulosmenojen
  summa, ei uniikkien kävijöiden määrä
- Liikennedata (jalankulku, pyöräily) esitetään kontekstidatana, ei venuekohtaisena
  mittarina. Se on yksi mittauspiste Oulussa (Karjasilta) eikä liity venue 2:een.
- Käyttöliittymän kieli suomi
- Vältä pitkää ajatusviivaa leipätekstissä, käytä pistettä, pilkkua tai kaksoispistettä

# Saavutettavuus

- Väriskaalat toimivat harmaasävyisenä ja punavihervärisokealle
- Jokaisella kaaviolla tekstivastine tai taulukkonäkymä
- Näppäimistönavigaatio toimii kaikissa valitsimissa
- prefers-reduced-motion huomioitu
- Kontrastit vähintään WCAG AA

# Responsiivisuus

Mobiili ensin. Kaaviot skaalautuvat leveyden mukaan, leveä sisältö (taulukot,
lämpökartta) vierii omassa säiliössään eikä koko sivu vaakasuunnassa.

# Julkaisu

- astro build tuottaa dist/
- Cloudflare Pages: build command "npm run build", output directory
  "packages/web/dist", root directory repo juuri
- .github/workflows/deploy.yml joka rakentaa ja julkaisee pushissa mainiin

# Testit

- vitest: build-data.ts:n muunnokset ja aggregaatit
- Skeeman validointitesti: jos data/processed/-tiedoston sarakkeet muuttuvat, testi
  kaatuu selkeällä viestillä
- Playwright-savutesti: jokainen sivu latautuu ilman konsolivirheitä ja pääkaavio
  renderöityy

# Hyväksymiskriteerit

1. npm run build menee läpi ja tuottaa staattisen sivuston oikeasta datasta
2. Sivun kokonaispaino etusivulla alle 500 kB (gzip)
3. Lighthouse: suorituskyky yli 90, saavutettavuus yli 95
4. Kaikki kuusi sivua toimivat, myös mobiilileveydellä 375 px
5. Jos manifest.json on yli 48 tuntia vanha, build epäonnistuu selkeällä virheellä
6. Ennustenäkymä erottaa visuaalisesti vuorokaudet 1-16 ja 17-30
7. Kaikilla kaavioilla on tekstivastine
8. README.md kertoo kehityskomennot ja julkaisun

# Älä tee näitä

- Älä hae dataa ajonaikaisesti selaimesta, kaikki on build-aikaista
- Älä lisää palvelinreittejä tai API-endpointteja
- Älä upota CDN-skriptejä, kaikki riippuvuudet npm:stä ja bundlattuna
- Älä esitä ennustetta yhtenä lukuna ilman epävarmuusväliä
- Älä yhdistä liikennedataa venuekohtaiseksi kävijämittariksi
- Älä käytä localStorage-riippuvaista tilaa jota ilman sivu ei toimi
````

---

## Prompti 4 / 4: lipputyökalu (itsenäinen HTML)

Tämä on apuväline, ei osa päivittäistä automaattiajoa. Sen voi toteuttaa milloin tahansa,
myös ennen osioita 2 ja 3. Se korvaa nykyisen manuaalisen työvaiheen, jossa
`data/raw/tickets/venue_{id}/tickets.csv` päivitetään käsin.

````text
Rakennat Oulu2026 Visitor Flow Frameworkiin apuvälineen: selainpohjaisen työkalun, jolla
lipunmyyntijärjestelmän CSV-vienti muunnetaan venuekohtaisiksi lippumääriksi.

# Lue ensin

- docs/FRAMEWORK_PLAN.md luku 4.2, kohta tickets_daily.csv
- config/venues.json: venuet ja niiden tickets_path
- data/raw/tickets/venue_1/tickets.csv: kohdeformaatti johon työkalu tuottaa dataa
- packages/ingest/src/ovf_ingest/normalize.py: miten lippudata luetaan ja normalisoidaan

# Tehtävä

Toteuta yksi itsenäinen tiedosto: tools/tickets-parser.html

Käyttäjä avaa sen selaimessa suoraan tiedostojärjestelmästä (file://), pudottaa siihen
lipunmyynnin CSV-viennin, kartoittaa sarakkeet, tarkistaa tuloksen ja lataa
venuekohtaiset tickets.csv-tiedostot. Käyttö on viikoittainen, noin viisi minuuttia.

# Ehdottomat tekniset rajoitteet

1. YKSI tiedosto. Kaikki HTML, CSS ja JavaScript samassa tiedostossa.
2. NOLLA ulkoista pyyntöä. Ei CDN:ää, ei fontteja verkosta, ei analytiikkaa. Työkalun on
   toimittava täysin offline. Kirjoita CSV-parseri itse, älä käytä kirjastoa.
3. Ei build-vaihetta. Ei npm:ää, ei bundleria. Vanilla JS, moderni syntaksi on ok.
4. Kaikki käsittely selaimessa. Mitään ei lähetetä mihinkään. Kerro tämä käyttäjälle
   näkyvästi käyttöliittymässä, koska data on lipunmyyntitietoa.
5. Toimii Chromen, Safarin ja Firefoxin nykyversioilla.

# Käyttöliittymän kulku

Vaihe 1: tiedoston valinta
  Pudotusalue ja tiedostonvalitsin. Myös liitä leikepöydältä -vaihtoehto.
  Tunnista automaattisesti:
  - Merkistö: kokeile UTF-8 (TextDecoder fatal:true), varalla windows-1252. Poista BOM.
    Suomalaiset viennit ovat usein latin-1, joten tämä ei ole teoreettinen ongelma.
  - Erotin: pilkku, puolipiste, sarkain tai pystyviiva. Päättele riviltä jolla eniten
    johdonmukaisia sarakkeita, älä pelkästään ensimmäiseltä riviltä.
  - Otsikkorivi: onko ensimmäinen rivi otsikko vai data.
  Näytä tunnistuksen tulos ja anna käyttäjän ohittaa se käsin.

Vaihe 2: esikatselu
  Taulukko, ensimmäiset 20 riviä, sarakkeiden nimet ja pääteltävät tyypit.
  Näytä rivimäärä ja havaitut ongelmat (eri sarakemäärä eri riveillä, tyhjät rivit).

Vaihe 3: sarakekartoitus
  a) Päivämääräsarake ja sen formaatti.
     Tunnista automaattisesti: d.m.yyyy, dd.mm.yyyy, yyyy-mm-dd, d/m/yyyy, m/d/yyyy,
     ISO 8601 aikaleima, Excelin päivämääräsarjanumero.
     Jos sarake sisältää aikaleiman, ota siitä päivä. Älä tee aikavyöhykemuunnosta,
     oleta Suomen aika.
     TÄRKEÄ VAROITUS käyttöliittymään: framework tarvitsee TAPAHTUMAPÄIVÄN eli sen
     päivän jolloin kävijät tulevat, EI ostopäivää. Lipunmyyntiviennissä on usein
     molemmat. Jos valitun sarakkeen päivämääristä yli 20 % on menneisyydessä yli
     30 vrk tai jakauma on selvästi eri kuin toisella päivämääräsarakkeella, näytä
     huomautus: "Tämä näyttää ostopäivältä. Varmista että valitsit tapahtumapäivän."
  b) Venue-sarake.
     Listaa sarakkeen uniikit arvot esiintymismäärineen. Jokaiselle arvolle valitsin:
     venue 1 Pekuri / venue 2 Kaupungintalo / ohita.
     Venuet luetaan työkaluun upotetusta listasta, joka vastaa config/venues.json:ia ja
     on muokattavissa käyttöliittymässä.
     Jos venue-saraketta ei ole, koko tiedosto ohjataan yhdelle valitulle venuelle.
  c) Lippumäärien laskentatapa, neljä vaihtoehtoa:
     A. Erilliset sarakkeet: valitse yksittäislippujen sarake ja ryhmälippujen sarake
     B. Yksi määräsarake + tyyppisarake: valitse määräsarake, tyyppisarake, ja merkitse
        kunkin tyyppiarvon kohdalle onko se yksittäis- vai ryhmälippu
     C. Yksi määräsarake, kaikki yksittäislippuja, ryhmät nolla
     D. Yksi rivi = yksi lippu, lasketaan rivien lukumäärä
     Määrä-arvoissa tuettava sekä piste- että pilkkudesimaali ja tuhaterotin
     (välilyönti tai sitkeä välilyönti).
  d) Valinnainen suodatus:
     - Tilasarake ja siitä poissuljettavat arvot (esim. Peruttu, Refunded, Cancelled).
       Näytä uniikit arvot valittavina.
     - Päivämääräväli.
  Kartoitus tallennetaan nimettynä profiilina localStorageen. Profiilin lataus,
  tallennus, nimeäminen ja poisto. Jos localStorage ei ole käytettävissä
  (yksityinen ikkuna), työkalun on toimittava normaalisti ilman profiileja:
  kääri jokainen luku ja kirjoitus try/catchiin.

Vaihe 4: tulos ja tarkistukset
  Aggregointi: ryhmittele (venue_id, päivä), summaa tickets_sold, groups_sold ja
  tickets_total. tickets_total = tickets_sold + groups_sold, ellei lähteessä ole omaa
  kokonaissaraketta, jolloin käytä sitä ja varoita jos summa ei täsmää.
  Näytä venuekohtainen taulukko ja yhteenveto:
  - luettuja rivejä, hyväksyttyjä, ohitettuja ja syy ohitukselle
  - päivämääräväli ja päivien lukumäärä
  - lippujen kokonaismäärät venueittain
  - pieni pylväskaavio päivittäisistä määristä, piirrettynä inline-SVG:llä
  Varoitukset, jokainen omana rivinään ja klikattavissa niin että vastaavat lähderivit
  korostuvat esikatselussa:
  - päivämäärä ei jäsentynyt
  - venue-arvo kartoittamatta
  - negatiivinen määrä
  - tickets_total ei ole tickets_sold + groups_sold
  - sama päivä esiintyy lähteessä useasti (tämä on ok, ne summataan, mutta kerro se)
  - päivämäärä yli vuoden tulevaisuudessa tai ennen vuotta 2020
  - venue jolle ei tullut yhtään riviä

Vaihe 5: yhdistäminen olemassa olevaan
  Kaksi tilaa:
  - Korvaa: tuloksena vain juuri jäsennetty data
  - Yhdistä: käyttäjä lataa tai liittää nykyisen tickets.csv:n venuekohtaisesti,
    työkalu yhdistää, poistaa duplikaatit päivän perusteella (uusi voittaa) ja
    järjestää päivämäärän mukaan. Näytä erotus: montako päivää lisättiin, montako
    muuttui ja mitkä arvot muuttuivat.
  Yhdistä on oletus, koska käyttö on viikoittain kertyvää.

Vaihe 6: vienti
  - Lataa venuekohtainen tickets.csv jokaiselle kartoitetulle venuelle.
    Formaatti täsmälleen: otsikkorivi DATE,TICKETS,GROUPS,TOTAL, erotin pilkku,
    päivämäärä muodossa d.m.yyyy ILMAN etunollia (14.1.2026, ei 14.01.2026),
    rivinvaihto \n, merkistö UTF-8 ilman BOMia, ei desimaaleja kokonaisluvuissa.
    Tiedostonimi tickets-venue-{id}.csv, ja näytä ohje mihin polkuun se kuuluu:
    data/raw/tickets/venue_{id}/tickets.csv
  - Lataa yhdistetty tickets_daily.csv normalisoidussa muodossa
    venue_id,date,tickets_sold,groups_sold,tickets_total, päivämäärä ISO-muodossa.
    Tämä on tarkistusta varten, ingest tuottaa saman tiedoston itse.
  - Kopioi leikepöydälle -painike kummallekin.
  - Näytä seuraavat askeleet tekstinä: mihin tiedostot kopioidaan ja mikä komento
    ajetaan seuraavaksi (python -m ovf_ingest run).

# Käyttöliittymän vaatimukset

- Kieli suomi
- Vaiheet näkyvät edistymisen osoittimena, edelliseen vaiheeseen voi palata ilman että
  tehty työ katoaa
- Tumma ja vaalea teema prefers-color-scheme mukaan
- Toimii 375 px leveydellä, mutta ensisijainen käyttö on työpöydällä
- Näppäimistönavigaatio toimii kaikissa valitsimissa, näkyvä fokus
- Kontrastit vähintään WCAG AA
- Varoitukset eivät ole pelkästään värillä erotettuja, myös ikoni tai teksti
- Vältä pitkää ajatusviivaa leipätekstissä, käytä pistettä, pilkkua tai kaksoispistettä
- Ei riippuvuutta localStoragesta: ilman sitä kaikki toimii, vain profiilit puuttuvat

# CSV-parserin vaatimukset

Kirjoita RFC 4180 -yhteensopiva parseri:
- Lainausmerkeissä olevat kentät, joissa voi olla erotin, rivinvaihto tai
  kaksinkertaistettu lainausmerkki
- CRLF ja LF
- Tyhjät rivit ohitetaan
- Vaihteleva sarakemäärä ei kaada parsintaa, vaan kirjataan varoitukseksi
- 50 000 rivin tiedoston on jäsennyttävä alle sekunnissa. Jos tiedosto on suurempi kuin
  20 MB, näytä varoitus ennen jäsennystä.

# Itsetestaus

Koska build-vaihetta ei ole, sisällytä testit samaan tiedostoon. Kun URL-parametri
?selftest=1 on annettu, työkalu ajaa testit ja näyttää tulokset taulukkona normaalin
käyttöliittymän sijaan. Testattavaa vähintään:
- CSV-parsinta: lainausmerkit, upotettu erotin, upotettu rivinvaihto, kaksinkertainen
  lainausmerkki, CRLF, BOM
- Erottimen tunnistus kaikilla neljällä erottimella
- Päivämäärän jäsennys jokaisella tuetulla formaatilla, myös virheellisillä syötteillä
- Määrien jäsennys pilkkudesimaalilla ja tuhaterottimella
- Aggregointi: kaksi riviä samalle päivälle summautuu
- Kaikki neljä laskentatapaa A, B, C, D
- Yhdistäminen: duplikaattipäivä, uusi voittaa
- Vientiformaatti: etunollattomuus, otsikkorivi, rivinvaihdot
- Tapahtumapäivä vs. ostopäivä -heuristiikka laukeaa oikein

Luo lisäksi kolme esimerkkitiedostoa manuaalista testausta varten:
  tools/fixtures/tickets-sample-semicolon-latin1.csv
  tools/fixtures/tickets-sample-comma-utf8.csv
  tools/fixtures/tickets-sample-one-row-per-ticket.csv
Kukin sisältää molemmat venuet, muutaman viikon dataa, sekä tarkoituksellisia
ongelmarivejä: peruttu tilaus, virheellinen päivämäärä, tuntematon venue-arvo.

# Dokumentaatio

Kirjoita tools/README.md joka kertoo:
- mihin ongelmaan työkalu vastaa ja miksi se on selaimessa eikä Python-skriptinä
- käyttöohje vaiheittain
- miten tulos viedään repoon ja mitä sen jälkeen ajetaan
- selkeä huomautus: framework tarvitsee tapahtumapäivän, ei ostopäivää
- miten itsetestit ajetaan

Lisää maininta työkalusta myös repon juuren README.md:hen.

# Hyväksymiskriteerit

1. tools/tickets-parser.html avautuu suoraan file:// -osoitteesta ja toimii ilman
   verkkoyhteyttä. Tarkista selaimen verkkovälilehdeltä että ulkoisia pyyntöjä on nolla.
2. Kaikki kolme esimerkkitiedostoa jäsentyvät ja tuottavat oikeat summat.
3. ?selftest=1 ajaa testit ja kaikki menevät läpi.
4. Ladattu tickets-venue-1.csv on tavu tavulta yhteensopiva nykyisen
   data/raw/tickets/venue_1/tickets.csv -tiedoston formaatin kanssa: sama otsikkorivi,
   sama päivämäärämuoto, sama erotin.
5. Kierrätystesti: nykyinen data/raw/tickets/venue_1/tickets.csv syötetään työkaluun,
   kartoitetaan ja viedään, ja tulos on identtinen alkuperäisen kanssa.
6. Yhdistämistila: uuden viikon rivit lisätään olemassa olevaan tiedostoon ilman että
   vanhat muuttuvat, ja erotusnäkymä kertoo tarkalleen mikä muuttui.
7. Työkalu toimii yksityisessä selainikkunassa, jossa localStorage heittää poikkeuksen.
8. Tiedoston koko alle 250 kB.

# Älä tee näitä

- Älä lisää ulkoisia riippuvuuksia tai CDN-linkkejä
- Älä lähetä dataa mihinkään, älä myöskään virheraportointiin
- Älä oleta lähdetiedoston sarakkeita, kaikki kartoitetaan käyttöliittymässä
- Älä kirjoita suoraan tiedostojärjestelmään, selain ei voi eikä saa
- Älä hiljaisesti pudota rivejä, jokainen ohitettu rivi näkyy varoituksissa syineen
- Älä pyöristä lippumääriä liukuluvuiksi, ne ovat kokonaislukuja
- Älä tee tästä osaa Astro-sovellusta, se on itsenäinen tiedosto
````

---

## Yhteenveto: mitä kukin osio tuottaa

| Osio | Teknologia | Syöte | Tuotos | Ajo |
| --- | --- | --- | --- | --- |
| 1. ingest | Python 3.12, pandas, requests | 3 ulkoista rajapintaa + tickets.csv | `data/processed/*.csv` + manifest | Päivittäin, GitHub Actions |
| 3. forecast | Python 3.12, scikit-learn (+ Prophet valinnaisena) | `data/processed/` | `data/forecasts/latest/` | Päivittäin, ingestin jälkeen |
| 2. web | Astro 5, TypeScript, Observable Plot | `data/processed/` + `data/forecasts/` | Staattinen sivusto | Build pushissa, Cloudflare Pages |
| 4. lipputyökalu | Yksi HTML-tiedosto, vanilla JS | Lipunmyynnin CSV-vienti | `data/raw/tickets/venue_{id}/tickets.csv` | Käsin, viikoittain |
