# Tietomalli: rajapinnat ja data

*In English: [`DATA_MODEL.en.md`](DATA_MODEL.en.md).*

Tämä dokumentti kuvaa Visitor Forecast -repon käyttämät ulkoiset rajapinnat, levylle
tallennetut datajoukot ja niiden skeemat. Dokumentti on tarkoitettu lähtötiedoksi, kun
olemassa olevan kävijä- ja säädatan päälle rakennetaan uusi visualisointisovellus.

Tila kuvaushetkellä: repo `oulu2026-visitor-flow-prediction-tool`, data haettu 1.1.2026 alkaen,
tuorein havainto 22.5.2026, tuorein ennuste ajettu 22.5.2026.

Kaikki polut ovat suhteessa hakemistoon `visitor_forecast/`, ellei toisin mainita.

---

## 1. Datan kulku

```
Ulkoiset rajapinnat                Raakacache (levy)              Prosessoitu (levy)                Ennusteet
------------------------------------------------------------------------------------------------------------------
Jaskaretail IoT (REST)      ->  data/raw/iot_sensors/venue_N/  ->  data/processed/iot_sensors/  \
Open-Meteo (REST)           ->  data/raw/weather/venue_N/      ->  data/processed/weather/       >  venue_N_features.csv  ->  data/forecasts/venue_N/
Oulun liikenne Eco-Counter  ->  data/raw/eco_counter/<site>/   ->  data/processed/eco_counter/  /   (tuntitason päätaulu)
  (GraphQL)                                                    ->  data/processed/eco_counter_sites/<site>/
Oulun liikenne TPM (REST)   ->  data/raw/traffic/tpm/          ->  data/processed/traffic/      (ei dataa levyllä nyt)
Lipunmyynti (manuaalinen)   ->  data/raw/tickets/venue_N/tickets.csv
Pyhäpäivät (ylläpidetty)    ->  config/holidays.csv
```

Keskeinen havainto visualisoinnin kannalta: **`data/processed/venue_{id}_features.csv` on jo
valmis, tuntitason yhdistelmätaulu**, jossa kävijät, liput, kalenteri, Eco-Counter ja sää ovat
samalla rivillä. Uuden sovelluksen ei tarvitse kutsua yhtäkään rajapintaa, jos sen riittää
lukea tämä tiedosto (ja halutessaan ennustetiedostot).

---

## 2. Ulkoiset rajapinnat

### 2.1 Jaskaretail IoT (kävijälaskenta)

| Kohta | Arvo |
| --- | --- |
| URL | `https://oulu.jaskaretail.com:443/ext/sensor/visitor` |
| Metodi | POST, parametrit query stringissä |
| Autentikointi | HTTP Basic, `JASKARETAIL_BASIC_AUTH_USERNAME` / `_PASSWORD` repojuuren `.env.local`-tiedostosta |
| Moduuli | `visitor_forecast/iot_sensors.py` |
| CLI | `scripts/01_fetch_iot_sensors.py --all-venues --days-back 7` |

Query-parametrit:

| Parametri | Esimerkki | Selitys |
| --- | --- | --- |
| `locationHierarchyIdList` | `178` | Pilkkuerotettu lista. Venue-kohtainen `locationHierarchyId` settings.jsonista |
| `startDate` / `endDate` | `2026-05-01` | Inklusiivinen ikkuna, `YYYY-MM-DD` |
| `interval` | `60min` | Oletus `iot_sensors.default_interval` |
| `countingTypeId` | `in` tai `out` | Haetaan erikseen molemmille suunnille ja yhdistetään |

Vastaus: `{"result": [ { "categoryName": "01/05/2026 08:00:00", "locationId": 178, "visitors": 12 }, ... ]}`.
Aikaleiman kenttä voi olla `categoryName`, `timestamp` tai `date`; formaatti `%d/%m/%Y %H:%M:%S`.
Lukuarvo etsitään avaimista `visitors`, `counts`, `count`, `value` (myös sisäkkäisistä objekteista).
Rivit summataan `(timestamp, locationId)`-tasolle, ja `in`/`out`-haut yhdistetään yhdeksi riviksi.

### 2.2 Open-Meteo (sää)

| Kohta | Arvo |
| --- | --- |
| Historia | `https://archive-api.open-meteo.com/v1/archive` |
| Ennuste | `https://api.open-meteo.com/v1/forecast` (enintään 16 vrk) |
| Autentikointi | ei tarvita |
| Aikavyöhyke | `timezone=Europe/Helsinki`, eli **aikaleimat ovat paikallista aikaa ilman vyöhyketietoa** |
| Moduuli | `visitor_forecast/weather.py` |
| CLI | `scripts/02_weather_fetch_openmeteo.py --all-venues --days-back 30` |

Haettavat `hourly`-parametrit: `temperature_2m`, `precipitation`, `wind_speed_10m`,
`relative_humidity_2m`, `weathercode`. Koordinaatit tulevat venue-määrityksestä.

Vastauksesta johdetut lisäkentät (`weather.py`):

- `weathercode_str`: WMO-koodin tekstivastine, sanakirja `WEATHER_CODES` (esim. 0 `clear`, 3 `overcast`, 61 `slight_rain`, 71 `slight_snow_fall`, 95 `thunderstorm`)
- `is_precipitation`: `precipitation > 0`
- `is_cold`: `temperature_2m < 0`
- `is_windy`: `wind_speed_10m > 10`

Ennustecachen tuoreusraja on 1 tunti (`FORECAST_CACHE_TTL`), sen jälkeen haetaan uudelleen.

### 2.3 Oulun liikenne Eco-Counter (jalankulku ja pyöräily)

| Kohta | Arvo |
| --- | --- |
| URL | `https://api.oulunliikenne.fi/proxy/graphql` |
| Metodi | POST, GraphQL |
| Autentikointi | ei tarvita |
| Moduuli | `visitor_forecast/traffic.py` |
| CLI | `scripts/07_fetch_eco_counter.py --all-venues --days-back 7`, sitten `scripts/09_aggregate_eco_counter_by_site.py` |

Kysely rakennetaan sensorikohtaisesti (`_build_eco_counter_site_data_query`):

```graphql
query GetEcoCounterSiteData {
  ecoCounterSiteData(id: "karjasilta_1", domain: Oulu_Kapy, step: hour,
                     begin: "2026-05-01T00:00:00", end: "2026-05-22T00:00:00") {
    date
    counts
  }
}
```

`domain` ja `step` upotetaan enumeina (validointi `^[A-Za-z_][A-Za-z0-9_]*$`), `id`, `begin` ja
`end` merkkijonoina. `step` on `hour` tai `day`.

Sensorityypit ja niiden merkitys:

| Tunnus | Tyyppi | Suunta | Sarakenimi prosessoidussa datassa |
| --- | --- | --- | --- |
| `JK_IN` | jalankulku | sisään | `jk_in_counts` |
| `JK_OUT` | jalankulku | ulos | `jk_out_counts` |
| `PP_IN` | pyöräily | sisään | `pp_in_counts` |
| `PP_OUT` | pyöräily | ulos | `pp_out_counts` |

**Vastauksen aikaleimat ovat UTC-muodossa** (`2026-05-22 04:00:00+00:00`), toisin kuin muut
lähteet. Katso luku 7.1.

### 2.4 Oulun liikenne TPM (ajoneuvoliikenne)

| Kohta | Arvo |
| --- | --- |
| URL | `https://api.oulunliikenne.fi/tpm/v1` |
| Endpointit | `GET /stations`, `GET /stations/{station_id}/measurements?from=&to=&timeResolution=hour` |
| Moduuli | `visitor_forecast/traffic.py`, funktio `fetch_tpm_data` |
| CLI | `scripts/06_fetch_tpm.py --venue-id 1 2 --days-back 7` |

Asemat suodatetaan venuen koordinaattien ympäriltä haversine-etäisyydellä
(`traffic.tpm.max_distance_km`, nyt 2.0 km). Prosessoitu tulos olisi
`data/processed/traffic/venue_{id}_tpm.csv` sarakkeilla `timestamp, venue_id,
tpm_station_count, tpm_mean_count`.

**Huom: TPM-dataa ei ole tällä hetkellä levyllä.** Integraatio on koodissa ja konfiguraatiossa,
mutta hakemistoa `data/raw/traffic/` ja `data/processed/traffic/` ei ole. Uusi
visualisointisovellus ei siis voi olettaa TPM-dataa olevan.

---

## 3. Konfiguraatio

Lähde: `visitor_forecast/config/settings.json`, validoitu Pydanticilla
(`visitor_forecast/configuration.py`). Uusi sovellus voi lukea saman tiedoston suoraan JSONina.

### 3.1 Venuet

| venue_id | name | city | lat | lon | capacity | locationHierarchyId | tickets |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Pekuri | Oulu | 65.0134 | 25.4756 | 160 | 178 | `data/raw/tickets/venue_1/tickets.csv` |
| 2 | Kaupungintalo | Espoo | 60.2055 | 24.6558 | 20 | 183 | `data/raw/tickets/venue_2/tickets.csv` |

Huomaa että venue 2:n koordinaatit ja kaupunki ovat Espoo, vaikka nimi on Kaupungintalo. Sää
haetaan näillä koordinaateilla, joten venue 1:n ja venue 2:n säädata eroaa toisistaan.

### 3.2 Eco-Counter-sivustot

Yksi konfiguroitu sivusto:

```json
"raatti": {
  "name": "Karjasilta",
  "domain": "Oulu_Kapy",
  "sensors": { "JK_IN": "karjasilta_1", "JK_OUT": "karjasilta_2",
               "PP_IN": "karjasilta_4", "PP_OUT": "karjasilta_3" },
  "venue_ids": [1, 2]
}
```

Sivuston avain on `raatti`, mutta näyttönimi on `Karjasilta`. Sivusto on liitetty **molempiin**
venueihin, joten Eco-Counter-luvut ovat identtiset venue 1:llä ja venue 2:lla.

### 3.3 Muut asetusryhmät

`forecast_horizon_days: 30`, `retrain_frequency_days: 7`, `web.port: 2026`,
`targets.visitors` (tuntitaso, metriikat `visitors_in`, `visitors_out`, `total_visitors`),
`targets.tickets` (päivätaso, metriikka `tickets_sold`).

---

## 4. Entiteetit ja skeemat

### 4.1 Tuntitason kävijähavainto (IoT)

Raaka: `data/raw/iot_sensors/venue_{id}/YYYY-MM-DD.csv`, yksi tiedosto per päivä, 142 tiedostoa
per venue (1.1.2026 - 22.5.2026).

| Sarake | Tyyppi | Selitys |
| --- | --- | --- |
| `timestamp` | naive datetime | Tunnin alku, paikallista aikaa |
| `locationId` | int | Sama kuin venuen `locationHierarchyId` |
| `visitors_in` | float | Sisään laskettu |
| `visitors_out` | float | Ulos laskettu |
| `total_visitors` | float | `visitors_in + visitors_out` |

Yhdistetty: `data/processed/iot_sensors/venue_{id}_iot.csv`, sarakkeet `timestamp,
visitors_in, visitors_out, total_visitors`, 3408 riviä.

Huomaa että `total_visitors` on **sisään- ja ulosmenojen summa**, ei nettokävijämäärä eikä
uniikkien kävijöiden määrä. Karkea kävijäarvio on `total_visitors / 2`.

### 4.2 Tuntitason sää

Raaka: `data/raw/weather/venue_{id}/YYYY-MM-DD.csv`, 148 tiedostoa per venue
(1.1.2026 - 28.5.2026, viimeiset päivät ovat ennustecachea).

| Sarake | Tyyppi | Selitys |
| --- | --- | --- |
| `timestamp` | naive datetime | Paikallista aikaa (Europe/Helsinki) |
| `temperature_2m` | float | Celsius |
| `precipitation` | float | mm kyseisellä tunnilla |
| `wind_speed_10m` | float | km/h |
| `relative_humidity_2m` | int | % |
| `weathercode` | int | WMO-koodi |
| `weathercode_str` | string | Tekstivastine |
| `is_precipitation` | bool | `True`/`False`-merkkijonona CSV:ssä |
| `is_cold` | bool | |
| `is_windy` | bool | |

Yhdistetty: `data/processed/weather/venue_{id}_weather.csv`. **Varoitus: tämä tiedosto sisältää
vain viimeisimmän hakuikkunan**, nyt 168 riviä (22.5. - 28.5.2026). Koko säähistoria löytyy
päiväkohtaisista raakatiedostoista ja `venue_{id}_features.csv`-tiedostosta.

### 4.3 Eco-Counter, sivustotaso

Raaka ja prosessoitu, molemmat tuntitasoa:

- `data/raw/eco_counter/raatti/YYYY-MM-DD.csv` (142 tiedostoa)
- `data/processed/eco_counter_sites/raatti/YYYY-MM-DD.csv` (142 tiedostoa)

| Sarake | Tyyppi | Selitys |
| --- | --- | --- |
| `date` | tz-aware datetime (UTC) | Sarakkeen nimi on `date`, mutta arvo on tunti |
| `jk_in_counts` | float | Jalankulkijat sisään |
| `jk_out_counts` | float | Jalankulkijat ulos |
| `pp_in_counts` | float | Pyöräilijät sisään |
| `pp_out_counts` | float | Pyöräilijät ulos |

Venuekohtainen yhdistelmä: `data/processed/eco_counter/venue_{id}_eco.csv`, 3381 riviä,
sarakkeet `date, counts (JK_IN), counts (JK_OUT), counts (PP_IN), counts (PP_OUT)`. Sulkeissa
olevat sarakenimet normalisoidaan nykyisessä dashboardissa muotoon `JK_IN` jne.
(`app/utils/data_loader.py: load_eco_counter`).

Kattavuus 1.1. - 22.5.2026, yhteensä venue 1:llä JK_IN 21 552 ja PP_IN 53 355 havaintoa.

### 4.4 Lipunmyynti (päivätaso)

`data/raw/tickets/venue_{id}/tickets.csv`, ylläpidetään käsin viikoittain.

| Sarake tiedostossa | Normalisoitu nimi | Selitys |
| --- | --- | --- |
| `DATE` | `date` | Muoto `d.m.YYYY`, esim. `14.1.2026` |
| `TICKETS` | `tickets_sold` | Yksittäisliput |
| `GROUPS` | `groups_sold` | Ryhmäliput |
| `TOTAL` | `tickets_total` | Yhteensä |

Sarakenimien tunnistus on aliaspohjaista ja skandit siedetään (`liput`, `ryhmat`, `yhteensa`,
`pvm`). Kattavuus: venue 1 14.1. - 17.5.2026 (124 riviä), venue 2 13.1. - 17.5.2026 (125 riviä).
Lipunmyynti loppuu siis viisi päivää ennen kävijädatan loppua.

### 4.5 Pyhäpäivät

`config/holidays.csv`, 16 riviä, vuosi 2026.

| Sarake | Selitys |
| --- | --- |
| `date` | `YYYY-MM-DD` |
| `holiday_name` | Suomenkielinen nimi, esim. `Uudenvuodenpäivä` |
| `is_weekend` | 0/1 |
| `is_last_workday_before_holiday` | 0/1 |
| `type` | `national` tai `religious` |
| `country` | `Finland` |

### 4.6 Tuntitason piirretaulu (päätaulu)

`data/processed/venue_{id}_features.csv`, 3408 riviä per venue, 59 saraketta,
1.1.2026 00:00 - 22.5.2026 23:00, tiheä tuntisarja ilman aukkoja.
`data/processed/combined_features.csv` sisältää molemmat venuet (6816 riviä).

Sarakkeet ryhmittäin:

**Avaimet ja mitat**

| Sarake | Selitys |
| --- | --- |
| `timestamp` | Tunnin alku, naive, paikallista aikaa |
| `date` | Päivä (00:00) |
| `venue_id`, `venue_name`, `location_city` | 1/Pekuri/Oulu tai 2/Kaupungintalo/Espoo |
| `hour` | 0-23 |

**Kävijät**

| Sarake | Selitys |
| --- | --- |
| `visitors_in`, `visitors_out`, `total_visitors` | Tunnin havainnot |
| `daily_visitors_in`, `daily_visitors_out`, `daily_total_visitors` | Kyseisen päivän summat, toistuvat jokaisella tunnilla |
| `visitors_lag_1d`, `visitors_lag_7d` | Edellisen päivän ja viikontakaisen päivän summa |
| `visitors_7d_avg`, `visitors_30d_avg` | Liukuvat keskiarvot päivätasolla |

**Liput**

| Sarake | Selitys |
| --- | --- |
| `daily_tickets_sold`, `daily_groups_sold`, `daily_tickets_total` | Päivän lipputiedot toistettuna tunneille. **NaN päiville joilla ei ole lippudataa** |
| `tickets_lag_1d`, `tickets_lag_7d`, `tickets_7d_avg`, `tickets_30d_avg` | Historiapiirteet, NaN havaintojakson ulkopuolella |
| `visitor_to_ticket_ratio` | `total_visitors / daily_tickets_sold`, NaN jos lippudataa ei ole |

**Kapasiteetti**

`capacity` (venuen vakio), `venue_capacity_utilization` (`total_visitors / capacity`),
`daily_capacity_utilization` (`daily_total_visitors / capacity`).

**Eco-Counter ja johdetut virtaukset**

| Sarake | Selitys |
| --- | --- |
| `jk_in_counts`, `jk_out_counts`, `pp_in_counts`, `pp_out_counts` | Raakalaskurit |
| `pedestrian_net_flow` | `jk_in - jk_out` |
| `bicycle_net_flow` | `pp_in - pp_out` |
| `pedestrian_total_flow`, `bicycle_total_flow` | Suuntien summat |
| `total_site_flow` | Kaikki yhteensä |
| `pedestrian_ratio`, `bicycle_ratio` | Osuudet kokonaisvirrasta, 0 jos nimittäjä 0 |
| `pedestrian_net_flow_lag_1d`, `bicycle_net_flow_lag_1d` | Siirto 24 riviä (tuntia) taaksepäin |

**Kalenteri**

`holiday_name` (NaN normaalipäivinä), `day_of_week` (0 = maanantai), `is_weekend`, `is_holiday`,
`days_before_next_holiday` (999 jos ei tiedossa), `is_last_workday_before_holiday`, `month`,
`year`, `day_of_month`, `week_of_year`.

**Sää**

`temperature_2m`, `precipitation`, `wind_speed_10m`, `relative_humidity_2m`, `weathercode`,
`weathercode_str`, `is_precipitation`, `is_cold`, `is_windy`. Kattavuus on 100 % koko jaksolla
molemmilla venueilla.

### 4.7 Ennustetiedostot

Hakemisto `data/forecasts/venue_{id}/`, tiedostonimissä ajopäivä `YYYYMMDD`. Uusin ajo 20260522,
edellinen 20260520. Horisontti 7 vuorokautta.

| Tiedosto | Rivit | Sarakkeet |
| --- | --- | --- |
| `forecast_visitors_{date}.csv` | 168 (7 vrk x 24 h) | `timestamp, venue_id, forecast_visitors_in, forecast_visitors_out, forecast_total_visitors`, säämuuttujat, `lower_bound, upper_bound` |
| `forecast_visitors_daily_{date}.csv` | 7 | `date, venue_id, forecast_visitors_in, forecast_visitors_out, forecast_total_visitors, lower_bound, upper_bound` |
| `forecast_tickets_{date}.csv` | 7 | `date, venue_id, forecast_tickets_sold, lower_bound, upper_bound` |
| `forecast_*_components.csv` | 504 | Prophetin komponentit: `ds, trend, weekly, yearly, daily, hourly_pattern, holidays`, pyhäkohtaiset sarakkeet, regressorikohtaiset vaikutukset, `yhat, timestamp, metric` |
| `forecast_*_feature_importance.csv` | 126 | `metric, feature, importance` (XGBoost-residuaalimalli) |

Mallit: `models/venue_{id}/prophet_{target}.pkl` ja `models/venue_{id}/xgb_{target}_residuals.pkl`,
targetit `visitors` ja `tickets`.

### 4.8 Legacy-tiedosto

`data/processed/features.csv` on vanha päivätason aineisto vuodelta 2024 (161 riviä, sarakkeet
`date, visitors, holiday_name, ...`). Se ei liity nykyiseen putkeen. **Älä käytä sitä uudessa
sovelluksessa.**

---

## 5. Tiedostokartta ja kattavuus

| Polku | Taso | Rivit tai tiedostot | Aikaväli |
| --- | --- | --- | --- |
| `data/processed/venue_1_features.csv` | tunti | 3408 riviä | 1.1. - 22.5.2026 |
| `data/processed/venue_2_features.csv` | tunti | 3408 riviä | 1.1. - 22.5.2026 |
| `data/processed/combined_features.csv` | tunti | 6816 riviä | 1.1. - 22.5.2026 |
| `data/processed/iot_sensors/venue_N_iot.csv` | tunti | 3408 riviä | 1.1. - 22.5.2026 |
| `data/processed/weather/venue_N_weather.csv` | tunti | 168 riviä | 22.5. - 28.5.2026 |
| `data/raw/weather/venue_N/*.csv` | tunti | 148 tiedostoa | 1.1. - 28.5.2026 |
| `data/processed/eco_counter/venue_N_eco.csv` | tunti | 3381 riviä | 1.1. - 22.5.2026 |
| `data/processed/eco_counter_sites/raatti/*.csv` | tunti | 142 tiedostoa | 1.1. - 22.5.2026 |
| `data/raw/tickets/venue_N/tickets.csv` | päivä | 124 - 125 riviä | 13.1. - 17.5.2026 |
| `config/holidays.csv` | päivä | 16 riviä | 2026 |
| `data/forecasts/venue_N/` | tunti ja päivä | 14 tiedostoa | 23.5. - 29.5.2026 |

Volyymit: venue 1 yhteensä 63 865 kävijätapahtumaa (maksimi 258 per tunti), venue 2 yhteensä
23 505 (maksimi 152). Lippuja myyty venue 1: 7745, venue 2: 6546.

---

## 6. Miten data yhdistetään

1. **Kävijät ja sää**: liitos `timestamp`-sarakkeella, molemmat tuntitasoa ja paikallista aikaa.
   Tämä liitos on jo tehty `venue_{id}_features.csv`-tiedostoon.
2. **Kävijät ja liput**: liitos `(date, venue_id)`. Lipputiedot toistetaan päivän jokaiselle
   tunnille etuliitteellä `daily_`.
3. **Kävijät ja Eco-Counter**: liitos `timestamp`-sarakkeella sen jälkeen kun Eco-Counterin
   `date` on muunnettu. Katso aikavyöhykevaroitus alla.
4. **Kalenteri**: liitos `date`-sarakkeella `config/holidays.csv`:sta.
5. **Päivätaso**: summaa `total_visitors`, `visitors_in`, `visitors_out`; keskiarvota lämpötila,
   tuuli ja kosteus; summaa sademäärä; ota `weathercode` moodina. Sama logiikka kuin
   `weather.aggregate_weather_daily`.

---

## 7. Sudenkuopat

### 7.1 Aikavyöhykkeet eivät ole yhtenäisiä

- IoT, sää ja piirretaulu: **naive datetime, paikallista aikaa** (Europe/Helsinki)
- Eco-Counter: **tz-aware UTC** (`+00:00`)

Tiedostossa `data_pipeline.load_site_eco_counter_data` Eco-Counterin aikaleima muunnetaan
`pd.to_datetime(..., utc=True).dt.tz_localize(None)`, mikä säilyttää UTC-kellonajan ja poistaa
vyöhykemerkinnän. Käytännössä Eco-Counterin luvut liittyvät piirretaulussa 2 - 3 tuntia väärään
tuntiin verrattuna kävijä- ja säädataan. Tämä kannattaa tarkistaa ja korjata uudessa
sovelluksessa: siirrä Eco-Counter Helsingin aikaan ennen liitosta.

### 7.2 Eco-Counter-data on jaettu venueiden kesken

Sivusto `raatti` on liitetty molempiin venueihin, joten `jk_*` ja `pp_*` -sarakkeet ovat
identtiset venue 1:llä ja venue 2:lla. Niitä ei voi esittää venuekohtaisena jalankulkuna.
Kyseessä on Karjasillan mittauspiste Oulussa, mikä ei liity venue 2:een (Espoo) mitenkään.

### 7.3 Nollatunnit

58,6 % venue 1:n ja 62,6 % venue 2:n tunneista on nollia. Osa on aitoja aukioloaikojen
ulkopuolisia tunteja, osa on `_normalize_iot_frame`-funktion tekemää tiheytystä
(`reindex(full_range, fill_value=0.0)`), joka täyttää puuttuvat tunnit nollilla. **Puuttuvaa
dataa ja aitoa nollaa ei voi erottaa toisistaan.** Ensimmäinen päivä jolla venue 1:llä on
kävijöitä on 22.1.2026, venue 2:lla 8.1.2026, vaikka sarja alkaa 1.1.

### 7.4 NaN vs. nolla lippudatassa

`daily_tickets_sold` on NaN päivinä joilta lippudataa ei ole (ennen 14.1. ja 17.5. jälkeen), ja
nolla havaintojakson sisällä olevina päivinä joilta myyntiä ei ole. Ero on tarkoituksellinen,
älä täytä NaN-arvoja nollilla visualisoinnissa.

### 7.5 Prosessoitu säätiedosto on vajaa

`data/processed/weather/venue_{id}_weather.csv` sisältää vain viimeisimmän hakuikkunan.
Historiallinen sää on luettava joko `venue_{id}_features.csv`-tiedostosta tai
`data/raw/weather/venue_{id}/*.csv`-päivätiedostoista.

### 7.6 Ennusteen in, out ja total eivät summaudu

`forecast_visitors_in`, `forecast_visitors_out` ja `forecast_total_visitors` ennustetaan
erillisillä malleilla, joten `in + out != total`. Esimerkiksi 23.5.2026: in 63,99, out 52,12,
total 191,31. Esitä ne rinnakkaisina sarjoina, älä pinottuna.

### 7.7 Aineisto on pieni ja epäkypsä

Neljä ja puoli kuukautta dataa, yksi mittauspiste liikennedatalle, ja venue 2 sijaitsee toisessa
kaupungissa. Ennusteiden luottamusvälit ovat leveitä (esim. päiväennuste 29 kävijää, väli 0 - 502).
Visualisoinnissa kannattaa korostaa havaittua dataa ja esittää ennuste varauksellisesti.

---

## 8. Lähtökohdat uudelle visualisointisovellukselle

### 8.1 Suositeltu datalähde

Yksinkertaisin polku: lue `data/processed/combined_features.csv` (2,2 MB, 6816 riviä,
59 saraketta) ja valinnaisesti uusimmat ennustetiedostot. Kaikki kävijä-, sää-, lippu-,
kalenteri- ja liikennedata on jo yhdistettynä. Rajapintakutsuja ei tarvita.

Jos sovellus halutaan staattiseksi (ei Python-backendiä), esiprosessoi CSV pienemmäksi
JSON-paketiksi: rajaa sarakkeet noin 15:een oleelliseen ja pyöristä liukuluvut. Tuloksena
karkeasti 400 - 600 kB, joka menee vaivatta yhteen HTML-tiedostoon tai staattiseen buildiin.

### 8.2 Sarakkeet jotka riittävät visualisointiin

`timestamp`, `date`, `hour`, `venue_id`, `venue_name`, `total_visitors`, `visitors_in`,
`visitors_out`, `daily_total_visitors`, `daily_tickets_sold`, `capacity`,
`venue_capacity_utilization`, `temperature_2m`, `precipitation`, `wind_speed_10m`,
`weathercode_str`, `is_precipitation`, `is_holiday`, `is_weekend`, `holiday_name`,
`day_of_week`, `total_site_flow`.

### 8.3 Näkymiä joita data tukee

| Näkymä | Data |
| --- | --- |
| Kävijämäärä ajassa, tunti- tai päivätaso, venuet rinnakkain | `total_visitors` aikasarjana |
| Sää ja kävijät samalla akselilla | `total_visitors` pylväinä, `temperature_2m` viivana, sadetunnit korostettuna |
| Viikonpäivä x kellonaika -lämpökartta | `day_of_week` x `hour`, arvona `total_visitors`-keskiarvo |
| Sään vaikutus | Hajontakuvio `temperature_2m` vs. päivän kävijät, väri `weathercode_str` mukaan |
| Sateen vaikutus | Vertailu `is_precipitation` True vs. False, keskimääräinen kävijämäärä tunnissa |
| Kapasiteetin käyttöaste | `venue_capacity_utilization` ajassa, raja-arvo 100 % |
| Liput vs. kävijät | Päivätaso, `daily_tickets_sold` ja `daily_total_visitors` |
| Pyhäpäivien vaikutus | `is_holiday` ja `holiday_name` merkintöinä aikasarjassa |
| Jalankulku ja pyöräily | `total_site_flow`, huomioi luvut 7.1 ja 7.2 |
| Ennuste vs. historia | Historia `venue_N_features.csv`, ennuste `forecast_visitors_*.csv` luottamusväleineen |

### 8.4 Tekniset reunaehdot

- Ei tietokantaa, kaikki data on tiedostoissa
- Nykyinen dashboard on Flask + Plotly portissa 2026 (`app/`), lukee samat tiedostot
- Uusi sovellus voi olla täysin erillinen, se ei kirjoita mitään repon dataan
- Bool-arvot ovat CSV:ssä merkkijonoina `True`/`False`
- Desimaalierotin on piste, koodaus UTF-8, skandit sarakearvoissa (`holiday_name`, `weathercode_str` ei)
