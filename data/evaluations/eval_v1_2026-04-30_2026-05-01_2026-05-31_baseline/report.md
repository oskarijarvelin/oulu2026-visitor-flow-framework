# Ennusteen arviointiraportti: 2026-05-01 – 2026-05-31

Ajon tunniste: `eval_v1_2026-04-30_2026-05-01_2026-05-31_baseline`

## 1. Verdikti

Ikkuna 2026-05-01–2026-05-31 (31 vrk), koulutus päättyy 2026-04-30, koulutusikkuna all, sään tila operational. Venue 1 (Pekuri): malli baseline teki keskimäärin 179,5 kävijän päivävirheen, päävertailukohta moving_average_28d 187,4. Eroa ei havaittu: -7,9 kävijää päivässä (95 % väli -58,5…+23,6). Tämä otos (31 päivää) olisi erottanut vasta 69,0 kävijän eron, eli 36,8 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 11 880, toteuma 14 521, ero -18,2 %, 80 % väli 10 683–13 840. Venue 2 (Kaupungintalo): malli baseline teki keskimäärin 76,4 kävijän päivävirheen, päävertailukohta climatology_dow 71,5. Eroa ei havaittu: +5,0 kävijää päivässä (95 % väli -5,4…+33,6). Tämä otos (31 päivää) olisi erottanut vasta 31,9 kävijän eron, eli 44,6 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 3 242, toteuma 5 149, ero -37,0 %, 80 % väli 2 885–4 617. Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.

## 2. Ikkuna ja asetelma

- Origo (viimeinen koulutuspäivä): **2026-04-30**
- Testijakso: **2026-05-01 – 2026-05-31** (31 vrk, horisontit 1–31)
- Koulutusikkuna: `all`
- Mallit: baseline
- Vertailukohdat: seasonal_naive, moving_average_28d, climatology_dow
- Päävertailukohdan valinta: `best`
- Sään tilat: perfect, operational, climatology (verdikti tilasta `operational`)
- Bootstrap: 10 000 uudelleenotantaa, lohkon pituus 7 vrk, siemen 20260101

| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 120 | 21 | 7 | 144,46 |
| 2 (Kaupungintalo) | 2026-01-01 | 120 | 10 | 7 | 121,54 |

Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten yksikään sisäennuste ei ylety testijaksoon.

## Venue 1 (Pekuri)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 11 880 | 14 521 | -2 641 | -18,2 % | 10 683 – 13 840 | ei | 7 585 – 17 753 |
| climatology_dow | 14 067 | 14 521 | -454 | -3,1 % | 14 067 – 25 416 | kyllä | 12 295 – 33 932 |
| moving_average_28d | 13 564 | 14 521 | -957 | -6,6 % | 11 162 – 14 242 | ei | 7 530 – 19 096 |
| seasonal_naive | 13 102 | 14 521 | -1 419 | -9,8 % | 11 107 – 14 783 | kyllä | 7 884 – 19 070 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

⚠ **Näiden mallien väli ei ole kalibroitu:** climatology_dow (suhteellisten virheiden mediaani 1,36). Sisäkkäisen backtestin mallit on koulutettu lyhyemmällä ja huonommalla aineistolla kuin ulompi malli, joten niiden virheissä on tasosiirtymä eikä pelkkää hajontaa. Väli perii sen. Lue kokonaismäärän ero ja bias erikseen, älä väliä.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 179,5 | 260,2 | 1,242 | -85,2 | 30,9 | 89,7 | 79,0 | 0,65 | 37,4 | 31 |
| baseline | 1-7 | 180,2 | 232,7 | 1,247 | -82,0 | 32,8 | 90,1 | 56,3 | 0,57 | 36,6 | 7 |
| baseline | 8-14 | 207,2 | 267,5 | 1,434 | -185,5 | 32,8 | 103,6 | 94,6 | 0,57 | 43,2 | 7 |
| baseline | 15-30 | 167,8 | 267,8 | 1,162 | -45,2 | 29,3 | 83,9 | 81,9 | 0,71 | 35,4 | 17 |
| climatology_dow | all | 187,6 | 250,8 | 1,298 | -14,7 | 61,8 | 93,8 | 63,0 | 0,48 | 38,0 | 31 |
| climatology_dow | 1-7 | 192,3 | 241,0 | 1,331 | -26,9 | 82,3 | 96,1 | 63,3 | 0,43 | 37,2 | 7 |
| climatology_dow | 8-14 | 170,8 | 207,6 | 1,182 | -100,2 | 28,6 | 85,4 | 54,9 | 0,71 | 35,7 | 7 |
| climatology_dow | 15-30 | 192,5 | 270,2 | 1,333 | +25,6 | 67,0 | 96,3 | 66,2 | 0,41 | 39,3 | 17 |
| moving_average_28d | all | 187,4 | 236,4 | 1,297 | -30,9 | 24,8 | 93,7 | 60,6 | 0,68 | 39,7 | 31 |
| moving_average_28d | 1-7 | 152,8 | 189,4 | 1,058 | -34,8 | 22,7 | 76,4 | 44,9 | 0,71 | 32,3 | 7 |
| moving_average_28d | 8-14 | 196,2 | 227,0 | 1,358 | -108,0 | 32,5 | 98,1 | 43,0 | 0,57 | 38,7 | 7 |
| moving_average_28d | 15-30 | 198,0 | 256,7 | 1,371 | +2,5 | 22,5 | 99,0 | 74,4 | 0,71 | 43,1 | 17 |
| seasonal_naive | all | 220,9 | 286,8 | 1,529 | -45,8 | 40,6 | 110,4 | 88,5 | 0,48 | 45,5 | 31 |
| seasonal_naive | 1-7 | 268,0 | 309,9 | 1,855 | -66,3 | 53,5 | 134,0 | 105,0 | 0,14 | 56,5 | 7 |
| seasonal_naive | 8-14 | 229,6 | 282,2 | 1,589 | -139,6 | 38,5 | 114,8 | 108,5 | 0,43 | 47,5 | 7 |
| seasonal_naive | 15-30 | 197,9 | 278,7 | 1,370 | +1,3 | 36,1 | 98,9 | 73,5 | 0,65 | 40,1 | 17 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **moving_average_28d** (MAE 187,4). Vertailukohtien MAE: seasonal_naive 220,9, moving_average_28d 187,4, climatology_dow 187,6.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | -7,9 | -58,5 … +23,6 | ei havaittavaa eroa vertailukohtaan | 0,042 | -0,131 … 0,293 | 69,0 | 36,8 % | -0,32 | 0,740 | 1,000 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,65 (20/31) | 0,45 … 0,81 | kalibroitu | -85,2 | -206,8 … -35,9 | -18,2 % | aliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 177,4 | 179,5 | 183,9 | +6,5 | 3,5 % |

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
| 2026-05-15 | perjantai | 1 174 | 441 | -733 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-05-26 | tiistai | 890 | 319 | -571 | malli sai klimatologiasään (horisontti 26 vrk) |
| 2026-05-05 | tiistai | 841 | 364 | -477 | runsas sade 9.6 mm |
| 2026-05-13 | keskiviikko | 731 | 269 | -462 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-05-30 | lauantai | 265 | 700 | +435 | malli sai klimatologiasään (horisontti 30 vrk); viikonloppu |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## Venue 2 (Kaupungintalo)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 3 242 | 5 149 | -1 907 | -37,0 % | 2 885 – 4 617 | ei | 1 165 – 6 967 |
| climatology_dow | 5 148 | 5 149 | -1 | -0,0 % | 4 780 – 6 921 | kyllä | 1 923 – 10 769 |
| moving_average_28d | 3 800 | 5 149 | -1 349 | -26,2 % | 3 278 – 4 812 | ei | 641 – 7 982 |
| seasonal_naive | 4 180 | 5 149 | -969 | -18,8 % | 4 016 – 7 038 | kyllä | 1 263 – 11 923 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 76,4 | 109,1 | 0,629 | -61,5 | 13,0 | 38,2 | 18,5 | 0,81 | 48,7 | 31 |
| baseline | 1-7 | 100,0 | 150,3 | 0,823 | -92,5 | 15,3 | 50,0 | 20,5 | 0,86 | 49,9 | 7 |
| baseline | 8-14 | 60,9 | 73,2 | 0,501 | -39,8 | 11,5 | 30,4 | 10,7 | 0,86 | 50,2 | 7 |
| baseline | 15-30 | 73,2 | 101,0 | 0,602 | -57,7 | 12,7 | 36,6 | 20,8 | 0,76 | 47,6 | 17 |
| climatology_dow | all | 71,5 | 95,3 | 0,588 | -0,0 | 10,4 | 35,7 | 22,7 | 0,97 | 42,9 | 31 |
| climatology_dow | 1-7 | 98,2 | 139,2 | 0,808 | -30,5 | 12,3 | 49,1 | 34,7 | 0,86 | 51,7 | 7 |
| climatology_dow | 8-14 | 56,1 | 63,9 | 0,462 | +12,5 | 6,8 | 28,1 | 18,6 | 1,00 | 37,4 | 7 |
| climatology_dow | 15-30 | 66,8 | 83,0 | 0,550 | +7,4 | 11,1 | 33,4 | 19,5 | 1,00 | 41,5 | 17 |
| moving_average_28d | all | 82,9 | 115,3 | 0,682 | -43,5 | 14,7 | 41,5 | 22,7 | 0,77 | 54,2 | 31 |
| moving_average_28d | 1-7 | 108,2 | 163,3 | 0,890 | -71,4 | 17,4 | 54,1 | 42,9 | 0,86 | 57,4 | 7 |
| moving_average_28d | 8-14 | 65,3 | 87,2 | 0,537 | -28,4 | 13,8 | 32,7 | 13,0 | 0,57 | 50,7 | 7 |
| moving_average_28d | 15-30 | 79,8 | 100,6 | 0,656 | -38,3 | 14,0 | 39,9 | 18,4 | 0,82 | 54,2 | 17 |
| seasonal_naive | all | 75,1 | 103,3 | 0,618 | -31,3 | 12,8 | 37,6 | 23,8 | 0,90 | 48,5 | 31 |
| seasonal_naive | 1-7 | 112,0 | 154,8 | 0,922 | -62,0 | 15,0 | 56,0 | 24,7 | 0,86 | 58,6 | 7 |
| seasonal_naive | 8-14 | 49,0 | 60,3 | 0,403 | -19,0 | 11,9 | 24,5 | 25,0 | 0,86 | 40,9 | 7 |
| seasonal_naive | 15-30 | 70,7 | 89,9 | 0,582 | -23,6 | 12,2 | 35,4 | 23,0 | 0,94 | 47,4 | 17 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 71,5). Vertailukohtien MAE: seasonal_naive 75,1, moving_average_28d 82,9, climatology_dow 71,5.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +5,0 | -5,4 … +33,6 | ei havaittavaa eroa vertailukohtaan | -0,070 | -0,566 … 0,080 | 31,9 | 44,6 % | 0,33 | 0,839 | 1,000 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,81 (25/31) | 0,63 … 0,93 | kalibroitu | -61,5 | -101,1 … -37,0 | -37,0 % | aliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 78,2 | 76,4 | 79,9 | +1,7 | 2,1 % |

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
| 2026-05-05 | tiistai | 514 | 168 | -346 | runsas sade 9.6 mm |
| 2026-05-22 | perjantai | 348 | 108 | -240 | malli sai klimatologiasään (horisontti 22 vrk) |
| 2026-05-21 | torstai | 309 | 111 | -198 | malli sai klimatologiasään (horisontti 21 vrk) |
| 2026-05-19 | tiistai | 265 | 106 | -159 | malli sai klimatologiasään (horisontti 19 vrk) |
| 2026-05-06 | keskiviikko | 251 | 104 | -147 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |

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
