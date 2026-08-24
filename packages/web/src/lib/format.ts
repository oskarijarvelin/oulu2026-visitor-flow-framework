/**
 * Suomenkielinen esitysmuoto. Kaikki paivamaarat ja kellonajat ovat Suomen aikaa:
 * data on jo paikallista aikaa, joten muotoilu on merkkijonojen kasittelya.
 */

import { localHour, plotDay, utcToHelsinki } from './dates.ts';
import type { Dow } from './types.ts';

const INTEGER = new Intl.NumberFormat('fi-FI', { maximumFractionDigits: 0 });
const ONE_DECIMAL = new Intl.NumberFormat('fi-FI', { minimumFractionDigits: 1, maximumFractionDigits: 1 });

export function formatInt(value: number): string {
  return INTEGER.format(Math.round(value));
}

export function formatDecimal(value: number, decimals = 1): string {
  if (decimals === 1) return ONE_DECIMAL.format(value);
  return new Intl.NumberFormat('fi-FI', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/** Etumerkillinen prosenttiluku, esim. "+3,4 %" tai "-3,0 %". */
export function formatSignedPct(value: number): string {
  const sign = value > 0 ? '+' : '';
  return `${sign}${formatDecimal(value)} %`;
}

/**
 * Kavijaluku aina yksikon kanssa. `visitors_total` on sisaan- ja ulosmenojen summa,
 * joten yksikko on tapahtuma, ei henkilo.
 */
export function visitorEvents(value: number, decimals = 0): string {
  const number = decimals === 0 ? formatInt(value) : formatDecimal(value, decimals);
  return `${number} kävijätapahtumaa`;
}

export function visitorEventsPerDay(value: number, decimals = 1): string {
  return `${formatDecimal(value, decimals)} kävijätapahtumaa vuorokaudessa`;
}

/** "2026-05-22" -> "22.5.2026" */
export function formatDate(date: string): string {
  const day = Number(date.slice(8, 10));
  const month = Number(date.slice(5, 7));
  return `${day}.${month}.${date.slice(0, 4)}`;
}

/** "2026-05-22" -> "22.5." Lyhyt muoto akseleille ja taulukoihin. */
export function formatDateShort(date: string): string {
  return `${Number(date.slice(8, 10))}.${Number(date.slice(5, 7))}.`;
}

/** "2026-05-22T14" -> "14:00" */
export function formatHour(ts: string): string {
  return `${String(localHour(ts)).padStart(2, '0')}:00`;
}

/** "2026-05-22T14" -> "22.5.2026 14:00" */
export function formatDateTime(ts: string): string {
  return `${formatDate(ts.slice(0, 10))} ${formatHour(ts)}`;
}

/** UTC-aikaleimasta Suomen aikaan: "2026-08-24T10:02:25Z" -> "24.8.2026 13:02" */
export function formatUtcAsHelsinki(iso: string): string {
  const local = utcToHelsinki(iso);
  return `${formatDate(local.slice(0, 10))} ${local.slice(11, 16)}`;
}

export const WEEKDAYS_SHORT = ['ma', 'ti', 'ke', 'to', 'pe', 'la', 'su'] as const;
export const WEEKDAYS_LONG = [
  'maanantai',
  'tiistai',
  'keskiviikko',
  'torstai',
  'perjantai',
  'lauantai',
  'sunnuntai',
] as const;

export function weekdayShort(dow: Dow): string {
  return WEEKDAYS_SHORT[dow] ?? '';
}

export function weekdayLong(dow: Dow): string {
  return WEEKDAYS_LONG[dow] ?? '';
}

/** "22.5.2026 (pe)" */
export function formatDateWithWeekday(date: string): string {
  const dow = ((plotDay(date).getUTCDay() + 6) % 7) as Dow;
  return `${formatDate(date)} (${weekdayShort(dow)})`;
}

export function formatCelsius(value: number | null | undefined): string {
  return value === null || value === undefined ? 'ei tietoa' : `${formatDecimal(value)} °C`;
}

export function formatMm(value: number | null | undefined): string {
  return value === null || value === undefined ? 'ei tietoa' : `${formatDecimal(value)} mm`;
}

export function formatHours(value: number): string {
  return `${formatDecimal(value)} tuntia`;
}

/** Tuntien lista tiivistettyna, esim. [7,8,9,11] -> "07-09, 11". */
export function formatHourRanges(hours: number[]): string {
  if (hours.length === 0) return 'ei tietoa';
  const sorted = [...hours].sort((a, b) => a - b);
  const ranges: string[] = [];
  let start = sorted[0]!;
  let previous = start;
  for (const hour of sorted.slice(1)) {
    if (hour === previous + 1) {
      previous = hour;
      continue;
    }
    ranges.push(start === previous ? pad(start) : `${pad(start)}-${pad(previous)}`);
    start = hour;
    previous = hour;
  }
  ranges.push(start === previous ? pad(start) : `${pad(start)}-${pad(previous)}`);
  return ranges.join(', ');
}

function pad(hour: number): string {
  return String(hour).padStart(2, '0');
}
