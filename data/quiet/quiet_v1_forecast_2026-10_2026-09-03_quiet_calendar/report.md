# Kuukauden hiljaisimmat päivät: lokakuu 2026

Ajon tunniste: `quiet_v1_forecast_2026-10_2026-09-03_quiet_calendar`

## 1. Vastaus

Pekuri (1), lokakuu 2026: hiljaisimmat päivät ovat su 4.10., ma 5.10., su 11.10., ma 12.10., su 18.10., ma 19.10., su 25.10.. Kynnys on kuukauden hiljaisin viidennes, 7 päivää 31 ehdokkaasta, ja malli erottaa ne 14 % mediaanipäivän alapuolelle. Varmin valinta on su 4.10., jonka todennäköisyys kuulua hiljaisimpiin on 48 %. Malli ei kuitenkaan erottele kuukauden päiviä merkittävästi: hiljaisin viidennes jää alle 15 % mediaanipäivän alapuolelle, joten järjestys kannattaa lukea suuntaa antavana. Mitattu luotettavuus (5 ikkunaa, ajo `quiet_v1_backtest_2026-04-01_2026-08-31_quiet_calendar-climatology_dow-seasonal_naive-moving_average_28d-baseline`): valitut päivät olivat keskimäärin 2 % (95 % väli -1 % … 9 %) mediaanipäivää hiljaisempia, eli hyötyä ei ole todennettu.

Kaupungintalo (2), lokakuu 2026: hiljaisimmat päivät ovat to 1.10., su 4.10., to 8.10., su 11.10., su 18.10., su 25.10.. Kynnys on kuukauden hiljaisin viidennes, 6 päivää 27 ehdokkaasta, ja malli erottaa ne 16 % mediaanipäivän alapuolelle. Varmin valinta on su 4.10., jonka todennäköisyys kuulua hiljaisimpiin on 37 %. Mitattu luotettavuus (5 ikkunaa, ajo `quiet_v1_backtest_2026-04-01_2026-08-31_quiet_calendar-climatology_dow-seasonal_naive-moving_average_28d-baseline`): valitut päivät olivat keskimäärin 45 % (95 % väli 25 % … 65 %) mediaanipäivää hiljaisempia, eli hyöty on todennettu.

## 2. Miten luku on muodostettu

- Pisteytyssääntö: `quiet_calendar`
- Kynnys: kuukauden hiljaisin 20 % ehdokaspäivistä, vähintään 3 ja enintään 10 päivää
- Simulaatioita todennäköisyyttä kohden: 10 000
- Siemenluku: 20 260 101

Pisteluku on kävijämäärän suuruusluokassa, mutta se on järjestysluku eikä ennuste: kaikki alla olevat suhdeluvut on jaettu kuukauden mediaanipäivällä, jolloin tason virhe kumoutuu eikä vaikuta järjestykseen.

Mallin erottelu ja toteutuva ero ovat kaksi eri lukua, eikä toinen ennusta toista. Pisteluku on ehdollinen keskiarvo, joten se on aina toteumaa tasaisempi: alla oleva suhdeluku kertoo, kuinka kauas malli päivät erottaa, ei kuinka hiljaisia ne toteutuvat olemaan. Toteutuvan eron arvio saadaan vain mittaamalla, ja se on komennon `quiet backtest` tulos.

## 3. Pekuri (1)

Origo 2026-09-03, sääntö `quiet_calendar`. Ehdokaspäiviä 31, hiljaisia päiviä 7. Kynnysarvo on 430,2 kävijätapahtumaa, eli 95 % mediaanipäivästä.

### Hiljaisimmat päivät

| Päivä | Sija | Suhde mediaaniin | Todennäköisyys | Samanarvoisia | Pyhä | Lämpötila | Sade |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| su 4.10. | 1 | 80 % | 48 % | 4 | – | 6,0 | 1,5 |
| ma 5.10. | 5 | 95 % | 29 % | 4 | – | 5,9 | 3,5 |
| su 11.10. | 2 | 80 % | 48 % | 4 | – | 6,5 | 6,2 |
| ma 12.10. | 6 | 95 % | 29 % | 4 | – | 5,2 | 2,7 |
| su 18.10. | 3 | 80 % | 48 % | 4 | – | 3,4 | 1,5 |
| ma 19.10. | 7 | 95 % | 29 % | 4 | – | 3,5 | 2,2 |
| su 25.10. | 4 | 80 % | 48 % | 4 | – | 1,7 | 2,5 |

### Koko kuukausi

| Päivä | Tila | Sija | Suhde mediaaniin | Todennäköisyys |
| --- | --- | ---: | ---: | ---: |
| to 1.10. | ehdokas | 13 | 100 % | 25 % |
| pe 2.10. | ehdokas | 22 | 120 % | 14 % |
| la 3.10. | ehdokas | 27 | 156 % | 5 % |
| su 4.10. | ehdokas | 1 | 80 % | 48 % |
| ma 5.10. | ehdokas | 5 | 95 % | 29 % |
| ti 6.10. | ehdokas | 18 | 111 % | 18 % |
| ke 7.10. | ehdokas | 9 | 99 % | 25 % |
| to 8.10. | ehdokas | 14 | 100 % | 25 % |
| pe 9.10. | ehdokas | 23 | 120 % | 14 % |
| la 10.10. | ehdokas | 28 | 156 % | 5 % |
| su 11.10. | ehdokas | 2 | 80 % | 48 % |
| ma 12.10. | ehdokas | 6 | 95 % | 29 % |
| ti 13.10. | ehdokas | 19 | 111 % | 18 % |
| ke 14.10. | ehdokas | 10 | 99 % | 25 % |
| to 15.10. | ehdokas | 15 | 100 % | 25 % |
| pe 16.10. | ehdokas | 24 | 120 % | 14 % |
| la 17.10. | ehdokas | 29 | 156 % | 5 % |
| su 18.10. | ehdokas | 3 | 80 % | 48 % |
| ma 19.10. | ehdokas | 7 | 95 % | 29 % |
| ti 20.10. | ehdokas | 20 | 111 % | 18 % |
| ke 21.10. | ehdokas | 11 | 99 % | 25 % |
| to 22.10. | ehdokas | 16 | 100 % | 25 % |
| pe 23.10. | ehdokas | 25 | 120 % | 14 % |
| la 24.10. | ehdokas | 30 | 156 % | 5 % |
| su 25.10. | ehdokas | 4 | 80 % | 48 % |
| ma 26.10. | ehdokas | 8 | 95 % | 29 % |
| ti 27.10. | ehdokas | 21 | 111 % | 18 % |
| ke 28.10. | ehdokas | 12 | 99 % | 25 % |
| to 29.10. | ehdokas | 17 | 100 % | 25 % |
| pe 30.10. | ehdokas | 26 | 120 % | 14 % |
| la 31.10. | ehdokas | 31 | 156 % | 5 % |

### Lähtötiedot

- Suljetut arkipäivät: ei yhtään
- Pyhäpäiväkerroin: 0,75 (8 havaintoa)
- Jäännösjakauma: mitattu, 348 havaintoa

### Varaukset

- Kynnys osuu tasapisteryhmän sisään: 4 päivää saa saman pistearvon ja niistä 3 mahtui hiljaisimpiin. Malli ei erottele näitä päiviä toisistaan, joten valinta niiden kesken on päivämääräjärjestyksessä ja voidaan tehdä muilla perusteilla.
- Kuukauden hiljaisin viidennes on vain 14 % mediaanipäivää hiljaisempi, joten kuukausi on tasainen eikä suositus erottele päiviä merkittävästi.
- Viimeinen havainto on 2026-09-03, 28 päivää ennen kuukauden alkua. Arkipäivämediaanit kuvaavat eri jaksoa kuin ennustettava kuukausi.
- Ylläpidetty kalenteri ei kata päivää 2026-10-01 eteenpäin (31 päivää), joten niiltä oletetaan ettei pyhäpäiviä ole.
- Säätiedot ovat klimatologiaa 31 päivälle; ne ovat taustatietoa eivätkä vaikuta pisteytykseen.

## 3. Kaupungintalo (2)

Origo 2026-09-03, sääntö `quiet_calendar`. Ehdokaspäiviä 27, hiljaisia päiviä 6. Kynnysarvo on 190,8 kävijätapahtumaa, eli 97 % mediaanipäivästä.

### Hiljaisimmat päivät

| Päivä | Sija | Suhde mediaaniin | Todennäköisyys | Samanarvoisia | Pyhä | Lämpötila | Sade |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| to 1.10. | 5 | 97 % | 22 % | 5 | – | 7,9 | 0,9 |
| su 4.10. | 1 | 77 % | 37 % | 4 | – | 6,0 | 1,5 |
| to 8.10. | 6 | 97 % | 22 % | 5 | – | 5,3 | 4,1 |
| su 11.10. | 2 | 77 % | 37 % | 4 | – | 6,5 | 6,2 |
| su 18.10. | 3 | 77 % | 37 % | 4 | – | 3,4 | 1,5 |
| su 25.10. | 4 | 77 % | 37 % | 4 | – | 1,7 | 2,5 |

### Koko kuukausi

| Päivä | Tila | Sija | Suhde mediaaniin | Todennäköisyys |
| --- | --- | ---: | ---: | ---: |
| to 1.10. | ehdokas | 5 | 97 % | 22 % |
| pe 2.10. | ehdokas | 10 | 100 % | 20 % |
| la 3.10. | ehdokas | 15 | 100 % | 20 % |
| su 4.10. | ehdokas | 1 | 77 % | 37 % |
| ma 5.10. | suljettu arkipäivä | – | 12 % | – |
| ti 6.10. | ehdokas | 24 | 116 % | 14 % |
| ke 7.10. | ehdokas | 20 | 101 % | 20 % |
| to 8.10. | ehdokas | 6 | 97 % | 22 % |
| pe 9.10. | ehdokas | 11 | 100 % | 20 % |
| la 10.10. | ehdokas | 16 | 100 % | 20 % |
| su 11.10. | ehdokas | 2 | 77 % | 37 % |
| ma 12.10. | suljettu arkipäivä | – | 12 % | – |
| ti 13.10. | ehdokas | 25 | 116 % | 14 % |
| ke 14.10. | ehdokas | 21 | 101 % | 20 % |
| to 15.10. | ehdokas | 7 | 97 % | 22 % |
| pe 16.10. | ehdokas | 12 | 100 % | 20 % |
| la 17.10. | ehdokas | 17 | 100 % | 20 % |
| su 18.10. | ehdokas | 3 | 77 % | 37 % |
| ma 19.10. | suljettu arkipäivä | – | 12 % | – |
| ti 20.10. | ehdokas | 26 | 116 % | 14 % |
| ke 21.10. | ehdokas | 22 | 101 % | 20 % |
| to 22.10. | ehdokas | 8 | 97 % | 22 % |
| pe 23.10. | ehdokas | 13 | 100 % | 20 % |
| la 24.10. | ehdokas | 18 | 100 % | 20 % |
| su 25.10. | ehdokas | 4 | 77 % | 37 % |
| ma 26.10. | suljettu arkipäivä | – | 12 % | – |
| ti 27.10. | ehdokas | 27 | 116 % | 14 % |
| ke 28.10. | ehdokas | 23 | 101 % | 20 % |
| to 29.10. | ehdokas | 9 | 97 % | 22 % |
| pe 30.10. | ehdokas | 14 | 100 % | 20 % |
| la 31.10. | ehdokas | 19 | 100 % | 20 % |

### Lähtötiedot

- Suljetut arkipäivät: ma
- Pyhäpäiväkerroin: 0,49 (8 havaintoa)
- Jäännösjakauma: mitattu, 348 havaintoa

### Varaukset

- Kynnys osuu tasapisteryhmän sisään: 5 päivää saa saman pistearvon ja niistä 2 mahtui hiljaisimpiin. Malli ei erottele näitä päiviä toisistaan, joten valinta niiden kesken on päivämääräjärjestyksessä ja voidaan tehdä muilla perusteilla.
- Viimeinen havainto on 2026-09-03, 28 päivää ennen kuukauden alkua. Arkipäivämediaanit kuvaavat eri jaksoa kuin ennustettava kuukausi.
- Ylläpidetty kalenteri ei kata päivää 2026-10-01 eteenpäin (31 päivää), joten niiltä oletetaan ettei pyhäpäiviä ole.
- Säätiedot ovat klimatologiaa 31 päivälle; ne ovat taustatietoa eivätkä vaikuta pisteytykseen.
- Suljetut arkipäivät jätetty ehdokkaista pois: maanantai.

## 4. Mitä tämä ei kerro

- **Pisteluku ei ole kävijäennuste.** Se on järjestysluku. Tason ennustamiseen on `python -m ovf_forecast run`, ja sen tarkkuus mitataan erikseen komennolla `evaluate`.
- **Todennäköisyys koskee järjestystä, ei kävijämäärää.** "70 %" tarkoittaa, että päivä päätyi hiljaisimpien joukkoon 70 %:ssa simuloiduista kuukausista.
- **Malli ei tunne tapahtumakalenteria.** Yksittäinen konsertti tai ryhmävaraus kääntää hiljaisen päivän vilkkaaksi, eikä tässä käytetyssä datassa ole tietoa siitä.
- **Sää on taustatietoa.** Se on taulukossa ihmisen päätöksen tueksi, mutta se ei vaikuta järjestykseen: mitattuna se ei parantanut sitä.
- **Suljetut päivät eivät ole hiljaisia päiviä.** Ne on rajattu ehdokkaista pois, koska tapahtumaa ei voi järjestää suljetussa kohteessa.
