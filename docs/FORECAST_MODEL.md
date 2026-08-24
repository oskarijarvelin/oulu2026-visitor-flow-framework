# Ennustemallit

Tämä dokumentti kuvaa `packages/forecast`-osion kaksi mallia: niiden rakenteen,
piirteet, vahvuudet, heikkoudet ja sen, milloin ennustetta ei pidä uskoa.

Pohjana on `FRAMEWORK_PLAN.md` luku 8, mutta **kaikki tässä esitetyt luvut ovat
mitattuja**, eivät arvioita. Ne on tuotettu ajolla

```bash
python -m ovf_forecast run
```

aineistolla, jonka viimeisin havaittu päivä on **2026-05-22**. Luvut päivittyvät
jokaisella ajolla tiedostoon `data/forecasts/latest/venue_{id}/metrics.json`; tämä
dokumentti on tilannekuva 2026-08-24 ajetusta versiosta.

---

## 1. Yhteenveto: mikä voittaa

| Venue | Malli | MAE 1-7 vrk | Voittaa seasonal_naive | Voittaa moving_average_28d |
| --- | --- | --- | --- | --- |
| 1 Pekuri | **baseline** | **178,5** | kyllä (214,9) | kyllä (192,4) |
| 1 Pekuri | prophet_xgb | 198,7 | kyllä (214,9) | **ei** (192,4) |
| 2 Kaupungintalo | **baseline** | 90,1 | kyllä (100,6) | kyllä (92,5) |
| 2 Kaupungintalo | prophet_xgb | **87,1** | kyllä (100,6) | kyllä (92,5) |

**Tuotantomalli on `baseline`.** Se on ainoa malli, joka voittaa molemmat
vertailukohdat molemmilla venueilla ja kaikilla kolmella horisonttikorilla.

`prophet_xgb` on venue 2:lla hieman tarkempi (87,1 vs. 90,1, ero 3 %) mutta venue 1:llä
selvästi huonompi (198,7 vs. 178,5, ero 11 %). Suunnitelman luvun 8.1 vaihtokriteeri on
"yli 10 % pienempi MAE kolmella peräkkäisellä ajolla". Se ei täyty, joten yksinkertainen
malli pidetään.

**Rehellisyysvaroitus.** Kaikkien mallien MAE on suuri suhteessa tasoon: venue 1:n
keskimääräinen päivä on noin 450 kävijää ja paras MAE on 178, eli noin 40 % tasosta.
sMAPE on venue 2:lla 55-58 %. Nämä ennusteet kertovat viikkorytmin ja karkean tason,
eivät yksittäisen päivän kävijämäärää. Katso luku 7.

---

## 2. Yhteinen rakenne

Molemmat mallit ennustavat **päivätasolla**. Tuntitaso ja epävarmuus tulevat yhteisistä
komponenteista. Tämä on tarkoituksellinen suunnitteluvalinta kahdesta syystä: mallit ovat
vertailukelpoisia, ja tuntiennusteiden summa on täsmälleen päiväennuste.

```
data/processed/  ->  dataset.build()  ->  features.build_daily()  ->  malli  ->  p50 päivätasolla
                                                                  \
                                      profile.build()  ------------>  tuntiprofiili  ->  tuntitason p50
                                                                  \
                                      backtest.run()  ------------>  suhteelliset virheet  ->  p10 / p90
```

Yhteinen rajapinta:

```python
class ForecastModel(Protocol):
    name: str
    def fit(self, daily: pd.DataFrame) -> None: ...
    def predict(self, future: pd.DataFrame) -> pd.Series: ...
```

`visitors_in` ja `visitors_out` **ei ennusteta erikseen**. Nykyisessä sovelluksessa ne
ovat kolme erillistä mallia, jolloin 23.5.2026 kohdalla lukee in 63,99, out 52,12 ja
total 191,31, eivätkä ne summaudu. Tässä ennustetaan vain `visitors_total`.

---

## 3. Perusmalli `baseline`

### 3.1 Kerros 1: päivätason taso

`sklearn.ensemble.HistGradientBoostingRegressor(loss="poisson")`, kohteena
`visitors_total` päivätasolla, venuekohtaisesti.

Poisson-tappio valittiin koska kohde on laskurisuure: jakauma on oikealle vino ja
ennusteen on oltava ei-negatiivinen. Poisson takaa positiivisuuden rakenteellisesti,
ilman jälkikäteistä nollaanleikkausta ja ilman log-muunnoksen takaisinmuunnosharhaa.

Hyperparametrit (`models/baseline.py`): `learning_rate=0.05`, `max_iter=400`,
`max_depth=4`, `max_leaf_nodes=15`, `min_samples_leaf=8`, `l2_regularization=1.0`,
`early_stopping=False`, `random_state=20260101`.

`early_stopping` on pois päältä, koska 120 rivin aikasarjasta lohkaistu satunnainen
validointijoukko olisi sekä pieni että väärin muodostettu. Mallin valinta tehdään
rolling origin -backtestillä, ei sisäisellä splitillä.

Hyperparametrit ovat tarkoituksella vaatimattomat. Viisi eri asetusyhdistelmää mitattiin
backtestillä, ja MAE liikkui venue 1:llä välillä 172,7-189,2 ja venue 2:lla 90,1-95,1.
Ero on pienempi kuin kahdeksan origon backtestin kohinataso, joten pidemmälle viritys
olisi hyperparametrien ylisovittamista backtestiin.

#### Piirteet

| Ryhmä | Piirteet |
| --- | --- |
| Kalenteri | `day_of_week` (kategorinen), `is_weekend`, `is_holiday`, `days_before_next_holiday` (katkaistu 14:ään), `is_last_workday_before_holiday`, `month`, `week_of_year` |
| Vuodenaika | `sin(2πd/365)`, `cos(2πd/365)`, `sin(4πd/365)`, `cos(4πd/365)` |
| Trendi | `days_since_start` |
| Sää | `temp_mean`, `temp_max`, `precip_sum`, `precip_hours`, `wind_mean`, `is_rainy_day`, `weather_group` (kategorinen: clear/cloudy/rain/snow/other) |
| Taso | `level_7d`, `level_28d`, `dow_index_28d` |

Lippudataa ei käytetä piirteenä, koska sitä ei ole tulevaisuudelle saatavilla.

#### Kriittinen suunnitteluvalinta: ei autoregressiivisiä viiveitä

Mallissa **ei ole viivepiirteitä, jotka päivittyisivät ennusteen edetessä**.

- **Koulutuksessa** `level_7d` ja `level_28d` ovat kausaalisia liukuvia keskiarvoja:
  rivi päivälle *t* näkee päivät *t-7…t-1*, ei koskaan omaa päiväänsä.
- **Ennustettaessa** ne lasketaan kerran origossa ja pysyvät vakioina koko 30
  vuorokauden horisontin ajan.

Nykyinen sovellus syöttää omat ennusteensa takaisin `lag_24h`- ja `lag_168h`-piirteisiin
(`modeling.py`, `history_values.append(final_prediction)`), jolloin virhe kumuloituu
horisontin pidentyessä. Tässä 30 vrk ennuste **ei ole 30 kertaa ketjutettu yhden päivän
ennuste**, vaan yksi origosta tehty ennuste.

`dow_index_28d` on ainoa tasopiirre, joka vaihtelee horisontin sisällä: se on kyseisen
viikonpäivän keskiarvon suhde 28 vrk keskiarvoon, joten se seuraa kohdepäivän
viikonpäivää.

Tämä on testattu: `test_features.py::test_future_features_ignore_observations_after_the_origin`
korruptoi kaikki origon jälkeiset havainnot ja vaatii, ettei yksikään piirre muutu.

#### Aloitusnollien poisto

Venue 1 ei raportoi mitään ennen 2026-01-22 ja venue 2 ennen 2026-01-08. Kyse on
asentamattomasta sensorista, ei tyhjästä museosta. Näiden päivien nollat pudotetaan
ennen koulutusta (`dataset.venue_history`), koska muuten ne vetäisivät kaikki
tasopiirteet alaspäin. Venue 1:lle jää 121 ja venue 2:lle 135 koulutuspäivää.

#### Mitatut piirretärkeydet

Permutaatiotärkeys, MAE-asteikolla, koko koulutusjoukossa:

| Venue | Kolme tärkeintä | Käytännössä hyödyttömät |
| --- | --- | --- |
| 1 Pekuri | `day_of_week` 136,6 · `level_7d` 48,8 · `wind_mean` 27,1 | `month`, `is_holiday`, `is_last_workday_before_holiday`, `is_rainy_day` |
| 2 Kaupungintalo | `level_28d` 49,2 · `day_of_week` 44,4 · `year_sin` 37,3 | `is_holiday`, `is_last_workday_before_holiday`, `is_rainy_day` |

Huomionarvoista: **viikonpäivä ja taso kantavat lähes kaiken signaalin.** Sää on
kolmanneksi tärkein, mutta `wind_mean` nousee `temp_mean`-piirteen ohi, mikä on
epäilyttävää — tuulisuus korreloi Oulussa vuodenajan kanssa, joten piirre todennäköisesti
toimii kausiproxynä eikä mekanismina. `is_holiday` ei tuota mitään, koska aineistossa on
vain kourallinen pyhiä.

### 3.2 Kerros 2: tuntiprofiili (yhteinen molemmille malleille)

`profile.py`. Päiväennuste jaetaan tunneille empiirisellä profiililla:

```
share[venue][dow][hour] = keskiarvo osuuksista visitors_hour / visitors_day
                          niiltä päiviltä joilla visitors_day > 0, viimeiset 8 viikkoa
```

Kutistus kohti viikonpäivien yhteistä profiilia, `k = 4`:

```
share_final = (n_dow * share_dow + k * share_all) / (n_dow + k)
```

Kahdeksan viikkoa antaa vain kahdeksan havaintoa per viikonpäivä, joten yksittäinen
poikkeava lauantai hallitsisi ilman kutistusta.

**Aukioloajat johdetaan datasta**: tunti katsotaan suljetuksi jos sen ei-nolla-osuus
viimeisen 8 viikon aikana on alle 5 %. Näiden osuus pakotetaan nollaan ennen
normalisointia. Mitatut aukiolotunnit:

| Venue | Avoinna (paikallista aikaa) |
| --- | --- |
| 1 Pekuri | 07-19 |
| 2 Kaupungintalo | 07-21 |

Lopuksi normalisointi niin että päivän osuuksien summa on tasan 1, jolloin
`tuntiennuste = daily_p50 * share_final` summautuu täsmälleen päiväennusteeseen.

**Kesäaika.** Paikallisessa päivässä on 23 tai 25 tuntia siirtymäpäivinä. Osuudet
normalisoidaan sille tuntijoukolle, joka päivällä oikeasti on, joten summa on 1 myös
näinä kahtena päivänä vuodessa.

Invariantti on testattu vietyjä tiedostoja vasten, ei muistinvaraisia lukuja vasten
(`test_cli.py::test_hourly_forecasts_sum_to_the_daily_forecast`). Pyöristys käyttää
suurimman jäännöksen menetelmää, joten summa täsmää myös CSV:n kolmen desimaalin
tarkkuudella.

### 3.3 Kerros 3: epävarmuus (yhteinen molemmille malleille)

`intervals.py`. Ennustevälit tulevat **mitatusta backtest-virheestä**, eivät mallin
sisäisistä oletuksista.

1. Rolling origin -backtest (luku 5).
2. Suhteellinen virhe `r = y_true / y_pred` jokaiselle (origo, horisontti) -parille.
3. `r`-jakauman kvantiilit q10 ja q90 horisonttikoreittain: 1-7, 8-14, 15-30.
4. `p10 = p50 * q10(h)`, `p90 = p50 * q90(h)`.

Suhteellinen muotoilu on tarkoituksellinen: virheen hajonta skaalautuu tason mukana.
Absoluuttinen virhejakauma antaisi hiljaisille päiville liian leveät ja vilkkaille liian
kapeat välit. Tuntitasolla käytetään samaa suhteellista leveyttä kuin päivätasolla.

Kaksi suojausta:

- Rivit, joilla `y_pred < 1.0`, jätetään pois kvantiililaskennasta. Nollalla jakaminen
  kertoisi enemmän ennusteen pienuudesta kuin mallin hajonnasta.
- Mediaanin on oltava oman välinsä sisällä: `q10 ≤ 1 ≤ q90` pakotetaan. Systemaattisen
  harhan raportoi `bias`-mittari, sen ei kuulu tuottaa `p10 > p50` -riviä tiedostoon.

#### Mitatut välikertoimet

| Venue | Malli | 1-7 | 8-14 | 15-30 |
| --- | --- | --- | --- | --- |
| 1 | baseline | 0,52 - 1,76 | 0,55 - 1,71 | 0,50 - 1,50 |
| 1 | prophet_xgb | 0,51 - 1,37 | 0,57 - 1,40 | 0,58 - 1,68 |
| 2 | baseline | 0,32 - 2,16 | 0,36 - 1,96 | 0,32 - 2,27 |
| 2 | prophet_xgb | 0,28 - 1,91 | 0,35 - 1,58 | 0,24 - 1,98 |

**Nämä välit ovat leveitä.** Venue 2:n ennuste 150 kävijää tarkoittaa väliä 47-324. Se
on rehellinen kuvaus siitä, mitä 4,5 kuukauden aineistolla pystyy sanomaan, mutta se
tarkoittaa myös ettei ennustetta voi käyttää tarkkaan resurssointiin.

Huomaa, että päivätason väli lasketaan **päivätasolla**, ei 24 tuntivälin summana.
Nykyisessä sovelluksessa summaus tuottaa absurdeja välejä, esimerkiksi ennuste 29
kävijää välillä 0-502.

---

## 4. Vertailumalli `prophet_xgb`

### 4.1 Rakenne

1. **Prophet** päivätason kohteeseen: trendi + viikkokausi + vuosikausi + pyhäpäivät +
   sääregressorit (`temp_mean`, `precip_sum`, `wind_mean`).
2. **XGBoost** Prophetin **residuaaleihin**, samoilla kalenteri- ja sääpiirteillä kuin
   perusmalli.
3. Lopullinen ennuste `prophet_yhat + xgb_residual`, leikattuna nollaan.
4. Tuntitaso ja epävarmuus samoista yhteisistä kerroksista 2 ja 3.

Prophetin omia `yhat_lower` ja `yhat_upper` -arvoja **ei käytetä**: ne eivät sisällä
XGBoost-vaiheen epävarmuutta lainkaan.

### 4.2 Vuosikausikomponentti: mitattu ongelma ja sen ratkaisu

Suunnitelma määrittelee vuosikauden osaksi mallia. 4,5 kuukauden aineistossa
vuosikautta ei kuitenkaan voi identifioida, ja pakotettuna se hajottaa ennusteen.

Mitattu venue 1:llä, origo 2026-04-24:

| Vuosikausi | Prophetin `yearly`-komponentti päivälle 30 | MAE 15-30 vrk |
| --- | --- | --- |
| Pakotettu päälle (fourier 3) | **+742 kävijää** | **774,0** |
| Pois päältä | ei komponenttia | **179,9** |

Komponentti sovittaa kohinaa koulutusikkunan sisällä ja ekstrapoloi sen suoraan ulos.
Päivän 30 ennuste oli 1231 kävijää, kun toteutunut taso oli noin 457.

**Ratkaisu**: malli pyytää vuosikautta, mutta säilyttää Prophetin oman `auto`-säännön,
joka kytkee vuosikauden pois alle kahden vuoden historialla
(`MIN_YEARLY_SEASONALITY_DAYS = 730`). Kun sääntö laukeaa, ajo lokittaa sen
eksplisiittisesti. Kahden vuoden aineistolla komponentti kytkeytyy itsestään päälle.

Vastaavasti Fourier-aste on 3 (Prophetin oletus on 10) ja `seasonality_prior_scale` on
5,0 (oletus 10,0). Molemmat on kiristetty juuri ylisovittamisen takia.

### 4.3 Mitä nykyisestä toteutuksesta ei toisteta

| Nykyinen | Tässä | Miksi |
| --- | --- | --- |
| Tuntitason Prophet, `daily_seasonality=True` **ja** oma `hourly_pattern` `period=1` | Päivätason Prophet, tuntitaso profiilista | Kaksi päällekkäistä vuorokausikautta on kollineaarinen ja tekee komponenteista tulkitsemattomia |
| Ennusteväli: Prophetin väli + piste-residuaali | Empiiriset backtest-kvantiilit | Prophetin väli ei sisällä XGBoostin epävarmuutta |
| Päivätason väli = 24 tuntivälin **summa** | Väli lasketaan päivätasolla | Summaus tuottaa absurdeja välejä, esim. 29 kävijää välillä 0-502 |
| `in`, `out` ja `total` erillisinä malleina | Yksi malli `total`ille | Erilliset mallit eivät summaudu |
| Ennusteet takaisin viivepiirteisiin | Ei rekursiota | Virhe kumuloituu horisontin pidentyessä |
| Yksi 80/20 aikajakosplit | Rolling origin -backtest | Yksi splitti antaa yhden havainnon mallin laadusta |
| Mediaanitäyttö puuttuville piirteille | NaN natiivisti tuettu | Mediaanitäyttö sekoittaa tammikuun ja toukokuun |

### 4.4 Asennus

`prophet_xgb` vaatii erillisen riippuvuusryhmän, koska Prophet vetää mukanaan
cmdstanin:

```bash
pip install -e ".[prophet]"
```

macOS tarvitsee lisäksi OpenMP-ajonaikaisen kirjaston XGBoostille:

```bash
brew install libomp
```

**Jos ryhmää ei ole asennettu, `prophet_xgb` ohitetaan selkeällä varoituksella eikä ajo
kaadu.** Ohitus kattaa myös tilanteen, jossa xgboost on asennettu mutta ei lataudu
(puuttuva libomp): molemmat tarkoittavat kutsujalle samaa asiaa. Ohitetut mallit
kirjataan manifestin kenttään `skipped_models`.

---

## 5. Validointi

### 5.1 Rolling origin -backtest

```
origo o = viimeisin havaittu päivä miinus (n * 7 vrk),  n = 1..N
koulutus = kaikki data <= o
ennuste  = o+1 .. o+30
```

Vaatimus: vähintään 60 päivää koulutusdataa per origo. Tällä aineistolla se on sitova
rajoite, ei `max_origins`:

| Venue | Koulutuspäiviä | Origoja | Backtest-ikkuna |
| --- | --- | --- | --- |
| 1 Pekuri | 121 | 8 | 2026-03-28 … 2026-05-22 |
| 2 Kaupungintalo | 135 | 10 | 2026-03-14 … 2026-05-22 |

Suunnitelma odotti noin 12 origoa; aloitusnollien poisto vie venue 1:ltä kolme viikkoa
alusta, joten origoja on kahdeksan. Se on suunnitelman minimi, ei sen tavoite.

Kaksi yksityiskohtaa pitää harjoituksen rehellisenä:

1. **Koulutus loppuu origoon**, myös tasopiirteiden ja tuntiprofiilin osalta.
2. **Sää degradoituu klimatologiaksi päivän 16 jälkeen myös backtestissä**, täsmälleen
   kuten tuotannossa. Pitkän horisontin luvut on siis mitattu samalla tasoitetulla
   säällä, jolla ne ajetaan.

Yksi tunnettu optimismi jää: horisonteilla 1-16 backtest käyttää **toteutunutta** säätä,
kun tuotanto käyttää **sääennustetta**. Sääennusteen oma virhe ei siis näy mitatuissa
luvuissa.

### 5.2 Peittävyys mitataan origo kerrallaan ulos jättäen

`backtest.csv`-tiedoston ja `coverage_80`-mittarin `p10`/`p90` lasketaan kvantiileilla,
jotka on sovitettu **ilman sitä origoa, jota ne pisteyttävät**. Jos välit sovitettaisiin
samoihin riveihin joita ne mittaavat, peittävyys olisi 80 % määritelmän nojalla eikä
kertoisi mitään. Tuotantoennusteen välit käyttävät kaikkia origoja.
`metrics.json` merkitsee tämän kenttään `coverage_method`.

### 5.3 Mitatut mittarit

#### Venue 1, Pekuri — origo 2026-05-22, 121 koulutuspäivää, 8 origoa

| Malli | Horisontti | MAE | RMSE | sMAPE | Bias | Peittävyys 80 % | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **baseline** | 1-7 | **178,5** | 227,5 | 38,3 | +42,8 | 0,75 | 56 |
| **baseline** | 8-14 | 176,2 | 221,8 | 36,7 | +29,6 | 0,71 | 49 |
| **baseline** | 15-30 | **178,9** | 222,6 | 37,0 | +72,6 | 0,76 | 85 |
| prophet_xgb | 1-7 | 198,7 | 250,9 | 40,6 | +83,4 | 0,77 | 56 |
| prophet_xgb | 8-14 | **167,2** | 220,9 | 34,7 | +43,2 | 0,73 | 49 |
| prophet_xgb | 15-30 | 179,9 | 232,6 | 37,3 | +32,4 | 0,76 | 85 |
| seasonal_naive | 1-7 | 214,9 | 279,2 | 43,2 | +38,6 | 0,79 | 56 |
| seasonal_naive | 8-14 | 197,4 | 263,6 | 39,4 | +12,8 | 0,78 | 49 |
| seasonal_naive | 15-30 | 179,2 | 234,0 | 36,7 | +17,8 | 0,74 | 85 |
| moving_average_28d | 1-7 | 192,4 | 225,6 | 40,8 | +45,7 | 0,75 | 56 |
| moving_average_28d | 8-14 | 194,0 | 229,8 | 41,3 | +43,8 | 0,76 | 49 |
| moving_average_28d | 15-30 | 211,0 | 240,7 | 44,1 | +54,2 | 0,81 | 85 |

#### Venue 2, Kaupungintalo — origo 2026-05-22, 135 koulutuspäivää, 10 origoa

| Malli | Horisontti | MAE | RMSE | sMAPE | Bias | Peittävyys 80 % | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 1-7 | 90,1 | 119,5 | 57,9 | +7,2 | 0,77 | 70 |
| baseline | 8-14 | 83,6 | 109,9 | 55,5 | +10,7 | 0,79 | 63 |
| baseline | 15-30 | 84,3 | 114,1 | 56,7 | +15,6 | 0,77 | 117 |
| **prophet_xgb** | 1-7 | **87,1** | 114,0 | 64,5 | +14,7 | 0,71 | 70 |
| **prophet_xgb** | 8-14 | **77,8** | 101,6 | 62,4 | +8,3 | 0,71 | 63 |
| **prophet_xgb** | 15-30 | **79,7** | 108,2 | 66,6 | -4,9 | 0,68 | 117 |
| seasonal_naive | 1-7 | 100,6 | 128,4 | 69,8 | -2,7 | 0,74 | 70 |
| seasonal_naive | 8-14 | 99,6 | 136,8 | 66,7 | +0,9 | 0,73 | 63 |
| seasonal_naive | 15-30 | 107,0 | 139,3 | 72,4 | +13,2 | 0,77 | 117 |
| moving_average_28d | 1-7 | 92,5 | 116,0 | 61,4 | -2,5 | 0,77 | 70 |
| moving_average_28d | 8-14 | 91,5 | 114,2 | 61,8 | +1,5 | 0,76 | 63 |
| moving_average_28d | 15-30 | 87,3 | 107,5 | 61,1 | +22,7 | 0,77 | 117 |

### 5.4 Mitä luvuista pitää lukea

**Vertailukohdat ovat lähellä.** `moving_average_28d` — pelkkä 28 päivän keskiarvo — on
venue 1:llä horisontilla 1-7 vain 8 % huonompi kuin perusmalli ja venue 2:lla 3 %
huonompi. Perusmalli voittaa, mutta ei murskaavasti. Suurin osa mallin arvosta on
viikonpäivärytmissä, jonka `moving_average` sivuuttaa kokonaan.

**Kaikki mallit yliarvioivat.** Bias on positiivinen lähes kaikkialla, venue 1:llä
horisontilla 15-30 jopa +72,6. Syy on rakenteellinen: kävijämäärä laskee tammikuun 653
päiväkeskiarvosta toukokuun 484:ään, ja origoon lukittu taso ei seuraa laskua.
Puumalli ei myöskään ekstrapoloi trendiä: `days_since_start` saturoituu viimeiseen
koulutusarvoonsa.

**seasonal_naive voittaa pitkällä horisontilla venue 1:llä.** Horisontilla 15-30 se on
179,2 kun perusmalli on 178,9 — käytännössä tasapeli. Kolmen viikon päähän "sama
viikonpäivä viimeksi havaittuna" on yhtä hyvä kuin gradient boosting.

**prophet_xgb on epäjohdonmukainen.** Se on venue 2:n paras malli kaikilla horisonteilla
ja venue 1:n huonoin lähihorisontilla. Kahdella venuella ja kahdeksalla origolla ei ole
mahdollista sanoa, kumpi havainto on signaalia.

---

## 6. Sää yli 16 vuorokauden

Open-Meteo antaa enintään 16 vuorokautta ennustetta, mutta horisontti on 30.

| Vuorokaudet | Lähde | `weather_source` |
| --- | --- | --- |
| 1-16 | `data/processed/weather_daily.csv` | `forecast` |
| 17-30 | `data/reference/climatology/venue_{id}.csv` | `climatology` |

Jokaisella ennusterivillä on `weather_source`-sarake. Käyttöliittymän on merkittävä
`climatology`-rivit näkyvästi: keskiarvosää tuottaa keskiarvokävijämäärän, joten
vuorokausien 17-30 ennusteet ovat systemaattisesti liian tasaisia.

Kolme yksityiskohtaa klimatologian käsittelyssä:

- **`is_rainy_day` jätetään puuttuvaksi**, ei arvata. Sataako päivänä 25, on aidosti
  tuntematon asia. Molemmat mallit lukevat NaN:n natiivisti, joten "en tiedä" ei maksa
  mitään, kun taas nollan tai ykkösen keksiminen maksaisi tarkkuutta.
- **`weathercode_str` on `overcast`** (tai `slight_snow_fall` pakkaspuolella).
  Kymmenen vuoden keskiarvo ei ole otos päiväjakaumasta: kymmenen kesäkuun keskiarvo
  jättää joka päivälle 2 mm tihkua, joten samat sadekynnykset kuin havainnoille
  luokittelisivat koko horisontin loppupuolen sateiseksi. Keskimääräinen oululainen
  päivä on pilvinen, ja sitä nämä rivit väittävät.
- **`precip_hours`** on niiden tuntien määrä, joiden klimatologinen keskisade on
  vähintään 0,1 mm. Se on approksimaatio, ei mitattu suure.

**Datan ikä.** Tässä ajossa kävijädata päättyy 2026-05-22 mutta säädata ulottuu
2026-09-07 asti. Horisontin päivät 1-16 saavat siis `weather_source = "forecast"`,
vaikka kyseisten päivien sää on tässä aineistossa jo toteutunutta arkistodataa.
Sarakkeen merkitys on "dynaaminen sää vs. tasoitettu klimatologia", ja se on säilytetty
sellaisenaan; ajo varoittaa erikseen siitä, että origo on 94 päivää vanha.

---

## 7. Milloin ennustetta ei pidä uskoa

Nämä on kirjattu myös jokaisen venuen `metrics.json`-tiedoston kenttään `do_not_trust`.

1. **Horisontti yli 14 vuorokautta.** Sää on klimatologiaa ja taso on lukittu origoon.
2. **Päivä jolla on ohjelmistoa tai tapahtuma, jota malli ei tunne.** Tämä on suurin
   yksittäinen virhelähde. Malli näkee menneet piikit datassa mutta ei tiedä tulevista.
3. **Ensimmäiset kaksi viikkoa uuden venuen tai uuden sensorin käyttöönotosta.**
4. **Jakso jolla ingest-manifesti raportoi `degraded`-lähteitä.**
5. **Koulujen loma-ajat ja juhannus**, joista aineistossa on korkeintaan yksi havainto.
   Tämän ajon horisontti sisältää juhannuksen (2026-06-19 ja 2026-06-20) horisontilla
   28-29, eli klimatologiasään alueella. Näihin kahteen päivään ei pidä luottaa
   lainkaan.
6. **Kaikki tilanteet joissa peittävyys on jäänyt alle 0,70** viimeisimmässä
   backtestissä. Tässä ajossa `prophet_xgb` venue 2:lla horisontilla 15-30 on 0,68.
7. **Kun `metrics.json`-tiedoston `warnings` ei ole tyhjä.** Tässä ajossa molemmilla
   venueilla on varoitus siitä, että viimeisin havaittu päivä on 94 päivää ennen ajoa.

---

## 8. Heikkoudet

### 8.1 Perusmalli

1. **Ei opi vuosikausivaihtelua.** Aineistossa ei ole yhtään täyttä vuotta.
   Vuodenaikapiirteet ovat käytännössä trendin jatketta; `year_sin` saa korkean
   permutaatiotärkeyden (25,6 ja 37,3), mutta se mittaa tässä kevään kulkua, ei
   vuosikautta.
2. **Kiinteä taso koko horisontille.** `level_28d` ei päivity ennusteen edetessä. Tämä
   näkyy mitattuna: venue 1:n bias kasvaa +42,8:sta (1-7) +72,6:een (15-30).
3. **Koulutuksen ja ennusteen tasopiirteet eivät ole symmetrisiä.** Koulutuksessa
   `level_7d` on aina täsmälleen edellisen viikon keskiarvo, eli yhtä tuore kuin
   horisontilla 1. Ennustettaessa se on horisontilla 30 kuukauden vanha. Malli oppii
   siis luottamaan tasoon enemmän kuin pitkällä horisontilla olisi perusteltua.
4. **Ei osaa ennakoida tapahtumia.** Konsertti tai näyttelyn avajaiset näkyvät datassa
   piikkinä, mutta malli ei tiedä tulevista.
5. **Sään vaikutus on korrelaatio, ei mekanismi.** `wind_mean` on venue 1:n kolmanneksi
   tärkein piirre, mikä on lähes varmasti kausiproxy eikä syy-yhteys.
6. **Tuntiprofiili on staattinen.** Sama viikonpäiväprofiili koko horisontille. Ei
   reagoi poikkeaviin aukioloaikoihin.
7. **Ennustevälit lepäävät 8-10 origon varassa.** q10 ja q90 lasketaan 49-117
   havainnosta koria kohti. Se on ohut otos kvantiileille.
8. **Nolla-inflaatio.** Noin 60 % tunneista on nollia. Päivätasolla ongelma on pieni,
   mutta profiilin reunatunnit (venue 1 klo 7 ja 19) ovat epävakaita.
9. **Puumalli ei ekstrapoloi.** Jos kävijämäärä lähtee aitoon kasvuun, `days_since_start`
   ei vie ennustetta koulutusdatan maksimin yli.

### 8.2 Vertailumalli

1. **Raskas asennus.** Prophet vaatii cmdstanin, XGBoost macOS:llä libompin.
2. **Vuosikausi ei ole identifioitavissa.** Mitattu luvussa 4.2: pakotettuna MAE 15-30
   nousee 179,9:stä 774,0:aan.
3. **Additiivisuusoletus.** Sade vaikuttaa lauantaihin eri tavalla kuin tiistaihin.
   Prophet ei mallinna interaktioita; XGBoost-vaihe voi korjata osan tästä.
4. **Kaksi virhelähdettä ketjussa.** Jos Prophet on systemaattisesti pielessä, XGBoost
   oppii korjaamaan sen samasta pienestä aineistosta.
5. **Hitaampi.** Koko ajo Prophetin kanssa 22 s, ilman sitä 17 s. Backtestissä 8-10
   origoa kertaa kaksi venueta tarkoittaa 20 Prophet-sovitusta.
6. **Epäjohdonmukainen venueiden välillä**, katso luku 5.4.

---

## 9. Tuotokset

```
data/forecasts/latest/manifest.json
data/forecasts/latest/venue_{id}/daily_30d.csv      # 30 vrk x 2 mallia = 60 riviä
data/forecasts/latest/venue_{id}/hourly_7d.csv      # 7 vrk x 24 h x 2 mallia = 336 riviä
data/forecasts/latest/venue_{id}/metrics.json
data/forecasts/latest/venue_{id}/backtest.csv
data/forecasts/{YYYY-MM-DD}/...                     # arkistokopio samasta rakenteesta
```

Sarakkeet on kuvattu `FRAMEWORK_PLAN.md` luvussa 4.3.

**Determinismi.** Kaikilla malleilla on kiinteä `random_state`, mikään ei sample'aa, ja
ainoa kahden ajon välillä muuttuva arvo on `generated_at`. Tämä on testattu
(`test_cli.py::test_two_runs_differ_only_in_the_timestamp`). `--as-of`-lippu lukitsee
myös aikaleiman, jolloin kaksi ajoa tuottavat tavulleen identtiset tiedostot.

---

## 10. Komennot

```bash
python -m ovf_forecast run                      # molemmat mallit, kaikki venuet
python -m ovf_forecast run --model baseline     # vain perusmalli
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12    # pelkkä validointi, ei kirjoiteta mitään
python -m ovf_forecast report                   # tulostaa metrics.json luettavana
```

Paluuarvo 0 kun kaikki ok, 1 kun jokin venue epäonnistui, 2 kun mitään ei syntynyt.
