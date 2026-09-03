# Kuukauden hiljaisimmat päivät

*In English: [`QUIET_DAYS.en.md`](QUIET_DAYS.en.md).*

Miten `python -m ovf_forecast quiet` löytää kuukauden hiljaisimmat päivät, mistä kynnys
tulee, miten mallin luotettavuus mitataan ja mitä tuloksesta **ei** voi päätellä.

Tämä on eri kysymys kuin `docs/FORECAST_MODEL.md`:n ennuste. Ennustemalli kertoo *kuinka
monta* kävijää päivä tuo. Tämä paketti kertoo, **mitkä kuukauden päivistä ovat sen
hiljaisimmat**, jotta asiakasaktivointitapahtuma osataan sijoittaa sinne missä vapaata
kapasiteettia on eniten.

Ero ei ole kosmeettinen. Tason ennustaminen vaatii tietoa siitä, kuinka vilkas lokakuu
on; järjestyksen ennustaminen vaatii vain tiedon siitä, mikä lokakuun keskiviikoista on
hiljainen. Kahdeksan kuukauden historialla jälkimmäiseen voi vastata, vaikka
edelliseen ei — `docs/EVALUATION.md` luku 12 kertoo, että tasoennuste häviää
yksinkertaiselle arkipäiväkeskiarvolle molemmilla kohteilla. Siksi tämän paketin jokainen
luku on jaettu kuukauden **oman mediaanipäivän** arvolla: tason virhe kumoutuu eikä
vaikuta järjestykseen.

---

## 1. Nopea aloitus

```bash
python -m ovf_forecast quiet backtest
python -m ovf_forecast quiet
```

Ensimmäinen mittaa, kannattaako mallia uskoa: se käy historian läpi kuukausi kerrallaan,
nimeää jokaisen kuukauden hiljaisimmat päivät pelkän sitä edeltävän datan perusteella ja
avaa toteuman vasta sen jälkeen. Toinen nimeää seuraavan kuukauden hiljaisimmat päivät ja
liittää vastaukseen sen, mitä ensimmäinen mittasi.

Tässä järjestyksessä, ei toisin päin. Ilman mittausta suositus on arvaus, jonka ympärillä
on siisti taulukko, ja komento sanoo sen ääneen:

> Mallin luotettavuutta ei ole mitattu tässä repositoriossa: aja
> `python -m ovf_forecast quiet backtest` ennen kuin suositukseen nojataan.

Molemmat tallentavat tuloksensa hakemistoon `data/quiet/`.

---

## 2. Komennot

| Komento | Mitä tekee |
| --- | --- |
| `quiet` | Nimeää seuraavan kuukauden hiljaisimmat päivät |
| `quiet --month 2026-10` | Nimeää valitun kuukauden päivät |
| `quiet --top-k 3` | Kolmen päivän lyhytlista viidenneksen sijaan |
| `quiet backtest` | Kuukausipyyhkäisy: yksi ikkuna per kuukausi + verdikti |
| `quiet backtest --sweep rolling --step 14 --horizon 30` | Liukuva origo |
| `quiet backtest --models quiet_calendar,baseline` | Vertaa sääntöjä keskenään |
| `quiet report --latest` | Tulostaa viimeisimmän tallennetun raportin |
| `quiet report --id <run_id>` | Tulostaa nimetyn ajon raportin |
| `quiet list` | Listaa tallennetut ajot |

### Valitsimet

| Valitsin | Oletus | Merkitys |
| --- | --- | --- |
| `--month` | havaintojen jälkeinen kuukausi | Kohdekuukausi `YYYY-MM` |
| `--score-model` | `quiet_calendar` | Järjestyssääntö, ks. luku 5 |
| `--quiet-share` | `0.20` | Kuinka suuri osuus ehdokaspäivistä on hiljaisia |
| `--top-k` | — | Kiinteä päivien lukumäärä; ohittaa `--quiet-share` |
| `--venue` | kaikki | Toistettava |
| `--simulations` | 10 000 (pyyhkäisyssä 2 000) | Simulaatiota todennäköisyyttä kohden |
| `--seed` | 20260101 | Simulaation ja bootstrapin siemenluku |
| `--sweep` | `monthly` | Vain `backtest`: `monthly` tai `rolling` |
| `--from`, `--to` | koko käytettävä historia | Vain `--sweep monthly` |
| `--step`, `--horizon`, `--max-windows` | 14, 30, 12 | Vain `--sweep rolling` |
| `--resamples` | 10 000 | Vain `backtest`: bootstrap-toistot |

Ajo on deterministinen. Sama syöte ja samat parametrit tuottavat tavulleen samat
tiedostot hakemistoon `data/quiet/{run_id}/`; ainoa muuttuva arvo on `index.json`in
`created_at`, joka on rekisterin eikä tuloksen kenttä.

Kuukausipyyhkäisy on oletus siksi, että kysymys on kuukausittainen ja kalenterikuukaudet
eivät mene päällekkäin. Liukuvassa pyyhkäisyssä peräkkäiset ikkunat jakavat päiviä, jolloin
ne eivät ole riippumattomia ja luottamusväli on todellista kapeampi. Raportti kertoo tämän
itse, kun ikkunat menevät päällekkäin.

---

## 3. Kynnys: mikä on hiljainen päivä

Kynnys on kolme päätöstä, ja ne ovat moduulissa
`packages/forecast/src/ovf_forecast/quiet/threshold.py` eivätkä missään muualla.

### 3.1 Ehdokkuus: mitkä päivät saavat olla hiljaisia

Suljettu päivä on jokaisen kuukauden hiljaisin päivä ja täysin hyödytön tapahtumalle.
Kaksi rajausta tehdään etukäteen, siis sellaisen tiedon perusteella joka on olemassa jo
ennustehetkellä:

| Sääntö | Ehto | Kohde |
| --- | --- | --- |
| `closed_weekday` | Arkipäivän mediaani < 15 % kohteen omasta mediaanista | Kaupungintalon maanantait ovat 14 % |
| `closed_holiday` | Pyhäpäiväkerroin < 15 % | Ei laukea nykyisellä datalla |

Toteumapuolella eli mittauksessa tulee kaksi rajausta lisää, koska ne vaativat havainnon:
päivä jolla ei ollut yhtään kävijää (`no_visitors`) oli sulkeminen tai anturikatko, ja
päivä jota ei mitattu kokonaan (`incomplete_day`) näyttää hiljaiselta syystä jolla ei ole
mitään tekemistä kävijöiden kanssa. Kumpaakaan ei voi soveltaa ennusteeseen, koska
molemmat vaativat sen tiedon jota malli yrittää ennustaa.

Rajaus on tarkoituksella tylppä: yksi lippu per viikonpäivä, ei kausittaisia aukioloja.
Neljä viikoittaista havaintoa per arkipäivä ei kanna hienompaa.

**Pelkästään hiljainen arkipäivä ei ole suljettu arkipäivä.** Pekurin sunnuntai on 82 %
kohteen mediaanipäivästä. Se on vastaus, ei suodatin.

### 3.2 Raja: kuukauden hiljaisin viidennes

Hiljaisia päiviä on `k = ceil(0.20 × ehdokaspäivien lukumäärä)`, rajattuna välille 3–10.
30 päivän kuukaudessa se on kuusi päivää.

Kynnys on suhteellinen ja kuukauden sisäinen. Se ei ole kävijämäärä, koska 400 kävijää on
Pekurissa hiljainen ja Kaupungintalossa ennätys, eikä se ole kiinteä osuus mediaanista,
koska kuukausien hajonta vaihtelee. Se on kuukauden oman jakauman 20 % persentiili.

### 3.3 Mistä 20 % tulee

Kynnys on valinta, ei luonnonvakio, joten se on mitattu. Alla kuukausipyyhkäisy
2026-04 … 2026-08 molemmilta kohteilta, `quiet_calendar`-säännöllä, viisi eri kynnystä.
Taulukko syntyy ajamalla pyyhkäisy viidesti:

```bash
for share in 0.10 0.15 0.20 0.25 0.33; do
  python -m ovf_forecast quiet backtest --quiet-share $share
done
```

| Osuus | k | Kynnys / mediaanipäivä | Paras mahdollinen hyöty | Mitattu hyöty | Osuvuus | Satunnaisvalinta |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 % | 3,4 | 0,46 | 58 % | 41 % | 48 % | 12 % |
| 15 % | 4,8 | 0,58 | 54 % | 32 % | 50 % | 17 % |
| **20 %** | **6,2** | **0,70** | **49 %** | **26 %** | **53 %** | **22 %** |
| 25 % | 7,5 | 0,77 | 45 % | 21 % | 52 % | 26 % |
| 33 % | 9,5 | 0,86 | 39 % | 15 % | 53 % | 33 % |

Luvut ovat molempien kohteiden keskiarvoja. *Hyöty* on 1 − (valittujen päivien keskiarvo ÷
kuukauden mediaanipäivä), *paras mahdollinen* sama luku jälkiviisaasti valituille päiville,
*osuvuus* osuus nimetyistä päivistä jotka todella kuuluivat hiljaisimpiin.

Taulukosta luetaan kolme asiaa:

1. **Tiukempi kynnys tuottaa hiljaisempia päiviä.** 10 %:n listalla valitut päivät ovat
   41 % mediaanipäivää hiljaisempia, 33 %:n listalla 15 %. Suhde satunnaisvalintaan on
   samalla paras: 4,0-kertainen 10 %:ssa, 1,6-kertainen 33 %:ssa.
2. **20 % osuu kohtaan, jossa kynnys on vielä tulkittavissa.** Raja asettuu 0,70:een
   mediaanipäivästä, eli hiljainen päivä on karkeasti "noin kolme neljäsosaa normaalista
   päivästä". Tiukemmalla rajalla `k` törmää alarajaan 3 eikä osuus enää ohjaa mitään.
3. **20 % antaa listan, jolla voi työskennellä.** Kuusi päivää riittää siihen, että
   tapahtuma mahtuu esiintyjän, tilan ja henkilöstön aikatauluihin. Kolme ei aina riitä.

Oletus on siis kompromissi eikä optimi, ja se on tarkoituksella se päätös jota on helpoin
muuttaa. **Jos tarvitset vain yhden tai kaksi päivämäärää, käytä `--top-k 3`: mitattu
hyöty on silloin noin kaksinkertainen.**

### 3.4 Olennaisuus: milloin vastausta ei kannata antaa

Tasaisellakin kuukaudella on hiljaisin viidennes, ja sen nimeäminen olisi suositus jonka
takana ei ole mitään. Siksi jokainen joukko kantaa lipun `is_material`: joukon on oltava
vähintään 15 % mediaanipäivän alapuolella ennen kuin sitä saa lukea suosituksena.
Ennusteessa lippu koskee **mallin erottelukykyä** — pystyykö sääntö ylipäätään erottamaan
kuukauden päiviä toisistaan — ja toteumassa **kuukauden todellista hajontaa**.

---

## 4. Ennustemalli

### 4.1 Pisteluku

Oletussääntö `quiet_calendar` antaa jokaiselle kohdekuukauden päivälle pisteluvun:

```
pisteluku(d) = arkipäiväkeskiarvo(viikonpäivä(d)) × pyhäpäiväkerroin(d)
```

- **Arkipäiväkeskiarvo** on kohteen kävijämäärän keskiarvo kyseisenä viikonpäivänä koko
  opetusikkunassa. Arkipäivälle jota opetusikkuna ei ole nähnyt käytetään kohteen
  keskiarvoa: päivä ilman pistelukua ei koskaan päätyisi suositukseen, ja se on eri väite
  kuin "tämä päivä ei ole hiljainen".
- **Pyhäpäiväkerroin** on mediaani suhteesta `toteuma / arkipäiväkeskiarvo` opetusikkunan
  pyhäpäiviltä, leikattuna välille 0,05–2,0 ja laskettuna vasta kolmesta havainnosta
  alkaen. Ilman pyhäpäivää kuukaudessa sääntö on täsmälleen `climatology_dow`.

Pisteluku on kävijämäärän suuruusluokassa, mutta **se ei ole kävijäennuste**. Se on
järjestysluku. Tasoennusteeseen on `python -m ovf_forecast run`.

### 4.2 Mallin erottelu ei ole toteutuva ero

Pisteluku on ehdollinen keskiarvo, ja ehdollinen keskiarvo on aina toteumaa tasaisempi.
Syyskuun 2026 ennusteessa Pekurin hiljaisin viidennes erottuu 18 % mediaanipäivän
alapuolelle. Toteutuneissa kuukausissa hiljaisin viidennes on keskimäärin 49 %
mediaanipäivän alapuolella. Nämä ovat eri lukuja eikä toinen ennusta toista:

- **Mallin erottelu** kertoo, kuinka kauas sääntö päivät erottaa. Sitä käytetään
  olennaisuuslipun laskentaan.
- **Toteutuva hyöty** kertoo, kuinka hiljaisia valitut päivät olivat. Sen saa vain
  mittaamalla, ja se on `quiet backtest`:n tulos.

Raportti sanoo tämän joka kerta, koska sekaannus on se virhe joka tästä työkalusta
tehdään.

### 4.3 Valintatodennäköisyys

Jokainen ehdokaspäivä saa todennäköisyyden kuulua kuukauden hiljaisimpiin. Se on tällä
datalla arvokkaampi luku kuin itse järjestys.

Menetelmä on Monte Carlo. Kuukausi simuloidaan 10 000 kertaa: pisteluvut kerrotaan
polulla, joka on lohkobootstrapattu **säännön omista mitatuista jäännöksistä**, kuukausi
järjestetään uudelleen ja lasketaan, kuinka usein kukin päivä päätyi hiljaisimpaan
joukkoon.

- **Jäännökset mitataan opetusikkunan sisällä.** Rullaava origo astuu taaksepäin 14
  päivää kerrallaan, ja uusin niistä on `origo − horisontti`, jolloin sen viimeinen
  ennustepäivä osuu täsmälleen origoon eikä koskaan päivää myöhemmäksi. Sama sääntö kuin
  arviointipaketin sisäkkäisessä backtestissä.
- **Lohko on seitsemän päivää.** Hiljainen viikko on hiljainen koko viikon, ja
  päiväkohtainen arvonta tekisi jokaisen päivän kohtalosta riippumattoman ja jokaisesta
  todennäköisyydestä liian varman.
- **Jos yhtään sisäistä origoa ei mahdu**, käytetään oletushajontaa ja raportti sanoo sen.
  Silloin todennäköisyys kertoo säännön järjestyksestä, ei mitatusta epävarmuudesta.

Todennäköisyyksien summa on `k` rakenteen nojalla, ja luvut ovat kalibroituja tai eivät —
sen kertoo testityökalun luku 6.4.

### 4.4 Tasapisteet

Oletussääntö antaa kuukauden jokaiselle sunnuntaille saman pisteluvun. Ne ovat siis
mallin näkökulmasta keskenään vaihdettavissa, ja kuuden päivän joukkoon mahtuu osa
seuraavan arkipäivän esiintymistä ja osa ei — pelkän kalenterijärjestyksen takia.

Tätä ei piiloteta:

- Samanpisteiset päivät saavat **saman todennäköisyyden** (ryhmän keskiarvon). 47 % ja
  45 % kahdelle identtiselle sunnuntaille olisi Monte Carlon kohinaa, jonka lukija ottaisi
  mieltymykseksi.
- Raportissa on sarake **Samanarvoisia**, ja kun kynnys osuu ryhmän sisään, vastaus sanoo
  sen: valinta niiden kesken on päivämääräjärjestyksessä eikä perustu dataan, joten se
  voidaan tehdä muilla perusteilla.

Kalenterijärjestys ei ole neutraali tapa purkaa tasapisteitä, ja luku 7 näyttää mitä siitä
seuraa säännölle jolla ei ole järjestystietoa lainkaan.

### 4.5 Kesken kuukauden

Kohdekuukauden päivät jotka ovat jo toteutuneet pidetään mukana ja merkitään
`observed`-tilaan. Ne kilpailevat paikasta hiljaisimpien joukossa **omalla toteutuneella
arvollaan** ja saavat simulaatiossa kertoimen 1,0. Näin ajo 12. päivänä antaa
johdonmukaisen vastauksen kuun lopusta sen sijaan, että ensimmäistä yhtätoista päivää
ei olisi olemassa.

### 4.6 Vuotokiellot

1. Sääntö näkee vain rivit `<= origo`. `ScoreRequest` katkaisee historian itse, joten
   pidemmän historian antaminen ei voi vuotaa havaintoa piirteeseen.
2. Ehdokkuussäännöt (`closed_weekday`, `closed_holiday`) johdetaan yksin opetusikkunasta.
3. Jäännösten sisäiset origot ovat kokonaan opetusikkunan sisällä (luku 4.3).
4. Kalenteritiedot — viikonpäivä, pyhäpäivä — ovat sallittuja, koska ne tiedetään
   etukäteen.
5. Sää ei ole piirre lainkaan (luku 5.3).

Testi `test_quiet_model.py::test_a_score_cannot_see_past_its_origin` ajaa jokaisen
säännön sekä täydellä että katkaistulla historialla ja vaatii saman tuloksen.

---

## 5. Säännöt ja se, miksi oletus on tämä

### 5.1 Käytettävissä olevat säännöt

| Sääntö | Mitä tekee |
| --- | --- |
| `quiet_calendar` | Arkipäiväkeskiarvo × pyhäpäiväkerroin. Oletus |
| `climatology_dow` | Opetusikkunan arkipäiväkeskiarvo. Sama ilman pyhäpäivätietoa |
| `seasonal_naive` | Origoon päättyvä viikko toistettuna |
| `moving_average_28d` | 28 päivän keskiarvo, sama luku joka päivälle |
| `baseline` | Tuotannon gradient boosting -malli järjestysavaimena |

Tasomallit ovat mukana vastustajina eivätkä koristeena: päiväennuste *on* kuukauden
järjestys, joten niitä ei arvostella työstä jota varten niitä ei rakennettu.

### 5.2 Mitattu vertailu

Kuukausipyyhkäisy 2026-04 … 2026-08, viisi ikkunaa, kynnys 20 %:

| Kohde | Sääntö | Hyöty | 95 % väli | Osuvuus | Satunnais | Talteen | Spearman | Verdikti |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Pekuri | `baseline` | 10 % | −1 % … 22 % | 43 % | 21 % | 30 % | 0,29 | ei todennettu |
| Pekuri | `seasonal_naive` | 10 % | −2 % … 19 % | 42 % | 21 % | 29 % | 0,34 | ei todennettu |
| Pekuri | `climatology_dow` | 8 % | −1 % … 17 % | 40 % | 21 % | 22 % | 0,35 | ei todennettu |
| Pekuri | `quiet_calendar` | 7 % | −1 % … 17 % | 40 % | 21 % | 20 % | 0,37 | ei todennettu |
| Pekuri | `moving_average_28d` | −12 % | −22 % … −1 % | 22 % | 21 % | −34 % | – | **haitallinen** |
| Kaupungintalo | `climatology_dow` | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 0,43 | **todennettu** |
| Kaupungintalo | `quiet_calendar` | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 0,42 | **todennettu** |
| Kaupungintalo | `baseline` | 34 % | 7 % … 57 % | 61 % | 22 % | 54 % | 0,46 | **todennettu** |
| Kaupungintalo | `seasonal_naive` | 29 % | 1 % … 55 % | 50 % | 22 % | 47 % | 0,24 | **todennettu** |
| Kaupungintalo | `moving_average_28d` | −16 % | −43 % … 11 % | 18 % | 22 % | −26 % | – | ei todennettu |

Toistettavissa komennolla:

```bash
python -m ovf_forecast quiet backtest \
  --models quiet_calendar,climatology_dow,seasonal_naive,moving_average_28d,baseline
```

Kolme havaintoa:

- **Neljän järkevän säännön välillä ei ole mitattavaa eroa.** Erot ovat muutamia
  prosenttiyksikköjä ja luottamusvälit ovat kymmeniä. Sääntövalinta ei ole se, mikä
  ratkaisee tämän tehtävän.
- **Kohteiden välillä on valtava ero.** Sama sääntö tuottaa 45 % hyötyä toisella ja 7 %
  toisella. Verdikti annetaan siksi kohteittain.
- **`moving_average_28d` on nollasääntö ja käyttäytyy sen mukaisesti.** Se antaa jokaiselle
  päivälle saman pisteluvun, jolloin tasapisteiden purku kalenterijärjestyksessä valitsee
  kuukauden kuusi ensimmäistä päivää. Tulos on satunnaisvalintaa huonompi, ja se on juuri
  se syy, miksi jaettuun tasapisteryhmään osuva kynnys raportoidaan (luku 4.4).

### 5.3 Mitä kokeiltiin ja jätettiin pois

Nämä mittaukset tehtiin kehityksen aikana samoilla ikkunoilla ja samalla
ehdokkuussäännöllä, mutta ne eivät ole toistettavissa valmiilla CLI:llä, koska hylätyt
muunnelmat eivät ole paketissa. Luvut ovat keskimääräistä hyötyä molemmilta kohteilta.

| Muunnelma | Kuukausi-ikkunat | Liukuvat ikkunat |
| --- | ---: | ---: |
| Arkipäiväkeskiarvo, koko ikkuna | 0,264 | 0,318 |
| Arkipäiväkeskiarvo + pyhäpäiväkerroin (**oletus**) | 0,262 | 0,317 |
| Arkipäivämediaani, 8 viikkoa | 0,239 | 0,299 |
| Arkipäivämediaani, koko ikkuna | 0,236 | 0,272 |
| Arkipäiväkeskiarvo, 8 viikkoa | 0,225 | 0,300 |

- **Keskiarvo voittaa mediaanin.** Silloin tällöin vilkas lauantai on täsmälleen se tieto,
  joka pitää lauantain poissa hiljaisten joukosta.
- **Tuoreusikkuna ei auta.** Kahdeksan viikon rajaus on neutraali tai haitallinen, joten
  sääntö käyttää koko opetusikkunaa.
- **Pyhäpäiväkerroin ei muuta mitään tällä datalla.** Kahdeksan kuukautta sisältää kahdeksan
  pyhäpäivää, ja niistä sulkemiset rajautuvat pois jo ennen suositusta. Kerroin on silti
  mukana, koska mekanismi on todellinen ja sen näyttäisi vasta täysi vuosi, jossa on joulu
  ja juhannus.
- **Sää ei paranna järjestystä.** Sadekerroin arkipäiväsäännön päällä antoi 0,813 vastaan
  0,811 keskimääräistä toteutunutta suhdelukua, eli eron kohinassa. Jäännösten korrelaatio
  sateeseen on 0,10–0,12 ja lämpötilaan noin 0. Sää on siksi raportin taulukossa
  **taustatietona ihmisen päätöstä varten**, ei pisteytyksessä.
- **Sääntöjen yhdistäminen sijalukuina** (`quiet_calendar` + `baseline`) ei parantanut
  tulosta.

---

## 6. Testityökalu

`quiet backtest` on mittalaite, ei osa tuotantoajoa. Jokainen ikkuna on yksi rehellinen
harjoitus oikeasta tehtävästä: opeta origoon asti, nimeä jakson hiljaisimmat päivät, avaa
toteuma vasta sitten.

### 6.1 Mittarit

| Mittari | Määritelmä | Mitä kertoo |
| --- | --- | --- |
| `hit_rate` | Osuus nimetyistä päivistä jotka kuuluivat todelliseen joukkoon | Osuvuus |
| `chance_rate` | `k / ehdokkaiden lukumäärä` | Mitä arvaus antaisi |
| `realized_ratio` | Nimettyjen päivien keskiarvo ÷ kuukauden mediaanipäivä | – |
| `benefit` | `1 − realized_ratio` | **Otsikkoluku** |
| `oracle_ratio` | Sama jälkiviisaasti valituille päiville | Katto |
| `capture` | `benefit ÷ oracle_benefit` | Osuus saavutettavissa olleesta |
| `spearman` | Järjestyskorrelaatio pisteluvun ja toteuman välillä | Koko järjestys, ei vain raja |
| `top1_ratio` | Hiljaisimmaksi ennustetun päivän toteuma ÷ mediaani | Yhden päivän valinta |

`hit_rate` on luonteva mutta neljästä hyödyttömin: se laskee ohituksen seitsemänneksi
hiljaisimpaan päivään yhtä pahaksi kuin ohituksen kuukauden vilkkaimpaan. `benefit` on se,
mihin päätös nojaa, ja siksi verdikti rakennetaan siitä.

### 6.2 Verdikti

Verdikti on kohde- ja sääntökohtainen ja perustuu hyödyn 95 %:n bootstrap-väliin:

| Verdikti | Ehto |
| --- | --- |
| `useful` — hyöty on todennettu | Koko väli yli nollan |
| `no_detectable_benefit` — hyötyä ei ole todennettu | Väli sisältää nollan |
| `harmful` — valinta osuu vilkkaampiin päiviin | Koko väli alle nollan |

Toinen, toissijainen verdikti kertoo saman osuvuudesta: ylittääkö `hit_rate − chance_rate`
nollan.

**"Ei todennettu" ei ole "ei hyötyä".** Siksi jokaiseen sellaiseen verdiktiin liitetään
pienin havaittava hyöty `MDE = 2,8 × sd / √ikkunat`. Viidellä ikkunalla se on suuri, ja se
on tämän aineiston tärkein rajoite.

### 6.3 Miksi bootstrap arpoo ikkunoita eikä päiviä

Saman kuukauden päivät jakavat origon, opetusjakson ja kuukauden sään; kaksi eri kuukautta
eivät jaa mitään. Päivien arpominen laskisi saman todistusaineiston moneen kertaan ja
tuottaisi välin, joka näyttää paljon päättäväisemmältä kuin aineisto on. Sama ratkaisu ja
sama perustelu kuin `docs/EVALUATION.md` luvussa 8.

### 6.4 Todennäköisyyksien kalibrointi

Paketti julkaisee todennäköisyyksiä, joten ne on tarkastettava. Jokainen ehdokaspäivä
tuottaa yhden parin — annettu todennäköisyys ja se, kuuluiko päivä lopulta hiljaisimpiin —
ja raportin luku 5 näyttää parit kuudessa välissä. Hyvin kalibroidussa mallissa sarakkeet
ovat lähellä toisiaan. Ohut väli ei kerro mitään, joten `n` on jokaisella rivillä.

Taulukko on laskettavissa uudelleen tallennetusta tiedostosta `days.csv`; sitä ei tarvitse
uskoa raportin sanaan.

### 6.5 Kaksi jälkiviisautta, jotka mittaus käyttää

Kumpaakaan ei piiloteta, koska molemmat siirtävät tulosta hieman mallille suotuisaan
suuntaan.

**Ehdokasjoukko on toteuman määrittelemä.** Päivä joka osoittautui suljetuksi, vajaasti
mitatuksi tai nollaksi rajautuu pois sekä toteumasta että siitä, mitä sääntö saa nimetä.
Sääntöä ei siis rangaista suljetun päivän ehdottamisesta. Se on puolustettava valinta —
sulkeminen on toiminnallinen tosiasia eikä järjestyssäännön virhe — mutta se tarkoittaa,
että mittaus ei kata riskiä "ehdotettu päivä osoittautuu suljetuksi". Nykyisellä datalla
tällaisia päiviä on kuusi kahdeksassa kuukaudessa, kaikki Kaupungintalolla.

**`k` otetaan toteuman ehdokasmäärästä.** Muuten nimetty ja todellinen joukko olisivat eri
kokoisia eikä osuvuutta olisi määritelty lainkaan. Sama `k` menee myös satunnaisvalinnan
laskentaan, joten se ei suosi sääntöä vertailussa.

---

## 7. Mitatut tulokset

Kuukausipyyhkäisy 2026-04 … 2026-08, `quiet_calendar`, kynnys 20 %, viisi ikkunaa.
Tallennettuna hakemistoon `data/quiet/`.

| Kohde | Hyöty | 95 % väli | Osuvuus | Satunnais | Talteen | MDE | Verdikti |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Pekuri (1) | 7 % | −1 % … 17 % | 40 % | 21 % | 20 % | 14 % | ei todennettu |
| Kaupungintalo (2) | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 32 % | **todennettu** |

**Kaupungintalolla menetelmä toimii.** Nimetyt päivät olivat keskimäärin 45 %
mediaanipäivää hiljaisempia, ja se on 72 % kaikesta siitä, mikä oli jälkiviisaastikin
saavutettavissa. Osuvuus on kolminkertainen arvaukseen nähden. Suurin osa signaalista on
kalenterirakennetta: suljetut maanantait rajautuvat ehdokkaista pois, ja pyhäpäivien
ympäristö on aidosti ja ennustettavasti hiljainen.

**Pekurilla ei toimi.** Hyöty on 7 % ja väli sisältää nollan. Osuvuus 40 % on selvästi
satunnaisvalinnan 21 % yläpuolella, mutta se ei muutu hyödyksi.

### 7.1 Miksi Pekuri on vaikea

Ero ei ole siinä, että Pekurin viikkorytmi olisi heikompi — se on itse asiassa vahvempi.
Ero syntyy kolmessa vaiheessa, ja jokainen niistä vie osansa.

| Vaihe | Pekuri | Kaupungintalo |
| --- | ---: | ---: |
| Paljonko kuukaudesta on voitettavissa (täysi oraakkeli) | 35 % | 63 % |
| Paras mahdollinen viikonpäiväsääntö | 17 % | 44 % |
| Mitattu malli | 7 % | 45 % |

**Vaihe 1: Pekurissa ei ole hiljaisia päiviä löydettäväksi.** Ehdokaspäivistä 1,4 % jää
alle puoleen kuukauden mediaanipäivästä ja **yksikään ei jää alle 0,3-kertaiseksi**.
Kaupungintalolla vastaavat luvut ovat 14,5 % ja 11,6 %: siellä on joka kuukausi joukko
lähes tyhjiä päiviä. Pekurin kuukausi on pohjastaan tasainen, joten täydellinenkin
jälkiviisaus tuottaisi vain 35 %:n hyödyn 63 %:n sijaan. Puolet erosta on tässä, eikä
sille voi tehdä mitään mallilla.

**Vaihe 2: viikonpäivä kantaa Pekurissa vain puolet siitä, mikä on löydettävissä.** Jos
sääntö tuntisi etukäteen kuukauden todelliset viikonpäiväkeskiarvot, se saisi Pekurissa
17 % eli 49 % kaikesta saatavilla olevasta; Kaupungintalolla 44 % eli 70 %. Loppu on
päiväkohtaista vaihtelua, jonka selittäjää tässä aineistossa ei ole: sään korrelaatio
jäännökseen on 0,10–0,12 ja tapahtumakalenteria ei ole olemassa.

**Vaihe 3: Pekurissa malli ei saa edes omaa viikonpäiväkattoaan.** Mitattu 7 % on 41 %
katosta 17 %. Kaupungintalolla 45 % on jo koko katto 44 % — sieltä ei ole enää mitään
irti paremmalla viikonpäiväarviolla. Syy on rytmin liukuminen. Pekurin maanantai on
tammikuussa kuukauden hiljaisin päivä (0,56 × mediaani) ja heinäkuussa sen vilkkaimpia
(1,36):

| | ma | ti | ke | to | pe | la | su |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| tammikuu | 0,56 | 1,09 | 0,57 | 0,84 | 1,04 | 1,99 | 0,89 |
| huhtikuu | 0,73 | 0,84 | 0,95 | 1,24 | 1,36 | 1,78 | 0,88 |
| heinäkuu | 1,36 | 1,29 | 1,07 | 0,97 | 0,96 | 1,23 | 0,81 |

Viikonpäivien välinen hajonta on 0,24 ja *saman* viikonpäivän kuukausivaihtelu 0,18. Koko
opetusikkunan keskiarvo kuvaa siis rytmiä, jota ennustettavassa kuukaudessa ei enää ole.
Tuoreusikkuna ei korjaa tätä (luku 5.3): kahdeksassa viikossa on kahdeksan havaintoa per
arkipäivä, ja keskiarvon keskivirhe 0,41 / √8 ≈ 0,15 on samaa suuruusluokkaa kuin
liukuminen itse. Harha vaihtuu varianssiin yksi yhteen.

**Ja huti maksaa.** Molemmilla kohteilla noin 19 % päivistä on yli 1,5 × mediaani, mutta
Pekurissa oikeat osumat ovat vain 0,7 × mediaani eivätkä siksi kompensoi väärää valintaa,
kun taas Kaupungintalon osumat ovat 0,2–0,3 × ja imevät hudin. Pekurin pahimmat valinnat
mitatuissa ikkunoissa olivat su 10.5. (174 % mediaanista), ma 22.6. (168 %) ja ma 6.7.
(150 %). Kyse ei ole yhdestä kummajaisesta: kolmen pahimman valinnan poistaminen nostaisi
hyödyn 7 %:sta vain 13 %:iin.

Pekurin kaksitoista vilkkainta päivää eivät ole yhtään ylläpidetyssä kalenterissa. Kolme
vilkkainta ovat perjantait 15.5. (319 % mediaanista), 12.6. (302 %) ja 14.8. (252 %).
Datassa ei ole mitään, mikä erottaisi ne tavallisesta perjantaista.

Tämä on tulos eikä rikkinäinen putki. Työkalun tehtävä on kertoa se, ja ennusteen
verdiktikappale kertoo sen joka kerta kun Pekurin syyskuuta kysytään.

---

## 8. Tuotokset

Yksi ajo on yksi hakemisto `data/quiet/{run_id}/` ja yksi rivi tiedostossa `index.json`.
Ajotunnisteet ovat deterministisiä ja luettavia, joten saman kuukauden ajaminen uudelleen
korvaa oman hakemistonsa eikä kerrytä lähes samanlaisia tuloksia.

| Tiedosto | Ennuste | Pyyhkäisy |
| --- | --- | --- |
| `report.md` | Vastaus, koko kuukausi, lähtötiedot, varaukset | Verdikti, tulokset, ikkunat, kalibrointi |
| `days.csv` | Kuukauden jokainen päivä per kohde | Jokainen ehdokaspäivä: pisteluku, toteuma, todennäköisyys |
| `windows.csv` | – | Yksi rivi per ikkuna, kohde ja sääntö |
| `metrics.json` | Joukko, ehdokkuus, jäännökset, päivät | Ikkunakohtaiset tulokset |
| `verdicts.json` | Yhteenveto ja mitattu luotettavuus | Kootut verdiktit ja kalibrointi |
| `config.json` | Kaikki ajon parametrit | Kaikki ajon parametrit |

Mikään ajohakemistossa ei sisällä kellonaikaa. Se on ainoa tapa, jolla determinismitesti
voidaan ylipäätään kirjoittaa. Luontihetki on `index.json`issa, joka on rekisteri eikä
tulos.

---

## 9. Tulos kolmessakymmenessä sekunnissa

Raportti alkaa kappaleella, jossa vastaus jo on. Jos haluat tarkistaa sen itse, neljä
lukua kantaa kokonaisuuden:

1. **Verdikti ja sen väli.** Olivatko nimetyt päivät todella hiljaisempia, ja ylittääkö
   väli nollan.
2. **Osuvuus satunnaisvalintaa vasten.** 40 % kuulostaa huonolta ja 67 % hyvältä, mutta
   kumpikaan ei tarkoita mitään ilman sitä, mitä arvaus antaisi.
3. **Todennäköisyys päivää kohden.** Tasainen 20 % kaikilla päivillä tarkoittaa, ettei
   malli erottele niitä. Korkea yksittäinen luku tarkoittaa, että se erottelee.
4. **Samanarvoisia-sarake.** Jos se on suurempi kuin yksi, mallilla ei ole mielipidettä
   ryhmän sisäisestä järjestyksestä ja valinta kuuluu sinulle.

---

## 10. Neljä tapaa huijata itseään

**Lukea mallin erottelu toteutuvana hyötynä.** "Hiljaisin viidennes on 18 %
mediaanipäivän alapuolella" on lause pisteluvusta. Toteutuva hyöty on 7 % tai 45 %
kohteesta riippuen, ja sen kertoo vain mittaus.

**Uskoa yhtä ikkunaa.** Yhden kuukauden kuusi päivää on yksi arvonta. Kooste useasta
ikkunasta on todistusaineisto, yksittäinen ikkuna on kuvaus.

**Ottaa liukuvan pyyhkäisyn väli sellaisenaan.** Peräkkäiset liukuvat ikkunat jakavat
päiviä, joten väli on todellista kapeampi. Otsikkoluku kannattaa lukea
kuukausipyyhkäisystä.

**Yleistää kohteesta toiseen.** Kaupungintalon 45 % ei kerro Pekurista mitään. Aukioloajat,
pyhäpäiväkäytäntö ja kävijäprofiili eroavat, ja mittaus tehdään kohteittain juuri siksi.

---

## 11. Mitä tästä EI voi päätellä

- **Että hiljaisin päivä olisi paras päivä.** Malli kertoo missä on vapaata kapasiteettia.
  Se ei tiedä, tavoittaako tapahtuma kohderyhmänsä sunnuntaina, eikä sitä ovatko henkilöstö
  tai kumppanit silloin käytettävissä.
- **Että sääntövalinta olisi todistettu.** Oletussääntö valittiin näiden samojen ikkunoiden
  perusteella, joten sen etu muihin sääntöihin nähden on yliarvio. Kohdekohtainen hyöty on
  sen sijaan mitattu opetusjakson ulkopuolelta ja se pätee.
- **Että tulos säilyisi, kun sen mukaan toimitaan.** Jos hiljaisina päivinä aletaan
  järjestää aktivointitapahtumia, ne muuttavat juuri niitä päiviä, joita malli ennustaa.
  Mittaus on toistettava tapahtumien alettua, ja tapahtumapäivät on merkittävä, muuten ne
  vääristävät sekä arkipäiväkeskiarvot että seuraavan mittauksen.
- **Että viisi ikkunaa riittäisi.** Pienin havaittava hyöty on jokaisessa verdiktissä
  mukana juuri siksi. Kahdestoista kuukausi on tämän mittauksen tärkein yksittäinen
  parannus.
- **Että `visitors_total` olisi kävijämäärä.** Se on sisään- ja ulostulotapahtumien summa,
  ks. README. Kaikki tämän dokumentin suhdeluvut ovat suhdelukuja, joten yksikkö kumoutuu,
  mutta kynnysarvo kävijätapahtumina ei ole päänlukumäärä.

---

## 12. Seuraavat askeleet

Järjestyksessä, vaikutuksen mukaan:

1. **Tapahtumakalenteri piirteeksi.** Sama johtopäätös kuin tasoennusteella
   (`docs/EVALUATION.md` luku 12). Pekurin kuukauden sisäisestä vaihtelusta 78 % on tällä
   hetkellä selittämätöntä, ja yksittäinen konsertti tai ryhmävaraus on todennäköisin
   selittäjä.
2. **Toinen vuosi historiaa.** Kuukausi-ikkunoita on viisi. Kahdellatoista pienin
   havaittava hyöty puolittuu, ja pyhäpäiväkerroin saisi ensimmäistä kertaa joulun ja
   juhannuksen.
3. **Aukiolokalenteri konfiguraatioon.** Suljetut arkipäivät päätellään nyt datasta 15 %:n
   kynnyksellä. Se toimii, mutta ylläpidetty aukiolotieto olisi oikea lähde, ja se poistaisi
   kynnyksen kokonaan.
4. **Tuntitason hiljaisuus.** Tapahtuma ei kestä vuorokautta. Tuntiprofiili on jo olemassa
   (`ovf_forecast.profile`), joten "kuukauden hiljaisin tiistai-iltapäivä" on saman
   rakenteen laajennus eikä uusi malli.
