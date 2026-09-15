# Forecast evaluation report: 2026-06-01 – 2026-06-30

Run id: `eval_v1_2026-05-31_2026-06-01_2026-06-30_baseline`

## 1. Verdict

Window 2026-06-01–2026-06-30 (30 days), training ends 2026-05-31, training window all, weather mode operational. Venue 1 (Pekuri): the model baseline made a mean daily error of 305.0 visitors, the main reference climatology_dow 138.9. The model loses to the reference statistically: a difference of +166.1 visitors per day (95 % interval +62.6…+264.5). The simple rule climatology_dow is better than the model on this window. This sample (30 days) would only have resolved a difference of 102.0 visitors, i.e. 73.4 % of the reference's MAE. The total for the period: forecast 2,961, actual 11,865, difference -75.0 %, 80 % interval 2,166–3,328. Venue 2 (Kaupungintalo): the model baseline made a mean daily error of 60.7 visitors, the main reference climatology_dow 44.5. No difference was detected: +16.2 visitors per day (95 % interval -9.0…+41.3). This sample (30 days) would only have resolved a difference of 36.7 visitors, i.e. 82.5 % of the reference's MAE; "no difference" therefore does not mean equivalence. The total for the period: forecast 2,900, actual 4,254, difference -31.8 %, 80 % interval 2,344–3,730. A single window's result is descriptive, not probative: the actual evidence comes from pooling several windows.

## 2. The window and the setup

- Origin (the last training day): **2026-05-31**
- Test period: **2026-06-01 – 2026-06-30** (30 days, horizons 1–30)
- Training window: `all`
- Models: baseline
- References: seasonal_naive, moving_average_28d, climatology_dow
- Main reference rule: `best`
- Weather modes: perfect, operational, climatology (the verdict comes from `operational`)
- Bootstrap: 10,000 resamples, block length 7 days, seed 20260101

| Venue | Training starts | Training days | Zero days | Nested origins | MASE denominator |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 151 | 21 | 11 | 170.43 |
| 2 (Kaupungintalo) | 2026-01-01 | 151 | 10 | 11 | 115.36 |

The prediction interval quantiles come from a nested backtest run entirely inside the training window: its last inner origin is the origin minus the horizon, so no inner forecast reaches into the test period.

## Venue 1 (Pekuri)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2,961 | 11,865 | -8,904 | -75.0 % | 2,166 – 3,328 | no | 1,695 – 4,228 |
| climatology_dow | 13,327 | 11,865 | +1,462 | +12.3 % | 13,327 – 19,805 | no | 9,493 – 26,445 |
| moving_average_28d | 14,457 | 11,865 | +2,592 | +21.8 % | 11,717 – 15,181 | yes | 7,548 – 21,891 |
| seasonal_naive | 13,351 | 11,865 | +1,486 | +12.5 % | 11,444 – 15,998 | yes | 7,750 – 20,133 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 305.0 | 375.3 | 1.790 | -296.8 | 33.9 | 152.5 | 252.9 | 0.27 | 142.4 | 30 |
| baseline | 1-7 | 97.2 | 121.0 | 0.570 | -61.9 | 19.8 | 48.6 | 23.9 | 0.71 | 26.9 | 7 |
| baseline | 8-14 | 358.6 | 494.9 | 2.104 | -358.6 | 40.4 | 179.3 | 293.5 | 0.43 | 126.2 | 7 |
| baseline | 15-30 | 372.5 | 388.0 | 2.186 | -372.5 | 37.3 | 186.3 | 335.3 | 0.00 | 200.0 | 16 |
| climatology_dow | all | 138.9 | 201.7 | 0.815 | +48.7 | 32.7 | 69.5 | 53.2 | 0.73 | 31.0 | 30 |
| climatology_dow | 1-7 | 110.7 | 124.9 | 0.649 | +71.1 | 21.2 | 55.3 | 54.7 | 0.71 | 28.7 | 7 |
| climatology_dow | 8-14 | 160.2 | 259.1 | 0.940 | -16.9 | 25.0 | 80.1 | 61.8 | 0.71 | 26.6 | 7 |
| climatology_dow | 15-30 | 142.0 | 200.3 | 0.833 | +67.6 | 41.2 | 71.0 | 48.8 | 0.75 | 33.9 | 16 |
| moving_average_28d | all | 150.4 | 191.0 | 0.883 | +86.4 | 21.6 | 75.2 | 46.0 | 0.83 | 35.5 | 30 |
| moving_average_28d | 1-7 | 150.0 | 171.8 | 0.880 | +104.2 | 26.3 | 75.0 | 34.0 | 0.86 | 38.9 | 7 |
| moving_average_28d | 8-14 | 196.5 | 269.4 | 1.153 | +16.2 | 20.6 | 98.2 | 80.9 | 0.86 | 37.4 | 7 |
| moving_average_28d | 15-30 | 130.5 | 153.9 | 0.766 | +109.3 | 20.0 | 65.2 | 36.0 | 0.81 | 33.2 | 16 |
| seasonal_naive | all | 186.1 | 263.4 | 1.092 | +49.5 | 32.4 | 93.1 | 53.7 | 0.60 | 39.2 | 30 |
| seasonal_naive | 1-7 | 171.7 | 197.3 | 1.008 | +48.0 | 15.8 | 85.9 | 47.8 | 0.71 | 41.7 | 7 |
| seasonal_naive | 8-14 | 267.7 | 374.6 | 1.571 | -40.0 | 56.9 | 133.9 | 107.2 | 0.43 | 49.7 | 7 |
| seasonal_naive | 15-30 | 156.8 | 227.4 | 0.920 | +89.4 | 29.1 | 78.4 | 32.9 | 0.62 | 33.4 | 16 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 138.9). The references' MAE: seasonal_naive 186.1, moving_average_28d 150.4, climatology_dow 138.9.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +166.1 | +62.6 … +264.5 | worse than the reference | -1.196 | -1.835 … -0.469 | 102.0 | 73.4 % | 2.63 | 0.043 | 0.087 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.27 (8/30) | 0.12 … 0.46 | too narrow | -296.8 | -424.1 … -167.4 | -75.0 % | systematically underestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 305.0 | 305.0 | 303.6 | -1.4 | -0.5 % |

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
| 2026-06-12 | Friday | 1,113 | 0 | -1,113 | no identified cause, possibly an event the model does not know about |
| 2026-06-22 | Monday | 620 | 0 | -620 | the model got climatology weather (horizon 22 days) |
| 2026-06-15 | Monday | 513 | 0 | -513 | no identified cause, possibly an event the model does not know about |
| 2026-06-23 | Tuesday | 457 | 0 | -457 | the model got climatology weather (horizon 23 days) |
| 2026-06-13 | Saturday | 449 | 0 | -449 | weekend |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## Venue 2 (Kaupungintalo)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 2,900 | 4,254 | -1,354 | -31.8 % | 2,344 – 3,730 | no | 1,092 – 5,751 |
| climatology_dow | 4,815 | 4,254 | +561 | +13.2 % | 4,059 – 5,882 | yes | 2,012 – 8,866 |
| moving_average_28d | 5,159 | 4,254 | +905 | +21.3 % | 4,024 – 6,146 | yes | 880 – 9,806 |
| seasonal_naive | 3,401 | 4,254 | -853 | -20.1 % | 3,166 – 10,448 | yes | 1,084 – 10,104 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 60.7 | 78.5 | 0.526 | -45.2 | 12.3 | 30.4 | 13.5 | 0.67 | 62.1 ⚠ | 30 |
| baseline | 1-7 | 35.6 | 47.4 | 0.309 | -34.6 | 10.3 | 17.8 | 6.7 | 1.00 | 24.0 | 7 |
| baseline | 8-14 | 44.2 | 58.5 | 0.383 | -24.2 | 11.6 | 22.1 | 11.4 | 0.86 | 31.9 | 7 |
| baseline | 15-30 | 78.9 | 95.3 | 0.684 | -58.9 | 13.5 | 39.5 | 17.4 | 0.44 | 92.0 ⚠ | 16 |
| climatology_dow | all | 44.5 | 70.1 | 0.386 | +18.7 | 15.0 | 22.3 | 15.4 | 0.87 | 38.2 ⚠ | 30 |
| climatology_dow | 1-7 | 23.7 | 30.3 | 0.205 | +23.7 | 7.2 | 11.8 | 17.4 | 1.00 | 17.3 | 7 |
| climatology_dow | 8-14 | 41.9 | 51.6 | 0.363 | -9.8 | 10.4 | 20.9 | 12.8 | 0.86 | 28.3 | 7 |
| climatology_dow | 15-30 | 54.8 | 87.4 | 0.475 | +29.0 | 20.4 | 27.4 | 15.7 | 0.81 | 51.7 ⚠ | 16 |
| moving_average_28d | all | 71.4 | 93.3 | 0.619 | +30.2 | 15.8 | 35.7 | 18.5 | 0.77 | 60.6 ⚠ | 30 |
| moving_average_28d | 1-7 | 42.6 | 65.0 | 0.369 | +32.0 | 12.2 | 21.3 | 19.0 | 0.86 | 36.1 | 7 |
| moving_average_28d | 8-14 | 63.7 | 77.0 | 0.552 | -1.5 | 14.7 | 31.9 | 14.2 | 1.00 | 39.6 | 7 |
| moving_average_28d | 15-30 | 87.4 | 109.0 | 0.757 | +43.2 | 17.8 | 43.7 | 20.2 | 0.62 | 80.5 ⚠ | 16 |
| seasonal_naive | all | 62.4 | 76.0 | 0.541 | -28.4 | 14.1 | 31.2 | 20.2 | 0.83 | 57.9 ⚠ | 30 |
| seasonal_naive | 1-7 | 53.1 | 62.3 | 0.461 | -27.7 | 10.3 | 26.6 | 21.8 | 1.00 | 39.7 | 7 |
| seasonal_naive | 8-14 | 61.1 | 72.8 | 0.530 | -61.1 | 14.4 | 30.6 | 14.6 | 0.86 | 48.2 | 7 |
| seasonal_naive | 15-30 | 67.1 | 82.5 | 0.581 | -14.4 | 15.6 | 33.5 | 21.9 | 0.75 | 70.2 ⚠ | 16 |

⚠ sMAPE is flagged unreliable: the test period contains zero days (at most 3 in a bucket). On a zero day the symmetric ratio hits its ceiling regardless of how close the forecast was. sMAPE does not ground the verdict.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 44.5). The references' MAE: seasonal_naive 62.4, moving_average_28d 71.4, climatology_dow 44.5.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +16.2 | -9.0 … +41.3 | no detectable difference from the reference | -0.363 | -1.364 … 0.126 | 36.7 | 82.5 % | 1.00 | 0.259 | 0.259 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.67 (20/30) | 0.47 … 0.83 | calibrated | -45.2 | -64.3 … -28.6 | -31.8 % | systematically underestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 56.9 | 60.7 | 63.1 | +6.2 | 9.9 % |

`perfect` is the upper bound: what the model could do if the weather were known exactly. `climatology` is the lower bound: what it can do without a weather forecast. `operational` is the most realistic estimate and assumes a good weather forecast. The improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive figure means that knowing the weather helps**, and it is the share of the model's accuracy that rests on knowing the weather.

| Weather mode | Realised weather | Climatology |
| --- | --- | --- |
| perfect (the realised weather) | 30 | 0 |
| operational (realised days 1-16, climatology from 17) | 16 | 14 |
| climatology (climatology for the whole period) | 0 | 30 |

### 9. The worst days

**baseline**

| Day | Weekday | Actual | Forecast | Error | Possible cause |
| --- | --- | --- | --- | --- | --- |
| 2026-06-18 | Thursday | 239 | 57 | -182 | the model got climatology weather (horizon 18 days) |
| 2026-06-16 | Tuesday | 316 | 143 | -173 | heavy rain 9.5 mm |
| 2026-06-27 | Saturday | 207 | 69 | -138 | the model got climatology weather (horizon 27 days); weekend |
| 2026-06-09 | Tuesday | 309 | 178 | -131 | no identified cause, possibly an event the model does not know about |
| 2026-06-24 | Wednesday | 204 | 77 | -127 | the model got climatology weather (horizon 24 days) |

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
