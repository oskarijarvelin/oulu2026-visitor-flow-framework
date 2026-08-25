# Ennusteen arviointiraportti: 2026-07-01 – 2026-07-31

Ajon tunniste: `eval_v1_2026-06-30_2026-07-01_2026-07-31_baseline`

## 1. Verdikti

Ikkuna 2026-07-01–2026-07-31 (31 vrk), koulutus päättyy 2026-06-30, koulutusikkuna all, sään tila operational. Venue 1 (Pekuri): malli baseline teki keskimäärin 174,3 kävijän päivävirheen, päävertailukohta climatology_dow 156,2. Eroa ei havaittu: +18,1 kävijää päivässä (95 % väli -15,5…+60,9). Tämä otos (31 päivää) olisi erottanut vasta 43,5 kävijän eron, eli 27,8 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 12 181, toteuma 16 994, ero -28,3 %, 80 % väli 10 022–14 392. Venue 2 (Kaupungintalo): malli baseline teki keskimäärin 108,0 kävijän päivävirheen, päävertailukohta climatology_dow 62,0. Malli häviää vertailukohdalle tilastollisesti: ero +46,0 kävijää päivässä (95 % väli +27,1…+66,1). Yksinkertainen sääntö climatology_dow on tällä ikkunalla parempi kuin malli. Tämä otos (31 päivää) olisi erottanut vasta 25,3 kävijän eron, eli 40,8 % vertailukohdan MAE:sta. Jakson kokonaismäärä: ennuste 3 262, toteuma 6 278, ero -48,0 %, 80 % väli 2 623–4 447. Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.

## 2. Ikkuna ja asetelma

- Origo (viimeinen koulutuspäivä): **2026-06-30**
- Testijakso: **2026-07-01 – 2026-07-31** (31 vrk, horisontit 1–31)
- Koulutusikkuna: `all`
- Mallit: baseline
- Vertailukohdat: seasonal_naive, moving_average_28d, climatology_dow
- Päävertailukohdan valinta: `best`
- Sään tilat: perfect, operational, climatology (verdikti tilasta `operational`)
- Bootstrap: 10 000 uudelleenotantaa, lohkon pituus 7 vrk, siemen 20260101

| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 181 | 21 | 12 | 170,78 |
| 2 (Kaupungintalo) | 2026-01-01 | 181 | 13 | 12 | 108,26 |

Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten yksikään sisäennuste ei ylety testijaksoon.

## Venue 1 (Pekuri)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 12 181 | 16 994 | -4 813 | -28,3 % | 10 022 – 14 392 | ei | 6 574 – 19 400 |
| climatology_dow | 13 653 | 16 994 | -3 341 | -19,7 % | 12 632 – 16 257 | ei | 8 698 – 23 914 |
| moving_average_28d | 12 174 | 16 994 | -4 820 | -28,4 % | 9 329 – 12 220 | ei | 6 036 – 17 391 |
| seasonal_naive | 11 228 | 16 994 | -5 766 | -33,9 % | 9 806 – 14 102 | ei | 5 617 – 20 263 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 174,3 | 210,0 | 1,021 | -155,3 | 33,6 | 87,2 | 36,8 | 0,65 | 35,6 | 31 |
| baseline | 1-7 | 121,4 | 165,3 | 0,711 | -100,3 | 27,0 | 60,7 | 25,7 | 0,86 | 23,9 | 7 |
| baseline | 8-14 | 167,1 | 185,7 | 0,978 | -131,4 | 29,7 | 83,5 | 31,7 | 0,57 | 37,4 | 7 |
| baseline | 15-30 | 199,1 | 234,4 | 1,166 | -187,7 | 37,9 | 99,5 | 43,4 | 0,59 | 39,7 | 17 |
| climatology_dow | all | 156,2 | 194,9 | 0,915 | -107,8 | 27,7 | 78,1 | 37,5 | 0,84 | 30,4 | 31 |
| climatology_dow | 1-7 | 167,5 | 225,4 | 0,981 | -58,8 | 25,1 | 83,7 | 50,1 | 0,71 | 31,5 | 7 |
| climatology_dow | 8-14 | 162,1 | 175,4 | 0,949 | -62,5 | 21,8 | 81,0 | 32,8 | 1,00 | 33,5 | 7 |
| climatology_dow | 15-30 | 149,2 | 188,9 | 0,874 | -146,6 | 31,2 | 74,6 | 34,2 | 0,82 | 28,8 | 17 |
| moving_average_28d | all | 164,7 | 209,2 | 0,964 | -155,5 | 35,3 | 82,3 | 57,8 | 0,55 | 31,9 | 31 |
| moving_average_28d | 1-7 | 137,6 | 200,5 | 0,805 | -106,9 | 28,7 | 68,8 | 56,9 | 0,71 | 26,6 | 7 |
| moving_average_28d | 8-14 | 120,7 | 148,6 | 0,707 | -110,6 | 29,8 | 60,3 | 16,9 | 0,71 | 25,1 | 7 |
| moving_average_28d | 15-30 | 194,0 | 232,8 | 1,136 | -194,0 | 40,3 | 97,0 | 75,0 | 0,41 | 37,0 | 17 |
| seasonal_naive | all | 188,8 | 227,4 | 1,105 | -186,0 | 36,7 | 94,4 | 29,7 | 0,77 | 38,5 | 31 |
| seasonal_naive | 1-7 | 145,9 | 214,3 | 0,854 | -137,9 | 31,0 | 72,9 | 31,9 | 0,71 | 28,9 | 7 |
| seasonal_naive | 8-14 | 145,9 | 171,2 | 0,854 | -141,6 | 33,0 | 72,9 | 16,0 | 1,00 | 32,1 | 7 |
| seasonal_naive | 15-30 | 224,1 | 251,6 | 1,312 | -224,1 | 40,6 | 112,1 | 34,5 | 0,71 | 45,0 | 17 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 156,2). Vertailukohtien MAE: seasonal_naive 188,8, moving_average_28d 164,7, climatology_dow 156,2.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +18,1 | -15,5 … +60,9 | ei havaittavaa eroa vertailukohtaan | -0,116 | -0,403 … 0,087 | 43,5 | 27,8 % | 0,79 | 0,472 | 0,472 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,65 (20/31) | 0,45 … 0,81 | kalibroitu | -155,3 | -211,2 … -134,8 | -28,3 % | aliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 168,2 | 174,3 | 181,5 | +13,3 | 7,3 % |

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
| 2026-07-27 | maanantai | 804 | 360 | -444 | malli sai klimatologiasään (horisontti 27 vrk) |
| 2026-07-15 | keskiviikko | 703 | 303 | -400 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-07-18 | lauantai | 826 | 482 | -344 | malli sai klimatologiasään (horisontti 18 vrk); viikonloppu |
| 2026-07-06 | maanantai | 755 | 417 | -338 | runsas sade 5.8 mm |
| 2026-07-28 | tiistai | 702 | 394 | -308 | runsas sade 13.9 mm; malli sai klimatologiasään (horisontti 28 vrk) |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## Venue 2 (Kaupungintalo)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 3 262 | 6 278 | -3 016 | -48,0 % | 2 623 – 4 447 | ei | 1 056 – 6 921 |
| climatology_dow | 5 053 | 6 278 | -1 225 | -19,5 % | 4 211 – 5 843 | ei | 2 125 – 8 564 |
| moving_average_28d | 4 486 | 6 278 | -1 792 | -28,5 % | 3 390 – 5 093 | ei | 626 – 8 118 |
| seasonal_naive | 4 755 | 6 278 | -1 523 | -24,3 % | 4 341 – 12 688 | kyllä | 1 566 – 11 974 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 108,0 | 130,0 | 0,998 | -97,3 | 17,9 | 54,0 | 25,5 | 0,45 | 73,3 | 31 |
| baseline | 1-7 | 45,1 | 63,7 | 0,417 | -32,9 | 12,7 | 22,6 | 9,8 | 0,86 | 44,9 | 7 |
| baseline | 8-14 | 90,5 | 112,6 | 0,836 | -87,6 | 15,2 | 45,3 | 34,5 | 0,43 | 61,8 | 7 |
| baseline | 15-30 | 141,2 | 154,7 | 1,304 | -127,8 | 21,1 | 70,6 | 28,2 | 0,29 | 89,8 | 17 |
| climatology_dow | all | 62,0 | 79,7 | 0,573 | -39,5 | 16,1 | 31,0 | 9,2 | 0,84 | 42,1 | 31 |
| climatology_dow | 1-7 | 37,9 | 50,5 | 0,350 | -4,3 | 10,7 | 18,9 | 11,5 | 0,86 | 39,4 | 7 |
| climatology_dow | 8-14 | 41,2 | 57,6 | 0,380 | -36,5 | 12,7 | 20,6 | 7,6 | 0,86 | 29,3 | 7 |
| climatology_dow | 15-30 | 80,5 | 95,8 | 0,744 | -55,3 | 19,8 | 40,2 | 8,9 | 0,82 | 48,6 | 17 |
| moving_average_28d | all | 102,3 | 116,6 | 0,945 | -57,8 | 20,1 | 51,1 | 21,4 | 0,52 | 67,6 | 31 |
| moving_average_28d | 1-7 | 62,8 | 90,8 | 0,580 | -20,1 | 17,1 | 31,4 | 17,6 | 0,71 | 48,6 | 7 |
| moving_average_28d | 8-14 | 90,6 | 101,6 | 0,837 | -52,4 | 19,1 | 45,3 | 13,7 | 0,71 | 61,0 | 7 |
| moving_average_28d | 15-30 | 123,3 | 130,8 | 1,139 | -75,5 | 21,7 | 61,7 | 26,1 | 0,35 | 78,1 | 17 |
| seasonal_naive | all | 73,3 | 95,4 | 0,677 | -49,1 | 17,4 | 36,6 | 19,4 | 0,90 | 45,5 | 31 |
| seasonal_naive | 1-7 | 55,4 | 78,2 | 0,512 | -14,0 | 12,1 | 27,7 | 29,4 | 0,86 | 47,3 | 7 |
| seasonal_naive | 8-14 | 49,7 | 63,0 | 0,459 | -46,3 | 14,2 | 24,9 | 15,1 | 1,00 | 31,1 | 7 |
| seasonal_naive | 15-30 | 90,3 | 111,5 | 0,834 | -64,8 | 20,8 | 45,1 | 17,1 | 0,88 | 50,6 | 17 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 62,0). Vertailukohtien MAE: seasonal_naive 73,3, moving_average_28d 102,3, climatology_dow 62,0.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +46,0 | +27,1 … +66,1 | huonompi kuin vertailukohta | -0,743 | -1,049 … -0,420 | 25,3 | 40,8 % | 3,61 | 0,018 | 0,037 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 2.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,45 (14/31) | 0,27 … 0,64 | liian kapea | -97,3 | -132,1 … -70,2 | -48,0 % | aliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 106,4 | 108,0 | 105,6 | -0,8 | -0,8 % |

`perfect` on yläraja: mihin malli pystyisi jos sää tiedettäisiin täydellisesti. `climatology` on alaraja: mihin se pystyy ilman sääennustetta. `operational` on realistisin arvio ja se olettaa hyvän sääennusteen. Sään tuoma parannus on `climatology`n MAE miinus `perfect`in MAE: **positiivinen luku tarkoittaa että sään tunteminen auttaa**, ja se on se osa mallin osumatarkkuudesta joka lepää sään tuntemisen varassa.

⚠ **Parannus on negatiivinen**, eli malli ennustaa tällä ikkunalla *paremmin* keskiarvosäällä kuin toteutuneella säällä. Se ei ole mittausvirhe vaan tulos: mallin oppima sääriippuvuus ei yleisty tähän jaksoon, vaan toteutunut sää vie ennustetta väärään suuntaan. Sääpiirteet sopivat siis koulutusjakson kohinaan enemmän kuin kävijöiden todelliseen sääkäyttäytymiseen.

| Sään tila | Toteutunutta säätä | Klimatologiaa |
| --- | --- | --- |
| perfect (toteutunut sää) | 31 | 0 |
| operational (toteutunut vrk 1-16, klimatologia 17+) | 16 | 15 |
| climatology (klimatologia koko jaksolta) | 0 | 31 |

### 9. Pahiten menneet päivät

**baseline**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-07-28 | tiistai | 387 | 135 | -252 | runsas sade 13.9 mm; malli sai klimatologiasään (horisontti 28 vrk) |
| 2026-07-15 | keskiviikko | 309 | 112 | -197 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-07-22 | keskiviikko | 304 | 109 | -195 | malli sai klimatologiasään (horisontti 22 vrk) |
| 2026-07-17 | perjantai | 281 | 95 | -186 | malli sai klimatologiasään (horisontti 17 vrk) |
| 2026-07-24 | perjantai | 279 | 94 | -185 | malli sai klimatologiasään (horisontti 24 vrk) |

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
