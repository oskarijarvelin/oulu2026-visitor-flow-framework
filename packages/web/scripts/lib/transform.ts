/**
 * Puhtaat aggregaatit. Naissa ei ole tiedostojarjestelmariippuvuuksia, joten ne
 * testataan suoraan (tests/transform.test.ts).
 */

import { addDays, dowOf, localDate, localHour } from '../../src/lib/dates.ts';
import type {
  BacktestRow,
  DailyRow,
  Dow,
  ForecastDailyRow,
  HorizonPoint,
  HourlySeries,
  ProfileCell,
} from '../../src/lib/types.ts';
import { BuildDataError } from './csv.ts';

// --- Numerot ---------------------------------------------------------------

/** Pyoristaa yhteen desimaaliin. */
export function round1(value: number): number {
  return Math.round(value * 10) / 10;
}

export function roundTo(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

export function round1OrNull(value: number | null): number | null {
  return value === null ? null : round1(value);
}

/** Kavijamaarat ovat laskureita: desimaali ei kerro niista mitaan. */
export function roundCount(value: number): number {
  return Math.round(value);
}

export function mean(values: number[]): number {
  if (values.length === 0) return 0;
  let total = 0;
  for (const value of values) total += value;
  return total / values.length;
}

export function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[middle - 1]! + sorted[middle]!) / 2 : sorted[middle]!;
}

export function sum(values: number[]): number {
  let total = 0;
  for (const value of values) total += value;
  return total;
}

// --- Aika ------------------------------------------------------------------

/**
 * "2026-05-22T14:00:00+03:00" -> "2026-05-22T14".
 *
 * Siirtyma pudotetaan tarkoituksella: koko sarja on paikallista aikaa ja seinakello
 * riittaa esitykseen. Tama puolittaa tuntisarjan koon.
 */
export function shortenLocalTs(tsLocal: string): string {
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}):\d{2}:\d{2}(?:[+-]\d{2}:\d{2}|Z)$/.exec(tsLocal);
  if (!match) throw new BuildDataError(`Aikaleimaa "${tsLocal}" ei tunnisteta paikalliseksi ISO-leimaksi.`);
  return `${match[1]}T${match[2]}`;
}

/** Manifestin ika tunteina, virheenkasittelyn kanssa. */
export function manifestAgeHours(generatedAt: string, now: Date): number {
  const parsed = Date.parse(generatedAt);
  if (!Number.isFinite(parsed)) {
    throw new BuildDataError(`Manifestin generated_at "${generatedAt}" ei ole kelvollinen aikaleima.`);
  }
  return (now.getTime() - parsed) / 3_600_000;
}

// --- Aggregaatit -----------------------------------------------------------

export interface PeriodSummary {
  days: number;
  visitors_total: number;
  mean_daily: number;
}

/** Viimeiset `days` paivaa annettuun paivaan asti, mukaan vain raportoivat paivat. */
export function summarisePeriod(rows: DailyRow[], endDate: string, days: number): PeriodSummary {
  const start = addDays(endDate, -(days - 1));
  const window = rows.filter((row) => row.date >= start && row.date <= endDate && row.is_reporting);
  const totals = window.map((row) => row.visitors_total);
  return { days: window.length, visitors_total: sum(totals), mean_daily: round1(mean(totals)) };
}

export function changePct(current: PeriodSummary, previous: PeriodSummary): number | null {
  if (previous.days === 0 || previous.mean_daily === 0) return null;
  return round1(((current.mean_daily - previous.mean_daily) / previous.mean_daily) * 100);
}

/**
 * Viikonpaiva x tunti -matriisi. Puuttuva ruutu (n = 0) on eri asia kuin nolla:
 * ensimmainen tarkoittaa ettei havaintoja ole, jalkimmainen etta kavijoita ei ollut.
 */
export function buildProfileCells(series: HourlySeries): ProfileCell[] {
  const buckets = new Map<string, number[]>();
  for (let i = 0; i < series.ts.length; i += 1) {
    const ts = series.ts[i]!;
    const key = `${dowOf(localDate(ts))}:${localHour(ts)}`;
    const bucket = buckets.get(key);
    if (bucket) bucket.push(series.visitors_total[i]!);
    else buckets.set(key, [series.visitors_total[i]!]);
  }

  const cells: ProfileCell[] = [];
  for (let dow = 0; dow < 7; dow += 1) {
    for (let hour = 0; hour < 24; hour += 1) {
      const values = buckets.get(`${dow}:${hour}`) ?? [];
      cells.push({
        dow: dow as Dow,
        hour,
        mean: values.length === 0 ? null : round1(mean(values)),
        median: values.length === 0 ? null : round1(median(values)),
        n: values.length,
        n_zero: values.filter((value) => value === 0).length,
      });
    }
  }
  return cells;
}

/**
 * Aukiolotunnit johdetaan datasta samalla saannolla kuin `packages/forecast/profile.py`:
 * tunti on suljettu kun sen ei-nolla-osuus jaa alle viiden prosentin.
 */
export function deriveOpenHours(cells: ProfileCell[], threshold = 0.05): number[] {
  const byHour = new Map<number, { observed: number; nonZero: number }>();
  for (const cell of cells) {
    const entry = byHour.get(cell.hour) ?? { observed: 0, nonZero: 0 };
    entry.observed += cell.n;
    entry.nonZero += cell.n - cell.n_zero;
    byHour.set(cell.hour, entry);
  }
  const open: number[] = [];
  for (const [hour, entry] of [...byHour.entries()].sort((a, b) => a[0] - b[0])) {
    if (entry.observed === 0) continue;
    if (entry.nonZero / entry.observed >= threshold) open.push(hour);
  }
  return open;
}

/** MAE horisontin funktiona, /quality-sivun kayria varten. */
export function maeByHorizon(rows: BacktestRow[]): HorizonPoint[] {
  const buckets = new Map<number, number[]>();
  for (const row of rows) {
    const error = Math.abs(row.y_true - row.y_pred);
    const bucket = buckets.get(row.horizon_days);
    if (bucket) bucket.push(error);
    else buckets.set(row.horizon_days, [error]);
  }
  return [...buckets.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([horizon, errors]) => ({ horizon_days: horizon, mae: round1(mean(errors)), n: errors.length }));
}

/** Osuus riveista joilla toteuma osui valille p10 - p90. */
export function coverage(rows: BacktestRow[]): number {
  if (rows.length === 0) return 0;
  const inside = rows.filter((row) => row.y_true >= row.p10 && row.y_true <= row.p90).length;
  return roundTo(inside / rows.length, 4);
}

/**
 * Ennusteen summa horisontin alusta annettuun vuorokauteen asti.
 *
 * Huomaa etta p10- ja p90-summat ovat paivakohtaisten valien summia, eivat jakson
 * yhteismaaran 80 prosentin vali. Ne ovat siis liian leveat summalle. Kayttoliittyma
 * kertoo taman.
 */
export function sumForecast(
  rows: ForecastDailyRow[],
  days: number,
): { p10: number; p50: number; p90: number; days: number } | null {
  const window = rows.filter((row) => row.horizon_days <= days);
  if (window.length === 0) return null;
  return {
    days: window.length,
    p10: roundCount(sum(window.map((row) => row.p10))),
    p50: roundCount(sum(window.map((row) => row.p50))),
    p90: roundCount(sum(window.map((row) => row.p90))),
  };
}

/** Suurin horisontti jolla saa on dynaamista ennustetta eika klimatologiaa. */
export function forecastWeatherDays(rows: ForecastDailyRow[]): number {
  const dynamic = rows.filter((row) => row.weather_source !== 'climatology').map((row) => row.horizon_days);
  return dynamic.length === 0 ? 0 : Math.max(...dynamic);
}
