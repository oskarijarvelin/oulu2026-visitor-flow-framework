# The quietest days of the month

*English translation. Finnish original: [`QUIET_DAYS.md`](QUIET_DAYS.md).*

How `python -m ovf_forecast quiet` finds the quietest days of the month, where the threshold
comes from, how the model's reliability is measured and what **cannot** be concluded from the
result.

This is a different question from the forecast in `docs/FORECAST_MODEL.md`. The forecast
model says *how many* visitors a day brings. This package says **which days of the month are
its quietest**, so that a customer activation event can be placed where there is the most
free capacity.

The difference is not cosmetic. Forecasting the level requires knowing how busy October is;
forecasting the ranking only requires knowing which of October's Wednesdays is quiet. With
eight months of history the latter can be answered even though the former cannot — chapter
12 of `docs/EVALUATION.md` shows that the level forecast loses to a simple per-weekday mean
at both venues. That is why every figure in this package is divided by the month's **own
median day**: the error in the level cancels out and does not affect the ranking.

---

## 1. Quick start

```bash
python -m ovf_forecast quiet backtest
python -m ovf_forecast quiet
```

The first measures whether the model is worth believing: it walks through the history a
month at a time, names each month's quietest days on the basis of the preceding data alone
and only then opens the actual values. The second names the quietest days of the coming
month and attaches to the answer what the first one measured.

In that order, not the other way round. Without the measurement the recommendation is a
guess with a tidy table around it, and the command says so out loud:

> Mallin luotettavuutta ei ole mitattu tässä repositoriossa: aja
> `python -m ovf_forecast quiet backtest` ennen kuin suositukseen nojataan.
>
> (The model's reliability has not been measured in this repository: run
> `python -m ovf_forecast quiet backtest` before leaning on the recommendation.)

Both save their results under `data/quiet/`.

---

## 2. Commands

| Command | What it does |
| --- | --- |
| `quiet` | Names the quietest days of the coming month |
| `quiet --month 2026-10` | Names the days of the chosen month |
| `quiet --top-k 3` | A shortlist of three days instead of a fifth |
| `quiet backtest` | Monthly sweep: one window per month + a verdict |
| `quiet backtest --sweep rolling --step 14 --horizon 30` | A rolling origin |
| `quiet backtest --models quiet_calendar,baseline` | Compares the rules against each other |
| `quiet report --latest` | Prints the most recent saved report |
| `quiet report --id <run_id>` | Prints the report of a named run |
| `quiet list` | Lists the saved runs |

### Options

| Option | Default | Meaning |
| --- | --- | --- |
| `--month` | the month after the observations | The target month, `YYYY-MM` |
| `--score-model` | `quiet_calendar` | The ranking rule, see chapter 5 |
| `--quiet-share` | `0.20` | What share of the candidate days count as quiet |
| `--top-k` | — | A fixed number of days; overrides `--quiet-share` |
| `--venue` | all | Repeatable |
| `--simulations` | 10,000 (2,000 in a sweep) | Simulations per probability |
| `--seed` | 20260101 | The seed for the simulation and the bootstrap |
| `--sweep` | `monthly` | `backtest` only: `monthly` or `rolling` |
| `--from`, `--to` | all usable history | `--sweep monthly` only |
| `--step`, `--horizon`, `--max-windows` | 14, 30, 12 | `--sweep rolling` only |
| `--resamples` | 10,000 | `backtest` only: bootstrap resamples |

The run is deterministic. The same input and the same parameters produce byte-identical files
under `data/quiet/{run_id}/`; the only value that changes is `created_at` in `index.json`,
which is a field of the registry rather than of the result.

The monthly sweep is the default because the question is a monthly one and calendar months do
not overlap. In a rolling sweep, successive windows share days, which makes them dependent
and the confidence interval narrower than it really is. The report says so itself when the
windows overlap.

---

## 3. The threshold: what a quiet day is

The threshold is three decisions, and they live in the module
`packages/forecast/src/ovf_forecast/quiet/threshold.py` and nowhere else.

### 3.1 Candidacy: which days are allowed to be quiet

A closed day is the quietest day of every month and completely useless for an event. Two
exclusions are made in advance, i.e. on the basis of information that already exists at
forecast time:

| Rule | Condition | Target |
| --- | --- | --- |
| `closed_weekday` | The weekday's median < 15 % of the venue's own median | Kaupungintalo's Mondays are at 14 % |
| `closed_holiday` | Public holiday factor < 15 % | Does not trigger on the current data |

On the actuals side, i.e. in the measurement, two more exclusions appear, because they
require an observation: a day with no visitors at all (`no_visitors`) was a closure or a
sensor outage, and a day that was not measured in full (`incomplete_day`) looks quiet for a
reason that has nothing to do with visitors. Neither can be applied to a forecast, because
both require exactly the information the model is trying to predict.

The exclusion is deliberately blunt: one flag per weekday, no seasonal opening hours. Four
weekly observations per weekday cannot carry anything finer.

**A merely quiet weekday is not a closed weekday.** Pekuri's Sunday is 82 % of the venue's
median day. That is an answer, not a filter.

### 3.2 The cut: the quietest fifth of the month

There are `k = ceil(0.20 × the number of candidate days)` quiet days, clamped to the range
3-10. In a 30-day month that is six days.

The threshold is relative and internal to the month. It is not a visitor count, because 400
visitors is quiet at Pekuri and a record at Kaupungintalo, and it is not a fixed share of the
median either, because the spread varies from month to month. It is the 20 % percentile of
the month's own distribution.

### 3.3 Where the 20 % comes from

The threshold is a choice, not a constant of nature, so it has been measured. Below is the
monthly sweep 2026-04 … 2026-08 for both venues, with the `quiet_calendar` rule and five
different thresholds. The table is produced by running the sweep five times:

```bash
for share in 0.10 0.15 0.20 0.25 0.33; do
  python -m ovf_forecast quiet backtest --quiet-share $share
done
```

| Share | k | Threshold / median day | Best possible benefit | Measured benefit | Hit rate | Random choice |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 % | 3.4 | 0.46 | 58 % | 41 % | 48 % | 12 % |
| 15 % | 4.8 | 0.58 | 54 % | 32 % | 50 % | 17 % |
| **20 %** | **6.2** | **0.70** | **49 %** | **26 %** | **53 %** | **22 %** |
| 25 % | 7.5 | 0.77 | 45 % | 21 % | 52 % | 26 % |
| 33 % | 9.5 | 0.86 | 39 % | 15 % | 53 % | 33 % |

The figures are means across both venues. *Benefit* is 1 − (the mean of the chosen days ÷ the
month's median day), *best possible* the same figure for days chosen with hindsight, *hit
rate* the share of the named days that genuinely belonged to the quietest ones.

Three things can be read from the table:

1. **A tighter threshold produces quieter days.** On the 10 % list the chosen days are 41 %
   quieter than the median day, on the 33 % list 15 %. The ratio to a random choice is at its
   best at the same time: 4.0-fold at 10 %, 1.6-fold at 33 %.
2. **20 % lands where the threshold is still interpretable.** The cut settles at 0.70 of the
   median day, i.e. a quiet day is roughly "about three quarters of a normal day". With a
   tighter cut, `k` hits its lower bound of 3 and the share no longer steers anything.
3. **20 % gives a list you can work with.** Six days is enough for an event to fit the
   schedules of the performer, the space and the staff. Three is not always enough.

The default is therefore a compromise rather than an optimum, and it is deliberately the
decision that is easiest to change. **If you only need one or two dates, use `--top-k 3`: the
measured benefit is then roughly twice as large.**

### 3.4 Materiality: when an answer should not be given

Even a flat month has a quietest fifth, and naming it would be a recommendation with nothing
behind it. Every set therefore carries the flag `is_material`: the set has to be at least
15 % below the median day before it may be read as a recommendation. In a forecast the flag
concerns **the model's power to discriminate** — whether the rule can separate the month's
days from each other at all — and in the actuals **the month's real spread**.

---

## 4. The forecast model

### 4.1 The score

The default rule `quiet_calendar` gives every day of the target month a score:

```
score(d) = day-of-week mean(weekday(d)) × public holiday factor(d)
```

- **The day-of-week mean** is the venue's mean visitor count on that weekday across the whole
  training window. For a weekday the training window has not seen, the venue's overall mean is
  used: a day without a score would never end up in the recommendation, and that is a
  different claim from "this day is not quiet".
- **The public holiday factor** is the median of the ratio `actual / day-of-week mean` over
  the public holidays in the training window, clipped to the range 0.05-2.0 and computed only
  from three observations upwards. Without a public holiday in the month the rule is exactly
  `climatology_dow`.

The score is on the same order of magnitude as a visitor count, but **it is not a visitor
forecast**. It is a ranking number. For a level forecast there is
`python -m ovf_forecast run`.

### 4.2 The model's separation is not the realised difference

The score is a conditional mean, and a conditional mean is always flatter than the actual
values. In the forecast for September 2026, Pekuri's quietest fifth separates to 18 % below
the median day. In the months that have actually happened, the quietest fifth is on average
49 % below the median day. These are different numbers and neither predicts the other:

- **The model's separation** says how far apart the rule pulls the days. It is used to compute
  the materiality flag.
- **The realised benefit** says how quiet the chosen days were. It can only be obtained by
  measuring, and it is the result of `quiet backtest`.

The report says this every time, because this confusion is the mistake people make with this
tool.

### 4.3 The selection probability

Every candidate day gets a probability of belonging to the month's quietest days. On this
data that is a more valuable figure than the ranking itself.

The method is Monte Carlo. The month is simulated 10,000 times: the scores are multiplied by
a path that is block-bootstrapped from **the rule's own measured residuals**, the month is
re-ranked, and how often each day ended up in the quietest set is counted.

- **The residuals are measured inside the training window.** The rolling origin steps back 14
  days at a time, and the newest of them is `origin − horizon`, so its last forecast day falls
  exactly on the origin and never a day later. The same rule as in the nested backtest of the
  evaluation package.
- **The block is seven days.** A quiet week is quiet for the whole week, and a per-day draw
  would make each day's fate independent and every probability too confident.
- **If no inner origin fits at all**, a default spread is used and the report says so. The
  probability then describes the rule's ranking rather than measured uncertainty.

The probabilities sum to `k` by construction, and they are calibrated or not — chapter 6.4 of
the test tool tells you which.

### 4.4 Ties

The default rule gives every Sunday of the month the same score. From the model's point of
view they are therefore interchangeable, and a set of six days will hold some occurrences of
the next weekday and not others — purely because of the calendar order.

This is not hidden:

- Days with equal scores get **the same probability** (the group's mean). 47 % and 45 % for
  two identical Sundays would be Monte Carlo noise that the reader would take for a
  preference.
- The report has a **Ties** column, and when the cut falls inside a group, the answer says so:
  the choice among them is in date order and is not based on the data, so it can be made on
  other grounds.

Calendar order is not a neutral way to break ties, and chapter 7 shows what follows from it
for a rule that has no ranking information at all.

### 4.5 Mid-month

Days of the target month that have already happened are kept and marked with the state
`observed`. They compete for a place among the quietest **with their own realised value** and
get a factor of 1.0 in the simulation. This way a run on the 12th gives a consistent answer
about the end of the month instead of behaving as though the first eleven days did not exist.

### 4.6 Leakage rules

1. The rule sees only rows `<= origin`. `ScoreRequest` truncates the history itself, so
   handing it a longer history cannot leak an observation into a feature.
2. The candidacy rules (`closed_weekday`, `closed_holiday`) are derived from the training
   window alone.
3. The inner origins for the residuals are entirely inside the training window (chapter 4.3).
4. Calendar information — the weekday, the public holidays — is allowed, because it is known
   in advance.
5. Weather is not a feature at all (chapter 5.3).

The test `test_quiet_model.py::test_a_score_cannot_see_past_its_origin` runs every rule on
both the full and the truncated history and requires the same result.

---

## 5. The rules, and why the default is this one

### 5.1 The available rules

| Rule | What it does |
| --- | --- |
| `quiet_calendar` | Day-of-week mean × public holiday factor. The default |
| `climatology_dow` | The training window's day-of-week mean. The same without the holiday information |
| `seasonal_naive` | The week ending at the origin, repeated |
| `moving_average_28d` | A 28-day mean, the same number for every day |
| `baseline` | The production gradient boosting model as a ranking key |

The level models are included as opponents rather than as decoration: a daily forecast *is* a
ranking of the month, so they are not being judged on work they were not built for.

### 5.2 The measured comparison

Monthly sweep 2026-04 … 2026-08, five windows, threshold 20 %:

| Venue | Rule | Benefit | 95 % interval | Hit rate | Chance | Capture | Spearman | Verdict |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Pekuri | `baseline` | 10 % | −1 % … 22 % | 43 % | 21 % | 30 % | 0.29 | not verified |
| Pekuri | `seasonal_naive` | 10 % | −2 % … 19 % | 42 % | 21 % | 29 % | 0.34 | not verified |
| Pekuri | `climatology_dow` | 8 % | −1 % … 17 % | 40 % | 21 % | 22 % | 0.35 | not verified |
| Pekuri | `quiet_calendar` | 7 % | −1 % … 17 % | 40 % | 21 % | 20 % | 0.37 | not verified |
| Pekuri | `moving_average_28d` | −12 % | −22 % … −1 % | 22 % | 21 % | −34 % | – | **harmful** |
| Kaupungintalo | `climatology_dow` | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 0.43 | **verified** |
| Kaupungintalo | `quiet_calendar` | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 0.42 | **verified** |
| Kaupungintalo | `baseline` | 34 % | 7 % … 57 % | 61 % | 22 % | 54 % | 0.46 | **verified** |
| Kaupungintalo | `seasonal_naive` | 29 % | 1 % … 55 % | 50 % | 22 % | 47 % | 0.24 | **verified** |
| Kaupungintalo | `moving_average_28d` | −16 % | −43 % … 11 % | 18 % | 22 % | −26 % | – | not verified |

Reproducible with:

```bash
python -m ovf_forecast quiet backtest \
  --models quiet_calendar,climatology_dow,seasonal_naive,moving_average_28d,baseline
```

Three observations:

- **There is no measurable difference between the four sensible rules.** The differences are a
  few percentage points and the confidence intervals are tens of them. The choice of rule is
  not what decides this task.
- **The difference between the venues is enormous.** The same rule yields 45 % benefit at one
  and 7 % at the other. The verdict is therefore given per venue.
- **`moving_average_28d` is a null rule and behaves like one.** It gives every day the same
  score, so breaking the ties in calendar order picks the first six days of the month. The
  result is worse than a random choice, and that is exactly why a cut that falls inside a
  shared tie group is reported (chapter 4.4).

### 5.3 What was tried and left out

These measurements were made during development on the same windows and with the same
candidacy rule, but they are not reproducible with the finished CLI, because the rejected
variants are not in the package. The figures are the mean benefit across both venues.

| Variant | Monthly windows | Rolling windows |
| --- | ---: | ---: |
| Day-of-week mean, whole window | 0.264 | 0.318 |
| Day-of-week mean + public holiday factor (**the default**) | 0.262 | 0.317 |
| Day-of-week median, 8 weeks | 0.239 | 0.299 |
| Day-of-week median, whole window | 0.236 | 0.272 |
| Day-of-week mean, 8 weeks | 0.225 | 0.300 |

- **The mean beats the median.** An occasional busy Saturday is exactly the information that
  keeps Saturday out of the quiet set.
- **A recency window does not help.** Restricting to eight weeks is neutral or harmful, so the
  rule uses the whole training window.
- **The public holiday factor changes nothing on this data.** Eight months contain eight public
  holidays, and the closures among them are excluded before the recommendation anyway. The
  factor is included regardless, because the mechanism is real and only a full year, with
  Christmas and Midsummer, would show it.
- **Weather does not improve the ranking.** A rain factor on top of the weekday rule gave a
  mean realised ratio of 0.813 against 0.811, i.e. a difference in the noise. The correlation
  of the residuals with rain is 0.10-0.12 and with temperature about 0. Weather is therefore
  in the report's table as **background for a human decision**, not in the scoring.
- **Combining rules by rank** (`quiet_calendar` + `baseline`) did not improve the result.

---

## 6. The test tool

`quiet backtest` is an instrument, not part of a production run. Every window is one honest
exercise of the real task: train up to the origin, name the quietest days of the period, open
the actual values only then.

### 6.1 Metrics

| Metric | Definition | What it says |
| --- | --- | --- |
| `hit_rate` | The share of the named days that belonged to the true set | Accuracy |
| `chance_rate` | `k / the number of candidates` | What a guess would give |
| `realized_ratio` | The mean of the named days ÷ the month's median day | – |
| `benefit` | `1 − realized_ratio` | **The headline figure** |
| `oracle_ratio` | The same for days chosen with hindsight | The ceiling |
| `capture` | `benefit ÷ oracle_benefit` | The share of what was achievable |
| `spearman` | Rank correlation between the score and the actual value | The whole ranking, not just the cut |
| `top1_ratio` | The actual value of the day forecast quietest ÷ the median | Choosing a single day |

`hit_rate` is the natural one but the least useful of the four: it counts missing to the
seventh-quietest day as being just as bad as missing to the busiest day of the month.
`benefit` is what the decision leans on, and the verdict is therefore built from it.

### 6.2 The verdict

The verdict is per venue and per rule and is based on the 95 % bootstrap interval of the
benefit:

| Verdict | Condition |
| --- | --- |
| `useful` — the benefit is verified | The whole interval above zero |
| `no_detectable_benefit` — the benefit is not verified | The interval contains zero |
| `harmful` — the choice lands on busier days | The whole interval below zero |

A second, secondary verdict says the same about accuracy: whether `hit_rate − chance_rate`
exceeds zero.

**"Not verified" is not "no benefit".** That is why every such verdict carries the minimum
detectable effect `MDE = 2.8 × sd / √windows`. With five windows it is large, and it is the
most important limitation of this dataset.

### 6.3 Why the bootstrap draws windows rather than days

Days from the same month share the origin, the training period and the month's weather; two
different months share nothing. Drawing days would count the same evidence many times over
and produce an interval that looks far more decisive than the data is. The same solution and
the same justification as in chapter 8 of `docs/EVALUATION.md`.

### 6.4 Calibration of the probabilities

The package publishes probabilities, so they have to be checked. Every candidate day produces
one pair — the probability given and whether the day ended up among the quietest — and chapter
5 of the report shows the pairs in six buckets. In a well-calibrated model the columns are
close to each other. A thin bucket says nothing, so `n` is on every row.

The table can be recomputed from the saved file `days.csv`; the report does not have to be
taken on its word.

### 6.5 Two pieces of hindsight the measurement uses

Neither is hidden, because both move the result slightly in the model's favour.

**The candidate set is defined by the actual values.** A day that turned out to be closed,
incompletely measured or a zero is excluded both from the actuals and from what the rule is
allowed to name. The rule is therefore not punished for proposing a closed day. That is a
defensible choice — a closure is an operational fact rather than an error of a ranking rule —
but it means the measurement does not cover the risk of "a proposed day turns out to be
closed". On the current data there are six such days in eight months, all at Kaupungintalo.

**`k` is taken from the number of candidates in the actuals.** Otherwise the named and the
true set would be different sizes and accuracy would not be defined at all. The same `k` also
goes into the random choice calculation, so it does not favour the rule in the comparison.

---

## 7. Measured results

Monthly sweep 2026-04 … 2026-08, `quiet_calendar`, threshold 20 %, five windows. Saved under
`data/quiet/`.

| Venue | Benefit | 95 % interval | Hit rate | Chance | Capture | MDE | Verdict |
| --- | ---: | --- | ---: | ---: | ---: | ---: | --- |
| Pekuri (1) | 7 % | −1 % … 17 % | 40 % | 21 % | 20 % | 14 % | not verified |
| Kaupungintalo (2) | 45 % | 25 % … 65 % | 67 % | 22 % | 72 % | 32 % | **verified** |

**At Kaupungintalo the method works.** The named days were on average 45 % quieter than the
median day, and that is 72 % of everything that was achievable even with hindsight. Accuracy
is three times what a guess gives. Most of the signal is calendar structure: closed Mondays
are excluded from the candidates, and the days around public holidays are genuinely and
predictably quiet.

**At Pekuri it does not work.** The benefit is 7 % and the interval contains zero. The hit
rate of 40 % is clearly above the 21 % of a random choice, but it does not turn into a
benefit.

### 7.1 Why Pekuri is hard

The difference is not that Pekuri's weekly rhythm is weaker — it is in fact stronger. The
difference builds up in three stages, and each takes its share.

| Stage | Pekuri | Kaupungintalo |
| --- | ---: | ---: |
| How much of the month is winnable (a full oracle) | 35 % | 63 % |
| The best possible weekday rule | 17 % | 44 % |
| The measured model | 7 % | 45 % |

**Stage 1: Pekuri has no quiet days to find.** 1.4 % of the candidate days fall below half of
the month's median day and **not one falls below 0.3 times it**. At Kaupungintalo the same
figures are 14.5 % and 11.6 %: there is a set of nearly empty days every month. Pekuri's month
is flat at the bottom, so even perfect hindsight would produce only a 35 % benefit instead of
63 %. Half of the difference is here, and no model can do anything about it.

**Stage 2: the weekday carries only half of what is findable at Pekuri.** If the rule knew the
month's true per-weekday means in advance, it would get 17 % at Pekuri, i.e. 49 % of
everything available; at Kaupungintalo 44 %, i.e. 70 %. The rest is day-level variation whose
explanation is not present in this dataset: the correlation of the weather with the residual
is 0.10-0.12 and an events calendar does not exist.

**Stage 3: at Pekuri the model does not even reach its own weekday ceiling.** The measured 7 %
is 41 % of the ceiling of 17 %. At Kaupungintalo 45 % is already the whole ceiling of 44 % —
there is nothing more to be had there from a better weekday estimate. The reason is drift in
the rhythm. Pekuri's Monday is the quietest day of the month in January (0.56 × the median)
and among its busiest in July (1.36):

| | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| January | 0.56 | 1.09 | 0.57 | 0.84 | 1.04 | 1.99 | 0.89 |
| April | 0.73 | 0.84 | 0.95 | 1.24 | 1.36 | 1.78 | 0.88 |
| July | 1.36 | 1.29 | 1.07 | 0.97 | 0.96 | 1.23 | 0.81 |

The spread between weekdays is 0.24 and the month-to-month variation of the *same* weekday is
0.18. The mean over the whole training window therefore describes a rhythm that no longer
exists in the month being forecast. A recency window does not fix this (chapter 5.3): eight
weeks hold eight observations per weekday, and the standard error of the mean, 0.41 / √8 ≈
0.15, is of the same order as the drift itself. Bias is traded for variance one for one.

**And a miss is expensive.** At both venues about 19 % of the days are above 1.5 × the median,
but at Pekuri the correct hits are only 0.7 × the median and therefore do not compensate for a
wrong choice, whereas Kaupungintalo's hits are 0.2-0.3 × and absorb the miss. Pekuri's worst
choices in the measured windows were Sun 05-10 (174 % of the median), Mon 06-22 (168 %) and
Mon 07-06 (150 %). This is not one oddity: removing the three worst choices would raise the
benefit from 7 % only to 13 %.

None of Pekuri's twelve busiest days appear in the maintained calendar. The three busiest are
the Fridays 05-15 (319 % of the median), 06-12 (302 %) and 08-14 (252 %). There is nothing in
the data that would separate them from an ordinary Friday.

This is a result, not a broken pipeline. The tool's job is to say so, and the forecast's
verdict paragraph says it every time Pekuri's September is asked about.

---

## 8. Outputs

One run is one directory `data/quiet/{run_id}/` and one row in `index.json`. The run
identifiers are deterministic and readable, so running the same month again overwrites its own
directory instead of accumulating near-identical results.

| File | Forecast | Sweep |
| --- | --- | --- |
| `report.md` | The answer, the whole month, the inputs, the caveats | The verdict, the results, the windows, the calibration |
| `days.csv` | Every day of the month per venue | Every candidate day: score, actual value, probability |
| `windows.csv` | – | One row per window, venue and rule |
| `metrics.json` | The set, candidacy, residuals, days | Per-window results |
| `verdicts.json` | The summary and the measured reliability | The pooled verdicts and the calibration |
| `config.json` | All the run's parameters | All the run's parameters |

Nothing in a run directory contains a clock time. That is the only way the determinism test
can be written at all. The creation time is in `index.json`, which is a registry rather than a
result.

---

## 9. The result in thirty seconds

The report opens with a paragraph that already contains the answer. If you want to check it
yourself, four figures carry the whole thing:

1. **The verdict and its interval.** Were the named days genuinely quieter, and does the
   interval clear zero.
2. **Accuracy against a random choice.** 40 % sounds bad and 67 % good, but neither means
   anything without knowing what a guess would give.
3. **The probability per day.** A flat 20 % on every day means the model does not separate
   them. A high individual figure means it does.
4. **The Ties column.** If it is greater than one, the model has no opinion about the ordering
   inside the group and the choice is yours.

---

## 10. Four ways to fool yourself

**Reading the model's separation as the realised benefit.** "The quietest fifth is 18 % below
the median day" is a sentence about the score. The realised benefit is 7 % or 45 % depending
on the venue, and only the measurement says which.

**Believing a single window.** Six days from one month is one draw. The pooled result from
several windows is evidence; an individual window is a description.

**Taking a rolling sweep's interval at face value.** Successive rolling windows share days, so
the interval is narrower than it really is. The headline figure is best read from the monthly
sweep.

**Generalising from one venue to another.** Kaupungintalo's 45 % says nothing about Pekuri.
The opening hours, the public holiday practice and the visitor profile differ, and that is
exactly why the measurement is made per venue.

---

## 11. What CANNOT be concluded from this

- **That the quietest day would be the best day.** The model says where there is free capacity.
  It does not know whether an event reaches its audience on a Sunday, nor whether the staff or
  the partners are available then.
- **That the choice of rule has been proven.** The default rule was chosen on the basis of
  these same windows, so its advantage over the other rules is an overestimate. The per-venue
  benefit, on the other hand, is measured outside the training period and it holds.
- **That the result would survive being acted upon.** If activation events start being held on
  the quiet days, they will change exactly the days the model forecasts. The measurement has to
  be repeated once the events begin, and the event days have to be marked, or they will distort
  both the day-of-week means and the next measurement.
- **That five windows would be enough.** The minimum detectable effect is included in every
  verdict for precisely this reason. A twelfth month is the single most important improvement
  to this measurement.
- **That `visitors_total` would be a visitor count.** It is the sum of entry and exit events,
  see the README. Every ratio in this document is a ratio, so the unit cancels out, but a
  threshold expressed in visitor events is not a headcount.

---

## 12. Next steps

In order, by impact:

1. **An events calendar as a feature.** The same conclusion as with the level forecast
   (`docs/EVALUATION.md` chapter 12). 78 % of Pekuri's within-month variation is currently
   unexplained, and an individual concert or group booking is the most likely explanation.
2. **A second year of history.** There are five monthly windows. With twelve the minimum
   detectable effect halves, and the public holiday factor would get Christmas and Midsummer
   for the first time.
3. **The opening calendar into the configuration.** Closed weekdays are currently inferred from
   the data with a 15 % threshold. That works, but maintained opening information would be the
   correct source, and it would remove the threshold entirely.
4. **Quietness at the hourly level.** An event does not last a whole day. The hourly profile
   already exists (`ovf_forecast.profile`), so "the quietest Tuesday afternoon of the month" is
   an extension of the same structure rather than a new model.
