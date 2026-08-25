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

Lähdetiedostojen rakenne on selvitetty, sarakekartoitus todennettu ja muunnos ajettu
kertaalleen käsin. Repon lipputiedostot ovat siis jo ajan tasalla, ja ne toimivat
työkalun regressiotestinä: työkalun on tuotettava täsmälleen samat tiedostot.

Repossa valmiina:

| Tiedosto | Sisältö |
| --- | --- |
| `tools/fixtures/kavijatilastot-pekuri.csv` | Aukiolotiimin vienti, venue 1 |
| `tools/fixtures/kavijatilastot-kaupungintalo.csv` | Aukiolotiimin vienti, venue 2 |
| `tools/fixtures/expected-tickets_daily.csv` | Odotettu tulos normalisoidussa muodossa |
| `tools/MUUNNOSRAPORTTI.md` | Käsin ajetun muunnoksen tulokset ja poikkeamat |
| `data/raw/tickets/venue_1/tickets.csv` | Muunnoksen tulos, 222 riviä |
| `data/raw/tickets/venue_2/tickets.csv` | Muunnoksen tulos, 222 riviä |

````text
Rakennat Oulu2026 Visitor Flow Frameworkiin apuvälineen: selainpohjaisen työkalun, jolla
aukiolotiimin ylläpitämä kävijätilasto-CSV muunnetaan venuekohtaisiksi lippumääriksi.

# Lue ensin

- docs/FRAMEWORK_PLAN.md luku 4.2, kohta tickets_daily.csv
- config/venues.json: venuet ja niiden tickets_path
- packages/ingest/src/ovf_ingest/normalize.py: miten lippudata luetaan ja normalisoidaan
- tools/MUUNNOSRAPORTTI.md: käsin ajetun muunnoksen tulokset, poikkeamat ja päätökset.
  Lue tämä huolella, se on tämän työkalun tosiasiallinen määrittely.

Tiedostot joita vasten työkalu kehitetään ja testataan:

- tools/fixtures/kavijatilastot-pekuri.csv          lähde, venue 1
- tools/fixtures/kavijatilastot-kaupungintalo.csv   lähde, venue 2
- data/raw/tickets/venue_1/tickets.csv              odotettu tulos, 222 riviä
- data/raw/tickets/venue_2/tickets.csv              odotettu tulos, 222 riviä
- tools/fixtures/expected-tickets_daily.csv         odotettu tulos normalisoituna, 444 riviä

# Tehtävä

Toteuta yksi itsenäinen tiedosto: tools/tickets-parser.html

Käyttäjä avaa sen selaimessa suoraan tiedostojärjestelmästä (file://), pudottaa siihen
aukiolotiimin CSV-viennin, tarkistaa tunnistetun kartoituksen, katsoo varoitukset ja
lataa venuekohtaisen tickets.csv-tiedoston. Käyttö on viikoittainen, noin viisi minuuttia.

# Ehdottomat tekniset rajoitteet

1. YKSI tiedosto. Kaikki HTML, CSS ja JavaScript samassa tiedostossa.
2. NOLLA ulkoista pyyntöä. Ei CDN:ää, ei fontteja verkosta, ei analytiikkaa. Työkalun on
   toimittava täysin offline. Kirjoita CSV-parseri itse, älä käytä kirjastoa.
3. Ei build-vaihetta. Ei npm:ää, ei bundleria. Vanilla JS, moderni syntaksi on ok.
4. Kaikki käsittely selaimessa. Mitään ei lähetetä mihinkään. Kerro tämä käyttäjälle
   näkyvästi käyttöliittymässä.
5. Toimii Chromen, Safarin ja Firefoxin nykyversioilla.

# Lähdetiedostojen todellinen rakenne

Aukiolotiimi ylläpitää Exceliä ja vie sen CSV:ksi. Tiedostoja on kaksi, yksi per venue,
ja niillä on ERI sarakerakenne. Molemmissa:

- Merkistö windows-1252 (cp1252), EI UTF-8. Ääkköset hajoavat jos tämän ohittaa.
- Erotin puolipiste.
- Rivi 1 on otsikkorivi. Sarake 0 on viikonpäivän nimi suomeksi, sarake 1 päivämäärä.
- Päivämäärä muodossa d.m.yyyy ilman etunollia.
- Tiedosto EI sisällä venue-saraketta. Koko tiedosto kuuluu yhdelle venuelle.

## Profiili A: PEKURI, venue 1

Otsikkorivi:
  ;Päivämäärä;Yleisöä;Ryhmät;Yhteensä;...

| Sarake | Otsikko | Käyttö |
| 1 | Päivämäärä | päivämäärä |
| 2 | Yleisöä | TICKETS |
| 3 | Ryhmät | GROUPS |
| 4 | Yhteensä | vain ristiintarkistus |
| 5+ | (nimetön) | muistiinpanoja ja irrallisia viikkosummia, ohitetaan |

## Profiili B: KAUPUNGINTALO, venue 2

Otsikkorivi:
  ;Päivämäärä;Varaus;Verkkokauppa tilastot;Ovelta;Ktalon puh tilasto;Ryhmät ;KUTOSET;Ktalon vieraat;Yhteensä;Lisätietoa;...

| Sarake | Otsikko | Käyttö |
| 1 | Päivämäärä | päivämäärä |
| 2 | Varaus | TICKETS, summattava |
| 3 | Verkkokauppa tilastot | TICKETS, summattava |
| 4 | Ovelta | TICKETS, summattava |
| 5 | Ktalon puh tilasto | TICKETS, summattava |
| 6 | Ryhmät  (huom. perässä välilyönti) | GROUPS, summattava |
| 7 | KUTOSET | GROUPS, summattava |
| 8 | Ktalon vieraat | GROUPS, summattava |
| 9 | Yhteensä | vain ristiintarkistus |
| 10 | Lisätietoa | muistiinpanoja, ohitetaan |
| 11+ | (nimetön) | roskaa: #ARVO!, juoksevia summia, sarjanumeroita, ohitetaan |

Eli TICKETS ja GROUPS ovat USEAN sarakkeen summia. Tämä on kartoituksen tärkein
ominaisuus, ei erikoistapaus.

## Kartoitus on todennettu ja muunnos ajettu

Kartoitus varmistettiin vertaamalla laskettuja arvoja siihen tickets.csv-tiedostoon,
joka repossa oli ENNEN muunnosta:
- venue 1: kaikki 124 päällekkäistä päivää täsmäsivät täydellisesti
- venue 2: ryhmäluvut täsmäsivät kaikilla 125 päivällä, yksittäisliput 50 päivällä

Venue 2:n yksittäislippujen erot eivät olleet kartoitusvirhe. Kaikki mahdolliset
sarakeyhdistelmät kokeiltiin tyhjentävästi, eikä mikään muu tuottanut parempaa osumaa.
Erot johtuivat siitä että aukiolotiimi oli korjannut Excelin lukuja vanhan tiedoston
tekemisen jälkeen. Muutokset menivät molempiin suuntiin ja koko jakson summa muuttui
vain 6 kävijää.

Muunnos on sen jälkeen ajettu, ja repon tickets.csv-tiedostot ovat nyt muunnoksen tulos:
molemmilla venueilla 222 riviä, Pekuri 14.1. - 23.8.2026 ja Kaupungintalo
13.1. - 23.8.2026 (25.7.2026 puuttuu, katso tools/MUUNNOSRAPORTTI.md).

TÄSTÄ SEURAA: työkalun on tuotettava näistä lähdetiedostoista täsmälleen nykyiset
repon tiedostot, rivi riviltä. Jos tulos eroaa, vika on työkalussa.

# Roskarivit ja poikkeamat joita lähdedatassa oikeasti on

Työkalun on käsiteltävä kaikki nämä. Ne on löydetty aidosta datasta, eivät keksittyjä.

Ohitettavat rivit:
- Kuukausiotsikot: päivämääräsarakkeessa lukee Helmikuu tai Maaliskuu
- Välisummarivit: päivämääräsarakkeessa lukee Yhteensä
- Tyhjät rivit ja rivit joissa päivämääräsarake on tyhjä
- Loppupään tyhjät päivärivit: venue 2:ssa on päivämääriä 18.9.2026 asti ilman dataa

Tekstiarvot numerosarakkeissa, tulkitaan nollaksi ja merkitään varoitukseksi:
- Suljettu, suljettu (venue 2, rivit 36, 108, 203)
- ei löytynyt? (venue 2, rivi 218)

Yhteensä-sarake on epäluotettava:
- venue 1: tyhjä 18 rivillä, venue 2: tyhjä 55 rivillä
- venue 1 rivi 142, 30.5.2026: Yhteensä 2251, vaikka komponentit ovat 35. Kuukausisumma
  on valunut päivän riville
- venue 2 rivi 163, 15.6.2026: Yhteensä 475, vaikka kaikki komponentit ovat tyhjiä.
  Viikkosumma väärässä sarakkeessa
- venue 1 rivit 79 ja 80, 30.3. ja 31.3.2026: arvot näyttävät vaihtaneen paikkaa
  rivien välillä
- venue 2 rivi 213, 4.8.2026: komponentit 113, Yhteensä 101

TÄSTÄ SEURAA SUUNNITTELUSÄÄNTÖ: TOTAL lasketaan aina TICKETS + GROUPS. Lähteen
Yhteensä-saraketta käytetään VAIN ristiintarkistukseen, joka tuottaa varoituksen jos
se eroaa. Sitä ei koskaan kirjoiteta suoraan tulokseen.

Päivämääräongelmat:
- venue 2 rivi 203: 25.6.2026 sijaitsee rivien 24.7.2026 ja 26.7.2026 välissä. Kyseessä
  on ilmeinen kirjoitusvirhe, oikea päivä on 25.7.2026. Työkalu ei saa korjata tätä
  automaattisesti, vaan sen on havaittava epäjärjestys ja pyydettävä käyttäjää
  päättämään: korjaa ehdotettuun päivään, pidä sellaisenaan, tai ohita rivi.

Tulevat päivät:
- venue 2 rivi 245: 5.9.2026, Ryhmät 200. Tämä on ennakkovaraus, ei toteutunut kävijä.
  Oletuksena kaikki päivät jotka ovat tämän päivän jälkeen jätetään pois, ja ne
  listataan erikseen. Käyttäjä voi ottaa ne mukaan, jos haluaa.

Nollapäivät:
- venue 2:ssa on 59 päivää joilla kaikki komponentit ovat nollia, pääosin maanantaita
  jolloin kohde on kiinni. Nämä kirjoitetaan tulokseen nollina, koska nolla on aito
  havainto. Erottele käyttöliittymässä "kiinni" ja "auki mutta ei kävijöitä" silloin
  kun lähteessä on Suljettu-merkintä.

# Käyttöliittymän kulku

Vaihe 1: tiedoston valinta
  Pudotusalue ja tiedostonvalitsin, myös liitä leikepöydältä.
  Automaattinen tunnistus: merkistö (kokeile UTF-8 TextDecoderilla fatal:true, varalla
  windows-1252, poista BOM), erotin (puolipiste, pilkku, sarkain, pystyviiva),
  otsikkorivi.
  Tunnista profiili otsikkorivin allekirjoituksesta: jos otsikoista löytyy Yleisöä,
  valitse profiili A ja venue 1. Jos löytyy Verkkokauppa tilastot tai KUTOSET, valitse
  profiili B ja venue 2. Näytä tunnistuksen tulos ja anna käyttäjän vaihtaa se.
  Useamman tiedoston voi käsitellä peräkkäin samassa istunnossa, ja tulokset
  kertyvät venueittain.

Vaihe 2: esikatselu
  Taulukko, ensimmäiset 20 riviä, sarakkeiden nimet ja indeksit. Rivimäärä ja havaitut
  ongelmat.

Vaihe 3: kartoitus
  Esitäytettynä tunnistetusta profiilista, mutta kaikki muokattavissa:
  - päivämääräsarake ja formaatti (d.m.yyyy, dd.mm.yyyy, yyyy-mm-dd, ISO-aikaleima,
    Excelin sarjanumero)
  - TICKETS: monivalinta sarakkeista, arvot summataan
  - GROUPS: monivalinta sarakkeista, arvot summataan
  - ristiintarkistussarake, valinnainen
  - venue, johon koko tiedosto kohdistetaan
  Sarakkeet tunnistetaan ensisijaisesti indeksin perusteella ja otsikon nimi on
  varmistus. Otsikoiden vertailussa poista alku- ja loppuvälilyönnit ja ohita
  kirjainkoko, koska lähteessä on esimerkiksi "Ryhmät " perässä välilyönnillä.
  Lukuarvoissa tuettava pilkkudesimaali ja tuhaterotin (välilyönti tai sitkeä välilyönti).
  Kartoitus tallennetaan nimettynä profiilina localStorageen. Kaksi profiilia on
  esiasennettuna: Pekuri ja Kaupungintalo. Jos localStorage ei ole käytettävissä
  (yksityinen ikkuna), työkalun on toimittava normaalisti ilman tallennusta: kääri
  jokainen luku ja kirjoitus try/catchiin.

Vaihe 4: tulos ja tarkistukset
  Aggregointi: ryhmittele päivän mukaan, summaa TICKETS ja GROUPS, laske
  TOTAL = TICKETS + GROUPS.
  Näytä taulukko, yhteenveto ja pieni inline-SVG-pylväskaavio päivittäisistä määristä.
  Yhteenvetoon: luettuja rivejä, hyväksyttyjä, ohitettuja ryhmiteltynä syyn mukaan,
  päivämääräväli, päivien lukumäärä, kokonaismäärät.
  Varoitukset omina riveinään, klikattavissa niin että lähderivi korostuu
  esikatselussa, ja jokainen kertoo rivinumeron lähdetiedostossa:
  - päivämäärä ei jäsentynyt
  - päivämäärä epäjärjestyksessä, ehdota korjausta
  - sama päivä esiintyy useasti
  - tekstiarvo numerosarakkeessa, näytä alkuperäinen teksti
  - ristiintarkistus ei täsmää, näytä molemmat luvut ja erotus
  - negatiivinen arvo
  - päivä tulevaisuudessa
  - epäuskottavan suuri arvo: yli 5-kertainen viimeisen 28 päivän mediaaniin nähden
  - venuelle ei tullut yhtään riviä

Vaihe 5: yhdistäminen olemassa olevaan
  Kaksi tilaa, yhdistäminen oletuksena:
  - Korvaa: vain juuri jäsennetty data
  - Yhdistä: käyttäjä lataa tai liittää nykyisen tickets.csv:n, työkalu yhdistää,
    poistaa duplikaatit päivän perusteella (uusi voittaa) ja järjestää päivämäärän
    mukaan. Näytä erotus: lisätyt päivät, muuttuneet päivät vanhoine ja uusine
    arvoineen, ja poistuneet päivät.
  Odotettu tulos tällä aineistolla: nolla lisättyä ja nolla muuttunutta päivää, koska
  repon tiedostot on jo muunnettu näistä samoista lähteistä. Tyhjä erotus on siis
  onnistumisen merkki, ei virhe. Kun aukiolotiimi toimittaa seuraavan viennin, erotus
  näyttää uudet ja korjatut päivät.

Vaihe 6: vienti
  - Lataa venuekohtainen tickets.csv. Formaatti täsmälleen: otsikkorivi
    DATE,TICKETS,GROUPS,TOTAL, erotin pilkku, päivämäärä muodossa d.m.yyyy ILMAN
    etunollia (14.1.2026, ei 14.01.2026), rivinvaihto \n, merkistö UTF-8 ilman BOMia,
    kokonaisluvut ilman desimaaleja.
    Tiedostonimi tickets-venue-{id}.csv, ja näytä kohdepolku
    data/raw/tickets/venue_{id}/tickets.csv
  - Lataa yhdistetty tickets_daily.csv normalisoidussa muodossa
    venue_id,date,tickets_sold,groups_sold,tickets_total, päivämäärä ISO-muodossa.
    Tämä on tarkistusta varten, ingest tuottaa saman tiedoston itse.
  - Kopioi leikepöydälle -painike kummallekin.
  - Näytä seuraavat askeleet: mihin tiedostot kopioidaan ja että sen jälkeen ajetaan
    python -m ovf_ingest run

# Sanasto ja rehellisyys

Lähdetiedostot ovat nimeltään Kävijätilastot ja niiden sarakkeet ovat kanavia
(varaus, verkkokauppa, ovelta, puhelin, ryhmät, talon vieraat). Kyse ei siis ole
puhtaasta lipunmyynnistä vaan kävijämääristä kanavittain. Frameworkin kentät
tickets_sold ja groups_sold tarkoittavat käytännössä yksittäiskävijöitä ja
ryhmäkävijöitä. Kirjoita tämä näkyviin sekä käyttöliittymään että tools/README.md:hen,
jotta lukuja ei tulkita myyntiraportiksi.

# Käyttöliittymän vaatimukset

- Kieli suomi
- Vaiheet näkyvät edistymisen osoittimena, edelliseen voi palata ilman että työ katoaa
- Tumma ja vaalea teema prefers-color-scheme mukaan
- Toimii 375 px leveydellä, ensisijainen käyttö työpöydällä
- Näppäimistönavigaatio kaikissa valitsimissa, näkyvä fokus
- Kontrastit vähintään WCAG AA
- Varoitukset eivät erotu pelkällä värillä, myös ikoni tai teksti
- Vältä pitkää ajatusviivaa leipätekstissä, käytä pistettä, pilkkua tai kaksoispistettä

# CSV-parserin vaatimukset

RFC 4180 -yhteensopiva: lainausmerkeissä olevat kentät joissa voi olla erotin,
rivinvaihto tai kaksinkertaistettu lainausmerkki. CRLF ja LF. Tyhjät rivit ohitetaan.
Vaihteleva sarakemäärä ei kaada parsintaa vaan kirjataan varoitukseksi. Riveillä on
usein vähemmän sarakkeita kuin otsikkorivillä, joten täydennä puuttuvat tyhjillä.
50 000 rivin tiedoston on jäsennyttävä alle sekunnissa.

# Itsetestaus

Koska build-vaihetta ei ole, sisällytä testit samaan tiedostoon. URL-parametrilla
?selftest=1 työkalu ajaa testit ja näyttää tulokset taulukkona. Testattavaa vähintään:
- CSV-parsinta: lainausmerkit, upotettu erotin, upotettu rivinvaihto, CRLF, BOM,
  vajaat rivit
- cp1252-dekoodaus: merkkijono jossa on ä, ö ja å dekoodautuu oikein
- erottimen ja profiilin tunnistus molemmilla aidoilla otsikkoriveillä
- päivämäärän jäsennys jokaisella tuetulla formaatilla ja virheellisillä syötteillä
- monen sarakkeen summaus TICKETS- ja GROUPS-kenttiin
- roskarivien tunnistus: Helmikuu, Maaliskuu, Yhteensä, tyhjä
- tekstiarvo numerosarakkeessa tulkitaan nollaksi ja tuottaa varoituksen
- ristiintarkistuksen poikkeama havaitaan
- epäjärjestyksessä oleva päivämäärä havaitaan
- yhdistäminen: duplikaattipäivä, uusi voittaa
- vientiformaatti: etunollattomuus, otsikkorivi, rivinvaihdot

# Regressiotestit aitoa dataa vasten

Nämä on ajettava käsin ja kirjattava tools/README.md:hen. Ne ovat tämän työkalun
tärkein hyväksymiskriteeri, koska odotettu tulos on tiedossa tarkalleen.

1. tools/fixtures/kavijatilastot-pekuri.csv profiililla A:
   tuloksen on oltava rivi riviltä identtinen tiedoston
   data/raw/tickets/venue_1/tickets.csv kanssa. 222 riviä, 14.1. - 23.8.2026,
   yksittäisliput yhteensä 13 957, ryhmät 3 631, kaikki yhteensä 17 588.
2. tools/fixtures/kavijatilastot-kaupungintalo.csv profiililla B:
   tuloksen on oltava rivi riviltä identtinen tiedoston
   data/raw/tickets/venue_2/tickets.csv kanssa. 222 riviä, 13.1. - 23.8.2026,
   yksittäisliput yhteensä 11 775, ryhmät 5 281, kaikki yhteensä 17 056.
   Huomaa että 25.7.2026 EI ole tuloksessa, koska lähteen rivillä 203 on
   kirjoitusvirhe. Tämä on tarkoituksellista, älä korjaa sitä.
3. Molemmat yhdessä normalisoituna: tuloksen on vastattava tiedostoa
   tools/fixtures/expected-tickets_daily.csv, 444 riviä.
4. Yhdistämistila samoilla tiedostoilla: erotuksen on oltava tyhjä.
5. Kaikki luvussa "Roskarivit ja poikkeamat" luetellut tapaukset näkyvät varoituksina.
   Odotettu varoitusmäärä: venue 1 kolme varoitusta ja viisi ohitettua riviä,
   venue 2 kahdeksan varoitusta ja kahdeksan ohitettua riviä.

Vertailun voi tehdä komennolla diff, koska tiedostojen pitää olla tavu tavulta samat.

# Dokumentaatio

Kirjoita tools/README.md: mihin ongelmaan työkalu vastaa, käyttöohje vaiheittain,
molempien profiilien sarakekartoitus taulukkona, tunnetut lähdedatan ongelmat, miten
tulos viedään repoon, mitä sen jälkeen ajetaan, ja miten itsetestit ajetaan. Lisää
maininta työkalusta repon juuren README.md:hen.

# Hyväksymiskriteerit

1. tools/tickets-parser.html avautuu file:// -osoitteesta ja toimii ilman verkkoa.
   Selaimen verkkovälilehdellä ulkoisia pyyntöjä nolla.
2. Molemmat aidot tiedostot tools/fixtures/-hakemistosta jäsentyvät oikein, ääkköset
   näkyvät oikein, ja profiili tunnistuu automaattisesti.
3. ?selftest=1 ajaa testit ja kaikki menevät läpi.
4. Kaikki viisi regressiotestiä menevät läpi. Erityisesti: ladattu tickets-venue-1.csv
   on tavu tavulta identtinen tiedoston data/raw/tickets/venue_1/tickets.csv kanssa,
   ja sama pätee venue 2:lle.
5. Yhdistämistila näyttää erotuksen tarkasti eikä hukkaa vanhoja päiviä.
6. Työkalu toimii yksityisessä selainikkunassa, jossa localStorage heittää poikkeuksen.
7. Tiedoston koko alle 250 kB.

# Älä tee näitä

- Älä lisää ulkoisia riippuvuuksia tai CDN-linkkejä
- Älä lähetä dataa mihinkään, älä myöskään virheraportointiin
- Älä kirjoita lähteen Yhteensä-saraketta suoraan tulokseen, se on epäluotettava
- Älä korjaa epäjärjestyksessä olevia päivämääriä automaattisesti, kysy käyttäjältä
- Älä hiljaisesti pudota rivejä, jokainen ohitettu rivi näkyy varoituksissa syineen
- Älä oleta UTF-8-merkistöä, lähde on windows-1252
- Älä lisää 25.7.2026 venue 2:n tulokseen, sen puuttuminen on tietoinen päätös
- Älä muuta repon tickets.csv-tiedostoja, ne ovat regressiotestin odotettu tulos
- Älä pyöristä lippumääriä liukuluvuiksi, ne ovat kokonaislukuja
- Älä tee tästä osaa Astro-sovellusta, se on itsenäinen tiedosto
````

## Yhteenveto: mitä kukin osio tuottaa

| Osio | Teknologia | Syöte | Tuotos | Ajo |
| --- | --- | --- | --- | --- |
| 1. ingest | Python 3.12, pandas, requests | 3 ulkoista rajapintaa + tickets.csv | `data/processed/*.csv` + manifest | Päivittäin, GitHub Actions |
| 3. forecast | Python 3.12, scikit-learn (+ Prophet valinnaisena) | `data/processed/` | `data/forecasts/latest/` | Päivittäin, ingestin jälkeen |
| 2. web | Astro 5, TypeScript, Observable Plot | `data/processed/` + `data/forecasts/` | Staattinen sivusto | Build pushissa, Cloudflare Pages |
| 4. lipputyökalu | Yksi HTML-tiedosto, vanilla JS | Aukiolotiimin kävijätilasto-CSV (cp1252, puolipiste) | `data/raw/tickets/venue_{id}/tickets.csv` | Käsin, viikoittain |
