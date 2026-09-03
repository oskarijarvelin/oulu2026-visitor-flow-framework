# Oulu2026 Visitor Flow Framework: tekninen suunnitelma

*In English: [`FRAMEWORK_PLAN.en.md`](FRAMEWORK_PLAN.en.md).*

Uusi kolmiosainen sovellus, joka korvaa nykyisen `oulu2026-visitor-flow-prediction-tool`
-repon toiminnallisuuden selkeämmällä vastuunjaolla, kevyemmillä riippuvuuksilla ja
julkaistavalla web-käyttöliittymällä.

Pohjana: `docs/DATA_MODEL.md` (rajapinnat ja datan skeemat) sekä nykyisen repon koodi
(`visitor_forecast/`, `app/`).

Päätökset jotka ohjaavat tätä suunnitelmaa:

- **Uusi monorepo** `oulu2026-visitor-flow-framework`. Nykyinen repo jää koskemattomaksi referenssiksi.
- **Astro, staattinen julkaisu** Cloudflare Pagesiin. Ei palvelinta, ei ajonaikaisia kustannuksia.
- **Kaksi ennustemallia rinnakkain**: kevyt tilastollinen perusmalli tuotantoon ja Prophet + XGBoost vertailukohdaksi, molemmat samassa tulosformaatissa.

---

## 1. Tavoitteet ja rajaukset

### Tavoitteet

1. Osiot ovat riippumattomia. Kukin voidaan ajaa, testata ja korvata erikseen.
2. Osioiden välinen rajapinta on tiedostosopimus, ei jaettu Python-koodi.
3. Datan haku ja ennusteiden luonti ovat ajastettavissa ilman ihmistä.
4. Web-osio on staattinen ja jaettavissa linkkinä tuotannon päätöksentekoon.
5. Ennusteen epävarmuus on rehellisesti näkyvissä, ei piilotettu yhteen lukuun.

### Rajaukset

- Ei tietokantaa. Kaikki data on versionhallinnassa olevia tiedostoja.
- Ei käyttäjien kirjautumista eikä kirjoitusoperaatioita selaimesta.
- Ei reaaliaikaisuutta. Päivitystahti on yksi ajo vuorokaudessa.
- Lipunmyyntidata pysyy manuaalisesti ylläpidettynä CSV-tiedostona.
- TPM-liikennedata jätetään pois ensimmäisestä versiosta, koska sitä ei ole kertynyt levylle.

---

## 2. Arkkitehtuuri

```
                    ULKOISET RAJAPINNAT
   Jaskaretail IoT   Open-Meteo   Oulun liikenne Eco-Counter
          |               |               |
          +---------------+---------------+
                          |
                 [ OSIO 1: ingest, Python ]
                 hae, normalisoi, validoi
                          |
                          v
              data/raw/ + data/processed/
              kanoninen aikasarja-aineisto
                          |
              +-----------+-----------+
              |                       |
   [ OSIO 3: forecast, Python ]       |
   perusmalli + Prophet/XGB           |
              |                       |
              v                       |
       data/forecasts/                |
       7 vrk tunti, 30 vrk päivä      |
              |                       |
              +-----------+-----------+
                          |
                 [ OSIO 2: web, Astro ]
                 build-aikainen JSON-paketointi
                          |
                          v
                 Cloudflare Pages, staattinen
```

Suoritusjärjestys päivittäisessä ajossa: **1 → 3 → 2**.
Kehitysjärjestys: **1 → 3 → 2**, mutta osio 2 voidaan aloittaa rinnakkain fixture-datalla.

---

## 3. Repo-rakenne

```
oulu2026-visitor-flow-framework/
├── README.md
├── Makefile                     # make ingest / forecast / web / all
├── pyproject.toml               # yhteinen Python-projekti, workspace-tyylinen
├── config/
│   ├── venues.json              # venue-määritykset (korvaa settings.json:in venues-osan)
│   ├── sources.json             # rajapintojen osoitteet, cachehakemistot, oletusikkunat
│   ├── sites.json               # Eco-Counter-sivustot ja sensorikartat
│   └── holidays.csv             # ylläpidetty pyhäkalenteri
├── packages/
│   ├── ingest/                  # OSIO 1
│   │   ├── src/ovf_ingest/
│   │   │   ├── __init__.py
│   │   │   ├── cli.py           # python -m ovf_ingest
│   │   │   ├── config.py        # pydantic-mallit config/-tiedostoille
│   │   │   ├── clients/
│   │   │   │   ├── jaskaretail.py
│   │   │   │   ├── openmeteo.py
│   │   │   │   └── ecocounter.py
│   │   │   ├── normalize.py     # aikavyöhykkeet, sarakenimet, tyypit
│   │   │   ├── store.py         # raw- ja processed-tiedostojen kirjoitus
│   │   │   ├── validate.py      # laatuportit ja manifestin rakennus
│   │   │   └── climatology.py   # sään pitkän aikavälin normaalit
│   │   └── tests/
│   ├── forecast/                # OSIO 3
│   │   ├── src/ovf_forecast/
│   │   │   ├── cli.py           # python -m ovf_forecast
│   │   │   ├── dataset.py       # processed -> mallinnusmatriisi
│   │   │   ├── features.py
│   │   │   ├── models/
│   │   │   │   ├── base.py      # yhteinen rajapinta: fit / predict / name
│   │   │   │   ├── baseline.py  # perusmalli
│   │   │   │   └── prophet_xgb.py
│   │   │   ├── profile.py       # tuntiprofiilin johtaminen
│   │   │   ├── backtest.py      # rolling origin -validointi
│   │   │   ├── intervals.py     # empiiriset ennustevälit
│   │   │   └── export.py        # forecast-artefaktien kirjoitus
│   │   └── tests/
│   └── web/                     # OSIO 2
│       ├── astro.config.mjs
│       ├── package.json
│       ├── scripts/build-data.ts   # data/ -> src/data/*.json
│       ├── src/
│       │   ├── pages/
│       │   ├── components/
│       │   ├── lib/
│       │   └── data/            # generoitu, gitignore
│       └── public/
├── data/                        # jaettu, versionhallinnassa
│   ├── raw/
│   ├── processed/
│   ├── reference/
│   └── forecasts/
├── .github/workflows/
│   ├── daily.yml                # ingest + forecast + commit + deploy
│   ├── ci.yml                   # testit ja lint
│   └── deploy.yml               # pelkkä web-julkaisu
└── docs/
    ├── DATA_MODEL.md            # kopioidaan tästä reposta
    ├── FRAMEWORK_PLAN.md        # tämä dokumentti
    └── FORECAST_MODEL.md        # mallidokumentaatio, luku 8 omana tiedostonaan
```

Python-osiot jakavat yhden `pyproject.toml`-tiedoston kahdella valinnaisella
riippuvuusryhmällä: `ingest` ja `forecast`. Prophet on erillisessä `prophet`-ryhmässä,
jotta perusmalli asentuu ilman cmdstania.

---

## 4. Datasopimukset

Osioiden ainoa yhteys on tiedostosopimus. Jos sopimus pysyy, mikä tahansa osio voidaan
kirjoittaa uusiksi.

### 4.1 Aikavyöhykesopimus

Nykyisen sovelluksen vakavin datavirhe on aikavyöhykkeiden sekoittuminen
(`DATA_MODEL.md` luku 7.1). Uusi sopimus:

- **Jokainen aikaleimallinen rivi sisältää kaksi saraketta**: `ts_utc` (ISO 8601, `Z`) ja
  `ts_local` (ISO 8601 Helsingin offsetilla, esim. `2026-05-22T07:00:00+03:00`).
- `ts_utc` on kaikkien liitosten avain.
- `ts_local` on ainoa asia jonka käyttöliittymä näyttää.
- Päivätason rivit käyttävät `date`-saraketta, joka on **paikallinen kalenteripäivä**.
- Kesäaikasiirtymän päivinä tuntisarjassa on 23 tai 25 riviä. Tämä on oikein, ei bugi.

### 4.2 Osio 1: tuotokset

Raakacache, muuttumaton kopio rajapinnan vastauksesta, yksi tiedosto per lähde ja päivä:

```
data/raw/visitors/venue_{id}/{YYYY-MM-DD}.json
data/raw/weather/venue_{id}/{YYYY-MM-DD}.json
data/raw/traffic/{site_id}/{YYYY-MM-DD}.json
```

Prosessoitu, kanoninen aineisto:

| Tiedosto | Avain | Sarakkeet |
| --- | --- | --- |
| `data/processed/visitors_hourly.csv` | `venue_id, ts_utc` | `venue_id, ts_utc, ts_local, visitors_in, visitors_out, visitors_total, is_imputed` |
| `data/processed/visitors_daily.csv` | `venue_id, date` | `venue_id, date, visitors_in, visitors_out, visitors_total, observed_hours, is_complete` |
| `data/processed/weather_hourly.csv` | `venue_id, ts_utc` | `venue_id, ts_utc, ts_local, temperature_2m, precipitation, wind_speed_10m, relative_humidity_2m, weathercode, weathercode_str, is_precipitation, is_cold, is_windy, source` |
| `data/processed/weather_daily.csv` | `venue_id, date` | `venue_id, date, temp_mean, temp_min, temp_max, precip_sum, precip_hours, wind_mean, weathercode_mode, weathercode_str, source` |
| `data/processed/traffic_hourly.csv` | `site_id, ts_utc` | `site_id, site_name, ts_utc, ts_local, jk_in, jk_out, pp_in, pp_out` |
| `data/processed/tickets_daily.csv` | `venue_id, date` | `venue_id, date, tickets_sold, groups_sold, tickets_total` |
| `data/processed/calendar_daily.csv` | `date` | `date, holiday_name, is_holiday, is_weekend, day_of_week, days_before_next_holiday, is_last_workday_before_holiday, week_of_year, month, year` |
| `data/processed/manifest.json` | | ajon metatiedot, katso 4.4 |

Keskeiset erot nykyiseen:

- `visitors_total` on **edelleen sisään- ja ulosmenojen summa**, mutta sarake `is_imputed`
  kertoo onko rivi haettu rajapinnasta vai täytetty nollalla. Tämä poistaa
  `DATA_MODEL.md` luvun 7.3 ongelman, jossa aitoa nollaa ja puuttuvaa dataa ei voi erottaa.
- Liikennedata ei ole venuekohtaista vaan sivustokohtaista (`site_id`). Kytkentä venueen
  tehdään vasta esityskerroksessa ja merkitään selvästi kontekstidataksi.
  Tämä poistaa `DATA_MODEL.md` luvun 7.2 harhaanjohtavuuden.
- Sään `source` on `archive`, `forecast` tai `climatology`.

Referenssidata:

```
data/reference/climatology/venue_{id}.csv   # day_of_year, hour, temp_mean, precip_mean, ...
```

### 4.3 Osio 3: tuotokset

```
data/forecasts/latest/manifest.json
data/forecasts/latest/venue_{id}/daily_30d.csv
data/forecasts/latest/venue_{id}/hourly_7d.csv
data/forecasts/latest/venue_{id}/metrics.json
data/forecasts/latest/venue_{id}/backtest.csv
data/forecasts/{YYYY-MM-DD}/...    # arkistokopio samasta rakenteesta
```

`daily_30d.csv`:

| Sarake | Selitys |
| --- | --- |
| `venue_id` | |
| `date` | Paikallinen kalenteripäivä |
| `horizon_days` | 1 - 30, etäisyys ennusteen origosta |
| `model` | `baseline` tai `prophet_xgb` |
| `p10`, `p50`, `p90` | Ennustejakauman kvantiilit, kävijätapahtumia |
| `weather_source` | `forecast` (vrk 1 - 16) tai `climatology` (vrk 17 - 30) |
| `temp_mean`, `precip_sum`, `weathercode_str` | Ennusteen taustalla ollut sää |
| `is_holiday`, `holiday_name` | |
| `generated_at` | Ajon aikaleima UTC |

Tiedostossa on rivit **molemmille malleille**, eli 30 vrk x 2 mallia = 60 riviä per venue.
Web-osio suodattaa `model`-sarakkeella.

`hourly_7d.csv`: sama logiikka, avaimet `venue_id, ts_utc, ts_local, horizon_hours, model`,
arvot `p10, p50, p90`, lisäksi `hour`, sääsarakkeet ja `generated_at`.

`metrics.json`: mallikohtaiset backtest-mittarit horisonttikoreittain, katso luku 8.8.

`backtest.csv`: `model, origin_date, target_date, horizon_days, venue_id, y_true, y_pred, p10, p90`.
Tämä mahdollistaa mallin laadun visualisoinnin web-osiossa ilman uudelleenlaskentaa.

### 4.4 manifest.json

Molemmat Python-osiot kirjoittavat manifestin. Web-osion build kaatuu, jos manifesti
puuttuu tai on liian vanha.

```json
{
  "generated_at": "2026-08-23T04:20:11Z",
  "pipeline": "ingest",
  "version": "1.0.0",
  "sources": [
    {"name": "jaskaretail", "status": "ok", "rows": 3408, "window": ["2026-08-16", "2026-08-23"]},
    {"name": "open-meteo", "status": "ok", "rows": 4032, "window": ["2026-07-24", "2026-09-08"]},
    {"name": "eco-counter", "status": "degraded", "rows": 0, "error": "HTTP 503"}
  ],
  "coverage": {
    "visitors_hourly": {"first": "2026-01-01T00:00:00Z", "last": "2026-08-22T21:00:00Z", "missing_hours": 12},
    "weather_hourly": {"first": "2026-01-01T00:00:00Z", "last": "2026-09-08T21:00:00Z", "missing_hours": 0}
  },
  "quality_gates": {"passed": true, "warnings": ["eco-counter unavailable"]}
}
```

---

## 5. Osio 1: ingest (Python)

### Tehtävä

Hakea samat datat kuin nykyinen sovellus, normalisoida ne ja kirjoittaa luvun 4.2
sopimuksen mukaisiksi tiedostoiksi. Ei mallinnusta, ei visualisointia.

### Lähteet ja parametrit

Rajapintakutsut ovat identtiset nykyisen sovelluksen kanssa. Yksityiskohdat: `DATA_MODEL.md` luku 2.

| Lähde | Kutsu | Huomiot |
| --- | --- | --- |
| Jaskaretail IoT | `POST /ext/sensor/visitor` erikseen `countingTypeId=in` ja `out` | Basic auth ympäristömuuttujista, ei koskaan repoon |
| Open-Meteo archive | `GET /v1/archive` | Historia, `timezone=Europe/Helsinki` |
| Open-Meteo forecast | `GET /v1/forecast`, `forecast_days` enintään 16 | Cache vanhenee tunnissa |
| Eco-Counter | `POST /proxy/graphql`, `ecoCounterSiteData` per sensori | Vastaus UTC:ssä, neljä sensoria per sivusto |

### Toimintaperiaate

1. **Inkrementaalinen ikkuna.** Oletus `--days-back 7`. Täysi uudelleenhaku `--start 2026-01-01`.
2. **Raakavastaus talteen ensin**, vasta sitten normalisointi. Jos normalisointi kaatuu,
   dataa ei ole menetetty.
3. **Idempotenssi.** Saman päivän uudelleenajo tuottaa saman lopputuloksen. Päivätiedostot
   ylikirjoitetaan, kanoniset taulut rakennetaan aina uudelleen päivätiedostoista.
4. **Osittainen epäonnistuminen ei kaada ajoa.** Jos Eco-Counter on alhaalla, kävijä- ja
   säädata haetaan silti ja manifestiin merkitään `degraded`.
5. **Laatuportit** ennen kanonisten tiedostojen kirjoitusta:
   - kävijäsarjassa ei saa olla yli 48 tunnin aukkoa viimeisen 30 vrk sisällä
   - säädatan kattavuus vähintään 99 % ennustejaksolla
   - negatiiviset laskurit hylätään ja lokitetaan
   - päivän kokonaismäärä ei saa ylittää `capacity * 24 * 4` (ilmiselvä sensorivika)
   - portin pettäessä uusi tiedosto kirjoitetaan `.rejected`-päätteellä ja vanha jää voimaan

### Sään klimatologia

Tarvitaan 17 - 30 vuorokauden ennusteille. Ajetaan erikseen, kerran, komennolla
`python -m ovf_ingest climatology --years 2016-2025`. Hakee Open-Meteo archivesta kunkin
venuen koordinaateille 10 vuoden tuntidatan ja tallentaa keskiarvot muodossa
`(day_of_year, hour) -> temp_mean, precip_mean, wind_mean`. Karkaus­päivät käsitellään
liittämällä 29.2. edelliseen päivään.

### CLI

```bash
python -m ovf_ingest run --days-back 7                  # päivittäinen ajo
python -m ovf_ingest run --start 2026-01-01 --end 2026-08-22
python -m ovf_ingest run --source weather --venue 1     # yksi lähde
python -m ovf_ingest climatology --years 2016-2025      # kertaluontoinen
python -m ovf_ingest verify                             # laatuportit ilman hakua
```

Paluuarvo 0 kun kaikki ok, 1 kun laatuportti petti, 2 kun kaikki lähteet epäonnistuivat.

---

## 6. Osio 3: forecast (Python)

### Tehtävä

Tuottaa venuekohtaiset 7 vuorokauden tuntiennusteet ja 30 vuorokauden päiväennusteet
kahdella mallilla, sekä niiden laatumittarit. Ei datan hakua rajapinnoista, lukee vain
`data/processed/`.

### Yleisrakenne

```
processed/  ->  dataset.build()  ->  features.build_daily() ---> model.fit / predict  ---> p50 päivätasolla
                                                             \
                                     profile.build()  ------->  tuntiprofiili  --------> tuntitason p50
                                                             \
                                     backtest.run()  -------->  suhteelliset virheet ---> p10 / p90
```

### Mallien yhteinen rajapinta

```python
class ForecastModel(Protocol):
    name: str                       # "baseline" | "prophet_xgb"
    def fit(self, daily: pd.DataFrame) -> None: ...
    def predict(self, future: pd.DataFrame) -> pd.Series: ...   # p50, päivätaso, kävijätapahtumia
```

Molemmat mallit ennustavat **päivätasolla**. Tuntitaso johdetaan yhteisellä
profiilikomponentilla, jotta mallit ovat vertailukelpoisia ja tuntiennusteen summa on
täsmälleen päiväennuste. Tämä korjaa nykyisen toteutuksen ongelman, jossa `in`, `out` ja
`total` ennustetaan erikseen eivätkä summaudu.

### CLI

```bash
python -m ovf_forecast run                          # molemmat mallit, kaikki venuet
python -m ovf_forecast run --model baseline
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12        # pelkkä validointi
python -m ovf_forecast report                       # tulostaa metrics.json luettavana
```

Mallidokumentaatio kokonaisuudessaan: luku 8.

---

## 7. Osio 2: web (Astro)

### Teknologiavalinnat

| Valinta | Perustelu |
| --- | --- |
| Astro 5, `output: 'static'` | Nolla JS oletuksena, saarekkeet vain kaavioihin. Sopii datalle joka päivittyy kerran vuorokaudessa |
| TypeScript | Datasopimus tyypitetään, build kaatuu jos skeema muuttuu |
| Observable Plot | Deklaratiivinen, SVG, kattaa aikasarjat, hajontakuviot, lämpökartat ja pylväät yhdellä API:lla |
| Tailwind CSS 4 | Nopea, tuttu |
| Cloudflare Pages | Staattinen hosting, automaattinen deploy gitistä |

Vaihtoehtona harkittiin Next.js:ää. Se hylättiin, koska mikään näkymä ei tarvitse
palvelinta: data on valmiiksi laskettu ja päivittyy kerran vuorokaudessa.

### Build-aikainen datan paketointi

`scripts/build-data.ts` ajetaan ennen `astro build`. Se lukee `data/processed/` ja
`data/forecasts/latest/`, laskee valmiit aggregaatit ja kirjoittaa `src/data/`-hakemistoon:

| Tiedosto | Sisältö | Arvioitu koko |
| --- | --- | --- |
| `meta.json` | venuet, päivitysaika, datan kattavuus, laatuvaroitukset | < 5 kB |
| `daily.json` | venuekohtainen päiväsarja: kävijät, sää, liput, pyhät | ~60 kB |
| `hourly.json` | tuntisarja pyöristettynä, vain viimeiset 120 vrk | ~250 kB |
| `profile.json` | viikonpäivä x tunti -matriisi, keskiarvo ja mediaani | ~10 kB |
| `forecast.json` | 7 vrk tunti ja 30 vrk päivä, molemmat mallit | ~40 kB |
| `quality.json` | backtest-mittarit ja aikasarja ennuste vs. toteuma | ~30 kB |

Yhteensä alle 400 kB. Liukuluvut pyöristetään yhteen desimaaliin, aikaleimat lyhennetään.

Buildin laatuportit: jos `manifest.json` on yli 48 tuntia vanha tai ennustetiedostot
puuttuvat, build epäonnistuu selkeällä virheellä sen sijaan että julkaisisi vanhaa dataa.

### Sivut

| Polku | Sisältö |
| --- | --- |
| `/` | Yleiskuva: molemmat venuet rinnakkain, viimeiset 30 vrk, seuraavat 7 vrk, avainluvut ja datan tuoreus |
| `/venue/[id]` | Venuekohtainen syväsukellus: aikasarja tunti- ja päivätasolla, viikonpäivä x tunti -lämpökartta, kapasiteetin käyttöaste, lippuvertailu |
| `/weather` | Sään ja kävijämäärien suhde: hajontakuvio lämpötila vs. kävijät, sateisten ja poutaisten päivien vertailu, säätilaluokittainen jakauma |
| `/forecast` | 7 vrk tunti ja 30 vrk päivä, p10 - p90 vyöhyke, mallien vertailu vierekkäin, sään lähde merkittynä |
| `/quality` | Backtest: ennuste vs. toteuma horisonteittain, MAE ja peittävyys, mallien paremmuus, tunnetut rajoitteet |
| `/about` | Mistä data tulee, mitä luvut tarkoittavat, mitä ne eivät tarkoita |

### Näkymien tarkat vaatimukset

**Aikasarja**: x-akseli paikallista aikaa, y-akseli kävijätapahtumia. Historia yhtenäisenä
viivana, ennuste katkoviivana, p10 - p90 vaaleana alueena. Pyhäpäivät pystyviivoina.
Sadetunnit taustavärinä. Zoom ja rajaus viimeiset 7 / 30 / 90 vrk / kaikki.

**Lämpökartta**: rivit viikonpäivä (ma - su), sarakkeet tunti (0 - 23), arvo keskimääräinen
`visitors_total`. Sekventiaalinen väriskaala, nolla-arvot erotettuna puuttuvista.

**Sääkorrelaatio**: hajontakuvio, x = päivän keskilämpötila, y = päivän kävijät, piste
värjätty säätilaluokan mukaan, koko = sademäärä. Mukaan yksinkertainen lineaarinen sovite
ja selkeä varoitus siitä että korrelaatio ei ole syysuhde.

**Mallien vertailu**: sama akseli, kaksi sarjaa (`baseline`, `prophet_xgb`), legenda
kertoo kummankin backtest-MAE:n. Oletuksena näkyy vain `baseline`.

**Datan laatu -banneri**: jokaisella sivulla ylhäällä, kertoo viimeisen ajon ajan ja
mahdolliset `degraded`-lähteet.

### Saavutettavuus ja esitystapa

- Väriskaalat toimivat myös harmaasävyisenä ja punavihervärisokealle
- Jokaisella kaaviolla on tekstivastine tai taulukkonäkymä
- Luvut esitetään aina yksikön kanssa: "kävijätapahtumaa", ei pelkkä numero
- Selkeä huomautus siitä että `visitors_total` on sisään- ja ulosmenojen summa

---

## 8. Ennustemallit

Tämä luku on suunnitelman ydin. Se irrotetaan omaksi tiedostoksi `docs/FORECAST_MODEL.md`.

### 8.1 Miksi kaksi mallia

Aineistoa on noin 4,5 kuukautta yhdeltä vuodelta. Se ei riitä vuosikausivaihtelun
oppimiseen, mutta riittää viikkorytmin ja sään vaikutuksen oppimiseen. Tässä tilanteessa
monimutkainen malli näyttää tarkemmalta kuin se on. Ratkaisu on ajaa yksinkertainen malli
tuotannossa ja monimutkaisempi rinnalla, ja mitata kumpi oikeasti voittaa.

Jos vertailumalli voittaa perusmallin backtestissä kolmella peräkkäisellä ajolla
selvästi (yli 10 % pienempi MAE), tuotantomalli vaihdetaan. Muuten pidetään yksinkertainen.

### 8.2 Perusmalli: rakenne

Nimi tulosteissa: `baseline`. Kolme kerrosta.

#### Kerros 1: päivätason taso

Kohde: `visitors_total` päivätasolla, venuekohtaisesti.

Malli: `sklearn.ensemble.HistGradientBoostingRegressor(loss="poisson")`.

Poisson-tappio valittiin koska kohde on laskurisuure, jakauma on oikealle vino ja
ennusteen on oltava ei-negatiivinen. Poisson-tappio takaa positiivisuuden ilman
log-muunnoksen aiheuttamaa harhaa takaisinmuunnoksessa.

Piirteet:

| Ryhmä | Piirteet |
| --- | --- |
| Kalenteri | `day_of_week` (kategorinen), `is_weekend`, `is_holiday`, `days_before_next_holiday` (katkaistu 14:ään), `is_last_workday_before_holiday`, `month`, `week_of_year` |
| Vuodenaika | `sin(2πd/365)`, `cos(2πd/365)`, `sin(4πd/365)`, `cos(4πd/365)`, missä d on vuoden päivä |
| Trendi | `days_since_start` |
| Sää | `temp_mean`, `temp_max`, `precip_sum`, `precip_hours`, `wind_mean`, `is_rainy_day`, `weather_group` (clear / cloudy / rain / snow / other) |
| Taso | `level_7d`, `level_28d`, `dow_index_28d` |

`level_7d` ja `level_28d` ovat viimeisten 7 ja 28 **havaitun** päivän keskiarvot
ennusteen origossa. Ne ovat vakioita koko horisontin ajan. `dow_index_28d` on kyseisen
viikonpäivän keskiarvon suhde 28 vrk keskiarvoon.

**Kriittinen suunnitteluvalinta**: mallissa ei ole autoregressiivisiä viiveitä, jotka
päivittyisivät ennusteen edetessä. Nykyinen sovellus syöttää omat ennusteensa takaisin
`lag_24h`- ja `lag_168h`-piirteisiin, jolloin virhe kumuloituu horisontin pidentyessä.
Tässä mallissa kaikki tasoa kuvaavat piirteet lasketaan kerran origossa, joten
30 vuorokauden ennuste ei ole 30 kertaa ketjutettu yhden päivän ennuste.

Lippudataa ei käytetä piirteenä, koska sitä ei ole tulevaisuudelle saatavilla.

#### Kerros 2: tuntiprofiili

Päiväennuste jaetaan tunneille empiirisellä profiililla.

```
share[venue][dow][hour] = keskiarvo osuuksista visitors_hour / visitors_day
                          niiltä päiviltä joilla visitors_day > 0,
                          viimeiset 8 viikkoa
```

Kutistus kohti viikonpäivien yhteistä profiilia, jotta yksittäiset poikkeamat eivät
hallitse:

```
share_final = (n_dow * share_dow + k * share_all) / (n_dow + k),  k = 4
```

Lopuksi normalisointi niin että päivän osuuksien summa on 1. Tuntiennuste on
`daily_p50 * share_final`. Tämä takaa että tuntiennusteiden summa on täsmälleen
päiväennuste.

Aukioloajat johdetaan datasta: tunti katsotaan suljetuksi, jos sen ei-nolla-osuus
viimeisen 8 viikon aikana on alle 5 %. Näiden tuntien osuus pakotetaan nollaan ennen
normalisointia.

#### Kerros 3: epävarmuus

Ennustevälit tulevat **empiirisestä backtestistä**, eivät mallin sisäisistä oletuksista.

1. Aja rolling origin -backtest (luku 8.8).
2. Laske suhteellinen virhe `r = y_true / y_pred` jokaiselle (origo, horisontti) -parille.
3. Laske `r`-jakauman kvantiilit q10 ja q90 horisonttikoreittain: 1 - 7, 8 - 14, 15 - 30.
4. `p10 = p50 * q10(h)`, `p90 = p50 * q90(h)`.

Suhteellinen muotoilu on tarkoituksellinen: virheen hajonta skaalautuu tason mukana, joten
absoluuttinen virhejakauma antaisi hiljaisille päiville liian leveät ja vilkkaille liian
kapeat välit. Tuntitasolla käytetään samaa suhteellista leveyttä kuin päivätasolla.

### 8.3 Perusmalli: vahvuudet

1. **Ei virheen kumuloitumista.** Kaikki tasopiirteet lasketaan origossa, joten 30 vrk
   ennuste ei ole ketjutettu.
2. **Kalibroitu epävarmuus.** Välit tulevat mitatusta out-of-sample-virheestä, joten
   80 % peittävyys on todennettavissa eikä oletus.
3. **Kevyt.** Riippuvuudet: pandas, numpy, scikit-learn. Ei cmdstania, ei
   kääntämistä, asennus alle minuutissa, ajo alle 10 sekunnissa molemmille venueille.
4. **Läpinäkyvä.** Permutaatiotärkeydet ja osittaisriippuvuudet ovat suoraan tulkittavia,
   ja tuntiprofiili on luettavissa taulukkona.
5. **Sisäisesti johdonmukainen.** Tuntiennusteiden summa on päiväennuste.
6. **Kestää puuttuvaa dataa.** HistGradientBoosting käsittelee NaN-arvot natiivisti,
   eikä mediaanitäyttöä tarvita.
7. **Ei-negatiivinen rakenteeltaan.** Poisson-tappio, ei jälkikäteistä nollaanleikkausta.

### 8.4 Perusmalli: heikkoudet

1. **Ei opi vuosikausivaihtelua.** 4,5 kuukauden aineistossa ei ole yhtään täyttä vuotta.
   Vuodenaikapiirteet ovat käytännössä trendin jatketta. Ennuste kesäkuulle perustuu
   toukokuun tasoon, ei kesäkuun historiaan.
2. **Kiinteä taso koko horisontille.** `level_28d` ei päivity ennusteen edetessä. Jos
   kävijämäärä on aidosti kasvussa, 30 vrk ennuste aliarvioi systemaattisesti.
3. **Ei osaa ennakoida tapahtumia.** Konsertti, näyttelyn avajaiset tai koulujen loma
   näkyvät datassa piikkinä, mutta malli ei tiedä tulevista. Tämä on suurin yksittäinen
   virhelähde tapahtumapainotteisessa kohteessa.
4. **Sään vaikutus on korrelaatio, ei mekanismi.** Malli oppii että lämpimänä päivänä
   kävijöitä on enemmän. Se ei erota sitä siitä että lämpimät päivät osuvat lomakaudelle.
5. **Tuntiprofiili on staattinen.** Sama viikonpäiväprofiili koko horisontille. Ei
   reagoi esimerkiksi poikkeaviin aukioloaikoihin.
6. **Ennustevälit ovat luotettavia vain siltä osin kuin backtest on edustava.** Origoja
   on 4,5 kuukauden aineistolla enintään noin 12 - 15, joten q10 ja q90 lepäävät ohuen
   otoksen varassa.
7. **Sää yli 16 vuorokauden on klimatologiaa.** Vuorokaudet 17 - 30 käyttävät historiallista
   keskiarvosäätä, mikä tasoittaa ennustetta ja kaventaa keinotekoisesti vaihtelua.
8. **Nolla-inflaatio.** Noin 60 % tunneista on nollia. Päivätasolla ongelma on pieni,
   mutta profiilin reunatunnit ovat epävakaita.

### 8.5 Vertailumalli: Prophet + XGBoost

Nimi tulosteissa: `prophet_xgb`. Sama rakenne kuin nykyisessä sovelluksessa, mutta
päivätasolla ja korjatuilla epäkohdilla.

Rakenne:

1. **Prophet** sovitetaan päivätason kohteeseen. Additiivinen malli:
   trendi + viikkokausi + vuosikausi + pyhäpäivät + sääregressorit
   (`temp_mean`, `precip_sum`, `wind_mean`).
2. **XGBoost** sovitetaan Prophetin **residuaaleihin** kalenteri- ja sääpiirteillä.
3. Lopullinen ennuste on `prophet_yhat + xgb_residual`, leikattuna nollaan.
4. Tuntitaso ja epävarmuus tulevat samoista yhteisistä komponenteista kuin perusmallissa,
   eli kerroksista 2 ja 3. Prophetin omia `yhat_lower` ja `yhat_upper` -arvoja **ei käytetä**.

Erot nykyiseen toteutukseen ja perustelut:

| Nykyinen | Uusi | Miksi |
| --- | --- | --- |
| Tuntitason Prophet, `daily_seasonality=True` **ja** oma `hourly_pattern`-kausi `period=1` | Päivätason Prophet, tuntitaso profiilista | Kaksi päällekkäistä vuorokausikautta on kollineaarinen ja tekee komponenteista tulkitsemattomia |
| Ennustevälit: Prophetin väli + piste-residuaali | Empiiriset backtest-kvantiilit | Prophetin väli ei sisällä XGBoostin epävarmuutta |
| Päivätason väli = 24 tuntivälin **summa** | Väli lasketaan päivätasolla | Summaus tuottaa absurdin leveitä välejä, esim. ennuste 29 kävijää välillä 0 - 502 |
| `in`, `out` ja `total` erillisinä malleina | Yksi malli `total`ille, `in` ja `out` jaettuna historiallisella suhteella | Erilliset mallit eivät summaudu: 63,99 + 52,12 ei ole 191,31 |
| Ennusteet syötetään takaisin viivepiirteisiin | Ei rekursiota | Virhe kumuloituu horisontin pidentyessä |
| Yksi 80/20 aikajakosplit, mittarit lasketaan siitä, lopullinen malli sovitetaan koko datalla | Rolling origin -backtest | Yksi splitti antaa yhden havainnon mallin laadusta |
| Mediaanitäyttö puuttuville piirteille | NaN natiivisti tuettu | Mediaanitäyttö vääristää ja piilottaa datan puutteet |

Vahvuudet:

1. Erottelee trendin, viikkokauden ja pyhät eksplisiittisesti, mikä on hyvä
   kommunikointiväline: "tämä piikki on juhannus, ei trendi".
2. Prophetin pyhäkomponentti käsittelee siirtyvät pyhät oikein.
3. Kaksivaiheisuus antaa gradient boostingille mahdollisuuden korjata systemaattisia
   poikkeamia jäljelle jäävästä signaalista.
4. Vertailukohta on tuttu ja jatkuvuus nykyiseen sovellukseen säilyy.

Heikkoudet:

1. **Raskas asennus.** Prophet vaatii cmdstanin. Nykyisessä repossa on jouduttu
   kirjoittamaan kiertotie (`_ensure_prophet_backend` luo puuttuvan makefilen).
   CI-ajossa asennus vie minuutteja.
2. **Ylisovittaminen lyhyeen aineistoon.** Vuosikausikomponentti sovitetaan 4,5 kuukauden
   dataan, jolloin se oppii kohinaa ja ekstrapoloi sen tulevaisuuteen.
3. **Additiivisuusoletus.** Sään ja viikonpäivän yhteisvaikutus ei ole additiivinen: sade
   vaikuttaa lauantaihin eri tavalla kuin tiistaihin. Prophet ei mallinna interaktioita.
4. **Kaksi virhelähdettä ketjussa.** Jos Prophet on systemaattisesti pielessä, XGBoost
   oppii korjaamaan sen, mutta korjaus perustuu samaan pieneen aineistoon.
5. **Hitaampi.** Sovitus on sekunneista minuutteihin, mikä hankaloittaa backtestin
   ajamista useilla origoilla.
6. **Vaikeampi selittää.** Komponenttitiedostossa on yli 90 saraketta.

### 8.6 Sää yli 16 vuorokauden

Open-Meteo antaa enintään 16 vuorokautta ennustetta. 30 vuorokauden ennuste tarvitsee
kuitenkin sään kaikille päiville.

| Vuorokaudet | Sään lähde | Merkintä |
| --- | --- | --- |
| 1 - 16 | Open-Meteo forecast | `weather_source = "forecast"` |
| 17 - 30 | Klimatologia, 10 vuoden keskiarvo samalle kalenteripäivälle | `weather_source = "climatology"` |

Nykyinen sovellus täyttää puuttuvan sään **mediaaniarvoilla koko koulutusaineistosta**,
mikä tarkoittaa tammikuun ja toukokuun sekoitusta. Klimatologia on selvästi parempi, mutta
sillä on oma seurauksensa: keskiarvosää tuottaa keskiarvokävijämäärän, joten vuorokausien
17 - 30 ennusteet ovat systemaattisesti liian tasaisia. Tämä on tehtävä näkyväksi
käyttöliittymässä: `weather_source`-sarake ohjaa visuaalisen merkinnän
"sää perustuu tilastolliseen keskiarvoon".

### 8.7 Validointi

**Rolling origin -backtest.**

```
origo o = viimeisin havaittu päivä miinus (n * 7 vrk),  n = 1..N
kullekin origolle:
    koulutus = kaikki data <= o
    ennuste  = o+1 .. o+30
    vertaa toteumaan
```

Origoja otetaan niin monta kuin dataa riittää, vähintään 8 ja siten että jokaisessa
koulutusjoukossa on vähintään 60 päivää. Nykyisellä aineistolla tämä tarkoittaa noin
12 origoa.

**Mittarit**, laskettuna horisonttikoreittain (1 - 7, 8 - 14, 15 - 30) ja mallikohtaisesti:

| Mittari | Miksi |
| --- | --- |
| MAE | Päämittari, samassa yksikössä kuin kohde |
| RMSE | Rankaisee suuria virheitä, paljastaa piikkien käsittelyn |
| sMAPE | Suhteellinen, vertailukelpoinen venueiden välillä joilla eri taso |
| Bias (keskivirhe etumerkillä) | Paljastaa systemaattisen yli- tai aliarvion |
| Peittävyys 80 % | Osuus toteumista p10 - p90 välillä. Tavoite 0,80, hyväksyttävä 0,70 - 0,90 |

**Vertailukohdat**, jotka on aina raportoitava mallien rinnalla:

- *Seasonal naive*: sama viikonpäivä viikko sitten
- *Liukuva keskiarvo*: viimeisten 28 päivän keskiarvo

Jos kumpikaan varsinainen malli ei voita näitä, mallia ei kannata käyttää. Tämä on
oleellinen rehellisyysportti, ja se raportoidaan `/quality`-sivulla.

### 8.8 Milloin ennustetta ei pidä uskoa

Nämä kirjataan sekä `metrics.json`-tiedostoon että käyttöliittymään.

1. Horisontti yli 14 vuorokautta. Sää on klimatologiaa ja taso on lukittu origoon.
2. Päivä jolla on ohjelmistoa tai tapahtuma, jota malli ei tunne.
3. Ensimmäiset kaksi viikkoa uuden venuen tai uuden sensorin käyttöönotosta.
4. Jakso jolla ingest-manifesti raportoi `degraded`-lähteitä.
5. Koulujen loma-ajat ja juhannus, joista aineistossa on korkeintaan yksi havainto.
6. Kaikki tilanteet joissa peittävyys on jäänyt alle 0,70 viimeisimmässä backtestissä.

---

## 9. Automaatio ja ajastus

### GitHub Actions, päivittäinen ajo

`.github/workflows/daily.yml`, `cron: "15 3 * * *"` UTC eli 06.15 Suomen kesäaikaa.

```
1. checkout
2. setup-python 3.12, asenna ingest-riippuvuudet
3. python -m ovf_ingest run --days-back 7
4. jos exit != 0: avaa issue ja keskeytä
5. asenna forecast-riippuvuudet
6. python -m ovf_forecast run
7. commit data/processed ja data/forecasts, viesti "data: automated update YYYY-MM-DD"
8. push, mikä laukaisee Cloudflare Pages -buildin
```

Salaisuudet GitHub Secretsissä: `JASKARETAIL_BASIC_AUTH_USERNAME`,
`JASKARETAIL_BASIC_AUTH_PASSWORD`. Prophet asennetaan vain jos `--model` sisältää
`prophet_xgb`, muuten työ jää alle kahteen minuuttiin.

### Vaihtoehto: paikallinen ajo

`launchd`-agentti macOS:lle (`~/Library/LaunchAgents/fi.oulu2026.ovf.plist`) tai
`cron`-rivi Linuxille. Ajaa saman `make daily` -komennon. Dokumentoidaan varamenettelynä,
jos Actions-minuutit loppuvat tai rajapinta vaatii verkon josta Actions ei pääse.

### Virhetilanteiden käsittely

| Tilanne | Toiminta |
| --- | --- |
| Yksi lähde alhaalla | Ajo jatkuu, manifestiin `degraded`, banneri sivustolle |
| Kaikki lähteet alhaalla | Ajo epäonnistuu, vanha data jää voimaan, GitHub-issue avataan |
| Laatuportti pettää | Uusi data `.rejected`-tiedostoon, vanha jää voimaan, issue |
| Ennusteajo kaatuu | Edellinen ennuste jää voimaan, web näyttää sen iän |
| Web-build kaatuu | Edellinen julkaisu jää voimaan Cloudflare Pagesissa |

---

## 10. Kehitysaskeleet

Vaiheet on mitoitettu niin että jokainen päättyy toimivaan, testattavaan tilaan.

### Vaihe 0: pohjustus

1. Luo repo `oulu2026-visitor-flow-framework`, MIT- tai vastaava lisenssi
2. Monorepo-runko luvun 3 mukaan, tyhjät paketit
3. `pyproject.toml`, riippuvuusryhmät `ingest`, `forecast`, `prophet`, `dev`
4. `ruff` + `pytest` + `mypy` konfiguraatiot, `.github/workflows/ci.yml`
5. Kopioi `config/venues.json`, `config/sites.json` ja `config/holidays.csv` nykyisestä reposta
6. Kopioi `docs/DATA_MODEL.md` ja tämä suunnitelma repoon

Valmis kun: `make ci` ajaa läpi tyhjällä testijoukolla.

### Vaihe 1: ingest, lukurajapinnat

1. `config.py`: pydantic-mallit ja lataus
2. `clients/openmeteo.py`: archive ja forecast, retry-logiikka, raakavastaus levylle
3. `clients/ecocounter.py`: GraphQL, neljä sensoria, UTC-käsittely
4. `clients/jaskaretail.py`: basic auth, in ja out, `.env`-lataus
5. Yksikkötestit tallennetuilla vastauksilla (`tests/fixtures/*.json`), ei verkkoa testeissä

Valmis kun: kukin client palauttaa normalisoidun DataFramen fixture-syötteestä.

### Vaihe 2: ingest, kanoninen aineisto

1. `normalize.py`: `ts_utc` ja `ts_local`, sarakenimet, tyypit, `is_imputed`
2. `store.py`: raakatiedostot ja kanoniset taulut, idempotentti kirjoitus
3. `validate.py`: laatuportit ja `manifest.json`
4. `climatology.py` ja kertaluontoinen ajo 10 vuoden datalle
5. `cli.py` ja luvun 5 komennot
6. Täysi historia-ajo `--start 2026-01-01`, vertaa rivimääriä nykyisen repon dataan

Valmis kun: `data/processed/` sisältää luvun 4.2 tiedostot ja `verify` menee läpi.

Tarkistuspiste: `visitors_hourly.csv` sisältää jaksolla 1.1. - 22.5.2026 **3407 riviä**
per venue. Laskutoimitus on 142 vrk x 24 h = 3408, miinus yksi tunti joka katoaa
kesäaikasiirtymässä 29.3.2026. Nykyisen repon `venue_N_features.csv` on 3408 riviä,
koska se käsittelee aikaleimoja vyöhykkeettöminä. Yhden rivin ero on odotettu ja
todistaa että uusi aikavyöhykekäsittely toimii.

### Vaihe 3: forecast, perusmalli

1. `dataset.py`: kanonisista tauluista päivätason mallinnusmatriisi
2. `features.py`: luvun 8.2 piirteet, yksikkötestit vuotoja vastaan
3. `models/baseline.py`
4. `profile.py`: tuntiprofiili ja aukioloaikojen johtaminen
5. `backtest.py`: rolling origin, myös vertailukohdat seasonal naive ja liukuva keskiarvo
6. `intervals.py`: suhteelliset kvantiilit
7. `export.py`: `daily_30d.csv`, `hourly_7d.csv`, `metrics.json`, `backtest.csv`

Valmis kun: perusmalli voittaa seasonal naiven MAE:ssa horisonteilla 1 - 7.
Jos ei voita, malli tai piirteet on korjattava ennen etenemistä.

### Vaihe 4: forecast, vertailumalli

1. `models/prophet_xgb.py` luvun 8.5 mukaan
2. Prophet valinnaisena riippuvuutena, selkeä virheilmoitus jos puuttuu
3. Molemmat mallit samaan tulostiedostoon `model`-sarakkeella
4. `report`-komento joka tulostaa mallien vertailun taulukkona

Valmis kun: `python -m ovf_forecast run` tuottaa rivit molemmille malleille ja
`metrics.json` sisältää neljä sarjaa (kaksi mallia, kaksi vertailukohtaa).

### Vaihe 5: web, runko ja data

1. Astro-projekti, Tailwind, TypeScript
2. `scripts/build-data.ts` ja luvun 7 JSON-paketit
3. Tyypit `src/lib/types.ts`, generoitu tai käsin kirjoitettu datasopimuksesta
4. Layout, navigaatio, datan tuoreus -banneri
5. `/` yleiskuvasivu ensimmäisillä kaavioilla

Valmis kun: `npm run build` tuottaa staattisen sivuston, joka näyttää oikeat luvut.

### Vaihe 6: web, näkymät

1. `/venue/[id]`: aikasarja, lämpökartta, kapasiteetti, liput
2. `/weather`: hajontakuvio ja säätilavertailu
3. `/forecast`: ennustekaaviot, p10 - p90, mallivalitsin, sään lähteen merkintä
4. `/quality`: backtest-visualisointi ja rajoitteet
5. `/about`
6. Saavutettavuustarkistus ja mobiilinäkymä

Valmis kun: kaikki luvun 7 näkymät toimivat ja sivun paino on alle 500 kB.

### Vaihe 7: automaatio

1. `.github/workflows/daily.yml`
2. Salaisuudet GitHub Secretsiin
3. Cloudflare Pages -projekti kytkettynä repoon
4. Testaa manuaalisella `workflow_dispatch`-ajolla
5. Virhetilanteiden testaus: väärä salasana, rajapinta alhaalla, laatuportti pettää
6. Dokumentoi paikallinen `launchd`-vaihtoehto

Valmis kun: kolme peräkkäistä automaattista ajoa on mennyt läpi ja sivusto on päivittynyt.

### Vaihe 8: käyttöönotto

1. `docs/FORECAST_MODEL.md` viimeistely mitatuilla luvuilla
2. `README.md`: asennus, ajo, vianetsintä
3. Rinnakkaisajo nykyisen sovelluksen kanssa 2 viikkoa, vertaa ennusteita
4. Päätös tuotantomallista mitattujen tulosten perusteella
5. Nykyinen repo merkitään arkistoiduksi tai jätetään referenssiksi

---

## 11. Riskit ja avoimet kysymykset

| Riski | Vaikutus | Lievennys |
| --- | --- | --- |
| Aineisto liian lyhyt luotettavaan 30 vrk ennusteeseen | Ennuste harhaanjohtava | Vertailukohdat aina näkyvissä, peittävyys raportoidaan, epävarmuus korostettuna |
| Jaskaretail-rajapinta muuttuu tai tunnukset vanhenevat | Kävijädata pysähtyy | Manifesti ja banneri, GitHub-issue automaattisesti |
| Eco-Counter on vain yksi piste Oulussa | Venue 2:lle merkityksetön | Esitetään kontekstidatana, ei venuekohtaisena mittarina |
| Tapahtumakalenterin puuttuminen | Suurin yksittäinen virhelähde | Avoin kysymys, katso alla |
| Datan kasvu gitissä | Repo turpoaa | Raakadata pakataan kuukausittain, arvio 25 MB vuodessa |
| Cloudflare Pages -buildin kaatuminen | Sivusto vanhenee | Edellinen julkaisu jää voimaan, buildin laatuportit |

### Avoimet kysymykset

1. **Onko tapahtumakalenteri saatavilla koneluettavasti?** Oulu2026:n ohjelmakalenteri
   piirteenä (`is_event_day`, `event_capacity`) olisi todennäköisesti suurin yksittäinen
   parannus ennusteen tarkkuuteen. Kannattaa selvittää ennen vaihetta 3.
2. **Pitääkö venue 2 (Kaupungintalo, Espoo) olla mukana?** Sen koordinaatit ja
   Eco-Counter-kytkentä ovat epäjohdonmukaisia nykyisessä konfiguraatiossa.
3. **Onko aukioloaikoja saatavilla eksplisiittisesti?** Nyt ne johdetaan datasta.
4. **Halutaanko sivusto julkiseksi vai suojatuksi?** Cloudflare Access lisää kirjautumisen
   ilman koodimuutoksia, jos data on sisäistä.
