/**
 * Arviointiajojen muunnokset.
 *
 * Verdiktit luetaan `verdicts.json`-tiedostosta sellaisenaan: tilastot on jo laskettu
 * eika niita lasketa uudelleen. Tassa tiedostossa tehdaan vain se mita verdiktissa ei
 * ole: paivatason mittarit, horisonttikorit, pahiten menneet paivat ja aikasarjat,
 * kaikki `predictions.csv`-tiedostosta build-aikana.
 *
 * Nama ovat puhtaita funktioita ilman tiedostojarjestelmariippuvuuksia, joten ne
 * testataan suoraan (tests/accuracy.test.ts).
 */

import { dowOf } from '../../src/lib/dates.ts';
import type {
  AccuracyHorizonRow,
  AccuracyMetrics,
  AccuracySeries,
  AccuracyWorstDay,
} from '../../src/lib/types.ts';
import { roundTo } from './transform.ts';

/** Yksi rivi `predictions.csv`-tiedostosta, lukuina. */
export interface PredictionRow {
  venue_id: number;
  date: string;
  horizon_days: number;
  model: string;
  weather_mode: string;
  y_true: number;
  p10: number;
  p50: number;
  p90: number;
}

/** Samat korit kuin osion 3 mittareissa. */
export const HORIZON_BUCKETS = ['1-7', '8-14', '15-30'] as const;

/** Kuinka monelta uusimmalta ikkuna-ajolta aikasarja otetaan mukaan pakettiin. */
export const SERIES_RUN_LIMIT = 12;

/** Montako pahiten mennytta paivaa naytetaan. */
export const WORST_DAY_COUNT = 5;

// --- Pyoristys -------------------------------------------------------------

/**
 * Kavijamaarat ja niista johdetut luvut yhteen desimaaliin. Sama saanto koskee
 * prosenttilukuja, koska ne esitetaan yhdella desimaalilla.
 */
export function count1(value: number): number {
  return roundTo(value, 1);
}

/** Osuudet, suhdeluvut ja p-arvot kolmeen desimaaliin. */
export function share3(value: number): number {
  return roundTo(value, 3);
}

export function count1OrNull(value: number | null | undefined): number | null {
  return value === null || value === undefined || !Number.isFinite(value) ? null : count1(value);
}

// --- Karsinta --------------------------------------------------------------

export interface RunRef {
  run_id: string;
  kind: 'window' | 'sweep';
  created_at: string;
  /** Koosteen jasenajot. Tyhja ikkuna-ajolla. */
  members: string[];
  /** Viimeinen testipaiva. Jarjestaa ajot kun `created_at` on sama. */
  last_day: string;
}

/**
 * Ajot joiden aikasarja otetaan mukaan pakettiin.
 *
 * Saanto on kaksiosainen: enintaan `limit` uusinta ikkuna-ajoa, ja aina jokainen ajo
 * johon jokin kooste viittaa. Jalkimmainen on pakollinen, koska kooste piirretaan
 * jasentensa sarjoista eika omastaan; ilman sita kooste jaisi ilman kuvaajaa.
 */
export function selectSeriesRuns(runs: RunRef[], limit = SERIES_RUN_LIMIT): Set<string> {
  const keep = new Set<string>();
  for (const run of runs) {
    for (const member of run.members) keep.add(member);
  }
  const windows = runs
    .filter((run) => run.kind === 'window')
    .sort((a, b) => b.created_at.localeCompare(a.created_at) || b.last_day.localeCompare(a.last_day));
  for (const run of windows.slice(0, limit)) keep.add(run.run_id);
  return keep;
}

/**
 * Ajot esitysjarjestykseen: koosteet ensin, sitten yksittaiset ikkunat, kummatkin
 * uusin ensin. Kooste on ylimpana koska se on varsinainen naytto; yksittainen ikkuna
 * on kuvaileva.
 */
export function sortRuns<T extends RunRef>(runs: T[]): T[] {
  const rank = (run: RunRef): number => (run.kind === 'sweep' ? 0 : 1);
  return [...runs].sort(
    (a, b) =>
      rank(a) - rank(b) ||
      b.created_at.localeCompare(a.created_at) ||
      b.last_day.localeCompare(a.last_day) ||
      a.run_id.localeCompare(b.run_id),
  );
}

// --- Horisonttikorit -------------------------------------------------------

/** Horisonttikori vuorokausina origosta. Yli 30 vrk osuu viimeiseen koriin. */
export function horizonBucket(days: number): string {
  if (days <= 7) return '1-7';
  if (days <= 14) return '8-14';
  return '15-30';
}

/**
 * MAE horisonttikoreittain, malleittain. Tama nayttaa missa kohtaa horisonttia
 * ennuste hajoaa; `verdicts.json` kertoo vain koko jakson.
 */
export function horizonRows(rows: PredictionRow[], models: string[]): AccuracyHorizonRow[] {
  const buckets = new Map<string, number[]>();
  for (const row of rows) {
    const key = `${horizonBucket(row.horizon_days)}|${row.model}`;
    const bucket = buckets.get(key);
    if (bucket) bucket.push(Math.abs(row.y_true - row.p50));
    else buckets.set(key, [Math.abs(row.y_true - row.p50)]);
  }

  const out: AccuracyHorizonRow[] = [];
  for (const bucket of HORIZON_BUCKETS) {
    for (const model of models) {
      const errors = buckets.get(`${bucket}|${model}`);
      if (!errors || errors.length === 0) continue;
      out.push({
        bucket,
        model,
        mae: count1(errors.reduce((acc, value) => acc + value, 0) / errors.length),
        n: errors.length,
      });
    }
  }
  return out;
}

// --- Paivatason mittarit ---------------------------------------------------

function pinball(actual: number[], predicted: number[], quantile: number): number {
  let total = 0;
  for (let i = 0; i < actual.length; i += 1) {
    const y = actual[i]!;
    const q = predicted[i]!;
    total += y >= q ? quantile * (y - q) : (1 - quantile) * (q - y);
  }
  return actual.length === 0 ? 0 : total / actual.length;
}

/**
 * Yhden mallin paivatason mittarit ajon paasaan tilassa.
 *
 * `maseDenominator` on koulutusdatan seasonal naive -MAE. Se ei ole
 * `predictions.csv`-tiedostossa, joten koosteessa ja ilman `metrics.json`-tiedostoa
 * MASE jaa nulliksi. Se on parempi kuin vaarin laskettu luku.
 */
export function modelMetrics(
  model: string,
  rows: PredictionRow[],
  maseDenominator: number | null,
): AccuracyMetrics {
  const n = rows.length;
  const actual = rows.map((row) => row.y_true);
  const predicted = rows.map((row) => row.p50);

  let absolute = 0;
  let squared = 0;
  let signed = 0;
  let smape = 0;
  let covered = 0;
  let zeroDays = 0;
  for (let i = 0; i < n; i += 1) {
    const y = actual[i]!;
    const p = predicted[i]!;
    absolute += Math.abs(y - p);
    squared += (y - p) ** 2;
    signed += p - y;
    const scale = Math.abs(y) + Math.abs(p);
    // Nollapaivalla symmetrinen suhde saavuttaa 200 %:n kattonsa riippumatta siita
    // kuinka lahella ennuste oli. Luku lasketaan silti, mutta merkitaan epaluotettavaksi.
    smape += scale === 0 ? 0 : (200 * Math.abs(p - y)) / scale;
    const row = rows[i]!;
    if (y >= row.p10 && y <= row.p90) covered += 1;
    if (y === 0) zeroDays += 1;
  }

  const mae = n === 0 ? 0 : absolute / n;
  return {
    model,
    n,
    mae: count1(mae),
    rmse: count1(n === 0 ? 0 : Math.sqrt(squared / n)),
    mase: maseDenominator === null || maseDenominator === 0 ? null : share3(mae / maseDenominator),
    bias: count1(n === 0 ? 0 : signed / n),
    pinball_q10: count1(pinball(actual, rows.map((row) => row.p10), 0.1)),
    pinball_q50: count1(pinball(actual, predicted, 0.5)),
    pinball_q90: count1(pinball(actual, rows.map((row) => row.p90), 0.9)),
    coverage_80: share3(n === 0 ? 0 : covered / n),
    smape: count1(n === 0 ? 0 : smape / n),
    smape_reliable: zeroDays === 0,
    zero_days: zeroDays,
  };
}

// --- Pahiten menneet paivat ------------------------------------------------

/**
 * Viisi suurinta virhetta yhdelle mallille, suurin ensin.
 *
 * Virhe on etumerkillinen (ennuste miinus toteuma), jarjestys itseisarvon mukaan.
 * Tasapelit ratkaistaan paivamaaralla, jotta paketti on deterministinen.
 */
export function worstDays(
  rows: PredictionRow[],
  holidays: Record<string, string>,
  limit = WORST_DAY_COUNT,
): AccuracyWorstDay[] {
  return [...rows]
    .sort(
      (a, b) => Math.abs(b.p50 - b.y_true) - Math.abs(a.p50 - a.y_true) || a.date.localeCompare(b.date),
    )
    .slice(0, limit)
    .map((row) => {
      const holidayName = holidays[row.date];
      return {
        date: row.date,
        dow: dowOf(row.date),
        y_true: count1(row.y_true),
        p50: count1(row.p50),
        error: count1(row.p50 - row.y_true),
        is_holiday: holidayName !== undefined,
        ...(holidayName === undefined ? {} : { holiday_name: holidayName }),
      };
    });
}

// --- Aikasarja -------------------------------------------------------------

/**
 * Paivasarja sarakemuotoon. Paamalleille tallennetaan vali, vertailukohdista riittaa
 * p50: ne piirretaan ohuina viivoina eika niiden valia nayteta.
 */
export function buildSeries(
  rows: PredictionRow[],
  mainModels: string[],
  holidays: Record<string, string>,
): AccuracySeries {
  const dates = [...new Set(rows.map((row) => row.date))].sort();
  const index = new Map(dates.map((date, position) => [date, position]));
  const withInterval = new Set(mainModels);

  const series: AccuracySeries = {
    dates,
    horizon_days: new Array<number>(dates.length).fill(0),
    y_true: new Array<number>(dates.length).fill(0),
    holidays: {},
    models: {},
  };

  for (const row of rows) {
    const position = index.get(row.date);
    if (position === undefined) continue;
    series.horizon_days[position] = row.horizon_days;
    series.y_true[position] = count1(row.y_true);

    let model = series.models[row.model];
    if (!model) {
      model = { p50: new Array<number>(dates.length).fill(0) };
      if (withInterval.has(row.model)) {
        model.p10 = new Array<number>(dates.length).fill(0);
        model.p90 = new Array<number>(dates.length).fill(0);
      }
      series.models[row.model] = model;
    }
    model.p50[position] = count1(row.p50);
    if (model.p10) model.p10[position] = count1(row.p10);
    if (model.p90) model.p90[position] = count1(row.p90);
  }

  for (const date of dates) {
    const name = holidays[date];
    if (name !== undefined) series.holidays[date] = name;
  }
  return series;
}
