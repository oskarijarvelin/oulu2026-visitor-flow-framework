# Lippudatan muunnosraportti

Ajettu 24.8.2026. Lähteenä aukiolotiimin kävijätilasto-CSV:t, jotka ovat repossa
polussa `tools/fixtures/`.

Muunnos noudattaa täsmälleen niitä sääntöjä, jotka on kirjattu promptiin 4
(`docs/CLAUDE_CODE_PROMPTS.md`). Tämä ajo toimii samalla vertailukohtana, jota vasten
valmiin selaintyökalun tulos voidaan tarkistaa: työkalun on tuotettava identtiset
tiedostot.

## Tulos

| | Pekuri (venue 1) | Kaupungintalo (venue 2) |
| --- | --- | --- |
| Päiviä | 222 | 222 |
| Aikaväli | 14.1. - 23.8.2026 | 13.1. - 23.8.2026 |
| Yksittäisliput | 13 957 | 11 775 |
| Ryhmäliput | 3 631 | 5 281 |
| Yhteensä | 17 588 | 17 056 |
| Nollapäiviä | 1 | 33 |
| Aukkoja sarjassa | ei yhtään | 25.7.2026 puuttuu |

## Muutos nykyisiin tiedostoihin

| | Pekuri | Kaupungintalo |
| --- | --- | --- |
| Lisätty päiviä | 98 (18.5. - 23.8.) | 97 (18.5. - 23.8.) |
| Muuttunut päiviä | 0 | 75 |
| Poistunut päiviä | 0 | 0 |

**Pekuri täsmää täydellisesti.** Kaikki 124 aiempaa päivää säilyivät muuttumattomina, ja
päälle tuli 98 uutta päivää. Tämä on vahvin mahdollinen todiste siitä että sarakekartoitus
on oikea.

**Kaupungintalon 75 muuttunutta päivää eivät ole muunnosvirhe.** Ryhmäluvut säilyivät
muuttumattomina kaikilla 125 aiemmalla päivällä. Muutokset koskevat vain yksittäislippuja,
ne menevät molempiin suuntiin (45 päivää ylös, 30 alas, vaihteluväli -56 ... +68) ja koko
jakson summa muuttuu vain 6 kävijää alaspäin. Aukiolotiimi on siis korjannut Excelin
lukuja sen jälkeen kun nykyinen tiedosto tehtiin. Uudet luvut ovat oikeat.

Varmistin tämän vielä erikseen kokeilemalla tyhjentävästi kaikki mahdolliset
sarakeyhdistelmät. Mikään muu kartoitus ei tuota parempaa osumaa nykyiseen tiedostoon,
joten kyse ei ole väärästä sarakevalinnasta.

## Käytetty kartoitus

**Pekuri:** `TICKETS = Yleisöä`, `GROUPS = Ryhmät`

**Kaupungintalo:**
`TICKETS = Varaus + Verkkokauppa tilastot + Ovelta + Ktalon puh tilasto`
`GROUPS = Ryhmät + KUTOSET + Ktalon vieraat`

Molemmilla `TOTAL = TICKETS + GROUPS`. Lähteen `Yhteensä`-saraketta käytettiin vain
ristiintarkistukseen, koska se on epäluotettava. Tuloksessa ei ole yhtään riviä, jolla
TOTAL ei olisi komponenttien summa.

## Vaatii huomiota

### 1. Kaupungintalon 25.7.2026 puuttuu

Lähteen rivillä 203 lukee päivämääränä 25.6.2026, mutta rivi sijaitsee rivien 24.7.2026
ja 26.7.2026 välissä ja sen `Varaus`-sarakkeessa lukee "suljettu". Kyseessä on lähes
varmasti kirjoitusvirhe, jonka pitäisi olla 25.7.2026.

En korjannut tätä automaattisesti. Rivi käsiteltiin sellaisenaan, jolloin sen nollat
summautuivat oikeaan 25.6.2026 päivään eivätkä muuttaneet sitä. Seurauksena 25.7.2026
puuttuu tuloksesta kokonaan.

Vaikutus on pieni: ingest täyttää havaintojakson sisällä olevat puuttuvat päivät nollalla,
mikä vastaa "suljettu"-merkintää. Jos haluat rivin mukaan eksplisiittisesti, korjaa
lähdetiedostoon päiväksi 25.7.2026 ja aja muunnos uudelleen.

### 2. Ristiintarkistuksen poikkeamat

Nämä eivät vaikuttaneet tulokseen, koska TOTAL lasketaan komponenteista, mutta ne
kannattaa korjata lähteeseen jotta Excelin omat summat pitävät paikkansa:

| Venue | Rivi | Päivä | Komponentit | Lähteen Yhteensä |
| --- | --- | --- | --- | --- |
| Pekuri | 79 | 30.3.2026 | 37 | 58 |
| Pekuri | 80 | 31.3.2026 | 58 | 37 |
| Pekuri | 142 | 30.5.2026 | 35 | 2 251 |
| Kaupungintalo | 163 | 15.6.2026 | 0 | 475 |
| Kaupungintalo | 213 | 4.8.2026 | 113 | 101 |

Rivien 79 ja 80 kohdalla Yhteensä-arvot näyttävät vaihtaneen paikkaa keskenään.
Rivin 142 arvo 2 251 on kuukausisumma, joka on valunut päivän riville. Rivin 163 arvo 475
on viikkosumma väärässä sarakkeessa.

### 3. Tekstiarvot numerosarakkeissa

Tulkittiin nolliksi:

| Rivi | Päivä | Sarake | Arvo |
| --- | --- | --- | --- |
| 36 | 13.2.2026 | Varaus | "Suljettu" |
| 108 | 23.4.2026 | Varaus | "suljettu" |
| 203 | (25.6.2026) | Varaus | "suljettu" |
| 218 | 9.8.2026 | Verkkokauppa tilastot | "ei löytynyt?" |

Rivin 218 "ei löytynyt?" on eri asia kuin nolla: verkkokaupan luku on tuntematon, ei
nolla. Kyseiselle päivälle kirjattiin 42 kävijää muista kanavista, joten todellinen luku
on tätä suurempi. Kannattaa selvittää aukiolotiimiltä.

### 4. Tulevaisuuden ennakkovaraus jätettiin pois

Kaupungintalon rivi 245: 5.9.2026, 200 hengen ryhmä. Tämä on ennakkovaraus eikä toteutunut
kävijämäärä, joten se ei kuulu historiadataan. Kaikki tämän päivän jälkeiset päivät
rajattiin pois.

## Ohitetut rivit

Nämä ovat lähteen rakenteesta johtuvia, eivät virheitä:

- Pekuri: 5 tyhjää välisummariviä (rivit 20, 49, 81, 112, 232)
- Kaupungintalo: kuukausiotsikot "Helmikuu" (rivi 23) ja "Maaliskuu" (rivi 53),
  välisummarivi "Yhteensä" (rivi 21) sekä 4 tyhjää riviä

## Sanasto

Lähdetiedostot ovat nimeltään Kävijätilastot ja niiden sarakkeet ovat kanavia, eivät
lipputuotteita. Frameworkin kentät `tickets_sold` ja `groups_sold` tarkoittavat tässä
aineistossa käytännössä yksittäiskävijöitä ja ryhmäkävijöitä. Lukuja ei siis pidä tulkita
myyntiraportiksi.
