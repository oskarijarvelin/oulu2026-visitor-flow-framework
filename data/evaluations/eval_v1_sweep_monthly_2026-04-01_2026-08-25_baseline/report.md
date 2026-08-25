# Ennusteen arviointiraportti, kooste: monthly 2026-04-01 – 2026-08-25

Ajon tunniste: `eval_v1_sweep_monthly_2026-04-01_2026-08-25_baseline`

## 1. Koosteverdikti

Kooste (monthly): 5 ikkunaa, 2026-04-01–2026-08-25, sään tila operational, päävertailukohta best. Venue 1 (Pekuri): malli baseline vastaan best-per-window, 5 ikkunaa (147 päivää). Malli oli parempi 1 ikkunassa ja huonompi 4 ikkunassa. Kooste on mallia vastaan: malli häviää yksinkertaiselle vertailukohdalle, keskiero +60,0 kävijää päivässä (95 % väli +3,1…+124,4). Venue 2 (Kaupungintalo): malli baseline vastaan climatology_dow, 5 ikkunaa (147 päivää). Malli oli parempi 1 ikkunassa ja huonompi 4 ikkunassa. Kooste on mallia vastaan: malli häviää yksinkertaiselle vertailukohdalle, keskiero +17,1 kävijää päivässä (95 % väli +3,7…+32,7). Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen otoksen varassa. Lisää dataa tai tapahtumakalenteri piirteenä voisi muuttaa tuloksen.

## 2. Ikkunat

| # | Testijakso | Origo | Koulutusikkuna | Ajon tunniste |
| --- | --- | --- | --- | --- |
| 1 | 2026-04-01 – 2026-04-30 | 2026-03-31 | all | `eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline` |
| 2 | 2026-05-01 – 2026-05-31 | 2026-04-30 | all | `eval_v1_2026-04-30_2026-05-01_2026-05-31_baseline` |
| 3 | 2026-06-01 – 2026-06-30 | 2026-05-31 | all | `eval_v1_2026-05-31_2026-06-01_2026-06-30_baseline` |
| 4 | 2026-07-01 – 2026-07-31 | 2026-06-30 | all | `eval_v1_2026-06-30_2026-07-01_2026-07-31_baseline` |
| 5 | 2026-08-01 – 2026-08-25 | 2026-07-31 | all | `eval_v1_2026-07-31_2026-08-01_2026-08-25_baseline` |

Sään tila verdiktille: `operational`. Päävertailukohdan valinta: `best`. Monivertailuperheen koko: 10.

## Venue 1 (Pekuri)

### Koosteverdikti

| Malli | Vertailukohta | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti | Puolesta | Vastaan | MDE | MDE / vertailun MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | best-per-window | 5 | 147 | +60,0 | +3,1 … +124,4 | huonompi kuin vertailukohta | 1 | 4 | 96,5 | 67,6 % |

### Ikkunakohtaiset tulokset: baseline

| Testijakso | Vertailukohta | Mallin MAE | Vertailun MAE | Keskiero d | 95 % väli | Verdikti | MDE | MDE % | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | climatology_dow | 102,9 | 96,2 | +6,7 | -3,2 … +30,7 | ei havaittavaa eroa vertailukohtaan | 34,5 | 35,9 % | 0,610 | 1,000 |
| 2026-05-01..2026-05-31 | moving_average_28d | 179,5 | 187,4 | -7,9 | -58,5 … +23,6 | ei havaittavaa eroa vertailukohtaan | 69,0 | 36,8 % | 0,740 | 1,000 |
| 2026-06-01..2026-06-30 | climatology_dow | 305,0 | 138,9 | +166,1 | +62,6 … +264,5 | huonompi kuin vertailukohta | 102,0 | 73,4 % | 0,043 | 0,391 |
| 2026-07-01..2026-07-31 | climatology_dow | 174,3 | 156,2 | +18,1 | -15,5 … +60,9 | ei havaittavaa eroa vertailukohtaan | 43,5 | 27,8 % | 0,472 | 1,000 |
| 2026-08-01..2026-08-25 | climatology_dow | 248,2 | 131,0 | +117,2 | +18,0 … +167,7 | huonompi kuin vertailukohta | 84,5 | 64,5 % | 0,077 | 0,614 |

#### Jakson kokonaismäärät: baseline

| Testijakso | Ennuste | Toteuma | Ero % | 80 % väli | Väli osuu |
| --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | 13 639 | 13 189 | +3,4 % | 13 639 – 20 089 | ei |
| 2026-05-01..2026-05-31 | 11 880 | 14 521 | -18,2 % | 10 683 – 13 840 | ei |
| 2026-06-01..2026-06-30 | 2 961 | 11 865 | -75,0 % | 2 166 – 3 328 | ei |
| 2026-07-01..2026-07-31 | 12 181 | 16 994 | -28,3 % | 10 022 – 14 392 | ei |
| 2026-08-01..2026-08-25 | 16 410 | 11 477 | +43,0 % | 15 961 – 23 474 | ei |

## Venue 2 (Kaupungintalo)

### Koosteverdikti

| Malli | Vertailukohta | Ikkunoita | Päiviä | Keskiero d | 95 % väli | Verdikti | Puolesta | Vastaan | MDE | MDE / vertailun MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | climatology_dow | 5 | 147 | +17,1 | +3,7 … +32,7 | huonompi kuin vertailukohta | 1 | 4 | 23,2 | 39,9 % |

### Ikkunakohtaiset tulokset: baseline

| Testijakso | Vertailukohta | Mallin MAE | Vertailun MAE | Keskiero d | 95 % väli | Verdikti | MDE | MDE % | DM p (raaka) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | climatology_dow | 95,5 | 75,1 | +20,4 | +11,5 … +47,7 | huonompi kuin vertailukohta | 24,4 | 32,5 % | 0,276 | 1,000 |
| 2026-05-01..2026-05-31 | climatology_dow | 76,4 | 71,5 | +5,0 | -5,4 … +33,6 | ei havaittavaa eroa vertailukohtaan | 31,9 | 44,6 % | 0,839 | 1,000 |
| 2026-06-01..2026-06-30 | climatology_dow | 61,0 | 44,5 | +16,5 | -8,4 … +42,1 | ei havaittavaa eroa vertailukohtaan | 36,5 | 81,8 % | 0,250 | 1,000 |
| 2026-07-01..2026-07-31 | climatology_dow | 108,0 | 62,0 | +46,0 | +27,1 … +66,1 | huonompi kuin vertailukohta | 25,3 | 40,8 % | 0,018 | 0,184 |
| 2026-08-01..2026-08-25 | climatology_dow | 30,1 | 32,3 | -2,3 | -9,6 … +9,8 | ei havaittavaa eroa vertailukohtaan | 10,8 | 33,4 % | 0,765 | 1,000 |

#### Jakson kokonaismäärät: baseline

| Testijakso | Ennuste | Toteuma | Ero % | 80 % väli | Väli osuu |
| --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | 6 232 | 3 791 | +64,4 % | 3 662 – 6 232 | kyllä |
| 2026-05-01..2026-05-31 | 3 242 | 5 149 | -37,0 % | 2 885 – 4 617 | ei |
| 2026-06-01..2026-06-30 | 2 902 | 4 254 | -31,8 % | 2 307 – 3 709 | ei |
| 2026-07-01..2026-07-31 | 3 262 | 6 278 | -48,0 % | 2 623 – 4 447 | ei |
| 2026-08-01..2026-08-25 | 3 636 | 3 995 | -9,0 % | 3 636 – 11 166 | kyllä |

## Rajoitteet

- Kooste bootstrapataan **kokonaisina ikkunoina**, koska ikkuna on riippumattomuuden luonnollinen yksikkö: kaksi saman ikkunan päivää jakavat koulutusjoukon, kaksi eri ikkunaa eivät.
- Ikkunakohtainen verdikti on kuvaileva. Koosteverdikti on se, joka kantaa näyttöä.
- Raakoja p-arvoja on korjattu Holm-Bonferronilla; perheen koko on kerrottu yllä.
- Aineistoa on noin kahdeksan kuukautta yhdeltä vuodelta, joten myös kooste lepää ohuen otoksen varassa.
