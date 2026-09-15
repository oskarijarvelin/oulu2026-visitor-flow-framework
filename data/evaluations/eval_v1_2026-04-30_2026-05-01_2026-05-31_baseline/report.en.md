# Forecast evaluation report: 2026-05-01 – 2026-05-31

Run id: `eval_v1_2026-04-30_2026-05-01_2026-05-31_baseline`

## 1. Verdict

Window 2026-05-01–2026-05-31 (31 days), training ends 2026-04-30, training window all, weather mode operational. Venue 1 (Pekuri): the model baseline made a mean daily error of 179.5 visitors, the main reference moving_average_28d 187.4. No difference was detected: -7.9 visitors per day (95 % interval -58.5…+23.6). This sample (31 days) would only have resolved a difference of 69.0 visitors, i.e. 36.8 % of the reference's MAE; "no difference" therefore does not mean equivalence. The total for the period: forecast 11,880, actual 14,521, difference -18.2 %, 80 % interval 10,683–13,840. Venue 2 (Kaupungintalo): the model baseline made a mean daily error of 75.8 visitors, the main reference climatology_dow 71.5. No difference was detected: +4.3 visitors per day (95 % interval -4.6…+31.9). This sample (31 days) would only have resolved a difference of 32.3 visitors, i.e. 45.2 % of the reference's MAE; "no difference" therefore does not mean equivalence. The total for the period: forecast 3,228, actual 5,149, difference -37.3 %, 80 % interval 2,926–4,685. A single window's result is descriptive, not probative: the actual evidence comes from pooling several windows.

## 2. The window and the setup

- Origin (the last training day): **2026-04-30**
- Test period: **2026-05-01 – 2026-05-31** (31 days, horizons 1–31)
- Training window: `all`
- Models: baseline
- References: seasonal_naive, moving_average_28d, climatology_dow
- Main reference rule: `best`
- Weather modes: perfect, operational, climatology (the verdict comes from `operational`)
- Bootstrap: 10,000 resamples, block length 7 days, seed 20260101

| Venue | Training starts | Training days | Zero days | Nested origins | MASE denominator |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 120 | 21 | 7 | 144.46 |
| 2 (Kaupungintalo) | 2026-01-01 | 120 | 10 | 7 | 121.54 |

The prediction interval quantiles come from a nested backtest run entirely inside the training window: its last inner origin is the origin minus the horizon, so no inner forecast reaches into the test period.

## Venue 1 (Pekuri)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 11,880 | 14,521 | -2,641 | -18.2 % | 10,683 – 13,840 | no | 7,585 – 17,753 |
| climatology_dow | 14,067 | 14,521 | -454 | -3.1 % | 14,067 – 25,416 | yes | 12,295 – 33,932 |
| moving_average_28d | 13,564 | 14,521 | -957 | -6.6 % | 11,162 – 14,242 | no | 7,530 – 19,096 |
| seasonal_naive | 13,102 | 14,521 | -1,419 | -9.8 % | 11,107 – 14,783 | yes | 7,884 – 19,070 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

⚠ **The interval for these models is not calibrated:** climatology_dow (median relative error 1.36). The models of the nested backtest are trained on shorter and poorer data than the outer model, so their errors carry a level shift rather than mere spread. The interval inherits it. Read the difference in the total and the bias separately, not the interval.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 179.5 | 260.2 | 1.242 | -85.2 | 30.9 | 89.7 | 79.0 | 0.65 | 37.4 | 31 |
| baseline | 1-7 | 180.2 | 232.7 | 1.247 | -82.0 | 32.8 | 90.1 | 56.3 | 0.57 | 36.6 | 7 |
| baseline | 8-14 | 207.2 | 267.5 | 1.434 | -185.5 | 32.8 | 103.6 | 94.6 | 0.57 | 43.2 | 7 |
| baseline | 15-30 | 167.8 | 267.8 | 1.162 | -45.2 | 29.3 | 83.9 | 81.9 | 0.71 | 35.4 | 17 |
| climatology_dow | all | 187.6 | 250.8 | 1.298 | -14.7 | 61.8 | 93.8 | 63.0 | 0.48 | 38.0 | 31 |
| climatology_dow | 1-7 | 192.3 | 241.0 | 1.331 | -26.9 | 82.3 | 96.1 | 63.3 | 0.43 | 37.2 | 7 |
| climatology_dow | 8-14 | 170.8 | 207.6 | 1.182 | -100.2 | 28.6 | 85.4 | 54.9 | 0.71 | 35.7 | 7 |
| climatology_dow | 15-30 | 192.5 | 270.2 | 1.333 | +25.6 | 67.0 | 96.3 | 66.2 | 0.41 | 39.3 | 17 |
| moving_average_28d | all | 187.4 | 236.4 | 1.297 | -30.9 | 24.8 | 93.7 | 60.6 | 0.68 | 39.7 | 31 |
| moving_average_28d | 1-7 | 152.8 | 189.4 | 1.058 | -34.8 | 22.7 | 76.4 | 44.9 | 0.71 | 32.3 | 7 |
| moving_average_28d | 8-14 | 196.2 | 227.0 | 1.358 | -108.0 | 32.5 | 98.1 | 43.0 | 0.57 | 38.7 | 7 |
| moving_average_28d | 15-30 | 198.0 | 256.7 | 1.371 | +2.5 | 22.5 | 99.0 | 74.4 | 0.71 | 43.1 | 17 |
| seasonal_naive | all | 220.9 | 286.8 | 1.529 | -45.8 | 40.6 | 110.4 | 88.5 | 0.48 | 45.5 | 31 |
| seasonal_naive | 1-7 | 268.0 | 309.9 | 1.855 | -66.3 | 53.5 | 134.0 | 105.0 | 0.14 | 56.5 | 7 |
| seasonal_naive | 8-14 | 229.6 | 282.2 | 1.589 | -139.6 | 38.5 | 114.8 | 108.5 | 0.43 | 47.5 | 7 |
| seasonal_naive | 15-30 | 197.9 | 278.7 | 1.370 | +1.3 | 36.1 | 98.9 | 73.5 | 0.65 | 40.1 | 17 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **moving_average_28d** (MAE 187.4). The references' MAE: seasonal_naive 220.9, moving_average_28d 187.4, climatology_dow 187.6.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | -7.9 | -58.5 … +23.6 | no detectable difference from the reference | 0.042 | -0.131 … 0.293 | 69.0 | 36.8 % | -0.32 | 0.740 | 1.000 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.65 (20/31) | 0.45 … 0.81 | calibrated | -85.2 | -206.8 … -35.9 | -18.2 % | systematically underestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 177.4 | 179.5 | 183.9 | +6.5 | 3.5 % |

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
| 2026-05-15 | Friday | 1,174 | 441 | -733 | no identified cause, possibly an event the model does not know about |
| 2026-05-26 | Tuesday | 890 | 319 | -571 | the model got climatology weather (horizon 26 days) |
| 2026-05-05 | Tuesday | 841 | 364 | -477 | heavy rain 9.6 mm |
| 2026-05-13 | Wednesday | 731 | 269 | -462 | no identified cause, possibly an event the model does not know about |
| 2026-05-30 | Saturday | 265 | 700 | +435 | the model got climatology weather (horizon 30 days); weekend |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## Venue 2 (Kaupungintalo)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 3,228 | 5,149 | -1,922 | -37.3 % | 2,926 – 4,685 | no | 1,160 – 6,928 |
| climatology_dow | 5,148 | 5,149 | -1 | -0.0 % | 4,780 – 6,921 | yes | 1,923 – 10,769 |
| moving_average_28d | 3,800 | 5,149 | -1,349 | -26.2 % | 3,278 – 4,812 | no | 641 – 7,982 |
| seasonal_naive | 4,180 | 5,149 | -969 | -18.8 % | 4,016 – 7,038 | yes | 1,263 – 11,923 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 75.8 | 108.6 | 0.624 | -62.0 | 13.0 | 37.9 | 17.8 | 0.74 | 48.0 | 31 |
| baseline | 1-7 | 100.0 | 150.3 | 0.823 | -92.5 | 15.3 | 50.0 | 20.5 | 0.86 | 49.9 | 7 |
| baseline | 8-14 | 60.9 | 73.2 | 0.501 | -39.8 | 11.5 | 30.4 | 10.7 | 0.86 | 50.2 | 7 |
| baseline | 15-30 | 72.0 | 100.0 | 0.592 | -58.6 | 12.7 | 36.0 | 19.6 | 0.65 | 46.4 | 17 |
| climatology_dow | all | 71.5 | 95.3 | 0.588 | -0.0 | 10.4 | 35.7 | 22.7 | 0.97 | 42.9 | 31 |
| climatology_dow | 1-7 | 98.2 | 139.2 | 0.808 | -30.5 | 12.3 | 49.1 | 34.7 | 0.86 | 51.7 | 7 |
| climatology_dow | 8-14 | 56.1 | 63.9 | 0.462 | +12.5 | 6.8 | 28.1 | 18.6 | 1.00 | 37.4 | 7 |
| climatology_dow | 15-30 | 66.8 | 83.0 | 0.550 | +7.4 | 11.1 | 33.4 | 19.5 | 1.00 | 41.5 | 17 |
| moving_average_28d | all | 82.9 | 115.3 | 0.682 | -43.5 | 14.7 | 41.5 | 22.7 | 0.77 | 54.2 | 31 |
| moving_average_28d | 1-7 | 108.2 | 163.3 | 0.890 | -71.4 | 17.4 | 54.1 | 42.9 | 0.86 | 57.4 | 7 |
| moving_average_28d | 8-14 | 65.3 | 87.2 | 0.537 | -28.4 | 13.8 | 32.7 | 13.0 | 0.57 | 50.7 | 7 |
| moving_average_28d | 15-30 | 79.8 | 100.6 | 0.656 | -38.3 | 14.0 | 39.9 | 18.4 | 0.82 | 54.2 | 17 |
| seasonal_naive | all | 75.1 | 103.3 | 0.618 | -31.3 | 12.8 | 37.6 | 23.8 | 0.90 | 48.5 | 31 |
| seasonal_naive | 1-7 | 112.0 | 154.8 | 0.922 | -62.0 | 15.0 | 56.0 | 24.7 | 0.86 | 58.6 | 7 |
| seasonal_naive | 8-14 | 49.0 | 60.3 | 0.403 | -19.0 | 11.9 | 24.5 | 25.0 | 0.86 | 40.9 | 7 |
| seasonal_naive | 15-30 | 70.7 | 89.9 | 0.582 | -23.6 | 12.2 | 35.4 | 23.0 | 0.94 | 47.4 | 17 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 71.5). The references' MAE: seasonal_naive 75.1, moving_average_28d 82.9, climatology_dow 71.5.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +4.3 | -4.6 … +31.9 | no detectable difference from the reference | -0.060 | -0.537 … 0.065 | 32.3 | 45.2 % | 0.29 | 0.859 | 1.000 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.74 (23/31) | 0.55 … 0.88 | calibrated | -62.0 | -100.3 … -39.0 | -37.3 % | systematically underestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 78.2 | 75.8 | 80.1 | +1.9 | 2.4 % |

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
| 2026-05-05 | Tuesday | 514 | 168 | -346 | heavy rain 9.6 mm |
| 2026-05-22 | Friday | 348 | 111 | -237 | the model got climatology weather (horizon 22 days) |
| 2026-05-21 | Thursday | 309 | 112 | -197 | the model got climatology weather (horizon 21 days) |
| 2026-05-06 | Wednesday | 251 | 104 | -147 | no identified cause, possibly an event the model does not know about |
| 2026-05-08 | Friday | 256 | 120 | -136 | no identified cause, possibly an event the model does not know about |

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
