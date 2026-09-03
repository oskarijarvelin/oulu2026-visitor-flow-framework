/**
 * Kielikohtaiset nimet malleille ja lahteille seka valitsin putken kaksikielisille
 * teksteille.
 *
 * Osiot 1 ja 3 kirjoittavat varoituksensa molemmilla kielilla, joten sivusto valitsee
 * vain oikean avaimen. Puuttuva kaannos naytetaan toisella kielella: vaaran kielinen
 * varoitus on parempi kuin piilotettu varoitus.
 */

import type { Lang } from '../i18n/index.ts';
import type { LocalisedText, ModelName } from './types.ts';

const MODEL_LABEL: Record<Lang, Record<string, string>> = {
  fi: {
    baseline: 'Perusmalli',
    prophet_xgb: 'Prophet + XGBoost',
    seasonal_naive: 'Sama viikonpäivä viimeksi',
    moving_average_28d: '28 vrk liukuva keskiarvo',
    climatology_dow: 'Viikonpäivän keskiarvo',
  },
  en: {
    baseline: 'Baseline',
    prophet_xgb: 'Prophet + XGBoost',
    seasonal_naive: 'Same weekday last time',
    moving_average_28d: '28-day moving average',
    climatology_dow: 'Weekday mean',
  },
};

export function modelLabel(model: ModelName, lang: Lang): string {
  return MODEL_LABEL[lang][model] ?? model;
}

/**
 * Vertailukohdan nimi. Koosteessa paavertailukohta voi vaihtua ikkunasta toiseen,
 * jolloin osio 3 kirjoittaa nimeksi `best-per-window` eika mallin nimea.
 */
const REFERENCE_ANY: Record<Lang, string> = {
  fi: 'Ikkunan paras vertailukohta',
  en: 'Best reference per window',
};

export function referenceLabel(reference: string, lang: Lang): string {
  if (reference === 'best-per-window') return REFERENCE_ANY[lang];
  return modelLabel(reference, lang);
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
 * Osioiden 1 ja 3 varoitukset tulevat valmiiksi molemmilla kielilla: putki kirjoittaa
 * ne muodossa `{ fi, en }`. Aiemmin tassa oli saannollisiin lausekkeisiin perustuva
 * kaannin, joka arvasi suomennoksen englanninkielisesta muotoilusta ja putosi
 * englantiin heti kun lause kirjoitettiin uusiksi. Nyt valitaan vain avain.
 */
export function localisedText(value: LocalisedText | string, lang: Lang): string {
  if (typeof value === 'string') return value;
  return value[lang] || value.fi || value.en || '';
}

export function localisedTexts(values: (LocalisedText | string)[], lang: Lang): string[] {
  return values.map((value) => localisedText(value, lang));
}
