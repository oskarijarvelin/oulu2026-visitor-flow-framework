/**
 * Varit. Sarja on Okabe-Ito, joka erottuu punavihervarisokealle. Kaaviot erottavat
 * sarjat lisaksi viivatyylilla, joten pelkka vari ei kanna tietoa.
 */

export const SERIES = {
  history: '#0072b2',
  forecast: '#d55e00',
  compare: '#009e73',
  accent: '#cc79a7',
  light: '#56b4e9',
} as const;

export const NEUTRAL = {
  ink: '#14171f',
  muted: '#4b5361',
  grid: '#e3e6eb',
  line: '#d5d9e0',
  surface: '#ffffff',
} as const;

/** Ennustevalin tayttovari. Vaalea mutta erottuva myos harmaasavyisena. */
export const BAND_FILL = '#f4c8a8';
export const BAND_FILL_COMPARE = '#bfe3d5';

/** Sadetuntien taustavari. */
export const RAIN_FILL = '#d9e6f2';

/** Pyhapaivien pystyviiva. */
export const HOLIDAY_LINE = '#6b7280';

/** Klimatologia-alue ennustekaaviossa: sama sanoma kuin kuvion viivoituksella. */
export const CLIMATOLOGY_FILL = '#efe6d8';

/** Puuttuva havainto lampokartassa. */
export const MISSING_FILL = '#c9ced7';

/**
 * Sekventiaalinen skaala lampokartalle. Viridis on havaintotasaisesti nouseva ja
 * sailyttaa jarjestyksensa harmaasavyisena, joten se toimii myos tulostettuna.
 */
export const SEQUENTIAL_SCHEME = 'viridis';

export const WEATHER_GROUP_COLOR: Record<string, string> = {
  clear: '#e69f00',
  cloudy: '#56b4e9',
  rain: '#0072b2',
  snow: '#7f8c9b',
  other: '#cc79a7',
};

/** Malleille vakioidut varit ja viivatyylit, jotta ne ovat samat joka sivulla. */
export const MODEL_STYLE: Record<string, { color: string; dash: string | null }> = {
  baseline: { color: SERIES.forecast, dash: '6 4' },
  prophet_xgb: { color: SERIES.compare, dash: '2 3' },
  seasonal_naive: { color: NEUTRAL.muted, dash: '1 3' },
  moving_average_28d: { color: SERIES.accent, dash: '8 3 2 3' },
};

export function modelStyle(model: string): { color: string; dash: string | null } {
  return MODEL_STYLE[model] ?? { color: SERIES.light, dash: '4 4' };
}
