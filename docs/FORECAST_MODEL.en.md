# The forecast models

*English translation. Finnish original: [`FORECAST_MODEL.md`](FORECAST_MODEL.md).*

This document describes the two models of the `packages/forecast` part: their structure,
their features, their strengths, their weaknesses and when the forecast should not be
believed.

It builds on chapter 8 of `FRAMEWORK_PLAN.md`, but **every figure presented here is
measured**, not estimated. They were produced by the run

```bash
python -m ovf_forecast run
```

on data whose most recent observed day is **2026-05-22**. The figures are refreshed on every
run into `data/forecasts/latest/venue_{id}/metrics.json`; this document is a snapshot of the
version run on 2026-08-24.

---

## 1. Summary: which one wins

| Venue | Model | MAE 1-7 days | Beats seasonal_naive | Beats moving_average_28d |
| --- | --- | --- | --- | --- |
| 1 Pekuri | **baseline** | **178.5** | yes (214.9) | yes (192.4) |
| 1 Pekuri | prophet_xgb | 198.7 | yes (214.9) | **no** (192.4) |
| 2 Kaupungintalo | **baseline** | 90.1 | yes (100.6) | yes (92.5) |
| 2 Kaupungintalo | prophet_xgb | **87.1** | yes (100.6) | yes (92.5) |

**The production model is `baseline`.** It is the only model that beats both references at
both venues and in all three horizon buckets.

`prophet_xgb` is slightly more accurate at venue 2 (87.1 vs. 90.1, a 3 % difference) but
clearly worse at venue 1 (198.7 vs. 178.5, an 11 % difference). The switching criterion in
chapter 8.1 of the plan is "more than 10 % lower MAE on three consecutive runs". That is not
met, so the simple model stays.

**A warning about honesty.** Every model's MAE is large relative to the level: an average day
at venue 1 is about 450 visitors and the best MAE is 178, i.e. about 40 % of the level. sMAPE
at venue 2 is 55-58 %. These forecasts describe the weekly rhythm and the rough level, not
the visitor count of an individual day. See chapter 7.

---

## 2. The shared structure

Both models forecast at the **daily level**. The hourly level and the uncertainty come from
shared components. This is a deliberate design choice for two reasons: the models are
comparable, and the sum of the hourly forecasts is exactly the daily forecast.

```
data/processed/  ->  dataset.build()  ->  features.build_daily()  ->  model  ->  p50 at the daily level
                                                                  \
                                      profile.build()  ------------>  hourly profile  ->  hourly p50
                                                                  \
                                      backtest.run()  ------------>  relative errors  ->  p10 / p90
```

The shared interface:

```python
class ForecastModel(Protocol):
    name: str
    def fit(self, daily: pd.DataFrame) -> None: ...
    def predict(self, future: pd.DataFrame) -> pd.Series: ...
```

`visitors_in` and `visitors_out` are **not forecast separately**. In the current application
they are three separate models, which is why 2026-05-23 reads in 63.99, out 52.12 and total
191.31, and they do not add up. Here only `visitors_total` is forecast.

---

## 3. The baseline model `baseline`

### 3.1 Layer 1: the daily level

`sklearn.ensemble.HistGradientBoostingRegressor(loss="poisson")`, targeting
`visitors_total` at the daily level, per venue.

The Poisson loss was chosen because the target is a count: the distribution is right-skewed
and the forecast has to be non-negative. Poisson guarantees positivity structurally, without
clipping to zero afterwards and without the back-transformation bias of a log transform.

The hyperparameters (`models/baseline.py`): `learning_rate=0.05`, `max_iter=400`,
`max_depth=4`, `max_leaf_nodes=15`, `min_samples_leaf=8`, `l2_regularization=1.0`,
`early_stopping=False`, `random_state=20260101`.

`early_stopping` is off, because a random validation set carved out of a 120-row time series
would be both small and wrongly constructed. Model selection is done with a rolling origin
backtest, not with an internal split.

The hyperparameters are deliberately modest. Five different combinations were measured with
the backtest, and the MAE moved between 172.7-189.2 at venue 1 and 90.1-95.1 at venue 2. The
difference is smaller than the noise level of an eight-origin backtest, so tuning further
would be overfitting the hyperparameters to the backtest.

#### Features

| Group | Features |
| --- | --- |
| Calendar | `day_of_week` (categorical), `is_weekend`, `is_holiday`, `days_before_next_holiday` (clipped to 14), `is_last_workday_before_holiday`, `month`, `week_of_year` |
| Season | `sin(2πd/365)`, `cos(2πd/365)`, `sin(4πd/365)`, `cos(4πd/365)` |
| Trend | `days_since_start` |
| Weather | `temp_mean`, `temp_max`, `precip_sum`, `precip_hours`, `wind_mean`, `is_rainy_day`, `weather_group` (categorical: clear/cloudy/rain/snow/other) |
| Level | `level_7d`, `level_28d`, `dow_index_28d` |

Ticket data is not used as a feature, because it is not available for the future.

#### A critical design choice: no autoregressive lags

The model has **no lag features that would update as the forecast advances**.

- **In training**, `level_7d` and `level_28d` are causal rolling means: the row for day *t*
  sees the days *t-7…t-1*, never its own day.
- **When forecasting**, they are computed once at the origin and stay constant across the
  whole 30-day horizon.

The current application feeds its own forecasts back into the `lag_24h` and `lag_168h`
features (`modeling.py`, `history_values.append(final_prediction)`), which makes the error
accumulate as the horizon lengthens. Here a 30-day forecast is **not a one-day forecast
chained 30 times**, but a single forecast made from the origin.

`dow_index_28d` is the only level feature that varies inside the horizon: it is the ratio of
that weekday's mean to the 28-day mean, so it follows the weekday of the target day.

This is tested:
`test_features.py::test_future_features_ignore_observations_after_the_origin` corrupts every
observation after the origin and requires that no feature changes.

#### Removing the leading zeros

Venue 1 reports nothing before 2026-01-22 and venue 2 before 2026-01-08. This is an
uninstalled sensor, not an empty museum. The zeros of these days are dropped before training
(`dataset.venue_history`), because otherwise they would drag all the level features
downwards. That leaves 121 training days for venue 1 and 135 for venue 2.

#### Measured feature importances

Permutation importance, on the MAE scale, over the whole training set:

| Venue | The three most important | In practice useless |
| --- | --- | --- |
| 1 Pekuri | `day_of_week` 136.6 · `level_7d` 48.8 · `wind_mean` 27.1 | `month`, `is_holiday`, `is_last_workday_before_holiday`, `is_rainy_day` |
| 2 Kaupungintalo | `level_28d` 49.2 · `day_of_week` 44.4 · `year_sin` 37.3 | `is_holiday`, `is_last_workday_before_holiday`, `is_rainy_day` |

Worth noting: **the weekday and the level carry almost all of the signal.** Weather is third
most important, but `wind_mean` rises above `temp_mean`, which is suspicious — windiness in
Oulu correlates with the season, so the feature is probably acting as a seasonal proxy rather
than as a mechanism. `is_holiday` produces nothing, because the dataset contains only a
handful of public holidays.

### 3.2 Layer 2: the hourly profile (shared by both models)

`profile.py`. The daily forecast is split across the hours with an empirical profile:

```
share[venue][dow][hour] = the mean of the shares visitors_hour / visitors_day
                          over the days where visitors_day > 0, the last 8 weeks
```

Shrunk towards the profile shared by all weekdays, `k = 4`:

```
share_final = (n_dow * share_dow + k * share_all) / (n_dow + k)
```

Eight weeks gives only eight observations per weekday, so a single unusual Saturday would
dominate without the shrinkage.

**Opening hours are derived from the data**: an hour is treated as closed if its non-zero
share over the last 8 weeks is below 5 %. The shares of those hours are forced to zero before
normalisation. The measured opening hours:

| Venue | Open (local time) |
| --- | --- |
| 1 Pekuri | 07-19 |
| 2 Kaupungintalo | 07-21 |

Finally the shares are normalised so that the day's shares sum to exactly 1, which makes
`hourly forecast = daily_p50 * share_final` add up exactly to the daily forecast.

**Daylight saving time.** A local day has 23 or 25 hours on the transition days. The shares
are normalised over the set of hours the day actually has, so the sum is 1 on those two days
of the year as well.

The invariant is tested against the exported files rather than against in-memory numbers
(`test_cli.py::test_hourly_forecasts_sum_to_the_daily_forecast`). Rounding uses the largest
remainder method, so the sum also matches at the three-decimal precision of the CSV.

### 3.3 Layer 3: uncertainty (shared by both models)

`intervals.py`. The prediction intervals come from **the measured backtest error**, not from
the model's internal assumptions.

1. A rolling origin backtest (chapter 5).
2. The relative error `r = y_true / y_pred` for every (origin, horizon) pair.
3. The q10 and q90 quantiles of the `r` distribution per horizon bucket: 1-7, 8-14, 15-30.
4. `p10 = p50 * q10(h)`, `p90 = p50 * q90(h)`.

The relative formulation is deliberate: the spread of the error scales with the level. An
absolute error distribution would give quiet days intervals that are too wide and busy days
intervals that are too narrow. At the hourly level the same relative width is used as at the
daily level.

Two safeguards:

- Rows where `y_pred < 1.0` are left out of the quantile calculation. Dividing by zero would
  say more about how small the forecast is than about the model's spread.
- The median has to be inside its own interval: `q10 ≤ 1 ≤ q90` is enforced. Systematic bias
  is reported by the `bias` metric; it has no business producing a `p10 > p50` row in a file.

#### The measured interval factors

| Venue | Model | 1-7 | 8-14 | 15-30 |
| --- | --- | --- | --- | --- |
| 1 | baseline | 0.52 - 1.76 | 0.55 - 1.71 | 0.50 - 1.50 |
| 1 | prophet_xgb | 0.51 - 1.37 | 0.57 - 1.40 | 0.58 - 1.68 |
| 2 | baseline | 0.32 - 2.16 | 0.36 - 1.96 | 0.32 - 2.27 |
| 2 | prophet_xgb | 0.28 - 1.91 | 0.35 - 1.58 | 0.24 - 1.98 |

**These intervals are wide.** A forecast of 150 visitors at venue 2 means an interval of
47-324. That is an honest description of what 4.5 months of data can say, but it also means
the forecast cannot be used for precise resourcing.

Note that the daily interval is computed **at the daily level**, not as the sum of 24 hourly
intervals. In the current application that summation produces absurd intervals, for example a
forecast of 29 visitors with an interval of 0-502.

---

## 4. The comparison model `prophet_xgb`

### 4.1 Structure

1. **Prophet** on the daily target: trend + weekly seasonality + yearly seasonality + public
   holidays + weather regressors (`temp_mean`, `precip_sum`, `wind_mean`).
2. **XGBoost** on Prophet's **residuals**, with the same calendar and weather features as the
   baseline model.
3. The final forecast is `prophet_yhat + xgb_residual`, clipped at zero.
4. The hourly level and the uncertainty come from the same shared layers 2 and 3.

Prophet's own `yhat_lower` and `yhat_upper` values are **not used**: they contain none of the
uncertainty of the XGBoost stage.

### 4.2 The yearly seasonality component: a measured problem and its solution

The plan defines yearly seasonality as part of the model. In 4.5 months of data, however,
yearly seasonality cannot be identified, and forced on it destroys the forecast.

Measured at venue 1, origin 2026-04-24:

| Yearly seasonality | Prophet's `yearly` component for day 30 | MAE 15-30 days |
| --- | --- | --- |
| Forced on (fourier 3) | **+742 visitors** | **774.0** |
| Off | no component | **179.9** |

The component fits noise inside the training window and extrapolates it straight out. The
forecast for day 30 was 1231 visitors, when the realised level was about 457.

**The solution**: the model asks for yearly seasonality but keeps Prophet's own `auto` rule,
which switches yearly seasonality off with less than two years of history
(`MIN_YEARLY_SEASONALITY_DAYS = 730`). When the rule triggers, the run logs it explicitly.
With two years of data the component switches itself on.

For the same reason the Fourier order is 3 (Prophet's default is 10) and
`seasonality_prior_scale` is 5.0 (default 10.0). Both were tightened precisely because of
overfitting.

### 4.3 What is not repeated from the current implementation

| Current | Here | Why |
| --- | --- | --- |
| Hourly Prophet, `daily_seasonality=True` **and** a custom `hourly_pattern` with `period=1` | Daily Prophet, hourly level from the profile | Two overlapping daily seasonalities are collinear and make the components uninterpretable |
| Prediction interval: Prophet's interval + the point residual | Empirical backtest quantiles | Prophet's interval does not include XGBoost's uncertainty |
| Daily interval = the **sum** of 24 hourly intervals | The interval is computed at the daily level | Summation produces absurd intervals, e.g. 29 visitors with an interval of 0-502 |
| `in`, `out` and `total` as separate models | One model for `total` | Separate models do not add up |
| Forecasts fed back into lag features | No recursion | The error accumulates as the horizon lengthens |
| A single 80/20 time split | A rolling origin backtest | One split gives one observation about model quality |
| Median imputation for missing features | NaN supported natively | Median imputation mixes January and May |

### 4.4 Installation

`prophet_xgb` requires a separate dependency group, because Prophet drags cmdstan along with
it:

```bash
pip install -e ".[prophet]"
```

macOS additionally needs the OpenMP runtime library for XGBoost:

```bash
brew install libomp
```

**If the group is not installed, `prophet_xgb` is skipped with a clear warning and the run
does not fail.** The skip also covers the case where xgboost is installed but does not load
(a missing libomp): to the caller both mean the same thing. Skipped models are recorded in
the manifest's `skipped_models` field.

---

## 5. Validation

### 5.1 The rolling origin backtest

```
origin o = the most recent observed day minus (n * 7 days),  n = 1..N
training = all data <= o
forecast = o+1 .. o+30
```

Requirement: at least 60 days of training data per origin. With this data that is the binding
constraint, not `max_origins`:

| Venue | Training days | Origins | Backtest window |
| --- | --- | --- | --- |
| 1 Pekuri | 121 | 8 | 2026-03-28 … 2026-05-22 |
| 2 Kaupungintalo | 135 | 10 | 2026-03-14 … 2026-05-22 |

The plan expected about 12 origins; removing the leading zeros takes three weeks off the
start for venue 1, so there are eight origins. That is the plan's minimum, not its target.

Two details keep the exercise honest:

1. **Training stops at the origin**, including for the level features and the hourly profile.
2. **The weather degrades to climatology after day 16 in the backtest as well**, exactly as in
   production. The long-horizon figures are therefore measured with the same smoothed weather
   they are run with.

One known optimism remains: at horizons 1-16 the backtest uses the **realised** weather, while
production uses a **weather forecast**. The weather forecast's own error therefore does not
appear in the measured figures.

### 5.2 Coverage is measured leaving one origin out at a time

The `p10`/`p90` in `backtest.csv` and in the `coverage_80` metric are computed with quantiles
fitted **without the origin they are scoring**. If the intervals were fitted on the same rows
they measure, coverage would be 80 % by definition and would say nothing. The production
forecast's intervals use every origin. `metrics.json` records this in the `coverage_method`
field.

### 5.3 The measured metrics

#### Venue 1, Pekuri — origin 2026-05-22, 121 training days, 8 origins

| Model | Horizon | MAE | RMSE | sMAPE | Bias | Coverage 80 % | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **baseline** | 1-7 | **178.5** | 227.5 | 38.3 | +42.8 | 0.75 | 56 |
| **baseline** | 8-14 | 176.2 | 221.8 | 36.7 | +29.6 | 0.71 | 49 |
| **baseline** | 15-30 | **178.9** | 222.6 | 37.0 | +72.6 | 0.76 | 85 |
| prophet_xgb | 1-7 | 198.7 | 250.9 | 40.6 | +83.4 | 0.77 | 56 |
| prophet_xgb | 8-14 | **167.2** | 220.9 | 34.7 | +43.2 | 0.73 | 49 |
| prophet_xgb | 15-30 | 179.9 | 232.6 | 37.3 | +32.4 | 0.76 | 85 |
| seasonal_naive | 1-7 | 214.9 | 279.2 | 43.2 | +38.6 | 0.79 | 56 |
| seasonal_naive | 8-14 | 197.4 | 263.6 | 39.4 | +12.8 | 0.78 | 49 |
| seasonal_naive | 15-30 | 179.2 | 234.0 | 36.7 | +17.8 | 0.74 | 85 |
| moving_average_28d | 1-7 | 192.4 | 225.6 | 40.8 | +45.7 | 0.75 | 56 |
| moving_average_28d | 8-14 | 194.0 | 229.8 | 41.3 | +43.8 | 0.76 | 49 |
| moving_average_28d | 15-30 | 211.0 | 240.7 | 44.1 | +54.2 | 0.81 | 85 |

#### Venue 2, Kaupungintalo — origin 2026-05-22, 135 training days, 10 origins

| Model | Horizon | MAE | RMSE | sMAPE | Bias | Coverage 80 % | n |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 1-7 | 90.1 | 119.5 | 57.9 | +7.2 | 0.77 | 70 |
| baseline | 8-14 | 83.6 | 109.9 | 55.5 | +10.7 | 0.79 | 63 |
| baseline | 15-30 | 84.3 | 114.1 | 56.7 | +15.6 | 0.77 | 117 |
| **prophet_xgb** | 1-7 | **87.1** | 114.0 | 64.5 | +14.7 | 0.71 | 70 |
| **prophet_xgb** | 8-14 | **77.8** | 101.6 | 62.4 | +8.3 | 0.71 | 63 |
| **prophet_xgb** | 15-30 | **79.7** | 108.2 | 66.6 | -4.9 | 0.68 | 117 |
| seasonal_naive | 1-7 | 100.6 | 128.4 | 69.8 | -2.7 | 0.74 | 70 |
| seasonal_naive | 8-14 | 99.6 | 136.8 | 66.7 | +0.9 | 0.73 | 63 |
| seasonal_naive | 15-30 | 107.0 | 139.3 | 72.4 | +13.2 | 0.77 | 117 |
| moving_average_28d | 1-7 | 92.5 | 116.0 | 61.4 | -2.5 | 0.77 | 70 |
| moving_average_28d | 8-14 | 91.5 | 114.2 | 61.8 | +1.5 | 0.76 | 63 |
| moving_average_28d | 15-30 | 87.3 | 107.5 | 61.1 | +22.7 | 0.77 | 117 |

### 5.4 What has to be read from these figures

**The references are close.** `moving_average_28d` — a plain 28-day mean — is only 8 % worse
than the baseline model at venue 1 at horizon 1-7 and 3 % worse at venue 2. The baseline wins,
but not crushingly. Most of the model's value is in the weekday rhythm, which
`moving_average` ignores entirely.

**Every model overestimates.** The bias is positive almost everywhere, at venue 1 as much as
+72.6 at horizon 15-30. The reason is structural: the visitor count falls from January's daily
mean of 653 to May's 484, and a level frozen at the origin does not follow it down. Nor does a
tree model extrapolate a trend: `days_since_start` saturates at its last training value.

**seasonal_naive wins at the long horizon at venue 1.** At horizon 15-30 it is 179.2 while the
baseline is 178.9 — in practice a tie. Three weeks out, "the same weekday as last observed" is
as good as gradient boosting.

**prophet_xgb is inconsistent.** It is venue 2's best model at every horizon and venue 1's
worst at the near horizon. With two venues and eight origins it is not possible to say which
observation is signal.

### 5.5 The evaluation framework: arbitrary windows and a statistical verdict

The backtest of chapter 5.1 measures the model at rolling origins and produces the production
prediction intervals. Alongside it there is `python -m ovf_forecast evaluate`, which answers
one question at a time: train up to a chosen day, forecast a chosen period, say whether it hit
and whether the difference against a reference is real. The full guide is
`docs/EVALUATION.md`; here is what it measured.

Three differences from the chapter 5.1 backtest matter for interpreting the figures:

1. **A third reference.** `climatology_dow` — the training data's per-weekday mean — is a
   clearly harder bar than `seasonal_naive` on this data, and the main reference is by default
   the **best** reference for each window.
2. **The leading zeros are not removed.** The evaluation reads the venue's series as it stands,
   because the training window is the one the user named. Venue 1's January-March window
   therefore contains 21 zero days out of 90.
3. **The weather is run in three modes** (`perfect`, `operational`, `climatology`); the verdict
   comes from `operational`.

#### Monthly sweep 2026-04 … 2026-08, the baseline model, `operational`

Venue 1, Pekuri. The main reference is chosen per window:

| Test period | Reference | Model MAE | Reference MAE | Difference d | 95 % interval | Verdict | MDE | MDE % |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| April | climatology_dow | 102.9 | 96.2 | +6.7 | −3.2 … +30.7 | no difference | 34.5 | 36 % |
| May | moving_average_28d | 179.5 | 187.4 | −7.9 | −58.5 … +23.6 | no difference | 69.0 | 37 % |
| June | climatology_dow | 305.0 | 138.9 | +166.1 | +62.6 … +264.5 | **worse** | 102.0 | 73 % |
| July | climatology_dow | 174.3 | 156.2 | +18.1 | −15.5 … +60.9 | no difference | 43.5 | 28 % |
| August (25 days) | climatology_dow | 248.2 | 131.0 | +117.2 | +18.0 … +167.7 | **worse** | 84.5 | 65 % |

**Pooled: worse.** A mean difference of +60.0 visitors per day (95 % interval +3.1 … +124.4),
1 window in favour, 4 against.

Venue 2, Kaupungintalo. The main reference was `climatology_dow` in every window:

| Test period | Model MAE | Reference MAE | Difference d | 95 % interval | Verdict | MDE | MDE % |
| --- | --- | --- | --- | --- | --- | --- | --- |
| April | 95.5 | 75.1 | +20.4 | +11.5 … +47.7 | **worse** | 24.4 | 33 % |
| May | 76.4 | 71.5 | +5.0 | −5.4 … +33.6 | no difference | 31.9 | 45 % |
| June | 61.0 | 44.5 | +16.5 | −8.4 … +42.1 | no difference | 36.5 | 82 % |
| July | 108.0 | 62.0 | +46.0 | +27.1 … +66.1 | **worse** | 25.3 | 41 % |
| August (25 days) | 30.1 | 32.3 | −2.3 | −9.6 … +9.8 | no difference | 10.8 | 33 % |

**Pooled: worse.** A mean difference of +17.1 visitors per day (95 % interval +3.7 … +32.7),
1 window in favour, 4 against.

The multiple comparison family has size 10. After the Holm correction not one individual DM
p-value falls below 0.05: the smallest corrected one is 0.18 (venue 2, July). The individual
window verdicts therefore rest on the bootstrap interval, which is this assessment's primary
method, not on DM.

#### What has to be read from this

**The baseline model loses to a simple reference.** At both venues the pooled result is
against the model, four windows out of five. This is a measured result and it is stated here
directly. The backtest figures of chapter 5.3 do not contradict it: there the references were
`seasonal_naive` and `moving_average_28d`, which the baseline model beats at the near horizon.
`climatology_dow` is a harder opponent, and it had not been measured before.

**The single biggest failure is June at venue 1, and the evaluation found the reason.** The
model forecast 2,961 visitors for the month and the actual was 11,865, i.e. 75 % below. It is
not just a level frozen at the origin: **the model forecast essentially zero for 20 days.**

The cause is the combination of the leading zeros and the seasonal feature.
`year_sin = sin(2π·doy/365)` is symmetric about the peak in the first half of the year, so days
in January and days in June get the same value. Venue 1's 21 zero days (01-01 to 01-21) fall in
the `year_sin` range 0.017-0.354 and the first observed day, 01-22, is 0.370. The tree model
learns the rule "`year_sin` ≤ 0.354 → 0 visitors". In June, `year_sin` falls below the same
boundary on 06-11 (doy 162, value 0.3456 — exactly the same as 01-21), and the forecast
collapses to zero.

The same origin, the same model, a different training window:

| Training window | Zero days in training | June forecast | Near-zero days |
| --- | --- | --- | --- |
| `all` (151 days) | 21 | 2,961 | 20 |
| `120` | 0 | 8,846 | 0 |
| `90` | 0 | 9,056 | 0 |

The actual was 11,865, so without the zeros the model underestimates June by about 25 % — that
is item 2 of chapter 8.1, a level frozen at the origin that does not follow the summer rise.
With the zeros the error is three times as large and of an entirely different nature.

This is handled in production: `venue_history` removes the leading zeros (chapter 3.1). The
evaluation does not remove them, because the training window is the one the user named, and
`--train-window` is the tool for that. The finding is nevertheless a general one: **any run of
zeros at the start of the data is mirrored through `year_sin` to the opposite side of the
year**, and section 8 of the report names the risk automatically when the training window
contains leading zeros.

**The total and the daily accuracy are different things.** In April, venue 1's
`climatology_dow` hits the monthly total to within 0.8 % (13,292 vs. 13,189), even though its
daily MAE is 96 visitors, i.e. about 22 % of the daily mean. Neither may be inferred from the
other, and the evaluation reports them separately.

**Knowing the weather is almost worthless to this model.** The three weather modes are run for
every window, and the difference between the `climatology` and `perfect` MAE — the share of
the accuracy that rests on knowing the weather — is as follows across the ten venue-month
pairs:

| Test period | Venue 1 | Venue 2 |
| --- | --- | --- |
| April | −0.2 (−0.2 %) | −14.0 (−16.0 %) |
| May | +6.5 (+3.5 %) | +1.7 (+2.1 %) |
| June | −1.4 (−0.5 %) | +5.4 (+8.7 %) |
| July | +13.3 (+7.3 %) | −0.8 (−0.8 %) |
| August | +26.5 (+10.8 %) | +1.4 (+4.1 %) |

A positive figure means that knowing the weather helps. Six of the ten are positive, four
negative, and most are of the order of a few percent. **In four cases the model forecasts
better on average weather than on the realised weather.** That is not a measurement error: the
weather dependence the model learned does not generalise to those periods; the weather features
fit the noise of the training period more than the visitors' real behaviour in the weather.
This is a direct confirmation of item 4 in chapter 8.1 — the effect of the weather is a
correlation, not a mechanism — and it also means that the 16-day weather forecast limit
(chapter 6) is not, on this data, the bottleneck it has been suspected to be.

**The MDE makes the "no difference" results readable.** Over a one-month window the minimum
detectable difference is 28-82 % of the reference's MAE. A month therefore proves only large
improvements, and three of venue 1's five "no difference" results mean precisely "the sample is
too small", not "equally good".

**What could change the result.** A second year of data would make the yearly seasonality
component measurable and would remove level errors like June's. An events calendar as a feature
would address item 3 of chapter 8.1, which is the single largest source of error in an
event-driven venue. Neither is available in this dataset, so the current result is the result of
the current dataset rather than the model's final grade.

---

## 6. Weather beyond 16 days

Open-Meteo gives at most 16 days of forecast, but the horizon is 30.

| Days | Source | `weather_source` |
| --- | --- | --- |
| 1-16 | `data/processed/weather_daily.csv` | `forecast` |
| 17-30 | `data/reference/climatology/venue_{id}.csv` | `climatology` |

Every forecast row carries a `weather_source` column. The interface has to mark the
`climatology` rows visibly: average weather produces an average visitor count, so the forecasts
for days 17-30 are systematically too flat.

Three details in how climatology is handled:

- **`is_rainy_day` is left missing**, not guessed. Whether it rains on day 25 is genuinely
  unknown. Both models read NaN natively, so "I don't know" costs nothing, whereas inventing a
  zero or a one would cost accuracy.
- **`weathercode_str` is `overcast`** (or `slight_snow_fall` on the freezing side). A ten-year
  mean is not a sample from the daily distribution: the mean of ten Junes leaves 2 mm of
  drizzle on every day, so the same rain thresholds as for observations would classify the
  whole far end of the horizon as rainy. An average day in Oulu is cloudy, and that is what
  these rows claim.
- **`precip_hours`** is the number of hours whose climatological mean precipitation is at least
  0.1 mm. It is an approximation, not a measured quantity.

**The age of the data.** In this run the visitor data ends on 2026-05-22 but the weather data
runs to 2026-09-07. Days 1-16 of the horizon therefore get `weather_source = "forecast"`, even
though the weather for those days is already realised archive data in this dataset. The
column's meaning is "dynamic weather vs. smoothed climatology", and it has been kept as it is;
the run warns separately that the origin is 94 days old.

---

## 7. When the forecast should not be believed

These are also recorded in the `do_not_trust` field of each venue's `metrics.json`, in
both languages as `{"fi": ..., "en": ...}`. The same holds for the `warnings` field: the
site renders them in the language the reader chose rather than guessing a translation.

1. **A horizon beyond 14 days.** The weather is climatology and the level is frozen at the
   origin.
2. **A day with programming or an event the model does not know about.** This is the single
   largest source of error. The model sees past spikes in the data but knows nothing about
   future ones.
3. **The first two weeks after a new venue or a new sensor is taken into use.**
4. **A period where the ingest manifest reports `degraded` sources.**
5. **School holidays and Midsummer**, of which the dataset holds at most one observation. This
   run's horizon contains Midsummer (2026-06-19 and 2026-06-20) at horizons 28-29, i.e. in the
   climatology weather region. Those two days should not be trusted at all.
6. **Every case where coverage fell below 0.70** in the most recent backtest. In this run
   `prophet_xgb` at venue 2 at horizon 15-30 is 0.68.
7. **When the `warnings` field of `metrics.json` is not empty.** In this run both venues carry
   a warning that the most recent observed day is 94 days before the run.

---

## 8. Weaknesses

### 8.1 The baseline model

1. **It does not learn year-to-year seasonality.** The dataset does not contain a single full
   year. The seasonal features are in practice an extension of the trend; `year_sin` gets a
   high permutation importance (25.6 and 37.3), but here it measures the progress of spring,
   not a yearly cycle.
2. **A fixed level for the whole horizon.** `level_28d` does not update as the forecast
   advances. This shows up in the measurements: venue 1's bias grows from +42.8 (1-7) to +72.6
   (15-30).
3. **The level features are not symmetric between training and forecasting.** In training,
   `level_7d` is always exactly the previous week's mean, i.e. as fresh as at horizon 1. When
   forecasting, at horizon 30 it is a month old. The model therefore learns to trust the level
   more than is justified at a long horizon.
4. **It cannot anticipate events.** A concert or an exhibition opening shows up in the data as
   a spike, but the model knows nothing about future ones.
5. **The effect of the weather is a correlation, not a mechanism.** `wind_mean` is venue 1's
   third most important feature, which is almost certainly a seasonal proxy rather than a causal
   link.
6. **The hourly profile is static.** The same weekday profile for the whole horizon. It does
   not react to unusual opening hours.
7. **The prediction intervals rest on 8-10 origins.** q10 and q90 are computed from 49-117
   observations per bucket. That is a thin sample for quantiles.
8. **Zero inflation.** About 60 % of the hours are zeros. At the daily level the problem is
   small, but the profile's edge hours (venue 1 at 07 and 19) are unstable.
9. **A tree model does not extrapolate.** If the visitor count enters genuine growth,
   `days_since_start` will not carry the forecast past the maximum of the training data.

### 8.2 The comparison model

1. **A heavy install.** Prophet requires cmdstan, and XGBoost requires libomp on macOS.
2. **Yearly seasonality is not identifiable.** Measured in chapter 4.2: forced on, the MAE at
   15-30 rises from 179.9 to 774.0.
3. **The additivity assumption.** Rain affects a Saturday differently from a Tuesday. Prophet
   does not model interactions; the XGBoost stage can correct part of this.
4. **Two sources of error in a chain.** If Prophet is systematically off, XGBoost learns to
   correct it from the same small dataset.
5. **Slower.** A full run with Prophet takes 22 s, without it 17 s. In the backtest, 8-10
   origins times two venues means 20 Prophet fits.
6. **Inconsistent between the venues**, see chapter 5.4.

---

## 9. Outputs

```
data/forecasts/latest/manifest.json
data/forecasts/latest/venue_{id}/daily_30d.csv      # 30 days x 2 models = 60 rows
data/forecasts/latest/venue_{id}/hourly_7d.csv      # 7 days x 24 h x 2 models = 336 rows
data/forecasts/latest/venue_{id}/metrics.json
data/forecasts/latest/venue_{id}/backtest.csv
data/forecasts/{YYYY-MM-DD}/...                     # an archive copy of the same structure
```

The columns are described in chapter 4.3 of `FRAMEWORK_PLAN.md`.

The evaluation writes into its own tree:

```
data/evaluations/index.json                    a catalogue of runs and their verdicts
data/evaluations/{run_id}/config.json          the run's full parameters
data/evaluations/{run_id}/predictions.csv      venue, day, horizon, model, weather mode, actual, p10/p50/p90
data/evaluations/{run_id}/metrics.json         metrics, totals, the worst days
data/evaluations/{run_id}/verdicts.json        the verdicts, machine-readable
data/evaluations/{run_id}/report.md            the human-readable report, in Finnish
data/evaluations/{run_id}/report.en.md         the same report in English
```

The `run_id` is deterministic and readable, and the same run with the same parameters
overwrites the same directory. See `docs/EVALUATION.md`.

**Determinism.** Every model has a fixed `random_state`, nothing samples, and the only value
that changes between two runs is `generated_at`. This is tested
(`test_cli.py::test_two_runs_differ_only_in_the_timestamp`). The `--as-of` flag also locks the
timestamp, in which case two runs produce byte-identical files.

---

## 10. Commands

```bash
python -m ovf_forecast run                      # both models, all venues
python -m ovf_forecast run --model baseline     # the baseline model only
python -m ovf_forecast run --venue 1 --horizon-days 30
python -m ovf_forecast backtest --origins 12    # validation only, writes nothing
python -m ovf_forecast report                   # prints metrics.json readably
```

Evaluation (`docs/EVALUATION.md`):

```bash
python -m ovf_forecast evaluate --test 2026-04                       # train to 2026-03-31, forecast April
python -m ovf_forecast evaluate --train-end 2026-03-31 --test 2026-04-01:2026-04-30
python -m ovf_forecast evaluate --sweep monthly --from 2026-04 --to 2026-08
python -m ovf_forecast evaluate --sweep rolling --step 14 --horizon 30
python -m ovf_forecast evaluate --models baseline --reference climatology_dow --train-window 120
python -m ovf_forecast evaluate report --id <run_id>                 # a saved report
python -m ovf_forecast evaluate report --pooled                      # a summary over all runs
python -m ovf_forecast evaluate list                                 # the saved runs
```

The return value is 0 when everything is fine, 1 when some venue failed, 2 when nothing was
produced.
