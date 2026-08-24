# Oulu2026 Visitor Flow Framework

Data pipeline for venue visitor forecasting. This repository currently contains
**part 1: `packages/ingest`** — fetching, normalizing and publishing the canonical
data tables. No modelling and no visualization live here yet.

`ovf_ingest` reads three external APIs, caches every response on disk unmodified,
and rebuilds a small set of canonical CSV tables plus a run manifest.

---

## Installation

Requires Python 3.12.

```bash
make install
```

That creates `.venv/` and installs the `ingest` and `dev` dependency groups. The
equivalent manual steps:

```bash
python3.12 -m venv .venv && .venv/bin/python -m pip install -e ".[ingest,dev]"
```

## Environment variables

Only the visitor API needs credentials. Copy `.env.example` to `.env` and fill it in:

```bash
cp .env.example .env
```

| Variable | Used by | Required |
| --- | --- | --- |
| `JASKARETAIL_BASIC_AUTH_USERNAME` | Jaskaretail IoT, HTTP Basic | yes |
| `JASKARETAIL_BASIC_AUTH_PASSWORD` | Jaskaretail IoT, HTTP Basic | yes |
| `OVF_ROOT` | Overrides repository root detection | no |

Real values are read from the process environment first, and from a repository-root
`.env` (or `.env.local`) only as a fallback. Both are gitignored; `.env.example` is
the template and holds no secrets. Open-Meteo and Eco-Counter need no authentication.

## Commands

```bash
python -m ovf_ingest run --days-back 7                  # daily incremental run
python -m ovf_ingest run --start 2026-01-01 --end 2026-08-22
python -m ovf_ingest run --source weather --venue 1     # limit what gets fetched
python -m ovf_ingest climatology --years 2016-2025      # run once
python -m ovf_ingest verify                             # quality gates, no fetching
```

Or through the Makefile: `make ingest`, `make ingest-full`, `make climatology`,
`make verify`, `make test`, `make lint`, `make typecheck`, `make check`.

| Flag | Meaning |
| --- | --- |
| `--days-back N` | Window is the last N days, ending today. Default 7. |
| `--start` / `--end` | Explicit local day window. `--end` requires `--start` and defaults to today. |
| `--source` | Repeatable or comma-separated: `visitors`, `weather`, `traffic`, `tickets`, `calendar`. |
| `--venue` | Repeatable venue id. Limits *fetching* only, see below. |
| `--today` | Override today's date, for reproducible runs. |
| `--log-level` | `debug`, `info` (default), `warning`, `error`. |
| `--root` | Repository root. Defaults to autodetect, then `OVF_ROOT`. |

`--source` and `--venue` narrow what is fetched, never what is written: the canonical
tables are always rebuilt from every day file on disk, so a partial run never truncates
history that a previous run collected.

### Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Everything succeeded |
| 1 | A quality gate failed; the affected tables were written as `.rejected` |
| 2 | Every attempted source failed, or the run could not start |

Logs go to stdout as one JSON object per line, with `level`, `ts`, `source` and
`message` plus any structured fields.

---

## The time zone contract

The most serious defect in the previous implementation was mixed time zones
(`docs/DATA_MODEL.md` §7.1): Eco-Counter answers in UTC, and its offset was stripped
without converting, so traffic data landed two to three hours off. This package
replaces that with an explicit contract.

**Every timestamped row carries two columns:**

| Column | Format | Role |
| --- | --- | --- |
| `ts_utc` | `2026-05-22T04:00:00Z` | **The join key.** Every table joins on this and nothing else. |
| `ts_local` | `2026-05-22T07:00:00+03:00` | Europe/Helsinki with a real offset. What a user interface shows. |

Daily rows use a `date` column, which is always the **local calendar day**.

All conversion goes through `zoneinfo`, never a fixed offset. On the spring-forward
day an hourly series has **23 rows**, and on the autumn day **25**. That is correct,
not a bug: for 1 Jan – 22 May 2026 the visitor series has **3407** rows per venue,
not 3408, because 03:00 local on 29 March 2026 does not exist.

### What each upstream actually sends

| Source | What it sends | How this package reads it |
| --- | --- | --- |
| Jaskaretail | Naive wall-clock local time, `%d/%m/%Y %H:%M:%S`, 24 labels per calendar day | Localized with `zoneinfo`. The label for the hour the clock skips is dropped with a warning. |
| Open-Meteo | Labels stamped with **one constant offset for the whole range**, reported in `utc_offset_seconds` | The reported offset is applied, not the zone rules — see below. |
| Eco-Counter | ISO 8601 in UTC, with `begin`/`end` also interpreted as UTC and **inclusive at both ends** | Converted with the offset honoured. The extra boundary hour falls into the next day and is discarded. |

**Open-Meteo needs care.** Asking it for `timezone=Europe/Helsinki` does not get
wall-clock Helsinki time back. It applies a single offset to the entire requested
range and reports it in `utc_offset_seconds`: a January window still comes back
stamped `GMT+3`. Reading those labels as local time puts every winter hour one hour
late — exactly the class of bug this rewrite exists to remove. So the request is sent
with the documented `timezone=Europe/Helsinki` parameter, but the response is decoded
using the offset the response itself declares, and `ts_local` is then derived through
`zoneinfo`. Verified against an independent `timezone=UTC` request: all 24 hours of
15 January 2026 land on the same UTC instant, to the value.

Because that offset depends on when the request is made, each weather window is
requested one day wider on each side, so a differing offset can never shave hours off
the boundaries.

---

## Outputs

### Raw cache

One JSON file per source, key and **local** calendar day, holding an unmodified copy
of the upstream response(s) for that day. Written *before* any normalization: if
normalization crashes, nothing fetched is lost.

```
data/raw/visitors/venue_{id}/{YYYY-MM-DD}.json    {"in": <response>, "out": <response>}
data/raw/weather/venue_{id}/{YYYY-MM-DD}.json     {"archive"|"forecast": <response>}
data/raw/traffic/{site_id}/{YYYY-MM-DD}.json      {"JK_IN": <response>, ... }
data/raw/tickets/venue_{id}/tickets.csv           maintained by hand
```

Each file is the day's slice of the response(s) with the surrounding structure intact.
The one field removed is Open-Meteo's `generationtime_ms`, which is server-side request
timing rather than data and would otherwise make every re-run dirty the cache.

### Canonical tables

CSV, UTF-8, `.` as the decimal separator, LF line endings, no index column. Booleans
are written as `True`/`False`, and missing values as an empty field.

| File | Key | Columns |
| --- | --- | --- |
| `data/processed/visitors_hourly.csv` | `venue_id, ts_utc` | `venue_id, ts_utc, ts_local, visitors_in, visitors_out, visitors_total, is_imputed` |
| `data/processed/visitors_daily.csv` | `venue_id, date` | `venue_id, date, visitors_in, visitors_out, visitors_total, observed_hours, is_complete` |
| `data/processed/weather_hourly.csv` | `venue_id, ts_utc` | `venue_id, ts_utc, ts_local, temperature_2m, precipitation, wind_speed_10m, relative_humidity_2m, weathercode, weathercode_str, is_precipitation, is_cold, is_windy, source` |
| `data/processed/weather_daily.csv` | `venue_id, date` | `venue_id, date, temp_mean, temp_min, temp_max, precip_sum, precip_hours, wind_mean, weathercode_mode, weathercode_str, source` |
| `data/processed/traffic_hourly.csv` | `site_id, ts_utc` | `site_id, site_name, ts_utc, ts_local, jk_in, jk_out, pp_in, pp_out` |
| `data/processed/tickets_daily.csv` | `venue_id, date` | `venue_id, date, tickets_sold, groups_sold, tickets_total` |
| `data/processed/calendar_daily.csv` | `date` | `date, holiday_name, is_holiday, is_weekend, day_of_week, days_before_next_holiday, is_last_workday_before_holiday, week_of_year, month, year` |
| `data/processed/manifest.json` | | run metadata, see below |
| `data/reference/climatology/venue_{id}.csv` | `day_of_year, hour` | `day_of_year, hour, temp_mean, temp_min, temp_max, precip_mean, wind_mean` |

### `visitors_total` is **not** a headcount

`visitors_total = visitors_in + visitors_out`. It is the number of counted **crossing
events**, so one person who walks in and later walks out contributes 2. It is not a
count of unique visitors and not a net occupancy. A rough visitor estimate is
`visitors_total / 2`. This matches the previous implementation, and is stated here
because the name invites the wrong reading.

### `is_imputed` separates a real zero from a missing hour

The previous implementation reindexed onto a dense hourly grid with `fill_value=0`, so
a genuine quiet hour and an hour the API never answered for became indistinguishable
(`docs/DATA_MODEL.md` §7.3). Here the densification still happens — a dense series is
what downstream modelling wants — but it is labelled:

- `is_imputed = False` — the API returned a value for this hour. A `0` here is a real,
  observed zero.
- `is_imputed = True` — the API returned nothing for this hour. The counts are `0` so
  sums stay well defined, but the row is *not evidence of anything*. Filter it out
  before computing rates, averages or model targets.

`visitors_daily` carries the same information per day as `observed_hours` (how many
hours were actually answered) and `is_complete` (whether that equals the number of
hours the local day has, 23, 24 or 25).

Weather and traffic have no imputation flag: their missing hours are left as empty
fields, i.e. `NaN`. Nothing is ever filled with a median or any other estimate.

### Traffic is site data, not venue data

`traffic_hourly.csv` is keyed on `site_id`, never on `venue_id`. The previous
implementation attached the single Karjasilta counter to *both* venues, which made
identical pedestrian and cycling figures appear as if they described each venue
(`docs/DATA_MODEL.md` §7.2) — including venue 2, which is in Espoo, roughly 500 km
away. Karjasilta is one measurement point in Oulu. Any link to a venue belongs in the
presentation layer and must be labelled as ambient context.

### `weather_hourly.source`

| Value | Meaning |
| --- | --- |
| `archive` | Reanalysis history, from `/v1/archive` |
| `forecast` | From `/v1/forecast`, which also covers recent days the archive has not caught up with |
| `climatology` | Long-term normals, for horizons past the 16-day forecast limit |

The last hours of the forecast horizon can legitimately come back empty from
Open-Meteo; those stay `NaN`.

### `manifest.json`

```json
{
  "generated_at": "2026-08-23T04:20:11Z",
  "pipeline": "ingest",
  "version": "1.0.0",
  "sources": [
    {"name": "jaskaretail", "status": "ok", "rows": 6816, "window": ["2026-08-16", "2026-08-23"]},
    {"name": "eco-counter", "status": "degraded", "rows": 0, "error": "HTTP 503"}
  ],
  "coverage": {
    "visitors_hourly": {"first": "...", "last": "...", "missing_hours": 12}
  },
  "quality_gates": {"passed": true, "warnings": []}
}
```

`status` is `ok`, `degraded` (some units failed), `failed` (all units failed) or
`skipped` (not selected by `--source`).

---

## How the pipeline behaves

1. **Incremental by default.** `--days-back 7`; a full rebuild is `--start 2026-01-01`.
2. **Raw response first, normalize second.** Nothing fetched is lost to a parsing bug.
3. **Idempotent.** Day files are overwritten and the canonical tables are always rebuilt
   from *every* day file, never appended to. Two consecutive runs over unchanged
   upstream data produce byte-identical files and an empty `git diff` — including
   `manifest.json`, which is left untouched when the only thing that would change is
   `generated_at`.
4. **Partial failure does not stop the run.** If Eco-Counter is down, visitors and
   weather are still fetched and the manifest records `degraded` or `failed`.
5. **Retries.** Three attempts with exponential backoff (1 s, 4 s, 16 s) on HTTP 5xx
   and timeouts. HTTP 4xx is a client mistake and is never retried.

### Quality gates

Gates run against the freshly built tables, before anything is written.

| Gate | Condition |
| --- | --- |
| `visitor_gap` | No run of unanswered visitor hours longer than 48 h within the last 30 days |
| `weather_coverage` | Weather covers at least 99 % of the fetched period |
| `negative_counts` | No negative counter values (negatives are rejected and logged during normalization) |
| `daily_capacity` | No day exceeds `capacity * 24 * 4` counted events — an obvious sensor fault |

When a gate fails, the tables it covers are written as `<name>.csv.rejected`, the
previous version is **left in place and stays authoritative**, the manifest records the
failure, and the run exits with code 1. Tables the gate does not cover are still
written normally.

`.rejected` files are gitignored: they are diagnostic output, not data.

**A note on non-contiguous windows.** Because the tables are densified across the whole
span of the day cache, days that were never fetched appear as `is_imputed` rows rather
than being silently skipped — a series with an invisible hole would hide the gap from
every downstream consumer. So backfilling January–May and then jumping straight to a
window in August will trip `visitor_gap` on the months in between, which is the gate
doing its job. The fix is to fetch the missing range, not to loosen the gate.

---

## Climatology

Open-Meteo forecasts at most 16 days ahead, so days 17–30 of a forecast need long-term
normals instead. Run this once:

```bash
python -m ovf_ingest climatology --years 2016-2025
```

It fetches ten years of hourly history per venue and reduces it to
`(day_of_year, hour) -> temp_mean, temp_min, temp_max, precip_mean, wind_mean` in
`data/reference/climatology/venue_{id}.csv`. `day_of_year` is on a common-year scale:
29 February is folded into 28 February, so day 60 means 1 March in every year.

---

## Configuration

| File | Contents |
| --- | --- |
| `config/venues.json` | Venue id, name, city, coordinates, capacity, `location_hierarchy_id`, ticket file path |
| `config/sites.json` | Eco-Counter sites: `site_id`, display name, GraphQL `domain`, and the four sensor ids |
| `config/sources.json` | Endpoints, cache directories, default window, HTTP timeout and retry policy, quality-gate thresholds |
| `config/holidays.csv` | Maintained Finnish holiday calendar |

Venues:

| id | name | city | lat | lon | capacity | `location_hierarchy_id` |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Pekuri | Oulu | 65.0134 | 25.4756 | 160 | 178 |
| 2 | Kaupungintalo | Espoo | 60.2055 | 24.6558 | 20 | 183 |

Venue 2 is named after a city hall but sits in Espoo, so its weather genuinely differs
from venue 1's. That is not a configuration error.

Ticket CSVs are matched case-insensitively against English and Finnish column aliases:
`DATE`/`pvm`, `TICKETS`/`liput`, `GROUPS`/`ryhmat`/`ryhmät`, `TOTAL`/`yhteensa`/`yhteensä`.
Dates are parsed with explicit formats only (`d.m.YYYY`, then `YYYY-MM-DD`), never by
inference. When the total column is absent it is derived as `tickets_sold + groups_sold`.

---

## Development

```bash
make check      # ruff + mypy + pytest
```

Tests never touch the network. `packages/ingest/tests/fixtures/` holds responses
captured from the live APIs, and the end-to-end tests drive the pipeline through
offline stand-ins for the three clients. Covered: each client's parsing, both 2026
daylight saving transitions, the `is_imputed` logic, every quality gate firing,
manifest structure, partial-failure handling, and byte-level idempotency.

## Repository layout

```
config/                          venues, sites, sources, holidays
packages/ingest/src/ovf_ingest/
  cli.py         command line entry point and run orchestration
  config.py      pydantic models for config/
  normalize.py   time zone contract, payload parsing, canonical table builders
  store.py       raw cache and canonical table I/O
  validate.py    quality gates and manifest construction
  climatology.py long-term weather normals
  clients/       jaskaretail.py, openmeteo.py, ecocounter.py, shared retry policy
packages/ingest/tests/
data/raw/        immutable per-day response cache
data/processed/  canonical tables and manifest.json
data/reference/  climatology
docs/            DATA_MODEL.md, FRAMEWORK_PLAN.md
```
