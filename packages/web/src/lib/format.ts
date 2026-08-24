/**
 * Kielikohtainen esitysmuoto.
 *
 * Kaikki aikaleimat ovat Suomen aikaa riippumatta kayttoliittyman kielesta: data on jo
 * paikallista aikaa, joten muotoilu on merkkijonojen kasittelya. Englanninkielinen
 * versio nayttaa siis samat hetket, vain eri kirjoitusasussa.
 *
 * Every timestamp is Finnish local time regardless of interface language: the data is
 * already local, so formatting is string handling. The English pages show the same
 * instants, only written differently.
 */

import { LOCALE, type Lang } from '../i18n/index.ts';
import { localHour, plotDay, utcToHelsinki } from './dates.ts';
import type { Dow } from './types.ts';

const WEEKDAYS_SHORT: Record<Lang, readonly string[]> = {
  fi: ['ma', 'ti', 'ke', 'to', 'pe', 'la', 'su'],
  en: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
};

const WEEKDAYS_LONG: Record<Lang, readonly string[]> = {
  fi: ['maanantai', 'tiistai', 'keskiviikko', 'torstai', 'perjantai', 'lauantai', 'sunnuntai'],
  en: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
};

const MONTHS_SHORT: Record<Lang, readonly string[]> = {
  fi: ['tammi', 'helmi', 'maalis', 'huhti', 'touko', 'kesä', 'heinä', 'elo', 'syys', 'loka', 'marras', 'joulu'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
};

/** Yksikko jonka kanssa jokainen kavijaluku esitetaan. */
const COUNT_UNIT: Record<Lang, { one: string; many: string; perDay: string }> = {
  fi: { one: 'kävijätapahtuma', many: 'kävijätapahtumaa', perDay: 'kävijätapahtumaa vuorokaudessa' },
  en: { one: 'visitor event', many: 'visitor events', perDay: 'visitor events per day' },
};

export interface Formatters {
  readonly lang: Lang;
  /** Kokonaisluku ryhmiteltyna, esim. "1 234" tai "1,234". */
  int(value: number): string;
  decimal(value: number, decimals?: number): string;
  /** Etumerkillinen prosenttiluku, esim. "+3,4 %" tai "+3.4%". */
  signedPct(value: number): string;
  pct(value: number, decimals?: number): string;
  /** Kavijaluku aina yksikon kanssa: se on tapahtuma, ei henkilo. */
  count(value: number, decimals?: number): string;
  countPerDay(value: number, decimals?: number): string;
  /** "22.5.2026" tai "22 May 2026". */
  date(date: string): string;
  /** Lyhyt muoto akseleille: "22.5." tai "22 May". */
  dateShort(date: string): string;
  /** "22.5.2026 (pe)" tai "22 May 2026 (Fri)". */
  dateWithWeekday(date: string): string;
  /** Suljettu vali kahden paivan valilla. */
  dateRange(from: string, to: string): string;
  /** "14:00" tuntileimasta "2026-05-22T14". */
  hour(ts: string): string;
  /** "22.5.2026 14:00". */
  dateTime(ts: string): string;
  /** UTC-aikaleima Suomen aikaan kirjoitettuna. */
  utc(iso: string): string;
  weekdayShort(dow: Dow): string;
  weekdayLong(dow: Dow): string;
  weekdaysShort(): readonly string[];
  monthShort(index: number): string;
  celsius(value: number | null | undefined): string;
  mm(value: number | null | undefined): string;
  /** Tuntilista tiivistettyna, esim. "07-09, 11". */
  hourRanges(hours: number[]): string;
  /** Puuttuvan arvon merkinta taulukoissa. */
  missing(): string;
}

const CACHE = new Map<Lang, Formatters>();

/** Muotoilijat yhdelle kielelle. Sama olio palautetaan aina, joten Intl-oliot jaetaan. */
export function formatters(lang: Lang): Formatters {
  const cached = CACHE.get(lang);
  if (cached) return cached;
  const created = build(lang);
  CACHE.set(lang, created);
  return created;
}

function build(lang: Lang): Formatters {
  const locale = LOCALE[lang];
  const integer = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 });
  const oneDecimal = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  const unit = COUNT_UNIT[lang];
  const short = WEEKDAYS_SHORT[lang];
  const long = WEEKDAYS_LONG[lang];
  const months = MONTHS_SHORT[lang];
  const isFinnish = lang === 'fi';

  const int = (value: number): string => integer.format(Math.round(value));

  const decimal = (value: number, decimals = 1): string => {
    if (decimals === 1) return oneDecimal.format(value);
    return new Intl.NumberFormat(locale, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    }).format(value);
  };

  const date = (value: string): string => {
    const day = Number(value.slice(8, 10));
    const month = Number(value.slice(5, 7));
    const year = value.slice(0, 4);
    // Suomessa numeromuoto on vakiintunut, englanniksi kuukauden nimi on selvempi
    // eika sekoitu amerikkalaiseen jarjestykseen.
    return isFinnish ? `${day}.${month}.${year}` : `${day} ${months[month - 1]} ${year}`;
  };

  const dateShort = (value: string): string => {
    const day = Number(value.slice(8, 10));
    const month = Number(value.slice(5, 7));
    return isFinnish ? `${day}.${month}.` : `${day} ${months[month - 1]}`;
  };

  const weekdayShort = (dow: Dow): string => short[dow] ?? '';

  const hour = (ts: string): string => `${String(localHour(ts)).padStart(2, '0')}:00`;

  return {
    lang,
    int,
    decimal,
    signedPct: (value: number): string => {
      const sign = value > 0 ? '+' : '';
      return isFinnish ? `${sign}${decimal(value)} %` : `${sign}${decimal(value)}%`;
    },
    pct: (value: number, decimals = 1): string =>
      isFinnish ? `${decimal(value, decimals)} %` : `${decimal(value, decimals)}%`,
    count: (value: number, decimals = 0): string => {
      const number = decimals === 0 ? int(value) : decimal(value, decimals);
      const word = Math.abs(value) === 1 && decimals === 0 ? unit.one : unit.many;
      return `${number} ${word}`;
    },
    countPerDay: (value: number, decimals = 1): string => `${decimal(value, decimals)} ${unit.perDay}`,
    date,
    dateShort,
    dateWithWeekday: (value: string): string => {
      const dow = ((plotDay(value).getUTCDay() + 6) % 7) as Dow;
      return `${date(value)} (${weekdayShort(dow)})`;
    },
    dateRange: (from: string, to: string): string => `${date(from)} - ${date(to)}`,
    hour,
    dateTime: (ts: string): string => `${date(ts.slice(0, 10))} ${hour(ts)}`,
    utc: (iso: string): string => {
      const local = utcToHelsinki(iso);
      return `${date(local.slice(0, 10))} ${local.slice(11, 16)}`;
    },
    weekdayShort,
    weekdayLong: (dow: Dow): string => long[dow] ?? '',
    weekdaysShort: () => short,
    monthShort: (index: number): string => months[index] ?? '',
    celsius: (value: number | null | undefined): string =>
      value === null || value === undefined
        ? isFinnish
          ? 'ei tietoa'
          : 'no data'
        : `${decimal(value)} °C`,
    mm: (value: number | null | undefined): string =>
      value === null || value === undefined
        ? isFinnish
          ? 'ei tietoa'
          : 'no data'
        : `${decimal(value)} mm`,
    hourRanges: (hours: number[]): string => {
      if (hours.length === 0) return isFinnish ? 'ei tietoa' : 'no data';
      const sorted = [...hours].sort((a, b) => a - b);
      const ranges: string[] = [];
      let start = sorted[0]!;
      let previous = start;
      for (const value of sorted.slice(1)) {
        if (value === previous + 1) {
          previous = value;
          continue;
        }
        ranges.push(start === previous ? pad(start) : `${pad(start)}-${pad(previous)}`);
        start = value;
        previous = value;
      }
      ranges.push(start === previous ? pad(start) : `${pad(start)}-${pad(previous)}`);
      return ranges.join(', ');
    },
    missing: () => '-',
  };
}

function pad(hour: number): string {
  return String(hour).padStart(2, '0');
}
