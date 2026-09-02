# Hiljaisten päivien ennustemallin luotettavuus

Ajon tunniste: `quiet_v1_backtest_2026-04-01_2026-08-25_quiet_calendar-climatology_dow-seasonal_naive-moving_average_28d-baseline`

## 1. Verdikti

- Pekuri (1) / `baseline`: valitut päivät olivat 10 % mediaanipäivää hiljaisempia (95 % väli -1 % … 22 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 43 % kun satunnaisvalinta antaisi 21 %.
- Pekuri (1) / `climatology_dow`: valitut päivät olivat 8 % mediaanipäivää hiljaisempia (95 % väli -1 % … 17 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 40 % kun satunnaisvalinta antaisi 21 %.
- Pekuri (1) / `moving_average_28d`: valitut päivät olivat -12 % mediaanipäivää hiljaisempia (95 % väli -22 % … -1 %, 5 ikkunaa), valinta osuu keskimääräistä vilkkaampiin päiviin; osuvuus 22 % kun satunnaisvalinta antaisi 21 %.
- Pekuri (1) / `quiet_calendar`: valitut päivät olivat 7 % mediaanipäivää hiljaisempia (95 % väli -1 % … 17 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 40 % kun satunnaisvalinta antaisi 21 %.
- Pekuri (1) / `seasonal_naive`: valitut päivät olivat 10 % mediaanipäivää hiljaisempia (95 % väli -2 % … 19 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 42 % kun satunnaisvalinta antaisi 21 %.
- Kaupungintalo (2) / `baseline`: valitut päivät olivat 34 % mediaanipäivää hiljaisempia (95 % väli 7 % … 57 %, 5 ikkunaa), hyöty on todennettu; osuvuus 61 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `climatology_dow`: valitut päivät olivat 45 % mediaanipäivää hiljaisempia (95 % väli 25 % … 65 %, 5 ikkunaa), hyöty on todennettu; osuvuus 67 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `moving_average_28d`: valitut päivät olivat -16 % mediaanipäivää hiljaisempia (95 % väli -43 % … 11 %, 5 ikkunaa), hyötyä ei ole todennettu; osuvuus 18 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `quiet_calendar`: valitut päivät olivat 45 % mediaanipäivää hiljaisempia (95 % väli 25 % … 65 %, 5 ikkunaa), hyöty on todennettu; osuvuus 67 % kun satunnaisvalinta antaisi 22 %.
- Kaupungintalo (2) / `seasonal_naive`: valitut päivät olivat 29 % mediaanipäivää hiljaisempia (95 % väli 1 % … 55 %, 5 ikkunaa), hyöty on todennettu; osuvuus 50 % kun satunnaisvalinta antaisi 22 %.

## 2. Menetelmä

- Ikkunoita: 5 (2026-04-01 – 2026-08-25)
- Ikkunatyyppi: monthly
- Säännöt: `quiet_calendar`, `climatology_dow`, `seasonal_naive`, `moving_average_28d`, `baseline`
- Kynnys: hiljaisin 20 % ehdokaspäivistä
- Bootstrap-toistoja: 10 000, siemenluku 20 260 101

Jokainen ikkuna opetetaan origoonsa asti, nimetään sen jälkeen jakson hiljaisimmat päivät ja avataan vasta sitten toteuma. Luottamusväli arvotaan kokonaisista ikkunoista, ei päivistä: saman kuukauden päivät jakavat origon, opetusjakson ja sään, eivätkä ole toisistaan riippumattomia havaintoja.

## 3. Tulokset

| Kohde | Sääntö | Ikkunoita | Hyöty | 95 % väli | Osuvuus | Satunnais | Talteen | Spearman | Verdikti |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Pekuri | `baseline` | 5 | 10 % | -1 % … 22 % | 43 % | 21 % | 30 % | 0,29 | hyötyä ei ole todennettu |
| Pekuri | `climatology_dow` | 5 | 8 % | -1 % … 17 % | 40 % | 21 % | 22 % | 0,35 | hyötyä ei ole todennettu |
| Pekuri | `moving_average_28d` | 5 | -12 % | -22 % … -1 % | 22 % | 21 % | -34 % | – | valinta osuu keskimääräistä vilkkaampiin päiviin |
| Pekuri | `quiet_calendar` | 5 | 7 % | -1 % … 17 % | 40 % | 21 % | 20 % | 0,37 | hyötyä ei ole todennettu |
| Pekuri | `seasonal_naive` | 5 | 10 % | -2 % … 19 % | 42 % | 21 % | 29 % | 0,34 | hyötyä ei ole todennettu |
| Kaupungintalo | `baseline` | 5 | 34 % | 7 % … 57 % | 61 % | 22 % | 54 % | 0,46 | hyöty on todennettu |
| Kaupungintalo | `climatology_dow` | 5 | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 0,43 | hyöty on todennettu |
| Kaupungintalo | `moving_average_28d` | 5 | -16 % | -43 % … 11 % | 18 % | 22 % | -26 % | – | hyötyä ei ole todennettu |
| Kaupungintalo | `quiet_calendar` | 5 | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 0,42 | hyöty on todennettu |
| Kaupungintalo | `seasonal_naive` | 5 | 29 % | 1 % … 55 % | 50 % | 22 % | 47 % | 0,24 | hyöty on todennettu |

**Hyöty** on 1 − (valittujen päivien keskiarvo ÷ kuukauden mediaanipäivä): kuinka paljon hiljaisempi suositus oli kuin mielivaltainen päivä. **Talteen** vertaa sitä siihen, mikä olisi ollut mahdollista jälkiviisaasti. **Osuvuus** on osuus nimetyistä päivistä, jotka todella kuuluivat hiljaisimpiin, ja **satunnais** se, minkä arvaus antaisi.

- Pekuri / `baseline`: pienin havaittava hyöty on 20 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
- Pekuri / `climatology_dow`: pienin havaittava hyöty on 14 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
- Pekuri / `quiet_calendar`: pienin havaittava hyöty on 14 %, joten 5 ikkunaa erottaa vain tätä suuremman eron. Tulos on "ei todennettua hyötyä", ei "ei hyötyä". Osuvuudesta verdikti on: osuvuus ylittää satunnaisvalinnan.
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
| 1 | `quiet_calendar` | 2026-08-01 – 2026-08-25 | 25 | 5 | 23 % | 39 % | 60 % | 72 % |
| 1 | `climatology_dow` | 2026-08-01 – 2026-08-25 | 25 | 5 | 23 % | 39 % | 60 % | 72 % |
| 1 | `seasonal_naive` | 2026-08-01 – 2026-08-25 | 25 | 5 | 17 % | 39 % | 40 % | 121 % |
| 1 | `moving_average_28d` | 2026-08-01 – 2026-08-25 | 25 | 5 | 2 % | 39 % | 20 % | 111 % |
| 1 | `baseline` | 2026-08-01 – 2026-08-25 | 25 | 5 | 28 % | 39 % | 60 % | 100 % |
| 2 | `quiet_calendar` | 2026-04-01 – 2026-04-30 | 28 | 6 | 22 % | 75 % | 33 % | 25 % |
| 2 | `climatology_dow` | 2026-04-01 – 2026-04-30 | 28 | 6 | 22 % | 75 % | 33 % | 25 % |
| 2 | `seasonal_naive` | 2026-04-01 – 2026-04-30 | 28 | 6 | 26 % | 75 % | 33 % | 25 % |
| 2 | `moving_average_28d` | 2026-04-01 – 2026-04-30 | 28 | 6 | -60 % | 75 % | 0 % | 186 % |
| 2 | `baseline` | 2026-04-01 – 2026-04-30 | 28 | 6 | 11 % | 75 % | 33 % | 25 % |
| 2 | `quiet_calendar` | 2026-05-01 – 2026-05-31 | 31 | 7 | 55 % | 63 % | 71 % | 32 % |
| 2 | `climatology_dow` | 2026-05-01 – 2026-05-31 | 31 | 7 | 55 % | 63 % | 71 % | 32 % |
| 2 | `seasonal_naive` | 2026-05-01 – 2026-05-31 | 31 | 7 | 22 % | 63 % | 57 % | 32 % |
| 2 | `moving_average_28d` | 2026-05-01 – 2026-05-31 | 31 | 7 | -42 % | 63 % | 29 % | 85 % |
| 2 | `baseline` | 2026-05-01 – 2026-05-31 | 31 | 7 | 50 % | 63 % | 71 % | 32 % |
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
| 2 | `quiet_calendar` | 2026-08-01 – 2026-08-25 | 21 | 5 | 16 % | 22 % | 60 % | 91 % |
| 2 | `climatology_dow` | 2026-08-01 – 2026-08-25 | 21 | 5 | 16 % | 22 % | 60 % | 91 % |
| 2 | `seasonal_naive` | 2026-08-01 – 2026-08-25 | 21 | 5 | -23 % | 22 % | 20 % | 120 % |
| 2 | `moving_average_28d` | 2026-08-01 – 2026-08-25 | 21 | 5 | -11 % | 22 % | 0 % | 120 % |
| 2 | `baseline` | 2026-08-01 – 2026-08-25 | 21 | 5 | -9 % | 22 % | 60 % | 84 % |

## 5. Todennäköisyyksien kalibrointi

Jokainen ehdokaspäivä tuottaa yhden parin: mallin antama todennäköisyys ja se, kuuluiko päivä lopulta hiljaisimpiin. Hyvin kalibroidussa mallissa sarakkeet ovat lähellä toisiaan.

| Kohde | Sääntö | Väli | n | Ennustettu | Toteutunut |
| --- | --- | --- | ---: | ---: | ---: |
| Pekuri | `baseline` | 0.00-0.10 | 51 | 5 % | 16 % |
| Pekuri | `baseline` | 0.10-0.25 | 39 | 16 % | 15 % |
| Pekuri | `baseline` | 0.25-0.50 | 47 | 36 % | 26 % |
| Pekuri | `baseline` | 0.50-0.75 | 10 | 54 % | 50 % |
| Pekuri | `climatology_dow` | 0.00-0.10 | 40 | 3 % | 20 % |
| Pekuri | `climatology_dow` | 0.10-0.25 | 55 | 17 % | 11 % |
| Pekuri | `climatology_dow` | 0.25-0.50 | 48 | 39 % | 31 % |
| Pekuri | `climatology_dow` | 0.50-0.75 | 4 | 51 % | 50 % |
| Pekuri | `moving_average_28d` | 0.10-0.25 | 138 | 21 % | 20 % |
| Pekuri | `moving_average_28d` | 0.25-0.50 | 9 | 26 % | 33 % |
| Pekuri | `quiet_calendar` | 0.00-0.10 | 37 | 3 % | 19 % |
| Pekuri | `quiet_calendar` | 0.10-0.25 | 56 | 16 % | 11 % |
| Pekuri | `quiet_calendar` | 0.25-0.50 | 53 | 38 % | 34 % |
| Pekuri | `quiet_calendar` | 0.50-0.75 | 1 | 53 % | 0 % |
| Pekuri | `seasonal_naive` | 0.00-0.10 | 51 | 2 % | 12 % |
| Pekuri | `seasonal_naive` | 0.10-0.25 | 45 | 19 % | 20 % |
| Pekuri | `seasonal_naive` | 0.25-0.50 | 39 | 37 % | 23 % |
| Pekuri | `seasonal_naive` | 0.50-0.75 | 12 | 58 % | 58 % |
| Kaupungintalo | `baseline` | 0.00-0.10 | 29 | 8 % | 10 % |
| Kaupungintalo | `baseline` | 0.10-0.25 | 78 | 16 % | 12 % |
| Kaupungintalo | `baseline` | 0.25-0.50 | 15 | 31 % | 27 % |
| Kaupungintalo | `baseline` | 0.50-0.75 | 9 | 64 % | 100 % |
| Kaupungintalo | `baseline` | 0.75-0.90 | 3 | 79 % | 100 % |
| Kaupungintalo | `baseline` | 0.90-1.00 | 4 | 98 % | 75 % |
| Kaupungintalo | `climatology_dow` | 0.00-0.10 | 50 | 8 % | 10 % |
| Kaupungintalo | `climatology_dow` | 0.10-0.25 | 64 | 15 % | 12 % |
| Kaupungintalo | `climatology_dow` | 0.25-0.50 | 8 | 32 % | 38 % |
| Kaupungintalo | `climatology_dow` | 0.75-0.90 | 4 | 89 % | 100 % |
| Kaupungintalo | `climatology_dow` | 0.90-1.00 | 12 | 97 % | 92 % |
| Kaupungintalo | `moving_average_28d` | 0.10-0.25 | 133 | 22 % | 22 % |
| Kaupungintalo | `moving_average_28d` | 0.25-0.50 | 5 | 26 % | 40 % |
| Kaupungintalo | `quiet_calendar` | 0.00-0.10 | 50 | 8 % | 10 % |
| Kaupungintalo | `quiet_calendar` | 0.10-0.25 | 65 | 15 % | 12 % |
| Kaupungintalo | `quiet_calendar` | 0.25-0.50 | 7 | 33 % | 43 % |
| Kaupungintalo | `quiet_calendar` | 0.75-0.90 | 3 | 89 % | 100 % |
| Kaupungintalo | `quiet_calendar` | 0.90-1.00 | 13 | 97 % | 92 % |
| Kaupungintalo | `seasonal_naive` | 0.00-0.10 | 53 | 7 % | 17 % |
| Kaupungintalo | `seasonal_naive` | 0.10-0.25 | 56 | 16 % | 9 % |
| Kaupungintalo | `seasonal_naive` | 0.25-0.50 | 13 | 35 % | 38 % |
| Kaupungintalo | `seasonal_naive` | 0.50-0.75 | 5 | 70 % | 100 % |
| Kaupungintalo | `seasonal_naive` | 0.90-1.00 | 11 | 96 % | 64 % |

## 6. Mitä tämä ei todista

- **Ikkunoita on vähän.** Koko historia on yksi vuosi, ja kuukausi-ikkunoita mahtuu siihen kourallinen. Pienin havaittava hyöty on kussakin verdiktissä mukana juuri siksi.
- **Yksi kohde ei kerro toisesta.** Verdikti annetaan kohteittain, koska aukioloajat, pyhäpäiväkäytäntö ja kävijäprofiili eroavat.
- **Sääntövalinta on tehty samalla datalla.** Oletussääntö valittiin näiden samojen ikkunoiden perusteella, joten sen etu muihin sääntöihin nähden on yliarvio. Kohdekohtainen hyöty sen sijaan on mitattu opetusjakson ulkopuolelta.
- **Mittaus käyttää kahta jälkiviisautta.** Ehdokasjoukko on ne päivät jotka toteutuivat havaittuina, täysinä ja nollaa suurempina, ja `k` otetaan toteuman ehdokasmäärästä. Molemmat pätevät samalla tavalla sääntöön ja satunnaisvalintaan, mutta sääntöä ei siis rangaista suljetun päivän ehdottamisesta.
- **Menneisyys ei sisällä tapahtumakalenteria.** Jos kohteessa aletaan järjestää aktivointitapahtumia hiljaisina päivinä, ne muuttavat juuri niitä päiviä, joita malli ennustaa, ja mittaus on toistettava.
