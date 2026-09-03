# Data model: APIs and data

*English translation. Finnish original: [`DATA_MODEL.md`](DATA_MODEL.md).*

This document describes the external APIs used by the Visitor Forecast repository, the
datasets stored on disk and their schemas. It is meant as the starting point for building a
new visualisation application on top of the existing visitor and weather data.

State at the time of writing: repository `oulu2026-visitor-flow-prediction-tool`, data
fetched from 2026-01-01 onwards, most recent observation 2026-05-22, most recent forecast run
2026-05-22.

All paths are relative to the `visitor_forecast/` directory unless stated otherwise.

---

## 1. The flow of data

```
External APIs                      Raw cache (disk)               Processed (disk)                  Forecasts
------------------------------------------------------------------------------------------------------------------
Jaskaretail IoT (REST)      ->  data/raw/iot_sensors/venue_N/  ->  data/processed/iot_sensors/  \
Open-Meteo (REST)           ->  data/raw/weather/venue_N/      ->  data/processed/weather/       >  venue_N_features.csv  ->  data/forecasts/venue_N/
Oulu traffic Eco-Counter    ->  data/raw/eco_counter/<site>/   ->  data/processed/eco_counter/  /   (the hourly main table)
  (GraphQL)                                                    ->  data/processed/eco_counter_sites/<site>/
Oulu traffic TPM (REST)     ->  data/raw/traffic/tpm/          ->  data/processed/traffic/      (no data on disk right now)
Ticket sales (manual)       ->  data/raw/tickets/venue_N/tickets.csv
Public holidays (maintained)->  config/holidays.csv
```

The key observation for visualisation: **`data/processed/venue_{id}_features.csv` is already
a finished, hourly combined table**, where visitors, tickets, calendar, Eco-Counter and
weather sit on the same row. A new application does not need to call a single API if reading
this file is enough for it (plus the forecast files, if it wants them).

---

## 2. External APIs

### 2.1 Jaskaretail IoT (visitor counting)

| Item | Value |
| --- | --- |
| URL | `https://oulu.jaskaretail.com:443/ext/sensor/visitor` |
| Method | POST, parameters in the query string |
| Authentication | HTTP Basic, `JASKARETAIL_BASIC_AUTH_USERNAME` / `_PASSWORD` from `.env.local` at the repository root |
| Module | `visitor_forecast/iot_sensors.py` |
| CLI | `scripts/01_fetch_iot_sensors.py --all-venues --days-back 7` |

Query parameters:

| Parameter | Example | Explanation |
| --- | --- | --- |
| `locationHierarchyIdList` | `178` | Comma-separated list. The per-venue `locationHierarchyId` from settings.json |
| `startDate` / `endDate` | `2026-05-01` | Inclusive window, `YYYY-MM-DD` |
| `interval` | `60min` | Defaults to `iot_sensors.default_interval` |
| `countingTypeId` | `in` or `out` | Fetched separately for both directions and merged |

Response: `{"result": [ { "categoryName": "01/05/2026 08:00:00", "locationId": 178, "visitors": 12 }, ... ]}`.
The timestamp field may be `categoryName`, `timestamp` or `date`; the format is
`%d/%m/%Y %H:%M:%S`. The numeric value is looked up under the keys `visitors`, `counts`,
`count`, `value` (including nested objects). Rows are summed to the `(timestamp, locationId)`
level, and the `in`/`out` fetches are merged into a single row.

### 2.2 Open-Meteo (weather)

| Item | Value |
| --- | --- |
| History | `https://archive-api.open-meteo.com/v1/archive` |
| Forecast | `https://api.open-meteo.com/v1/forecast` (at most 16 days) |
| Authentication | not needed |
| Time zone | `timezone=Europe/Helsinki`, i.e. **the timestamps are local time without zone information** |
| Module | `visitor_forecast/weather.py` |
| CLI | `scripts/02_weather_fetch_openmeteo.py --all-venues --days-back 30` |

The `hourly` parameters fetched: `temperature_2m`, `precipitation`, `wind_speed_10m`,
`relative_humidity_2m`, `weathercode`. The coordinates come from the venue definition.

Extra fields derived from the response (`weather.py`):

- `weathercode_str`: the textual equivalent of the WMO code, dictionary `WEATHER_CODES` (e.g. 0 `clear`, 3 `overcast`, 61 `slight_rain`, 71 `slight_snow_fall`, 95 `thunderstorm`)
- `is_precipitation`: `precipitation > 0`
- `is_cold`: `temperature_2m < 0`
- `is_windy`: `wind_speed_10m > 10`

The freshness limit for the forecast cache is 1 hour (`FORECAST_CACHE_TTL`), after which it
is fetched again.

### 2.3 Oulu traffic Eco-Counter (pedestrians and cyclists)

| Item | Value |
| --- | --- |
| URL | `https://api.oulunliikenne.fi/proxy/graphql` |
| Method | POST, GraphQL |
| Authentication | not needed |
| Module | `visitor_forecast/traffic.py` |
| CLI | `scripts/07_fetch_eco_counter.py --all-venues --days-back 7`, then `scripts/09_aggregate_eco_counter_by_site.py` |

The query is built per sensor (`_build_eco_counter_site_data_query`):

```graphql
query GetEcoCounterSiteData {
  ecoCounterSiteData(id: "karjasilta_1", domain: Oulu_Kapy, step: hour,
                     begin: "2026-05-01T00:00:00", end: "2026-05-22T00:00:00") {
    date
    counts
  }
}
```

`domain` and `step` are embedded as enums (validated with `^[A-Za-z_][A-Za-z0-9_]*$`), while
`id`, `begin` and `end` are strings. `step` is `hour` or `day`.

The sensor types and what they mean:

| Code | Type | Direction | Column name in the processed data |
| --- | --- | --- | --- |
| `JK_IN` | pedestrian | in | `jk_in_counts` |
| `JK_OUT` | pedestrian | out | `jk_out_counts` |
| `PP_IN` | cycling | in | `pp_in_counts` |
| `PP_OUT` | cycling | out | `pp_out_counts` |

**The timestamps in the response are in UTC** (`2026-05-22 04:00:00+00:00`), unlike the other
sources. See chapter 7.1.

### 2.4 Oulu traffic TPM (vehicle traffic)

| Item | Value |
| --- | --- |
| URL | `https://api.oulunliikenne.fi/tpm/v1` |
| Endpoints | `GET /stations`, `GET /stations/{station_id}/measurements?from=&to=&timeResolution=hour` |
| Module | `visitor_forecast/traffic.py`, function `fetch_tpm_data` |
| CLI | `scripts/06_fetch_tpm.py --venue-id 1 2 --days-back 7` |

Stations are filtered around the venue's coordinates by haversine distance
(`traffic.tpm.max_distance_km`, currently 2.0 km). The processed result would be
`data/processed/traffic/venue_{id}_tpm.csv` with the columns `timestamp, venue_id,
tpm_station_count, tpm_mean_count`.

**Note: there is currently no TPM data on disk.** The integration is in the code and in the
configuration, but the directories `data/raw/traffic/` and `data/processed/traffic/` do not
exist. A new visualisation application therefore cannot assume TPM data is available.

---

## 3. Configuration

Source: `visitor_forecast/config/settings.json`, validated with Pydantic
(`visitor_forecast/configuration.py`). A new application can read the same file directly as
JSON.

### 3.1 Venues

| venue_id | name | city | lat | lon | capacity | locationHierarchyId | tickets |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Pekuri | Oulu | 65.0134 | 25.4756 | 160 | 178 | `data/raw/tickets/venue_1/tickets.csv` |
| 2 | Kaupungintalo | Espoo | 60.2055 | 24.6558 | 20 | 183 | `data/raw/tickets/venue_2/tickets.csv` |

Note that venue 2's coordinates and city are Espoo, even though the name is Kaupungintalo.
The weather is fetched with these coordinates, so the weather data for venue 1 and venue 2
differ from each other.

### 3.2 Eco-Counter sites

One configured site:

```json
"raatti": {
  "name": "Karjasilta",
  "domain": "Oulu_Kapy",
  "sensors": { "JK_IN": "karjasilta_1", "JK_OUT": "karjasilta_2",
               "PP_IN": "karjasilta_4", "PP_OUT": "karjasilta_3" },
  "venue_ids": [1, 2]
}
```

The site key is `raatti`, but the display name is `Karjasilta`. The site is attached to
**both** venues, so the Eco-Counter figures are identical for venue 1 and venue 2.

### 3.3 The other settings groups

`forecast_horizon_days: 30`, `retrain_frequency_days: 7`, `web.port: 2026`,
`targets.visitors` (hourly, metrics `visitors_in`, `visitors_out`, `total_visitors`),
`targets.tickets` (daily, metric `tickets_sold`).

---

## 4. Entities and schemas

### 4.1 Hourly visitor observation (IoT)

Raw: `data/raw/iot_sensors/venue_{id}/YYYY-MM-DD.csv`, one file per day, 142 files per venue
(2026-01-01 - 2026-05-22).

| Column | Type | Explanation |
| --- | --- | --- |
| `timestamp` | naive datetime | Start of the hour, local time |
| `locationId` | int | The same as the venue's `locationHierarchyId` |
| `visitors_in` | float | Counted in |
| `visitors_out` | float | Counted out |
| `total_visitors` | float | `visitors_in + visitors_out` |

Merged: `data/processed/iot_sensors/venue_{id}_iot.csv`, columns `timestamp, visitors_in,
visitors_out, total_visitors`, 3408 rows.

Note that `total_visitors` is the **sum of entries and exits**, not a net visitor count and
not a count of unique visitors. A rough visitor estimate is `total_visitors / 2`.

### 4.2 Hourly weather

Raw: `data/raw/weather/venue_{id}/YYYY-MM-DD.csv`, 148 files per venue (2026-01-01 -
2026-05-28; the last days are the forecast cache).

| Column | Type | Explanation |
| --- | --- | --- |
| `timestamp` | naive datetime | Local time (Europe/Helsinki) |
| `temperature_2m` | float | Celsius |
| `precipitation` | float | mm in that hour |
| `wind_speed_10m` | float | km/h |
| `relative_humidity_2m` | int | % |
| `weathercode` | int | WMO code |
| `weathercode_str` | string | Textual equivalent |
| `is_precipitation` | bool | As the string `True`/`False` in the CSV |
| `is_cold` | bool | |
| `is_windy` | bool | |

Merged: `data/processed/weather/venue_{id}_weather.csv`. **Warning: this file holds only the
most recent fetch window**, currently 168 rows (2026-05-22 - 2026-05-28). The full weather
history is in the per-day raw files and in `venue_{id}_features.csv`.

### 4.3 Eco-Counter, site level

Raw and processed, both hourly:

- `data/raw/eco_counter/raatti/YYYY-MM-DD.csv` (142 files)
- `data/processed/eco_counter_sites/raatti/YYYY-MM-DD.csv` (142 files)

| Column | Type | Explanation |
| --- | --- | --- |
| `date` | tz-aware datetime (UTC) | The column is named `date`, but the value is an hour |
| `jk_in_counts` | float | Pedestrians in |
| `jk_out_counts` | float | Pedestrians out |
| `pp_in_counts` | float | Cyclists in |
| `pp_out_counts` | float | Cyclists out |

The per-venue combination: `data/processed/eco_counter/venue_{id}_eco.csv`, 3381 rows,
columns `date, counts (JK_IN), counts (JK_OUT), counts (PP_IN), counts (PP_OUT)`. The column
names in brackets are normalised in the current dashboard into the form `JK_IN` and so on
(`app/utils/data_loader.py: load_eco_counter`).

Coverage 2026-01-01 - 2026-05-22, in total 21,552 JK_IN and 53,355 PP_IN observations at
venue 1.

### 4.4 Ticket sales (daily)

`data/raw/tickets/venue_{id}/tickets.csv`, maintained by hand every week.

| Column in the file | Normalised name | Explanation |
| --- | --- | --- |
| `DATE` | `date` | Format `d.m.YYYY`, e.g. `14.1.2026` |
| `TICKETS` | `tickets_sold` | Single tickets |
| `GROUPS` | `groups_sold` | Group tickets |
| `TOTAL` | `tickets_total` | Total |

Column name detection is alias-based and tolerates Scandinavian characters (`liput`,
`ryhmat`, `yhteensa`, `pvm`). Coverage: venue 1 2026-01-14 - 2026-05-17 (124 rows), venue 2
2026-01-13 - 2026-05-17 (125 rows). Ticket sales therefore end five days before the visitor
data does.

### 4.5 Public holidays

`config/holidays.csv`, 16 rows, the year 2026.

| Column | Explanation |
| --- | --- |
| `date` | `YYYY-MM-DD` |
| `holiday_name` | The Finnish name, e.g. `Uudenvuodenpäivä` |
| `is_weekend` | 0/1 |
| `is_last_workday_before_holiday` | 0/1 |
| `type` | `national` or `religious` |
| `country` | `Finland` |

### 4.6 The hourly feature table (the main table)

`data/processed/venue_{id}_features.csv`, 3408 rows per venue, 59 columns, 2026-01-01 00:00 -
2026-05-22 23:00, a dense hourly series without gaps.
`data/processed/combined_features.csv` holds both venues (6816 rows).

The columns by group:

**Keys and dimensions**

| Column | Explanation |
| --- | --- |
| `timestamp` | Start of the hour, naive, local time |
| `date` | The day (00:00) |
| `venue_id`, `venue_name`, `location_city` | 1/Pekuri/Oulu or 2/Kaupungintalo/Espoo |
| `hour` | 0-23 |

**Visitors**

| Column | Explanation |
| --- | --- |
| `visitors_in`, `visitors_out`, `total_visitors` | The hour's observations |
| `daily_visitors_in`, `daily_visitors_out`, `daily_total_visitors` | That day's sums, repeated on every hour |
| `visitors_lag_1d`, `visitors_lag_7d` | The sum for the previous day and for the day a week earlier |
| `visitors_7d_avg`, `visitors_30d_avg` | Rolling means at the daily level |

**Tickets**

| Column | Explanation |
| --- | --- |
| `daily_tickets_sold`, `daily_groups_sold`, `daily_tickets_total` | The day's ticket figures repeated across the hours. **NaN for days with no ticket data** |
| `tickets_lag_1d`, `tickets_lag_7d`, `tickets_7d_avg`, `tickets_30d_avg` | History features, NaN outside the observation period |
| `visitor_to_ticket_ratio` | `total_visitors / daily_tickets_sold`, NaN when there is no ticket data |

**Capacity**

`capacity` (a venue constant), `venue_capacity_utilization` (`total_visitors / capacity`),
`daily_capacity_utilization` (`daily_total_visitors / capacity`).

**Eco-Counter and the derived flows**

| Column | Explanation |
| --- | --- |
| `jk_in_counts`, `jk_out_counts`, `pp_in_counts`, `pp_out_counts` | The raw counters |
| `pedestrian_net_flow` | `jk_in - jk_out` |
| `bicycle_net_flow` | `pp_in - pp_out` |
| `pedestrian_total_flow`, `bicycle_total_flow` | The sums of the directions |
| `total_site_flow` | Everything together |
| `pedestrian_ratio`, `bicycle_ratio` | Shares of the total flow, 0 when the denominator is 0 |
| `pedestrian_net_flow_lag_1d`, `bicycle_net_flow_lag_1d` | Shifted 24 rows (hours) back |

**Calendar**

`holiday_name` (NaN on ordinary days), `day_of_week` (0 = Monday), `is_weekend`, `is_holiday`,
`days_before_next_holiday` (999 when unknown), `is_last_workday_before_holiday`, `month`,
`year`, `day_of_month`, `week_of_year`.

**Weather**

`temperature_2m`, `precipitation`, `wind_speed_10m`, `relative_humidity_2m`, `weathercode`,
`weathercode_str`, `is_precipitation`, `is_cold`, `is_windy`. Coverage is 100 % across the
whole period at both venues.

### 4.7 Forecast files

Directory `data/forecasts/venue_{id}/`, with the run date `YYYYMMDD` in the file names. The
newest run is 20260522, the previous one 20260520. The horizon is 7 days.

| File | Rows | Columns |
| --- | --- | --- |
| `forecast_visitors_{date}.csv` | 168 (7 days x 24 h) | `timestamp, venue_id, forecast_visitors_in, forecast_visitors_out, forecast_total_visitors`, the weather variables, `lower_bound, upper_bound` |
| `forecast_visitors_daily_{date}.csv` | 7 | `date, venue_id, forecast_visitors_in, forecast_visitors_out, forecast_total_visitors, lower_bound, upper_bound` |
| `forecast_tickets_{date}.csv` | 7 | `date, venue_id, forecast_tickets_sold, lower_bound, upper_bound` |
| `forecast_*_components.csv` | 504 | Prophet's components: `ds, trend, weekly, yearly, daily, hourly_pattern, holidays`, per-holiday columns, per-regressor effects, `yhat, timestamp, metric` |
| `forecast_*_feature_importance.csv` | 126 | `metric, feature, importance` (the XGBoost residual model) |

Models: `models/venue_{id}/prophet_{target}.pkl` and
`models/venue_{id}/xgb_{target}_residuals.pkl`, with the targets `visitors` and `tickets`.

### 4.8 The legacy file

`data/processed/features.csv` is an old daily dataset from 2024 (161 rows, columns `date,
visitors, holiday_name, ...`). It has nothing to do with the current pipeline. **Do not use
it in a new application.**

---

## 5. File map and coverage

| Path | Level | Rows or files | Date range |
| --- | --- | --- | --- |
| `data/processed/venue_1_features.csv` | hourly | 3408 rows | 2026-01-01 - 2026-05-22 |
| `data/processed/venue_2_features.csv` | hourly | 3408 rows | 2026-01-01 - 2026-05-22 |
| `data/processed/combined_features.csv` | hourly | 6816 rows | 2026-01-01 - 2026-05-22 |
| `data/processed/iot_sensors/venue_N_iot.csv` | hourly | 3408 rows | 2026-01-01 - 2026-05-22 |
| `data/processed/weather/venue_N_weather.csv` | hourly | 168 rows | 2026-05-22 - 2026-05-28 |
| `data/raw/weather/venue_N/*.csv` | hourly | 148 files | 2026-01-01 - 2026-05-28 |
| `data/processed/eco_counter/venue_N_eco.csv` | hourly | 3381 rows | 2026-01-01 - 2026-05-22 |
| `data/processed/eco_counter_sites/raatti/*.csv` | hourly | 142 files | 2026-01-01 - 2026-05-22 |
| `data/raw/tickets/venue_N/tickets.csv` | daily | 124 - 125 rows | 2026-01-13 - 2026-05-17 |
| `config/holidays.csv` | daily | 16 rows | 2026 |
| `data/forecasts/venue_N/` | hourly and daily | 14 files | 2026-05-23 - 2026-05-29 |

Volumes: venue 1 in total 63,865 visitor events (maximum 258 per hour), venue 2 in total
23,505 (maximum 152). Tickets sold, venue 1: 7745, venue 2: 6546.

---

## 6. How the data is joined

1. **Visitors and weather**: joined on `timestamp`, both hourly and in local time. This join
   has already been made into `venue_{id}_features.csv`.
2. **Visitors and tickets**: joined on `(date, venue_id)`. The ticket figures are repeated
   across every hour of the day with the prefix `daily_`.
3. **Visitors and Eco-Counter**: joined on `timestamp` after the Eco-Counter's `date` has
   been converted. See the time zone warning below.
4. **Calendar**: joined on `date` from `config/holidays.csv`.
5. **Daily level**: sum `total_visitors`, `visitors_in`, `visitors_out`; average the
   temperature, wind and humidity; sum the precipitation; take `weathercode` as the mode. The
   same logic as `weather.aggregate_weather_daily`.

---

## 7. Pitfalls

### 7.1 The time zones are not consistent

- IoT, weather and the feature table: **naive datetime, local time** (Europe/Helsinki)
- Eco-Counter: **tz-aware UTC** (`+00:00`)

In `data_pipeline.load_site_eco_counter_data`, the Eco-Counter timestamp is converted with
`pd.to_datetime(..., utc=True).dt.tz_localize(None)`, which keeps the UTC clock time and
drops the zone marking. In practice the Eco-Counter figures are joined into the feature table
2-3 hours off from the correct hour compared with the visitor and weather data. This is worth
checking and fixing in a new application: move the Eco-Counter to Helsinki time before the
join.

### 7.2 The Eco-Counter data is shared between the venues

The site `raatti` is attached to both venues, so the `jk_*` and `pp_*` columns are identical
for venue 1 and venue 2. They cannot be presented as per-venue pedestrian traffic. This is
the Karjasilta measuring point in Oulu, which has nothing to do with venue 2 (Espoo).

### 7.3 Zero hours

58.6 % of venue 1's and 62.6 % of venue 2's hours are zeros. Some are genuine hours outside
opening times, some come from the densification done by `_normalize_iot_frame`
(`reindex(full_range, fill_value=0.0)`), which fills missing hours with zeros. **Missing data
and a genuine zero cannot be told apart.** The first day on which venue 1 has visitors is
2026-01-22 and venue 2 2026-01-08, even though the series starts on 01-01.

### 7.4 NaN vs. zero in the ticket data

`daily_tickets_sold` is NaN on days with no ticket data (before 01-14 and after 05-17), and
zero on days inside the observation period with no sales. The difference is intentional; do
not fill the NaN values with zeros in a visualisation.

### 7.5 The processed weather file is incomplete

`data/processed/weather/venue_{id}_weather.csv` holds only the most recent fetch window.
Historical weather has to be read either from `venue_{id}_features.csv` or from the per-day
files `data/raw/weather/venue_{id}/*.csv`.

### 7.6 The forecast's in, out and total do not add up

`forecast_visitors_in`, `forecast_visitors_out` and `forecast_total_visitors` are forecast
with separate models, so `in + out != total`. For example on 2026-05-23: in 63.99, out 52.12,
total 191.31. Present them as parallel series, not stacked.

### 7.7 The dataset is small and immature

Four and a half months of data, one measuring point for the traffic data, and venue 2 is in
another city. The forecast confidence intervals are wide (e.g. a daily forecast of 29
visitors, interval 0 - 502). A visualisation should emphasise the observed data and present
the forecast with reservations.

---

## 8. Starting points for a new visualisation application

### 8.1 The recommended data source

The simplest path: read `data/processed/combined_features.csv` (2.2 MB, 6816 rows, 59
columns) and optionally the newest forecast files. All the visitor, weather, ticket, calendar
and traffic data is already joined. No API calls are needed.

If the application is to be static (no Python backend), preprocess the CSV into a smaller
JSON bundle: cut the columns down to the roughly 15 relevant ones and round the floats. The
result is roughly 400-600 kB, which fits effortlessly into one HTML file or a static build.

### 8.2 The columns that suffice for visualisation

`timestamp`, `date`, `hour`, `venue_id`, `venue_name`, `total_visitors`, `visitors_in`,
`visitors_out`, `daily_total_visitors`, `daily_tickets_sold`, `capacity`,
`venue_capacity_utilization`, `temperature_2m`, `precipitation`, `wind_speed_10m`,
`weathercode_str`, `is_precipitation`, `is_holiday`, `is_weekend`, `holiday_name`,
`day_of_week`, `total_site_flow`.

### 8.3 Views the data supports

| View | Data |
| --- | --- |
| Visitor count over time, hourly or daily, venues side by side | `total_visitors` as a time series |
| Weather and visitors on the same axis | `total_visitors` as bars, `temperature_2m` as a line, rainy hours highlighted |
| Weekday x hour heatmap | `day_of_week` x `hour`, with the mean of `total_visitors` as the value |
| The effect of the weather | Scatter plot of `temperature_2m` vs. the day's visitors, coloured by `weathercode_str` |
| The effect of rain | A comparison of `is_precipitation` True vs. False, mean visitors per hour |
| Capacity utilisation | `venue_capacity_utilization` over time, with a 100 % threshold |
| Tickets vs. visitors | Daily level, `daily_tickets_sold` and `daily_total_visitors` |
| The effect of public holidays | `is_holiday` and `holiday_name` as markers on the time series |
| Pedestrians and cyclists | `total_site_flow`, mind chapters 7.1 and 7.2 |
| Forecast vs. history | History from `venue_N_features.csv`, forecast from `forecast_visitors_*.csv` with its confidence intervals |

### 8.4 Technical constraints

- No database, all the data is in files
- The current dashboard is Flask + Plotly on port 2026 (`app/`) and reads the same files
- A new application can be entirely separate; it writes nothing into the repository's data
- Boolean values are the strings `True`/`False` in the CSV
- The decimal separator is a dot, the encoding UTF-8, with Scandinavian characters in column
  values (`holiday_name`; `weathercode_str` has none)
