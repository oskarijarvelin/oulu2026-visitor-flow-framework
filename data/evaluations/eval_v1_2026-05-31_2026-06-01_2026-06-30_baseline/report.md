# Ennusteen arviointiraportti: 2026-06-01 – 2026-06-30

Ajon tunniste: `eval_v1_2026-05-31_2026-06-01_2026-06-30_baseline`

## 1. Verdikti

Ikkuna 2026-06-01–2026-06-30 (30 vrk), koulutus päättyy 2026-05-31, koulutusikkuna all, sään tila operational. Venue 1 (Pekuri): malli baseline teki keskimäärin 305,0 kävijän päivävirheen, päävertailukohta climatology_dow 138,9. Malli häviää vertailukohdalle tilastollisesti: ero +166,1 kävijää päivässä (95 % väli +62,6…+264,5). Yksinkertainen sääntö climatology_dow on tällä ikkunalla parempi kuin malli. Tämä otos (30 päivää) olisi erottanut vasta 102,0 kävijän eron, eli 73,4 % vertailukohdan MAE:sta. Jakson kokonaismäärä: ennuste 2 961, toteuma 11 865, ero -75,0 %, 80 % väli 2 166–3 328. Venue 2 (Kaupungintalo): malli baseline teki keskimäärin 61,0 kävijän päivävirheen, päävertailukohta climatology_dow 44,5. Eroa ei havaittu: +16,5 kävijää päivässä (95 % väli -8,4…+42,1). Tämä otos (30 päivää) olisi erottanut vasta 36,5 kävijän eron, eli 81,8 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 2 902, toteuma 4 254, ero -31,8 %, 80 % väli 2 307–3 709. Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.

## 2. Ikkuna ja asetelma

- Origo (viimeinen koulutuspäivä): **2026-05-31**
- Testijakso: **2026-06-01 – 2026-06-30** (30 vrk, horisontit 1–30)
- Koulutusikkuna: `all`
- Mallit: baseline
- Vertailukohdat: seasonal_naive, moving_average_28d, climatology_dow
- Päävertailukohdan valinta: `best`
- Sään tilat: perfect, operational, climatology (verdikti tilasta `operational`)
- Bootstrap: 10 000 uudelleenotantaa, lohkon pituus 7 vrk, siemen 20260101

| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 151 | 21 | 11 | 170,43 |
| 2 (Kaupungintalo) | 2026-01-01 | 151 | 10 | 11 | 115,36 |

Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten yksikään sisäennuste ei ylety testijaksoon.

## Venue 1 (Pekuri)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2 961 | 11 865 | -8 904 | -75,0 % | 2 166 – 3 328 | ei | 1 695 – 4 228 |
| climatology_dow | 13 327 | 11 865 | +1 462 | +12,3 % | 13 327 – 19 805 | ei | 9 493 – 26 445 |
| moving_average_28d | 14 457 | 11 865 | +2 592 | +21,8 % | 11 717 – 15 181 | kyllä | 7 548 – 21 891 |
| seasonal_naive | 13 351 | 11 865 | +1 486 | +12,5 % | 11 444 – 15 998 | kyllä | 7 750 – 20 133 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 305,0 | 375,3 | 1,790 | -296,8 | 33,9 | 152,5 | 252,9 | 0,27 | 142,4 | 30 |
| baseline | 1-7 | 97,2 | 121,0 | 0,570 | -61,9 | 19,8 | 48,6 | 23,9 | 0,71 | 26,9 | 7 |
| baseline | 8-14 | 358,6 | 494,9 | 2,104 | -358,6 | 40,4 | 179,3 | 293,5 | 0,43 | 126,2 | 7 |
| baseline | 15-30 | 372,5 | 388,0 | 2,186 | -372,5 | 37,3 | 186,3 | 335,3 | 0,00 | 200,0 | 16 |
| climatology_dow | all | 138,9 | 201,7 | 0,815 | +48,7 | 32,7 | 69,5 | 53,2 | 0,73 | 31,0 | 30 |
| climatology_dow | 1-7 | 110,7 | 124,9 | 0,649 | +71,1 | 21,2 | 55,3 | 54,7 | 0,71 | 28,7 | 7 |
| climatology_dow | 8-14 | 160,2 | 259,1 | 0,940 | -16,9 | 25,0 | 80,1 | 61,8 | 0,71 | 26,6 | 7 |
| climatology_dow | 15-30 | 142,0 | 200,3 | 0,833 | +67,6 | 41,2 | 71,0 | 48,8 | 0,75 | 33,9 | 16 |
| moving_average_28d | all | 150,4 | 191,0 | 0,883 | +86,4 | 21,6 | 75,2 | 46,0 | 0,83 | 35,5 | 30 |
| moving_average_28d | 1-7 | 150,0 | 171,8 | 0,880 | +104,2 | 26,3 | 75,0 | 34,0 | 0,86 | 38,9 | 7 |
| moving_average_28d | 8-14 | 196,5 | 269,4 | 1,153 | +16,2 | 20,6 | 98,2 | 80,9 | 0,86 | 37,4 | 7 |
| moving_average_28d | 15-30 | 130,5 | 153,9 | 0,766 | +109,3 | 20,0 | 65,2 | 36,0 | 0,81 | 33,2 | 16 |
| seasonal_naive | all | 186,1 | 263,4 | 1,092 | +49,5 | 32,4 | 93,1 | 53,7 | 0,60 | 39,2 | 30 |
| seasonal_naive | 1-7 | 171,7 | 197,3 | 1,008 | +48,0 | 15,8 | 85,9 | 47,8 | 0,71 | 41,7 | 7 |
| seasonal_naive | 8-14 | 267,7 | 374,6 | 1,571 | -40,0 | 56,9 | 133,9 | 107,2 | 0,43 | 49,7 | 7 |
| seasonal_naive | 15-30 | 156,8 | 227,4 | 0,920 | +89,4 | 29,1 | 78,4 | 32,9 | 0,62 | 33,4 | 16 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 138,9). Vertailukohtien MAE: seasonal_naive 186,1, moving_average_28d 150,4, climatology_dow 138,9.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +166,1 | +62,6 … +264,5 | huonompi kuin vertailukohta | -1,196 | -1,835 … -0,469 | 102,0 | 73,4 % | 2,63 | 0,043 | 0,087 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,27 (8/30) | 0,12 … 0,46 | liian kapea | -296,8 | -424,1 … -167,4 | -75,0 % | aliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 305,0 | 305,0 | 303,6 | -1,4 | -0,5 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

⚠ **Parannus on negatiivinen**, eli malli ennustaa tällä ikkunalla *paremmin* keskiarvosäällä kuin toteutuneella säällä. Se ei ole mittausvirhe vaan tulos: mallin oppima sääriippuvuus ei yleisty tähän jaksoon, vaan toteutunut sää vie ennustetta väärään suuntaan. Sääpiirteet sopivat siis koulutusjakson kohinaan enemmän kuin kävijöiden todelliseen sääkäyttäytymiseen.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 30 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 14 |
| climatology (klimatologia koko jaksolta) | 0 | 30 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-06-12 | perjantai | 1 113 | 0 | -1 113 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-06-22 | maanantai | 620 | 0 | -620 | malli sai klimatologiasään (horisontti 22 vrk) |
| 2026-06-15 | maanantai | 513 | 0 | -513 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-06-23 | tiistai | 457 | 0 | -457 | malli sai klimatologiasään (horisontti 23 vrk) |
| 2026-06-13 | lauantai | 449 | 0 | -449 | viikonloppu |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## Venue 2 (Kaupungintalo)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2 902 | 4 254 | -1 352 | -31,8 % | 2 307 – 3 709 | ei | 1 104 – 5 771 |
| climatology_dow | 4 815 | 4 254 | +561 | +13,2 % | 4 059 – 5 882 | kyllä | 2 012 – 8 866 |
| moving_average_28d | 5 159 | 4 254 | +905 | +21,3 % | 4 024 – 6 146 | kyllä | 880 – 9 806 |
| seasonal_naive | 3 401 | 4 254 | -853 | -20,1 % | 3 166 – 10 448 | kyllä | 1 084 – 10 104 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 61,0 | 78,5 | 0,529 | -45,1 | 12,4 | 30,5 | 12,8 | 0,67 | 62,3 ⚠ | 30 |
| baseline | 1-7 | 35,6 | 47,4 | 0,309 | -34,6 | 10,3 | 17,8 | 6,7 | 1,00 | 24,0 | 7 |
| baseline | 8-14 | 44,2 | 58,5 | 0,383 | -24,2 | 11,6 | 22,1 | 11,4 | 0,86 | 31,9 | 7 |
| baseline | 15-30 | 79,5 | 95,3 | 0,689 | -58,8 | 13,7 | 39,8 | 16,1 | 0,44 | 92,3 ⚠ | 16 |
| climatology_dow | all | 44,5 | 70,1 | 0,386 | +18,7 | 15,0 | 22,3 | 15,4 | 0,87 | 38,2 ⚠ | 30 |
| climatology_dow | 1-7 | 23,7 | 30,3 | 0,205 | +23,7 | 7,2 | 11,8 | 17,4 | 1,00 | 17,3 | 7 |
| climatology_dow | 8-14 | 41,9 | 51,6 | 0,363 | -9,8 | 10,4 | 20,9 | 12,8 | 0,86 | 28,3 | 7 |
| climatology_dow | 15-30 | 54,8 | 87,4 | 0,475 | +29,0 | 20,4 | 27,4 | 15,7 | 0,81 | 51,7 ⚠ | 16 |
| moving_average_28d | all | 71,4 | 93,3 | 0,619 | +30,2 | 15,8 | 35,7 | 18,5 | 0,77 | 60,6 ⚠ | 30 |
| moving_average_28d | 1-7 | 42,6 | 65,0 | 0,369 | +32,0 | 12,2 | 21,3 | 19,0 | 0,86 | 36,1 | 7 |
| moving_average_28d | 8-14 | 63,7 | 77,0 | 0,552 | -1,5 | 14,7 | 31,9 | 14,2 | 1,00 | 39,6 | 7 |
| moving_average_28d | 15-30 | 87,4 | 109,0 | 0,757 | +43,2 | 17,8 | 43,7 | 20,2 | 0,62 | 80,5 ⚠ | 16 |
| seasonal_naive | all | 62,4 | 76,0 | 0,541 | -28,4 | 14,1 | 31,2 | 20,2 | 0,83 | 57,9 ⚠ | 30 |
| seasonal_naive | 1-7 | 53,1 | 62,3 | 0,461 | -27,7 | 10,3 | 26,6 | 21,8 | 1,00 | 39,7 | 7 |
| seasonal_naive | 8-14 | 61,1 | 72,8 | 0,530 | -61,1 | 14,4 | 30,6 | 14,6 | 0,86 | 48,2 | 7 |
| seasonal_naive | 15-30 | 67,1 | 82,5 | 0,581 | -14,4 | 15,6 | 33,5 | 21,9 | 0,75 | 70,2 ⚠ | 16 |

⚠ sMAPE on merkitty epäluotettavaksi: testijaksolla on nollapäiviä (enimmillään 3 korissa). Nollapäivällä symmetrinen suhde saavuttaa kattonsa riippumatta siitä kuinka lähellä ennuste oli. sMAPEa ei käytetä verdiktin perustana.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 44,5). Vertailukohtien MAE: seasonal_naive 62,4, moving_average_28d 71,4, climatology_dow 44,5.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +16,5 | -8,4 … +42,1 | ei havaittavaa eroa vertailukohtaan | -0,370 | -1,381 … 0,118 | 36,5 | 81,8 % | 1,02 | 0,250 | 0,250 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,67 (20/30) | 0,47 … 0,83 | kalibroitu | -45,1 | -64,7 … -28,5 | -31,8 % | aliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 56,9 | 61,0 | 62,3 | +5,4 | 8,7 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 30 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 14 |
| climatology (klimatologia koko jaksolta) | 0 | 30 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-06-18 | torstai | 239 | 57 | -182 | malli sai klimatologiasään (horisontti 18 vrk) |
| 2026-06-16 | tiistai | 316 | 143 | -173 | runsas sade 9.5 mm |
| 2026-06-27 | lauantai | 207 | 76 | -131 | malli sai klimatologiasään (horisontti 27 vrk); viikonloppu |
| 2026-06-09 | tiistai | 309 | 178 | -131 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-06-24 | keskiviikko | 204 | 77 | -127 | malli sai klimatologiasään (horisontti 24 vrk) |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## 8. Rajoitteet

- **Otoskoko.** Yksi ikkuna on 30 päivää yhdestä origosta. Ne eivät ole 30 riippumatonta havaintoa: kaikki jakavat saman koulutusjoukon ja saman kuukauden sään.
- **Yhden ikkunan verdikti on kuvaileva, ei todistava.** Varsinainen näyttö syntyy usean ikkunan koosteesta (`--sweep monthly` tai `--sweep rolling`).
- **"Ei havaittavaa eroa" ei tarkoita samanveroisuutta.** Lue MDE kohdasta 5 ennen kuin teet siitä johtopäätöksen.
- **sMAPEa ei käytetä verdiktin perustana**, koska nollapäivät rikkovat sen.
- **Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta.** Vuosikausivaihtelua ei voi oppia, joten vertailu toiseen vuoteen ei ole mahdollinen.
- **Lippudataa ei käytetä piirteenä**, koska sitä ei ole tulevaisuudelle.
- **Venue 1: koulutusikkunan alussa on 21 nollapäivää** sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.
- **Venue 2: koulutusikkunan alussa on 7 nollapäivää** sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.
