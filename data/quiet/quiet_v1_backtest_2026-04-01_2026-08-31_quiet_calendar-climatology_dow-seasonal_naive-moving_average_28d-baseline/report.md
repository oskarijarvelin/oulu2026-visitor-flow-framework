# Hiljaisten päivien ennustemallin luotettavuus

Ajon tunniste: `quiet_v1_backtest_2026-04-01_2026-08-31_quiet_calendar-climatology_dow-seasonal_naive-moving_average_28d-baseline`

## 1. Verdikti

- Pekuri (1) / `baseline`: valitut päivät olivat 8 % mediaanipäivää hiljaisempia (95 % väli -1 % … 20 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 40 % kun satunnaisvalinta antaisi 22 %.
- Pekuri (1) / `climatology_dow`: valitut päivät olivat 3 % mediaanipäivää hiljaisempia (95 % väli -1 % … 9 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 36 % kun satunnaisvalinta antaisi 22 %.
- Pekuri (1) / `moving_average_28d`: valitut päivät olivat -14 % mediaanipäivää hiljaisempia (95 % väli -22 % … -6 %, 5 ikkunaa), valinta osuu keskimääräistä vilkkaampiin päiviin; osuvuus 20 % kun satunnaisvalinta antaisi 22 %.
- Pekuri (1) / `quiet_calendar`: valitut päivät olivat 2 % mediaanipäivää hiljaisempia (95 % väli -1 % … 9 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 36 % kun satunnaisvalinta antaisi 22 %.
- Pekuri (1) / `seasonal_naive`: valitut päivät olivat 8 % mediaanipäivää hiljaisempia (95 % väli -4 % … 18 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 40 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `baseline`: valitut päivät olivat 43 % mediaanipäivää hiljaisempia (95 % väli 26 % … 57 %, 5 ikkunaa), hyöty on todennettu; osuvuus 60 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `climatology_dow`: valitut päivät olivat 45 % mediaanipäivää hiljaisempia (95 % väli 25 % … 65 %, 5 ikkunaa), hyöty on todennettu; osuvuus 65 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `moving_average_28d`: valitut päivät olivat -16 % mediaanipäivää hiljaisempia (95 % väli -42 % … 11 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 18 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `quiet_calendar`: valitut päivät olivat 45 % mediaanipäivää hiljaisempia (95 % väli 25 % … 65 %, 5 ikkunaa), hyöty on todennettu; osuvuus 65 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `seasonal_naive`: valitut päivät olivat 30 % mediaanipäivää hiljaisempia (95 % väli 3 % … 55 %, 5 ikkunaa), hyöty on todennettu; osuvuus 50 % kun satunnaisvalinta antaisi 22 %.

## 2. Menetelmä

- Ikkunoita: 5 (2026-04-01 – 2026-08-31)
- Ikkunatyyppi: monthly
- Säännöt: `quiet_calendar`, `climatology_dow`, `seasonal_naive`, `moving_average_28d`, `baseline`
- Kynnys: hiljaisin 20 % ehdokaspäivistä
- Bootstrap-toistoja: 10 000, siemenluku 20 260 101

Jokainen ikkuna opetetaan origoonsa asti, nimetään sen jälkeen jakson hiljaisimmat päivät ja avataan vasta sitten toteuma. Luottamusväli arvotaan kokonaisista ikkunoista, ei päivistä: saman kuukauden päivät jakavat origon, opetusjakson ja sään, eivätkä ole toisistaan riippumattomia havaintoja.

## 3. Tulokset

| Kohde | Sääntö | Ikkunoita | Hyöty | 95 % väli | Osuvuus | Satunnais | Talteen | Spearman | Verdikti |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Pekuri | `baseline` | 5 | 8 % | -1 % … 20 % | 40 % | 22 % | 24 % | 0,31 | hyötyä ei ole todennettu |
| Pekuri | `climatology_dow` | 5 | 3 % | -1 % … 9 % | 36 % | 22 % | 8 % | 0,36 | hyötyä ei ole todennettu |
| Pekuri | `moving_average_28d` | 5 | -14 % | -22 % … -6 % | 20 % | 22 % | -42 % | – | valinta osuu keskimääräistä vilkkaampiin päiviin |
| Pekuri | `quiet_calendar` | 5 | 2 % | -1 % … 9 % | 36 % | 22 % | 7 % | 0,38 | hyötyä ei ole todennettu |
| Pekuri | `seasonal_naive` | 5 | 8 % | -4 % … 18 % | 40 % | 22 % | 24 % | 0,33 | hyötyä ei ole todennettu |
| Kaupungintalo | `baseline` | 5 | 43 % | 26 % … 57 % | 60 % | 22 % | 66 % | 0,49 | hyöty on todennettu |
| Kaupungintalo | `climatology_dow` | 5 | 45 % | 25 % … 65 % | 65 % | 22 % | 70 % | 0,41 | hyöty on todennettu |
| Kaupungintalo | `moving_average_28d` | 5 | -16 % | -42 % … 11 % | 18 % | 22 % | -24 % | – | hyötyä ei ole todennettu |
| Kaupungintalo | `quiet_calendar` | 5 | 45 % | 25 % … 65 % | 65 % | 22 % | 70 % | 0,40 | hyöty on todennettu |
| Kaupungintalo | `seasonal_naive` | 5 | 30 % | 3 % … 55 % | 50 % | 22 % | 46 % | 0,24 | hyöty on todennettu |

**Hyöty** on 1 − (valittujen päivien keskiarvo ÷ kuukauden mediaanipäivä): kuinka paljon hiljaisempi suositus oli kuin mielivaltainen päivä. **Talteen** vertaa sitä siihen, mikä olisi ollut mahdollista jälkiviisaasti. **Osuvuus** on osuus nimetyistä päivistä, jotka todella kuuluivat hiljaisimpiin, ja **satunnais** se, minkä arvaus antaisi.

- Pekuri / `baseline`: pienin havaittava hyöty on 16 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
- Pekuri / `climatology_dow`: pienin havaittava hyöty on 9 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
- Pekuri / `quiet_calendar`: pienin havaittava hyöty on 9 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
- Pekuri / `seasonal_naive`: pienin havaittava hyöty on 17 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
- Kaupungintalo / `moving_average_28d`: pienin havaittava hyöty on 43 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ei eroa satunnaisvalinnasta.

## 4. Ikkunakohtaiset tulokset

| Kohde | Sääntö | Jakso | Ehdokkaita | k | Hyöty | Paras mahdollinen | Osuvuus | Hiljaisin valinta |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | `quiet_calendar` | 2026-04-01 – 2026-04-30 | 30 | 6 | 15 % | 38 % | 33 % | 122 % |
| 1 | `climatology_dow` | 2026-04-01 – 2026-04-30 | 30 | 6 | 15 % | 38 % | 33 % | 122 % |
| 1 | `seasonal_naive` | 2026-04-01 – 2026-04-30 | 30 | 6 | 22 % | 38 % | 50 % | 104 % |
| 1 | `moving_average_28d` | 2026-04-01 – 2026-04-30 | 30 | 6 | -21 % | 38 % | 0 % | 114 % |
| 1 | `baseline` | 2026-04-01 – 2026-04-30 | 30 | 6 | 27 % | 38 % | 50 % | 122 % |
| 1 | `quiet_calendar` | 2026-05-01 – 2026-05-31 | 31 | 7 | -0 % | 35 % | 43 % | 111 % |
| 1 | `climatology_dow` | 2026-05-01 – 2026-05-31 | 31 | 7 | 2 % | 35 % | 43 % | 84 % |
| 1 | `seasonal_naive` | 2026-05-01 – 2026-05-31 | 31 | 7 | -14 % | 35 % | 29 % | 84 % |
| 1 | `moving_average_28d` | 2026-05-01 – 2026-05-31 | 31 | 7 | -28 % | 35 % | 14 % | 97 % |
| 1 | `baseline` | 2026-05-01 – 2026-05-31 | 31 | 7 | 1 % | 35 % | 29 % | 62 % |
| 1 | `quiet_calendar` | 2026-06-01 – 2026-06-30 | 30 | 6 | -1 % | 39 % | 33 % | 79 % |
| 1 | `climatology_dow` | 2026-06-01 – 2026-06-30 | 30 | 6 | -1 % | 39 % | 33 % | 79 % |
| 1 | `seasonal_naive` | 2026-06-01 – 2026-06-30 | 30 | 6 | 11 % | 39 % | 50 % | 44 % |
| 1 | `moving_average_28d` | 2026-06-01 – 2026-06-30 | 30 | 6 | -12 % | 39 % | 17 % | 79 % |
| 1 | `baseline` | 2026-06-01 – 2026-06-30 | 30 | 6 | -4 % | 39 % | 33 % | 79 % |
| 1 | `quiet_calendar` | 2026-07-01 – 2026-07-31 | 31 | 7 | -1 % | 24 % | 29 % | 69 % |
| 1 | `climatology_dow` | 2026-07-01 – 2026-07-31 | 31 | 7 | -1 % | 24 % | 29 % | 69 % |
| 1 | `seasonal_naive` | 2026-07-01 – 2026-07-31 | 31 | 7 | 14 % | 24 % | 43 % | 69 % |
| 1 | `moving_average_28d` | 2026-07-01 – 2026-07-31 | 31 | 7 | 1 % | 24 % | 57 % | 66 % |
| 1 | `baseline` | 2026-07-01 – 2026-07-31 | 31 | 7 | 1 % | 24 % | 43 % | 88 % |
| 1 | `quiet_calendar` | 2026-08-01 – 2026-08-31 | 31 | 7 | -0 % | 32 % | 43 % | 78 % |
| 1 | `climatology_dow` | 2026-08-01 – 2026-08-31 | 31 | 7 | -0 % | 32 % | 43 % | 78 % |
| 1 | `seasonal_naive` | 2026-08-01 – 2026-08-31 | 31 | 7 | 8 % | 32 % | 29 % | 131 % |
| 1 | `moving_average_28d` | 2026-08-01 – 2026-08-31 | 31 | 7 | -9 % | 32 % | 14 % | 120 % |
| 1 | `baseline` | 2026-08-01 – 2026-08-31 | 31 | 7 | 17 % | 32 % | 43 % | 109 % |
| 2 | `quiet_calendar` | 2026-04-01 – 2026-04-30 | 28 | 6 | 22 % | 75 % | 33 % | 25 % |
| 2 | `climatology_dow` | 2026-04-01 – 2026-04-30 | 28 | 6 | 22 % | 75 % | 33 % | 25 % |
| 2 | `seasonal_naive` | 2026-04-01 – 2026-04-30 | 28 | 6 | 26 % | 75 % | 33 % | 25 % |
| 2 | `moving_average_28d` | 2026-04-01 – 2026-04-30 | 28 | 6 | -60 % | 75 % | 0 % | 186 % |
| 2 | `baseline` | 2026-04-01 – 2026-04-30 | 28 | 6 | 39 % | 75 % | 50 % | 25 % |
| 2 | `quiet_calendar` | 2026-05-01 – 2026-05-31 | 31 | 7 | 55 % | 63 % | 71 % | 32 % |
| 2 | `climatology_dow` | 2026-05-01 – 2026-05-31 | 31 | 7 | 55 % | 63 % | 71 % | 32 % |
| 2 | `seasonal_naive` | 2026-05-01 – 2026-05-31 | 31 | 7 | 22 % | 63 % | 57 % | 32 % |
| 2 | `moving_average_28d` | 2026-05-01 – 2026-05-31 | 31 | 7 | -42 % | 63 % | 29 % | 85 % |
| 2 | `baseline` | 2026-05-01 – 2026-05-31 | 31 | 7 | 45 % | 63 % | 57 % | 32 % |
| 2 | `quiet_calendar` | 2026-06-01 – 2026-06-30 | 27 | 6 | 77 % | 77 % | 100 % | 13 % |
| 2 | `climatology_dow` | 2026-06-01 – 2026-06-30 | 27 | 6 | 77 % | 77 % | 100 % | 13 % |
| 2 | `seasonal_naive` | 2026-06-01 – 2026-06-30 | 27 | 6 | 70 % | 77 % | 83 % | 13 % |
| 2 | `moving_average_28d` | 2026-06-01 – 2026-06-30 | 27 | 6 | 11 % | 77 % | 17 % | 13 % |
| 2 | `baseline` | 2026-06-01 – 2026-06-30 | 27 | 6 | 66 % | 77 % | 83 % | 13 % |
| 2 | `quiet_calendar` | 2026-07-01 – 2026-07-31 | 31 | 7 | 58 % | 78 % | 71 % | 1 % |
| 2 | `climatology_dow` | 2026-07-01 – 2026-07-31 | 31 | 7 | 58 % | 78 % | 71 % | 1 % |
| 2 | `seasonal_naive` | 2026-07-01 – 2026-07-31 | 31 | 7 | 51 % | 78 % | 57 % | 1 % |
| 2 | `moving_average_28d` | 2026-07-01 – 2026-07-31 | 31 | 7 | 21 % | 78 % | 43 % | 77 % |
| 2 | `baseline` | 2026-07-01 – 2026-07-31 | 31 | 7 | 52 % | 78 % | 57 % | 5 % |
| 2 | `quiet_calendar` | 2026-08-01 – 2026-08-31 | 26 | 6 | 16 % | 33 % | 50 % | 92 % |
| 2 | `climatology_dow` | 2026-08-01 – 2026-08-31 | 26 | 6 | 16 % | 33 % | 50 % | 92 % |
| 2 | `seasonal_naive` | 2026-08-01 – 2026-08-31 | 26 | 6 | -19 % | 33 % | 17 % | 121 % |
| 2 | `moving_average_28d` | 2026-08-01 – 2026-08-31 | 26 | 6 | -9 % | 33 % | 0 % | 121 % |
| 2 | `baseline` | 2026-08-01 – 2026-08-31 | 26 | 6 | 13 % | 33 % | 50 % | 84 % |

## 5. Todennäköisyyksien kalibrointi

Jokainen ehdokaspäivä tuottaa yhden parin: mallin antama todennäköisyys ja se, kuuluiko päivä lopulta hiljaisimpiin. Hyvin kalibroidussa mallissa sarakkeet ovat lähellä toisiaan.

| Kohde | Sääntö | Väli | n | Ennustettu | Toteutunut |
| --- | --- | --- | ---: | ---: | ---: |
| Pekuri | `baseline` | 0.00-0.10 | 46 | 4 % | 15 % |
| Pekuri | `baseline` | 0.10-0.25 | 47 | 16 % | 17 % |
| Pekuri | `baseline` | 0.25-0.50 | 50 | 36 % | 26 % |
| Pekuri | `baseline` | 0.50-0.75 | 10 | 54 % | 50 % |
| Pekuri | `climatology_dow` | 0.00-0.10 | 41 | 3 % | 20 % |
| Pekuri | `climatology_dow` | 0.10-0.25 | 58 | 17 % | 12 % |
| Pekuri | `climatology_dow` | 0.25-0.50 | 50 | 39 % | 32 % |
| Pekuri | `climatology_dow` | 0.50-0.75 | 4 | 51 % | 50 % |
| Pekuri | `moving_average_28d` | 0.10-0.25 | 144 | 21 % | 21 % |
| Pekuri | `moving_average_28d` | 0.25-0.50 | 9 | 26 % | 33 % |
| Pekuri | `quiet_calendar` | 0.00-0.10 | 38 | 3 % | 18 % |
| Pekuri | `quiet_calendar` | 0.10-0.25 | 59 | 17 % | 12 % |
| Pekuri | `quiet_calendar` | 0.25-0.50 | 55 | 38 % | 34 % |
| Pekuri | `quiet_calendar` | 0.50-0.75 | 1 | 53 % | 0 % |
| Pekuri | `seasonal_naive` | 0.00-0.10 | 51 | 3 % | 14 % |
| Pekuri | `seasonal_naive` | 0.10-0.25 | 46 | 19 % | 20 % |
| Pekuri | `seasonal_naive` | 0.25-0.50 | 44 | 37 % | 23 % |
| Pekuri | `seasonal_naive` | 0.50-0.75 | 12 | 58 % | 58 % |
| Kaupungintalo | `baseline` | 0.00-0.10 | 31 | 7 % | 13 % |
| Kaupungintalo | `baseline` | 0.10-0.25 | 80 | 16 % | 10 % |
| Kaupungintalo | `baseline` | 0.25-0.50 | 16 | 31 % | 31 % |
| Kaupungintalo | `baseline` | 0.50-0.75 | 9 | 64 % | 100 % |
| Kaupungintalo | `baseline` | 0.75-0.90 | 4 | 85 % | 100 % |
| Kaupungintalo | `baseline` | 0.90-1.00 | 3 | 100 % | 67 % |
| Kaupungintalo | `climatology_dow` | 0.00-0.10 | 50 | 8 % | 10 % |
| Kaupungintalo | `climatology_dow` | 0.10-0.25 | 70 | 15 % | 13 % |
| Kaupungintalo | `climatology_dow` | 0.25-0.50 | 7 | 34 % | 43 % |
| Kaupungintalo | `climatology_dow` | 0.75-0.90 | 4 | 89 % | 100 % |
| Kaupungintalo | `climatology_dow` | 0.90-1.00 | 12 | 97 % | 92 % |
| Kaupungintalo | `moving_average_28d` | 0.10-0.25 | 138 | 22 % | 22 % |
| Kaupungintalo | `moving_average_28d` | 0.25-0.50 | 5 | 25 % | 20 % |
| Kaupungintalo | `quiet_calendar` | 0.00-0.10 | 50 | 8 % | 10 % |
| Kaupungintalo | `quiet_calendar` | 0.10-0.25 | 70 | 15 % | 13 % |
| Kaupungintalo | `quiet_calendar` | 0.25-0.50 | 7 | 34 % | 43 % |
| Kaupungintalo | `quiet_calendar` | 0.75-0.90 | 3 | 89 % | 100 % |
| Kaupungintalo | `quiet_calendar` | 0.90-1.00 | 13 | 97 % | 92 % |
| Kaupungintalo | `seasonal_naive` | 0.00-0.10 | 57 | 6 % | 18 % |
| Kaupungintalo | `seasonal_naive` | 0.10-0.25 | 56 | 16 % | 9 % |
| Kaupungintalo | `seasonal_naive` | 0.25-0.50 | 13 | 35 % | 38 % |
| Kaupungintalo | `seasonal_naive` | 0.50-0.75 | 5 | 70 % | 100 % |
| Kaupungintalo | `seasonal_naive` | 0.90-1.00 | 12 | 94 % | 58 % |

## 6. Mitä tämä ei todista

- **Ikkunoita on vähän.** Koko historia on yksi vuosi, ja kuukausi-ikkunoita mahtuu siihen kourallinen. Pienin havaittava hyöty on kussakin verdiktissä mukana juuri siksi.
- **Yksi kohde ei kerro toisesta.** Verdikti annetaan kohteittain, koska aukioloajat, pyhäpäiväkäytäntö ja kävijäprofiili eroavat.
- **Sääntövalinta on tehty samalla datalla.** Oletussääntö valittiin näiden samojen ikkunoiden perusteella, joten sen etu muihin sääntöihin nähden on yliarvio. Kohdekohtainen hyöty sen sijaan on mitattu opetusjakson ulkopuolelta.
- **Mittaus käyttää kahta jälkiviisautta.** Ehdokasjoukko on ne päivät jotka toteutuivat havaittuina, täysinä ja nollaa suurempina, ja `k` otetaan toteuman ehdokasmäärästä. Molemmat pätevät samalla tavalla sääntöön ja satunnaisvalintaan, mutta sääntöä ei siis rangaista suljetun päivän ehdottamisesta.
- **Menneisyys ei sisällä tapahtumakalenteria.** Jos kohteessa aletaan järjestää aktivointitapahtumia hiljaisina päivinä, ne muuttavat juuri niitä päiviä, joita malli ennustaa, ja mittaus on toistettava.
