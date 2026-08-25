# Ennusteen arviointiraportti: 2026-04-01 – 2026-04-30

Ajon tunniste: `eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline-prophet_xgb`

## 1. Verdikti

Ikkuna 2026-04-01–2026-04-30 (30 vrk), koulutus päättyy 2026-03-31, koulutusikkuna all, sään tila operational. Venue 1 (Pekuri): malli baseline teki keskimäärin 102,9 kävijän päivävirheen, päävertailukohta climatology_dow 96,2. Eroa ei havaittu: +6,7 kävijää päivässä (95 % väli -3,2…+30,7). Tämä otos (30 päivää) olisi erottanut vasta 34,5 kävijän eron, eli 35,9 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 13 639, toteuma 13 189, ero +3,4 %, 80 % väli 13 639–20 089. Venue 1 (Pekuri): malli prophet_xgb teki keskimäärin 343,2 kävijän päivävirheen, päävertailukohta climatology_dow 96,2. Malli häviää vertailukohdalle tilastollisesti: ero +247,0 kävijää päivässä (95 % väli +167,1…+311,1). Yksinkertainen sääntö climatology_dow on tällä ikkunalla parempi kuin malli. Tämä otos (30 päivää) olisi erottanut vasta 103,7 kävijän eron, eli 107,8 % vertailukohdan MAE:sta. Jakson kokonaismäärä: ennuste 23 156, toteuma 13 189, ero +75,6 %, 80 % väli 14 707–23 156. Venue 2 (Kaupungintalo): malli baseline teki keskimäärin 95,5 kävijän päivävirheen, päävertailukohta climatology_dow 75,1. Malli häviää vertailukohdalle tilastollisesti: ero +20,4 kävijää päivässä (95 % väli +11,5…+47,7). Yksinkertainen sääntö climatology_dow on tällä ikkunalla parempi kuin malli. Tämä otos (30 päivää) olisi erottanut vasta 24,4 kävijän eron, eli 32,5 % vertailukohdan MAE:sta. Jakson kokonaismäärä: ennuste 6 232, toteuma 3 791, ero +64,4 %, 80 % väli 3 662–6 232. Venue 2 (Kaupungintalo): malli prophet_xgb teki keskimäärin 82,8 kävijän päivävirheen, päävertailukohta climatology_dow 75,1. Eroa ei havaittu: +7,7 kävijää päivässä (95 % väli -5,4…+31,6). Tämä otos (30 päivää) olisi erottanut vasta 21,4 kävijän eron, eli 28,5 % vertailukohdan MAE:sta; "ei eroa" ei siis tarkoita samanveroisuutta. Jakson kokonaismäärä: ennuste 5 790, toteuma 3 791, ero +52,7 %, 80 % väli 2 375–5 790. Yhden ikkunan tulos on kuvaileva, ei todistava: varsinainen näyttö syntyy usean ikkunan koosteesta.

## 2. Ikkuna ja asetelma

- Origo (viimeinen koulutuspäivä): **2026-03-31**
- Testijakso: **2026-04-01 – 2026-04-30** (30 vrk, horisontit 1–30)
- Koulutusikkuna: `all`
- Mallit: baseline, prophet_xgb
- Vertailukohdat: seasonal_naive, moving_average_28d, climatology_dow
- Päävertailukohdan valinta: `best`
- Sään tilat: perfect, operational, climatology (verdikti tilasta `operational`)
- Bootstrap: 10 000 uudelleenotantaa, lohkon pituus 7 vrk, siemen 20260101

| Venue | Koulutus alkaa | Koulutuspäiviä | Nollapäiviä | Sisäkkäisiä origoja | MASE-nimittäjä |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 90 | 21 | 3 | 141,18 |
| 2 (Kaupungintalo) | 2026-01-01 | 90 | 8 | 3 | 128,57 |

Ennustevälien kvantiilit tulevat sisäkkäisestä backtestistä, joka ajetaan kokonaan koulutusikkunan sisällä: sen viimeinen sisäorigo on origo miinus horisontti, joten yksikään sisäennuste ei ylety testijaksoon.

## Venue 1 (Pekuri)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 13 639 | 13 189 | +450 | +3,4 % | 13 639 – 20 089 | ei | 9 021 – 28 852 |
| climatology_dow | 13 292 | 13 189 | +103 | +0,8 % | 13 292 – 28 944 | ei | 13 292 – 37 419 |
| moving_average_28d | 17 336 | 13 189 | +4 147 | +31,4 % | 17 336 – 20 813 | ei | 12 546 – 27 846 |
| prophet_xgb | 23 156 | 13 189 | +9 967 | +75,6 % | 14 707 – 23 156 | ei | 11 544 – 25 100 |
| seasonal_naive | 15 172 | 13 189 | +1 983 | +15,0 % | 15 172 – 19 406 | ei | 10 655 – 23 270 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

⚠ **Näiden mallien väli ei ole kalibroitu:** climatology_dow (suhteellisten virheiden mediaani 1,86), prophet_xgb (suhteellisten virheiden mediaani 0,69). Sisäkkäisen backtestin mallit on koulutettu lyhyemmällä ja huonommalla aineistolla kuin ulompi malli, joten niiden virheissä on tasosiirtymä eikä pelkkää hajontaa. Väli perii sen. Lue kokonaismäärän ero ja bias erikseen, älä väliä.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 102,9 | 134,3 | 0,729 | +15,0 | 16,0 | 51,5 | 52,2 | 0,90 | 24,5 | 30 |
| baseline | 1-7 | 83,2 | 110,9 | 0,589 | -34,5 | 15,6 | 41,6 | 35,7 | 0,86 | 21,2 | 7 |
| baseline | 8-14 | 146,1 | 154,8 | 1,035 | +88,2 | 16,3 | 73,0 | 55,8 | 0,71 | 35,6 | 7 |
| baseline | 15-30 | 92,6 | 134,1 | 0,656 | +4,6 | 16,1 | 46,3 | 57,9 | 1,00 | 21,1 | 16 |
| climatology_dow | all | 96,2 | 122,7 | 0,681 | +3,4 | 49,5 | 48,1 | 80,8 | 0,33 | 22,3 | 30 |
| climatology_dow | 1-7 | 100,7 | 105,4 | 0,713 | -8,9 | 46,8 | 50,3 | 73,6 | 0,57 | 22,9 | 7 |
| climatology_dow | 8-14 | 100,5 | 124,1 | 0,712 | +58,0 | 73,5 | 50,3 | 92,9 | 0,14 | 24,3 | 7 |
| climatology_dow | 15-30 | 92,4 | 129,0 | 0,654 | -15,1 | 40,2 | 46,2 | 78,6 | 0,31 | 21,1 | 16 |
| moving_average_28d | all | 197,6 | 219,8 | 1,400 | +138,2 | 56,9 | 98,8 | 48,9 | 0,40 | 41,9 | 30 |
| moving_average_28d | 1-7 | 143,2 | 156,9 | 1,014 | +122,6 | 38,7 | 71,6 | 45,3 | 0,43 | 29,0 | 7 |
| moving_average_28d | 8-14 | 202,9 | 238,7 | 1,437 | +189,4 | 88,2 | 101,4 | 55,7 | 0,29 | 46,8 | 7 |
| moving_average_28d | 15-30 | 219,1 | 234,3 | 1,552 | +122,7 | 51,2 | 109,6 | 47,4 | 0,44 | 45,5 | 16 |
| prophet_xgb | all | 343,2 | 382,9 | 2,431 | +332,2 | 46,7 | 171,6 | 39,7 | 0,57 | 58,8 | 30 |
| prophet_xgb | 1-7 | 165,0 | 210,5 | 1,168 | +117,9 | 35,2 | 82,5 | 26,6 | 0,57 | 30,1 | 7 |
| prophet_xgb | 8-14 | 435,4 | 455,5 | 3,084 | +435,4 | 105,0 | 217,7 | 56,5 | 0,14 | 75,1 | 7 |
| prophet_xgb | 15-30 | 380,9 | 405,8 | 2,698 | +380,9 | 26,3 | 190,4 | 38,1 | 0,75 | 64,2 | 16 |
| seasonal_naive | all | 129,5 | 158,1 | 0,917 | +66,1 | 26,1 | 64,8 | 33,6 | 0,67 | 28,1 | 30 |
| seasonal_naive | 1-7 | 114,7 | 120,2 | 0,813 | +42,7 | 16,0 | 57,4 | 31,6 | 0,57 | 24,8 | 7 |
| seasonal_naive | 8-14 | 146,1 | 164,6 | 1,035 | +109,6 | 27,7 | 73,1 | 35,4 | 0,43 | 33,2 | 7 |
| seasonal_naive | 15-30 | 128,7 | 169,4 | 0,912 | +57,3 | 29,8 | 64,3 | 33,7 | 0,81 | 27,3 | 16 |

Testijaksolla ei ole nollapäiviä, joten sMAPE on tässä ikkunassa luettavissa.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 96,2). Vertailukohtien MAE: seasonal_naive 129,5, moving_average_28d 197,6, climatology_dow 96,2.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +6,7 | -3,2 … +30,7 | ei havaittavaa eroa vertailukohtaan | -0,070 | -0,314 … 0,034 | 34,5 | 35,9 % | 0,56 | 0,610 | 1,000 |
| prophet_xgb | +247,0 | +167,1 … +311,1 | huonompi kuin vertailukohta | -2,568 | -3,617 … -1,607 | 103,7 | 107,8 % | 4,47 | 0,003 | 0,012 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 4.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,90 (27/30) | 0,73 … 0,98 | kalibroitu | +15,0 | -16,7 … +56,4 | +3,4 % | ei systemaattista harhaa |
| prophet_xgb | 0,57 (17/30) | 0,37 … 0,75 | liian kapea | +332,2 | +245,6 … +407,7 | +75,6 % | yliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 108,1 | 102,9 | 107,9 | -0,2 | -0,2 % |
| prophet_xgb | 356,7 | 343,2 | 325,5 | -31,2 | -9,6 % |

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
| 2026-04-16 | torstai | 788 | 386 | -402 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-04-24 | perjantai | 683 | 472 | -211 | malli sai klimatologiasään (horisontti 24 vrk) |
| 2026-04-05 | sunnuntai | 485 | 280 | -205 | pyhäpäivä: Toinen pääsiäispäivä; viikonloppu |
| 2026-04-10 | perjantai | 625 | 422 | -203 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-04-08 | keskiviikko | 360 | 543 | +183 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |

**prophet_xgb**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-04-11 | lauantai | 556 | 1 218 | +662 | viikonloppu |
| 2026-04-30 | torstai | 364 | 939 | +575 | malli sai klimatologiasään (horisontti 30 vrk) |
| 2026-04-28 | tiistai | 284 | 848 | +564 | malli sai klimatologiasään (horisontti 28 vrk) |
| 2026-04-29 | keskiviikko | 254 | 801 | +547 | malli sai klimatologiasään (horisontti 29 vrk) |
| 2026-04-12 | sunnuntai | 212 | 748 | +536 | viikonloppu |

Tämä on raportin käytännöllisin osa: se kertoo mitä mallista puuttuu. Toistuva syy samassa sarakkeessa on suora ehdotus seuraavaksi piirteeksi.

## Venue 2 (Kaupungintalo)

### 3. Jakson kokonaismäärä

| Malli | Ennuste | Toteuma | Ero | Ero % | 80 % väli | Väli osuu | Naiivi päiväsummaväli |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 6 232 | 3 791 | +2 441 | +64,4 % | 3 662 – 6 232 | kyllä | 1 423 – 9 112 |
| climatology_dow | 5 346 | 3 791 | +1 555 | +41,0 % | 5 346 – 7 603 | ei | 2 595 – 12 230 |
| moving_average_28d | 5 802 | 3 791 | +2 011 | +53,0 % | 5 554 – 7 626 | ei | 1 213 – 12 548 |
| prophet_xgb | 5 790 | 3 791 | +1 999 | +52,7 % | 2 375 – 5 790 | kyllä | 1 003 – 8 125 |
| seasonal_naive | 7 656 | 3 791 | +3 865 | +102,0 % | 7 093 – 14 491 | ei | 3 273 – 20 184 |

Kokonaismäärän väli on simuloitu: koulutusikkunan sisäisen backtestin päivätason suhteellisia virheitä bootstrapataan lohkoina kokonaisiksi jaksoiksi, jokainen simuloitu polku summataan ja väli luetaan summien jakaumasta. Viimeinen sarake näyttää, mihin päivien p10- ja p90-arvojen summaaminen olisi johtanut; se olettaa kaikkien päivien virheiden osuvan samaan suuntaan eikä ole kokonaismäärän väli.

⚠ **Näiden mallien väli ei ole kalibroitu:** baseline (suhteellisten virheiden mediaani 0,65), prophet_xgb (suhteellisten virheiden mediaani 0,45). Sisäkkäisen backtestin mallit on koulutettu lyhyemmällä ja huonommalla aineistolla kuin ulompi malli, joten niiden virheissä on tasosiirtymä eikä pelkkää hajontaa. Väli perii sen. Lue kokonaismäärän ero ja bias erikseen, älä väliä.

### 4. Päivätason mittarit

Sään tila `operational`. Pinball-tappio kvantiileille 0,1 / 0,5 / 0,9.

| Malli | Horisontti | MAE | RMSE | MASE | Bias | Pinball 0,1 | Pinball 0,5 | Pinball 0,9 | Peittävyys 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 95,5 | 117,7 | 0,743 | +81,4 | 12,1 | 47,7 | 20,5 | 0,80 | 69,4 ⚠ | 30 |
| baseline | 1-7 | 80,9 | 102,2 | 0,629 | +34,3 | 19,4 | 40,5 | 18,9 | 0,57 | 80,0 ⚠ | 7 |
| baseline | 8-14 | 94,6 | 111,1 | 0,736 | +94,6 | 8,7 | 47,3 | 16,0 | 1,00 | 49,6 | 7 |
| baseline | 15-30 | 102,3 | 126,6 | 0,795 | +96,2 | 10,3 | 51,1 | 23,2 | 0,81 | 73,5 | 16 |
| climatology_dow | all | 75,1 | 95,6 | 0,584 | +51,8 | 18,1 | 37,6 | 28,8 | 0,70 | 61,5 ⚠ | 30 |
| climatology_dow | 1-7 | 81,3 | 102,3 | 0,632 | +28,9 | 22,2 | 40,7 | 31,8 | 0,71 | 81,5 ⚠ | 7 |
| climatology_dow | 8-14 | 52,0 | 63,4 | 0,404 | +17,8 | 7,9 | 26,0 | 24,0 | 1,00 | 32,6 | 7 |
| climatology_dow | 15-30 | 82,6 | 103,9 | 0,642 | +76,7 | 20,7 | 41,3 | 29,6 | 0,56 | 65,3 | 16 |
| moving_average_28d | all | 88,2 | 106,3 | 0,686 | +67,0 | 14,7 | 44,1 | 29,2 | 0,83 | 68,4 ⚠ | 30 |
| moving_average_28d | 1-7 | 103,9 | 119,5 | 0,808 | +46,0 | 26,3 | 52,0 | 29,9 | 0,71 | 82,1 ⚠ | 7 |
| moving_average_28d | 8-14 | 67,5 | 86,8 | 0,525 | +34,8 | 13,1 | 33,7 | 21,9 | 1,00 | 45,8 | 7 |
| moving_average_28d | 15-30 | 90,3 | 107,9 | 0,703 | +90,3 | 10,3 | 45,2 | 32,0 | 0,81 | 72,3 | 16 |
| prophet_xgb | all | 82,8 | 106,5 | 0,644 | +66,6 | 12,9 | 41,4 | 18,4 | 0,73 | 73,3 ⚠ | 30 |
| prophet_xgb | 1-7 | 91,9 | 121,5 | 0,715 | +56,7 | 21,8 | 45,9 | 35,2 | 0,71 | 80,7 ⚠ | 7 |
| prophet_xgb | 8-14 | 79,1 | 93,7 | 0,615 | +79,1 | 11,8 | 39,5 | 11,8 | 1,00 | 49,2 | 7 |
| prophet_xgb | 15-30 | 80,5 | 104,7 | 0,626 | +65,5 | 9,5 | 40,2 | 14,0 | 0,62 | 80,5 | 16 |
| seasonal_naive | all | 138,6 | 171,3 | 1,078 | +128,8 | 27,3 | 69,3 | 54,6 | 0,67 | 78,9 ⚠ | 30 |
| seasonal_naive | 1-7 | 112,1 | 140,2 | 0,872 | +98,7 | 19,9 | 56,1 | 68,2 | 0,57 | 90,2 ⚠ | 7 |
| seasonal_naive | 8-14 | 105,0 | 127,8 | 0,817 | +87,6 | 7,7 | 52,5 | 51,3 | 1,00 | 45,9 | 7 |
| seasonal_naive | 15-30 | 164,8 | 198,2 | 1,282 | +160,1 | 39,1 | 82,4 | 50,2 | 0,56 | 88,4 | 16 |

⚠ sMAPE on merkitty epäluotettavaksi: testijaksolla on nollapäiviä (enimmillään 2 korissa). Nollapäivällä symmetrinen suhde saavuttaa kattonsa riippumatta siitä kuinka lähellä ennuste oli. sMAPEa ei käytetä verdiktin perustana.

### 5. Tilastollinen arvio

Päävertailukohta tällä ikkunalla: **climatology_dow** (MAE 75,1). Vertailukohtien MAE: seasonal_naive 138,6, moving_average_28d 88,2, climatology_dow 75,1.

| Malli | Keskiero d | 95 % väli | Verdikti | Taitopistemäärä | Taidon 95 % väli | MDE | MDE / vertailun MAE | DM | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +20,4 | +11,5 … +47,7 | huonompi kuin vertailukohta | -0,271 | -0,763 … -0,146 | 24,4 | 32,5 % | 1,52 | 0,276 | 0,829 |
| prophet_xgb | +7,7 | -5,4 … +31,6 | ei havaittavaa eroa vertailukohtaan | -0,102 | -0,516 … 0,069 | 21,4 | 28,5 % | 0,69 | 0,542 | 1,000 |

`d` on mallin ja vertailukohdan absoluuttisten päivävirheiden erotus; negatiivinen tarkoittaa että malli on lähempänä. Väli on liikkuvan lohkon bootstrapista (lohko 7 vrk), joka on tämän arvion ensisijainen menetelmä.

**MDE eli pienin havaittava ero** kertoo kuinka suuri eron olisi pitänyt olla, jotta tämä otos olisi sen erottanut. Kun verdikti on "ei havaittavaa eroa", MDE erottaa kaksi eri asiaa: mallit ovat yhtä hyviä, tai otos on liian pieni. Yhden kuukauden ikkunassa MDE on tällä aineistolla suuruusluokkaa 30 % vertailukohdan MAE:sta, eli kuukausi pystyy todistamaan vain suuret parannukset.

**Diebold-Mariano on toissijainen.** Yhden origon 30 virhettä eivät ole riippumattomia havaintoja: ne jakavat saman koulutusjoukon ja saman maailmantilan, joten DM:n oletukset ovat venytettyjä. p-arvo lasketaan uudelleenkeskitetystä bootstrapista, ei t-jakaumasta. Holm-korjattu p-arvo on laskettu perheelle, jonka koko on 4.

### 6. Kalibrointi ja bias

| Malli | Peittävyys 80 % | Clopper-Pearson 95 % | Kalibrointi | Bias | Bias 95 % väli | Bias % toteumasta | Biasin verdikti |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0,80 (24/30) | 0,61 … 0,92 | kalibroitu | +81,4 | +59,7 … +123,7 | +64,4 % | yliarvioi systemaattisesti |
| prophet_xgb | 0,73 (22/30) | 0,54 … 0,88 | kalibroitu | +66,6 | +44,8 … +99,0 | +52,7 % | yliarvioi systemaattisesti |

Kalibrointi on "kalibroitu", jos 0,80 on Clopper-Pearsonin eksaktin binomivälin sisällä. Bias on keskivirhe etumerkillä (ennuste miinus toteuma); jos sen väli ei sisällä nollaa, malli yli- tai aliarvioi systemaattisesti.

### 7. Sään kolmen tilan vertailu

| Malli | perfect MAE | operational MAE | climatology MAE | Sään tuoma parannus (climatology − perfect) | Osuus climatologyn MAE:sta |
| --- | --- | --- | --- | --- | --- |
| baseline | 101,5 | 95,5 | 87,5 | -14,0 | -16,0 % |
| prophet_xgb | 94,0 | 82,8 | 73,2 | -20,9 | -28,5 % |

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
| 2026-04-18 | lauantai | 5 | 238 | +233 | malli sai klimatologiasään (horisontti 18 vrk); viikonloppu |
| 2026-04-23 | torstai | 27 | 252 | +225 | malli sai klimatologiasään (horisontti 23 vrk) |
| 2026-04-15 | keskiviikko | 53 | 277 | +224 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-04-03 | perjantai | 0 | 196 | +196 | pyhäpäivä: Pitkäperjantai; toteuma 0, venue todennäköisesti kiinni |
| 2026-04-12 | sunnuntai | 85 | 274 | +189 | viikonloppu |

**prophet_xgb**

| Päivä | Viikonpäivä | Toteuma | Ennuste | Virhe | Mahdollinen syy |
| --- | --- | --- | --- | --- | --- |
| 2026-04-03 | perjantai | 0 | 258 | +258 | pyhäpäivä: Pitkäperjantai; toteuma 0, venue todennäköisesti kiinni |
| 2026-04-18 | lauantai | 5 | 202 | +197 | malli sai klimatologiasään (horisontti 18 vrk); viikonloppu |
| 2026-04-23 | torstai | 27 | 220 | +193 | malli sai klimatologiasään (horisontti 23 vrk) |
| 2026-04-15 | keskiviikko | 53 | 228 | +175 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |
| 2026-04-10 | perjantai | 142 | 298 | +156 | ei tunnistettua syytä, mahdollisesti tapahtuma jota malli ei tunne |

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
