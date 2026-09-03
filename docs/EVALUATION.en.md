# Evaluating the forecasts

*English translation. Finnish original: [`EVALUATION.md`](EVALUATION.md).*

How `python -m ovf_forecast evaluate` is run, how its results are read and what **cannot**
be concluded from them.

This document complements chapter 5 of `docs/FORECAST_MODEL.md`. Where `backtest` measures
the model at rolling origins and produces the production prediction intervals, `evaluate`
answers one question at a time: **train up to this day, forecast this period, tell me
whether it hit and whether the difference against a reference is real.**

The question is forecasting the level. The *ranking* of the quietest days of the month is a
different question, and it has its own tool and its own measurement:
`docs/QUIET_DAYS.md`.

---

## 1. Quick start

```bash
python -m ovf_forecast evaluate --test 2026-04
```

Trains on all data available up to 2026-03-31, forecasts April, compares against the actual
values and prints the verdict as a single paragraph. Results are saved under
`data/evaluations/`.

A full monthly sweep, five windows and their pooled summary:

```bash
python -m ovf_forecast evaluate --sweep monthly --from 2026-04 --to 2026-08 --models baseline
```

Takes about a minute without prophet.

---

## 2. Commands

| Command | What it does |
| --- | --- |
| `evaluate --train-end 2026-03-31 --test 2026-04-01:2026-04-30` | One window, explicit boundaries |
| `evaluate --test 2026-04` | The same as a shorthand: origin 2026-03-31, test period all of April |
| `evaluate --test 2026-04-15` | A single-day test period |
| `evaluate --sweep monthly --from 2026-04 --to 2026-08` | One window per month + a pooled summary |
| `evaluate --sweep rolling --step 14 --horizon 30` | The origin moves in 14-day steps |
| `evaluate report --id <run_id>` | Prints a saved report |
| `evaluate report --pooled` | Pools every saved run into one verdict |
| `evaluate list` | Lists the saved runs |

### Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--models` | `baseline,prophet_xgb` | Comma-separated list. Prophet is skipped when it is not installed |
| `--reference` | `best` | `best`, `seasonal_naive`, `moving_average_28d` or `climatology_dow` |
| `--weather` | all three | `perfect`, `operational`, `climatology` |
| `--train-window` | `all` | `all` or a number of days (a rolling window) |
| `--venue` | all | Repeatable, e.g. `--venue 1 --venue 2` |
| `--step`, `--horizon`, `--max-windows` | 14, 30, 12 | `--sweep rolling` only |
| `--resamples`, `--seed` | 10,000, 20260101 | Bootstrap |

The run is deterministic. The same input and the same parameters produce byte-identical
files under `data/evaluations/{run_id}/`; the only value that changes is `created_at` in
`index.json`, which is a field of the registry rather than of the result.

---

## 3. Defining a window

A window is three things:

- **origin** — the last day whose data may be used in training
- **test_start … test_end** — the period being evaluated
- **train_window** — `all` or a number of days

`test_start` is **always** `origin + 1 day`. If you give `--train-end` and `--test` so that
a gap is left between them, the command refuses. A gap would silently drop the horizons at
which the forecast is at its worst, and every metric would look better than it is.

---

## 4. Leakage rules

An evaluation is useless if the forecast has seen data from the test period. The
implementation has six rules and one deliberate exception.

1. **The model is trained only on data whose day is ≤ the origin.**
2. **Level features** (`level_7d`, `level_28d`, `dow_index_28d`) are computed at the origin
   and stay constant through the whole test period.
3. **The MASE denominator** — the training data's own seasonal naive MAE — is computed from
   the training window only.
4. **The prediction interval quantiles** come from a nested backtest run entirely inside the
   training window. Its last inner origin is `origin − horizon`, so no inner forecast
   reaches into the test period. *This is the easiest mistake to make:* a production run
   calibrates its intervals from the freshest data, and in an evaluation the freshest data
   is exactly that test period. Coverage computed that way would be 80 % by construction
   rather than by measurement.
5. **The references** read only days ≤ the origin. In particular `seasonal_naive` is **not**
   `y[t−7]`: it repeats the week that ended at the origin. In the form `y[t−7]`, horizon 8
   would already be reading actual values from the test period.
6. **Calendar information** (weekdays, public holidays) is allowed, because it is known in
   advance.
7. **Ticket data is not used as a feature**, because it does not exist for the future.

The exception is **weather**, and that is precisely what the three weather modes measure;
see chapter 5.

The leakage rule is tested from the outside:
`packages/forecast/tests/test_evaluation_leakage.py` runs the evaluation, replaces every
observation after the origin with random numbers, runs it again and requires bit-identical
forecasts. In `climatology` mode the weather is replaced as well.

---

## 5. The three weather modes

In production a weather forecast is available, not the realised weather. Evaluating on the
realised weather gives too good a result, evaluating on climatology too poor a one. Every
window is therefore run three times.

| Mode | Weather over the test period | Interpretation |
| --- | --- | --- |
| `perfect` | realised, for the whole period | **Upper bound**: what the model could do if the weather were known |
| `operational` | realised for days 1-16, climatology from day 17 | **The most realistic estimate**, assuming a good weather forecast |
| `climatology` | climatology for the whole period | **Lower bound**: what the model can do without a weather forecast |

The verdict is computed from `operational` by default. Chapter 7 of the report gives the MAE
of all three and their difference: **the gap between perfect and climatology is the share of
the model's accuracy that rests on knowing the weather.** That is a result in its own right
and is reported separately.

The references do not read the weather at all, so their forecast is the same in all three
modes. That is intentional: it makes the effect of the weather readable straight from the
table.

**The improvement can be negative**, and on this dataset it is in four out of ten
venue-month pairs: the model forecasts better on average weather than on the realised
weather. That is not a measurement error but a result — the weather dependence the model
learned does not generalise to that period — and the report flags it separately. See
chapter 5.5 of `docs/FORECAST_MODEL.md`.

A fourth mode, `archived_forecast` — the weather forecast that was actually available at the
origin — has not been implemented. It would be the genuinely correct answer to this problem;
see chapter 11.

---

## 6. The references

All three are always computed, and all three are reported.

| Name | Definition |
| --- | --- |
| `seasonal_naive` | The observation from the same weekday in the 7-day period that ended at the origin, repeated across the whole horizon |
| `moving_average_28d` | The mean of the 28 days preceding the origin, constant for the whole period |
| `climatology_dow` | The training data's per-weekday mean, constant for each weekday |

**The main reference is by default the best of these three on that window**, not
`seasonal_naive`. The justification is in the data: with the current data `climatology_dow`
beats `seasonal_naive` in most months, so a fixed `seasonal_naive` would be too low a bar.
`--reference` locks one in if you want that.

### Measured reference figures

Origin 2026-03-31, test 2026-04-01 … 2026-04-30, `--train-window all`:

**Venue 1 (Pekuri).** Actual total 13,189, MASE denominator 141.18.

| Reference | MAE | RMSE | Bias | Forecast total |
| --- | --- | --- | --- | --- |
| seasonal_naive | 129.50 | 158.12 | +66.10 | 15,172 |
| moving_average_28d | 197.61 | 219.80 | +138.22 | 17,336 |
| **climatology_dow** | **96.20** | 122.72 | +3.44 | 13,292 |

**Venue 2 (Kaupungintalo).** Actual total 3,791, MASE denominator 128.57.

| Reference | MAE | Forecast total |
| --- | --- | --- |
| seasonal_naive | 138.57 | 7,656 |
| moving_average_28d | 88.16 | 5,802 |
| **climatology_dow** | **75.14** | 5,346 |

These are acceptance criteria, and `test_evaluation_baselines.py` checks them.

### Leading zeros: one deliberate difference from production

A production run (`venue_history`) removes the contiguous run of zero days at the start of a
venue: venue 1 reports nothing before 2026-01-22 and venue 2 nothing before 2026-01-08, and
this is an uninstalled sensor rather than a museum nobody visited.

**The evaluation does not remove them.** The reason is that the training window is the one
the user named, and quietly moving the left edge would turn `--train-window all` into
something other than what it looks like. The difference is large: trimmed, venue 1's
`climatology_dow` in April would be 164.73 rather than 96.20 and the MASE denominator 123.69
rather than 141.18.

The consequence has to be said out loud: **in the January-March window, 21 of the 90 days of
venue 1's training data are zeros.** The report gives the figure in section 8, and
`--train-window` cuts them out:

```bash
python -m ovf_forecast evaluate --test 2026-04 --train-window 60
```

#### The zeros do not stay at the start

This is not merely a nuisance that lowers the level, and the evaluation revealed why. The
seasonal feature `year_sin = sin(2π·doy/365)` is symmetric: it rises from January to a peak
at the start of April and falls back again. **A day in January and a day in June therefore
get the same value.**

Venue 1's zero days are 2026-01-01 to 2026-01-21, i.e. `year_sin` between 0.017 and 0.354;
the first observed day, 01-22, is 0.370. The tree model learns the rule "`year_sin` ≤ 0.354
→ 0 visitors" from this. In June, `year_sin` falls below the same boundary on 06-11 (doy
162, `year_sin` 0.3456 — the same value as 01-21), and **the model forecasts zero for the
rest of the month.**

Measured, origin 2026-05-31, venue 1, June total (actual 11,865):

| Training window | Zero days in training | June forecast | Near-zero days |
| --- | --- | --- | --- |
| `all` (151 days) | 21 | **2,961** | 20 |
| `120` | 0 | 8,846 | 0 |
| `90` | 0 | 9,056 | 0 |

The same phenomenon applies to any venue with a run of zeros at the start of the data. **If
a forecast collapses towards zero in the middle of summer, this is the first place to
look**, and section 8 of the report names it automatically when the training window contains
leading zeros.

---

## 7. Metrics

Computed per venue, per model, per weather mode and per horizon bucket (1-7, 8-14, 15-30)
as well as for the whole period (`all`).

| Metric | Notes |
| --- | --- |
| **MAE** | The main metric |
| RMSE | Penalises large errors |
| **MASE** | MAE / the training data's seasonal naive MAE. Comparable across venues |
| Bias | Mean signed error (forecast − actual) |
| **Pinball 0.1 / 0.5 / 0.9** | The proper score for a quantile forecast |
| Coverage 80 % | The share of actual values inside p10-p90 |
| sMAPE | **Flagged unreliable when the test period contains zero days** |

### sMAPE and zero days

Venue 2 is closed on some public holidays (e.g. 2026-04-03 and 2026-04-06, 2026-06-19 to
2026-06-21). On a zero day the symmetric ratio hits its ceiling of 200 % regardless of how
close the forecast was: `smape(actual 0, forecast 3) = 200 %`, while
`smape(actual 500, forecast 503) < 1 %`. The metric is computed, because leaving it out
would only lead to it being asked for, but it **never grounds a verdict** and the report
marks it with a `⚠`.

---

## 8. Statistical assessment

### The basic setup

The absolute error series of the model and of the reference are compared pairwise on the
same days:

```
d_t = |y_t − model_t| − |y_t − reference_t|
```

A negative mean means the model is closer.

### Primary method: the moving block bootstrap

- block length **7 days**, so that the autocorrelation of the weekly rhythm survives
- **10,000** resamples, a fixed seed
- a 95 % percentile interval for the mean of `d`
- verdict: **better** if the whole interval is below zero, **worse** if the whole interval
  is above zero, otherwise **no detectable difference**

A per-day bootstrap would give an interval about a third too narrow, because the visitor
counts of consecutive days are not independent.

The **skill score** `SS = 1 − MAE_model / MAE_reference` and its bootstrap interval are also
reported.

### MDE, a mandatory part of the verdict

```
MDE = 2.8 · sd(d) / √n
```

When the verdict is "no detectable difference", it can mean two different things: **the
models are equally good**, or **the sample is too small**. Only the MDE separates these. It
is reported both as visitors per day and as a percentage of the reference's MAE.

With the current data, the MDE over a one-month window is **28-82 % of the reference's
MAE**, typically around a third. **One month can therefore only prove large improvements.**
Never read a "no difference" result as evidence of equivalence.

### Diebold-Mariano, as a secondary test

Computed with a Newey-West variance (Bartlett kernel, lag `ceil(1.5·n^(1/3))`) and the
Harvey-Leybourne-Newbold small-sample correction. The HLN formula asks for a horizon *h*;
here the errors span horizons 1-30 from one origin and there is no single *h*, so
`h = lag + 1` — the same dependence assumption the variance already makes.

**The p-value is computed from a recentred bootstrap, not from a t-distribution.** The
package does not need scipy for the sake of one distribution function.

DM is marked secondary and the reason is stated in the report: **the 30 errors from one
origin are not 30 independent observations.** They share the same training set and the same
month of weather. DM's assumptions are therefore stretched.

### Pooling several windows, the most important result

The verdict from one window is **descriptive, not probative.** The actual evidence comes
from pooling several windows, and there **the bootstrap resamples whole windows, not
individual days.** The window is the natural unit of independence: two days from the same
window share a training set, two different windows do not. A day-level bootstrap over the
pooled data would count the same evidence many times over.

The pooled result is the report's main heading. The verdict for an individual window is
presented below it as a detail, and the pooled summary says how many windows favoured the
model and how many went against it.

### Multiple comparison correction

When a sweep runs `k` windows and `m` models, `k·m` hypotheses are tested and roughly one in
twenty comes out significant by chance. Both the **raw** and the
**Holm-Bonferroni-corrected** p-value are reported, and the size of the family is stated.

### Bias and calibration

- **Bias**: a bootstrap confidence interval for the mean error. If the interval does not
  contain zero, the model systematically over- or underestimates. The direction and the
  magnitude are given both as visitors and as a percentage.
- **Calibration**: 80 % coverage and a **Clopper-Pearson exact** binomial interval for it
  (30 days is a small sample and the proportion is close to the edge of the unit interval,
  where the normal approximation is at its worst). Verdict: *calibrated* if 0.80 falls
  inside the interval, *too narrow* if coverage falls below, *too wide* if above.

---

## 9. The total for the period

A producer asks "how many visitors in April", not "what was the daily MAE". **These are
different questions and neither may be inferred from the other.**

In April, venue 1's `climatology_dow` hits the monthly total to within 0.8 % (13,292 vs.
13,189), even though its daily MAE is 96 visitors, i.e. about 22 % of the daily mean. Daily
errors of opposite sign cancel each other out in the sum.

### The interval for the total is not summed from the days

The sum of the daily p10 values and the sum of the p90 values are **not** the month's
interval. They answer the question "what if every single day landed on its own tenth
percentile", and that scenario requires all 30 errors to point in the same direction. The
old application made this mistake and its monthly intervals were unusable.

The interval is **simulated**: the daily relative errors of the backtest inside the training
window are bootstrapped in blocks into whole periods, each simulated path is multiplied by
the daily forecasts and summed, and the interval is read from the distribution of those
sums. The report shows the naive sum alongside it so that the difference is visible.

### When the interval for the total should not be believed

The models of the nested backtest are trained on **shorter and poorer data** than the outer
model — that is a structural property of a nested backtest. If the median of their relative
errors drifts more than 25 % from one, the errors carry a **level shift rather than mere
spread**, the interval inherits it, and the report flags it with `⚠ Näiden mallien väli ei
ole kalibroitu` (the interval for these models is not calibrated). In that case read the
difference in the total and the bias separately, not the interval.

The point forecast is always kept inside its own interval, for the same reason as the daily
intervals (`ovf_forecast.intervals`): an interval that does not contain the number it is an
interval for is not publishable. The level shift is still reported as bias, as a difference
and in the `median_ratio` field.

---

## 10. Outputs

```
data/evaluations/
  index.json                   a catalogue of runs: run_id, creation time, window, models, verdict
  {run_id}/
    config.json                the run's full parameters
    predictions.csv            venue_id, date, horizon_days, model, weather_mode, y_true, p10, p50, p90
    metrics.json               every metric, the totals, the worst days
    verdicts.json              the verdicts in machine-readable form
    report.md                  the human-readable report
```

The `run_id` is deterministic and readable, for example
`eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline`. Everything that changes the answer but
does not show in the name — a venue restriction, a rolling training window, a restricted set
of weather modes, a locked reference — is appended as a readable suffix (`_v1`, `_tw120`,
`_wxoper`, `_ref-climatology_dow`). The same run with the same parameters overwrites the
same directory.

### The structure of the report

1. **The verdict** as a single paragraph in Finnish, without jargon
2. The window and the setup
3. The total for the period
4. Daily metrics, models and references side by side
5. Statistical assessment: confidence interval, skill score, MDE, DM
6. Calibration and bias
7. A comparison of the three weather modes
8. Limitations
9. **The worst days** — the five largest errors with their dates and possible causes (a
   public holiday, heavy rain, climatology weather, a zero day)

Section 9 is in practice the most useful one: it says what the model is missing. A recurring
cause in the same column is a direct proposal for the next feature.

---

## 11. What CANNOT be concluded from the results

This chapter is the most important one.

**"No detectable difference" does not mean the models are equally good.** It means *this
sample did not separate them*. Read the MDE. With the current data the MDE over one month is
on the order of a third of the reference's MAE, so small but real improvements stay
invisible.

**A result from one window is not proof.** It is a description of what happened in one
month. Use a sweep.

**A good monthly total does not prove good daily accuracy, and vice versa.** See chapter 9.

**sMAPE is not fit to ground a verdict** on this data. See chapter 7.

**Coverage cannot be read from default intervals.** If the nested backtest did not produce
enough observations for some horizon bucket, the interval is a fixed default. Section 8 of
the report names these.

**Nothing can be said about year-to-year variation.** There is about eight months of data
from a single year. A comparison against another year is impossible, and the models' annual
seasonal components cannot be assessed.

**The true value of the weather has not been measured.** `perfect` is too good and
`climatology` too poor; `operational` assumes a **good** weather forecast instead of using
the weather forecast that was actually available at the origin. The right answer would be a
fourth mode, `archived_forecast`. It has not been implemented, but it is possible, and the
API has been checked against the documentation:

- **Open-Meteo's Historical Forecast API is not fit for this.** It stitches the first hours
  of successive runs into one continuous series, i.e. it is closer to a best estimate of
  what happened than to the forecast that was visible at the origin. It has no parameter for
  the forecast issue time, only `start_date` and `end_date`.
- **The Single Runs API is the one needed here.** It stores each model run separately and is
  queried by the UTC initialisation time `run=` (e.g. `run=2026-03-31T00:00`), which yields
  the whole forecast horizon of one run.
- **Coverage is sufficient.** Most models have been archived since January 2024, i.e. for
  the whole span of this dataset. The horizon of a single run is about 7+ days for global
  models and 2-5 days for regional ones, so over a 30-day window `archived_forecast` would
  cover only the near days and the rest would fall back to climatology.

Implementing it would require the fetch and a storage format on the ingest side, because an
evaluation run may not call the network: determinism and offline operation are conditions of
this package. Until that is done, **`operational` is the best guess and not a measurement**,
and the `perfect`-`climatology` gap is what is actually known about the value of the
weather.

**The prediction intervals rest on a thin sample.** The nested backtest typically has 3-12
origins, and in the April window only 3.

---

## 12. Measured results

See chapter 5.5 of `docs/FORECAST_MODEL.md`. In short: **in the monthly sweep 2026-04 …
2026-08 the baseline model loses to the best simple reference at both venues**, in four
windows out of five. That is a correct and honest result, not a failure — and as such it is
also in the report's first paragraph.
