# tools

*English translation. Finnish original: [`README.md`](README.md).*

Helpers that belong to neither the ingest nor the web part. These are run by hand.

- [`tickets-parser.html`](#visitor-statistics-converter) converts the opening team's
  visitor statistics CSV into a per-venue tickets file.
- [`MUUNNOSRAPORTTI.en.md`](MUUNNOSRAPORTTI.en.md) is the report of the conversion run by
  hand. It is the de facto specification of this tool and the reference for the
  regression test.
- `fixtures/` holds the genuine source files and the expected output.

---

## Visitor statistics converter

### The problem this answers

The opening team maintains visitor counts in Excel and exports them as CSV. The framework,
meanwhile, reads a per-venue file `data/raw/tickets/venue_{id}/tickets-venue-{id}.csv` in
the form `DATE,TICKETS,GROUPS,TOTAL`. Between the two sits the same manual work every
week: a different column structure per venue, sums across several columns, month headings
and subtotal rows in the middle of the data, text in numeric columns and an unreliable
total column.

The tool performs that conversion in the browser, shows what it is about to do and reports
what is wrong in the source data. Weekly use takes about five minutes.

### What the figures mean

The source files are called **Kävijätilastot** (visitor statistics) and their columns are
channels: booking, web shop, at the door, phone, groups and house guests. So these are not
pure ticket sales but visitor counts by channel.

In this dataset the framework's `tickets_sold` and `groups_sold` fields mean, in practice,
**individual visitors** and **group visitors**. These figures should not be read as a sales
report or as revenue in euros.

### Use

Open `tools/tickets-parser.html` in a browser straight from the file system. No server, no
install, no network connection.

```bash
open tools/tickets-parser.html
```

One file containing all the HTML, CSS and JavaScript. No external requests, no CDN, no
libraries. All processing happens in the browser, nothing is sent anywhere. Works on
current versions of Chrome, Safari and Firefox.

**Step 1, choosing the file.** Drop a CSV, pick one with the file chooser or paste from the
clipboard. The tool detects the character encoding, the delimiter and the profile. Several
files can be processed one after another; results accumulate per venue.

**Step 2, preview.** A table of the source rows, the column names and indices. The row
count and the problems detected.

**Step 3, mapping.** Prefilled from the detected profile, everything editable: the date
column and its format, the TICKETS and GROUPS columns as multi-select, an optional
cross-check column, the venue and the cutoff date. A mapping can be saved as a named
profile in the browser's localStorage.

**Step 4, result and checks.** A summary, the warnings each on their own row and a bar
chart. Every warning names the row number in the source file, and clicking it jumps
straight to that row in the preview.

**Step 5, merging.** Load the current tickets file from the repository and the tool shows
the difference: days added, days changed with their old and new values, and days removed.

**Step 6, export.** Download the per-venue file and, for checking, the combined
`tickets_daily.csv`. Both also to the clipboard.

You can move freely between the steps from the progress indicator; work is not lost.

### Column mapping

Columns are identified **primarily by index**, and the heading name is the confirmation.
When comparing headings, leading and trailing spaces are stripped and case is ignored,
because the source contains for instance `Ryhmät ` with a trailing space.

#### Profile A: Pekuri, venue 1

Heading row: `;Päivämäärä;Yleisöä;Ryhmät;Yhteensä;...`

| Column | Heading | Use |
| --- | --- | --- |
| 0 | (unnamed) | weekday, a label column |
| 1 | `Päivämäärä` | date, format `d.m.yyyy` |
| 2 | `Yleisöä` | **TICKETS** |
| 3 | `Ryhmät` | **GROUPS** |
| 4 | `Yhteensä` | cross-check only |
| 5 onwards | (unnamed) | notes and stray weekly totals, skipped |

Detected from the heading `Yleisöä`.

#### Profile B: Kaupungintalo, venue 2

Heading row:
`;Päivämäärä;Varaus;Verkkokauppa tilastot;Ovelta;Ktalon puh tilasto;Ryhmät ;KUTOSET;Ktalon vieraat;Yhteensä;Lisätietoa;...`

| Column | Heading | Use |
| --- | --- | --- |
| 0 | (unnamed) | weekday, a label column |
| 1 | `Päivämäärä` | date, format `d.m.yyyy` |
| 2 | `Varaus` | **TICKETS**, summed |
| 3 | `Verkkokauppa tilastot` | **TICKETS**, summed |
| 4 | `Ovelta` | **TICKETS**, summed |
| 5 | `Ktalon puh tilasto` | **TICKETS**, summed |
| 6 | `Ryhmät ` (trailing space) | **GROUPS**, summed |
| 7 | `KUTOSET` | **GROUPS**, summed |
| 8 | `Ktalon vieraat` | **GROUPS**, summed |
| 9 | `Yhteensä` | cross-check only |
| 10 | `Lisätietoa` | notes, skipped |
| 11 onwards | (unnamed) | junk: `#ARVO!`, running totals, serial numbers, skipped |

Detected from the headings `Verkkokauppa tilastot` or `KUTOSET`.

For both, `TOTAL = TICKETS + GROUPS`.

### Why the source's total column is not written to the output

It is unreliable. At Pekuri it is empty on 18 rows and at Kaupungintalo on 55 rows, and
monthly and weekly totals have leaked into it on daily rows. `TOTAL` is therefore **always**
computed from the components, and the source total column is used only for a cross-check
that raises a warning when it differs from the computed value.

### Known problems in the source data

All of these were found in genuine data. The tool handles them and reports them.

**Rows to skip.** Month headings (`Helmikuu`, `Maaliskuu`), subtotal rows (`Yhteensä`),
empty rows and rows whose date column is empty.

**Empty day rows at the end.** The end of the files carries pre-calendared days without a
single entry, at Kaupungintalo all the way to 2026-09-18. These are skipped. Note the
difference: an empty day row in the middle of the file is a **genuine zero day** and is
written to the output as a zero, because a zero is a genuine observation.

**Text values in numeric columns.** Interpreted as zero and flagged as a warning; the
original text is shown.

| Venue | Row | Day | Column | Value |
| --- | --- | --- | --- | --- |
| 2 | 36 | 2026-02-13 | `Varaus` | `Suljettu` |
| 2 | 108 | 2026-04-23 | `Varaus` | `suljettu` |
| 2 | 203 | (2026-06-25) | `Varaus` | `suljettu` |
| 2 | 218 | 2026-08-09 | `Verkkokauppa tilastot` | `ei löytynyt?` |

The `ei löytynyt?` (not found?) on row 218 is a different thing from a zero: the web shop
figure is unknown. That day recorded 42 visitors through the other channels, so the true
figure is higher than that. Worth clarifying with the opening team.

**Cross-check discrepancies.** These do not affect the output, because TOTAL is computed
from the components, but they are worth fixing at the source.

| Venue | Row | Day | Components | Source total | Explanation |
| --- | --- | --- | --- | --- | --- |
| 1 | 79 | 2026-03-30 | 37 | 58 | values swapped with row 80 |
| 1 | 80 | 2026-03-31 | 58 | 37 | same |
| 1 | 142 | 2026-05-30 | 35 | 2,251 | monthly total leaked onto a daily row |
| 2 | 163 | 2026-06-15 | 0 | 475 | weekly total in the wrong column |
| 2 | 213 | 2026-08-04 | 113 | 101 | |

**A date out of order.** Row 203 at Kaupungintalo reads `25.6.2026`, but the row sits
between `24.7.2026` and `26.7.2026` and its weekday is `Lauantai` (Saturday). 2026-07-25 is
a Saturday, 2026-06-25 is a Thursday, so this is almost certainly a typo.

**The tool does not fix this automatically.** It detects the ordering problem, suggests the
date 2026-07-25 and asks the user to decide: correct it to the suggested date, keep it as
it stands, or skip the row. The default is to keep it as it stands, in which case the row's
zeros are summed into the real 2026-06-25 day without changing it. As a result **2026-07-25
is missing from the output**. This is a deliberate decision, see
[MUUNNOSRAPORTTI.en.md](MUUNNOSRAPORTTI.en.md).

**Advance bookings and the day in progress.** Row 245 at Kaupungintalo holds 2026-09-05 and
a group of 200. That is an advance booking, not a realised visitor count. The tool cuts off
the cutoff date and every later day and lists them separately. The cutoff date defaults to
the current day, because that day is still in progress. The user can change the cutoff date
or include the cut days.

**Zero days.** Kaupungintalo has many days where every component is zero, mostly Mondays
when the venue is closed. These are written to the output as zeros. The interface separates
"closed (Suljettu)" from "open, no visitors" depending on whether the source carries a
Suljettu marking.

### Exporting the result into the repository

1. Download the per-venue files in step 6.
2. Copy them to their target paths. The paths come from the `tickets_path` field in
   `config/venues.json`:

   ```
   data/raw/tickets/venue_1/tickets-venue-1.csv
   data/raw/tickets/venue_2/tickets-venue-2.csv
   ```

3. Check the change before passing it on:

   ```bash
   git diff data/raw/tickets
   ```

4. Run ingest:

   ```bash
   python -m ovf_ingest run
   ```

   It produces the file `data/processed/tickets_daily.csv`.

The `tickets_daily.csv` downloadable in step 6 can be compared against ingest's output if
you want to confirm that normalisation goes as expected. Ingest produces the same file
itself, so this one is not committed to the repository.

### Export format

`tickets-venue-{id}.csv`:

- heading row `DATE,TICKETS,GROUPS,TOTAL`
- comma delimiter
- date `d.m.yyyy` **without leading zeros**: `14.1.2026`, not `14.01.2026`
- newline `\n`, UTF-8 without a BOM
- integers without decimals

`tickets_daily.csv`:

- heading row `venue_id,date,tickets_sold,groups_sold,tickets_total`
- date in ISO format

### Self-tests

Append `?selftest=1` to the address:

```
file:///.../tools/tickets-parser.html?selftest=1
```

The tests run and the result is shown as a table. The browser tab title reads `OK 72/72` or
`VIRHE n/72`. There are 72 tests and they cover CSV parsing (quotes, an embedded delimiter,
an embedded newline, CRLF, BOM, short rows, performance), cp1252 decoding, delimiter and
profile detection on both genuine heading rows, date parsing in every supported format and
on invalid input, summing across several columns, junk row detection, text values, the
cross-check, the ordering problem, merging and the export format.

The tests run from the same code as the tool itself, so they prove that the browser they
run in behaves as expected.

---

## Regression tests against genuine data

These are run by hand. They are the tool's most important acceptance criterion, because the
expected result is known exactly.

**First set the cutoff date to `24.8.2026`** in step 3. The conversion was run by hand on
2026-08-24, so the reference files are cut off there. Without this the tool uses the current
day, which brings into the output days that were still in the future at that time.

Run 2026-08-25; all five passed.

### 1. Pekuri, profile A

Source `tools/fixtures/kavijatilastot-pekuri.csv`, output compared against
`data/raw/tickets/venue_1/tickets-venue-1.csv`.

| Measure | Expected | Result |
| --- | --- | --- |
| Rows | 222 | 222 |
| Date range | 2026-01-14 - 2026-08-23 | 2026-01-14 - 2026-08-23 |
| Single tickets | 13,957 | 13,957 |
| Groups | 3,631 | 3,631 |
| Total | 17,588 | 17,588 |
| Byte-for-byte identical | yes | **yes** |

### 2. Kaupungintalo, profile B

Source `tools/fixtures/kavijatilastot-kaupungintalo.csv`, output compared against
`data/raw/tickets/venue_2/tickets-venue-2.csv`.

| Measure | Expected | Result |
| --- | --- | --- |
| Rows | 222 | 222 |
| Date range | 2026-01-13 - 2026-08-23 | 2026-01-13 - 2026-08-23 |
| Single tickets | 11,775 | 11,775 |
| Groups | 5,281 | 5,281 |
| Total | 17,056 | 17,056 |
| Byte-for-byte identical | yes | **yes** |

2026-07-25 is **not** in the output, because row 203 of the source carries a typo. This is
intentional.

### 3. Both together, normalised

Output compared against `tools/fixtures/expected-tickets_daily.csv`.

444 rows, identical.

### 4. Merge mode on the same files

The difference against the current files in the repository:

| Venue | Added | Changed | Removed | Unchanged |
| --- | --- | --- | --- | --- |
| 1 | 0 | 0 | 0 | 222 |
| 2 | 0 | 0 | 0 | 222 |

**An empty difference is a sign of success, not an error.** The files in the repository were
already converted from these same sources. When the opening team delivers the next export,
the difference will show the new and corrected days.

### 5. Warnings and skipped rows

Every case listed under "Known problems in the source data" shows up as a warning.

| | Warnings | Skipped: junk rows | Skipped: empty rows at the end | Cut: current and future |
| --- | --- | --- | --- | --- |
| Venue 1 | 3 | 6 | 3 | 0 |
| Venue 2 | 9 | 8 | 13 | 13 |

Venue 1: three cross-check discrepancies, rows 79, 80 and 142.

Venue 2: four text values (rows 36, 108, 203, 218), two cross-check discrepancies (rows 163,
213), one ordering problem (row 203) and one duplicate day (row 203, because 2026-06-25
already appears earlier), plus one note about an implausibly large value.

Two differences against the figures in `MUUNNOSRAPORTTI.md`, both explainable:

- **Venue 1 skips 6 junk rows, not 5.** The report's list (rows 20, 49, 81, 112, 232) does
  not include row 144, which is completely empty. The tool counts it, because every skipped
  row is shown with its reason and no row is dropped silently.
- **Venue 2 produces 9 warnings, not 8.** The ninth is a note about 2026-05-05: a total of
  279 is more than five times the median of the preceding 28 days (46). The conversion run
  by hand did not have this check. It is not a data error: the day's figures are internally
  consistent (68 single, 211 group, source total 279), so this is a genuinely exceptionally
  busy day. The note exists precisely for eyeballing cases like this, not for rejecting
  them.

### How to make the comparison

Download the file in step 6 and compare:

```bash
diff ~/Downloads/tickets-venue-1.csv data/raw/tickets/venue_1/tickets-venue-1.csv
```

Empty output means the files are byte for byte the same.

---

## Constraints

- One file, no build step, no dependencies, no external requests.
- The tool works in a private browser window where `localStorage` throws. Saving is skipped
  and everything else continues as normal.
- Pasting from the clipboard always yields UTF-8 text. If the Scandinavian characters look
  wrong, drop the file instead of pasting its contents.
- File size around 115 kB.
