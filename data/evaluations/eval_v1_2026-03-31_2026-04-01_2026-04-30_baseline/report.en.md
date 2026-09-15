# Forecast evaluation report: 2026-04-01 – 2026-04-30

Run id: `eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline`

## 1. Verdict

Window 2026-04-01–2026-04-30 (30 days), training ends 2026-03-31, training window all, weather mode operational. Venue 1 (Pekuri): the model baseline made a mean daily error of 102.9 visitors, the main reference climatology_dow 96.2. No difference was detected: +6.7 visitors per day (95 % interval -3.2…+30.7). This sample (30 days) would only have resolved a difference of 34.5 visitors, i.e. 35.9 % of the reference's MAE; "no difference" therefore does not mean equivalence. The total for the period: forecast 13,639, actual 13,189, difference +3.4 %, 80 % interval 13,639–20,089. Venue 2 (Kaupungintalo): the model baseline made a mean daily error of 95.1 visitors, the main reference climatology_dow 75.1. The model loses to the reference statistically: a difference of +20.0 visitors per day (95 % interval +7.8…+48.9). The simple rule climatology_dow is better than the model on this window. This sample (30 days) would only have resolved a difference of 24.7 visitors, i.e. 32.9 % of the reference's MAE. The total for the period: forecast 6,155, actual 3,791, difference +62.4 %, 80 % interval 3,666–6,155. A single window's result is descriptive, not probative: the actual evidence comes from pooling several windows.

## 2. The window and the setup

- Origin (the last training day): **2026-03-31**
- Test period: **2026-04-01 – 2026-04-30** (30 days, horizons 1–30)
- Training window: `all`
- Models: baseline
- References: seasonal_naive, moving_average_28d, climatology_dow
- Main reference rule: `best`
- Weather modes: perfect, operational, climatology (the verdict comes from `operational`)
- Bootstrap: 10,000 resamples, block length 7 days, seed 20260101

| Venue | Training starts | Training days | Zero days | Nested origins | MASE denominator |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 90 | 21 | 3 | 141.18 |
| 2 (Kaupungintalo) | 2026-01-01 | 90 | 8 | 3 | 128.57 |

The prediction interval quantiles come from a nested backtest run entirely inside the training window: its last inner origin is the origin minus the horizon, so no inner forecast reaches into the test period.

## Venue 1 (Pekuri)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 13,639 | 13,189 | +450 | +3.4 % | 13,639 – 20,089 | no | 9,021 – 28,852 |
| climatology_dow | 13,292 | 13,189 | +103 | +0.8 % | 13,292 – 28,944 | no | 13,292 – 37,419 |
| moving_average_28d | 17,336 | 13,189 | +4,147 | +31.4 % | 17,336 – 20,813 | no | 12,546 – 27,846 |
| seasonal_naive | 15,172 | 13,189 | +1,983 | +15.0 % | 15,172 – 19,406 | no | 10,655 – 23,270 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

⚠ **The interval for these models is not calibrated:** climatology_dow (median relative error 1.86). The models of the nested backtest are trained on shorter and poorer data than the outer model, so their errors carry a level shift rather than mere spread. The interval inherits it. Read the difference in the total and the bias separately, not the interval.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 102.9 | 134.3 | 0.729 | +15.0 | 16.0 | 51.5 | 52.2 | 0.90 | 24.5 | 30 |
| baseline | 1-7 | 83.2 | 110.9 | 0.589 | -34.5 | 15.6 | 41.6 | 35.7 | 0.86 | 21.2 | 7 |
| baseline | 8-14 | 146.1 | 154.8 | 1.035 | +88.2 | 16.3 | 73.0 | 55.8 | 0.71 | 35.6 | 7 |
| baseline | 15-30 | 92.6 | 134.1 | 0.656 | +4.6 | 16.1 | 46.3 | 57.9 | 1.00 | 21.1 | 16 |
| climatology_dow | all | 96.2 | 122.7 | 0.681 | +3.4 | 49.5 | 48.1 | 80.8 | 0.33 | 22.3 | 30 |
| climatology_dow | 1-7 | 100.7 | 105.4 | 0.713 | -8.9 | 46.8 | 50.3 | 73.6 | 0.57 | 22.9 | 7 |
| climatology_dow | 8-14 | 100.5 | 124.1 | 0.712 | +58.0 | 73.5 | 50.3 | 92.9 | 0.14 | 24.3 | 7 |
| climatology_dow | 15-30 | 92.4 | 129.0 | 0.654 | -15.1 | 40.2 | 46.2 | 78.6 | 0.31 | 21.1 | 16 |
| moving_average_28d | all | 197.6 | 219.8 | 1.400 | +138.2 | 56.9 | 98.8 | 48.9 | 0.40 | 41.9 | 30 |
| moving_average_28d | 1-7 | 143.2 | 156.9 | 1.014 | +122.6 | 38.7 | 71.6 | 45.3 | 0.43 | 29.0 | 7 |
| moving_average_28d | 8-14 | 202.9 | 238.7 | 1.437 | +189.4 | 88.2 | 101.4 | 55.7 | 0.29 | 46.8 | 7 |
| moving_average_28d | 15-30 | 219.1 | 234.3 | 1.552 | +122.7 | 51.2 | 109.6 | 47.4 | 0.44 | 45.5 | 16 |
| seasonal_naive | all | 129.5 | 158.1 | 0.917 | +66.1 | 26.1 | 64.8 | 33.6 | 0.67 | 28.1 | 30 |
| seasonal_naive | 1-7 | 114.7 | 120.2 | 0.813 | +42.7 | 16.0 | 57.4 | 31.6 | 0.57 | 24.8 | 7 |
| seasonal_naive | 8-14 | 146.1 | 164.6 | 1.035 | +109.6 | 27.7 | 73.1 | 35.4 | 0.43 | 33.2 | 7 |
| seasonal_naive | 15-30 | 128.7 | 169.4 | 0.912 | +57.3 | 29.8 | 64.3 | 33.7 | 0.81 | 27.3 | 16 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 96.2). The references' MAE: seasonal_naive 129.5, moving_average_28d 197.6, climatology_dow 96.2.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +6.7 | -3.2 … +30.7 | no detectable difference from the reference | -0.070 | -0.314 … 0.034 | 34.5 | 35.9 % | 0.56 | 0.610 | 0.610 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.90 (27/30) | 0.73 … 0.98 | calibrated | +15.0 | -16.7 … +56.4 | +3.4 % | no systematic bias |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 108.1 | 102.9 | 107.9 | -0.2 | -0.2 % |

`perfect` is the upper bound: what the model could do if the weather were known exactly. `climatology` is the lower bound: what it can do without a weather forecast. `operational` is the most realistic estimate and assumes a good weather forecast. The improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive figure means that knowing the weather helps**, and it is the share of the model's accuracy that rests on knowing the weather.

⚠ **The improvement is negative**, i.e. on this window the model forecasts *better* on average weather than on the realised weather. That is not a measurement error but a result: the weather dependence the model learned does not generalise to this period, and the realised weather pushes the forecast the wrong way. The weather features fit the noise of the training period more than the visitors' real behaviour in the weather.

| Weather mode | Realised weather | Climatology |
| --- | --- | --- |
| perfect (the realised weather) | 30 | 0 |
| operational (realised days 1-16, climatology from 17) | 16 | 14 |
| climatology (climatology for the whole period) | 0 | 30 |

### 9. The worst days

**baseline**

| Day | Weekday | Actual | Forecast | Error | Possible cause |
| --- | --- | --- | --- | --- | --- |
| 2026-04-16 | Thursday | 788 | 386 | -402 | no identified cause, possibly an event the model does not know about |
| 2026-04-24 | Friday | 683 | 472 | -211 | the model got climatology weather (horizon 24 days) |
| 2026-04-05 | Sunday | 485 | 280 | -205 | public holiday: Toinen pääsiäispäivä; weekend |
| 2026-04-10 | Friday | 625 | 422 | -203 | no identified cause, possibly an event the model does not know about |
| 2026-04-08 | Wednesday | 360 | 543 | +183 | no identified cause, possibly an event the model does not know about |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## Venue 2 (Kaupungintalo)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 6,155 | 3,791 | +2,364 | +62.4 % | 3,666 – 6,155 | yes | 1,409 – 8,945 |
| climatology_dow | 5,346 | 3,791 | +1,555 | +41.0 % | 5,346 – 7,603 | no | 2,595 – 12,230 |
| moving_average_28d | 5,802 | 3,791 | +2,011 | +53.0 % | 5,554 – 7,626 | no | 1,213 – 12,548 |
| seasonal_naive | 7,656 | 3,791 | +3,865 | +102.0 % | 7,093 – 14,491 | no | 3,273 – 20,184 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

⚠ **The interval for these models is not calibrated:** baseline (median relative error 0.65). The models of the nested backtest are trained on shorter and poorer data than the outer model, so their errors carry a level shift rather than mere spread. The interval inherits it. Read the difference in the total and the bias separately, not the interval.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 95.1 | 117.3 | 0.740 | +78.8 | 11.9 | 47.6 | 20.0 | 0.80 | 69.0 ⚠ | 30 |
| baseline | 1-7 | 80.9 | 102.2 | 0.629 | +34.3 | 19.4 | 40.5 | 18.9 | 0.57 | 80.0 ⚠ | 7 |
| baseline | 8-14 | 94.6 | 111.1 | 0.736 | +94.6 | 8.7 | 47.3 | 16.0 | 1.00 | 49.6 | 7 |
| baseline | 15-30 | 101.5 | 125.8 | 0.790 | +91.3 | 10.0 | 50.8 | 22.1 | 0.81 | 72.8 | 16 |
| climatology_dow | all | 75.1 | 95.6 | 0.584 | +51.8 | 18.1 | 37.6 | 28.8 | 0.70 | 61.5 ⚠ | 30 |
| climatology_dow | 1-7 | 81.3 | 102.3 | 0.632 | +28.9 | 22.2 | 40.7 | 31.8 | 0.71 | 81.5 ⚠ | 7 |
| climatology_dow | 8-14 | 52.0 | 63.4 | 0.404 | +17.8 | 7.9 | 26.0 | 24.0 | 1.00 | 32.6 | 7 |
| climatology_dow | 15-30 | 82.6 | 103.9 | 0.642 | +76.7 | 20.7 | 41.3 | 29.6 | 0.56 | 65.3 | 16 |
| moving_average_28d | all | 88.2 | 106.3 | 0.686 | +67.0 | 14.7 | 44.1 | 29.2 | 0.83 | 68.4 ⚠ | 30 |
| moving_average_28d | 1-7 | 103.9 | 119.5 | 0.808 | +46.0 | 26.3 | 52.0 | 29.9 | 0.71 | 82.1 ⚠ | 7 |
| moving_average_28d | 8-14 | 67.5 | 86.8 | 0.525 | +34.8 | 13.1 | 33.7 | 21.9 | 1.00 | 45.8 | 7 |
| moving_average_28d | 15-30 | 90.3 | 107.9 | 0.703 | +90.3 | 10.3 | 45.2 | 32.0 | 0.81 | 72.3 | 16 |
| seasonal_naive | all | 138.6 | 171.3 | 1.078 | +128.8 | 27.3 | 69.3 | 54.6 | 0.67 | 78.9 ⚠ | 30 |
| seasonal_naive | 1-7 | 112.1 | 140.2 | 0.872 | +98.7 | 19.9 | 56.1 | 68.2 | 0.57 | 90.2 ⚠ | 7 |
| seasonal_naive | 8-14 | 105.0 | 127.8 | 0.817 | +87.6 | 7.7 | 52.5 | 51.3 | 1.00 | 45.9 | 7 |
| seasonal_naive | 15-30 | 164.8 | 198.2 | 1.282 | +160.1 | 39.1 | 82.4 | 50.2 | 0.56 | 88.4 | 16 |

⚠ sMAPE is flagged unreliable: the test period contains zero days (at most 2 in a bucket). On a zero day the symmetric ratio hits its ceiling regardless of how close the forecast was. sMAPE does not ground the verdict.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 75.1). The references' MAE: seasonal_naive 138.6, moving_average_28d 88.2, climatology_dow 75.1.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +20.0 | +7.8 … +48.9 | worse than the reference | -0.266 | -0.759 … -0.107 | 24.7 | 32.9 % | 1.42 | 0.293 | 0.586 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.80 (24/30) | 0.61 … 0.92 | calibrated | +78.8 | +52.0 … +125.8 | +62.4 % | systematically overestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 101.5 | 95.1 | 81.5 | -20.0 | -24.5 % |

`perfect` is the upper bound: what the model could do if the weather were known exactly. `climatology` is the lower bound: what it can do without a weather forecast. `operational` is the most realistic estimate and assumes a good weather forecast. The improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive figure means that knowing the weather helps**, and it is the share of the model's accuracy that rests on knowing the weather.

⚠ **The improvement is negative**, i.e. on this window the model forecasts *better* on average weather than on the realised weather. That is not a measurement error but a result: the weather dependence the model learned does not generalise to this period, and the realised weather pushes the forecast the wrong way. The weather features fit the noise of the training period more than the visitors' real behaviour in the weather.

| Weather mode | Realised weather | Climatology |
| --- | --- | --- |
| perfect (the realised weather) | 30 | 0 |
| operational (realised days 1-16, climatology from 17) | 16 | 14 |
| climatology (climatology for the whole period) | 0 | 30 |

### 9. The worst days

**baseline**

| Day | Weekday | Actual | Forecast | Error | Possible cause |
| --- | --- | --- | --- | --- | --- |
| 2026-04-18 | Saturday | 5 | 267 | +262 | the model got climatology weather (horizon 18 days); weekend |
| 2026-04-15 | Wednesday | 53 | 277 | +224 | no identified cause, possibly an event the model does not know about |
| 2026-04-03 | Friday | 0 | 196 | +196 | public holiday: Pitkäperjantai; actual 0, the venue was probably closed |
| 2026-04-12 | Sunday | 85 | 274 | +189 | weekend |
| 2026-04-21 | Tuesday | 51 | 229 | +178 | the model got climatology weather (horizon 21 days) |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## 8. Limitations

- **Sample size.** One window is 30 days from one origin. They are not 30 independent observations: they all share the same training set and the same month of weather.
- **A single window's verdict is descriptive, not probative.** The actual evidence comes from pooling several windows (`--sweep monthly` or `--sweep rolling`).
- **"No detectable difference" does not mean equivalence.** Read the MDE in section 5 before drawing a conclusion from it.
- **sMAPE does not ground the verdict**, because zero days break it.
- **There is about eight months of data from a single year.** Year-to-year seasonality cannot be learned, so a comparison against another year is impossible.
- **Ticket data is not used as a feature**, because it does not exist for the future.
- **Venue 1: the training window opens with 21 zero days** from before the sensor was installed. The evaluation does not remove them, because the training window is the one the user named; `--train-window` cuts them out. The zeros do not stay at the start: the seasonal feature `year_sin` is symmetric about midsummer, so January's zero days get the same value as the June days that mirror them and the model can read summer as January. If a forecast collapses towards zero in the middle of summer, this is the first place to look.
- **Venue 2: the training window opens with 7 zero days** from before the sensor was installed. The evaluation does not remove them, because the training window is the one the user named; `--train-window` cuts them out. The zeros do not stay at the start: the seasonal feature `year_sin` is symmetric about midsummer, so January's zero days get the same value as the June days that mirror them and the model can read summer as January. If a forecast collapses towards zero in the middle of summer, this is the first place to look.
