# Ennusteen arviointiraportti: 2026-08-01 – 2026-08-31

Ajon tunniste: `eval_v1_2026-07-31_2026-08-01_2026-08-31_baseline`

## 1. Verdikti

Ikkuna 2026-08-01–2026-08-31 (31 vrk), koulutus päättyy 2026-07-31, koulutusikkuna all, sään tila operational. Venue 1 (Pekuri): malli baseline teki keskimäärin 255,8 kävijän päivävirheen, päävertailukohta climatology_dow 128,0. Malli häviää vertailukohdalle tilastollisesti: ero +127,8 kävijää päivässä (95 % väli +44,2…+184,1). Yksinkertainen sääntö climatology_dow on tällä ikkunalla parempi kuin malli. Tämä otos (31 päivää) olisi erottanut vasta 70,8 kävijän eron, eli 55,3 % vertailukohdan MAE:sta. Jakson kokonaismäärä: ennuste 20 173, toteuma 13 514, ero +49,3 %, 80 % väli 18 620–27 237. Venue 2 (Kaupungintalo): malli baseline teki keskimäärin 37,0 kävijän päivävirheen, päävertailukohta climatology_dow 36,8. Eroa ei havaittu: +0,2 kävijää päivässä (95 % väli -10,6…+8,5). Tämä otos (31 päivää) olisi erottanut vasta 10,6 kävijän eron, eli 28,8 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 4 335, toteuma 4 866, ero -10,9 %, 80 % väli 4 166–7 382. Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.

## 2. Ikkuna ja asetelma

- Origo (viimeinen koulutuspäivä): **2026-07-31**
- Testijakso: **2026-08-01 – 2026-08-31** (31 vrk, horisontit 1–31)
- Koulutusikkuna: `all`
- Mallit: baseline
- Vertailukohdat: seasonal_naive, moving_average_28d, climatology_dow
- Päävertailukohdan valinta: `best`
- Sään tilat: perfect, operational, climatology (verdikti tilasta `operational`)
- Bootstrap: 10 000 uudelleenotantaa, lohkon pituus 7 vrk, siemen 20260101

| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 212 | 21 | 12 | 163,08 |
| 2 (Kaupungintalo) | 2026-01-01 | 212 | 13 | 12 | 100,17 |

Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten yksikään sisäennuste ei ylety testijaksoon.

## Venue 1 (Pekuri)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 20 173 | 13 514 | +6 659 | +49,3 % | 18 620 – 27 237 | ei | 11 569 – 39 322 |
| climatology_dow | 14 172 | 13 514 | +658 | +4,9 % | 13 066 – 16 902 | kyllä | 8 597 – 25 386 |
| moving_average_28d | 17 464 | 13 514 | +3 950 | +29,2 % | 15 214 – 20 615 | ei | 9 748 – 28 923 |
| seasonal_naive | 18 747 | 13 514 | +5 233 | +38,7 % | 18 747 – 26 305 | ei | 9 632 – 38 311 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 255,8 | 281,1 | 1,569 | +214,8 | 35,2 | 127,9 | 83,3 | 0,58 | 49,0 | 31 |
| baseline | 1-7 | 244,8 | 267,4 | 1,501 | +244,8 | 18,0 | 122,4 | 64,0 | 0,71 | 43,6 | 7 |
| baseline | 8-14 | 196,8 | 219,7 | 1,207 | +36,0 | 26,5 | 98,4 | 53,9 | 0,86 | 33,6 | 7 |
| baseline | 15-30 | 284,7 | 307,8 | 1,746 | +276,1 | 45,9 | 142,3 | 103,3 | 0,41 | 57,5 | 17 |
| climatology_dow | all | 128,0 | 180,4 | 0,785 | +21,2 | 20,7 | 64,0 | 50,1 | 0,84 | 27,2 | 31 |
| climatology_dow | 1-7 | 82,8 | 95,4 | 0,508 | +24,4 | 15,0 | 41,4 | 40,2 | 1,00 | 17,6 | 7 |
| climatology_dow | 8-14 | 178,0 | 276,9 | 1,091 | -125,8 | 30,4 | 89,0 | 72,9 | 0,71 | 29,6 | 7 |
| climatology_dow | 15-30 | 126,0 | 155,0 | 0,773 | +80,5 | 19,1 | 63,0 | 44,7 | 0,82 | 30,1 | 17 |
| moving_average_28d | all | 200,8 | 225,6 | 1,231 | +127,4 | 23,0 | 100,4 | 55,7 | 0,74 | 41,7 | 31 |
| moving_average_28d | 1-7 | 131,1 | 145,7 | 0,804 | +131,1 | 12,6 | 65,5 | 47,0 | 1,00 | 27,3 | 7 |
| moving_average_28d | 8-14 | 219,8 | 264,4 | 1,348 | -19,1 | 34,0 | 109,9 | 58,1 | 0,71 | 38,2 | 7 |
| moving_average_28d | 15-30 | 221,7 | 235,1 | 1,360 | +186,2 | 22,7 | 110,9 | 58,3 | 0,65 | 49,0 | 17 |
| seasonal_naive | all | 218,6 | 271,8 | 1,341 | +168,8 | 29,9 | 109,3 | 80,0 | 0,77 | 42,0 | 31 |
| seasonal_naive | 1-7 | 196,4 | 227,6 | 1,205 | +163,9 | 11,7 | 98,2 | 80,2 | 1,00 | 36,4 | 7 |
| seasonal_naive | 8-14 | 170,3 | 242,1 | 1,044 | +13,7 | 30,9 | 85,1 | 67,2 | 1,00 | 28,6 | 7 |
| seasonal_naive | 15-30 | 247,6 | 298,8 | 1,519 | +234,7 | 37,0 | 123,8 | 85,2 | 0,59 | 49,9 | 17 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 128,0). Vertailukohtien MAE: seasonal_naive 218,6, moving_average_28d 200,8, climatology_dow 128,0.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +127,8 | +44,2 … +184,1 | huonompi kuin vertailukohta | -0,998 | -1,664 … -0,273 | 70,8 | 55,3 % | 3,17 | 0,055 | 0,111 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,58 (18/31) | 0,39 … 0,75 | liian kapea | +214,8 | +84,6 … +306,1 | +49,3 % | yliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 223,5 | 255,8 | 253,0 | +29,5 | 11,7 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 31 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 15 |
| climatology (klimatologia koko jaksolta) | 0 | 31 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-08-22 | lauantai | 287 | 789 | +502 | malli sai klimatologiasään (horisontti 22 vrk); viikonloppu |
| 2026-08-04 | tiistai | 397 | 835 | +438 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-08-31 | maanantai | 263 | 685 | +422 | malli sai klimatologiasään (horisontti 31 vrk) |
| 2026-08-14 | perjantai | 1 084 | 668 | -416 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-08-24 | maanantai | 313 | 714 | +401 | malli sai klimatologiasään (horisontti 24 vrk) |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## Venue 2 (Kaupungintalo)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 4 335 | 4 866 | -531 | -10,9 % | 4 166 – 7 382 | kyllä | 1 647 – 11 230 |
| climatology_dow | 5 018 | 4 866 | +152 | +3,1 % | 4 268 – 5 629 | kyllä | 2 156 – 7 884 |
| moving_average_28d | 6 353 | 4 866 | +1 487 | +30,6 % | 5 730 – 8 160 | ei | 820 – 12 683 |
| seasonal_naive | 5 393 | 4 866 | +527 | +10,8 % | 5 130 – 16 174 | ei | 2 164 – 12 183 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 37,0 | 63,4 | 0,370 | -17,1 | 11,9 | 18,5 | 20,5 | 0,97 | 29,5 | 31 |
| baseline | 1-7 | 12,4 | 17,9 | 0,124 | -9,1 | 11,2 | 6,2 | 15,1 | 1,00 | 10,2 | 7 |
| baseline | 8-14 | 33,5 | 42,8 | 0,335 | -31,7 | 11,8 | 16,8 | 21,6 | 1,00 | 27,9 | 7 |
| baseline | 15-30 | 48,6 | 80,2 | 0,485 | -14,4 | 12,2 | 24,3 | 22,3 | 0,94 | 38,1 | 17 |
| climatology_dow | all | 36,8 | 60,3 | 0,367 | +4,9 | 11,0 | 18,4 | 12,7 | 0,77 | 27,5 | 31 |
| climatology_dow | 1-7 | 16,9 | 19,4 | 0,169 | +1,9 | 9,9 | 8,4 | 8,6 | 1,00 | 9,6 | 7 |
| climatology_dow | 8-14 | 25,6 | 40,2 | 0,255 | -9,5 | 10,3 | 12,8 | 9,1 | 0,71 | 19,7 | 7 |
| climatology_dow | 15-30 | 49,6 | 76,2 | 0,495 | +12,0 | 11,7 | 24,8 | 16,0 | 0,71 | 38,0 | 17 |
| moving_average_28d | all | 75,7 | 97,5 | 0,755 | +48,0 | 14,4 | 37,8 | 25,2 | 0,87 | 51,6 | 31 |
| moving_average_28d | 1-7 | 53,7 | 76,4 | 0,536 | +40,5 | 14,4 | 26,8 | 23,2 | 0,86 | 37,2 | 7 |
| moving_average_28d | 8-14 | 57,4 | 76,4 | 0,573 | +29,1 | 14,8 | 28,7 | 23,0 | 1,00 | 36,1 | 7 |
| moving_average_28d | 15-30 | 92,2 | 111,9 | 0,921 | +58,8 | 14,3 | 46,1 | 27,0 | 0,82 | 63,9 | 17 |
| seasonal_naive | all | 100,5 | 130,1 | 1,004 | +17,0 | 11,8 | 50,3 | 57,5 | 0,74 | 71,8 | 31 |
| seasonal_naive | 1-7 | 79,9 | 104,0 | 0,797 | +18,4 | 11,9 | 39,9 | 54,4 | 0,86 | 56,4 | 7 |
| seasonal_naive | 8-14 | 87,3 | 107,8 | 0,871 | +7,0 | 9,8 | 43,6 | 47,7 | 0,71 | 67,9 | 7 |
| seasonal_naive | 15-30 | 114,5 | 147,0 | 1,143 | +20,5 | 12,6 | 57,3 | 62,9 | 0,71 | 79,8 | 17 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 36,8). Vertailukohtien MAE: seasonal_naive 100,5, moving_average_28d 75,7, climatology_dow 36,8.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +0,2 | -10,6 … +8,5 | ei havaittavaa eroa vertailukohtaan | -0,006 | -0,205 … 0,295 | 10,6 | 28,8 % | 0,04 | 0,967 | 0,967 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,97 (30/31) | 0,83 … 1,00 | liian leveä | -17,1 | -38,8 … +2,4 | -10,9 % | ei systemaattista harhaa |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 37,0 | 37,0 | 39,2 | +2,2 | 5,5 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 31 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 15 |
| climatology (klimatologia koko jaksolta) | 0 | 31 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-08-15 | lauantai | 371 | 155 | -216 | runsas sade 8,7 mm; viikonloppu |
| 2026-08-27 | torstai | 317 | 143 | -174 | malli sai klimatologiasään (horisontti 27 vrk) |
| 2026-08-26 | keskiviikko | 21 | 173 | +152 | malli sai klimatologiasään (horisontti 26 vrk) |
| 2026-08-13 | torstai | 284 | 190 | -94 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-08-18 | tiistai | 155 | 214 | +59 | runsas sade 7,0 mm; malli sai klimatologiasään (horisontti 18 vrk) |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## 8. Rajoitteet

- **Otoskoko.** Yksi ikkuna on 31 päivää yhdestä origosta. Ne eivät ole 31 riippumatonta havaintoa: kaikki jakavat saman koulutusjoukon ja saman kuukauden sään.
- **Yhden ikkunan verdikti on kuvaileva, ei todistava.** Varsinainen näyttö syntyy usean ikkunan koosteesta (`--sweep monthly` tai `--sweep rolling`).
- **"Ei havaittavaa eroa" ei tarkoita samanveroisuutta.** Lue MDE kohdasta 5 ennen kuin teet siitä johtopäätöksen.
- **sMAPEa ei käytetä verdiktin perustana**, koska nollapäivät rikkovat sen.
- **Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta.** Vuosikausivaihtelua ei voi oppia, joten vertailu toiseen vuoteen ei ole mahdollinen.
- **Lippudataa ei käytetä piirteenä**, koska sitä ei ole tulevaisuudelle.
- **Venue 1: koulutusikkunan alussa on 21 nollapäivää** sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.
- **Venue 2: koulutusikkunan alussa on 7 nollapäivää** sensorin käyttöönottoa edeltävältä ajalta. Arviointi ei poista niitä, koska koulutusikkuna on se jonka käyttäjä nimesi; `--train-window` rajaa ne pois. Nollat eivät jää alkuun: vuodenaikapiirre `year_sin` on symmetrinen kesäpäivän suhteen, joten tammikuun nollapäivät saavat saman arvon kuin niitä vastaavat kesäkuun päivät ja malli voi lukea kesän tammikuuksi. Jos ennuste romahtaa lähelle nollaa keskellä kesää, tämä on ensimmäinen paikka katsoa.
