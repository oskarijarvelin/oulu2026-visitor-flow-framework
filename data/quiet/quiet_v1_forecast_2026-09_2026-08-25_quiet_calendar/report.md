# Kuukauden hiljaisimmat päivät: syyskuu 2026

Ajon tunniste: `quiet_v1_forecast_2026-09_2026-08-25_quiet_calendar`

## 1. Vastaus

Pekuri (1), syyskuu 2026: hiljaisimmat päivät ovat su 6.9., ma 7.9., su 13.9., ma 14.9., su 20.9., su 27.9.. Kynnys on kuukauden hiljaisin viidennes, 6 päivää 30 ehdokkaasta, ja malli erottaa ne 18 % mediaanipäivän alapuolelle. Varmin valinta on su 6.9., jonka todennäköisyys kuulua hiljaisimpiin on 47 %. Mitattu luotettavuus (5 ikkunaa, ajo `quiet_v1_backtest_2026-04-01_2026-08-25_quiet_calendar-climatology_dow-seasonal_naive-moving_average_28d-baseline`): valitut päivät olivat keskimäärin 7 % (95 % väli -1 % … 17 %) mediaanipäivää hiljaisempia, eli hyötyä ei ole todennettu.

Kaupungintalo (2), syyskuu 2026: hiljaisimmat päivät ovat to 3.9., su 6.9., to 10.9., su 13.9., su 20.9., su 27.9.. Kynnys on kuukauden hiljaisin viidennes, 6 päivää 26 ehdokkaasta, ja malli erottaa ne 16 % mediaanipäivän alapuolelle. Varmin valinta on su 6.9., jonka todennäköisyys kuulua hiljaisimpiin on 44 %. Mitattu luotettavuus (5 ikkunaa, ajo `quiet_v1_backtest_2026-04-01_2026-08-25_quiet_calendar-climatology_dow-seasonal_naive-moving_average_28d-baseline`): valitut päivät olivat keskimäärin 45 % (95 % väli 25 % … 65 %) mediaanipäivää hiljaisempia, eli hyöty on todennettu.

## 2. Miten luku on muodostettu

- Pisteytyssääntö: `quiet_calendar`
- Kynnys: kuukauden hiljaisin 20 % ehdokaspäivistä, vähintään 3 ja enintään 10 päivää
- Simulaatioita todennäköisyyttä kohden: 10 000
- Siemenluku: 20 260 101

Pisteluku on kävijämäärän suuruusluokassa, mutta se on järjestysluku eikä ennuste: kaikki alla olevat suhdeluvut on jaettu kuukauden mediaanipäivällä, jolloin tason virhe kumoutuu eikä vaikuta järjestykseen.

Mallin erottelu ja toteutuva ero ovat kaksi eri lukua, eikä toinen ennusta toista. Pisteluku on ehdollinen keskiarvo, joten se on aina toteumaa tasaisempi: alla oleva suhdeluku kertoo, kuinka kauas malli päivät erottaa, ei kuinka hiljaisia ne toteutuvat olemaan. Toteutuvan eron arvio saadaan vain mittaamalla, ja se on komennon `quiet backtest` tulos.

## 3. Pekuri (1)

Origo 2026-08-25, sääntö `quiet_calendar`. Ehdokaspäiviä 30, hiljaisia päiviä 6. Kynnysarvo on 435,6 kävijätapahtumaa, eli 92 % mediaanipäivästä.

### Hiljaisimmat päivät

| Päivä | Sija | Suhde mediaaniin | Todennäköisyys | Samanarvoisia | Pyhä | Lämpötila | Sade |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| su 6.9. | 1 | 77 % | 47 % | 4 | – | 13,2 | 4,6 |
| ma 7.9. | 5 | 92 % | 27 % | 4 | – | 11,9 | 8,6 |
| su 13.9. | 2 | 77 % | 47 % | 4 | – | 11,7 | 5,1 |
| ma 14.9. | 6 | 92 % | 27 % | 4 | – | 10,5 | 2,8 |
| su 20.9. | 3 | 77 % | 47 % | 4 | – | 8,9 | 2,4 |
| su 27.9. | 4 | 77 % | 47 % | 4 | – | 9,3 | 2,9 |

### Koko kuukausi

| Päivä | Tila | Sija | Suhde mediaaniin | Todennäköisyys |
| --- | --- | ---: | ---: | ---: |
| ti 1.9. | ehdokas | 18 | 107 % | 14 % |
| ke 2.9. | ehdokas | 9 | 98 % | 21 % |
| to 3.9. | ehdokas | 14 | 100 % | 19 % |
| pe 4.9. | ehdokas | 23 | 117 % | 11 % |
| la 5.9. | ehdokas | 27 | 152 % | 3 % |
| su 6.9. | ehdokas | 1 | 77 % | 47 % |
| ma 7.9. | ehdokas | 5 | 92 % | 27 % |
| ti 8.9. | ehdokas | 19 | 107 % | 14 % |
| ke 9.9. | ehdokas | 10 | 98 % | 21 % |
| to 10.9. | ehdokas | 15 | 100 % | 19 % |
| pe 11.9. | ehdokas | 24 | 117 % | 11 % |
| la 12.9. | ehdokas | 28 | 152 % | 3 % |
| su 13.9. | ehdokas | 2 | 77 % | 47 % |
| ma 14.9. | ehdokas | 6 | 92 % | 27 % |
| ti 15.9. | ehdokas | 20 | 107 % | 14 % |
| ke 16.9. | ehdokas | 11 | 98 % | 21 % |
| to 17.9. | ehdokas | 16 | 100 % | 19 % |
| pe 18.9. | ehdokas | 25 | 117 % | 11 % |
| la 19.9. | ehdokas | 29 | 152 % | 3 % |
| su 20.9. | ehdokas | 3 | 77 % | 47 % |
| ma 21.9. | ehdokas | 7 | 92 % | 27 % |
| ti 22.9. | ehdokas | 21 | 107 % | 14 % |
| ke 23.9. | ehdokas | 12 | 98 % | 21 % |
| to 24.9. | ehdokas | 17 | 100 % | 19 % |
| pe 25.9. | ehdokas | 26 | 117 % | 11 % |
| la 26.9. | ehdokas | 30 | 152 % | 3 % |
| su 27.9. | ehdokas | 4 | 77 % | 47 % |
| ma 28.9. | ehdokas | 8 | 92 % | 27 % |
| ti 29.9. | ehdokas | 22 | 107 % | 14 % |
| ke 30.9. | ehdokas | 13 | 98 % | 21 % |

### Lähtötiedot

- Suljetut arkipäivät: ei yhtään
- Pyhäpäiväkerroin: 0,74 (8 havaintoa)
- Jäännösjakauma: mitattu, 216 havaintoa

### Varaukset

- Kynnys osuu tasapisteryhmän sisään: 4 päivää saa saman pistearvon ja niistä 2 mahtui hiljaisimpiin. Malli ei erottele näitä päiviä toisistaan, joten valinta niiden kesken on päivämääräjärjestyksessä ja voidaan tehdä muilla perusteilla.
- Ylläpidetty kalenteri ei kata päivää 2026-09-10 eteenpäin (21 päivää), joten niiltä oletetaan ettei pyhäpäiviä ole.
- Säätiedot ovat klimatologiaa 21 päivälle; ne ovat taustatietoa eivätkä vaikuta pisteytykseen.

## 3. Kaupungintalo (2)

Origo 2026-08-25, sääntö `quiet_calendar`. Ehdokaspäiviä 26, hiljaisia päiviä 6. Kynnysarvo on 192,7 kävijätapahtumaa, eli 98 % mediaanipäivästä.

### Hiljaisimmat päivät

| Päivä | Sija | Suhde mediaaniin | Todennäköisyys | Samanarvoisia | Pyhä | Lämpötila | Sade |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| to 3.9. | 5 | 98 % | 23 % | 4 | – | 14,6 | 2,8 |
| su 6.9. | 1 | 77 % | 44 % | 4 | – | 13,2 | 4,6 |
| to 10.9. | 6 | 98 % | 23 % | 4 | – | 15,3 | 2,0 |
| su 13.9. | 2 | 77 % | 44 % | 4 | – | 13,8 | 4,4 |
| su 20.9. | 3 | 77 % | 44 % | 4 | – | 11,6 | 1,0 |
| su 27.9. | 4 | 77 % | 44 % | 4 | – | 11,6 | 2,0 |

### Koko kuukausi

| Päivä | Tila | Sija | Suhde mediaaniin | Todennäköisyys |
| --- | --- | ---: | ---: | ---: |
| ti 1.9. | ehdokas | 22 | 116 % | 14 % |
| ke 2.9. | ehdokas | 17 | 104 % | 19 % |
| to 3.9. | ehdokas | 5 | 98 % | 23 % |
| pe 4.9. | ehdokas | 9 | 100 % | 21 % |
| la 5.9. | ehdokas | 13 | 100 % | 22 % |
| su 6.9. | ehdokas | 1 | 77 % | 44 % |
| ma 7.9. | suljettu arkipäivä | – | 12 % | – |
| ti 8.9. | ehdokas | 23 | 116 % | 14 % |
| ke 9.9. | ehdokas | 18 | 104 % | 19 % |
| to 10.9. | ehdokas | 6 | 98 % | 23 % |
| pe 11.9. | ehdokas | 10 | 100 % | 21 % |
| la 12.9. | ehdokas | 14 | 100 % | 22 % |
| su 13.9. | ehdokas | 2 | 77 % | 44 % |
| ma 14.9. | suljettu arkipäivä | – | 12 % | – |
| ti 15.9. | ehdokas | 24 | 116 % | 14 % |
| ke 16.9. | ehdokas | 19 | 104 % | 19 % |
| to 17.9. | ehdokas | 7 | 98 % | 23 % |
| pe 18.9. | ehdokas | 11 | 100 % | 21 % |
| la 19.9. | ehdokas | 15 | 100 % | 22 % |
| su 20.9. | ehdokas | 3 | 77 % | 44 % |
| ma 21.9. | suljettu arkipäivä | – | 12 % | – |
| ti 22.9. | ehdokas | 25 | 116 % | 14 % |
| ke 23.9. | ehdokas | 20 | 104 % | 19 % |
| to 24.9. | ehdokas | 8 | 98 % | 23 % |
| pe 25.9. | ehdokas | 12 | 100 % | 21 % |
| la 26.9. | ehdokas | 16 | 100 % | 22 % |
| su 27.9. | ehdokas | 4 | 77 % | 44 % |
| ma 28.9. | suljettu arkipäivä | – | 12 % | – |
| ti 29.9. | ehdokas | 26 | 116 % | 14 % |
| ke 30.9. | ehdokas | 21 | 104 % | 19 % |

### Lähtötiedot

- Suljetut arkipäivät: ma
- Pyhäpäiväkerroin: 0,49 (8 havaintoa)
- Jäännösjakauma: mitattu, 216 havaintoa

### Varaukset

- Kynnys osuu tasapisteryhmän sisään: 4 päivää saa saman pistearvon ja niistä 2 mahtui hiljaisimpiin. Malli ei erottele näitä päiviä toisistaan, joten valinta niiden kesken on päivämääräjärjestyksessä ja voidaan tehdä muilla perusteilla.
- Ylläpidetty kalenteri ei kata päivää 2026-09-10 eteenpäin (21 päivää), joten niiltä oletetaan ettei pyhäpäiviä ole.
- Säätiedot ovat klimatologiaa 21 päivälle; ne ovat taustatietoa eivätkä vaikuta pisteytykseen.
- Suljetut arkipäivät jätetty ehdokkaista pois: maanantai.

## 4. Mitä tämä ei kerro

- **Pisteluku ei ole kävijäennuste.** Se on järjestysluku. Tason ennustamiseen on `python -m ovf_forecast run`, ja sen tarkkuus mitataan erikseen komennolla `evaluate`.
- **Todennäköisyys koskee järjestystä, ei kävijämäärää.** "70 %" tarkoittaa, että päivä päätyi hiljaisimpien joukkoon 70 %:ssa simuloiduista kuukausista.
- **Malli ei tunne tapahtumakalenteria.** Yksittäinen konsertti tai ryhmävaraus kääntää hiljaisen päivän vilkkaaksi, eikä tässä käytetyssä datassa ole tietoa siitä.
- **Sää on taustatietoa.** Se on taulukossa ihmisen päätöksen tueksi, mutta se ei vaikuta järjestykseen: mitattuna se ei parantanut sitä.
- **Suljetut päivät eivät ole hiljaisia päiviä.** Ne on rajattu ehdokkaista pois, koska tapahtumaa ei voi järjestää suljetussa kohteessa.
