# Claude Code prompts: Oulu2026 Visitor Flow Framework

*English translation. Finnish original: [`CLAUDE_CODE_PROMPTS.md`](CLAUDE_CODE_PROMPTS.md).
The prompts themselves are run in Finnish in the original; this translation is for reading
and reviewing them.*

Six ready-made prompts: three for the main parts and three for additional features. Each is
self-contained and is run in its own Claude Code session at the repository root.

## How to use them

**Run order**: Part 1 → Part 3 → Part 2. The web part needs finished data files, and the
forecast part needs ingest's outputs.

**Prompt 4 (the ticket tool) is independent** of the others and can be run at any time,
including before parts 2 and 3. It is not part of the daily automated run but replaces a
manual step in which the ticket data is entered by hand.

**Prompt 5 (the evaluation framework) requires part 3 to be finished.** It extends the
forecast package with a command that can produce forecasts for arbitrary time windows and
compare them against the actual values automatically.

**Prompt 6 (visualising the accuracy tests) requires parts 2 and 3 as well as prompt 5.** It
adds a view to the site for reading the results of evaluation runs in the browser.

**Before the first prompt**, create the repository and copy the documentation:

```bash
mkdir -p ~/Documents/GitHub/oulu2026-visitor-flow-framework
cd ~/Documents/GitHub/oulu2026-visitor-flow-framework
git init
mkdir -p docs
cp ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/docs/DATA_MODEL.md docs/
cp ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/docs/FRAMEWORK_PLAN.md docs/
cp ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/docs/CLAUDE_CODE_PROMPTS.md docs/
claude
```

**Tips**:

- Run each prompt in a fresh session, so that the context stays clean
- Give Claude Code permission to run the tests and the lint automatically
- Each part ends with acceptance criteria; ask Claude Code to check them
- If a part is left unfinished, continue in the same session: the documents are in the
  repository

---

## Prompt 1 / 6: the ingest part (Python)

````text
You are building the first part of the Oulu2026 Visitor Flow Framework: the ingest package
that fetches the data. You are at the root of a new, empty repository.

# Read first

- docs/DATA_MODEL.md: describes every external API, their parameters, the structures of the
  responses and the data schemas of the current application. Chapter 2 is authoritative on
  the APIs, chapter 7 describes the current known errors that are now being fixed.
- docs/FRAMEWORK_PLAN.md: chapters 3, 4 and 5 are the specification of this part.

The reference implementation can be read at
~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool. In particular
visitor_forecast/iot_sensors.py, weather.py and traffic.py. Read them to confirm the details
of the API calls, but DO NOT copy the architecture: the new implementation has a different
structure and fixes the reference's errors.

# The task

Implement the package packages/ingest (Python 3.12), which fetches data from three APIs,
normalises it and writes it into canonical files. No modelling, no visualisation.

# The repository skeleton you create

pyproject.toml at the root, dependency groups: ingest (pandas, requests, pydantic,
python-dateutil, pyarrow), dev (pytest, ruff, mypy). NO Prophet in this part.

packages/ingest/src/ovf_ingest/
  __init__.py, cli.py, config.py, normalize.py, store.py, validate.py, climatology.py
  clients/jaskaretail.py, clients/openmeteo.py, clients/ecocounter.py
packages/ingest/tests/
config/venues.json, config/sources.json, config/sites.json, config/holidays.csv
data/raw/, data/processed/, data/reference/   (with .gitkeep files)
Makefile, README.md, .gitignore, .env.example

Copy config/holidays.csv straight from the reference repository's
visitor_forecast/config/holidays.csv. Convert the venues, iot_sensors, weather, eco_counters
and eco_counter_sites sections of the reference's settings.json into config/venues.json,
config/sources.json and config/sites.json. Do not invent venue values: they are venue 1
Pekuri (Oulu, 65.0134, 25.4756, capacity 160, locationHierarchyId 178) and venue 2
Kaupungintalo (Espoo, 60.2055, 24.6558, capacity 20, locationHierarchyId 183).

# The APIs

1. Jaskaretail IoT, visitor counting
   POST https://oulu.jaskaretail.com:443/ext/sensor/visitor
   Query parameters: locationHierarchyIdList, startDate, endDate (YYYY-MM-DD),
   interval=60min, countingTypeId (fetched separately with the values "in" and "out").
   HTTP Basic auth from the environment variables JASKARETAIL_BASIC_AUTH_USERNAME and
   JASKARETAIL_BASIC_AUTH_PASSWORD, loaded from the .env file if not in the environment.
   Response: {"result": [{"categoryName": "01/05/2026 08:00:00", "locationId": 178,
   "visitors": 12}, ...]}. The timestamp format is %d/%m/%Y %H:%M:%S, in local time.
   The numeric value may be under the keys visitors, counts, count or value.

2. Open-Meteo, weather
   History:  GET https://archive-api.open-meteo.com/v1/archive
   Forecast: GET https://api.open-meteo.com/v1/forecast, forecast_days at most 16
   Parameters: latitude, longitude, hourly=temperature_2m,precipitation,
   wind_speed_10m,relative_humidity_2m,weathercode, timezone=Europe/Helsinki
   No authentication. Derive the extra fields: weathercode_str (the WMO code map, see
   WEATHER_CODES in the reference's weather.py), is_precipitation (precipitation > 0),
   is_cold (temperature_2m < 0), is_windy (wind_speed_10m > 10).

3. Oulu traffic Eco-Counter, pedestrians and cyclists
   POST https://api.oulunliikenne.fi/proxy/graphql
   The query per sensor:
   query { ecoCounterSiteData(id: "karjasilta_1", domain: Oulu_Kapy, step: hour,
           begin: "2026-05-01T00:00:00", end: "2026-05-22T00:00:00") { date counts } }
   domain and step are enums (no quotes), while id, begin and end are strings.
   The site raatti (display name Karjasilta, domain Oulu_Kapy), the sensors:
   JK_IN=karjasilta_1, JK_OUT=karjasilta_2, PP_IN=karjasilta_4, PP_OUT=karjasilta_3.
   NOTE: the timestamps in the response are in UTC, unlike in the other sources.

# The time zone contract, an absolute requirement

The most serious bug in the current application is the mixing of time zones: the zone marking
is stripped from Eco-Counter's UTC timestamps without converting them, so the traffic data
lands 2-3 hours in the wrong hour.

The new contract: every row with a timestamp has TWO columns.
- ts_utc: ISO 8601 UTC, e.g. 2026-05-22T04:00:00Z
- ts_local: ISO 8601 with the Europe/Helsinki offset, e.g. 2026-05-22T07:00:00+03:00
ts_utc is the key for every join. Daily rows use a date column, which is the local calendar
day. Use the zoneinfo module, not a fixed offset. On daylight saving transition days the
hourly series has 23 or 25 rows; this is correct.

# The outputs

The raw cache, an unmodified copy of the response:
  data/raw/visitors/venue_{id}/{YYYY-MM-DD}.json
  data/raw/weather/venue_{id}/{YYYY-MM-DD}.json
  data/raw/traffic/{site_id}/{YYYY-MM-DD}.json

The canonical tables (CSV, UTF-8, a dot as the decimal separator):
  data/processed/visitors_hourly.csv
    venue_id, ts_utc, ts_local, visitors_in, visitors_out, visitors_total, is_imputed
  data/processed/visitors_daily.csv
    venue_id, date, visitors_in, visitors_out, visitors_total, observed_hours, is_complete
  data/processed/weather_hourly.csv
    venue_id, ts_utc, ts_local, temperature_2m, precipitation, wind_speed_10m,
    relative_humidity_2m, weathercode, weathercode_str, is_precipitation, is_cold,
    is_windy, source
  data/processed/weather_daily.csv
    venue_id, date, temp_mean, temp_min, temp_max, precip_sum, precip_hours,
    wind_mean, weathercode_mode, weathercode_str, source
  data/processed/traffic_hourly.csv
    site_id, site_name, ts_utc, ts_local, jk_in, jk_out, pp_in, pp_out
  data/processed/tickets_daily.csv
    venue_id, date, tickets_sold, groups_sold, tickets_total
  data/processed/calendar_daily.csv
    date, holiday_name, is_holiday, is_weekend, day_of_week,
    days_before_next_holiday, is_last_workday_before_holiday, week_of_year, month, year
  data/processed/manifest.json
    the run's metadata: generated_at, pipeline, version, sources[] (name, status, rows,
    window, error), coverage{} (first, last, missing_hours per table),
    quality_gates{passed, warnings[]}

Important differences from the reference:
- is_imputed separates a genuine zero from missing data. The reference fills missing hours
  with zeros and the difference can no longer be detected. Mark a row is_imputed=true if it
  was created by densification and the API did not return a value for it.
- The traffic data is per site (site_id), NOT per venue. The reference duplicates the same
  Karjasilta measuring point onto both venues, which is misleading.
- weather_hourly.source is archive, forecast or climatology.
- visitors_total is visitors_in + visitors_out, as in the reference. Document this clearly in
  the README: it is not a count of unique visitors.

Ticket sales: read the reference repository's data/raw/tickets/venue_{id}/tickets.csv, with
the columns DATE (format d.m.YYYY), TICKETS, GROUPS, TOTAL. Copy the files into the new
repository at data/raw/tickets/venue_{id}/tickets.csv and normalise them into
tickets_daily.csv. Support column name aliases in Finnish too: pvm, liput, ryhmat, yhteensa.

# How it works

1. An incremental window, the default --days-back 7. A full fetch is --start 2026-01-01.
2. The raw response to disk BEFORE normalisation.
3. Idempotence: re-running the same day produces the same result. The canonical tables are
   always rebuilt from all the per-day files, never appended to.
4. A partial failure does not fail the run. If Eco-Counter is down, the others are fetched
   anyway and the manifest is marked status=degraded.
5. Retry: 3 attempts with an exponential delay (1s, 4s, 16s) on HTTP 5xx and timeouts. 4xx is
   not retried.
6. Quality gates before the canonical files are written:
   - no gap of more than 48 hours in the visitor series within the last 30 days
   - weather data coverage at least 99 % over the fetched period
   - negative counters are rejected and logged
   - a day's total may not exceed capacity * 24 * 4
   When a gate fails, write the new file with a .rejected suffix, leave the old one in force,
   record it in the manifest and return exit code 1.

# Climatology

A separate command, run once: it fetches 10 years of hourly data from the Open-Meteo archive
for each venue's coordinates and stores the means as
data/reference/climatology/venue_{id}.csv with the columns
day_of_year, hour, temp_mean, temp_min, temp_max, precip_mean, wind_mean.
February 29 is merged into the preceding day. This is needed later for the forecasts at days
17-30, because Open-Meteo gives at most 16 days of forecast.

# CLI

python -m ovf_ingest run --days-back 7
python -m ovf_ingest run --start 2026-01-01 --end 2026-08-22
python -m ovf_ingest run --source weather --venue 1
python -m ovf_ingest climatology --years 2016-2025
python -m ovf_ingest verify

Exit codes: 0 all fine, 1 a quality gate failed, 2 every source failed.
Structured logging to stdout (level, timestamp, source, message).

# Tests

pytest, no network connection in the tests. Save the real response structures as
tests/fixtures/*.json files and test against them:
- each client's parsing from fixture input
- the time zone conversion, including the daylight saving transitions (2026-03-29 and
  2026-10-25)
- the is_imputed logic
- the quality gates triggering
- idempotence: the same run twice produces identical files
- the structure of the manifest

# Acceptance criteria

1. python -m ovf_ingest run --start 2026-01-01 --end 2026-05-22 produces a
   visitors_hourly.csv with 3407 rows per venue. The arithmetic: 142 days x 24 hours = 3408,
   minus the one hour that disappears in the daylight saving transition on 2026-03-29. The
   reference repository's venue_N_features.csv has 3408 rows, because it does not account for
   daylight saving at all. The difference is expected and is a sign that the time zone
   handling is correct.
2. Eco-Counter's ts_local is exactly 2 hours (winter) or 3 hours (summer) ahead of ts_utc,
   and the same hour joins correctly to the visitor data.
3. python -m ovf_ingest verify passes and manifest.json is valid.
4. Two consecutive runs produce identical files (git diff is empty).
5. ruff check and mypy pass, pytest is green.
6. README.md documents the install, the environment variables and the commands.

# Do not do these

- Do not use pandas' default timestamp parsing without a format
- Do not fill missing values with medians, use NaN
- Do not write secrets into the repository; .env is in .gitignore and .env.example is the
  template
- Do not implement forecasting logic in this part
- Do not add Prophet or xgboost to the dependencies
````

---

## Prompt 2 / 6: the forecast part (Python)

````text
You are building the third part of the Oulu2026 Visitor Flow Framework: the forecast package.
The repository already has a working ingest part, which has produced the canonical data files
in data/processed/.

# Read first

- docs/FRAMEWORK_PLAN.md chapter 8 in full. It is the specification of this part and contains
  the exact structures, features, strengths and weaknesses of the models.
- docs/FRAMEWORK_PLAN.md chapter 4.3: the schemas of the output files.
- docs/DATA_MODEL.md chapter 7: the known problems of the current implementation.
- packages/ingest/src/ovf_ingest/: where the data comes from and in what form.

The reference implementation: ~/Documents/GitHub/oulu2026-visitor-flow-prediction-tool/
visitor_forecast/modeling.py. Read it to understand what NOT to do. Its concrete errors are
listed in FRAMEWORK_PLAN.md chapter 8.5.

# The task

Implement the package packages/forecast, which reads data/processed/ and produces per-venue
7-day hourly forecasts and 30-day daily forecasts with two models, together with their
quality metrics. No API calls.

# Structure

packages/forecast/src/ovf_forecast/
  cli.py, dataset.py, features.py, profile.py, backtest.py, intervals.py, export.py
  models/base.py, models/baseline.py, models/prophet_xgb.py
packages/forecast/tests/

The forecast dependency group: pandas, numpy, scikit-learn, pyarrow.
The prophet dependency group: prophet, xgboost. Separate, because Prophet requires cmdstan.
If the prophet group is not installed, the prophet_xgb model is skipped with a clear warning;
the run is not failed.

# The models' shared interface

class ForecastModel(Protocol):
    name: str
    def fit(self, daily: pd.DataFrame) -> None: ...
    def predict(self, future: pd.DataFrame) -> pd.Series: ...

BOTH models forecast at the daily level. The hourly level is derived with a shared profile
component. This way the models are comparable and the sum of the hourly forecasts is exactly
the daily forecast. The reference implementation forecasts visitors_in, visitors_out and
total_visitors with separate models, so they do not add up (e.g. 63.99 + 52.12 is not
191.31). Do not repeat this.

# The baseline model, name "baseline"

Layer 1, the daily level:
  sklearn.ensemble.HistGradientBoostingRegressor(loss="poisson")
  Target: visitors_total at the daily level, per venue.
  The Poisson loss because the target is a count, the distribution is skewed and the forecast
  has to be non-negative without clipping afterwards.

  Features:
  - Calendar: day_of_week (categorical), is_weekend, is_holiday,
    days_before_next_holiday (clipped to 14), is_last_workday_before_holiday,
    month, week_of_year
  - Season: sin(2*pi*d/365), cos(2*pi*d/365), sin(4*pi*d/365), cos(4*pi*d/365)
  - Trend: days_since_start
  - Weather: temp_mean, temp_max, precip_sum, precip_hours, wind_mean, is_rainy_day,
    weather_group (clear/cloudy/rain/snow/other, derived from the weathercode)
  - Level: level_7d, level_28d, dow_index_28d

  level_7d and level_28d are the means of the last 7 and 28 OBSERVED days at the forecast's
  origin, and they are CONSTANT across the whole horizon. dow_index_28d is the ratio of that
  weekday's mean to the 28-day mean.

  CRITICAL: the model must not have autoregressive lags that would update as the forecast
  advances. The reference implementation feeds its own forecasts back into the lag_24h and
  lag_168h features, which makes the error accumulate. Here a 30-day forecast must not be a
  one-day forecast chained 30 times.

  Ticket data is not used as a feature, because it does not exist for the future.

Layer 2, the hourly profile (profile.py, shared by both models):
  share[venue][dow][hour] = the mean of the shares visitors_hour / visitors_day
  over the days where visitors_day > 0, the last 8 weeks.
  Shrinkage: share_final = (n_dow * share_dow + k * share_all) / (n_dow + k), k = 4
  Opening hours from the data: an hour is closed if its non-zero share over the last 8 weeks
  is below 5 %. The share of closed hours is forced to zero before normalisation.
  Finally normalise so that the day's shares sum to exactly 1.
  The hourly forecast = daily_p50 * share_final.

Layer 3, uncertainty (intervals.py, shared):
  1. Run a rolling origin backtest.
  2. Compute the relative error r = y_true / y_pred for every (origin, horizon).
  3. Compute the q10 and q90 quantiles of the r distribution per horizon bucket: 1-7, 8-14,
     15-30.
  4. p10 = p50 * q10(h), p90 = p50 * q90(h).
  The relative formulation is deliberate: the spread of the error scales with the level.
  At the hourly level use the same relative width as at the daily level.

# The comparison model, name "prophet_xgb"

1. Prophet on the daily target: trend + weekly seasonality + yearly seasonality + public
   holidays + weather regressors (temp_mean, precip_sum, wind_mean).
2. XGBoost on Prophet's residuals with the calendar and weather features.
3. The final forecast is prophet_yhat + xgb_residual, clipped at zero.
4. The hourly level and the uncertainty from the same shared layers 2 and 3. Prophet's own
   yhat_lower and yhat_upper values are NOT used.

The reference's errors that are not repeated:
- An hourly Prophet with both daily_seasonality=True and a custom hourly_pattern seasonality
  with period=1. These are the same daily cycle twice, which is collinear.
- A daily prediction interval computed as the sum of 24 hourly intervals. That produces
  absurd intervals, for example a forecast of 29 visitors with an interval of 0-502.
- A single 80/20 time split for computing the metrics.
- Median imputation for missing features.

# Weather beyond 16 days

Open-Meteo gives at most 16 days of forecast, but the horizon is 30 days.
  Days 1-16:  data/processed/weather_daily.csv, source=forecast
  Days 17-30: data/reference/climatology/venue_{id}.csv, source=climatology
Mark a weather_source column on every forecast row. Climatology flattens the forecast, and
this has to be made visible to the interface.

# Validation (backtest.py)

Rolling origin:
  origin o = the most recent observed day minus (n * 7 days), n = 1..N
  training = all data <= o
  forecast = o+1 .. o+30
As many origins as the data allows, at least 8, and at least 60 days in every training set.

The metrics per horizon bucket (1-7, 8-14, 15-30) and per model:
MAE, RMSE, sMAPE, bias (mean signed error), coverage 80 %
(the share of actual values inside p10-p90, target 0.80).

The references, which must ALWAYS be computed and reported alongside the models:
- seasonal_naive: the same weekday a week ago
- moving_average_28d: the mean of the last 28 days
If neither actual model beats these, that has to be reported clearly.

# The outputs

data/forecasts/latest/manifest.json
data/forecasts/latest/venue_{id}/daily_30d.csv
  venue_id, date, horizon_days, model, p10, p50, p90, weather_source,
  temp_mean, precip_sum, weathercode_str, is_holiday, holiday_name, generated_at
  Rows for BOTH models, i.e. 60 rows per venue.
data/forecasts/latest/venue_{id}/hourly_7d.csv
  venue_id, ts_utc, ts_local, horizon_hours, model, p10, p50, p90, hour,
  weather_source, temperature_2m, precipitation, weathercode_str, generated_at
data/forecasts/latest/venue_{id}/metrics.json
  the per-model and per-reference metrics by horizon bucket,
  plus n_origins, backtest_window, trained_at, n_training_days
data/forecasts/latest/venue_{id}/backtest.csv
  model, venue_id, origin_date, target_date, horizon_days, y_true, y_pred, p10, p90
data/forecasts/{YYYY-MM-DD}/...  an archive copy of the same structure

# CLI

python -m ovf_forecast run
python -m ovf_forecast run --model baseline
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12
python -m ovf_forecast report

The run has to be deterministic: a fixed random_state, no time-dependent randomness. The same
input produces the same result.

# Tests

- Building the features does not leak the future: a test confirming that observations after
  the origin are not used in computing any feature
- The sum of the hourly forecasts is exactly the daily forecast (tolerance 1e-6)
- p10 <= p50 <= p90 always
- The forecasts are non-negative
- The profile's shares sum to 1 for every (venue, dow)
- The backtest does not use data after the origin in training
- prophet_xgb is skipped cleanly when prophet is missing
- Synthetic data with a known weekly rhythm: the model learns it

# Acceptance criteria

1. python -m ovf_forecast run produces every file in the "outputs" section for both venues
   and both models.
2. The baseline model beats the seasonal_naive reference on MAE at horizons 1-7. If it does
   not, report this clearly and say which features would be worth adding.
3. 80 % coverage is between 0.70 and 0.90 at horizons 1-7.
4. Two consecutive runs produce identical files apart from generated_at.
5. A full run without prophet takes under 60 seconds for both venues.
6. ruff, mypy and pytest pass.
7. Write docs/FORECAST_MODEL.md documenting both models: structure, features, strengths,
   weaknesses, when the forecast should not be believed, and the MEASURED backtest figures.
   Based on docs/FRAMEWORK_PLAN.md chapter 8, but replace the estimates with the real
   figures.

# Do not do these

- Do not feed forecasts back into the lag features
- Do not use Prophet's own prediction intervals
- Do not sum hourly intervals into a daily interval
- Do not forecast visitors_in and visitors_out with separate models; split them from the
  daily forecast with the historical ratio
- Do not fetch anything from an API in this part
- Do not hide poor results: if the model loses to a reference, that is reported
````

---

## Prompt 3 / 6: the web part (Astro)

````text
You are building the second part of the Oulu2026 Visitor Flow Framework: the static web
interface. The repository already has the ingest and forecast parts, which have produced the
files in data/processed/ and data/forecasts/latest/.

# Read first

- docs/FRAMEWORK_PLAN.md chapter 7: the specification of this part, the pages and the views
- docs/FRAMEWORK_PLAN.md chapters 4.2 and 4.3: the exact schemas of the input files
- docs/FORECAST_MODEL.md: what the forecast means and what its limitations are
- data/processed/*.csv and data/forecasts/latest/: look at the real files before coding

# The task

Implement packages/web: an Astro 5 project that packages the data at build time and
visualises it. Fully static, published to Cloudflare Pages.

# Technologies

- Astro 5, output: 'static'
- TypeScript in strict mode
- Tailwind CSS 4
- Observable Plot for the charts (@observablehq/plot)
- No React, Vue or Svelte integration. The charts are vanilla TS islands, loaded with the
  client:visible directive.

# Build-time data packaging

scripts/build-data.ts is run before the astro build (the npm prebuild script). It reads
../../data/processed/ and ../../data/forecasts/latest/, computes the aggregates and writes
into src/data/ (gitignored):

  meta.json     the venues, the last update, data coverage, quality warnings   < 5 kB
  daily.json    the per-venue daily series: visitors, weather, tickets, holidays ~60 kB
  hourly.json   the hourly series, only the last 120 days, rounded             ~250 kB
  profile.json  the weekday x hour matrix, mean and median                     ~10 kB
  forecast.json 7 days hourly and 30 days daily, both models                   ~40 kB
  quality.json  the backtest metrics and the forecast vs. actual series        ~30 kB

Under 400 kB in total. Round the floats to one decimal.

The build's quality gates, which fail the build with a clear error:
- data/processed/manifest.json is missing or more than 48 hours old
- the forecast files are missing
- the schema does not match what is expected (check the columns, do not assume)
A failed build is better than a site presenting stale data.

Type the data contract in src/lib/types.ts and validate it in the build.

# The pages

/                 Overview: both venues side by side, the last 30 days, the next 7 days, the
                  key figures, the freshness of the data
/venue/[id]       Per venue: the time series at the hourly and daily level, the weekday x
                  hour heatmap, capacity utilisation, the ticket comparison
/weather          The relationship between weather and visitor counts: a scatter plot, rainy
                  vs. dry, the distribution by weather class
/forecast         7 days hourly and 30 days daily, the p10-p90 band, the model comparison,
                  the weather source marked
/quality          The backtest: forecast vs. actual by horizon, MAE and coverage, the
                  comparison against seasonal naive, the known limitations
/about            Where the data comes from, what the figures mean, what they do not mean

# The requirements for the views

Time series: x in local time, y in visitor events. History as a solid line, the forecast
dashed, p10-p90 as a pale area. Public holidays as vertical lines, rainy hours as a
background colour. A range selector: 7 / 30 / 90 days / all.

Heatmap: rows are the weekday Mon-Sun, columns the hour 0-23, the value the mean
visitors_total. A sequential colour scale. Zero values have to be visually distinguishable
from missing ones.

Weather correlation: a scatter plot, x the day's mean temperature, y the day's visitors,
colour the weather class, size the precipitation. A linear fit and a clear note that
correlation is not causation.

The forecast view: a model selector (baseline / prophet_xgb / both), by default baseline
only. The legend gives each one's backtest MAE. Days 17-30 are marked visually distinctly,
because their weather is a statistical average (weather_source = climatology).

The data quality banner: on every page, giving the time of the last run and any degraded
sources from the manifest.

# Presentation requirements

- All dates and times in Finnish time, in the format 22.5.2026 and 14:00
- Figures with their unit: "1 234 kävijätapahtumaa" (visitor events), not a bare number
- A clear note with every visitor figure: visitors_total is the sum of entries and exits, not
  a count of unique visitors
- The traffic data (pedestrians, cyclists) is presented as context data, not as a per-venue
  metric. It is a single measuring point in Oulu (Karjasilta) and has nothing to do with
  venue 2.
- The interface language is Finnish
- Avoid the em dash in body text; use a full stop, a comma or a colon

# Accessibility

- The colour scales work in greyscale and for red-green colour blindness
- Every chart has a text alternative or a table view
- Keyboard navigation works in every selector
- prefers-reduced-motion is respected
- Contrasts at least WCAG AA

# Responsiveness

Mobile first. The charts scale with the width, and wide content (tables, the heatmap) scrolls
inside its own container rather than the whole page scrolling horizontally.

# Publishing

- astro build produces dist/
- Cloudflare Pages: build command "npm run build", output directory "packages/web/dist", root
  directory the repository root
- .github/workflows/deploy.yml which builds and publishes on a push to main

# Tests

- vitest: the conversions and aggregates of build-data.ts
- A schema validation test: if the columns of a data/processed/ file change, the test fails
  with a clear message
- A Playwright smoke test: every page loads without console errors and the main chart renders

# Acceptance criteria

1. npm run build passes and produces a static site from the real data
2. The total page weight on the front page is under 500 kB (gzip)
3. Lighthouse: performance above 90, accessibility above 95
4. All six pages work, including at a mobile width of 375 px
5. If manifest.json is more than 48 hours old, the build fails with a clear error
6. The forecast view visually separates days 1-16 and 17-30
7. Every chart has a text alternative
8. README.md documents the development commands and the publishing

# Do not do these

- Do not fetch data at runtime from the browser; everything is build-time
- Do not add server routes or API endpoints
- Do not embed CDN scripts; every dependency from npm and bundled
- Do not present the forecast as a single number without its uncertainty interval
- Do not combine the traffic data into a per-venue visitor metric
- Do not use localStorage-dependent state without which the page does not work
````

---

## Prompt 4 / 6: the ticket tool (a standalone HTML file)

This is a helper, not part of the daily automated run. It can be implemented at any time,
including before parts 2 and 3. It replaces the current manual step in which
`data/raw/tickets/venue_{id}/tickets.csv` is updated by hand.

The structure of the source files has been worked out, the column mapping verified and the
conversion run once by hand. The repository's ticket files are therefore already up to date,
and they act as the tool's regression test: the tool has to produce exactly the same files.

Already in the repository:

| File | Content |
| --- | --- |
| `tools/fixtures/kavijatilastot-pekuri.csv` | The opening team's export, venue 1 |
| `tools/fixtures/kavijatilastot-kaupungintalo.csv` | The opening team's export, venue 2 |
| `tools/fixtures/expected-tickets_daily.csv` | The expected result in normalised form |
| `tools/MUUNNOSRAPORTTI.md` | The results and discrepancies of the conversion run by hand |
| `data/raw/tickets/venue_1/tickets.csv` | The result of the conversion, 222 rows |
| `data/raw/tickets/venue_2/tickets.csv` | The result of the conversion, 222 rows |

````text
You are building a helper for the Oulu2026 Visitor Flow Framework: a browser-based tool that
converts the visitor statistics CSV maintained by the opening team into per-venue ticket
figures.

# Read first

- docs/FRAMEWORK_PLAN.md chapter 4.2, the tickets_daily.csv section
- config/venues.json: the venues and their tickets_path
- packages/ingest/src/ovf_ingest/normalize.py: how the ticket data is read and normalised
- tools/MUUNNOSRAPORTTI.md: the results, discrepancies and decisions of the conversion run by
  hand. Read this carefully; it is the de facto specification of this tool.

The files the tool is developed and tested against:

- tools/fixtures/kavijatilastot-pekuri.csv          the source, venue 1
- tools/fixtures/kavijatilastot-kaupungintalo.csv   the source, venue 2
- data/raw/tickets/venue_1/tickets.csv              the expected result, 222 rows
- data/raw/tickets/venue_2/tickets.csv              the expected result, 222 rows
- tools/fixtures/expected-tickets_daily.csv         the expected result normalised, 444 rows

# The task

Implement one standalone file: tools/tickets-parser.html

The user opens it in a browser straight from the file system (file://), drops the opening
team's CSV export into it, checks the detected mapping, looks at the warnings and downloads
the per-venue tickets.csv file. Use is weekly, about five minutes.

# Absolute technical constraints

1. ONE file. All the HTML, CSS and JavaScript in the same file.
2. ZERO external requests. No CDN, no fonts from the network, no analytics. The tool has to
   work fully offline. Write the CSV parser yourself, do not use a library.
3. No build step. No npm, no bundler. Vanilla JS, modern syntax is fine.
4. All processing in the browser. Nothing is sent anywhere. Tell the user this visibly in the
   interface.
5. Works on current versions of Chrome, Safari and Firefox.

# The real structure of the source files

The opening team maintains an Excel file and exports it as CSV. There are two files, one per
venue, and they have DIFFERENT column structures. In both:

- The character encoding is windows-1252 (cp1252), NOT UTF-8. The Scandinavian characters
  break if this is skipped.
- The delimiter is a semicolon.
- Row 1 is the heading row. Column 0 is the weekday name in Finnish, column 1 the date.
- The date is in the format d.m.yyyy without leading zeros.
- The file does NOT contain a venue column. The whole file belongs to one venue.

## Profile A: PEKURI, venue 1

The heading row:
  ;Päivämäärä;Yleisöä;Ryhmät;Yhteensä;...

| Column | Heading | Use |
| 1 | Päivämäärä | the date |
| 2 | Yleisöä | TICKETS |
| 3 | Ryhmät | GROUPS |
| 4 | Yhteensä | cross-check only |
| 5+ | (unnamed) | notes and stray weekly totals, skipped |

## Profile B: KAUPUNGINTALO, venue 2

The heading row:
  ;Päivämäärä;Varaus;Verkkokauppa tilastot;Ovelta;Ktalon puh tilasto;Ryhmät ;KUTOSET;Ktalon vieraat;Yhteensä;Lisätietoa;...

| Column | Heading | Use |
| 1 | Päivämäärä | the date |
| 2 | Varaus | TICKETS, summed |
| 3 | Verkkokauppa tilastot | TICKETS, summed |
| 4 | Ovelta | TICKETS, summed |
| 5 | Ktalon puh tilasto | TICKETS, summed |
| 6 | Ryhmät  (note the trailing space) | GROUPS, summed |
| 7 | KUTOSET | GROUPS, summed |
| 8 | Ktalon vieraat | GROUPS, summed |
| 9 | Yhteensä | cross-check only |
| 10 | Lisätietoa | notes, skipped |
| 11+ | (unnamed) | junk: #ARVO!, running totals, serial numbers, skipped |

So TICKETS and GROUPS are sums over SEVERAL columns. This is the most important property of
the mapping, not a special case.

## The mapping is verified and the conversion has been run

The mapping was confirmed by comparing the computed values against the tickets.csv file that
was in the repository BEFORE the conversion:
- venue 1: all 124 overlapping days matched perfectly
- venue 2: the group figures matched on all 125 days, the single tickets on 50 days

The differences in venue 2's single tickets were not a mapping error. Every possible column
combination was tried exhaustively, and none produced a better match. The differences were
because the opening team had corrected the figures in the Excel file after the old file was
made. The changes went in both directions and the total over the whole period moved by just 6
visitors.

The conversion has since been run, and the repository's tickets.csv files are now the result
of it: 222 rows at both venues, Pekuri 2026-01-14 - 2026-08-23 and Kaupungintalo 2026-01-13 -
2026-08-23 (2026-07-25 is missing, see tools/MUUNNOSRAPORTTI.md).

IT FOLLOWS THAT: the tool has to produce, from these source files, exactly the current
repository files, row by row. If the result differs, the fault is in the tool.

# The junk rows and discrepancies that genuinely exist in the source data

The tool has to handle all of these. They were found in genuine data; they are not invented.

Rows to skip:
- Month headings: the date column reads Helmikuu or Maaliskuu
- Subtotal rows: the date column reads Yhteensä
- Empty rows and rows whose date column is empty
- Empty day rows at the end: venue 2 has dates all the way to 2026-09-18 with no data

Text values in numeric columns, interpreted as zero and flagged as a warning:
- Suljettu, suljettu (venue 2, rows 36, 108, 203)
- ei löytynyt? (venue 2, row 218)

The total column is unreliable:
- venue 1: empty on 18 rows, venue 2: empty on 55 rows
- venue 1 row 142, 2026-05-30: total 2251, while the components are 35. A monthly total has
  leaked onto a daily row
- venue 2 row 163, 2026-06-15: total 475, while every component is empty. A weekly total in
  the wrong column
- venue 1 rows 79 and 80, 2026-03-30 and 2026-03-31: the values look like they have swapped
  places between the rows
- venue 2 row 213, 2026-08-04: components 113, total 101

FROM THIS FOLLOWS A DESIGN RULE: TOTAL is always computed as TICKETS + GROUPS. The source's
total column is used ONLY for a cross-check that raises a warning when it differs. It is never
written into the output directly.

Date problems:
- venue 2 row 203: 2026-06-25 sits between the rows 2026-07-24 and 2026-07-26. This is an
  obvious typo; the correct day is 2026-07-25. The tool must not fix this automatically;
  it has to detect the ordering problem and ask the user to decide: correct it to the
  suggested date, keep it as it stands, or skip the row.

Future days:
- venue 2 row 245: 2026-09-05, Ryhmät 200. This is an advance booking, not a realised visitor.
  By default every day after the current day is left out, and they are listed separately. The
  user can include them if they want.

Zero days:
- venue 2 has 59 days where every component is zero, mostly Mondays when the venue is closed.
  These are written into the output as zeros, because a zero is a genuine observation.
  Distinguish "closed" from "open but no visitors" in the interface whenever the source
  carries a Suljettu marking.

# The flow of the interface

Step 1: choosing the file
  A drop zone and a file chooser, plus paste from the clipboard.
  Automatic detection: the character encoding (try UTF-8 with TextDecoder fatal:true, falling
  back to windows-1252, strip the BOM), the delimiter (semicolon, comma, tab, pipe), the
  heading row.
  Detect the profile from the signature of the heading row: if the headings contain Yleisöä,
  choose profile A and venue 1. If they contain Verkkokauppa tilastot or KUTOSET, choose
  profile B and venue 2. Show the result of the detection and let the user change it.
  Several files can be processed one after another in the same session, and the results
  accumulate per venue.

Step 2: preview
  A table, the first 20 rows, the column names and indices. The row count and the problems
  detected.

Step 3: mapping
  Prefilled from the detected profile, but everything editable:
  - the date column and its format (d.m.yyyy, dd.mm.yyyy, yyyy-mm-dd, an ISO timestamp, an
    Excel serial number)
  - TICKETS: a multi-select of columns, the values are summed
  - GROUPS: a multi-select of columns, the values are summed
  - the cross-check column, optional
  - the venue the whole file is assigned to
  Columns are identified primarily by index and the heading name is the confirmation. When
  comparing headings, strip the leading and trailing spaces and ignore case, because the
  source contains for instance "Ryhmät " with a trailing space.
  Numeric values have to support a decimal comma and a thousands separator (a space or a
  non-breaking space).
  The mapping is saved as a named profile in localStorage. Two profiles are preinstalled:
  Pekuri and Kaupungintalo. If localStorage is unavailable (a private window), the tool has to
  work normally without saving: wrap every read and write in try/catch.

Step 4: result and checks
  Aggregation: group by day, sum TICKETS and GROUPS, compute TOTAL = TICKETS + GROUPS.
  Show a table, a summary and a small inline SVG bar chart of the daily figures.
  In the summary: rows read, rows accepted, rows skipped grouped by reason, the date range,
  the number of days, the totals.
  The warnings each on their own row, clickable so that the source row is highlighted in the
  preview, and each naming the row number in the source file:
  - the date did not parse
  - the date is out of order, suggest a correction
  - the same day appears several times
  - a text value in a numeric column, show the original text
  - the cross-check does not match, show both figures and the difference
  - a negative value
  - a day in the future
  - an implausibly large value: more than 5 times the median of the last 28 days
  - a venue received no rows at all

Step 5: merging with what exists
  Two modes, merging by default:
  - Replace: only the data just parsed
  - Merge: the user loads or pastes the current tickets.csv, the tool merges, removes
    duplicates by day (the new one wins) and sorts by date. Show the difference: days added,
    days changed with their old and new values, and days removed.
  The expected result with this data: zero days added and zero days changed, because the
  repository's files have already been converted from these same sources. An empty difference
  is therefore a sign of success, not an error. When the opening team delivers the next
  export, the difference will show the new and corrected days.

Step 6: export
  - Download the per-venue tickets.csv. The format exactly: the heading row
    DATE,TICKETS,GROUPS,TOTAL, a comma delimiter, the date in the format d.m.yyyy WITHOUT
    leading zeros (14.1.2026, not 14.01.2026), the newline \n, UTF-8 without a BOM, integers
    without decimals.
    The file name tickets-venue-{id}.csv, and show the target path
    data/raw/tickets/venue_{id}/tickets.csv
  - Download the combined tickets_daily.csv in normalised form
    venue_id,date,tickets_sold,groups_sold,tickets_total, the date in ISO format.
    This is for checking; ingest produces the same file itself.
  - A "copy to clipboard" button for each.
  - Show the next steps: where the files are copied and that
    python -m ovf_ingest run is run afterwards

# Vocabulary and honesty

The source files are called Kävijätilastot (visitor statistics) and their columns are channels
(booking, web shop, at the door, phone, groups, house guests). So these are not pure ticket
sales but visitor counts by channel. The framework's tickets_sold and groups_sold fields mean,
in practice, individual visitors and group visitors. Write this visibly both into the
interface and into tools/README.md, so that the figures are not read as a sales report.

# Interface requirements

- The language is Finnish
- The steps are visible as a progress indicator, and you can go back without losing work
- A dark and a light theme following prefers-color-scheme
- Works at a width of 375 px; the primary use is on the desktop
- Keyboard navigation in every selector, a visible focus
- Contrasts at least WCAG AA
- Warnings do not stand out by colour alone; an icon or text as well
- Avoid the em dash in body text; use a full stop, a comma or a colon

# CSV parser requirements

RFC 4180 compatible: quoted fields that may contain the delimiter, a newline or a doubled
quote. CRLF and LF. Empty rows are skipped. A varying number of columns does not break the
parse but is recorded as a warning. Rows often have fewer columns than the heading row, so pad
the missing ones with empties. A 50,000-row file has to parse in under a second.

# Self-testing

Since there is no build step, include the tests in the same file. With the URL parameter
?selftest=1 the tool runs the tests and shows the results as a table. At least these have to
be tested:
- CSV parsing: quotes, an embedded delimiter, an embedded newline, CRLF, BOM, short rows
- cp1252 decoding: a string containing ä, ö and å decodes correctly
- delimiter and profile detection on both genuine heading rows
- date parsing in every supported format and on invalid input
- summing several columns into the TICKETS and GROUPS fields
- junk row detection: Helmikuu, Maaliskuu, Yhteensä, empty
- a text value in a numeric column is interpreted as zero and produces a warning
- a cross-check discrepancy is detected
- a date that is out of order is detected
- merging: a duplicate day, the new one wins
- the export format: no leading zeros, the heading row, the newlines

# Regression tests against genuine data

These have to be run by hand and recorded in tools/README.md. They are this tool's most
important acceptance criterion, because the expected result is known exactly.

1. tools/fixtures/kavijatilastot-pekuri.csv with profile A:
   the result has to be identical row by row to the file
   data/raw/tickets/venue_1/tickets.csv. 222 rows, 2026-01-14 - 2026-08-23, single tickets in
   total 13,957, groups 3,631, everything together 17,588.
2. tools/fixtures/kavijatilastot-kaupungintalo.csv with profile B:
   the result has to be identical row by row to the file
   data/raw/tickets/venue_2/tickets.csv. 222 rows, 2026-01-13 - 2026-08-23, single tickets in
   total 11,775, groups 5,281, everything together 17,056.
   Note that 2026-07-25 is NOT in the result, because row 203 of the source carries a typo.
   This is intentional; do not fix it.
3. Both together, normalised: the result has to match the file
   tools/fixtures/expected-tickets_daily.csv, 444 rows.
4. Merge mode on the same files: the difference has to be empty.
5. Every case listed under "the junk rows and discrepancies" shows up as a warning. The
   expected warning count: venue 1 three warnings and five skipped rows, venue 2 eight
   warnings and eight skipped rows.

The comparison can be made with diff, because the files have to be byte for byte the same.

# Documentation

Write tools/README.md: the problem the tool answers, a step-by-step guide, the column mapping
of both profiles as a table, the known problems in the source data, how the result is exported
into the repository, what is run afterwards, and how the self-tests are run. Add a mention of
the tool to the repository root's README.md.

# Acceptance criteria

1. tools/tickets-parser.html opens from a file:// address and works without a network. Zero
   external requests in the browser's network tab.
2. Both genuine files from tools/fixtures/ parse correctly, the Scandinavian characters show
   correctly, and the profile is detected automatically.
3. ?selftest=1 runs the tests and all of them pass.
4. All five regression tests pass. In particular: the downloaded tickets-venue-1.csv is byte
   for byte identical to data/raw/tickets/venue_1/tickets.csv, and the same holds for venue 2.
5. Merge mode shows the difference accurately and does not lose old days.
6. The tool works in a private browser window where localStorage throws.
7. The file size is under 250 kB.

# Do not do these

- Do not add external dependencies or CDN links
- Do not send data anywhere, not even for error reporting
- Do not write the source's total column straight into the output; it is unreliable
- Do not fix dates that are out of order automatically; ask the user
- Do not drop rows silently; every skipped row appears in the warnings with its reason
- Do not assume UTF-8; the source is windows-1252
- Do not add 2026-07-25 to venue 2's result; its absence is a deliberate decision
- Do not change the repository's tickets.csv files; they are the regression test's expected
  result
- Do not round the ticket figures into floats; they are integers
- Do not make this part of the Astro application; it is a standalone file
````

---

## Prompt 5 / 6: the evaluation framework (Python, extends part 3)

Requires part 3 (`packages/forecast`) to be finished. This adds a command to it for producing
forecasts for any time window and comparing them against the actual values automatically,
together with a statistical assessment of whether the difference against a reference is
significant.

The prompt contains the real figures from the current data, so the acceptance criteria can be
checked number by number.

````text
You are extending the forecast package of the Oulu2026 Visitor Flow Framework with an
evaluation framework for testing the accuracy of the forecasts systematically over arbitrary
time windows.

# Read first

- docs/FRAMEWORK_PLAN.md chapter 8: the structure of the models, chapter 8.7 validation
- docs/FORECAST_MODEL.md: the documentation of the models and the measured figures
- packages/forecast/src/ovf_forecast/: the current implementation, in particular backtest.py,
  features.py, intervals.py and models/
- data/processed/visitors_daily.csv: the data the evaluation targets

# The task

Implement `python -m ovf_forecast evaluate`, with which one can:

1. Train the model over a freely chosen historical period
2. Forecast a freely chosen test period
3. Compare the forecast against the actual values automatically
4. Say whether the difference against a reference is statistically significant
5. Accumulate results across runs, so that the model's development can be followed

The example use this is built for: train on the January-March data, forecast April, get an
automatic assessment of the accuracy.

# Structure

packages/forecast/src/ovf_forecast/evaluation/
  __init__.py
  windows.py      defining and resolving the windows
  runner.py       running one window: training, forecast, fetching the actual values
  baselines.py    the references
  metrics.py      the metrics
  significance.py bootstrap, Diebold-Mariano, power analysis
  totals.py       estimating the total for the period
  store.py        saving the results and the registry
  report.py       generating the markdown report
packages/forecast/tests/test_evaluation_*.py

No new dependencies are needed. numpy is enough for the bootstrap; do not add scipy or
statsmodels for the sake of a t-distribution: implement the p-value from the bootstrap.

# Defining a window

A window consists of three things:

- origin: the last day whose data may be used in training
- test_start, test_end: the period being evaluated, always starting at origin + 1 day
- train_window: `all` (the whole history up to the origin) or a number of days (a rolling
  window)

The target is `visitors_total` at the daily level, per venue. The ticket target is an optional
extra; implement it only if the main target works.

# Leakage rules, the most important requirement of this feature

An evaluation is useless if the forecast has seen data from the test period. Everything below
is mandatory:

1. The model is trained only on data whose day is <= origin.
2. The level features (level_7d, level_28d, dow_index_28d) are computed at the origin and stay
   constant through the whole test period.
3. The hourly profile is derived from the training data only.
4. The MASE denominator is computed from the training data only.
5. The prediction interval quantiles come from a nested backtest run ENTIRELY inside the
   training window. This is easy to get wrong: in a normal run the quantiles are computed from
   the most recent data, but in an evaluation they must not see the test period.
6. Calendar information (public holidays, weekdays) is allowed, because it is known in
   advance.
7. Ticket data is not used as a feature, because it does not exist for the future.

## Handling the weather, three modes

The weather is a special case. In production a weather forecast is available, not the realised
weather. On the realised weather the evaluation gives too good a result. Run every window in
three modes and report all of them:

| Mode | Weather over the test period | Interpretation |
| perfect | the realised weather for the whole period | Upper bound: what the model could do if the weather were known |
| operational | realised for days 1-16, climatology from day 17 | The most realistic estimate, assuming a good weather forecast |
| climatology | climatology for the whole period | Lower bound: what the model can do without a weather forecast |

The default is `operational`. The difference between perfect and climatology says how large a
share of the model's accuracy rests on knowing the weather. That is a valuable result in
itself; report it separately.

An optional extra, implement only if you have time: Open-Meteo has an archived weather
forecast service, which would give exactly the forecast that was available at the origin.
Check the documentation first for whether it exists and what it returns, and do not assume the
shape of the API. If it works, add a fourth mode, `archived_forecast`, which is the genuinely
correct answer to this problem.

# The references

These are always computed and their definitions are binding. All of them are leak-free, i.e.
they use only data <= origin.

1. `seasonal_naive`
   For a test day t, take the observation from the same weekday in the 7-day period preceding
   the origin (the origin included). The same week is repeated across the whole horizon.
   NOTE: do not use the form y[t-7], because at horizon 8 and beyond it would read actual
   values from the test period. That is a leak.

2. `moving_average_28d`
   The mean of the 28 days preceding the origin, constant through the whole test period.

3. `climatology_dow`
   The training data's per-weekday mean, constant for each weekday.

The default reference for the verdict is **the best of these three on that window**, not
seasonal_naive. The justification: with the current data climatology_dow beats seasonal_naive
in most months, so seasonal_naive would be too low a bar. Report all three regardless.

# The metrics

Computed per venue, per model and per horizon bucket (1-7, 8-14, 15-30):

| Metric | Notes |
| MAE | The main metric |
| RMSE | Penalises large errors |
| MASE | MAE divided by the training data's seasonal naive MAE. Comparable across venues |
| Bias | Mean signed error; reveals systematic over- or underestimation |
| Pinball loss | For the quantiles 0.1, 0.5 and 0.9. The proper score for a quantile forecast |
| Coverage 80 % | The share of actual values inside p10-p90 |
| sMAPE | Compute it, but flag it unreliable when the test period contains zero days |

The sMAPE warning is necessary: venue 2 has 33 zero days, and sMAPE explodes on them. Do not
use sMAPE as the basis of the verdict.

# The statistical assessment

## The basic setup

The absolute error series of the model and the reference are compared pairwise:

    d_t = |y_t - model_t| - |y_t - reference_t|

A negative mean means the model is better.

## A single window's assessment, the primary method

A moving block bootstrap:
- block length 7 days, so that the autocorrelation of the weekly rhythm survives
- 10,000 resamples
- a 95 % percentile-based confidence interval for the mean of d
- verdict: better if the whole interval is below zero, worse if the whole interval is above
  zero, otherwise no detectable difference

Also report the skill score SS = 1 - MAE_model / MAE_reference and its bootstrap interval.

## Diebold-Mariano as a secondary test

Also compute the DM statistic with a Newey-West variance (Bartlett kernel, lag
ceil(1.5 * n^(1/3))) and the Harvey-Leybourne-Newbold small-sample correction. Report the
p-value, but mark it as secondary and write in the report why: the 30 errors from one origin
are not independent observations, because they share the same training set and the same state
of the world. DM's assumptions are therefore stretched.

## Power analysis, a mandatory part of the verdict

When the verdict is "no detectable difference", it can mean two different things: the models
are equally good, or the sample is too small. Separate these by computing the minimum
detectable effect:

    MDE = 2.8 * sd(d) / sqrt(n)

Report the MDE both as visitors per day and as a percentage of the reference's MAE. With the
current data, over a one-month window the MDE is on the order of 27-30 % of the reference's
MAE, i.e. one month can only prove large improvements. This has to be clearly visible in the
report, so that nobody reads a "no difference" result as evidence of equivalence.

## Pooling several windows, the most important result

The verdict from one window is descriptive, not probative. The actual evidence comes from
pooling several windows:

- the bootstrap resamples WHOLE WINDOWS, not individual days, because the window is the
  natural unit of independence
- report the per-window results as a table and their pooled summary as one verdict
- say how many windows favoured the model and how many went against it

Make this pooled verdict the report's main heading. The verdict for an individual window is
presented below it as a detail.

## Multiple comparison correction

When a sweep runs k windows and m models, chance produces significant results. Report both the
raw and the Holm-Bonferroni-corrected p-value, and state the size of the family.

# The other assessments

## Bias

A bootstrap confidence interval for the mean error. If the interval does not contain zero, the
model systematically over- or underestimates. Give the direction and the magnitude both as
visitors and as a percentage.

## Calibration

80 % coverage and a Clopper-Pearson exact binomial interval for it. Verdict: calibrated if
0.80 is inside the interval, too narrow if coverage falls below, too wide if above.

## The total for the period

A producer asks "how many visitors in April", not "what was the daily MAE". Report separately:
- the forecast total and the actual, the absolute and the percentage difference
- an 80 % interval for the total

The interval for the total must NOT be computed by summing the daily p10 and p90 values. That
is the same mistake the old application made. Compute it by simulation: block-bootstrap the
daily relative errors of the backtest inside the training window, multiply the daily forecasts
by them, sum each simulated path, and take the quantiles from the distribution of the sums.

This difference is genuinely visible in the data: in April, venue 1's climatology_dow hits the
monthly total to within 0.8 %, even though its daily MAE is 96 visitors, i.e. about 22 % of
the daily mean. A good monthly total and poor daily accuracy can occur at the same time, and
neither may be inferred from the other.

# Sweeps

python -m ovf_forecast evaluate --sweep monthly --from 2026-04 --to 2026-08
  the origin is the last day of the previous month, the test period is a whole month

python -m ovf_forecast evaluate --sweep rolling --step 14 --horizon 30
  the origin moves in 14-day steps, the test period is always horizon days

A sweep runs every window, saves them separately and produces a pooled verdict.

# CLI

python -m ovf_forecast evaluate --train-end 2026-03-31 --test 2026-04-01:2026-04-30
python -m ovf_forecast evaluate --test 2026-04
python -m ovf_forecast evaluate --sweep monthly --from 2026-04 --to 2026-08
python -m ovf_forecast evaluate --sweep rolling --step 14 --horizon 30
python -m ovf_forecast evaluate --models baseline,prophet_xgb
python -m ovf_forecast evaluate --reference best|seasonal_naive|moving_average_28d|climatology_dow
python -m ovf_forecast evaluate --weather perfect,operational,climatology
python -m ovf_forecast evaluate --train-window all|120
python -m ovf_forecast evaluate --venue 1
python -m ovf_forecast evaluate report --id <run_id>
python -m ovf_forecast evaluate report --pooled
python -m ovf_forecast evaluate list

`--test 2026-04` is a shorthand: the origin is 2026-03-31 and the test period is all of April.

The run is deterministic: a fixed seed for the bootstrap, the same input produces the same
result. At the end of the run print the verdict as one human-readable paragraph in Finnish, so
that the command can be run without having to open the report.

# The outputs

data/evaluations/index.json
  a catalogue of runs: run_id, creation time, window, models, main reference, verdict

data/evaluations/{run_id}/config.json      the run's full parameters
data/evaluations/{run_id}/predictions.csv
  venue_id, date, horizon_days, model, weather_mode, y_true, p10, p50, p90
data/evaluations/{run_id}/metrics.json     every metric
data/evaluations/{run_id}/verdicts.json    the verdicts in machine-readable form
data/evaluations/{run_id}/report.md        the human-readable report

The run_id is deterministic and readable, for example
eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline. The same run with the same parameters
overwrites the same directory rather than creating a new one.

# The structure of the report

1. The verdict in one paragraph in Finnish, without jargon
2. The window and the setup: what was trained, on what, what was forecast
3. The monthly total: forecast, actual, difference, 80 % interval
4. The daily metrics as a table, the models and the references side by side
5. The statistical assessment: the confidence interval, the skill score, the MDE, DM's p-value
6. Calibration and bias
7. A comparison of the three weather modes
8. Limitations: the sample size, what cannot be concluded from this
9. The worst days, the five largest errors with their dates and possible causes (a public
   holiday, exceptional weather, an event)

Section 9 is in practice the most useful one: it says what the model is missing.

# Tests

The most critical first.

1. The leakage test, the most important test in the whole feature:
   run the evaluation, save the forecasts, then replace ALL the data after the origin with
   random numbers, run the forecast stage again and confirm that the forecasts are
   bit-identical. If they change, there is a leak somewhere.
2. The exact values of the references, see the acceptance criteria.
3. seasonal_naive does not use observations from the test period at horizons 8-30.
4. The nested backtest does not see the test period: the same test as 1, targeted at the
   computation of the quantiles.
5. The bootstrap's coverage: on synthetic data with a known difference, the 95 % confidence
   interval contains the true value about 95 % of the time (Monte Carlo, 200 repetitions).
6. Determinism: two consecutive runs produce identical files.
7. The interval for the total is not the sum of the daily intervals: a test confirming that it
   is narrower than the naive sum.
8. The MDE calculation against a hand-computed example.

# Acceptance criteria

These are computed from the current data (data/processed/visitors_daily.csv, 237 days per
venue, 2026-01-01 - 2026-08-25) and they have to match.

1. The window origin 2026-03-31, test 2026-04-01 ... 2026-04-30, venue 1, the references:

   | Reference | MAE | RMSE | Bias | Forecast total |
   | seasonal_naive | 129.50 | 158.12 | +66.10 | 15,172 |
   | moving_average_28d | 197.61 | 219.80 | +138.22 | 17,336 |
   | climatology_dow | 96.20 | 122.72 | +3.44 | 13,292 |

   The actual total 13,189. The MASE denominator (the training data's seasonal naive MAE)
   141.18.

2. The same window, venue 2, the references:

   | Reference | MAE | Forecast total |
   | seasonal_naive | 138.57 | 7,656 |
   | moving_average_28d | 88.16 | 5,802 |
   | climatology_dow | 75.14 | 5,346 |

   The actual total 3,791. The MASE denominator 128.57.

3. The monthly sweep 2026-04 ... 2026-08 produces five windows for both venues and a pooled
   verdict.
4. The leakage test passes.
5. The verdict always names the main reference and gives the MDE, including when no difference
   was detected.
6. A full sweep without prophet takes under five minutes.
7. ruff, mypy and pytest pass.
8. Update docs/FORECAST_MODEL.md with the evaluation's results and add docs/EVALUATION.md,
   which explains how the evaluation is run, how the results are read and what CANNOT be
   concluded from them.

# An expected finding, do not be surprised if this happens

With the current data it is likely that the model does not beat the climatology_dow reference
statistically significantly in any individual month. There is only about eight months of data
from a single year, and the MDE is on the order of 30 %. This is a correct and honest result,
not a failure. Report it as it stands and say what additional data or additional features (an
events calendar, for instance) could change.

If the model loses to a simple reference in several windows, say so directly in the report's
first paragraph.

# Do not do these

- Do not use data from the test period at any stage of the training, the features or the
  quantiles
- Do not use the form y[t-7] as the seasonal naive reference beyond a 7-day horizon
- Do not sum the daily p10 and p90 values into a monthly interval
- Do not base the verdict on sMAPE; venue 2's zero days break it
- Do not present a single window's result as proof; it is descriptive
- Do not leave out the MDE when the verdict is "no difference"
- Do not choose the weakest option as the reference to make the model look better
- Do not hide poor results in appendices
````

---

## Prompt 6 / 6: visualising the accuracy tests (Astro, extends part 2)

Requires parts 2 and 3 as well as prompt 5 to be finished, and at least one run to exist in
`data/evaluations/`. This adds a view to the site for reading the results of evaluation runs
in the browser through tables and charts.

````text
You are extending the web part of the Oulu2026 Visitor Flow Framework with a view that
visualises the forecast model's accuracy tests.

# Read first

- README.md chapter "Part 3: measuring forecast accuracy": what the evaluation does
- docs/EVALUATION.md: the meaning of the verdicts, the MDE, the three weather modes, what
  cannot be concluded from the results. Chapter 11 is the basis of this view's text content.
- packages/web/scripts/build-data.ts and scripts/lib/: how the data is packaged at build time
- packages/web/src/views/QualityView.astro: the closest existing counterpart
- packages/web/src/charts/: the current structure of the Observable Plot islands
- data/evaluations/index.json and one run's verdicts.json: the shape of the source data

# The task

Add a new page `/accuracy` (and `/en/accuracy`) to the site, on which all the saved evaluation
runs can be browsed. The page is public and is linked in the navigation.

# The relationship to the current /quality page

There are now two of these and they answer different questions. Confusion is likely, so both
pages get a short explanation and a cross-reference to the other:

- `/quality` measures **the production pipeline**: the rolling origin backtest, from which the
  prediction intervals the published forecast carries are derived. It moves on every run.
- `/accuracy` measures **chosen windows**: train up to here, forecast this period, did the
  model beat a simple rule. It moves when somebody runs an evaluation.

# Packaging the data

Extend `scripts/build-data.ts` to produce a new file, `src/data/accuracy.json`.

The sources:
- `data/evaluations/index.json`: the list of runs
- `data/evaluations/{run_id}/verdicts.json`: everything needed to present the verdict
- `data/evaluations/{run_id}/predictions.csv`: the columns
  `venue_id, date, horizon_days, model, weather_mode, y_true, p10, p50, p90`

`verdicts.json` is ready as it stands: it contains the `window` or `sweep` metadata,
`summary_fi`, `family_size`, and per venue `baseline_mae`, plus per model `comparison`
(mean_difference, ci_low, ci_high, verdict, model_mae, reference_mae, skill_score, mde,
mde_pct, dm_*), `bias`, `calibration`, `total` and `weather_sensitivity`. A sweep run
additionally has `windows[]` and, per model, `pooled` and `per_window[]`. Do not recompute
these in the browser; read them as they stand.

Pruning, so that the bundle stays small:
- from `predictions.csv` take only the rows whose `weather_mode` is the run's
  `primary_weather_mode`
- take the time series from at most the 12 most recent window runs, and always from every run
  a sweep refers to
- the verdicts are taken from every run
- round the floats: visitor counts to one decimal, proportions to three
- the target size is under 150 kB

Type the contract in `src/lib/types.ts` and validate it in the build the same way as the other
bundles.

## Two exceptions to the current build gates

1. **Missing evaluation data must not fail the build.** If `data/evaluations/` is missing or
   empty, write an `accuracy.json` with an empty `runs` list and let the page render an empty
   state. The evaluation is an optional step, unlike ingest and forecast.
2. **`schema_version` is checked.** If some run's `verdicts.json` is not `v1`, the build fails
   with a clear message naming which run and which version it saw. Silently rendering the
   wrong thing is worse than a failed build.

# The structure of the page

## The run selector

At the top a selector listing the saved runs: the pooled summaries first, then the individual
windows, both newest first. Each shows the test period, the kind, the models and the verdict
briefly.

The selected run is stored in the URL hash, for example
`#run=eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline`, so that an individual run can be
shared as a link. The page has to work without JavaScript too: render the newest pooled
summary's content statically and let the selector change the view only once the island has
loaded.

## The verdict bar

Immediately below the selector, per venue:
- the verdict as a word, with a colour and an icon to match (better, no detectable difference,
  worse)
- the mean difference and its 95 % interval
- the name of the main reference and the MAE of both
- the MDE sentence always included when the verdict is "no detectable difference"

The verdict is presented as it stands even when it goes against the model. Do not raise the
best window into the heading when the pooled result says otherwise.

## The charts

All with Observable Plot, in `src/charts/`, with the same island pattern as the current ones.
Each has a text alternative or a table view.

1. **Forecast vs. actual.** x = the day, y = visitors. The actual as a solid line, the model's
   p50 dashed, p10-p90 as a pale area. The references as thin lines, hidden by default,
   selectable. Public holidays as vertical lines.
2. **Error by horizon.** Grouped bars: MAE per horizon bucket (1-7, 8-14, 15-30), the model
   and the three references side by side. This shows where along the horizon the forecast
   falls apart.
3. **The difference against the reference with its confidence interval.** A dot and range
   chart: the mean difference d and its 95 % interval, with the zero line emphasised. This is
   the most important image on the page, because the verdict is read straight from it. In a
   sweep run, one row per window plus the pooled result at the bottom.
4. **The total for the period.** The forecast and the actual as bars, with the simulated 80 %
   interval included. If the run's `total.is_thin` or `total.is_drifted` is true, show a
   warning and say that the interval should not be read, but the difference and the bias
   separately.
5. **Calibration.** Coverage and its Clopper-Pearson interval, with a target line at 0.80.
6. **The three weather modes.** perfect, operational and climatology MAE as bars. Mark
   `perfect` clearly as an upper bound, not as a result.

## The tables

- The daily metrics: the model and the references as rows, MAE, RMSE, MASE, bias, pinball,
  coverage, sMAPE. sMAPE is flagged unreliable when the test period contains zero days.
- In a sweep run, the window table: the test period, the reference, the model's MAE, the
  reference's MAE, the mean difference, the interval, the verdict, the MDE.
- The worst days: the five largest errors, with the day, the weekday, the actual, the
  forecast, the error and a public holiday marking. Compute this from `predictions.csv` at
  build time.

## The explanatory texts

With each chart, one or two sentences about what is read from it. At the end of the page a
section "what cannot be concluded from this", summarising chapter 11 of `docs/EVALUATION.md`.
At least these three:
- a single window's result is descriptive, not probative
- "no detectable difference" does not mean equivalence, see the MDE
- the `perfect` weather figure is an upper bound, not an achieved result

# Bilingualism

All the texts into `src/i18n/ui/fi.ts` and `en.ts` with the current pattern. The verdict words
are translated, but `summary_fi` in `verdicts.json` is a finished Finnish paragraph: show it in
Finnish as it stands and write the English equivalent from the same structured fields; do not
translate the string in the browser.

A new link `/accuracy` in the navigation after the `/quality` link, in
`src/components/SiteNav.astro`.

# Technical constraints

- Follow the current patterns: `src/charts/base.ts`, `src/lib/colors.ts`, `src/lib/format.ts`,
  `Figure`, `TableScroll`, `Callout`, `client:visible`
- No new dependencies; Observable Plot is enough
- No runtime data fetching; everything is build-time
- Mobile at 375 px works, wide tables scroll inside their own container
- The colour scales work in greyscale and for red-green colour blindness. The verdict must not
  stand out by colour alone; include an icon or a word
- Avoid the em dash in body text

# Tests

- vitest: building `accuracy.json`, the pruning rules, the rounding, the empty state, the
  `schema_version` gate triggering
- vitest: computing the worst days on a known input
- Playwright: `/accuracy` and `/en/accuracy` load without console errors, the run selector
  changes the view, and a hash link opens the right run
- A schema test that fails if the structure of `verdicts.json` changes

# Acceptance criteria

With the current data (six runs: five monthly windows and one pooled summary):

1. The run selector lists six runs, the pooled summary first.
2. The pooled run `eval_v1_sweep_monthly_2026-04-01_2026-08-25_baseline` shows the verdict
   "worse than the reference" for both venues: venue 1 a mean difference of +60.0 (interval
   +3.1 … +124.4), venue 2 +17.1 (interval +3.7 … +32.7), and a window split of 1 in favour /
   4 against.
3. The April window shows venue 1 the verdict "no detectable difference", a mean difference of
   +6.7 (interval -3.2 … +30.7), an MDE of 34.5, i.e. 35.9 %, and venue 2 the verdict "worse",
   a mean difference of +20.4.
4. April's reference MAEs at venue 1: seasonal_naive 129.5, moving_average_28d 197.6,
   climatology_dow 96.2.
5. April's total at venue 1: forecast 13,639, actual 13,189, difference +3.4 %.
6. An empty `data/evaluations/` produces a working page with an empty state, not a failed
   build.
7. `accuracy.json` under 150 kB, the page weight under 500 kB.
8. npm run build, vitest and Playwright pass.
9. Update README.md's Part 2 section with the new page and its relationship to `/quality`.

# Do not do these

- Do not recompute the statistics in the browser; `verdicts.json` has already computed them
- Do not fail the build on missing evaluation data
- Do not present the `perfect` weather figure as a result
- Do not choose the best window for the heading when the pooled result goes against the model
- Do not leave out the MDE when the verdict is "no detectable difference"
- Do not add CDN scripts or new npm dependencies
- Do not translate the `summary_fi` paragraph in the browser; build the English equivalent
  from the fields
````

---

## Summary: what each part produces

| Part | Technology | Input | Output | Run |
| --- | --- | --- | --- | --- |
| 1. ingest | Python 3.12, pandas, requests | 3 external APIs + tickets.csv | `data/processed/*.csv` + a manifest | Daily, GitHub Actions |
| 3. forecast | Python 3.12, scikit-learn (+ Prophet optionally) | `data/processed/` | `data/forecasts/latest/` | Daily, after ingest |
| 2. web | Astro 5, TypeScript, Observable Plot | `data/processed/` + `data/forecasts/` | A static site | Built on push, Cloudflare Pages |
| 4. ticket tool | One HTML file, vanilla JS | The opening team's visitor statistics CSV (cp1252, semicolon) | `data/raw/tickets/venue_{id}/tickets.csv` | By hand, weekly |
| 5. evaluation | Python, extends part 3 | `data/processed/` + a chosen time window | `data/evaluations/{run_id}/` | By hand, at the pace of model development |
| 6. accuracy view | Astro, extends part 2 | `data/evaluations/` | The page `/accuracy` | Built on push |
