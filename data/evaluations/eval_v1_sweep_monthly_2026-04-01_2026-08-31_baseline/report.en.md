# Forecast evaluation report, pooled: monthly 2026-04-01 – 2026-08-31

Run id: `eval_v1_sweep_monthly_2026-04-01_2026-08-31_baseline`

## 1. Pooled verdict

Pooled (monthly): 5 windows, 2026-04-01–2026-08-31, weather mode operational, main reference best. Venue 1 (Pekuri): the model baseline against best-per-window, 5 windows (153 days). The model was better in 1 windows and worse in 4. The pooled result goes against the model: it loses to a simple reference, a mean difference of +62.2 visitors per day (95 % interval +3.1…+126.6). Venue 2 (Kaupungintalo): the model baseline against climatology_dow, 5 windows (153 days). The model was better in 0 windows and worse in 5. The pooled result goes against the model: it loses to a simple reference, a mean difference of +16.9 visitors per day (95 % interval +5.0…+31.3). There is about eight months of data from a single year, so the pooled result rests on a thin sample too. More data, or an events calendar as a feature, could change it.

## 2. The windows

| # | Test period | Origin | Training window | Run id |
| --- | --- | --- | --- | --- |
| 1 | 2026-04-01 – 2026-04-30 | 2026-03-31 | all | `eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline` |
| 2 | 2026-05-01 – 2026-05-31 | 2026-04-30 | all | `eval_v1_2026-04-30_2026-05-01_2026-05-31_baseline` |
| 3 | 2026-06-01 – 2026-06-30 | 2026-05-31 | all | `eval_v1_2026-05-31_2026-06-01_2026-06-30_baseline` |
| 4 | 2026-07-01 – 2026-07-31 | 2026-06-30 | all | `eval_v1_2026-06-30_2026-07-01_2026-07-31_baseline` |
| 5 | 2026-08-01 – 2026-08-31 | 2026-07-31 | all | `eval_v1_2026-07-31_2026-08-01_2026-08-31_baseline` |

The weather mode for the verdict: `operational`. The main reference rule: `best`. The multiple comparison family size: 10.

## Venue 1 (Pekuri)

### Pooled verdict

| Model | Reference | Windows | Days | Mean difference d | 95 % interval | Verdict | In favour | Against | MDE | MDE / reference MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | best-per-window | 5 | 153 | +62.2 | +3.1 … +126.6 | worse than the reference | 1 | 4 | 99.1 | 69.9 % |

### Per-window results: baseline

| Test period | Reference | Model MAE | Reference MAE | Mean difference d | 95 % interval | Verdict | MDE | MDE % | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | climatology_dow | 102.9 | 96.2 | +6.7 | -3.2 … +30.7 | no detectable difference from the reference | 34.5 | 35.9 % | 0.610 | 1.000 |
| 2026-05-01..2026-05-31 | moving_average_28d | 179.5 | 187.4 | -7.9 | -58.5 … +23.6 | no detectable difference from the reference | 69.0 | 36.8 % | 0.740 | 1.000 |
| 2026-06-01..2026-06-30 | climatology_dow | 305.0 | 138.9 | +166.1 | +62.6 … +264.5 | worse than the reference | 102.0 | 73.4 % | 0.043 | 0.391 |
| 2026-07-01..2026-07-31 | climatology_dow | 174.3 | 156.2 | +18.1 | -15.5 … +60.9 | no detectable difference from the reference | 43.5 | 27.8 % | 0.472 | 1.000 |
| 2026-08-01..2026-08-31 | climatology_dow | 255.8 | 128.0 | +127.8 | +44.2 … +184.1 | worse than the reference | 70.8 | 55.3 % | 0.055 | 0.443 |

#### Period totals: baseline

| Test period | Forecast | Actual | Difference % | 80 % interval | Interval covers |
| --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | 13,639 | 13,189 | +3.4 % | 13,639 – 20,089 | no |
| 2026-05-01..2026-05-31 | 11,880 | 14,521 | -18.2 % | 10,683 – 13,840 | no |
| 2026-06-01..2026-06-30 | 2,961 | 11,865 | -75.0 % | 2,166 – 3,328 | no |
| 2026-07-01..2026-07-31 | 12,181 | 16,994 | -28.3 % | 10,022 – 14,392 | no |
| 2026-08-01..2026-08-31 | 20,173 | 13,514 | +49.3 % | 18,620 – 27,237 | no |

## Venue 2 (Kaupungintalo)

### Pooled verdict

| Model | Reference | Windows | Days | Mean difference d | 95 % interval | Verdict | In favour | Against | MDE | MDE / reference MAE |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| baseline | climatology_dow | 5 | 153 | +16.9 | +5.0 … +31.3 | worse than the reference | 0 | 5 | 21.5 | 37.1 % |

### Per-window results: baseline

| Test period | Reference | Model MAE | Reference MAE | Mean difference d | 95 % interval | Verdict | MDE | MDE % | DM p (raw) | DM p (Holm) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | climatology_dow | 95.1 | 75.1 | +20.0 | +7.8 … +48.9 | worse than the reference | 24.7 | 32.9 % | 0.293 | 1.000 |
| 2026-05-01..2026-05-31 | climatology_dow | 75.8 | 71.5 | +4.3 | -4.6 … +31.9 | no detectable difference from the reference | 32.3 | 45.2 % | 0.859 | 1.000 |
| 2026-06-01..2026-06-30 | climatology_dow | 60.7 | 44.5 | +16.2 | -9.0 … +41.3 | no detectable difference from the reference | 36.7 | 82.5 % | 0.259 | 1.000 |
| 2026-07-01..2026-07-31 | climatology_dow | 106.0 | 62.0 | +44.0 | +26.0 … +62.9 | worse than the reference | 24.1 | 38.9 % | 0.017 | 0.174 |
| 2026-08-01..2026-08-31 | climatology_dow | 37.0 | 36.8 | +0.2 | -10.6 … +8.5 | no detectable difference from the reference | 10.6 | 28.8 % | 0.967 | 1.000 |

#### Period totals: baseline

| Test period | Forecast | Actual | Difference % | 80 % interval | Interval covers |
| --- | --- | --- | --- | --- | --- |
| 2026-04-01..2026-04-30 | 6,155 | 3,791 | +62.4 % | 3,666 – 6,155 | yes |
| 2026-05-01..2026-05-31 | 3,228 | 5,149 | -37.3 % | 2,926 – 4,685 | no |
| 2026-06-01..2026-06-30 | 2,900 | 4,254 | -31.8 % | 2,344 – 3,730 | no |
| 2026-07-01..2026-07-31 | 3,345 | 6,278 | -46.7 % | 2,740 – 4,616 | no |
| 2026-08-01..2026-08-31 | 4,335 | 4,866 | -10.9 % | 4,166 – 7,382 | yes |

## Limitations

- The pooled result is bootstrapped over **whole windows**, because the window is the natural unit of independence: two days from the same window share a training set, two different windows do not.
- A per-window verdict is descriptive. The pooled verdict is the one that carries evidence.
- The raw p-values are corrected with Holm-Bonferroni; the family size is stated above.
- There is about eight months of data from a single year, so the pooled result rests on a thin sample too.
