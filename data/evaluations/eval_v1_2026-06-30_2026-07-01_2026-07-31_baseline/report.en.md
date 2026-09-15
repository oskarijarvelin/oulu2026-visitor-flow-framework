# Forecast evaluation report: 2026-07-01 – 2026-07-31

Run id: `eval_v1_2026-06-30_2026-07-01_2026-07-31_baseline`

## 1. Verdict

Window 2026-07-01–2026-07-31 (31 days), training ends 2026-06-30, training window all, weather mode operational. Venue 1 (Pekuri): the model baseline made a mean daily error of 174.3 visitors, the main reference climatology_dow 156.2. No difference was detected: +18.1 visitors per day (95 % interval -15.5…+60.9). This sample (31 days) would only have resolved a difference of 43.5 visitors, i.e. 27.8 % of the reference's MAE; "no difference" therefore does not mean equivalence. The total for the period: forecast 12,181, actual 16,994, difference -28.3 %, 80 % interval 10,022–14,392. Venue 2 (Kaupungintalo): the model baseline made a mean daily error of 106.0 visitors, the main reference climatology_dow 62.0. The model loses to the reference statistically: a difference of +44.0 visitors per day (95 % interval +26.0…+62.9). The simple rule climatology_dow is better than the model on this window. This sample (31 days) would only have resolved a difference of 24.1 visitors, i.e. 38.9 % of the reference's MAE. The total for the period: forecast 3,345, actual 6,278, difference -46.7 %, 80 % interval 2,740–4,616. A single window's result is descriptive, not probative: the actual evidence comes from pooling several windows.

## 2. The window and the setup

- Origin (the last training day): **2026-06-30**
- Test period: **2026-07-01 – 2026-07-31** (31 days, horizons 1–31)
- Training window: `all`
- Models: baseline
- References: seasonal_naive, moving_average_28d, climatology_dow
- Main reference rule: `best`
- Weather modes: perfect, operational, climatology (the verdict comes from `operational`)
- Bootstrap: 10,000 resamples, block length 7 days, seed 20260101

| Venue | Training starts | Training days | Zero days | Nested origins | MASE denominator |
| --- | --- | --- | --- | --- | --- |
| 1 (Pekuri) | 2026-01-01 | 181 | 21 | 12 | 170.78 |
| 2 (Kaupungintalo) | 2026-01-01 | 181 | 13 | 12 | 108.26 |

The prediction interval quantiles come from a nested backtest run entirely inside the training window: its last inner origin is the origin minus the horizon, so no inner forecast reaches into the test period.

## Venue 1 (Pekuri)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 12,181 | 16,994 | -4,813 | -28.3 % | 10,022 – 14,392 | no | 6,574 – 19,400 |
| climatology_dow | 13,653 | 16,994 | -3,341 | -19.7 % | 12,632 – 16,257 | no | 8,698 – 23,914 |
| moving_average_28d | 12,174 | 16,994 | -4,820 | -28.4 % | 9,329 – 12,220 | no | 6,036 – 17,391 |
| seasonal_naive | 11,228 | 16,994 | -5,766 | -33.9 % | 9,806 – 14,102 | no | 5,617 – 20,263 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 174.3 | 210.0 | 1.021 | -155.3 | 33.6 | 87.2 | 36.8 | 0.65 | 35.6 | 31 |
| baseline | 1-7 | 121.4 | 165.3 | 0.711 | -100.3 | 27.0 | 60.7 | 25.7 | 0.86 | 23.9 | 7 |
| baseline | 8-14 | 167.1 | 185.7 | 0.978 | -131.4 | 29.7 | 83.5 | 31.7 | 0.57 | 37.4 | 7 |
| baseline | 15-30 | 199.1 | 234.4 | 1.166 | -187.7 | 37.9 | 99.5 | 43.4 | 0.59 | 39.7 | 17 |
| climatology_dow | all | 156.2 | 194.9 | 0.915 | -107.8 | 27.7 | 78.1 | 37.5 | 0.84 | 30.4 | 31 |
| climatology_dow | 1-7 | 167.5 | 225.4 | 0.981 | -58.8 | 25.1 | 83.7 | 50.1 | 0.71 | 31.5 | 7 |
| climatology_dow | 8-14 | 162.1 | 175.4 | 0.949 | -62.5 | 21.8 | 81.0 | 32.8 | 1.00 | 33.5 | 7 |
| climatology_dow | 15-30 | 149.2 | 188.9 | 0.874 | -146.6 | 31.2 | 74.6 | 34.2 | 0.82 | 28.8 | 17 |
| moving_average_28d | all | 164.7 | 209.2 | 0.964 | -155.5 | 35.3 | 82.3 | 57.8 | 0.55 | 31.9 | 31 |
| moving_average_28d | 1-7 | 137.6 | 200.5 | 0.805 | -106.9 | 28.7 | 68.8 | 56.9 | 0.71 | 26.6 | 7 |
| moving_average_28d | 8-14 | 120.7 | 148.6 | 0.707 | -110.6 | 29.8 | 60.3 | 16.9 | 0.71 | 25.1 | 7 |
| moving_average_28d | 15-30 | 194.0 | 232.8 | 1.136 | -194.0 | 40.3 | 97.0 | 75.0 | 0.41 | 37.0 | 17 |
| seasonal_naive | all | 188.8 | 227.4 | 1.105 | -186.0 | 36.7 | 94.4 | 29.7 | 0.77 | 38.5 | 31 |
| seasonal_naive | 1-7 | 145.9 | 214.3 | 0.854 | -137.9 | 31.0 | 72.9 | 31.9 | 0.71 | 28.9 | 7 |
| seasonal_naive | 8-14 | 145.9 | 171.2 | 0.854 | -141.6 | 33.0 | 72.9 | 16.0 | 1.00 | 32.1 | 7 |
| seasonal_naive | 15-30 | 224.1 | 251.6 | 1.312 | -224.1 | 40.6 | 112.1 | 34.5 | 0.71 | 45.0 | 17 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 156.2). The references' MAE: seasonal_naive 188.8, moving_average_28d 164.7, climatology_dow 156.2.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +18.1 | -15.5 … +60.9 | no detectable difference from the reference | -0.116 | -0.403 … 0.087 | 43.5 | 27.8 % | 0.79 | 0.472 | 0.472 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.65 (20/31) | 0.45 … 0.81 | calibrated | -155.3 | -211.2 … -134.8 | -28.3 % | systematically underestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 168.2 | 174.3 | 181.5 | +13.3 | 7.3 % |

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
| 2026-07-27 | Monday | 804 | 360 | -444 | the model got climatology weather (horizon 27 days) |
| 2026-07-15 | Wednesday | 703 | 303 | -400 | no identified cause, possibly an event the model does not know about |
| 2026-07-18 | Saturday | 826 | 482 | -344 | the model got climatology weather (horizon 18 days); weekend |
| 2026-07-06 | Monday | 755 | 417 | -338 | heavy rain 5.8 mm |
| 2026-07-28 | Tuesday | 702 | 394 | -308 | heavy rain 13.9 mm; the model got climatology weather (horizon 28 days) |

This is the most practical part of the report: it says what the model is missing. A recurring cause in the same column is a direct proposal for the next feature.

## Venue 2 (Kaupungintalo)

### 3. The total for the period

| Model | Forecast | Actual | Difference | Difference % | 80 % interval | Interval covers | Naive daily sum interval |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 3,345 | 6,278 | -2,933 | -46.7 % | 2,740 – 4,616 | no | 1,078 – 7,166 |
| climatology_dow | 5,053 | 6,278 | -1,225 | -19.5 % | 4,211 – 5,843 | no | 2,125 – 8,564 |
| moving_average_28d | 4,486 | 6,278 | -1,792 | -28.5 % | 3,390 – 5,093 | no | 626 – 8,118 |
| seasonal_naive | 4,755 | 6,278 | -1,523 | -24.3 % | 4,341 – 12,688 | yes | 1,566 – 11,974 |

The interval for the total is simulated: the daily relative errors of the backtest inside the training window are bootstrapped in blocks into whole periods, each simulated path is summed, and the interval is read from the distribution of those sums. The last column shows where summing the daily p10 and p90 values would have led; it assumes every day's error points the same way and is not an interval for the total.

### 4. Daily metrics

Weather mode `operational`. Pinball loss for the quantiles 0.1 / 0.5 / 0.9.

| Model | Horizon | MAE | RMSE | MASE | Bias | Pinball 0.1 | Pinball 0.5 | Pinball 0.9 | Coverage 80 % | sMAPE | n |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | all | 106.0 | 127.4 | 0.979 | -94.6 | 17.9 | 53.0 | 21.1 | 0.52 | 71.4 | 31 |
| baseline | 1-7 | 45.1 | 63.7 | 0.417 | -32.9 | 12.7 | 22.6 | 9.8 | 0.86 | 44.9 | 7 |
| baseline | 8-14 | 90.5 | 112.6 | 0.836 | -87.6 | 15.2 | 45.3 | 34.5 | 0.43 | 61.8 | 7 |
| baseline | 15-30 | 137.4 | 150.7 | 1.269 | -122.9 | 21.1 | 68.7 | 20.2 | 0.41 | 86.2 | 17 |
| climatology_dow | all | 62.0 | 79.7 | 0.573 | -39.5 | 16.1 | 31.0 | 9.2 | 0.84 | 42.1 | 31 |
| climatology_dow | 1-7 | 37.9 | 50.5 | 0.350 | -4.3 | 10.7 | 18.9 | 11.5 | 0.86 | 39.4 | 7 |
| climatology_dow | 8-14 | 41.2 | 57.6 | 0.380 | -36.5 | 12.7 | 20.6 | 7.6 | 0.86 | 29.3 | 7 |
| climatology_dow | 15-30 | 80.5 | 95.8 | 0.744 | -55.3 | 19.8 | 40.2 | 8.9 | 0.82 | 48.6 | 17 |
| moving_average_28d | all | 102.3 | 116.6 | 0.945 | -57.8 | 20.1 | 51.1 | 21.4 | 0.52 | 67.6 | 31 |
| moving_average_28d | 1-7 | 62.8 | 90.8 | 0.580 | -20.1 | 17.1 | 31.4 | 17.6 | 0.71 | 48.6 | 7 |
| moving_average_28d | 8-14 | 90.6 | 101.6 | 0.837 | -52.4 | 19.1 | 45.3 | 13.7 | 0.71 | 61.0 | 7 |
| moving_average_28d | 15-30 | 123.3 | 130.8 | 1.139 | -75.5 | 21.7 | 61.7 | 26.1 | 0.35 | 78.1 | 17 |
| seasonal_naive | all | 73.3 | 95.4 | 0.677 | -49.1 | 17.4 | 36.6 | 19.4 | 0.90 | 45.5 | 31 |
| seasonal_naive | 1-7 | 55.4 | 78.2 | 0.512 | -14.0 | 12.1 | 27.7 | 29.4 | 0.86 | 47.3 | 7 |
| seasonal_naive | 8-14 | 49.7 | 63.0 | 0.459 | -46.3 | 14.2 | 24.9 | 15.1 | 1.00 | 31.1 | 7 |
| seasonal_naive | 15-30 | 90.3 | 111.5 | 0.834 | -64.8 | 20.8 | 45.1 | 17.1 | 0.88 | 50.6 | 17 |

The test period has no zero days, so sMAPE is readable in this window.

### 5. Statistical assessment

The main reference on this window: **climatology_dow** (MAE 62.0). The references' MAE: seasonal_naive 73.3, moving_average_28d 102.3, climatology_dow 62.0.

| Model | Mean difference d | 95 % interval | Verdict | Skill score | Skill 95 % interval | MDE | MDE / reference MAE | DM | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | +44.0 | +26.0 … +62.9 | worse than the reference | -0.710 | -1.019 … -0.392 | 24.1 | 38.9 % | 3.59 | 0.017 | 0.035 |

`d` is the difference between the model's and the reference's absolute daily errors; negative means the model is closer. The interval comes from a moving block bootstrap (block 7 days), which is this assessment's primary method.

**The MDE, the minimum detectable effect,** says how large the difference would have had to be for this sample to detect it. When the verdict is "no detectable difference", the MDE separates two different things: the models are equally good, or the sample is too small. Over a one-month window the MDE is, with this data, on the order of 30 % of the reference's MAE, so a month can only prove large improvements.

**Diebold-Mariano is secondary.** The 30 errors from one origin are not independent observations: they share the same training set and the same state of the world, so DM's assumptions are stretched. The p-value is computed from a recentred bootstrap, not from a t-distribution. The Holm-corrected p-value was computed for a family of size 2.

### 6. Calibration and bias

| Model | Coverage 80 % | Clopper-Pearson 95 % | Calibration | Bias | Bias 95 % interval | Bias % of actual | Bias verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | 0.52 (16/31) | 0.33 … 0.70 | too narrow | -94.6 | -127.9 … -68.7 | -46.7 % | systematically underestimates |

Calibration is "calibrated" when 0.80 falls inside the Clopper-Pearson exact binomial interval. Bias is the mean signed error (forecast minus actual); if its interval does not contain zero, the model systematically over- or underestimates.

### 7. The three weather modes

| Model | perfect MAE | operational MAE | climatology MAE | Improvement from the weather (climatology − perfect) | Share of the climatology MAE |
| --- | --- | --- | --- | --- | --- |
| baseline | 106.4 | 106.0 | 102.7 | -3.7 | -3.6 % |

`perfect` is the upper bound: what the model could do if the weather were known exactly. `climatology` is the lower bound: what it can do without a weather forecast. `operational` is the most realistic estimate and assumes a good weather forecast. The improvement from the weather is the `climatology` MAE minus the `perfect` MAE: **a positive figure means that knowing the weather helps**, and it is the share of the model's accuracy that rests on knowing the weather.

⚠ **The improvement is negative**, i.e. on this window the model forecasts *better* on average weather than on the realised weather. That is not a measurement error but a result: the weather dependence the model learned does not generalise to this period, and the realised weather pushes the forecast the wrong way. The weather features fit the noise of the training period more than the visitors' real behaviour in the weather.

| Weather mode | Realised weather | Climatology |
| --- | --- | --- |
| perfect (the realised weather) | 31 | 0 |
| operational (realised days 1-16, climatology from 17) | 16 | 15 |
| climatology (climatology for the whole period) | 0 | 31 |

### 9. The worst days

**baseline**

| Day | Weekday | Actual | Forecast | Error | Possible cause |
| --- | --- | --- | --- | --- | --- |
| 2026-07-28 | Tuesday | 387 | 128 | -259 | heavy rain 13.9 mm; the model got climatology weather (horizon 28 days) |
| 2026-07-15 | Wednesday | 309 | 112 | -197 | no identified cause, possibly an event the model does not know about |
| 2026-07-17 | Friday | 281 | 98 | -183 | the model got climatology weather (horizon 17 days) |
| 2026-07-22 | Wednesday | 304 | 123 | -181 | the model got climatology weather (horizon 22 days) |
| 2026-07-18 | Saturday | 271 | 97 | -174 | the model got climatology weather (horizon 18 days); weekend |

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
