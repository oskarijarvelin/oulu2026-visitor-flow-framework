# Ennusteen arviointiraportti: 2026-08-01 – 2026-08-25

Ajon tunniste: `eval_v1_2026-07-31_2026-08-01_2026-08-25_baseline`

## 1. Verdikti

Ikkuna 2026-08-01–2026-08-25 (25 vrk), koulutus päättyy 2026-07-31, koulutusikkuna all, sään tila operational. Venue 1 (Pekuri): malli baseline teki keskimäärin 248,2 kävijän päivävirheen, päävertailukohta climatology_dow 131,0. Malli häviää vertailukohdalle tilastollisesti: ero +117,2 kävijää päivässä (95 % väli +18,0…+167,7). Yksinkertainen sääntö climatology_dow on tällä ikkunalla parempi kuin malli. Tämä otos (25 päivää) olisi erottanut vasta 84,5 kävijän eron, eli 64,5 % vertailukohdan MAE:sta. Jakson kokonaismäärä: ennuste 16 410, toteuma 11 477, ero +43,0 %, 80 % väli 15 961–23 474. Venue 2 (Kaupungintalo): malli baseline teki keskimäärin 30,1 kävijän päivävirheen, päävertailukohta climatology_dow 32,3. Eroa ei havaittu: -2,3 kävijää päivässä (95 % väli -9,6…+9,8). Tämä otos (25 päivää) olisi erottanut vasta 10,8 kävijän eron, eli 33,4 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 3 636, toteuma 3 995, ero -9,0 %, 80 % väli 3 636–11 166. Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.

## 2. Ikkuna ja asetelma

- Origo (viimeinen koulutuspäivä): **2026-07-31**
- Testijakso: **2026-08-01 – 2026-08-25** (25 vrk, horisontit 1–25)
- Koulutusikkuna: `all`
- Mallit: baseline
- Vertailukohdat: seasonal_naive, moving_average_28d, climatology_dow
- Päävertailukohdan valinta: `best`
- Sään tilat: perfect, operational, climatology (verdikti tilasta `operational`)
- Bootstrap: 10 000 uudelleenotantaa, lohkon pituus 7 vrk, siemen 20260101

| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 212 | 21 | 12 | 163,08 |
| 2 (Kaupungintalo) | 2026-01-01 | 212 | 13 | 12 | 100,17 |

Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten yksikään sisäennuste ei ylety testijaksoon.

## Venue 1 (Pekuri)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 16 410 | 11 477 | +4 933 | +43,0 % | 15 961 – 23 474 | ei | 9 944 – 31 205 |
| climatology_dow | 11 442 | 11 477 | -35 | -0,3 % | 10 608 – 13 999 | kyllä | 7 300 – 20 388 |
| moving_average_28d | 14 084 | 11 477 | +2 607 | +22,7 % | 12 540 – 17 141 | ei | 8 004 – 23 782 |
| seasonal_naive | 15 276 | 11 477 | +3 799 | +33,1 % | 15 276 – 21 511 | ei | 7 743 – 30 683 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 248,2 | 276,5 | 1,522 | +197,3 | 43,7 | 124,1 | 78,9 | 0,56 | 46,5 | 25 |
| baseline | 1-7 | 244,8 | 267,4 | 1,501 | +244,8 | 15,4 | 122,4 | 64,5 | 0,71 | 43,6 | 7 |
| baseline | 8-14 | 196,8 | 219,7 | 1,207 | +36,0 | 27,0 | 98,4 | 57,9 | 0,86 | 33,6 | 7 |
| baseline | 15-30 | 283,0 | 312,3 | 1,735 | +269,8 | 72,4 | 141,5 | 101,4 | 0,27 | 56,5 | 11 |
| climatology_dow | all | 131,0 | 189,6 | 0,803 | -1,4 | 26,8 | 65,5 | 48,3 | 0,80 | 27,0 | 25 |
| climatology_dow | 1-7 | 82,8 | 95,4 | 0,508 | +24,4 | 15,0 | 41,4 | 36,6 | 1,00 | 17,6 | 7 |
| climatology_dow | 8-14 | 178,0 | 276,9 | 1,091 | -125,8 | 30,4 | 89,0 | 68,4 | 0,71 | 29,6 | 7 |
| climatology_dow | 15-30 | 131,8 | 164,7 | 0,808 | +61,4 | 32,0 | 65,9 | 42,9 | 0,73 | 31,3 | 11 |
| moving_average_28d | all | 195,3 | 224,1 | 1,197 | +104,3 | 27,3 | 97,6 | 53,4 | 0,72 | 39,5 | 25 |
| moving_average_28d | 1-7 | 131,1 | 145,7 | 0,804 | +131,1 | 12,5 | 65,5 | 43,7 | 0,86 | 27,3 | 7 |
| moving_average_28d | 8-14 | 219,8 | 264,4 | 1,348 | -19,1 | 33,7 | 109,9 | 54,7 | 0,71 | 38,2 | 7 |
| moving_average_28d | 15-30 | 220,6 | 237,0 | 1,353 | +165,7 | 32,7 | 110,3 | 58,9 | 0,64 | 48,2 | 11 |
| seasonal_naive | all | 213,7 | 268,1 | 1,311 | +152,0 | 28,9 | 106,9 | 76,8 | 0,76 | 40,4 | 25 |
| seasonal_naive | 1-7 | 196,4 | 227,6 | 1,205 | +163,9 | 11,7 | 98,2 | 80,2 | 1,00 | 36,4 | 7 |
| seasonal_naive | 8-14 | 170,3 | 242,1 | 1,044 | +13,7 | 30,9 | 85,1 | 67,7 | 1,00 | 28,6 | 7 |
| seasonal_naive | 15-30 | 252,4 | 305,0 | 1,548 | +232,4 | 38,5 | 126,2 | 80,5 | 0,45 | 50,4 | 11 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 131,0). Vertailukohtien MAE: seasonal_naive 213,7, moving_average_28d 195,3, climatology_dow 131,0.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +117,2 | +18,0 … +167,7 | huonompi kuin vertailukohta | -0,894 | -1,595 … -0,108 | 84,5 | 64,5 % | 2,37 | 0,077 | 0,153 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,56 (14/25) | 0,35 … 0,76 | liian kapea | +197,3 | +48,0 … +280,6 | +43,0 % | yliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 218,3 | 248,2 | 244,7 | +26,5 | 10,8 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 25 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 9 |
| climatology (klimatologia koko jaksolta) | 0 | 25 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-08-22 | lauantai | 287 | 789 | +502 | malli sai klimatologiasään (horisontti 22 vrk); viikonloppu |
| 2026-08-04 | tiistai | 397 | 835 | +438 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-08-14 | perjantai | 1 084 | 668 | -416 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-08-24 | maanantai | 313 | 714 | +401 | malli sai klimatologiasään (horisontti 24 vrk) |
| 2026-08-18 | tiistai | 360 | 730 | +370 | runsas sade 7.0 mm; malli sai klimatologiasään (horisontti 18 vrk) |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## Venue 2 (Kaupungintalo)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 3 636 | 3 995 | -359 | -9,0 % | 3 636 – 11 166 | kyllä | 1 672 – 10 222 |
| climatology_dow | 4 079 | 3 995 | +84 | +2,1 % | 3 533 – 4 774 | kyllä | 1 930 – 6 484 |
| moving_average_28d | 5 123 | 3 995 | +1 128 | +28,2 % | 4 914 – 7 258 | ei | 743 – 10 378 |
| seasonal_naive | 4 500 | 3 995 | +505 | +12,6 % | 4 306 – 12 677 | ei | 1 953 – 11 058 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

⚠ **Näiden mallien väli ei ole kalibroitu:** baseline (suhteellisten virheiden mediaani 1,28). Sisäkkäisen backtestin mallit on koulutettu lyhyemmällä ja huonommalla aineistolla kuin ulompi malli, joten niiden virheissä on tasosiirtymä eikä pelkkää hajontaa. Väli perii sen. Lue kokonaismäärän ero ja bias erikseen, älä väliä.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 30,1 | 52,8 | 0,300 | -14,4 | 9,3 | 15,0 | 24,9 | 0,96 | 22,7 | 25 |
| baseline | 1-7 | 12,4 | 17,9 | 0,124 | -9,1 | 10,2 | 6,2 | 28,6 | 1,00 | 10,2 | 7 |
| baseline | 8-14 | 33,5 | 42,8 | 0,335 | -31,7 | 10,7 | 16,8 | 20,1 | 0,86 | 27,9 | 7 |
| baseline | 15-30 | 39,1 | 70,5 | 0,390 | -6,7 | 7,8 | 19,5 | 25,6 | 1,00 | 27,3 | 11 |
| climatology_dow | all | 32,3 | 50,5 | 0,323 | +3,4 | 8,3 | 16,2 | 12,8 | 0,88 | 21,8 | 25 |
| climatology_dow | 1-7 | 16,9 | 19,4 | 0,169 | +1,9 | 9,3 | 8,4 | 8,9 | 1,00 | 9,6 | 7 |
| climatology_dow | 8-14 | 25,6 | 40,2 | 0,255 | -9,5 | 9,9 | 12,8 | 9,9 | 0,86 | 19,7 | 7 |
| climatology_dow | 15-30 | 46,4 | 67,2 | 0,464 | +12,4 | 6,7 | 23,2 | 17,2 | 0,82 | 30,7 | 11 |
| moving_average_28d | all | 70,0 | 90,5 | 0,699 | +45,1 | 14,4 | 35,0 | 25,5 | 0,88 | 46,2 | 25 |
| moving_average_28d | 1-7 | 53,7 | 76,4 | 0,536 | +40,5 | 14,6 | 26,8 | 24,6 | 0,86 | 37,2 | 7 |
| moving_average_28d | 8-14 | 57,4 | 76,4 | 0,573 | +29,1 | 15,0 | 28,7 | 22,5 | 1,00 | 36,1 | 7 |
| moving_average_28d | 15-30 | 88,5 | 105,8 | 0,883 | +58,3 | 13,9 | 44,2 | 28,0 | 0,82 | 58,3 | 11 |
| seasonal_naive | all | 101,2 | 133,5 | 1,010 | +20,2 | 9,3 | 50,6 | 63,6 | 0,76 | 69,2 | 25 |
| seasonal_naive | 1-7 | 79,9 | 104,0 | 0,797 | +18,4 | 10,2 | 39,9 | 64,9 | 0,86 | 56,4 | 7 |
| seasonal_naive | 8-14 | 87,3 | 107,8 | 0,871 | +7,0 | 9,0 | 43,6 | 47,7 | 0,71 | 67,9 | 7 |
| seasonal_naive | 15-30 | 123,5 | 161,9 | 1,233 | +29,7 | 8,9 | 61,8 | 72,8 | 0,73 | 78,1 | 11 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 32,3). Vertailukohtien MAE: seasonal_naive 101,2, moving_average_28d 70,0, climatology_dow 32,3.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | -2,3 | -9,6 … +9,8 | ei havaittavaa eroa vertailukohtaan | 0,070 | -0,249 … 0,318 | 10,8 | 33,4 % | -0,35 | 0,765 | 0,765 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,96 (24/25) | 0,80 … 1,00 | kalibroitu | -14,4 | -45,5 … +5,9 | -9,0 % | ei systemaattista harhaa |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 31,8 | 30,1 | 33,1 | +1,4 | 4,1 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 25 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 9 |
| climatology (klimatologia koko jaksolta) | 0 | 25 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-08-15 | lauantai | 371 | 155 | -216 | runsas sade 8.7 mm; viikonloppu |
| 2026-08-13 | torstai | 284 | 190 | -94 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-08-18 | tiistai | 155 | 212 | +57 | runsas sade 7.0 mm; malli sai klimatologiasään (horisontti 18 vrk) |
| 2026-08-19 | keskiviikko | 138 | 194 | +56 | runsas sade 8.3 mm; malli sai klimatologiasään (horisontti 19 vrk) |
| 2026-08-06 | torstai | 176 | 134 | -42 | runsas sade 15.2 mm |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## 8. Rajoitteet

- **Otoskoko.** Yksi ikkuna on 25 päivää yhdestä origosta. Ne eivät ole 25 riippumatonta havaintoa: kaikki jakavat saman koulutusjoukon ja saman kuukauden sään.
- **Yhden ikkunan verdikti on kuvaileva, ei todistava.** Varsinainen näyttö syntyy usean ikkunan koosteesta (`--sweep monthly` tai `--sweep rolling`).
- **"Ei havaittavaa eroa" ei tarkoita samanveroisuutta.** Lue MDE kohdasta 5 ennen kuin teet siitä johtopäätöksen.
- **sMAPEa ei käytetä verdiktin perustana**, koska nollapäivät rikkovat sen.
- **Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta.** Vuosikausivaihtelua ei voi oppia, joten vertailu toiseen vuoteen ei ole mahdollinen.
- **Lippudataa ei käytetä piirteenä**, koska sitä ei ole tulevaisuudelle.
- **Venue 1: koulutusikkunan alussa on 21 nollapäivää** sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.
- **Venue 2: koulutusikkunan alussa on 7 nollapäivää** sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.
