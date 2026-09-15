# Forecast evaluation report: 2026-08-01 – 2026-08-31

Run id: `eval_v1_2026-07-31_2026-08-01_2026-08-31_baseline`

## 1. Verdict

Window 2026-08-01–2026-08-31 (31 days), training ends 2026-07-31, training window all, weather mode operational. Venue 1 (Pekuri): the model baseline made a mean daily error of 255.8 visitors, the main reference climatology_dow 128.0. The model loses to the reference statistically: a difference of +127.8 visitors per day (95 % interval +44.2…+184.1). The simple rule climatology_dow is better than the model on this window. This sample (31 days) would only have resolved a difference of 70.8 visitors, i.e. 55.3 % of the reference's MAE. The total for the period: forecast 20,173, actual 13,514, difference +49.3 %, 80 % interval 18,620–27,237. Venue 2 (Kaupungintalo): the model baseline made a mean daily error of 37.0 visitors, the main reference climatology_dow 36.8. No difference was detected: +0.2 visitors per day (95 % interval -10.6…+8.5). This sample (31 days) would only have resolved a difference of 10.6 visitors, i.e. 28.8 % of the reference's MAE; "no difference" therefore does not mean equivalence. The total for the period: forecast 4,335, actual 4,866, difference -10.9 %, 80 % interval 4,166–7,382. A single window's result is descriptive, not probative: the actual evidence comes from pooling several windows.

## 2. The window and the setup

- Origin (the last training day): **2026-07-31**
- Test period: **2026-08-01 – 2026-08-31** (31 days, horizons 1–31)
- Training window: `all`
- Models: baseline
- References: seasonal_naive, moving_average_28d, climatology_dow
- Main reference rule: `best`
- Weather modes: perfect, operational, climatology (the verdict comes from `operational`)
- Bootstrap: 10,000 resamples, block length 7 days, seed 20260101

| Venue | Training starts | Training days | Zero days | Nested origins | MASE denominator |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 212 | 21 | 12 | 163.08 |
| 2 (Kaupungintalo) | 2026-01-01 | 212 | 13 | 12 | 100.17 |

The prediction interval quantiles come from a nested backtest run entirely inside the training window: its last inner origin is the origin minus the horizon, so no inner forecast reaches into the test period.

## Venue 1 (Pekuri)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 20,173 | 13,514 | +6,659 | +49.3 % | 18,620 – 27,237 | no | 11,569 – 39,322 |
| climatology_dow | 14,172 | 13,514 | +658 | +4.9 % | 13,066 – 16,902 | yes | 8,597 – 25,386 |
| moving_average_28d | 17,464 | 13,514 | +3,950 | +29.2 % | 15,214 – 20,615 | no | 9,748 – 28,923 |
| seasonal_naive | 18,747 | 13,514 | +5,233 | +38.7 % | 18,747 – 26,305 | no | 9,632 – 38,311 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 255.8 | 281.1 | 1.569 | +214.8 | 35.2 | 127.9 | 83.3 | 0.58 | 49.0 | 31 |
| baseline | 1-7 | 244.8 | 267.4 | 1.501 | +244.8 | 18.0 | 122.4 | 64.0 | 0.71 | 43.6 | 7 |
| baseline | 8-14 | 196.8 | 219.7 | 1.207 | +36.0 | 26.5 | 98.4 | 53.9 | 0.86 | 33.6 | 7 |
| baseline | 15-30 | 284.7 | 307.8 | 1.746 | +276.1 | 45.9 | 142.3 | 103.3 | 0.41 | 57.5 | 17 |
| climatology_dow | all | 128.0 | 180.4 | 0.785 | +21.2 | 20.7 | 64.0 | 50.1 | 0.84 | 27.2 | 31 |
| climatology_dow | 1-7 | 82.8 | 95.4 | 0.508 | +24.4 | 15.0 | 41.4 | 40.2 | 1.00 | 17.6 | 7 |
| climatology_dow | 8-14 | 178.0 | 276.9 | 1.091 | -125.8 | 30.4 | 89.0 | 72.9 | 0.71 | 29.6 | 7 |
| climatology_dow | 15-30 | 126.0 | 155.0 | 0.773 | +80.5 | 19.1 | 63.0 | 44.7 | 0.82 | 30.1 | 17 |
| moving_average_28d | all | 200.8 | 225.6 | 1.231 | +127.4 | 23.0 | 100.4 | 55.7 | 0.74 | 41.7 | 31 |
| moving_average_28d | 1-7 | 131.1 | 145.7 | 0.804 | +131.1 | 12.6 | 65.5 | 47.0 | 1.00 | 27.3 | 7 |
| moving_average_28d | 8-14 | 219.8 | 264.4 | 1.348 | -19.1 | 34.0 | 109.9 | 58.1 | 0.71 | 38.2 | 7 |
| moving_average_28d | 15-30 | 221.7 | 235.1 | 1.360 | +186.2 | 22.7 | 110.9 | 58.3 | 0.65 | 49.0 | 17 |
| seasonal_naive | all | 218.6 | 271.8 | 1.341 | +168.8 | 29.9 | 109.3 | 80.0 | 0.77 | 42.0 | 31 |
| seasonal_naive | 1-7 | 196.4 | 227.6 | 1.205 | +163.9 | 11.7 | 98.2 | 80.2 | 1.00 | 36.4 | 7 |
| seasonal_naive | 8-14 | 170.3 | 242.1 | 1.044 | +13.7 | 30.9 | 85.1 | 67.2 | 1.00 | 28.6 | 7 |
| seasonal_naive | 15-30 | 247.6 | 298.8 | 1.519 | +234.7 | 37.0 | 123.8 | 85.2 | 0.59 | 49.9 | 17 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 128.0). The references' MAE: seasonal_naive 218.6, moving_average_28d 200.8, climatology_dow 128.0.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +127.8 | +44.2 … +184.1 | worse than the reference | -0.998 | -1.664 … -0.273 | 70.8 | 55.3 % | 3.17 | 0.055 | 0.111 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.58 (18/31) | 0.39 … 0.75 | too narrow | +214.8 | +84.6 … +306.1 | +49.3 % | systematically overestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 223.5 | 255.8 | 253.0 | +29.5 | 11.7 % |

`perfect` is the upper bound: what the model could do if the weather were known exactly. `climatology` is the lower bound: what it can do without a weather forecast. `operational` is the most realistic estimate and assumes a good weather forecast. The improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive figure means that knowing the weather helps**, and it is the share of the model's accuracy that rests on knowing the weather.

| Weather mode | Realised weather | Climatology |
| --- | --- | --- |
| perfect (the realised weather) | 31 | 0 |
| operational (realised days 1-16, climatology from 17) | 16 | 15 |
| climatology (climatology for the whole period) | 0 | 31 |

### 9. The worst days

**baseline**

| Day | Weekday | Actual | Forecast | Error | Possible cause |
| --- | --- | --- | --- | --- | --- |
| 2026-08-22 | Saturday | 287 | 789 | +502 | the model got climatology weather (horizon 22 days); weekend |
| 2026-08-04 | Tuesday | 397 | 835 | +438 | no identified cause, possibly an event the model does not know about |
| 2026-08-31 | Monday | 263 | 685 | +422 | the model got climatology weather (horizon 31 days) |
| 2026-08-14 | Friday | 1,084 | 668 | -416 | no identified cause, possibly an event the model does not know about |
| 2026-08-24 | Monday | 313 | 714 | +401 | the model got climatology weather (horizon 24 days) |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## Venue 2 (Kaupungintalo)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 4,335 | 4,866 | -531 | -10.9 % | 4,166 – 7,382 | yes | 1,647 – 11,230 |
| climatology_dow | 5,018 | 4,866 | +152 | +3.1 % | 4,268 – 5,629 | yes | 2,156 – 7,884 |
| moving_average_28d | 6,353 | 4,866 | +1,487 | +30.6 % | 5,730 – 8,160 | no | 820 – 12,683 |
| seasonal_naive | 5,393 | 4,866 | +527 | +10.8 % | 5,130 – 16,174 | no | 2,164 – 12,183 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 37.0 | 63.4 | 0.370 | -17.1 | 11.9 | 18.5 | 20.5 | 0.97 | 29.5 | 31 |
| baseline | 1-7 | 12.4 | 17.9 | 0.124 | -9.1 | 11.2 | 6.2 | 15.1 | 1.00 | 10.2 | 7 |
| baseline | 8-14 | 33.5 | 42.8 | 0.335 | -31.7 | 11.8 | 16.8 | 21.6 | 1.00 | 27.9 | 7 |
| baseline | 15-30 | 48.6 | 80.2 | 0.485 | -14.4 | 12.2 | 24.3 | 22.3 | 0.94 | 38.1 | 17 |
| climatology_dow | all | 36.8 | 60.3 | 0.367 | +4.9 | 11.0 | 18.4 | 12.7 | 0.77 | 27.5 | 31 |
| climatology_dow | 1-7 | 16.9 | 19.4 | 0.169 | +1.9 | 9.9 | 8.4 | 8.6 | 1.00 | 9.6 | 7 |
| climatology_dow | 8-14 | 25.6 | 40.2 | 0.255 | -9.5 | 10.3 | 12.8 | 9.1 | 0.71 | 19.7 | 7 |
| climatology_dow | 15-30 | 49.6 | 76.2 | 0.495 | +12.0 | 11.7 | 24.8 | 16.0 | 0.71 | 38.0 | 17 |
| moving_average_28d | all | 75.7 | 97.5 | 0.755 | +48.0 | 14.4 | 37.8 | 25.2 | 0.87 | 51.6 | 31 |
| moving_average_28d | 1-7 | 53.7 | 76.4 | 0.536 | +40.5 | 14.4 | 26.8 | 23.2 | 0.86 | 37.2 | 7 |
| moving_average_28d | 8-14 | 57.4 | 76.4 | 0.573 | +29.1 | 14.8 | 28.7 | 23.0 | 1.00 | 36.1 | 7 |
| moving_average_28d | 15-30 | 92.2 | 111.9 | 0.921 | +58.8 | 14.3 | 46.1 | 27.0 | 0.82 | 63.9 | 17 |
| seasonal_naive | all | 100.5 | 130.1 | 1.004 | +17.0 | 11.8 | 50.3 | 57.5 | 0.74 | 71.8 | 31 |
| seasonal_naive | 1-7 | 79.9 | 104.0 | 0.797 | +18.4 | 11.9 | 39.9 | 54.4 | 0.86 | 56.4 | 7 |
| seasonal_naive | 8-14 | 87.3 | 107.8 | 0.871 | +7.0 | 9.8 | 43.6 | 47.7 | 0.71 | 67.9 | 7 |
| seasonal_naive | 15-30 | 114.5 | 147.0 | 1.143 | +20.5 | 12.6 | 57.3 | 62.9 | 0.71 | 79.8 | 17 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 36.8). The references' MAE: seasonal_naive 100.5, moving_average_28d 75.7, climatology_dow 36.8.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +0.2 | -10.6 … +8.5 | no detectable difference from the reference | -0.006 | -0.205 … 0.295 | 10.6 | 28.8 % | 0.04 | 0.967 | 0.967 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.97 (30/31) | 0.83 … 1.00 | too wide | -17.1 | -38.8 … +2.4 | -10.9 % | no systematic bias |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 37.0 | 37.0 | 39.2 | +2.2 | 5.5 % |

`perfect` is the upper bound: what the model could do if the weather were known exactly. `climatology` is the lower bound: what it can do without a weather forecast. `operational` is the most realistic estimate and assumes a good weather forecast. The improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive figure means that knowing the weather helps**, and it is the share of the model's accuracy that rests on knowing the weather.

| Weather mode | Realised weather | Climatology |
| --- | --- | --- |
| perfect (the realised weather) | 31 | 0 |
| operational (realised days 1-16, climatology from 17) | 16 | 15 |
| climatology (climatology for the whole period) | 0 | 31 |

### 9. The worst days

**baseline**

| Day | Weekday | Actual | Forecast | Error | Possible cause |
| --- | --- | --- | --- | --- | --- |
| 2026-08-15 | Saturday | 371 | 155 | -216 | heavy rain 8.7 mm; weekend |
| 2026-08-27 | Thursday | 317 | 143 | -174 | the model got climatology weather (horizon 27 days) |
| 2026-08-26 | Wednesday | 21 | 173 | +152 | the model got climatology weather (horizon 26 days) |
| 2026-08-13 | Thursday | 284 | 190 | -94 | no identified cause, possibly an event the model does not know about |
| 2026-08-18 | Tuesday | 155 | 214 | +59 | heavy rain 7.0 mm; the model got climatology weather (horizon 18 days) |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## 8. Limitations

- **Sample size.** One window is 31 days from one origin. They are not 31 independent observations: they all share the same training set and the same month of weather.
- **A single window's verdict is descriptive, not probative.** The actual evidence comes from pooling several windows (`--sweep monthly` or `--sweep rolling`).
- **"No detectable difference" does not mean equivalence.** Read the MDE in section 5 before drawing a conclusion from it.
- **sMAPE does not ground the verdict**, because zero days break it.
- **There is about eight months of data from a single year.** Year-to-year seasonality cannot be learned, so a comparison against another year is impossible.
- **Ticket data is not used as a feature**, because it does not exist for the future.
- **Venue 1: the training window opens with 21 zero days** from before the sensor was installed. The evaluation does not remove them, because the training window is the one the user named; `--train-window` cuts them out. The zeros do not stay at the start: the seasonal feature `year_sin` is symmetric about midsummer, so January's zero days get the same value as the June days that mirror them and the model can read summer as January. If a forecast collapses towards zero in the middle of summer, this is the first place to look.
- **Venue 2: the training window opens with 7 zero days** from before the sensor was installed. The evaluation does not remove them, because the training window is the one the user named; `--train-window` cuts them out. The zeros do not stay at the start: the seasonal feature `year_sin` is symmetric about midsummer, so January's zero days get the same value as the June days that mirror them and the model can read summer as January. If a forecast collapses towards zero in the middle of summer, this is the first place to look.
