/**
 * Saan luokittelu. Sama WMO-koodikartta ja sama sadekynnys kuin
 * `packages/forecast/src/ovf_forecast/dataset.py` kayttaa, jotta sivusto ja malli
 * puhuvat samasta saasta.
 */

import type { Lang } from '../i18n/index.ts';
import type { WeatherGroup } from './types.ts';

const WEATHER_GROUPS: Record<Exclude<WeatherGroup, 'other'>, number[]> = {
  clear: [0, 1],
  cloudy: [2, 3, 45, 48],
  rain: [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99],
  snow: [71, 73, 75, 77, 85, 86],
};

const CODE_TO_GROUP = new Map<number, WeatherGroup>();
for (const [group, codes] of Object.entries(WEATHER_GROUPS)) {
  for (const code of codes) CODE_TO_GROUP.set(code, group as WeatherGroup);
}

export function weatherGroup(code: number | null | undefined): WeatherGroup | null {
  if (code === null || code === undefined || !Number.isFinite(code)) return null;
  return CODE_TO_GROUP.get(Math.round(code)) ?? 'other';
}

/** Sama kynnys kuin mallin `is_rainy_day`-piirteella: `RAINY_DAY_MM = 1.0`. */
export const RAINY_DAY_MM = 1.0;

/** Tunti lasketaan sadetunniksi kun sademaara on vahintaan tama. */
export const RAINY_HOUR_MM = 0.1;

export function isRainyDay(precipSum: number | null | undefined): boolean | null {
  if (precipSum === null || precipSum === undefined) return null;
  return precipSum >= RAINY_DAY_MM;
}

export const WEATHER_GROUP_ORDER: WeatherGroup[] = ['clear', 'cloudy', 'rain', 'snow', 'other'];

const WEATHER_GROUP_LABEL: Record<Lang, Record<WeatherGroup, string>> = {
  fi: {
    clear: 'Selkeää',
    cloudy: 'Pilvistä',
    rain: 'Sadetta',
    snow: 'Lunta',
    other: 'Muu',
  },
  en: {
    clear: 'Clear',
    cloudy: 'Cloudy',
    rain: 'Rain',
    snow: 'Snow',
    other: 'Other',
  },
};

export function weatherGroupLabel(group: WeatherGroup, lang: Lang): string {
  return WEATHER_GROUP_LABEL[lang][group];
}

/**
 * Saatilaluokka tekstimuotoisesta koodista. Ennustetiedostot kirjoittavat
 * `weathercode_str`-sarakkeen mutta eivat numerokoodia, joten luokittelu tehdaan
 * nimen perusteella. Jarjestys on merkitseva: "snow_showers" on lunta, ei sadetta.
 */
export function weatherGroupFromLabel(label: string | null | undefined): WeatherGroup | null {
  if (!label) return null;
  const value = label.toLowerCase();
  if (value.includes('snow') || value.includes('sleet') || value.includes('hail')) return 'snow';
  if (
    value.includes('rain') ||
    value.includes('drizzle') ||
    value.includes('shower') ||
    value.includes('thunder')
  ) {
    return 'rain';
  }
  if (value.includes('clear') || value.includes('sunny')) return 'clear';
  if (value.includes('cloud') || value.includes('overcast') || value.includes('fog')) return 'cloudy';
  return 'other';
}
