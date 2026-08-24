/**
 * Odotetut sarakkeet jokaiselle syotetiedostolle.
 *
 * Tama on osioiden 1 ja 3 kanssa sovittu rajapinta, kuvattu FRAMEWORK_PLAN.md luvuissa
 * 4.2 ja 4.3. Sarakkeet tarkistetaan, ei oleteta: jos Python-osio nimeaa sarakkeen
 * uudelleen tai pudottaa sen, build kaatuu tassa eika vasta puolivalmiissa JSONissa.
 */

import { BuildDataError, type Table } from './csv.ts';

export const PROCESSED_SCHEMA = {
  'visitors_hourly.csv': [
    'venue_id',
    'ts_utc',
    'ts_local',
    'visitors_in',
    'visitors_out',
    'visitors_total',
    'is_imputed',
  ],
  'visitors_daily.csv': [
    'venue_id',
    'date',
    'visitors_in',
    'visitors_out',
    'visitors_total',
    'observed_hours',
    'is_complete',
  ],
  'weather_hourly.csv': [
    'venue_id',
    'ts_utc',
    'ts_local',
    'temperature_2m',
    'precipitation',
    'wind_speed_10m',
    'relative_humidity_2m',
    'weathercode',
    'weathercode_str',
    'is_precipitation',
    'is_cold',
    'is_windy',
    'source',
  ],
  'weather_daily.csv': [
    'venue_id',
    'date',
    'temp_mean',
    'temp_min',
    'temp_max',
    'precip_sum',
    'precip_hours',
    'wind_mean',
    'weathercode_mode',
    'weathercode_str',
    'source',
  ],
  'traffic_hourly.csv': ['site_id', 'site_name', 'ts_utc', 'ts_local', 'jk_in', 'jk_out', 'pp_in', 'pp_out'],
  'tickets_daily.csv': ['venue_id', 'date', 'tickets_sold', 'groups_sold', 'tickets_total'],
  'calendar_daily.csv': [
    'date',
    'holiday_name',
    'is_holiday',
    'is_weekend',
    'day_of_week',
    'days_before_next_holiday',
    'is_last_workday_before_holiday',
    'week_of_year',
    'month',
    'year',
  ],
} as const satisfies Record<string, readonly string[]>;

export const FORECAST_SCHEMA = {
  'daily_30d.csv': [
    'venue_id',
    'date',
    'horizon_days',
    'model',
    'p10',
    'p50',
    'p90',
    'weather_source',
    'temp_mean',
    'precip_sum',
    'weathercode_str',
    'is_holiday',
    'holiday_name',
    'generated_at',
  ],
  'hourly_7d.csv': [
    'venue_id',
    'ts_utc',
    'ts_local',
    'horizon_hours',
    'model',
    'p10',
    'p50',
    'p90',
    'hour',
    'weather_source',
    'temperature_2m',
    'precipitation',
    'weathercode_str',
    'generated_at',
  ],
  'backtest.csv': [
    'model',
    'venue_id',
    'origin_date',
    'target_date',
    'horizon_days',
    'y_true',
    'y_pred',
    'p10',
    'p90',
  ],
} as const satisfies Record<string, readonly string[]>;

/** Kentat joiden on loydyttava `data/processed/manifest.json`-tiedostosta. */
export const INGEST_MANIFEST_KEYS = ['generated_at', 'pipeline', 'version', 'sources', 'coverage', 'quality_gates'];

/** Kentat joiden on loydyttava `data/forecasts/latest/manifest.json`-tiedostosta. */
export const FORECAST_MANIFEST_KEYS = ['generated_at', 'pipeline', 'version', 'models', 'venues'];

/** Kentat joiden on loydyttava venuekohtaisesta `metrics.json`-tiedostosta. */
export const METRICS_KEYS = [
  'venue_id',
  'venue_name',
  'origin_date',
  'n_training_days',
  'training_window',
  'n_origins',
  'backtest_window',
  'horizon_buckets',
  'models',
  'benchmarks',
  'metrics',
  'benchmark_comparison',
  'interval_bands',
  'coverage_method',
  'do_not_trust',
  'warnings',
  'hourly_profile',
];

/**
 * Vaatii etta taulukossa on tasan odotetut sarakkeet. Jarjestys saa vaihdella,
 * mutta puuttuva tai ylimaarainen sarake kaataa buildin.
 */
export function assertColumns(table: Table, expected: readonly string[]): void {
  const actual = new Set(table.columns);
  const missing = expected.filter((column) => !actual.has(column));
  const extra = table.columns.filter((column) => !expected.includes(column));
  if (missing.length === 0 && extra.length === 0) return;

  const parts = [`Tiedoston ${table.name} skeema ei vastaa odotettua.`];
  if (missing.length > 0) parts.push(`  Puuttuvat sarakkeet: ${missing.join(', ')}`);
  if (extra.length > 0) parts.push(`  Odottamattomat sarakkeet: ${extra.join(', ')}`);
  parts.push(`  Odotettu: ${expected.join(', ')}`);
  parts.push(`  Luettu:   ${table.columns.join(', ')}`);
  parts.push('  Korjaa joko Python-osion tuloste tai packages/web/scripts/lib/schema.ts.');
  throw new BuildDataError(parts.join('\n'));
}

/** Vaatii etta JSON-objektissa on kaikki nimetyt avaimet. */
export function assertKeys(value: unknown, expected: readonly string[], name: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new BuildDataError(`Tiedoston ${name} sisallon pitaisi olla JSON-objekti.`);
  }
  const record = value as Record<string, unknown>;
  const missing = expected.filter((key) => !(key in record));
  if (missing.length > 0) {
    throw new BuildDataError(
      `Tiedoston ${name} skeema ei vastaa odotettua.\n  Puuttuvat kentat: ${missing.join(', ')}\n` +
        '  Korjaa joko Python-osion tuloste tai packages/web/scripts/lib/schema.ts.',
    );
  }
  return record;
}
