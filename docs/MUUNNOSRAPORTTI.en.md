# Ticket data conversion report

*English translation. Finnish original: [`MUUNNOSRAPORTTI.md`](MUUNNOSRAPORTTI.md).*

Run 2026-08-24. The source files are the opening team's visitor statistics CSVs, kept in
the repository under `tools/fixtures/`.

The conversion follows exactly the rules written down in prompt 4
(`docs/CLAUDE_CODE_PROMPTS.md`). This run doubles as the reference the finished browser
tool is checked against: the tool has to produce identical files.

## Result

| | Pekuri (venue 1) | Kaupungintalo (venue 2) |
| --- | --- | --- |
| Days | 222 | 222 |
| Date range | 2026-01-14 - 2026-08-23 | 2026-01-13 - 2026-08-23 |
| Single tickets | 13,957 | 11,775 |
| Group tickets | 3,631 | 5,281 |
| Total | 17,588 | 17,056 |
| Zero days | 1 | 33 |
| Gaps in the series | none | 2026-07-25 missing |

## Change against the current files

| | Pekuri | Kaupungintalo |
| --- | --- | --- |
| Days added | 98 (05-18 - 08-23) | 97 (05-18 - 08-23) |
| Days changed | 0 | 75 |
| Days removed | 0 | 0 |

**Pekuri matches perfectly.** All 124 earlier days survived unchanged and 98 new days were
added on top. This is the strongest possible evidence that the column mapping is correct.

**The 75 changed days at Kaupungintalo are not a conversion error.** The group figures
stayed unchanged on all 125 earlier days. The changes touch single tickets only, they go
in both directions (45 days up, 30 down, range -56 to +68) and the total over the whole
period moves by just 6 visitors downwards. The opening team has therefore corrected the
numbers in the Excel file after the current file was made. The new figures are the right
ones.

I confirmed this separately by exhaustively trying every possible column combination. No
other mapping produces a better match against the current file, so this is not a case of
picking the wrong columns.

## Mapping used

**Pekuri:** `TICKETS = Yleisöä`, `GROUPS = Ryhmät`

**Kaupungintalo:**
`TICKETS = Varaus + Verkkokauppa tilastot + Ovelta + Ktalon puh tilasto`
`GROUPS = Ryhmät + KUTOSET + Ktalon vieraat`

For both, `TOTAL = TICKETS + GROUPS`. The source's own `Yhteensä` (total) column was used
for cross-checking only, because it is unreliable. The result contains no row where TOTAL
is not the sum of its components.

## Needs attention

### 1. Kaupungintalo 2026-07-25 is missing

Row 203 of the source carries the date 2026-06-25, but the row sits between 2026-07-24 and
2026-07-26 and its `Varaus` column reads "suljettu" (closed). This is almost certainly a
typo that should read 2026-07-25.

I did not fix this automatically. The row was processed as it stands, so its zeros were
summed into the real 2026-06-25 day without changing it. As a result 2026-07-25 is missing
from the output entirely.

The impact is small: ingest fills missing days inside the observation period with zero,
which matches a "closed" marking. If you want the row included explicitly, correct the
date in the source file to 2026-07-25 and run the conversion again.

### 2. Cross-check discrepancies

These did not affect the result, because TOTAL is computed from the components, but they
are worth fixing at the source so that the Excel file's own sums hold:

| Venue | Row | Day | Components | Source total |
| --- | --- | --- | --- | --- |
| Pekuri | 79 | 2026-03-30 | 37 | 58 |
| Pekuri | 80 | 2026-03-31 | 58 | 37 |
| Pekuri | 142 | 2026-05-30 | 35 | 2,251 |
| Kaupungintalo | 163 | 2026-06-15 | 0 | 475 |
| Kaupungintalo | 213 | 2026-08-04 | 113 | 101 |

On rows 79 and 80 the total values look like they have swapped places. The value 2,251 on
row 142 is a monthly total that has leaked onto a daily row. The value 475 on row 163 is a
weekly total in the wrong column.

### 3. Text values in numeric columns

Interpreted as zeros:

| Row | Day | Column | Value |
| --- | --- | --- | --- |
| 36 | 2026-02-13 | Varaus | "Suljettu" |
| 108 | 2026-04-23 | Varaus | "suljettu" |
| 203 | (2026-06-25) | Varaus | "suljettu" |
| 218 | 2026-08-09 | Verkkokauppa tilastot | "ei löytynyt?" |

The "ei löytynyt?" (not found?) on row 218 is a different thing from a zero: the web shop
figure is unknown, not zero. That day recorded 42 visitors through the other channels, so
the true figure is higher than that. Worth clarifying with the opening team.

### 4. A future advance booking was left out

Kaupungintalo row 245: 2026-09-05, a group of 200. This is an advance booking rather than
a realised visitor count, so it does not belong in historical data. Every day after the
run date was cut off.

## Skipped rows

These follow from the structure of the source and are not errors:

- Pekuri: 5 empty subtotal rows (rows 20, 49, 81, 112, 232)
- Kaupungintalo: the month headings "Helmikuu" (February, row 23) and "Maaliskuu" (March,
  row 53), the subtotal row "Yhteensä" (total, row 21) and 4 empty rows

## Vocabulary

The source files are called Kävijätilastot (visitor statistics) and their columns are
channels, not ticket products. In this dataset the framework's `tickets_sold` and
`groups_sold` fields mean, in practice, individual visitors and group visitors. The
figures should therefore not be read as a sales report.
