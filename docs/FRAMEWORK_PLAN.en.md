# Oulu2026 Visitor Flow Framework: the technical plan

*English translation. Finnish original: [`FRAMEWORK_PLAN.md`](FRAMEWORK_PLAN.md).*

A new application in three parts, replacing the functionality of the current
`oulu2026-visitor-flow-prediction-tool` repository with a clearer division of
responsibility, lighter dependencies and a publishable web interface.

Based on: `docs/DATA_MODEL.md` (the APIs and the data schemas) and the code of the current
repository (`visitor_forecast/`, `app/`).

The decisions that steer this plan:

- **A new monorepo**, `oulu2026-visitor-flow-framework`. The current repository is left untouched as a reference.
- **Astro, published statically** to Cloudflare Pages. No server, no runtime costs.
- **Two forecast models side by side**: a light statistical baseline model for production and Prophet + XGBoost as a comparison, both in the same output format.

---

## 1. Goals and boundaries

### Goals

1. The parts are independent. Each can be run, tested and replaced separately.
2. The interface between the parts is a file contract, not shared Python code.
3. Fetching the data and producing the forecasts can be scheduled without a human.
4. The web part is static and can be shared as a link into production decision-making.
5. The uncertainty of the forecast is honestly visible, not hidden inside a single number.

### Boundaries

- No database. All the data is files under version control.
- No user login and no write operations from the browser.
- No real time. The update rate is one run per day.
- The ticket sales data stays a manually maintained CSV file.
- The TPM traffic data is left out of the first version, because none of it has accumulated
  on disk.

---

## 2. Architecture

```
                      EXTERNAL APIs
   Jaskaretail IoT   Open-Meteo   Oulu traffic Eco-Counter
          |               |               |
          +---------------+---------------+
                          |
                 [ PART 1: ingest, Python ]
                 fetch, normalise, validate
                          |
                          v
              data/raw/ + data/processed/
              the canonical time series data
                          |
              +-----------+-----------+
              |                       |
   [ PART 3: forecast, Python ]       |
   baseline model + Prophet/XGB       |
              |                       |
              v                       |
       data/forecasts/                |
       7 days hourly, 30 days daily   |
              |                       |
              +-----------+-----------+
                          |
                 [ PART 2: web, Astro ]
                 build-time JSON packaging
                          |
                          v
                 Cloudflare Pages, static
```

Run order in the daily run: **1 → 3 → 2**.
Development order: **1 → 3 → 2**, but part 2 can be started in parallel with fixture data.

---

## 3. Repository structure

```
oulu2026-visitor-flow-framework/
├── README.md
├── Makefile                     # make ingest / forecast / web / all
├── pyproject.toml               # one shared Python project, workspace-style
├── config/
│   ├── venues.json              # the venue definitions (replaces the venues section of settings.json)
│   ├── sources.json             # API addresses, cache directories, default windows
│   ├── sites.json               # the Eco-Counter sites and the sensor maps
│   └── holidays.csv             # the maintained public holiday calendar
├── packages/
│   ├── ingest/                  # PART 1
│   │   ├── src/ovf_ingest/
│   │   │   ├── __init__.py
│   │   │   ├── cli.py           # python -m ovf_ingest
│   │   │   ├── config.py        # pydantic models for the config/ files
│   │   │   ├── clients/
│   │   │   │   ├── jaskaretail.py
│   │   │   │   ├── openmeteo.py
│   │   │   │   └── ecocounter.py
│   │   │   ├── normalize.py     # time zones, column names, types
│   │   │   ├── store.py         # writing the raw and processed files
│   │   │   ├── validate.py      # the quality gates and building the manifest
│   │   │   └── climatology.py   # the long-term weather normals
│   │   └── tests/
│   ├── forecast/                # PART 3
│   │   ├── src/ovf_forecast/
│   │   │   ├── cli.py           # python -m ovf_forecast
│   │   │   ├── dataset.py       # processed -> the modelling matrix
│   │   │   ├── features.py
│   │   │   ├── models/
│   │   │   │   ├── base.py      # the shared interface: fit / predict / name
│   │   │   │   ├── baseline.py  # the baseline model
│   │   │   │   └── prophet_xgb.py
│   │   │   ├── profile.py       # deriving the hourly profile
│   │   │   ├── backtest.py      # rolling origin validation
│   │   │   ├── intervals.py     # the empirical prediction intervals
│   │   │   └── export.py        # writing the forecast artefacts
│   │   └── tests/
│   └── web/                     # PART 2
│       ├── astro.config.mjs
│       ├── package.json
│       ├── scripts/build-data.ts   # data/ -> src/data/*.json
│       ├── src/
│       │   ├── pages/
│       │   ├── components/
│       │   ├── lib/
│       │   └── data/            # generated, gitignored
│       └── public/
├── data/                        # shared, under version control
│   ├── raw/
│   ├── processed/
│   ├── reference/
│   └── forecasts/
├── .github/workflows/
│   ├── daily.yml                # ingest + forecast + commit + deploy
│   ├── ci.yml                   # tests and lint
│   └── deploy.yml               # web publishing only
└── docs/
    ├── DATA_MODEL.md            # copied from this repository
    ├── FRAMEWORK_PLAN.md        # this document
    └── FORECAST_MODEL.md        # the model documentation, chapter 8 as its own file
```

The Python parts share a single `pyproject.toml` with two optional dependency groups:
`ingest` and `forecast`. Prophet is in a separate `prophet` group, so that the baseline model
installs without cmdstan.

---

## 4. The data contracts

The only connection between the parts is the file contract. As long as the contract holds,
any part can be rewritten.

### 4.1 The time zone contract

The most serious data error in the current application is the mixing of time zones
(`DATA_MODEL.md` chapter 7.1). The new contract:

- **Every row with a timestamp carries two columns**: `ts_utc` (ISO 8601, `Z`) and `ts_local`
  (ISO 8601 with the Helsinki offset, e.g. `2026-05-22T07:00:00+03:00`).
- `ts_utc` is the key for every join.
- `ts_local` is the only one the interface displays.
- Daily rows use a `date` column, which is the **local calendar day**.
- On daylight saving transition days the hourly series has 23 or 25 rows. That is correct, not
  a bug.

### 4.2 Part 1: outputs

The raw cache, an unmodified copy of the API response, one file per source and day:

```
data/raw/visitors/venue_{id}/{YYYY-MM-DD}.json
data/raw/weather/venue_{id}/{YYYY-MM-DD}.json
data/raw/traffic/{site_id}/{YYYY-MM-DD}.json
```

The processed, canonical data:

| File | Key | Columns |
| --- | --- | --- |
| `data/processed/visitors_hourly.csv` | `venue_id, ts_utc` | `venue_id, ts_utc, ts_local, visitors_in, visitors_out, visitors_total, is_imputed` |
| `data/processed/visitors_daily.csv` | `venue_id, date` | `venue_id, date, visitors_in, visitors_out, visitors_total, observed_hours, is_complete` |
| `data/processed/weather_hourly.csv` | `venue_id, ts_utc` | `venue_id, ts_utc, ts_local, temperature_2m, precipitation, wind_speed_10m, relative_humidity_2m, weathercode, weathercode_str, is_precipitation, is_cold, is_windy, source` |
| `data/processed/weather_daily.csv` | `venue_id, date` | `venue_id, date, temp_mean, temp_min, temp_max, precip_sum, precip_hours, wind_mean, weathercode_mode, weathercode_str, source` |
| `data/processed/traffic_hourly.csv` | `site_id, ts_utc` | `site_id, site_name, ts_utc, ts_local, jk_in, jk_out, pp_in, pp_out` |
| `data/processed/tickets_daily.csv` | `venue_id, date` | `venue_id, date, tickets_sold, groups_sold, tickets_total` |
| `data/processed/calendar_daily.csv` | `date` | `date, holiday_name, is_holiday, is_weekend, day_of_week, days_before_next_holiday, is_last_workday_before_holiday, week_of_year, month, year` |
| `data/processed/manifest.json` | | the run's metadata, see 4.4 |

The key differences from the current situation:

- `visitors_total` is **still the sum of entries and exits**, but the `is_imputed` column says
  whether the row was fetched from the API or filled with a zero. This removes the problem of
  `DATA_MODEL.md` chapter 7.3, where a genuine zero and missing data cannot be told apart.
- The traffic data is not per venue but per site (`site_id`). The link to a venue is made only
  in the presentation layer and is clearly marked as context data. This removes the misleading
  aspect of `DATA_MODEL.md` chapter 7.2.
- The weather's `source` is `archive`, `forecast` or `climatology`.

Reference data:

```
data/reference/climatology/venue_{id}.csv   # day_of_year, hour, temp_mean, precip_mean, ...
```

### 4.3 Part 3: outputs

```
data/forecasts/latest/manifest.json
data/forecasts/latest/venue_{id}/daily_30d.csv
data/forecasts/latest/venue_{id}/hourly_7d.csv
data/forecasts/latest/venue_{id}/metrics.json
data/forecasts/latest/venue_{id}/backtest.csv
data/forecasts/{YYYY-MM-DD}/...    # an archive copy of the same structure
```

`daily_30d.csv`:

| Column | Explanation |
| --- | --- |
| `venue_id` | |
| `date` | The local calendar day |
| `horizon_days` | 1 - 30, the distance from the forecast's origin |
| `model` | `baseline` or `prophet_xgb` |
| `p10`, `p50`, `p90` | The quantiles of the forecast distribution, in visitor events |
| `weather_source` | `forecast` (days 1 - 16) or `climatology` (days 17 - 30) |
| `temp_mean`, `precip_sum`, `weathercode_str` | The weather behind the forecast |
| `is_holiday`, `holiday_name` | |
| `generated_at` | The run's timestamp in UTC |

The file has rows for **both models**, i.e. 30 days x 2 models = 60 rows per venue. The web
part filters on the `model` column.

`hourly_7d.csv`: the same logic, with the keys `venue_id, ts_utc, ts_local, horizon_hours,
model`, the values `p10, p50, p90`, plus `hour`, the weather columns and `generated_at`.

`metrics.json`: the per-model backtest metrics by horizon bucket, see chapter 8.8.

`backtest.csv`: `model, origin_date, target_date, horizon_days, venue_id, y_true, y_pred, p10,
p90`. This makes it possible to visualise model quality in the web part without recomputing
anything.

### 4.4 manifest.json

Both Python parts write a manifest. The web part's build fails if the manifest is missing or
too old.

```json
{
  "generated_at": "2026-08-23T04:20:11Z",
  "pipeline": "ingest",
  "version": "1.0.0",
  "sources": [
    {"name": "jaskaretail", "status": "ok", "rows": 3408, "window": ["2026-08-16", "2026-08-23"]},
    {"name": "open-meteo", "status": "ok", "rows": 4032, "window": ["2026-07-24", "2026-09-08"]},
    {"name": "eco-counter", "status": "degraded", "rows": 0, "error": "HTTP 503"}
  ],
  "coverage": {
    "visitors_hourly": {"first": "2026-01-01T00:00:00Z", "last": "2026-08-22T21:00:00Z", "missing_hours": 12},
    "weather_hourly": {"first": "2026-01-01T00:00:00Z", "last": "2026-09-08T21:00:00Z", "missing_hours": 0}
  },
  "quality_gates": {"passed": true, "warnings": ["eco-counter unavailable"]}
}
```

---

## 5. Part 1: ingest (Python)

### The task

Fetch the same data as the current application, normalise it and write it into files that
follow the contract of chapter 4.2. No modelling, no visualisation.

### The sources and their parameters

The API calls are identical to the current application's. The details: `DATA_MODEL.md`
chapter 2.

| Source | Call | Notes |
| --- | --- | --- |
| Jaskaretail IoT | `POST /ext/sensor/visitor` separately for `countingTypeId=in` and `out` | Basic auth from environment variables, never into the repository |
| Open-Meteo archive | `GET /v1/archive` | History, `timezone=Europe/Helsinki` |
| Open-Meteo forecast | `GET /v1/forecast`, `forecast_days` at most 16 | The cache expires in an hour |
| Eco-Counter | `POST /proxy/graphql`, `ecoCounterSiteData` per sensor | The response is in UTC, four sensors per site |

### How it works

1. **An incremental window.** The default is `--days-back 7`. A full refetch is
   `--start 2026-01-01`.
2. **The raw response is saved first**, and only then normalised. If normalisation crashes, no
   data has been lost.
3. **Idempotence.** Re-running the same day produces the same end result. The per-day files are
   overwritten, and the canonical tables are always rebuilt from the per-day files.
4. **A partial failure does not fail the run.** If Eco-Counter is down, the visitor and weather
   data are fetched anyway and the manifest is marked `degraded`.
5. **Quality gates** before the canonical files are written:
   - the visitor series may not have a gap of more than 48 hours within the last 30 days
   - weather data coverage at least 99 % over the forecast period
   - negative counters are rejected and logged
   - a day's total may not exceed `capacity * 24 * 4` (an obvious sensor fault)
   - when a gate fails, the new file is written with a `.rejected` suffix and the old one
     stays in force

### Weather climatology

Needed for the forecasts at 17 - 30 days. Run separately, once, with
`python -m ovf_ingest climatology --years 2016-2025`. It fetches 10 years of hourly data from
the Open-Meteo archive for each venue's coordinates and stores the means in the form
`(day_of_year, hour) -> temp_mean, precip_mean, wind_mean`. Leap days are handled by merging
February 29 into the preceding day.

### CLI

```bash
python -m ovf_ingest run --days-back 7                  # the daily run
python -m ovf_ingest run --start 2026-01-01 --end 2026-08-22
python -m ovf_ingest run --source weather --venue 1     # a single source
python -m ovf_ingest climatology --years 2016-2025      # one-off
python -m ovf_ingest verify                             # the quality gates without fetching
```

The return value is 0 when everything is fine, 1 when a quality gate failed, 2 when every
source failed.

---

## 6. Part 3: forecast (Python)

### The task

Produce per-venue 7-day hourly forecasts and 30-day daily forecasts with two models, together
with their quality metrics. No fetching from APIs; it reads only `data/processed/`.

### The overall structure

```
processed/  ->  dataset.build()  ->  features.build_daily() ---> model.fit / predict  ---> p50 at the daily level
                                                             \
                                     profile.build()  ------->  hourly profile  --------> hourly p50
                                                             \
                                     backtest.run()  -------->  relative errors ---------> p10 / p90
```

### The models' shared interface

```python
class ForecastModel(Protocol):
    name: str                       # "baseline" | "prophet_xgb"
    def fit(self, daily: pd.DataFrame) -> None: ...
    def predict(self, future: pd.DataFrame) -> pd.Series: ...   # p50, daily level, visitor events
```

Both models forecast at the **daily level**. The hourly level is derived with a shared profile
component, so that the models are comparable and the sum of the hourly forecast is exactly the
daily forecast. This fixes the problem in the current implementation, where `in`, `out` and
`total` are forecast separately and do not add up.

### CLI

```bash
python -m ovf_forecast run                          # both models, all venues
python -m ovf_forecast run --model baseline
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12        # validation only
python -m ovf_forecast report                       # prints metrics.json readably
```

The model documentation in full: chapter 8.

---

## 7. Part 2: web (Astro)

### The technology choices

| Choice | Justification |
| --- | --- |
| Astro 5, `output: 'static'` | Zero JS by default, islands only for the charts. Suits data that updates once a day |
| TypeScript | The data contract is typed, and the build fails if the schema changes |
| Observable Plot | Declarative, SVG, covers time series, scatter plots, heatmaps and bars with one API |
| Tailwind CSS 4 | Fast, familiar |
| Cloudflare Pages | Static hosting, automatic deploy from git |

Next.js was considered as an alternative. It was rejected, because no view needs a server: the
data is precomputed and updates once a day.

### Build-time data packaging

`scripts/build-data.ts` is run before `astro build`. It reads `data/processed/` and
`data/forecasts/latest/`, computes the aggregates in advance and writes into `src/data/`:

| File | Content | Estimated size |
| --- | --- | --- |
| `meta.json` | the venues, the update time, data coverage, quality warnings | < 5 kB |
| `daily.json` | the per-venue daily series: visitors, weather, tickets, public holidays | ~60 kB |
| `hourly.json` | the hourly series, rounded, only the last 120 days | ~250 kB |
| `profile.json` | the weekday x hour matrix, mean and median | ~10 kB |
| `forecast.json` | 7 days hourly and 30 days daily, both models | ~40 kB |
| `quality.json` | the backtest metrics and the forecast vs. actual time series | ~30 kB |

Under 400 kB in total. Floats are rounded to one decimal and timestamps are shortened.

The build's quality gates: if `manifest.json` is more than 48 hours old or the forecast files
are missing, the build fails with a clear error instead of publishing stale data.

### The pages

| Path | Content |
| --- | --- |
| `/` | Overview: both venues side by side, the last 30 days, the next 7 days, the key figures and the freshness of the data |
| `/venue/[id]` | A per-venue deep dive: the time series at the hourly and daily level, the weekday x hour heatmap, capacity utilisation, the ticket comparison |
| `/weather` | The relationship between weather and visitor counts: a scatter plot of temperature vs. visitors, a comparison of rainy and dry days, the distribution by weather class |
| `/forecast` | 7 days hourly and 30 days daily, the p10 - p90 band, the models side by side, the weather source marked |
| `/quality` | The backtest: forecast vs. actual by horizon, MAE and coverage, which model is better, the known limitations |
| `/about` | Where the data comes from, what the figures mean, what they do not mean |

### The detailed requirements for the views

**Time series**: the x axis in local time, the y axis in visitor events. History as a solid
line, the forecast dashed, p10 - p90 as a pale area. Public holidays as vertical lines. Rainy
hours as a background colour. Zoom and a range selector for the last 7 / 30 / 90 days / all.

**Heatmap**: rows are the weekday (Mon - Sun), columns the hour (0 - 23), the value the mean
`visitors_total`. A sequential colour scale, with zero values distinguished from missing ones.

**Weather correlation**: a scatter plot, x = the day's mean temperature, y = the day's
visitors, the point coloured by weather class, size = precipitation. Including a simple linear
fit and a clear warning that correlation is not causation.

**Model comparison**: the same axis, two series (`baseline`, `prophet_xgb`), with the legend
giving each one's backtest MAE. By default only `baseline` is shown.

**The data quality banner**: at the top of every page, giving the time of the last run and any
`degraded` sources.

### Accessibility and presentation

- The colour scales work in greyscale and for red-green colour blindness
- Every chart has a text alternative or a table view
- Figures are always presented with their unit: "visitor events", not a bare number
- A clear note that `visitors_total` is the sum of entries and exits

---

## 8. The forecast models

This chapter is the core of the plan. It is split out into its own file,
`docs/FORECAST_MODEL.md`.

### 8.1 Why two models

There is about 4.5 months of data from a single year. That is not enough to learn year-to-year
seasonality, but it is enough to learn the weekly rhythm and the effect of the weather. In
that situation a complex model looks more accurate than it is. The solution is to run a simple
model in production and a more complex one alongside it, and to measure which actually wins.

If the comparison model beats the baseline model in the backtest on three consecutive runs by
a clear margin (more than 10 % lower MAE), the production model is switched. Otherwise the
simple one stays.

### 8.2 The baseline model: structure

The name in the outputs: `baseline`. Three layers.

#### Layer 1: the daily level

Target: `visitors_total` at the daily level, per venue.

Model: `sklearn.ensemble.HistGradientBoostingRegressor(loss="poisson")`.

The Poisson loss was chosen because the target is a count, the distribution is right-skewed
and the forecast has to be non-negative. The Poisson loss guarantees positivity without the
bias a log transform causes in the back-transformation.

Features:

| Group | Features |
| --- | --- |
| Calendar | `day_of_week` (categorical), `is_weekend`, `is_holiday`, `days_before_next_holiday` (clipped to 14), `is_last_workday_before_holiday`, `month`, `week_of_year` |
| Season | `sin(2πd/365)`, `cos(2πd/365)`, `sin(4πd/365)`, `cos(4πd/365)`, where d is the day of the year |
| Trend | `days_since_start` |
| Weather | `temp_mean`, `temp_max`, `precip_sum`, `precip_hours`, `wind_mean`, `is_rainy_day`, `weather_group` (clear / cloudy / rain / snow / other) |
| Level | `level_7d`, `level_28d`, `dow_index_28d` |

`level_7d` and `level_28d` are the means of the last 7 and 28 **observed** days at the
forecast's origin. They are constant across the whole horizon. `dow_index_28d` is the ratio of
that weekday's mean to the 28-day mean.

**A critical design choice**: the model has no autoregressive lags that would update as the
forecast advances. The current application feeds its own forecasts back into the `lag_24h` and
`lag_168h` features, which makes the error accumulate as the horizon lengthens. In this model
every feature describing the level is computed once at the origin, so a 30-day forecast is not
a one-day forecast chained 30 times.

Ticket data is not used as a feature, because it is not available for the future.

#### Layer 2: the hourly profile

The daily forecast is split across the hours with an empirical profile.

```
share[venue][dow][hour] = the mean of the shares visitors_hour / visitors_day
                          over the days where visitors_day > 0,
                          the last 8 weeks
```

Shrunk towards the profile shared by all weekdays, so that individual outliers do not
dominate:

```
share_final = (n_dow * share_dow + k * share_all) / (n_dow + k),  k = 4
```

Finally normalised so that the day's shares sum to 1. The hourly forecast is
`daily_p50 * share_final`. This guarantees that the sum of the hourly forecasts is exactly the
daily forecast.

Opening hours are derived from the data: an hour is treated as closed if its non-zero share
over the last 8 weeks is below 5 %. The share of those hours is forced to zero before
normalisation.

#### Layer 3: uncertainty

The prediction intervals come from an **empirical backtest**, not from the model's internal
assumptions.

1. Run a rolling origin backtest (chapter 8.8).
2. Compute the relative error `r = y_true / y_pred` for every (origin, horizon) pair.
3. Compute the q10 and q90 quantiles of the `r` distribution per horizon bucket: 1 - 7,
   8 - 14, 15 - 30.
4. `p10 = p50 * q10(h)`, `p90 = p50 * q90(h)`.

The relative formulation is deliberate: the spread of the error scales with the level, so an
absolute error distribution would give quiet days intervals that are too wide and busy days
intervals that are too narrow. At the hourly level the same relative width is used as at the
daily level.

### 8.3 The baseline model: strengths

1. **No error accumulation.** Every level feature is computed at the origin, so a 30-day
   forecast is not chained.
2. **Calibrated uncertainty.** The intervals come from measured out-of-sample error, so 80 %
   coverage is verifiable rather than assumed.
3. **Light.** Dependencies: pandas, numpy, scikit-learn. No cmdstan, no compilation, install
   in under a minute, a run in under 10 seconds for both venues.
4. **Transparent.** The permutation importances and the partial dependences are directly
   interpretable, and the hourly profile can be read as a table.
5. **Internally consistent.** The sum of the hourly forecasts is the daily forecast.
6. **Tolerates missing data.** HistGradientBoosting handles NaN values natively, and no median
   imputation is needed.
7. **Non-negative by construction.** The Poisson loss, without clipping to zero afterwards.

### 8.4 The baseline model: weaknesses

1. **It does not learn year-to-year seasonality.** 4.5 months of data does not contain a
   single full year. The seasonal features are in practice an extension of the trend. The
   forecast for June rests on May's level, not on June's history.
2. **A fixed level for the whole horizon.** `level_28d` does not update as the forecast
   advances. If the visitor count is genuinely growing, the 30-day forecast underestimates
   systematically.
3. **It cannot anticipate events.** A concert, an exhibition opening or a school holiday shows
   up in the data as a spike, but the model knows nothing about future ones. This is the
   single largest source of error in an event-driven venue.
4. **The effect of the weather is a correlation, not a mechanism.** The model learns that a
   warm day brings more visitors. It cannot separate that from warm days falling in the
   holiday season.
5. **The hourly profile is static.** The same weekday profile for the whole horizon. It does
   not react to, for instance, unusual opening hours.
6. **The prediction intervals are only as reliable as the backtest is representative.** With
   4.5 months of data there are at most about 12 - 15 origins, so q10 and q90 rest on a thin
   sample.
7. **Weather beyond 16 days is climatology.** Days 17 - 30 use historical average weather,
   which smooths the forecast and artificially narrows the variation.
8. **Zero inflation.** About 60 % of the hours are zeros. At the daily level the problem is
   small, but the profile's edge hours are unstable.

### 8.5 The comparison model: Prophet + XGBoost

The name in the outputs: `prophet_xgb`. The same structure as in the current application, but
at the daily level and with the flaws fixed.

Structure:

1. **Prophet** is fitted to the daily target. An additive model: trend + weekly seasonality +
   yearly seasonality + public holidays + weather regressors (`temp_mean`, `precip_sum`,
   `wind_mean`).
2. **XGBoost** is fitted to Prophet's **residuals** with the calendar and weather features.
3. The final forecast is `prophet_yhat + xgb_residual`, clipped at zero.
4. The hourly level and the uncertainty come from the same shared components as in the
   baseline model, i.e. layers 2 and 3. Prophet's own `yhat_lower` and `yhat_upper` values are
   **not used**.

The differences from the current implementation, with the reasons:

| Current | New | Why |
| --- | --- | --- |
| Hourly Prophet, `daily_seasonality=True` **and** a custom `hourly_pattern` seasonality with `period=1` | Daily Prophet, hourly level from the profile | Two overlapping daily seasonalities are collinear and make the components uninterpretable |
| Prediction intervals: Prophet's interval + the point residual | Empirical backtest quantiles | Prophet's interval does not include XGBoost's uncertainty |
| Daily interval = the **sum** of 24 hourly intervals | The interval is computed at the daily level | Summation produces absurdly wide intervals, e.g. a forecast of 29 visitors with an interval of 0 - 502 |
| `in`, `out` and `total` as separate models | One model for `total`, with `in` and `out` split by the historical ratio | Separate models do not add up: 63.99 + 52.12 is not 191.31 |
| Forecasts fed back into the lag features | No recursion | The error accumulates as the horizon lengthens |
| One 80/20 time split, metrics computed from it, the final model fitted on all the data | A rolling origin backtest | One split gives one observation about model quality |
| Median imputation for missing features | NaN supported natively | Median imputation distorts and hides gaps in the data |

Strengths:

1. It separates the trend, the weekly cycle and the public holidays explicitly, which is a
   good communication tool: "this spike is Midsummer, not a trend".
2. Prophet's holiday component handles moveable feasts correctly.
3. The two-stage structure gives gradient boosting a chance to correct systematic deviations
   in the remaining signal.
4. The reference point is familiar and continuity with the current application is preserved.

Weaknesses:

1. **A heavy install.** Prophet requires cmdstan. The current repository has had to write a
   workaround (`_ensure_prophet_backend` creates a missing makefile). In a CI run the install
   takes minutes.
2. **Overfitting to short data.** The yearly seasonality component is fitted to 4.5 months of
   data, so it learns noise and extrapolates it into the future.
3. **The additivity assumption.** The joint effect of the weather and the weekday is not
   additive: rain affects a Saturday differently from a Tuesday. Prophet does not model
   interactions.
4. **Two sources of error in a chain.** If Prophet is systematically off, XGBoost learns to
   correct it, but the correction rests on the same small dataset.
5. **Slower.** A fit takes from seconds to minutes, which makes running the backtest over many
   origins awkward.
6. **Harder to explain.** The components file has more than 90 columns.

### 8.6 Weather beyond 16 days

Open-Meteo gives at most 16 days of forecast. A 30-day forecast, however, needs weather for
every day.

| Days | Weather source | Marking |
| --- | --- | --- |
| 1 - 16 | Open-Meteo forecast | `weather_source = "forecast"` |
| 17 - 30 | Climatology, a 10-year mean for the same calendar day | `weather_source = "climatology"` |

The current application fills missing weather with **the medians of the whole training
dataset**, which means a mixture of January and May. Climatology is clearly better, but it has
a consequence of its own: average weather produces an average visitor count, so the forecasts
for days 17 - 30 are systematically too flat. This has to be made visible in the interface:
the `weather_source` column drives a visual marking, "the weather is based on a statistical
average".

### 8.7 Validation

**The rolling origin backtest.**

```
origin o = the most recent observed day minus (n * 7 days),  n = 1..N
for each origin:
    training = all data <= o
    forecast = o+1 .. o+30
    compare against the actual values
```

As many origins are taken as the data allows, at least 8 and such that every training set has
at least 60 days. With the current data that means about 12 origins.

**The metrics**, computed per horizon bucket (1 - 7, 8 - 14, 15 - 30) and per model:

| Metric | Why |
| --- | --- |
| MAE | The main metric, in the same unit as the target |
| RMSE | Penalises large errors, reveals how spikes are handled |
| sMAPE | Relative, comparable between venues at different levels |
| Bias (mean signed error) | Reveals systematic over- or underestimation |
| Coverage 80 % | The share of actual values inside p10 - p90. Target 0.80, acceptable 0.70 - 0.90 |

**The references**, which always have to be reported alongside the models:

- *Seasonal naive*: the same weekday a week ago
- *Moving average*: the mean of the last 28 days

If neither actual model beats these, the model is not worth using. This is an essential
honesty gate, and it is reported on the `/quality` page.

### 8.8 When the forecast should not be believed

These are recorded both in `metrics.json` and in the interface.

1. A horizon beyond 14 days. The weather is climatology and the level is frozen at the origin.
2. A day with programming or an event the model does not know about.
3. The first two weeks after a new venue or a new sensor is taken into use.
4. A period where the ingest manifest reports `degraded` sources.
5. School holidays and Midsummer, of which the dataset holds at most one observation.
6. Every case where coverage fell below 0.70 in the most recent backtest.

---

## 9. Automation and scheduling

### GitHub Actions, the daily run

`.github/workflows/daily.yml`, `cron: "15 3 * * *"` UTC, i.e. 06:15 Finnish summer time.

```
1. checkout
2. setup-python 3.12, install the ingest dependencies
3. python -m ovf_ingest run --days-back 7
4. if exit != 0: open an issue and stop
5. install the forecast dependencies
6. python -m ovf_forecast run
7. commit data/processed and data/forecasts, message "data: automated update YYYY-MM-DD"
8. push, which triggers the Cloudflare Pages build
```

The secrets in GitHub Secrets: `JASKARETAIL_BASIC_AUTH_USERNAME`,
`JASKARETAIL_BASIC_AUTH_PASSWORD`. Prophet is installed only if `--model` includes
`prophet_xgb`; otherwise the job stays under two minutes.

### An alternative: a local run

A `launchd` agent for macOS (`~/Library/LaunchAgents/fi.oulu2026.ovf.plist`) or a `cron` line
for Linux. It runs the same `make daily` command. Documented as a fallback in case the Actions
minutes run out or the API requires a network Actions cannot reach.

### Handling failures

| Situation | Action |
| --- | --- |
| One source down | The run continues, the manifest is marked `degraded`, a banner on the site |
| Every source down | The run fails, the old data stays in force, a GitHub issue is opened |
| A quality gate fails | The new data goes into a `.rejected` file, the old stays in force, an issue |
| The forecast run crashes | The previous forecast stays in force, the web shows its age |
| The web build crashes | The previous publication stays in force on Cloudflare Pages |

---

## 10. Development steps

The phases are sized so that each ends in a working, testable state.

### Phase 0: groundwork

1. Create the repository `oulu2026-visitor-flow-framework`, MIT or a similar licence
2. The monorepo skeleton per chapter 3, empty packages
3. `pyproject.toml`, the dependency groups `ingest`, `forecast`, `prophet`, `dev`
4. `ruff` + `pytest` + `mypy` configurations, `.github/workflows/ci.yml`
5. Copy `config/venues.json`, `config/sites.json` and `config/holidays.csv` from the current
   repository
6. Copy `docs/DATA_MODEL.md` and this plan into the repository

Done when: `make ci` runs through with an empty test set.

### Phase 1: ingest, the read APIs

1. `config.py`: the pydantic models and loading
2. `clients/openmeteo.py`: archive and forecast, retry logic, the raw response to disk
3. `clients/ecocounter.py`: GraphQL, four sensors, UTC handling
4. `clients/jaskaretail.py`: basic auth, in and out, loading `.env`
5. Unit tests with stored responses (`tests/fixtures/*.json`), no network in the tests

Done when: each client returns a normalised DataFrame from fixture input.

### Phase 2: ingest, the canonical data

1. `normalize.py`: `ts_utc` and `ts_local`, the column names, the types, `is_imputed`
2. `store.py`: the raw files and the canonical tables, idempotent writing
3. `validate.py`: the quality gates and `manifest.json`
4. `climatology.py` and the one-off run over 10 years of data
5. `cli.py` and the commands of chapter 5
6. A full history run with `--start 2026-01-01`, comparing the row counts against the current
   repository's data

Done when: `data/processed/` contains the files of chapter 4.2 and `verify` passes.

Checkpoint: `visitors_hourly.csv` contains **3407 rows** per venue for the period 2026-01-01 -
2026-05-22. The arithmetic is 142 days x 24 h = 3408, minus the one hour that disappears in
the daylight saving transition on 2026-03-29. The current repository's `venue_N_features.csv`
has 3408 rows, because it treats timestamps as zoneless. The one-row difference is expected
and proves that the new time zone handling works.

### Phase 3: forecast, the baseline model

1. `dataset.py`: the daily modelling matrix from the canonical tables
2. `features.py`: the features of chapter 8.2, unit tests against leakage
3. `models/baseline.py`
4. `profile.py`: the hourly profile and deriving the opening hours
5. `backtest.py`: rolling origin, including the references seasonal naive and moving average
6. `intervals.py`: the relative quantiles
7. `export.py`: `daily_30d.csv`, `hourly_7d.csv`, `metrics.json`, `backtest.csv`

Done when: the baseline model beats seasonal naive on MAE at horizons 1 - 7. If it does not,
the model or the features have to be fixed before moving on.

### Phase 4: forecast, the comparison model

1. `models/prophet_xgb.py` per chapter 8.5
2. Prophet as an optional dependency, with a clear error message when it is missing
3. Both models into the same output file with a `model` column
4. A `report` command that prints the model comparison as a table

Done when: `python -m ovf_forecast run` produces rows for both models and `metrics.json`
contains four series (two models, two references).

### Phase 5: web, the skeleton and the data

1. The Astro project, Tailwind, TypeScript
2. `scripts/build-data.ts` and the JSON bundles of chapter 7
3. The types in `src/lib/types.ts`, generated or hand-written from the data contract
4. The layout, the navigation, the data freshness banner
5. The `/` overview page with the first charts

Done when: `npm run build` produces a static site that shows the correct figures.

### Phase 6: web, the views

1. `/venue/[id]`: the time series, the heatmap, capacity, tickets
2. `/weather`: the scatter plot and the weather class comparison
3. `/forecast`: the forecast charts, p10 - p90, the model selector, the weather source marking
4. `/quality`: the backtest visualisation and the limitations
5. `/about`
6. An accessibility check and the mobile view

Done when: all the views of chapter 7 work and the page weight is under 500 kB.

### Phase 7: automation

1. `.github/workflows/daily.yml`
2. The secrets into GitHub Secrets
3. A Cloudflare Pages project connected to the repository
4. Test with a manual `workflow_dispatch` run
5. Failure testing: a wrong password, an API down, a quality gate failing
6. Document the local `launchd` alternative

Done when: three consecutive automatic runs have passed and the site has updated.

### Phase 8: going live

1. Finalise `docs/FORECAST_MODEL.md` with the measured figures
2. `README.md`: install, run, troubleshooting
3. Run in parallel with the current application for 2 weeks, comparing the forecasts
4. Decide on the production model on the basis of the measured results
5. Mark the current repository as archived or leave it as a reference

---

## 11. Risks and open questions

| Risk | Impact | Mitigation |
| --- | --- | --- |
| The dataset is too short for a reliable 30-day forecast | The forecast is misleading | The references are always visible, coverage is reported, the uncertainty is emphasised |
| The Jaskaretail API changes or the credentials expire | The visitor data stops | The manifest and the banner, a GitHub issue automatically |
| Eco-Counter is only a single point in Oulu | Meaningless for venue 2 | Presented as context data, not as a per-venue metric |
| The lack of an events calendar | The single largest source of error | An open question, see below |
| The growth of the data in git | The repository bloats | The raw data is compressed monthly, an estimated 25 MB a year |
| The Cloudflare Pages build crashing | The site goes stale | The previous publication stays in force, the build quality gates |

### Open questions

1. **Is an events calendar available in machine-readable form?** Oulu2026's programme calendar
   as a feature (`is_event_day`, `event_capacity`) would probably be the single largest
   improvement to the forecast's accuracy. Worth investigating before phase 3.
2. **Does venue 2 (Kaupungintalo, Espoo) need to be included?** Its coordinates and its
   Eco-Counter link are inconsistent in the current configuration.
3. **Are the opening hours available explicitly?** At present they are derived from the data.
4. **Should the site be public or protected?** Cloudflare Access adds a login without code
   changes, if the data is internal.
