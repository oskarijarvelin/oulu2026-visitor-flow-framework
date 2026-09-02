# Ennusteiden arviointi

Miten `python -m ovf_forecast evaluate` ajetaan, miten sen tulokset luetaan ja mitä
niistä **ei** voi päätellä.

Tämä dokumentti täydentää lukua `docs/FORECAST_MODEL.md` luku 5. Siinä missä
`backtest` mittaa mallia liukuvilla origoilla ja tuottaa tuotannon ennustevälit,
`evaluate` vastaa yhteen kysymykseen kerrallaan: **kouluta tähän päivään asti, ennusta
tämä jakso, kerro osuiko se ja onko ero vertailukohtaan todellinen.**

Kysymys on tason ennustaminen. Kuukauden hiljaisimpien päivien *järjestys* on eri
kysymys, ja sillä on oma työkalunsa ja oma mittauksensa: `docs/QUIET_DAYS.md`.

---

## 1. Nopea aloitus

```bash
python -m ovf_forecast evaluate --test 2026-04
```

Kouluttaa kaiken 31.3.2026 asti saatavilla olevan datan, ennustaa huhtikuun, vertaa
toteumaan ja tulostaa verdiktin yhtenä kappaleena. Tulokset tallentuvat hakemistoon
`data/evaluations/`.

Koko kuukausisweep, viisi ikkunaa ja niiden kooste:

```bash
python -m ovf_forecast evaluate --sweep monthly --from 2026-04 --to 2026-08 --models baseline
```

Kestää noin minuutin ilman prophetia.

---

## 2. Komennot

| Komento | Mitä tekee |
| --- | --- |
| `evaluate --train-end 2026-03-31 --test 2026-04-01:2026-04-30` | Yksi ikkuna, eksplisiittiset rajat |
| `evaluate --test 2026-04` | Sama lyhenteenä: origo 31.3., testijakso koko huhtikuu |
| `evaluate --test 2026-04-15` | Yhden päivän testijakso |
| `evaluate --sweep monthly --from 2026-04 --to 2026-08` | Yksi ikkuna per kuukausi + kooste |
| `evaluate --sweep rolling --step 14 --horizon 30` | Origo siirtyy 14 vrk välein |
| `evaluate report --id <run_id>` | Tulostaa tallennetun raportin |
| `evaluate report --pooled` | Kokoaa kaikki tallennetut ajot yhdeksi verdiktiksi |
| `evaluate list` | Listaa tallennetut ajot |

### Valitsimet

| Valitsin | Oletus | Merkitys |
| --- | --- | --- |
| `--models` | `baseline,prophet_xgb` | Pilkulla erotettu lista. Prophet ohitetaan jos sitä ei ole asennettu |
| `--reference` | `best` | `best`, `seasonal_naive`, `moving_average_28d` tai `climatology_dow` |
| `--weather` | kaikki kolme | `perfect`, `operational`, `climatology` |
| `--train-window` | `all` | `all` tai päivien lukumäärä (liukuva ikkuna) |
| `--venue` | kaikki | Toistettava, esim. `--venue 1 --venue 2` |
| `--step`, `--horizon`, `--max-windows` | 14, 30, 12 | Vain `--sweep rolling` |
| `--resamples`, `--seed` | 10 000, 20260101 | Bootstrap |

Ajo on deterministinen. Sama syöte ja samat parametrit tuottavat tavulleen samat
tiedostot `data/evaluations/{run_id}/`-hakemistoon; ainoa muuttuva arvo on `index.json`in
`created_at`, joka on rekisterin eikä tuloksen kenttä.

---

## 3. Ikkunan määrittely

Ikkuna on kolme asiaa:

- **origin** — viimeinen päivä jonka data on käytettävissä koulutuksessa
- **test_start … test_end** — arvioitava jakso
- **train_window** — `all` tai päivien lukumäärä

`test_start` on **aina** `origin + 1 vrk`. Jos annat `--train-end` ja `--test` niin että
väliin jää rako, komento kieltäytyy. Rako pudottaisi hiljaisesti ne horisontit joilla
ennuste on huonoimmillaan, ja jokainen mittari näyttäisi paremmalta kuin se on.

---

## 4. Vuotokiellot

Arviointi on hyödytön jos ennuste on nähnyt testijakson dataa. Toteutuksessa on
kuusi sääntöä ja yksi tarkoituksellinen poikkeus.

1. **Malli koulutetaan vain datalla jonka päivä ≤ origo.**
2. **Tasopiirteet** (`level_7d`, `level_28d`, `dow_index_28d`) lasketaan origossa ja
   pysyvät vakiona koko testijakson.
3. **MASE-nimittäjä** — koulutusdatan oma seasonal naive -MAE — lasketaan vain
   koulutusikkunasta.
4. **Ennustevälien kvantiilit** tulevat sisäkkäisestä backtestistä, joka ajetaan
   kokonaan koulutusikkunan sisällä. Sen viimeisin sisäorigo on `origo − horisontti`,
   joten yksikään sisäennuste ei ylety testijaksoon. *Tämä on helpoin virhe tehdä:*
   tuotantoajo kalibroi välinsä tuoreimmasta datasta, ja arvioinnissa tuorein data on
   juuri se testijakso. Näin laskettu peittävyys olisi 80 % rakenteesta eikä mittauksesta.
5. **Vertailukohdat** lukevat vain päiviä ≤ origo. Erityisesti `seasonal_naive` **ei** ole
   `y[t−7]`: se toistaa origossa päättyneen viikon. Muodossa `y[t−7]` horisontti 8 lukisi
   jo testijakson toteumia.
6. **Kalenteritiedot** (viikonpäivät, pyhät) ovat sallittuja, koska ne tiedetään etukäteen.
7. **Lippudataa ei käytetä piirteenä**, koska sitä ei ole tulevaisuudelle.

Poikkeus on **sää**, ja se on nimenomaan se mitä kolme sään tilaa mittaavat; ks. luku 5.

Vuotokielto on testattu ulkoapäin: `packages/forecast/tests/test_evaluation_leakage.py`
ajaa arvioinnin, korvaa kaikki origon jälkeiset havainnot satunnaisluvuilla, ajaa
uudelleen ja vaatii bittitasolla identtiset ennusteet. `climatology`-tilassa myös sää
korvataan.

---

## 5. Sään kolme tilaa

Tuotannossa käytettävissä on sääennuste, ei toteutunut sää. Toteutuneella säällä
arviointi antaa liian hyvän tuloksen, klimatologialla liian huonon. Siksi jokainen
ikkuna ajetaan kolmesti.

| Tila | Sää testijaksolla | Tulkinta |
| --- | --- | --- |
| `perfect` | toteutunut koko jaksolta | **Yläraja**: mihin malli pystyisi jos sää tiedettäisiin |
| `operational` | toteutunut vrk 1–16, klimatologia vrk 17+ | **Realistisin arvio**, olettaa hyvän sääennusteen |
| `climatology` | klimatologia koko jaksolta | **Alaraja**: mihin malli pystyy ilman sääennustetta |

Verdikti lasketaan oletuksena `operational`-tilasta. Raportin luku 7 kertoo kaikkien
kolmen MAE:n ja niiden erotuksen: **perfectin ja climatologyn välinen ero on se osa mallin
osumatarkkuudesta joka lepää sään tuntemisen varassa.** Se on itsenäinen tulos ja
raportoidaan erikseen.

Vertailukohdat eivät lue säätä lainkaan, joten niiden ennuste on kaikissa kolmessa
tilassa sama. Se on tarkoitus: se tekee sään vaikutuksesta luettavan suoraan taulukosta.

**Parannus voi olla negatiivinen**, ja tällä aineistolla se on neljässä kymmenestä
venue–kuukausi-parista: malli ennustaa paremmin keskiarvosäällä kuin toteutuneella säällä.
Se ei ole mittausvirhe vaan tulos — mallin oppima sääriippuvuus ei yleisty kyseiseen
jaksoon — ja raportti merkitsee sen erikseen. Ks. `docs/FORECAST_MODEL.md` luku 5.5.

Neljättä tilaa `archived_forecast` — se sääennuste joka origossa oli oikeasti
saatavilla — ei ole toteutettu. Se olisi aidosti oikea vastaus tähän ongelmaan; ks.
luku 11.

---

## 6. Vertailukohdat

Kaikki kolme lasketaan aina, ja kaikki kolme raportoidaan.

| Nimi | Määritelmä |
| --- | --- |
| `seasonal_naive` | Origossa päättyneen 7 vrk jakson havainto samalta viikonpäivältä, toistettuna koko horisontille |
| `moving_average_28d` | Origoa edeltävien 28 päivän keskiarvo, vakio koko jakson |
| `climatology_dow` | Koulutusdatan viikonpäiväkohtainen keskiarvo, vakio kullekin viikonpäivälle |

**Päävertailukohta on oletuksena paras näistä kolmesta kyseisellä ikkunalla**, ei
`seasonal_naive`. Perustelu on aineistossa: nykyisellä datalla `climatology_dow` voittaa
`seasonal_naiven` useimmilla kuukausilla, joten kiinteä `seasonal_naive` olisi liian
helppo rima. `--reference` lukitsee halutessasi yhden.

### Mitatut vertailuluvut

Origo 2026-03-31, testi 2026-04-01 … 2026-04-30, `--train-window all`:

**Venue 1 (Pekuri).** Toteutunut summa 13 189, MASE-nimittäjä 141,18.

| Vertailukohta | MAE | RMSE | Bias | Ennustettu summa |
| --- | --- | --- | --- | --- |
| seasonal_naive | 129,50 | 158,12 | +66,10 | 15 172 |
| moving_average_28d | 197,61 | 219,80 | +138,22 | 17 336 |
| **climatology_dow** | **96,20** | 122,72 | +3,44 | 13 292 |

**Venue 2 (Kaupungintalo).** Toteutunut summa 3 791, MASE-nimittäjä 128,57.

| Vertailukohta | MAE | Ennustettu summa |
| --- | --- | --- |
| seasonal_naive | 138,57 | 7 656 |
| moving_average_28d | 88,16 | 5 802 |
| **climatology_dow** | **75,14** | 5 346 |

Nämä ovat hyväksymiskriteerejä, ja `test_evaluation_baselines.py` tarkistaa ne.

### Aloitusnollat: yksi tarkoituksellinen ero tuotantoon

Tuotantoajo (`venue_history`) poistaa venuen alusta yhtenäisen nollapäiväjakson: venue 1
ei raportoi mitään ennen 22.1.2026 eikä venue 2 ennen 8.1.2026, ja kyse on asentamattomasta
sensorista eikä museosta jossa ei käynyt kukaan.

**Arviointi ei poista niitä.** Syy on että koulutusikkuna on se jonka käyttäjä nimesi, ja
vasemman reunan hiljainen siirtäminen tekisi `--train-window all`ista jotain muuta kuin
miltä se näyttää. Ero on suuri: trimmattuna venue 1:n `climatology_dow` olisi huhtikuussa
164,73 eikä 96,20 ja MASE-nimittäjä 123,69 eikä 141,18.

Seuraus on kerrottava ääneen: **tammi–maaliskuun ikkunassa venue 1:n koulutusdatasta 21
päivää 90:stä on nollia.** Raportti kertoo luvun kohdassa 8, ja `--train-window`
rajaa ne pois:

```bash
python -m ovf_forecast evaluate --test 2026-04 --train-window 60
```

#### Nollat eivät jää alkuun

Tämä ei ole pelkkä tasoa laskeva haitta, ja arviointi paljasti miksi. Vuodenaikapiirre
`year_sin = sin(2π·doy/365)` on symmetrinen: se nousee tammikuusta huipulle huhtikuun
alussa ja laskee takaisin. **Tammikuun päivä ja kesäkuun päivä saavat siis saman arvon.**

Venue 1:n nollapäivät ovat 1.–21.1.2026, eli `year_sin` välillä 0,017–0,354; ensimmäinen
havaittu päivä 22.1. on 0,370. Puumalli oppii tästä säännön "`year_sin` ≤ 0,354 →
0 kävijää". Kesäkuussa `year_sin` laskee saman rajan alle 11.6. (doy 162, `year_sin`
0,3456 — sama arvo kuin 21.1.), ja **malli ennustaa loppukuulle nollaa.**

Mitattuna, origo 2026-05-31, venue 1, kesäkuun kokonaismäärä (toteuma 11 865):

| Koulutusikkuna | Nollapäiviä koulutuksessa | Kesäkuun ennuste | Lähes nollan päiviä |
| --- | --- | --- | --- |
| `all` (151 vrk) | 21 | **2 961** | 20 |
| `120` | 0 | 8 846 | 0 |
| `90` | 0 | 9 056 | 0 |

Sama ilmiö koskee mitä tahansa venueä jolla on nollajakso datan alussa. **Jos ennuste
romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa**, ja raportin
kohta 8 nimeää sen automaattisesti kun koulutusikkunassa on aloitusnollia.

---

## 7. Mittarit

Lasketaan venueittain, malleittain, sään tiloittain ja horisonttikoreittain
(1–7, 8–14, 15–30) sekä koko jaksolle (`all`).

| Mittari | Huomiot |
| --- | --- |
| **MAE** | Päämittari |
| RMSE | Rankaisee suuria virheitä |
| **MASE** | MAE / koulutusdatan seasonal naive -MAE. Vertailukelpoinen venueiden välillä |
| Bias | Keskivirhe etumerkillä (ennuste − toteuma) |
| **Pinball 0,1 / 0,5 / 0,9** | Oikea pistemäärä kvantiiliennusteelle |
| Peittävyys 80 % | Osuus toteumista p10–p90 välillä |
| sMAPE | **Merkitty epäluotettavaksi jos testijaksolla on nollapäiviä** |

### sMAPE ja nollapäivät

Venue 2 on kiinni osana pyhistä (esim. 3.4. ja 6.4.2026, 19.–21.6.2026). Nollapäivällä
symmetrinen suhde saavuttaa 200 %:n kattonsa riippumatta siitä kuinka lähellä ennuste oli:
`smape(toteuma 0, ennuste 3) = 200 %`, kun taas `smape(toteuma 500, ennuste 503) < 1 %`.
Mittari lasketaan, koska sen poisjättäminen johtaisi vain siihen että sitä kysytään, mutta
se **ei koskaan perusta verdiktiä** ja raportti merkitsee sen `⚠`-merkillä.

---

## 8. Tilastollinen arvio

### Perusasetelma

Verrataan mallin ja vertailukohdan absoluuttisten virheiden sarjoja pareittain samoilta
päiviltä:

```
d_t = |y_t − malli_t| − |y_t − vertailu_t|
```

Negatiivinen keskiarvo tarkoittaa että malli on lähempänä.

### Ensisijainen menetelmä: liikkuvan lohkon bootstrap

- lohkon pituus **7 päivää**, jotta viikkorytmin autokorrelaatio säilyy
- **10 000** uudelleenotantaa, kiinteä siemen
- 95 % persentiiliväli keskiarvolle `d`
- verdikti: **parempi** jos koko väli alle nollan, **huonompi** jos koko väli yli nollan,
  muuten **ei havaittavaa eroa**

Päiväkohtainen bootstrap antaisi noin kolmanneksen liian kapean välin, koska peräkkäisten
päivien kävijämäärät eivät ole riippumattomia.

Raportoidaan myös **taitopistemäärä** `SS = 1 − MAE_malli / MAE_vertailu` ja sen
bootstrap-väli.

### MDE, pakollinen osa verdiktiä

```
MDE = 2,8 · sd(d) / √n
```

Kun verdikti on "ei havaittavaa eroa", se voi tarkoittaa kahta eri asiaa: **mallit ovat
yhtä hyviä**, tai **otos on liian pieni**. Vain MDE erottaa nämä. Se raportoidaan sekä
kävijöinä per päivä että prosentteina vertailukohdan MAE:sta.

Nykyisellä aineistolla yhden kuukauden ikkunassa MDE on **28–82 % vertailukohdan
MAE:sta**, tyypillisesti noin kolmannes. **Yksi kuukausi pystyy siis todistamaan vain
suuret parannukset.** Älä koskaan lue "ei eroa" -tulosta todisteeksi samanveroisuudesta.

### Diebold-Mariano, toissijaisena

Lasketaan Newey-West-varianssilla (Bartlett-ydin, viive `ceil(1,5·n^(1/3))`) ja
Harvey-Leybourne-Newbold-pienotoskorjauksella. HLN-kaava kysyy horisonttia *h*; tässä
virheet kattavat horisontit 1–30 yhdestä origosta eikä yhtä *h*:ta ole, joten
`h = viive + 1` — sama riippuvuusoletus jonka varianssi jo tekee.

**p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta.** Paketti ei
tarvitse scipyä yhden jakaumafunktion takia.

DM on merkitty toissijaiseksi ja syy sanotaan raportissa: **yhden origon 30 virhettä
eivät ole 30 riippumatonta havaintoa.** Ne jakavat saman koulutusjoukon ja saman
kuukauden sään. DM:n oletukset ovat siis venytettyjä.

### Monen ikkunan kooste, tärkein tulos

Yhden ikkunan verdikti on **kuvaileva, ei todistava.** Varsinainen näyttö syntyy usean
ikkunan koosteesta, ja siinä **bootstrap uudelleenottaa kokonaisia ikkunoita, ei
yksittäisiä päiviä.** Ikkuna on riippumattomuuden luonnollinen yksikkö: kaksi saman
ikkunan päivää jakavat koulutusjoukon, kaksi eri ikkunaa eivät. Päivätason bootstrap
pooled-datasta laskisi saman näytön moneen kertaan.

Kooste on raportin pääotsikko. Yksittäisen ikkunan verdikti esitetään sen alla
yksityiskohtana, ja kooste kertoo montako ikkunaa mallia puolsi ja montako vastusti.

### Monivertailukorjaus

Kun sweep ajaa `k` ikkunaa ja `m` mallia, testataan `k·m` hypoteesia ja noin joka
kahdeskymmenes tulee merkitseväksi sattumalta. Raportoidaan sekä **raaka** että
**Holm-Bonferroni-korjattu** p-arvo, ja perheen koko kerrotaan.

### Bias ja kalibrointi

- **Bias**: bootstrap-luottamusväli keskivirheelle. Jos väli ei sisällä nollaa, malli yli-
  tai aliarvioi systemaattisesti. Suunta ja suuruus kerrotaan sekä kävijöinä että
  prosentteina.
- **Kalibrointi**: 80 % peittävyys ja sille **Clopper-Pearsonin eksakti** binomiväli
  (30 päivää on pieni otos ja osuus on lähellä yksikkövälin reunaa, missä
  normaaliapproksimaatio on huonoimmillaan). Verdikti: *kalibroitu* jos 0,80 on välin
  sisällä, *liian kapea* jos peittävyys jää alle, *liian leveä* jos yli.

---

## 9. Jakson kokonaismäärä

Tuottaja kysyy "montako kävijää huhtikuussa", ei "mikä oli päivätason MAE". **Nämä ovat
eri kysymyksiä eikä kumpaakaan saa päätellä toisesta.**

Huhtikuussa venue 1:n `climatology_dow` osuu kuukausisummaan 0,8 %:n tarkkuudella
(13 292 vs. 13 189), vaikka sen päivätason MAE on 96 kävijää eli noin 22 % päivän
keskiarvosta. Vastakkaisen merkkiset päivävirheet kumoavat toisensa summassa.

### Kokonaismäärän väliä ei summata päivistä

Päivien p10-arvojen summa ja p90-arvojen summa **eivät ole** kuukauden väli. Ne vastaavat
kysymykseen "entä jos jokainen päivä osuisi omaan kymmenenteen persentiiliinsä", ja se
skenaario vaatii kaikkien 30 virheen osoittavan samaan suuntaan. Vanha sovellus teki tämän
virheen ja sen kuukausivälit olivat käyttökelvottomia.

Väli **simuloidaan**: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä
bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku kerrotaan
päiväennusteilla ja summataan, ja väli luetaan summien jakaumasta. Raportti näyttää
naiivin summan rinnalla, jotta ero on nähtävissä.

### Milloin kokonaismäärän väliä ei pidä uskoa

Sisäkkäisen backtestin mallit on koulutettu **lyhyemmällä ja huonommalla aineistolla** kuin
ulompi malli — se on nested backtestin rakenteellinen ominaisuus. Jos niiden suhteellisten
virheiden mediaani karkaa yli 25 % ykkösestä, virheissä on **tasosiirtymä eikä pelkkää
hajontaa**, väli perii sen, ja raportti merkitsee sen `⚠ Näiden mallien väli ei ole
kalibroitu`. Lue silloin kokonaismäärän ero ja bias erikseen, älä väliä.

Piste-ennuste pidetään aina oman välinsä sisällä, samasta syystä kuin päivätason välit
(`ovf_forecast.intervals`): väli joka ei sisällä lukua jolle se on väli, ei ole
julkaisukelpoinen. Tasosiirtymä raportoidaan silti biasina, erotuksena ja
`median_ratio`-kenttänä.

---

## 10. Tuotokset

```
data/evaluations/
  index.json                   luettelo ajoista: run_id, luontiaika, ikkuna, mallit, verdikti
  {run_id}/
    config.json                ajon täydelliset parametrit
    predictions.csv            venue_id, date, horizon_days, model, weather_mode, y_true, p10, p50, p90
    metrics.json               kaikki mittarit, kokonaismäärät, pahiten menneet päivät
    verdicts.json              verdiktit koneluettavassa muodossa
    report.md                  ihmisluettava raportti
```

`run_id` on deterministinen ja luettava, esimerkiksi
`eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline`. Kaikki mikä muuttaa vastausta mutta ei
näy nimessä — venue-rajaus, liukuva koulutusikkuna, rajattu joukko sään tiloja, lukittu
vertailukohta — liitetään loppuun luettavana päätteenä (`_v1`, `_tw120`, `_wxoper`,
`_ref-climatology_dow`). Sama ajo samoilla parametreilla korvaa saman hakemiston.

### Raportin rakenne

1. **Verdikti** yhtenä kappaleena suomeksi, ilman jargonia
2. Ikkuna ja asetelma
3. Jakson kokonaismäärä
4. Päivätason mittarit, mallit ja vertailukohdat rinnakkain
5. Tilastollinen arvio: luottamusväli, taitopistemäärä, MDE, DM
6. Kalibrointi ja bias
7. Sään kolmen tilan vertailu
8. Rajoitteet
9. **Pahiten menneet päivät** — viisi suurinta virhettä päivämäärineen ja mahdollisine
   syineen (pyhäpäivä, runsas sade, klimatologiasää, nollapäivä)

Kohta 9 on käytännössä hyödyllisin: se kertoo mitä mallista puuttuu. Toistuva syy samassa
sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

---

## 11. Mitä tuloksista EI voi päätellä

Tämä luku on tärkein.

**"Ei havaittavaa eroa" ei tarkoita että mallit ovat yhtä hyviä.** Se tarkoittaa että
*tämä otos ei erottanut niitä*. Lue MDE. Nykyisellä aineistolla yhden kuukauden MDE on
suuruusluokkaa kolmannes vertailukohdan MAE:sta, eli pienet mutta todelliset parannukset
jäävät näkymättömiin.

**Yhden ikkunan tulos ei ole todiste.** Se on kuvaus siitä mitä yhtenä kuukautena
tapahtui. Käytä sweepiä.

**Hyvä kuukausisumma ei todista hyvää päivätarkkuutta, eikä päinvastoin.** Ks. luku 9.

**sMAPE ei kelpaa verdiktin perustaksi** tällä aineistolla. Ks. luku 7.

**Peittävyyttä ei voi lukea oletusväleistä.** Jos sisäkkäinen backtest ei tuottanut
tarpeeksi havaintoja johonkin horisonttikoriin, väli on kiinteä oletusarvo. Raportin
kohta 8 nimeää nämä.

**Vuosikausivaihtelusta ei voi sanoa mitään.** Aineistoa on noin kahdeksan kuukautta
yhdeltä vuodelta. Vertailu toiseen vuoteen ei ole mahdollinen, eivätkä mallien
vuosikausikomponentit ole arvioitavissa.

**Sään todellista arvoa ei ole mitattu.** `perfect` on liian hyvä ja `climatology` liian
huono; `operational` olettaa **hyvän** sääennusteen sen sijaan että käyttäisi sitä
sääennustetta joka origossa oli oikeasti saatavilla. Oikea vastaus olisi neljäs tila
`archived_forecast`. Sitä ei ole toteutettu, mutta se on mahdollinen, ja rajapinta on
tarkistettu dokumentaatiosta:

- **Open-Meteon Historical Forecast API ei kelpaa tähän.** Se ompelee peräkkäisten
  ajokertojen ensimmäiset tunnit yhdeksi jatkuvaksi sarjaksi, eli se on lähempänä
  parasta arviota toteutuneesta kuin sitä ennustetta joka origossa oli näkyvissä. Sillä
  ei ole parametria ennusteen antohetkelle, vain `start_date` ja `end_date`.
- **Single Runs API on se jota tähän tarvitaan.** Se säilöö jokaisen mallikierroksen
  erikseen ja sitä haetaan UTC-alustusajalla `run=` (esim. `run=2026-03-31T00:00`),
  jolloin saa yhden ajon koko ennustehorisontin.
- **Kattavuus riittää.** Useimmat mallit on arkistoitu tammikuusta 2024, eli koko tämän
  aineiston ajalta. Yksittäisen ajon horisontti on globaaleilla malleilla noin 7+ vrk ja
  alueellisilla 2–5 vrk, joten 30 vrk ikkunassa `archived_forecast` kattaisi vain
  lähipäivät ja loppu jäisi klimatologiaksi.

Toteutus vaatisi haun ja tallennusmuodon ingest-puolelle, koska arviointiajo ei saa
kutsua verkkoa: determinismi ja offline-ajettavuus ovat tämän paketin ehtoja. Kunnes se
on tehty, **`operational` on paras arvaus eikä mittaus**, ja `perfect`–`climatology`-väli
on se mikä sään arvosta oikeasti tiedetään.

**Ennustevälit lepäävät ohuen otoksen varassa.** Sisäkkäisessä backtestissä on
tyypillisesti 3–12 origoa, ja huhtikuun ikkunassa vain 3.

---

## 12. Mitatut tulokset

Ks. `docs/FORECAST_MODEL.md` luku 5.5. Lyhyesti: **kuukausisweepissä 2026-04 … 2026-08
perusmalli häviää parhaalle yksinkertaiselle vertailukohdalle molemmilla venueilla**,
neljässä ikkunassa viidestä. Se on oikea ja rehellinen tulos, ei epäonnistuminen — ja
sellaisena se on myös raportin ensimmäisessä kappaleessa.
