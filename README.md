# Oulu2026 Visitor Flow Framework

Data pipeline and published site for venue visitor forecasting. All three parts live
here:

| Part | Package | What it does |
| --- | --- | --- |
| 1 | `packages/ingest` | Fetches three external APIs, caches every response unmodified, rebuilds the canonical CSV tables plus a run manifest |
| 3 | `packages/forecast` | Reads those tables and writes 7-day hourly and 30-day daily forecasts for two models, with measured quality metrics |
| 2 | `packages/web` | Astro site that packages those files into JSON at build time and publishes a static, Finnish-language dashboard |

The parts share no code. Their only connection is the file contract in
`docs/FRAMEWORK_PLAN.md` chapters 4.2 and 4.3, and the web build fails loudly when that
contract changes. Run order is **1 → 3 → 2**.

`ovf_forecast` never calls an API. It reads `data/processed/` and writes
`data/forecasts/`. The models and their measured backtest numbers are documented in
[`docs/FORECAST_MODEL.md`](docs/FORECAST_MODEL.md).

`packages/web` calls nothing at all, at build time or in the browser. It reads the same
two directories from disk, writes six JSON files, and renders them into static HTML.

---

## Installation

Requires Python 3.12.

```bash
make install
```

That creates `.venv/` and installs the `ingest`, `forecast` and `dev` dependency
groups. The equivalent manual steps:

```bash
python3.12 -m venv .venv && .venv/bin/python -m pip install -e ".[ingest,forecast,dev]"
```

The `prophet_xgb` comparison model needs one more group, kept separate because Prophet
builds cmdstan and the install takes minutes:

```bash
make install-prophet          # or: pip install -e ".[prophet]"
brew install libomp           # macOS only: XGBoost needs an OpenMP runtime
```

Without it, `python -m ovf_forecast run` skips `prophet_xgb` with a warning and produces
the baseline forecast as normal. Nothing fails.

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

Forecasting reads only what ingest already wrote:

```bash
python -m ovf_forecast run                      # both models, every venue
python -m ovf_forecast run --model baseline     # skip the slow comparison model
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12    # validate, write nothing
python -m ovf_forecast report                   # print the last run's metrics
```

Or through the Makefile: `make ingest`, `make ingest-full`, `make climatology`,
`make verify`, `make forecast`, `make forecast-baseline`, `make backtest`,
`make report`, `make test`, `make lint`, `make typecheck`, `make check`.

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

The forecast tests run on a synthetic dataset with a known weekly rhythm, known opening
hours and a known weather response (`packages/forecast/tests/synthetic.py`), so they
assert what a model *should* have learned rather than whatever it happens to produce.
Covered: that no feature reads an observation from after the forecast origin, that the
hourly forecasts sum to the daily one in the exported files, that `p10 <= p50 <= p90`
everywhere, that the profile shares sum to 1 per weekday, that the backtest never trains
on data after its origin, that a missing prophet install is skipped cleanly, and that two
runs differ only in `generated_at`. `test_acceptance.py` additionally measures the real
committed data and fails if the baseline stops beating the seasonal-naive benchmark.


---

## Part 2: the web section

`packages/web` is an Astro 5 site with `output: 'static'`. It has no server routes, no
API endpoints and no CDN scripts: every dependency comes from npm and is bundled. The
browser never fetches data at runtime, because there is nothing to fetch.

The interface language is Finnish. Dates read `22.5.2026`, times read `14:00`, and every
count carries its unit, because `visitors_total` is the sum of entries and exits rather
than a headcount.

### Requirements

Node 20.11 or newer, and npm 10 or newer. From the repository root:

```bash
npm install
```

The workspace is declared in the root `package.json`, so this installs
`packages/web` as well.

### Commands

Run these from the repository root. Each one forwards to the `@ovf/web` workspace.

```bash
npm run dev        # package the data, then start the dev server on :4321
npm run data       # only rebuild packages/web/src/data/*.json
npm run build      # prebuild runs npm run data, then astro build into packages/web/dist
npm run preview    # serve the built dist/ locally
npm run check      # astro check: TypeScript in strict mode across pages, islands and scripts
npm test           # vitest: build-data transforms plus schema validation against the real files
npm run test:e2e   # playwright smoke test against a freshly built dist/
```

The Makefile wraps the same steps: `make web`, `make web-dev`, `make web-data`,
`make web-check`, `make web-test`. `make all` runs ingest, forecast and the web build in
that order.

Playwright needs its browser once: `npx playwright install chromium` inside
`packages/web`.

### Build-time data packaging

`scripts/build-data.ts` runs as the npm `prebuild` step. It reads `data/processed/` and
`data/forecasts/latest/`, computes the aggregates, and writes six files into
`packages/web/src/data/`, which is gitignored because it is derived:

| File | Contents |
| --- | --- |
| `meta.json` | Venues, run timestamps, coverage, quality warnings |
| `daily.json` | Per-venue daily series: visitors, weather, tickets, holidays |
| `hourly.json` | Hourly series, the last 120 days only |
| `profile.json` | Weekday x hour matrix, mean and median |
| `forecast.json` | 7-day hourly and 30-day daily, both models |
| `quality.json` | Backtest metrics and the forecast-versus-actual series |

Total under 400 kB. Floats are rounded to one decimal, counts to integers, and the two
largest files are column-oriented rather than arrays of objects, so the payload does not
grow out of budget as the history lengthens. The script prints the size of each file.

The data contract is typed in `src/lib/types.ts` and the input columns are listed in
`scripts/lib/schema.ts`. Both are checked, never assumed.

### Build gates

The build fails, with a message rather than a stack trace, when:

- `data/processed/manifest.json` is missing, or older than 48 hours
- the forecast files are missing or empty
- any input file's columns differ from `scripts/lib/schema.ts`

A failed build is the correct outcome: a site that silently shows week-old numbers as
current is worse than one that does not deploy. The age limit can be relaxed for a
deliberate run against an old dataset:

```bash
OVF_MAX_MANIFEST_AGE_HOURS=720 npm run build
```

`OVF_NOW` overrides the clock and `OVF_HOURLY_DAYS` the hourly window; both exist for
tests and reproducible runs.

### Pages

| Path | Contents |
| --- | --- |
| `/` | Both venues side by side, last 30 days, next 7 days, key figures, data freshness |
| `/venue/[id]` | Hourly and daily series, weekday x hour heatmap, capacity, ticket comparison |
| `/weather` | Temperature scatter with a linear fit, rainy versus dry, weather-class distribution |
| `/forecast` | 7-day hourly and 30-day daily, p10 to p90 band, model comparison, weather source marked |
| `/quality` | Backtest by horizon, MAE and coverage, comparison to seasonal naive, known limits |
| `/about` | Where the data comes from, what the numbers mean, what they do not mean |

### Charts

Charts are Observable Plot drawn by vanilla TypeScript islands, loaded with
`client:visible`. There is no React, Vue or Svelte integration; `src/renderer/`
registers a small Astro renderer instead, so `client:visible` works against a plain
`(element, props) => void` function. The server-rendered placeholder is not decoration:
`client:visible` observes the island's children, so an island that renders nothing on
the server never hydrates.

Every chart has a text alternative and a table underneath it, both rendered on the
server. Colour scales are sequential and keep their order in greyscale, series differ by
dash pattern as well as colour, selectors are ordinary buttons, and no view depends on
`localStorage`. Wide content scrolls inside its own container; the page itself never
scrolls sideways.

Measured on the built output: Lighthouse performance 99-100 and accessibility 100 on
every page, and the front page weighs about 99 kB gzipped including the Plot bundle.

### Deployment

Cloudflare Pages, configured against the repository root:

| Setting | Value |
| --- | --- |
| Root directory | repository root |
| Build command | `npm run build` |
| Output directory | `packages/web/dist` |
| Node version | Read from `.node-version` at the repository root (currently 22) |

`.github/workflows/deploy.yml` builds, runs both test suites and publishes on every push
to `main`. Pull requests are built and tested but not published. It needs two secrets,
`CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`, and optionally the repository
variable `CLOUDFLARE_PAGES_PROJECT` when the Pages project is not named
`oulu2026-visitor-flow`.

The workflow builds from the files in the repository, so the daily run has to commit
`data/processed/` and `data/forecasts/latest/` for the published site to move forward.
Push the data and the site follows; do not push it and the 48-hour gate stops the deploy
rather than publishing stale numbers.

The pages carry `<meta name="robots" content="noindex">`. The site is meant to be shared
as a link inside the organisation, not indexed.

---

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
packages/forecast/src/ovf_forecast/
  cli.py         command line entry point and run orchestration
  dataset.py     reads data/processed, builds history and future covariate frames
  features.py    daily features; the layer that guarantees no future leaks in
  profile.py     shared hourly profile, so hourly forecasts sum to the daily one
  backtest.py    rolling origin validation and the metrics computed from it
  intervals.py   empirical prediction intervals from measured backtest error
  export.py      writes data/forecasts deterministically
  models/        base.py (protocol + registry), baseline.py, prophet_xgb.py
packages/forecast/tests/
packages/web/
  astro.config.mjs               static output, Tailwind, the vanilla island renderer
  scripts/build-data.ts          data/ -> src/data/*.json, with the build gates
  scripts/lib/                   csv.ts, schema.ts, transform.ts, read.ts, paths.ts
  src/lib/                       types.ts (the data contract), dates, format, weather, series
  src/renderer/                  the Astro renderer that makes client:visible work without a framework
  src/charts/                    Observable Plot islands: timeseries, heatmap, scatter, bars, lines, forecast, backtest
  src/components/                Layout, QualityBanner, Figure, TableScroll, StatCard, Callout
  src/pages/                     index, venue/[id], weather, forecast, quality, about
  tests/                         vitest unit and schema tests, tests/e2e Playwright smoke test
data/raw/        immutable per-day response cache
data/processed/  canonical tables and manifest.json
data/reference/  climatology
data/forecasts/  latest/ plus one dated archive per run
docs/            DATA_MODEL.md, FRAMEWORK_PLAN.md, FORECAST_MODEL.md
.github/workflows/deploy.yml     build, test and publish to Cloudflare Pages
```
