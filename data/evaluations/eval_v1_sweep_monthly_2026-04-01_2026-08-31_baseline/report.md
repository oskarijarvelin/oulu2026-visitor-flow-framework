# Ennusteen arviointiraportti, kooste: monthly 2026-04-01 – 2026-08-31

Ajon tunniste: `eval_v1_sweep_monthly_2026-04-01_2026-08-31_baseline`

## 1. Koosteverdikti

Kooste (monthly): 5 ikkunaa, 2026-04-01–2026-08-31, sään tila operational, päävertailukohta best. Venue 1 (Pekuri): malli baseline vastaan best-per-window, 5 ikkunaa (153 päivää). Malli oli parempi 1 ikkunassa ja huonompi 4 ikkunassa. Kooste on mallia vastaan: malli häviää yksinkertaiselle vertailukohdalle, keskiero +62,2 kävijää päivässä (95 % väli +3,1…+126,6). Venue 2 (Kaupungintalo): malli baseline vastaan climatology_dow, 5 ikkunaa (153 päivää). Malli oli parempi 0 ikkunassa ja huonompi 5 ikkunassa. Kooste on mallia vastaan: malli häviää yksinkertaiselle vertailukohdalle, keskiero +16,9 kävijää päivässä (95 % väli +5,0…+31,3). Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen otoksen varassa. Lisää dataa tai tapahtumakalenteri piirteenä voisi muuttaa tuloksen.

## 2. Ikkunat

| # | Testijakso | Origo | Koulutusikkuna | Ajon tunniste |
| --- | --- | --- | --- | --- |
| 1 | 2026-04-01 – 2026-04-30 | 2026-03-31 | all | `eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline` |
| 2 | 2026-05-01 – 2026-05-31 | 2026-04-30 | all | `eval_v1_2026-04-30_2026-05-01_2026-05-31_baseline` |
| 3 | 2026-06-01 – 2026-06-30 | 2026-05-31 | all | `eval_v1_2026-05-31_2026-06-01_2026-06-30_baseline` |
| 4 | 2026-07-01 – 2026-07-31 | 2026-06-30 | all | `eval_v1_2026-06-30_2026-07-01_2026-07-31_baseline` |
| 5 | 2026-08-01 – 2026-08-31 | 2026-07-31 | all | `eval_v1_2026-07-31_2026-08-01_2026-08-31_baseline` |

Sään tila verdiktille: `operational`. Päävertailukohdan valinta: `best`. Monivertailuperheen koko: 10.

## Venue 1 (Pekuri)

### Koosteverdikti

| Malli | Vertailukohta | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti | Puolesta | Vastaan | MDE | MDE / vertailun MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | best-per-window | 5 | 153 | +62,2 | +3,1 … +126,6 | huonompi kuin vertailukohta | 1 | 4 | 99,1 | 69,9 % |

### Ikkunakohtaiset tulokset: baseline

| Testijakso | Vertailukohta | Mallin MAE | Vertailun MAE | Keskiero d | 95 % väli | Verdikti | MDE | MDE % | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | climatology_dow | 102,9 | 96,2 | +6,7 | -3,2 … +30,7 | ei havaittavaa eroa vertailukohtaan | 34,5 | 35,9 % | 0,610 | 1,000 |
| 2026-05-01..2026-05-31 | moving_average_28d | 179,5 | 187,4 | -7,9 | -58,5 … +23,6 | ei havaittavaa eroa vertailukohtaan | 69,0 | 36,8 % | 0,740 | 1,000 |
| 2026-06-01..2026-06-30 | climatology_dow | 305,0 | 138,9 | +166,1 | +62,6 … +264,5 | huonompi kuin vertailukohta | 102,0 | 73,4 % | 0,043 | 0,391 |
| 2026-07-01..2026-07-31 | climatology_dow | 174,3 | 156,2 | +18,1 | -15,5 … +60,9 | ei havaittavaa eroa vertailukohtaan | 43,5 | 27,8 % | 0,472 | 1,000 |
| 2026-08-01..2026-08-31 | climatology_dow | 255,8 | 128,0 | +127,8 | +44,2 … +184,1 | huonompi kuin vertailukohta | 70,8 | 55,3 % | 0,055 | 0,443 |

#### Jakson kokonaismäärät: baseline

| Testijakso | Ennuste | Toteuma | Ero % | 80 % väli | Väli osuu |
| --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | 13 639 | 13 189 | +3,4 % | 13 639 – 20 089 | ei |
| 2026-05-01..2026-05-31 | 11 880 | 14 521 | -18,2 % | 10 683 – 13 840 | ei |
| 2026-06-01..2026-06-30 | 2 961 | 11 865 | -75,0 % | 2 166 – 3 328 | ei |
| 2026-07-01..2026-07-31 | 12 181 | 16 994 | -28,3 % | 10 022 – 14 392 | ei |
| 2026-08-01..2026-08-31 | 20 173 | 13 514 | +49,3 % | 18 620 – 27 237 | ei |

## Venue 2 (Kaupungintalo)

### Koosteverdikti

| Malli | Vertailukohta | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti | Puolesta | Vastaan | MDE | MDE / vertailun MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | climatology_dow | 5 | 153 | +16,9 | +5,0 … +31,3 | huonompi kuin vertailukohta | 0 | 5 | 21,5 | 37,1 % |

### Ikkunakohtaiset tulokset: baseline

| Testijakso | Vertailukohta | Mallin MAE | Vertailun MAE | Keskiero d | 95 % väli | Verdikti | MDE | MDE % | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | climatology_dow | 95,1 | 75,1 | +20,0 | +7,8 … +48,9 | huonompi kuin vertailukohta | 24,7 | 32,9 % | 0,293 | 1,000 |
| 2026-05-01..2026-05-31 | climatology_dow | 75,8 | 71,5 | +4,3 | -4,6 … +31,9 | ei havaittavaa eroa vertailukohtaan | 32,3 | 45,2 % | 0,859 | 1,000 |
| 2026-06-01..2026-06-30 | climatology_dow | 60,7 | 44,5 | +16,2 | -9,0 … +41,3 | ei havaittavaa eroa vertailukohtaan | 36,7 | 82,5 % | 0,259 | 1,000 |
| 2026-07-01..2026-07-31 | climatology_dow | 106,0 | 62,0 | +44,0 | +26,0 … +62,9 | huonompi kuin vertailukohta | 24,1 | 38,9 % | 0,017 | 0,174 |
| 2026-08-01..2026-08-31 | climatology_dow | 37,0 | 36,8 | +0,2 | -10,6 … +8,5 | ei havaittavaa eroa vertailukohtaan | 10,6 | 28,8 % | 0,967 | 1,000 |

#### Jakson kokonaismäärät: baseline

| Testijakso | Ennuste | Toteuma | Ero % | 80 % väli | Väli osuu |
| --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | 6 155 | 3 791 | +62,4 % | 3 666 – 6 155 | kyllä |
| 2026-05-01..2026-05-31 | 3 228 | 5 149 | -37,3 % | 2 926 – 4 685 | ei |
| 2026-06-01..2026-06-30 | 2 900 | 4 254 | -31,8 % | 2 344 – 3 730 | ei |
| 2026-07-01..2026-07-31 | 3 345 | 6 278 | -46,7 % | 2 740 – 4 616 | ei |
| 2026-08-01..2026-08-31 | 4 335 | 4 866 | -10,9 % | 4 166 – 7 382 | kyllä |

## Rajoitteet

- Kooste bootstrapataan **kokonaisina ikkunoina**, koska ikkuna on riippumattomuuden luonnollinen yksikkö: kaksi saman ikkunan päivää jakavat koulutusjoukon, kaksi eri ikkunaa eivät.
- Ikkunakohtainen verdikti on kuvaileva. Koosteverdikti on se, joka kantaa näyttöä.
- Raakoja p-arvoja on korjattu Holm-Bonferronilla; perheen koko on kerrottu yllä.
- Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen otoksen varassa.
