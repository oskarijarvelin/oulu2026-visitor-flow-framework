/**
 * Suomenkieliset nimet malleille ja lahteille seka Python-osioiden englanninkielisten
 * varoitusten kaannokset. Tuntematon varoitus naytetaan sellaisenaan: se on parempi
 * kuin varoituksen piilottaminen.
 */

import type { ModelName } from './types.ts';

export const MODEL_LABEL: Record<string, string> = {
  baseline: 'Perusmalli',
  prophet_xgb: 'Prophet + XGBoost',
  seasonal_naive: 'Sama viikonpäivä viimeksi',
  moving_average_28d: '28 vrk liukuva keskiarvo',
};

export const MODEL_DESCRIPTION: Record<string, string> = {
  baseline: 'Gradient boosting Poisson-tappiolla, tuotantomalli.',
  prophet_xgb: 'Prophet-trendi ja XGBoost-jäännösmalli, vertailukohta.',
  seasonal_naive: 'Vertailukohta: saman viikonpäivän viimeisin havainto.',
  moving_average_28d: 'Vertailukohta: 28 vuorokauden liukuva keskiarvo.',
};

export function modelLabel(model: ModelName): string {
  return MODEL_LABEL[model] ?? model;
}

export const SOURCE_LABEL: Record<string, string> = {
  jaskaretail: 'Jaskaretail, kävijälaskurit',
  'open-meteo': 'Open-Meteo, sää',
  'eco-counter': 'Eco-Counter, Oulun liikenne',
  tickets: 'Lipunmyynti, ylläpidetty CSV',
  calendar: 'Pyhäkalenteri',
};

export function sourceLabel(name: string): string {
  return SOURCE_LABEL[name] ?? name;
}

export const SOURCE_STATUS_LABEL: Record<string, string> = {
  ok: 'kunnossa',
  degraded: 'heikentynyt',
  failed: 'epäonnistui',
  missing: 'puuttuu',
};

export function sourceStatusLabel(status: string): string {
  return SOURCE_STATUS_LABEL[status] ?? status;
}

export const WEATHER_SOURCE_LABEL: Record<string, string> = {
  archive: 'toteutunut sää',
  forecast: 'sääennuste',
  climatology: 'klimatologia, 10 vuoden keskiarvo',
};

export function weatherSourceLabel(source: string): string {
  return WEATHER_SOURCE_LABEL[source] ?? source;
}

/** Osioiden 1 ja 3 kirjoittamat varoitukset ovat englanniksi. Nama ovat tunnetut. */
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

/** Kaantaa tunnetun varoituksen. Tuntematon palautetaan sellaisenaan. */
export function translateWarning(warning: string): string {
  for (const pattern of WARNING_PATTERNS) {
    const match = pattern.test.exec(warning);
    if (match) return pattern.render(match);
  }
  return warning;
}

export function translateWarnings(warnings: string[]): string[] {
  return warnings.map(translateWarning);
}

export const HORIZON_BUCKET_LABEL: Record<string, string> = {
  '1-7': '1-7 vrk',
  '8-14': '8-14 vrk',
  '15-30': '15-30 vrk',
};

export function horizonBucketLabel(bucket: string): string {
  return HORIZON_BUCKET_LABEL[bucket] ?? `${bucket} vrk`;
}
