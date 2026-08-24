/**
 * Sarjojen kasittely. Tuntidata on JSONissa sarakemuodossa koon takia; nama apurit
 * muuttavat sen rivimuotoon jota Observable Plot odottaa.
 */

import { addDays, localDate, plotDate, plotDay } from './dates.ts';
import type {
  BacktestColumns,
  BacktestRow,
  DailyColumns,
  DailyRow,
  ForecastDailyRow,
  HourlySeries,
  WeatherGroup,
} from './types.ts';

/**
 * Sarakemuotoinen paivasarja riveiksi. JSON on sarakemuodossa koon takia, mutta
 * sivut ja Observable Plot kasittelevat rivimuotoa.
 */
export function toDailyRows(columns: DailyColumns | undefined, groups: WeatherGroup[]): DailyRow[] {
  if (!columns) return [];
  const incomplete = new Set(columns.incomplete_idx);
  const notReporting = new Set(columns.not_reporting_idx);
  return columns.date.map((date, index) => {
    const groupIndex = columns.weather_group[index] ?? -1;
    const holidayName = columns.holidays[date];
    const row: DailyRow = {
      date,
      visitors_in: columns.visitors_in[index] ?? 0,
      visitors_out: columns.visitors_out[index] ?? 0,
      visitors_total: columns.visitors_total[index] ?? 0,
      is_complete: !incomplete.has(index),
      is_reporting: !notReporting.has(index),
      is_holiday: holidayName !== undefined,
    };
    if (holidayName !== undefined) row.holiday_name = holidayName;
    const tempMean = columns.temp_mean[index];
    if (tempMean !== null && tempMean !== undefined) row.temp_mean = tempMean;
    const tempMax = columns.temp_max[index];
    if (tempMax !== null && tempMax !== undefined) row.temp_max = tempMax;
    const precip = columns.precip_sum[index];
    if (precip !== null && precip !== undefined) row.precip_sum = precip;
    if (groupIndex >= 0 && groups[groupIndex]) row.weather_group = groups[groupIndex];
    const ticketsSold = columns.tickets_sold[index];
    if (ticketsSold !== null && ticketsSold !== undefined) row.tickets_sold = ticketsSold;
    const groupsSold = columns.groups_sold[index];
    if (groupsSold !== null && groupsSold !== undefined) row.groups_sold = groupsSold;
    const ticketsTotal = columns.tickets_total[index];
    if (ticketsTotal !== null && ticketsTotal !== undefined) row.tickets_total = ticketsTotal;
    return row;
  });
}

/** Sarakemuotoinen backtest riveiksi. */
export function toBacktestRows(columns: BacktestColumns | undefined): BacktestRow[] {
  if (!columns) return [];
  return columns.origin.map((originIndex, index) => ({
    origin_date: columns.origins[originIndex] ?? '',
    horizon_days: columns.horizon_days[index] ?? 0,
    y_true: columns.y_true[index] ?? 0,
    y_pred: columns.y_pred[index] ?? 0,
    p10: columns.p10[index] ?? 0,
    p90: columns.p90[index] ?? 0,
  }));
}

export interface HourlyPoint {
  ts: string;
  at: Date;
  date: string;
  visitors_in: number;
  visitors_total: number;
  is_imputed: boolean;
  is_rain: boolean;
}

export function toHourlyPoints(series: HourlySeries): HourlyPoint[] {
  const imputed = new Set(series.imputed_idx);
  const rain = new Set(series.rain_idx);
  return series.ts.map((ts, index) => ({
    ts,
    at: plotDate(ts),
    date: localDate(ts),
    visitors_in: series.visitors_in[index] ?? 0,
    visitors_total: series.visitors_total[index] ?? 0,
    is_imputed: imputed.has(index),
    is_rain: rain.has(index),
  }));
}

export interface DailyPoint extends DailyRow {
  at: Date;
}

export function toDailyPoints(rows: DailyRow[]): DailyPoint[] {
  return rows.map((row) => ({ ...row, at: plotDay(row.date) }));
}

export interface ForecastPoint extends ForecastDailyRow {
  at: Date;
  /** true kun paivan saa on klimatologiaa eika dynaamista ennustetta. */
  is_climatology: boolean;
}

export function toForecastPoints(rows: ForecastDailyRow[]): ForecastPoint[] {
  return rows.map((row) => ({
    ...row,
    at: plotDay(row.date),
    is_climatology: row.weather_source === 'climatology',
  }));
}

/** Rajaa paivasarjan viimeisiin `days` vuorokauteen. `null` tarkoittaa koko sarjaa. */
export function lastDays<T extends { date: string }>(rows: T[], days: number | null): T[] {
  if (days === null || rows.length === 0) return rows;
  const end = rows[rows.length - 1]!.date;
  const start = addDays(end, -(days - 1));
  return rows.filter((row) => row.date >= start);
}

/** Rajaa tuntisarjan viimeisiin `days` vuorokauteen. */
export function lastHourlyDays(points: HourlyPoint[], days: number | null): HourlyPoint[] {
  if (days === null || points.length === 0) return points;
  const end = points[points.length - 1]!.date;
  const start = addDays(end, -(days - 1));
  return points.filter((point) => point.date >= start);
}

/** Yhtenaiset sadejaksot taustavarjostusta varten. */
export interface Interval {
  from: Date;
  to: Date;
}

export function rainIntervals(points: HourlyPoint[]): Interval[] {
  const intervals: Interval[] = [];
  let start: HourlyPoint | null = null;
  let previous: HourlyPoint | null = null;
  for (const point of points) {
    if (point.is_rain) {
      if (start === null) start = point;
      previous = point;
      continue;
    }
    if (start !== null && previous !== null) {
      intervals.push({ from: start.at, to: new Date(previous.at.getTime() + 3_600_000) });
      start = null;
    }
  }
  if (start !== null && previous !== null) {
    intervals.push({ from: start.at, to: new Date(previous.at.getTime() + 3_600_000) });
  }
  return intervals;
}

/** Sateiset vuorokaudet paivasarjasta, taustavarjostusta varten. */
export function rainyDayIntervals(rows: DailyRow[], threshold: number): Interval[] {
  return rows
    .filter((row) => (row.precip_sum ?? 0) >= threshold)
    .map((row) => ({ from: plotDay(row.date), to: new Date(plotDay(row.date).getTime() + 86_400_000) }));
}

export interface Holiday {
  date: string;
  at: Date;
  name: string;
}

export function holidaysIn(rows: { date: string; is_holiday: boolean; holiday_name?: string }[]): Holiday[] {
  return rows
    .filter((row) => row.is_holiday)
    .map((row) => ({ date: row.date, at: plotDay(row.date), name: row.holiday_name ?? 'Pyhäpäivä' }));
}

/** Pienimman nelionsumman suora. Palauttaa myos Pearsonin korrelaatiokertoimen. */
export interface LinearFit {
  slope: number;
  intercept: number;
  r: number;
  n: number;
  predict: (x: number) => number;
}

export function linearFit(points: { x: number; y: number }[]): LinearFit | null {
  const usable = points.filter((point) => Number.isFinite(point.x) && Number.isFinite(point.y));
  const n = usable.length;
  if (n < 3) return null;
  const meanX = usable.reduce((acc, point) => acc + point.x, 0) / n;
  const meanY = usable.reduce((acc, point) => acc + point.y, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (const point of usable) {
    const dx = point.x - meanX;
    const dy = point.y - meanY;
    sxy += dx * dy;
    sxx += dx * dx;
    syy += dy * dy;
  }
  if (sxx === 0 || syy === 0) return null;
  const slope = sxy / sxx;
  const intercept = meanY - slope * meanX;
  return {
    slope,
    intercept,
    r: sxy / Math.sqrt(sxx * syy),
    n,
    predict: (x: number) => slope * x + intercept,
  };
}

export function meanOf(values: number[]): number {
  return values.length === 0 ? 0 : values.reduce((acc, value) => acc + value, 0) / values.length;
}

export function medianOf(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[middle - 1]! + sorted[middle]!) / 2 : sorted[middle]!;
}

export function quantileOf(values: number[], q: number): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const position = (sorted.length - 1) * q;
  const lower = Math.floor(position);
  const upper = Math.ceil(position);
  if (lower === upper) return sorted[lower]!;
  return sorted[lower]! + (sorted[upper]! - sorted[lower]!) * (position - lower);
}
