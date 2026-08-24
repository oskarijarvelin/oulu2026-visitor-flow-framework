/**
 * Kielikohtaiset nimet malleille ja lahteille seka Python-osioiden englanninkielisten
 * varoitusten kaannokset.
 *
 * Osiot 1 ja 3 kirjoittavat varoituksensa englanniksi. Englanninkielisessa
 * kayttoliittymassa ne naytetaan sellaisenaan, suomenkielisessa kaannettyna.
 * Tuntematon varoitus naytetaan aina sellaisenaan: se on parempi kuin varoituksen
 * piilottaminen.
 */

import type { Lang } from '../i18n/index.ts';
import type { ModelName } from './types.ts';

const MODEL_LABEL: Record<Lang, Record<string, string>> = {
  fi: {
    baseline: 'Perusmalli',
    prophet_xgb: 'Prophet + XGBoost',
    seasonal_naive: 'Sama viikonpäivä viimeksi',
    moving_average_28d: '28 vrk liukuva keskiarvo',
  },
  en: {
    baseline: 'Baseline',
    prophet_xgb: 'Prophet + XGBoost',
    seasonal_naive: 'Same weekday last time',
    moving_average_28d: '28-day moving average',
  },
};

export function modelLabel(model: ModelName, lang: Lang): string {
  return MODEL_LABEL[lang][model] ?? model;
}

const SOURCE_LABEL: Record<Lang, Record<string, string>> = {
  fi: {
    jaskaretail: 'Jaskaretail, kävijälaskurit',
    'open-meteo': 'Open-Meteo, sää',
    'eco-counter': 'Eco-Counter, Oulun liikenne',
    tickets: 'Lipunmyynti, ylläpidetty CSV',
    calendar: 'Pyhäkalenteri',
  },
  en: {
    jaskaretail: 'Jaskaretail, visitor counters',
    'open-meteo': 'Open-Meteo, weather',
    'eco-counter': 'Eco-Counter, Oulu traffic',
    tickets: 'Ticket sales, maintained CSV',
    calendar: 'Holiday calendar',
  },
};

export function sourceLabel(name: string, lang: Lang): string {
  return SOURCE_LABEL[lang][name] ?? name;
}

const SOURCE_STATUS_LABEL: Record<Lang, Record<string, string>> = {
  fi: { ok: 'kunnossa', degraded: 'heikentynyt', failed: 'epäonnistui', missing: 'puuttuu' },
  en: { ok: 'ok', degraded: 'degraded', failed: 'failed', missing: 'missing' },
};

export function sourceStatusLabel(status: string, lang: Lang): string {
  return SOURCE_STATUS_LABEL[lang][status] ?? status;
}

const WEATHER_SOURCE_LABEL: Record<Lang, Record<string, string>> = {
  fi: {
    archive: 'toteutunut sää',
    forecast: 'sääennuste',
    climatology: 'klimatologia, 10 vuoden keskiarvo',
  },
  en: {
    archive: 'observed weather',
    forecast: 'weather forecast',
    climatology: 'climatology, 10-year average',
  },
};

export function weatherSourceLabel(source: string, lang: Lang): string {
  return WEATHER_SOURCE_LABEL[lang][source] ?? source;
}

const HORIZON_BUCKET_LABEL: Record<Lang, (bucket: string) => string> = {
  fi: (bucket) => `${bucket} vrk`,
  en: (bucket) => `${bucket} days`,
};

export function horizonBucketLabel(bucket: string, lang: Lang): string {
  return HORIZON_BUCKET_LABEL[lang](bucket);
}

/**
 * Osioiden 1 ja 3 varoitukset ovat englanniksi. Nama ovat tunnetut muodot; muut
 * palautetaan sellaisenaan.
 */
const WARNING_PATTERNS: { test: RegExp; render: (match: RegExpExecArray) => string }[] = [
  {
    test: /^The last observed day is (\d{4}-\d{2}-\d{2}), (\d+) days before this run\./,
    render: (match) =>
      `Viimeisin havaittu päivä on ${fi(match[1]!)}, eli ${match[2]} vuorokautta ennen ajoa. ` +
      'Ennuste lähtee vanhentuneesta tasosta.',
  },
  {
    test: /^The maintained calendar does not reach (\d{4}-\d{2}-\d{2}); those days assume no holiday\.$/,
    render: (match) =>
      `Ylläpidetty pyhäkalenteri ei ulotu päivään ${fi(match[1]!)} asti. Sen jälkeisiä ` +
      'ennustepäiviä käsitellään arkipäivinä, vaikka joukossa olisi pyhä.',
  },
  {
    test: /^Horizons past (\d+) days: the weather is climatology and the level is frozen at the origin\.$/,
    render: (match) =>
      `Yli ${match[1]} vuorokauden horisontit: sää on klimatologiaa ja taso on lukittu ennusteen origoon.`,
  },
  {
    test: /^Days with programming or an event the model has never seen\.$/,
    render: () => 'Päivät joilla on ohjelmistoa tai tapahtuma, jota malli ei ole nähnyt.',
  },
  {
    test: /^The first two weeks after a new venue or a new sensor comes online\.$/,
    render: () => 'Kaksi ensimmäistä viikkoa uuden venuen tai uuden sensorin käyttöönotosta.',
  },
  {
    test: /^Periods where the ingest manifest reports a degraded source\.$/,
    render: () => 'Jaksot joilla ingest-manifesti raportoi heikentyneen lähteen.',
  },
  {
    test: /^School holidays and midsummer, of which this dataset holds at most one observation\.$/,
    render: () => 'Koulujen loma-ajat ja juhannus, joista aineistossa on korkeintaan yksi havainto.',
  },
];

function fi(date: string): string {
  return `${Number(date.slice(8, 10))}.${Number(date.slice(5, 7))}.${date.slice(0, 4)}`;
}

/** Kaantaa tunnetun varoituksen. Englanniksi lahde on jo oikealla kielella. */
export function translateWarning(warning: string, lang: Lang): string {
  if (lang === 'en') return warning;
  for (const pattern of WARNING_PATTERNS) {
    const match = pattern.test.exec(warning);
    if (match) return pattern.render(match);
  }
  return warning;
}

export function translateWarnings(warnings: string[], lang: Lang): string[] {
  return warnings.map((warning) => translateWarning(warning, lang));
}
