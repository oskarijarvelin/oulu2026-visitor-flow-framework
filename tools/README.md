# tools

*In English: [`README.en.md`](README.en.md).*

Apuvälineitä, jotka eivät kuulu ingest- tai web-osioon. Nämä ajetaan käsin.

- [`tickets-parser.html`](#kävijätilastojen-muunnin) muuntaa aukiolotiimin
  kävijätilasto-CSV:n venuekohtaiseksi tickets-tiedostoksi.
- [`MUUNNOSRAPORTTI.md`](MUUNNOSRAPORTTI.md) on käsin ajetun muunnoksen raportti.
  Se on tämän työkalun tosiasiallinen määrittely ja regressiotestin vertailukohta.
- `fixtures/` sisältää aidot lähdetiedostot ja odotetun tuloksen.

---

## Kävijätilastojen muunnin

### Mihin ongelmaan tämä vastaa

Aukiolotiimi ylläpitää kävijämääristä Exceliä ja vie sen CSV:ksi. Framework taas
lukee venuekohtaisen tiedoston `data/raw/tickets/venue_{id}/tickets-venue-{id}.csv`,
jonka muoto on `DATE,TICKETS,GROUPS,TOTAL`. Näiden välissä on joka viikko sama
käsityö: eri sarakerakenne per venue, monen sarakkeen summia, kuukausiotsikoita ja
välisummarivejä keskellä dataa, tekstiä numerosarakkeissa ja epäluotettava
Yhteensä-sarake.

Työkalu tekee tämän muunnoksen selaimessa, näyttää mitä se aikoo tehdä ja kertoo
mitä lähdedatassa on vialla. Viikoittainen käyttö vie noin viisi minuuttia.

### Mitä luvut tarkoittavat

Lähdetiedostot ovat nimeltään **Kävijätilastot** ja niiden sarakkeet ovat kanavia:
varaus, verkkokauppa, ovelta, puhelin, ryhmät ja talon vieraat. Kyse ei siis ole
puhtaasta lipunmyynnistä vaan kävijämääristä kanavittain.

Frameworkin kentät `tickets_sold` ja `groups_sold` tarkoittavat tässä aineistossa
käytännössä **yksittäiskävijöitä** ja **ryhmäkävijöitä**. Näitä lukuja ei pidä
tulkita myyntiraportiksi eikä euromääräiseksi tuotoksi.

### Käyttö

Avaa `tools/tickets-parser.html` selaimessa suoraan tiedostojärjestelmästä. Ei
palvelinta, ei asennusta, ei verkkoyhteyttä.

```bash
open tools/tickets-parser.html
```

Yksi tiedosto, jossa on kaikki HTML, CSS ja JavaScript. Ei ulkoisia pyyntöjä, ei
CDN:ää, ei kirjastoja. Kaikki käsittely tapahtuu selaimessa, mitään ei lähetetä
mihinkään. Toimii Chromen, Safarin ja Firefoxin nykyversioilla.

**Vaihe 1, tiedoston valinta.** Pudota CSV, valitse tiedostonvalitsimella tai liitä
leikepöydältä. Työkalu tunnistaa merkistön, erottimen ja profiilin. Useamman
tiedoston voi käsitellä peräkkäin, tulokset kertyvät venueittain.

**Vaihe 2, esikatselu.** Taulukko lähderiveistä, sarakkeiden nimet ja indeksit.
Rivimäärä ja havaitut ongelmat.

**Vaihe 3, kartoitus.** Esitäytetty tunnistetusta profiilista, kaikki muokattavissa:
päivämääräsarake ja muoto, TICKETS- ja GROUPS-sarakkeet monivalintana, valinnainen
ristiintarkistussarake, venue ja rajapäivä. Kartoituksen voi tallentaa nimettynä
profiilina selaimen localStorageen.

**Vaihe 4, tulos ja tarkistukset.** Yhteenveto, varoitukset omina riveinään ja
pylväskaavio. Jokainen varoitus kertoo rivinumeron lähdetiedostossa, ja siitä pääsee
klikkaamalla suoraan kyseiselle riville esikatselussa.

**Vaihe 5, yhdistäminen.** Lataa repossa oleva nykyinen tickets-tiedosto, niin
työkalu näyttää erotuksen: lisätyt päivät, muuttuneet päivät vanhoine ja uusine
arvoineen, ja poistuneet päivät.

**Vaihe 6, vienti.** Lataa venuekohtainen tiedosto ja tarkistusta varten yhdistetty
`tickets_daily.csv`. Molemmat myös leikepöydälle.

Vaiheiden välillä voi liikkua vapaasti edistymisen osoittimesta, työ ei katoa.

### Sarakekartoitus

Sarakkeet tunnistetaan **ensisijaisesti indeksin perusteella**, otsikon nimi on
varmistus. Otsikoiden vertailussa poistetaan alku- ja loppuvälilyönnit ja ohitetaan
kirjainkoko, koska lähteessä on esimerkiksi `Ryhmät ` perässä välilyönnillä.

#### Profiili A: Pekuri, venue 1

Otsikkorivi: `;Päivämäärä;Yleisöä;Ryhmät;Yhteensä;...`

| Sarake | Otsikko | Käyttö |
| --- | --- | --- |
| 0 | (nimetön) | viikonpäivä, otsikkosarake |
| 1 | `Päivämäärä` | päivämäärä, muoto `d.m.yyyy` |
| 2 | `Yleisöä` | **TICKETS** |
| 3 | `Ryhmät` | **GROUPS** |
| 4 | `Yhteensä` | vain ristiintarkistus |
| 5 ja siitä eteenpäin | (nimetön) | muistiinpanoja ja irrallisia viikkosummia, ohitetaan |

Tunnistetaan otsikosta `Yleisöä`.

#### Profiili B: Kaupungintalo, venue 2

Otsikkorivi:
`;Päivämäärä;Varaus;Verkkokauppa tilastot;Ovelta;Ktalon puh tilasto;Ryhmät ;KUTOSET;Ktalon vieraat;Yhteensä;Lisätietoa;...`

| Sarake | Otsikko | Käyttö |
| --- | --- | --- |
| 0 | (nimetön) | viikonpäivä, otsikkosarake |
| 1 | `Päivämäärä` | päivämäärä, muoto `d.m.yyyy` |
| 2 | `Varaus` | **TICKETS**, summattava |
| 3 | `Verkkokauppa tilastot` | **TICKETS**, summattava |
| 4 | `Ovelta` | **TICKETS**, summattava |
| 5 | `Ktalon puh tilasto` | **TICKETS**, summattava |
| 6 | `Ryhmät ` (perässä välilyönti) | **GROUPS**, summattava |
| 7 | `KUTOSET` | **GROUPS**, summattava |
| 8 | `Ktalon vieraat` | **GROUPS**, summattava |
| 9 | `Yhteensä` | vain ristiintarkistus |
| 10 | `Lisätietoa` | muistiinpanoja, ohitetaan |
| 11 ja siitä eteenpäin | (nimetön) | roskaa: `#ARVO!`, juoksevia summia, sarjanumeroita, ohitetaan |

Tunnistetaan otsikoista `Verkkokauppa tilastot` tai `KUTOSET`.

Molemmilla `TOTAL = TICKETS + GROUPS`.

### Miksi lähteen Yhteensä-saraketta ei kirjoiteta tulokseen

Se on epäluotettava. Pekurissa se on tyhjä 18 rivillä ja Kaupungintalossa 55
rivillä, ja siihen on valunut kuukausi- ja viikkosummia päivien riveille.
`TOTAL` lasketaan siksi **aina** komponenteista, ja Yhteensä-saraketta käytetään
vain ristiintarkistukseen, joka tuottaa varoituksen jos se eroaa lasketusta.

### Tunnetut lähdedatan ongelmat

Kaikki nämä on löydetty aidosta datasta. Työkalu käsittelee ne ja raportoi ne.

**Ohitettavat rivit.** Kuukausiotsikot (`Helmikuu`, `Maaliskuu`), välisummarivit
(`Yhteensä`), tyhjät rivit ja rivit joissa päivämääräsarake on tyhjä.

**Loppupään tyhjät päivärivit.** Tiedostojen lopussa on valmiiksi kalenteroituja
päiviä ilman yhtään merkintää, Kaupungintalossa 18.9.2026 asti. Nämä ohitetaan.
Huomaa ero: keskellä tiedostoa oleva tyhjä päivärivi on **aito nollapäivä** ja se
kirjoitetaan tulokseen nollana, koska nolla on aito havainto.

**Tekstiarvot numerosarakkeissa.** Tulkitaan nollaksi ja merkitään varoitukseksi,
alkuperäinen teksti näytetään.

| Venue | Rivi | Päivä | Sarake | Arvo |
| --- | --- | --- | --- | --- |
| 2 | 36 | 13.2.2026 | `Varaus` | `Suljettu` |
| 2 | 108 | 23.4.2026 | `Varaus` | `suljettu` |
| 2 | 203 | (25.6.2026) | `Varaus` | `suljettu` |
| 2 | 218 | 9.8.2026 | `Verkkokauppa tilastot` | `ei löytynyt?` |

Rivin 218 `ei löytynyt?` on eri asia kuin nolla: verkkokaupan luku on tuntematon.
Kyseiselle päivälle kirjattiin 42 kävijää muista kanavista, joten todellinen luku on
tätä suurempi. Kannattaa selvittää aukiolotiimiltä.

**Ristiintarkistuksen poikkeamat.** Nämä eivät vaikuta tulokseen, koska TOTAL
lasketaan komponenteista, mutta ne kannattaa korjata lähteeseen.

| Venue | Rivi | Päivä | Komponentit | Lähteen Yhteensä | Selitys |
| --- | --- | --- | --- | --- | --- |
| 1 | 79 | 30.3.2026 | 37 | 58 | arvot vaihtaneet paikkaa rivin 80 kanssa |
| 1 | 80 | 31.3.2026 | 58 | 37 | sama |
| 1 | 142 | 30.5.2026 | 35 | 2 251 | kuukausisumma valunut päivän riville |
| 2 | 163 | 15.6.2026 | 0 | 475 | viikkosumma väärässä sarakkeessa |
| 2 | 213 | 4.8.2026 | 113 | 101 | |

**Päivämäärä epäjärjestyksessä.** Kaupungintalon rivillä 203 lukee `25.6.2026`,
mutta rivi sijaitsee rivien `24.7.2026` ja `26.7.2026` välissä ja sen viikonpäivä on
`Lauantai`. 25.7.2026 on lauantai, 25.6.2026 on torstai, joten kyseessä on lähes
varmasti kirjoitusvirhe.

**Työkalu ei korjaa tätä automaattisesti.** Se havaitsee epäjärjestyksen, ehdottaa
päivää 25.7.2026 ja pyytää käyttäjää päättämään: korjaa ehdotettuun päivään, pidä
sellaisenaan tai ohita rivi. Oletus on pitää sellaisenaan, jolloin rivin nollat
summautuvat oikeaan 25.6.2026 päivään eivätkä muuta sitä. Seurauksena **25.7.2026
puuttuu tuloksesta**. Tämä on tietoinen päätös, katso
[MUUNNOSRAPORTTI.md](MUUNNOSRAPORTTI.md).

**Ennakkovaraukset ja kesken oleva päivä.** Kaupungintalon rivillä 245 on 5.9.2026 ja
200 hengen ryhmä. Se on ennakkovaraus, ei toteutunut kävijämäärä. Työkalu rajaa pois
rajapäivän ja sitä myöhemmät päivät ja listaa ne erikseen. Rajapäivä on oletuksena
kuluva päivä, koska se on vielä kesken. Käyttäjä voi vaihtaa rajapäivää tai ottaa
rajatut päivät mukaan.

**Nollapäivät.** Kaupungintalossa on paljon päiviä joilla kaikki komponentit ovat
nollia, pääosin maanantaita jolloin kohde on kiinni. Nämä kirjoitetaan tulokseen
nollina. Käyttöliittymä erottelee "kiinni (Suljettu)" ja "auki, ei kävijöitä" sen
mukaan onko lähteessä Suljettu-merkintä.

### Tuloksen vienti repoon

1. Lataa venuekohtaiset tiedostot vaiheessa 6.
2. Kopioi ne kohdepolkuihin. Polut tulevat tiedostosta `config/venues.json`
   kentästä `tickets_path`:

   ```
   data/raw/tickets/venue_1/tickets-venue-1.csv
   data/raw/tickets/venue_2/tickets-venue-2.csv
   ```

3. Tarkista muutos ennen kuin viet sen eteenpäin:

   ```bash
   git diff data/raw/tickets
   ```

4. Aja ingest:

   ```bash
   python -m ovf_ingest run
   ```

   Se tuottaa tiedoston `data/processed/tickets_daily.csv`.

Vaiheessa 6 ladattavan `tickets_daily.csv`:n voi verrata ingestin tuotokseen, jos
haluat varmistaa että normalisointi menee odotetusti. Ingest tuottaa saman tiedoston
itse, joten tätä ei viedä repoon.

### Vientimuoto

`tickets-venue-{id}.csv`:

- otsikkorivi `DATE,TICKETS,GROUPS,TOTAL`
- erotin pilkku
- päivämäärä `d.m.yyyy` **ilman etunollia**: `14.1.2026`, ei `14.01.2026`
- rivinvaihto `\n`, merkistö UTF-8 ilman BOMia
- kokonaisluvut ilman desimaaleja

`tickets_daily.csv`:

- otsikkorivi `venue_id,date,tickets_sold,groups_sold,tickets_total`
- päivämäärä ISO-muodossa

### Itsetestit

Lisää osoitteen perään `?selftest=1`:

```
file:///.../tools/tickets-parser.html?selftest=1
```

Testit ajetaan ja tulos näytetään taulukkona. Selaimen välilehden otsikkoon tulee
`OK 72/72` tai `VIRHE n/72`. Testejä on 72 ja ne kattavat CSV-jäsennyksen
(lainausmerkit, upotettu erotin, upotettu rivinvaihto, CRLF, BOM, vajaat rivit,
suorituskyky), cp1252-dekoodauksen, erottimen ja profiilin tunnistuksen molemmilla
aidoilla otsikkoriveillä, päivämäärän jäsennyksen jokaisella tuetulla muodolla ja
virheellisillä syötteillä, monen sarakkeen summauksen, roskarivien tunnistuksen,
tekstiarvot, ristiintarkistuksen, epäjärjestyksen, yhdistämisen ja vientimuodon.

Testit ajetaan samasta koodista kuin työkalu itse, joten ne todistavat että selain
jossa ne ajetaan käyttäytyy odotetusti.

---

## Regressiotestit aitoa dataa vasten

Nämä ajetaan käsin. Ne ovat työkalun tärkein hyväksymiskriteeri, koska odotettu
tulos on tiedossa tarkalleen.

**Aseta ensin rajapäiväksi `24.8.2026`** vaiheessa 3. Muunnos ajettiin käsin
24.8.2026, joten vertailutiedostot on rajattu siihen. Ilman tätä työkalu käyttää
kuluvaa päivää, jolloin tulokseen tulee mukaan päiviä jotka olivat tuolloin vielä
tulevaisuudessa.

Ajettu 25.8.2026, kaikki viisi menivät läpi.

### 1. Pekuri, profiili A

Lähde `tools/fixtures/kavijatilastot-pekuri.csv`, tulos vertailuun
`data/raw/tickets/venue_1/tickets-venue-1.csv`.

| Mitta | Odotettu | Tulos |
| --- | --- | --- |
| Rivejä | 222 | 222 |
| Aikaväli | 14.1. - 23.8.2026 | 14.1. - 23.8.2026 |
| Yksittäisliput | 13 957 | 13 957 |
| Ryhmät | 3 631 | 3 631 |
| Yhteensä | 17 588 | 17 588 |
| Tavu tavulta identtinen | kyllä | **kyllä** |

### 2. Kaupungintalo, profiili B

Lähde `tools/fixtures/kavijatilastot-kaupungintalo.csv`, tulos vertailuun
`data/raw/tickets/venue_2/tickets-venue-2.csv`.

| Mitta | Odotettu | Tulos |
| --- | --- | --- |
| Rivejä | 222 | 222 |
| Aikaväli | 13.1. - 23.8.2026 | 13.1. - 23.8.2026 |
| Yksittäisliput | 11 775 | 11 775 |
| Ryhmät | 5 281 | 5 281 |
| Yhteensä | 17 056 | 17 056 |
| Tavu tavulta identtinen | kyllä | **kyllä** |

25.7.2026 **ei** ole tuloksessa, koska lähteen rivillä 203 on kirjoitusvirhe. Tämä on
tarkoituksellista.

### 3. Molemmat yhdessä normalisoituna

Tulos vertailuun `tools/fixtures/expected-tickets_daily.csv`.

444 riviä, identtinen.

### 4. Yhdistämistila samoilla tiedostoilla

Erotus repon nykyisiin tiedostoihin:

| Venue | Lisätty | Muuttunut | Poistunut | Ennallaan |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | 0 | 222 |
| 2 | 0 | 0 | 0 | 222 |

**Tyhjä erotus on onnistumisen merkki, ei virhe.** Repon tiedostot on jo muunnettu
näistä samoista lähteistä. Kun aukiolotiimi toimittaa seuraavan viennin, erotus
näyttää uudet ja korjatut päivät.

### 5. Varoitukset ja ohitetut rivit

Kaikki luvussa "Tunnetut lähdedatan ongelmat" luetellut tapaukset näkyvät
varoituksina.

| | Varoitukset | Ohitetut: roskarivit | Ohitetut: loppupään tyhjät | Rajatut: kuluva ja tulevat |
| --- | --- | --- | --- | --- |
| Venue 1 | 3 | 6 | 3 | 0 |
| Venue 2 | 9 | 8 | 13 | 13 |

Venue 1: kolme ristiintarkistuksen poikkeamaa, rivit 79, 80 ja 142.

Venue 2: neljä tekstiarvoa (rivit 36, 108, 203, 218), kaksi ristiintarkistuksen
poikkeamaa (rivit 163, 213), yksi epäjärjestys (rivi 203) ja yksi duplikaattipäivä
(rivi 203, koska 25.6.2026 on jo aiemmin), sekä yksi huomautus epäuskottavan suuresta
arvosta.

Kaksi eroa `MUUNNOSRAPORTTI.md`:n lukuihin, molemmat selitettävissä:

- **Venue 1 ohittaa 6 roskariviä, ei 5.** Raportin lista (rivit 20, 49, 81, 112, 232)
  ei sisällä riviä 144, joka on täysin tyhjä. Työkalu laskee sen mukaan, koska
  jokainen ohitettu rivi näkyy syineen eikä yhtään riviä pudoteta hiljaisesti.
- **Venue 2 tuottaa 9 varoitusta, ei 8.** Yhdeksäs on huomautus 5.5.2026:
  yhteensä 279 on yli viisinkertainen edeltävän 28 vuorokauden mediaaniin (46)
  nähden. Käsin ajetussa muunnoksessa ei ollut tätä tarkistusta. Kyseessä ei ole
  datavirhe: päivän luvut ovat sisäisesti ristiriidattomat (68 yksittäistä, 211
  ryhmää, lähteen Yhteensä 279), joten kyseessä on aito poikkeuksellisen vilkas
  päivä. Huomautus on tarkoitettu juuri tällaisten silmäilyyn, ei hylkäämiseen.

### Miten vertailun tekee

Lataa tiedosto vaiheessa 6 ja vertaa:

```bash
diff ~/Downloads/tickets-venue-1.csv data/raw/tickets/venue_1/tickets-venue-1.csv
```

Tyhjä tuloste tarkoittaa että tiedostot ovat tavu tavulta samat.

---

## Rajoitteet

- Yksi tiedosto, ei build-vaihetta, ei riippuvuuksia, ei ulkoisia pyyntöjä.
- Työkalu toimii yksityisessä selainikkunassa, jossa `localStorage` heittää
  poikkeuksen. Tallennus ohitetaan, muu toiminta jatkuu normaalisti.
- Leikepöydältä liittäminen tuottaa aina UTF-8-tekstiä. Jos ääkköset näyttävät
  väärältä, pudota tiedosto sen sijaan että liittäisit sisällön.
- Tiedoston koko noin 115 kB.
