/**
 * Aikalaskennan apurit. Kaikki data on jo Suomen aikaa, joten nama kasittelevat
 * merkkijonoja eivatka tee aikavyohykemuunnoksia. Ainoa poikkeus on `utcToHelsinki`,
 * jota tarvitaan manifestien UTC-aikaleimoille.
 */

import type { Dow } from './types.ts';

/** Kalenteripaiva paikallisesta aikaleimasta: "2026-05-22T14" -> "2026-05-22". */
export function localDate(ts: string): string {
  return ts.slice(0, 10);
}

/** Paikallinen tunti: "2026-05-22T14" -> 14. */
export function localHour(ts: string): number {
  return Number(ts.slice(11, 13));
}

/**
 * Paikallinen aikaleima Date-olioksi piirtamista varten.
 *
 * Seinakelloaika tulkitaan UTC:na, jolloin kaikki akselien ja tekstien muotoilu
 * UTC-metodeilla nayttaa tasmalleen Suomen ajan ilman aikavyohykekirjastoja.
 * Syksyn kesaajan paattymispaivana toistuva tunti saa saman leiman kahdesti; se on
 * tiedostettu kosmeettinen rajoite eika vaikuta lukuihin.
 */
export function plotDate(ts: string): Date {
  const [datePart, hourPart] = ts.split('T');
  return new Date(`${datePart}T${(hourPart ?? '00').slice(0, 2)}:00:00Z`);
}

/** Kalenteripaiva Date-olioksi piirtamista varten. */
export function plotDay(date: string): Date {
  return new Date(`${date}T00:00:00Z`);
}

/** Kalenteripaivien erotus, molemmat muodossa YYYY-MM-DD. */
export function daysBetween(from: string, to: string): number {
  return Math.round((plotDay(to).getTime() - plotDay(from).getTime()) / 86_400_000);
}

export function addDays(date: string, days: number): string {
  return new Date(plotDay(date).getTime() + days * 86_400_000).toISOString().slice(0, 10);
}

/** Viikonpaiva 0 = maanantai, sama konventio kuin `calendar_daily.day_of_week`. */
export function dowOf(date: string): Dow {
  return ((plotDay(date).getUTCDay() + 6) % 7) as Dow;
}

/** Manifestin ika tunteina. Negatiivinen jos manifesti on tulevaisuudesta. */
export function ageHours(generatedAt: string, now: Date): number {
  return (now.getTime() - Date.parse(generatedAt)) / 3_600_000;
}

const HELSINKI = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Europe/Helsinki',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
});

/** UTC-aikaleima "2026-08-24T10:02:25Z" -> paikallinen "2026-08-24T13:02". */
export function utcToHelsinki(iso: string): string {
  const parts = HELSINKI.formatToParts(new Date(iso));
  const get = (type: Intl.DateTimeFormatPartTypes): string =>
    parts.find((part) => part.type === type)?.value ?? '00';
  const hour = get('hour') === '24' ? '00' : get('hour');
  return `${get('year')}-${get('month')}-${get('day')}T${hour}:${get('minute')}`;
}
