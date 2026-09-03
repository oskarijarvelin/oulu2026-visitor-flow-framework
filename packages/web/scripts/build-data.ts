/**
 * Paketoi `data/processed/`- ja `data/forecasts/latest/`-tiedostot sivuston
 * build-aikaiseksi JSON-dataksi hakemistoon `src/data/`.
 *
 * Ajetaan npm-skriptilla `prebuild`, eli ennen `astro build`. Skripti kaataa buildin
 * jos data puuttuu, on liian vanhaa tai sen skeema on muuttunut. Mieluummin
 * epaonnistunut build kuin sivusto joka nayttaa vanhaa dataa oikeana.
 */

import { existsSync, mkdirSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { BuildDataError, bool, int, num, optionalNum, optionalStr, str, type Row } from './lib/csv.ts';
import { CONFIG_DIR, EVALUATIONS_DIR, FORECAST_DIR, OUT_DIR, PROCESSED_DIR } from './lib/paths.ts';
import { addDays, localDate } from '../src/lib/dates.ts';
import { RAINY_HOUR_MM, WEATHER_GROUP_ORDER, weatherGroup, weatherGroupFromLabel } from '../src/lib/weather.ts';
import { readJson, readTable, requireDirectory } from './lib/read.ts';
import {
  EVALUATION_INDEX_KEYS,
  EVALUATION_RUN_KEYS,
  FORECAST_MANIFEST_KEYS,
  FORECAST_SCHEMA,
  INGEST_MANIFEST_KEYS,
  METRICS_KEYS,
  PREDICTIONS_SCHEMA,
  PROCESSED_SCHEMA,
  VERDICTS_KEYS,
  VERDICT_COMPARISON_KEYS,
  VERDICT_POOLED_KEYS,
  VERDICT_SWEEP_MODEL_KEYS,
  VERDICT_WINDOW_MODEL_KEYS,
  VERDICT_WINDOW_VENUE_KEYS,
  assertEvaluationVersion,
  assertKeys,
} from './lib/schema.ts';
import {
  HORIZON_BUCKETS,
  buildSeries,
  count1,
  horizonRows,
  modelMetrics,
  selectSeriesRuns,
  share3,
  sortRuns,
  worstDays,
  type PredictionRow,
  type RunRef,
} from './lib/accuracy.ts';
import {
  buildProfileCells,
  changePct,
  deriveOpenHours,
  forecastWeatherDays,
  maeByHorizon,
  manifestAgeHours,
  mean,
  median,
  round1,
  round1OrNull,
  roundCount,
  shortenLocalTs,
  sum,
  sumForecast,
  summarisePeriod,
} from './lib/transform.ts';
import type {
  AccuracyBias,
  AccuracyCalibration,
  AccuracyComparison,
  AccuracyData,
  AccuracyModel,
  AccuracyPerWindow,
  AccuracyPooled,
  AccuracyRun,
  AccuracyTotal,
  AccuracyVenue,
  AccuracyWeatherSensitivity,
  AccuracyWindow,
  AccuracyWindowRef,
  BacktestColumns,
  BacktestRow,
  DailyColumns,
  DailyData,
  DailyRow,
  ForecastData,
  ForecastDailyRow,
  ForecastHourlyRow,
  HorizonPoint,
  HourlyData,
  HourlySeries,
  LocalisedText,
  Meta,
  ModelName,
  ProfileData,
  QualityData,
  SourceStatus,
  TrafficDailyRow,
  VenueForecast,
  Verdict,
  VenueQuality,
  VenueSummary,
  WeatherMode,
  WeatherSource,
} from '../src/lib/types.ts';

// --- Asetukset -------------------------------------------------------------

/** Buildin laatuportti: tata vanhempi ingest-manifesti kaataa buildin. */
const MAX_MANIFEST_AGE_HOURS = Number(process.env.OVF_MAX_MANIFEST_AGE_HOURS ?? 48);
/** Tuntisarjaan otetaan vain viimeisimmat vuorokaudet, jotta sivun paino pysyy kurissa. */
const HOURLY_DAYS = Number(process.env.OVF_HOURLY_DAYS ?? 120);
/** Oletusmalli kayttoliittymassa. Perustelu: docs/FORECAST_MODEL.md luku 1. */
const PRODUCTION_MODEL = 'baseline';
/** Backtestin rivitason sarja rajataan paamalleihin; vertailukohdat jaavat koosteisiin. */
const BACKTEST_ROW_MODELS = new Set(['baseline', 'prophet_xgb']);
/** Arvioinnin vertailukohdat esitysjarjestyksessa. Sama jarjestys kuin docs/EVALUATION.md luvussa 6. */
const EVALUATION_BASELINES = ['seasonal_naive', 'moving_average_28d', 'climatology_dow'];

// --- Konfiguraatio ---------------------------------------------------------

interface VenueConfig {
  venue_id: number;
  name: string;
  city: string;
  capacity: number;
}

function readVenues(): VenueConfig[] {
  const raw = readJson(resolve(CONFIG_DIR, 'venues.json'), 'Venue-konfiguraatio') as {
    venues?: unknown;
  };
  if (!Array.isArray(raw.venues) || raw.venues.length === 0) {
    throw new BuildDataError('config/venues.json ei sisalla venues-taulukkoa.');
  }
  return raw.venues.map((entry, index) => {
    const venue = assertKeys(entry, ['venue_id', 'name', 'city', 'capacity'], `config/venues.json[${index}]`);
    return {
      venue_id: Number(venue.venue_id),
      name: String(venue.name),
      city: String(venue.city),
      capacity: Number(venue.capacity),
    };
  });
}

/**
 * Varoituslista sellaisena kuin osiot 1 ja 3 sen kirjoittavat: yksi olio kielta kohden.
 *
 * Vanhat ajot kirjoittivat pelkan merkkijonon. Se luetaan yha, samana tekstina molemmilla
 * kielilla: vanha data nakyy silloin alkukielellaan eika katoa sivulta kokonaan.
 */
function localisedList(value: unknown): LocalisedText[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    if (typeof item === 'string') return { fi: item, en: item };
    const record = (item ?? {}) as Record<string, unknown>;
    const fi = typeof record.fi === 'string' ? record.fi : '';
    const en = typeof record.en === 'string' ? record.en : '';
    return { fi: fi || en, en: en || fi };
  });
}

// --- Laatuportit -----------------------------------------------------------

interface IngestManifest {
  generated_at: string;
  version: string;
  sources: SourceStatus[];
  coverage: Record<string, { first: string; last: string; missing_hours: number }>;
  quality_gates: { passed: boolean; warnings: LocalisedText[] };
}

function readIngestManifest(now: Date): IngestManifest & { age_hours: number } {
  const path = resolve(PROCESSED_DIR, 'manifest.json');
  const raw = assertKeys(readJson(path, 'Ingest-manifesti'), INGEST_MANIFEST_KEYS, 'data/processed/manifest.json');
  const generatedAt = String(raw.generated_at);
  const age = manifestAgeHours(generatedAt, now);

  if (age > MAX_MANIFEST_AGE_HOURS) {
    throw new BuildDataError(
      [
        'Ingest-manifesti on liian vanha, build keskeytetaan.',
        `  Tiedosto:     ${path}`,
        `  generated_at: ${generatedAt}`,
        `  Ika:          ${round1(age)} tuntia`,
        `  Sallittu:     ${MAX_MANIFEST_AGE_HOURS} tuntia`,
        '',
        '  Sivustoa ei julkaista vanhalla datalla. Aja "make ingest && make forecast"',
        '  tai aseta OVF_MAX_MANIFEST_AGE_HOURS jos ajat tietoisesti vanhalla aineistolla.',
      ].join('\n'),
    );
  }
  if (age < -1) {
    throw new BuildDataError(
      `Ingest-manifestin generated_at (${generatedAt}) on tulevaisuudessa. Tarkista kellonaika.`,
    );
  }

  const gates = raw.quality_gates as { passed?: unknown; warnings?: unknown };
  return {
    generated_at: generatedAt,
    version: String(raw.version),
    sources: (raw.sources as SourceStatus[]) ?? [],
    coverage: (raw.coverage as IngestManifest['coverage']) ?? {},
    quality_gates: {
      passed: gates?.passed === true,
      warnings: localisedList(gates?.warnings),
    },
    age_hours: round1(age),
  };
}

interface ForecastManifestVenue {
  venue_id: number;
  origin_date: string;
  horizon_days: number;
  hourly_days: number;
  warnings: LocalisedText[];
}

interface ForecastManifest {
  generated_at: string;
  version: string;
  models: ModelName[];
  skipped_models: ModelName[];
  warnings: LocalisedText[];
  venues: ForecastManifestVenue[];
  age_hours: number;
}

function readForecastManifest(now: Date): ForecastManifest {
  requireDirectory(FORECAST_DIR, 'Ennustehakemisto data/forecasts/latest');
  const path = resolve(FORECAST_DIR, 'manifest.json');
  const raw = assertKeys(
    readJson(path, 'Ennustemanifesti'),
    FORECAST_MANIFEST_KEYS,
    'data/forecasts/latest/manifest.json',
  );
  const models = raw.models as ModelName[];
  if (!Array.isArray(models) || models.length === 0) {
    throw new BuildDataError('Ennustemanifestissa ei ole yhtaan mallia. Aja "make forecast".');
  }
  const venues = raw.venues as ForecastManifestVenue[];
  if (!Array.isArray(venues) || venues.length === 0) {
    throw new BuildDataError('Ennustemanifestissa ei ole yhtaan venueta. Aja "make forecast".');
  }
  return {
    generated_at: String(raw.generated_at),
    version: String(raw.version),
    models,
    skipped_models: Array.isArray(raw.skipped_models) ? (raw.skipped_models as ModelName[]) : [],
    warnings: localisedList(raw.warnings),
    venues,
    age_hours: round1(manifestAgeHours(String(raw.generated_at), now)),
  };
}

// --- Syotteiden luku -------------------------------------------------------

function processed(file: keyof typeof PROCESSED_SCHEMA) {
  return readTable(resolve(PROCESSED_DIR, file), PROCESSED_SCHEMA[file]);
}

function forecastTable(venueId: number, file: keyof typeof FORECAST_SCHEMA) {
  return readTable(resolve(FORECAST_DIR, `venue_${venueId}`, file), FORECAST_SCHEMA[file]);
}

/**
 * Jattaa kentan kokonaan pois kun arvo puuttuu. Poissa oleva avain on JSONissa
 * huomattavasti halvempi kuin `null`, ja tyypeissa kentat ovat siksi valinnaisia.
 */
function omitNull<K extends string>(key: K, value: number | null): Record<K, number> | Record<string, never> {
  return value === null ? {} : ({ [key]: value } as Record<K, number>);
}

/**
 * Ryhmittelee rivit mallin mukaan ja pudottaa `model`-kentan riveilta. Sama nimi
 * toistettuna sadoilla riveilla on turhaa painoa, ja kayttoliittyman mallivalitsin
 * osoittaa suoraan avaimeen.
 */
function splitByModel<T extends { model: ModelName }>(rows: T[]): Record<ModelName, Omit<T, 'model'>[]> {
  const out: Record<ModelName, Omit<T, 'model'>[]> = {};
  for (const { model, ...rest } of rows) {
    const bucket = out[model];
    if (bucket) bucket.push(rest);
    else out[model] = [rest];
  }
  return out;
}

function groupBy<T>(rows: T[], key: (row: T) => string): Map<string, T[]> {
  const map = new Map<string, T[]>();
  for (const row of rows) {
    const k = key(row);
    const bucket = map.get(k);
    if (bucket) bucket.push(row);
    else map.set(k, [row]);
  }
  return map;
}

function indexBy(rows: Row[], key: (row: Row) => string): Map<string, Row> {
  const map = new Map<string, Row>();
  for (const row of rows) map.set(key(row), row);
  return map;
}

// --- Rakennus --------------------------------------------------------------

function main(): void {
  const now = process.env.OVF_NOW ? new Date(process.env.OVF_NOW) : new Date();
  if (Number.isNaN(now.getTime())) {
    throw new BuildDataError(`OVF_NOW-ymparistomuuttujaa "${process.env.OVF_NOW}" ei voi lukea aikaleimana.`);
  }

  const venues = readVenues();
  const ingest = readIngestManifest(now);
  const forecastManifest = readForecastManifest(now);

  const visitorsDaily = processed('visitors_daily.csv');
  const visitorsHourly = processed('visitors_hourly.csv');
  const weatherDaily = processed('weather_daily.csv');
  const weatherHourly = processed('weather_hourly.csv');
  const tickets = processed('tickets_daily.csv');
  const calendar = processed('calendar_daily.csv');
  const traffic = processed('traffic_hourly.csv');

  const calendarByDate = indexBy(calendar.rows, (row) => str(row, 'date'));
  const weatherDailyByKey = indexBy(weatherDaily.rows, (row) => `${str(row, 'venue_id')}|${str(row, 'date')}`);
  const ticketsByKey = indexBy(tickets.rows, (row) => `${str(row, 'venue_id')}|${str(row, 'date')}`);
  const weatherHourlyByKey = indexBy(weatherHourly.rows, (row) => `${str(row, 'venue_id')}|${str(row, 'ts_utc')}`);

  const visitorsDailyByVenue = groupBy(visitorsDaily.rows, (row) => str(row, 'venue_id'));
  const visitorsHourlyByVenue = groupBy(visitorsHourly.rows, (row) => str(row, 'venue_id'));

  const daily: DailyData = {
    weather_groups: WEATHER_GROUP_ORDER,
    venues: {},
    traffic: buildTrafficDaily(traffic.rows),
  };
  const hourly: HourlyData = { days: HOURLY_DAYS, first_day: '', last_day: '', venues: {} };
  const profile: ProfileData = { venues: {} };
  const forecast: ForecastData = {
    generated_at: forecastManifest.generated_at,
    models: forecastManifest.models,
    default_model: forecastManifest.models.includes(PRODUCTION_MODEL)
      ? PRODUCTION_MODEL
      : forecastManifest.models[0]!,
    venues: {},
  };
  const quality: QualityData = { venues: {} };
  const summaries: VenueSummary[] = [];

  let hourlyFirst = '';
  let hourlyLast = '';

  for (const venue of venues) {
    const key = String(venue.venue_id);
    const dailyRows = visitorsDailyByVenue.get(key);
    if (!dailyRows || dailyRows.length === 0) {
      throw new BuildDataError(
        `Venuelle ${venue.venue_id} (${venue.name}) ei loydy yhtaan riviä tiedostosta visitors_daily.csv.`,
      );
    }

    // Sensorin kayttoonottoa edeltavat nollat eivat ole tyhjia paivia. Ne merkitaan
    // erikseen, jotta keskiarvot ja profiilit eivat vaany niiden takia.
    const sortedDaily = [...dailyRows].sort((a, b) => str(a, 'date').localeCompare(str(b, 'date')));
    const firstReporting = sortedDaily.find((row) => int(row, 'visitors_total') > 0);
    if (!firstReporting) {
      throw new BuildDataError(`Venue ${venue.venue_id} ei raportoi yhtaan nollasta poikkeavaa paivaa.`);
    }
    const firstDay = str(firstReporting, 'date');
    const lastDay = str(sortedDaily[sortedDaily.length - 1]!, 'date');

    const venueDaily: DailyRow[] = sortedDaily.map((row) => {
      const date = str(row, 'date');
      const calendarRow = calendarByDate.get(date);
      const weatherRow = weatherDailyByKey.get(`${key}|${date}`);
      const ticketRow = ticketsByKey.get(`${key}|${date}`);
      const holidayName = calendarRow ? optionalStr(calendarRow, 'holiday_name') : null;
      const group = weatherRow ? weatherGroup(optionalNum(weatherRow, 'weathercode_mode')) : null;
      return {
        date,
        visitors_in: int(row, 'visitors_in'),
        visitors_out: int(row, 'visitors_out'),
        visitors_total: int(row, 'visitors_total'),
        is_complete: bool(row, 'is_complete'),
        is_reporting: date >= firstDay,
        is_holiday: calendarRow ? bool(calendarRow, 'is_holiday') : false,
        ...(holidayName ? { holiday_name: holidayName } : {}),
        ...omitNull('temp_mean', weatherRow ? round1OrNull(optionalNum(weatherRow, 'temp_mean')) : null),
        ...omitNull('temp_max', weatherRow ? round1OrNull(optionalNum(weatherRow, 'temp_max')) : null),
        ...omitNull('precip_sum', weatherRow ? round1OrNull(optionalNum(weatherRow, 'precip_sum')) : null),
        ...(group ? { weather_group: group } : {}),
        ...omitNull('tickets_sold', ticketRow ? int(ticketRow, 'tickets_sold') : null),
        ...omitNull('groups_sold', ticketRow ? int(ticketRow, 'groups_sold') : null),
        ...omitNull('tickets_total', ticketRow ? int(ticketRow, 'tickets_total') : null),
      };
    });
    daily.venues[key] = toDailyColumns(venueDaily);

    // --- Tuntisarja ---------------------------------------------------------
    const hourlyRows = (visitorsHourlyByVenue.get(key) ?? []).sort((a, b) =>
      str(a, 'ts_utc').localeCompare(str(b, 'ts_utc')),
    );
    if (hourlyRows.length === 0) {
      throw new BuildDataError(`Venuelle ${venue.venue_id} ei loydy tuntirivejä tiedostosta visitors_hourly.csv.`);
    }
    const fullSeries = toHourlySeries(hourlyRows, key, weatherHourlyByKey);
    const cutoff = addDays(lastDay, -(HOURLY_DAYS - 1));
    const windowStart = fullSeries.ts.findIndex((ts) => localDate(ts) >= cutoff);
    hourly.venues[key] = sliceSeries(fullSeries, windowStart < 0 ? 0 : windowStart);
    const windowTs = hourly.venues[key]!.ts;
    if (windowTs.length > 0) {
      const first = localDate(windowTs[0]!);
      const last = localDate(windowTs[windowTs.length - 1]!);
      hourlyFirst = hourlyFirst === '' || first < hourlyFirst ? first : hourlyFirst;
      hourlyLast = hourlyLast === '' || last > hourlyLast ? last : hourlyLast;
    }

    // --- Viikonpaiva x tunti -profiili --------------------------------------
    // Profiili lasketaan koko raportoivasta historiasta, ei vain tuntisarjan ikkunasta.
    const reportingStart = fullSeries.ts.findIndex((ts) => localDate(ts) >= firstDay);
    const reportingSeries = sliceSeries(fullSeries, reportingStart < 0 ? 0 : reportingStart);
    const cells = buildProfileCells(reportingSeries);
    const means = cells.map((cell) => cell.mean).filter((value): value is number => value !== null);
    profile.venues[key] = {
      cells,
      open_hours: deriveOpenHours(cells),
      max_mean: means.length === 0 ? 0 : Math.max(...means),
      days: new Set(reportingSeries.ts.map(localDate)).size,
      first_day: firstDay,
      last_day: lastDay,
    };

    // --- Ennuste ------------------------------------------------------------
    const venueForecast = buildVenueForecast(venue.venue_id);
    forecast.venues[key] = venueForecast;

    // --- Laatu --------------------------------------------------------------
    const venueQuality = buildVenueQuality(venue.venue_id);
    quality.venues[key] = venueQuality;
    venueForecast.mae = Object.fromEntries(
      Object.entries(venueQuality.metrics).map(([model, buckets]) => [
        model,
        Object.fromEntries(Object.entries(buckets).map(([bucket, m]) => [bucket, round1(m.mae)])),
      ]),
    );

    // --- Yhteenveto ---------------------------------------------------------
    const reporting = venueDaily.filter((row) => row.is_reporting);
    const totals = reporting.map((row) => row.visitors_total);
    const maxDaily = totals.length === 0 ? 0 : Math.max(...totals);
    const maxDailyRow = reporting.find((row) => row.visitors_total === maxDaily);
    const last30 = summarisePeriod(venueDaily, lastDay, 30);
    const prev30 = summarisePeriod(venueDaily, addDays(lastDay, -30), 30);
    const manifestVenue = forecastManifest.venues.find((entry) => entry.venue_id === venue.venue_id);

    summaries.push({
      venue_id: venue.venue_id,
      name: venue.name,
      city: venue.city,
      capacity: venue.capacity,
      first_day: firstDay,
      last_day: lastDay,
      observed_days: venueDaily.length,
      reporting_days: reporting.length,
      visitors_total: sum(totals),
      visitors_in: sum(reporting.map((row) => row.visitors_in)),
      visitors_out: sum(reporting.map((row) => row.visitors_out)),
      mean_daily: round1(mean(totals)),
      median_daily: round1(median(totals)),
      max_daily: maxDaily,
      max_daily_date: maxDailyRow?.date ?? lastDay,
      max_hourly: Math.max(0, ...reportingSeries.visitors_total),
      open_hours: profile.venues[key]!.open_hours,
      last30,
      prev30,
      change_pct: changePct(last30, prev30),
      tickets_total: sum(
        venueDaily
          .map((row) => row.tickets_total)
          .filter((value): value is number => typeof value === 'number'),
      ),
      next7: sumForecast(venueForecast.daily[forecast.default_model] ?? [], 7),
      origin_date: venueForecast.origin_date,
      warnings: localisedList(manifestVenue?.warnings),
    });
  }

  hourly.first_day = hourlyFirst;
  hourly.last_day = hourlyLast;

  const meta: Meta = {
    built_at: now.toISOString().replace(/\.\d{3}Z$/, 'Z'),
    production_model: forecast.default_model,
    venues: summaries,
    ingest: {
      generated_at: ingest.generated_at,
      age_hours: ingest.age_hours,
      version: ingest.version,
      sources: ingest.sources,
      coverage: ingest.coverage,
      quality_gates: ingest.quality_gates,
      degraded: ingest.sources.filter((source) => source.status !== 'ok'),
    },
    forecast: {
      generated_at: forecastManifest.generated_at,
      age_hours: forecastManifest.age_hours,
      version: forecastManifest.version,
      models: forecastManifest.models,
      skipped_models: forecastManifest.skipped_models,
      warnings: forecastManifest.warnings,
      origin_date: forecastManifest.venues
        .map((entry) => entry.origin_date)
        .sort()
        .at(-1)!,
      horizon_days: Math.max(...forecastManifest.venues.map((entry) => entry.horizon_days ?? 30)),
      hourly_days: Math.max(...forecastManifest.venues.map((entry) => entry.hourly_days ?? 7)),
    },
    traffic: buildTrafficSummary(traffic.rows),
  };

  // Pyhapaivat paivamaaran mukaan: arviointisivu merkitsee ne aikasarjaan ja
  // pahiten menneiden paivien taulukkoon.
  const holidayNames: Record<string, string> = {};
  for (const row of calendar.rows) {
    if (!bool(row, 'is_holiday')) continue;
    holidayNames[str(row, 'date')] = optionalStr(row, 'holiday_name') ?? 'Pyhäpäivä';
  }
  const accuracy = buildAccuracy(holidayNames);

  mkdirSync(OUT_DIR, { recursive: true });
  const written = [
    write('meta.json', meta),
    write('daily.json', daily),
    write('hourly.json', hourly),
    write('profile.json', profile),
    write('forecast.json', forecast),
    write('quality.json', quality),
    write('accuracy.json', accuracy),
  ];

  const total = written.reduce((acc, entry) => acc + entry.bytes, 0);
  const evaluations =
    accuracy.runs.length === 0 ? 'ei arviointiajoja' : `${accuracy.runs.length} arviointiajoa`;
  process.stdout.write(
    `build-data: ${venues.length} venueta, ingest ${ingest.age_hours} h vanha, ${evaluations}\n`,
  );
  for (const entry of written) {
    process.stdout.write(`  ${entry.file.padEnd(14)} ${(entry.bytes / 1024).toFixed(1).padStart(7)} kB\n`);
  }
  process.stdout.write(`  ${'yhteensa'.padEnd(14)} ${(total / 1024).toFixed(1).padStart(7)} kB\n`);
}

// --- Osabuilderit ----------------------------------------------------------

function toHourlySeries(rows: Row[], venueKey: string, weatherByKey: Map<string, Row>): HourlySeries {
  const series: HourlySeries = {
    ts: [],
    visitors_in: [],
    visitors_total: [],
    imputed_idx: [],
    rain_idx: [],
  };
  rows.forEach((row, index) => {
    series.ts.push(shortenLocalTs(str(row, 'ts_local')));
    series.visitors_in.push(int(row, 'visitors_in'));
    series.visitors_total.push(int(row, 'visitors_total'));
    if (bool(row, 'is_imputed')) series.imputed_idx.push(index);
    const weather = weatherByKey.get(`${venueKey}|${str(row, 'ts_utc')}`);
    const precipitation = weather ? optionalNum(weather, 'precipitation') : null;
    if (precipitation !== null && precipitation >= RAINY_HOUR_MM) series.rain_idx.push(index);
  });
  return series;
}

function sliceSeries(series: HourlySeries, start: number): HourlySeries {
  return {
    ts: series.ts.slice(start),
    visitors_in: series.visitors_in.slice(start),
    visitors_total: series.visitors_total.slice(start),
    imputed_idx: series.imputed_idx.filter((index) => index >= start).map((index) => index - start),
    rain_idx: series.rain_idx.filter((index) => index >= start).map((index) => index - start),
  };
}

/**
 * Liikennelaskurin tuoreimmilla tunneilla lukemat voivat olla viela tyhjia. Ne ovat
 * puuttuvia havaintoja, eivat nollia, joten ne jatetaan pois kokonaan sen sijaan etta
 * ne vetaisivat vuorokauden summan alas.
 */
function trafficCounts(row: Row): { pedestrians: number; cyclists: number } | null {
  const values = ['jk_in', 'jk_out', 'pp_in', 'pp_out'].map((column) => optionalNum(row, column));
  if (values.every((value) => value === null)) return null;
  const [jkIn, jkOut, ppIn, ppOut] = values;
  return {
    pedestrians: Math.round((jkIn ?? 0) + (jkOut ?? 0)),
    cyclists: Math.round((ppIn ?? 0) + (ppOut ?? 0)),
  };
}

/**
 * Rivimuoto sarakemuotoon. Tama on ainoa paikka jossa muunnos tehdaan; sivut lukevat
 * sarakkeet takaisin riveiksi apurilla `toDailyRows()`.
 */
function toDailyColumns(rows: DailyRow[]): DailyColumns {
  const columns: DailyColumns = {
    date: [],
    visitors_in: [],
    visitors_out: [],
    visitors_total: [],
    temp_mean: [],
    temp_max: [],
    precip_sum: [],
    weather_group: [],
    tickets_sold: [],
    groups_sold: [],
    tickets_total: [],
    incomplete_idx: [],
    not_reporting_idx: [],
    holidays: {},
  };
  rows.forEach((row, index) => {
    columns.date.push(row.date);
    columns.visitors_in.push(row.visitors_in);
    columns.visitors_out.push(row.visitors_out);
    columns.visitors_total.push(row.visitors_total);
    columns.temp_mean.push(row.temp_mean ?? null);
    columns.temp_max.push(row.temp_max ?? null);
    columns.precip_sum.push(row.precip_sum ?? null);
    columns.weather_group.push(row.weather_group ? WEATHER_GROUP_ORDER.indexOf(row.weather_group) : -1);
    columns.tickets_sold.push(row.tickets_sold ?? null);
    columns.groups_sold.push(row.groups_sold ?? null);
    columns.tickets_total.push(row.tickets_total ?? null);
    if (!row.is_complete) columns.incomplete_idx.push(index);
    if (!row.is_reporting) columns.not_reporting_idx.push(index);
    if (row.is_holiday) columns.holidays[row.date] = row.holiday_name ?? 'Pyhäpäivä';
  });
  return columns;
}

function toBacktestColumns(rows: BacktestRow[]): BacktestColumns {
  const origins: string[] = [];
  const originIndex = new Map<string, number>();
  const columns: BacktestColumns = {
    origins,
    origin: [],
    horizon_days: [],
    y_true: [],
    y_pred: [],
    p10: [],
    p90: [],
  };
  for (const row of rows) {
    let index = originIndex.get(row.origin_date);
    if (index === undefined) {
      index = origins.length;
      origins.push(row.origin_date);
      originIndex.set(row.origin_date, index);
    }
    columns.origin.push(index);
    columns.horizon_days.push(row.horizon_days);
    columns.y_true.push(row.y_true);
    columns.y_pred.push(row.y_pred);
    columns.p10.push(row.p10);
    columns.p90.push(row.p90);
  }
  return columns;
}

function buildTrafficDaily(rows: Row[]): TrafficDailyRow[] {
  const byDate = new Map<string, TrafficDailyRow>();
  for (const row of rows) {
    const counts = trafficCounts(row);
    if (counts === null) continue;
    const date = localDate(str(row, 'ts_local'));
    const entry = byDate.get(date) ?? { date, pedestrians: 0, cyclists: 0 };
    entry.pedestrians += counts.pedestrians;
    entry.cyclists += counts.cyclists;
    byDate.set(date, entry);
  }
  return [...byDate.values()].sort((a, b) => a.date.localeCompare(b.date));
}

function buildTrafficSummary(rows: Row[]): Meta['traffic'] {
  const measured = rows.filter((row) => trafficCounts(row) !== null);
  if (measured.length === 0) return null;
  const dates = measured.map((row) => localDate(str(row, 'ts_local'))).sort();
  const counts = measured.map((row) => trafficCounts(row)!);
  return {
    site_id: str(measured[0]!, 'site_id'),
    site_name: str(measured[0]!, 'site_name'),
    first_day: dates[0]!,
    last_day: dates[dates.length - 1]!,
    hours: measured.length,
    pedestrians: sum(counts.map((entry) => entry.pedestrians)),
    cyclists: sum(counts.map((entry) => entry.cyclists)),
  };
}

function buildVenueForecast(venueId: number): VenueForecast {
  const dailyTable = forecastTable(venueId, 'daily_30d.csv');
  const hourlyTable = forecastTable(venueId, 'hourly_7d.csv');

  const dailyRows: (ForecastDailyRow & { model: ModelName })[] = dailyTable.rows.map((row) => {
    const holidayName = optionalStr(row, 'holiday_name');
    const group = weatherGroupFromLabel(optionalStr(row, 'weathercode_str'));
    return {
      model: str(row, 'model'),
      date: str(row, 'date'),
      horizon_days: int(row, 'horizon_days'),
      p10: roundCount(num(row, 'p10')),
      p50: roundCount(num(row, 'p50')),
      p90: roundCount(num(row, 'p90')),
      weather_source: str(row, 'weather_source') as WeatherSource,
      ...omitNull('temp_mean', round1OrNull(optionalNum(row, 'temp_mean'))),
      ...omitNull('precip_sum', round1OrNull(optionalNum(row, 'precip_sum'))),
      ...(group ? { weather_group: group } : {}),
      is_holiday: bool(row, 'is_holiday'),
      ...(holidayName ? { holiday_name: holidayName } : {}),
    };
  });
  dailyRows.sort((a, b) => a.horizon_days - b.horizon_days || a.model.localeCompare(b.model));

  const hourlyRows: (ForecastHourlyRow & { model: ModelName })[] = hourlyTable.rows.map((row) => ({
    model: str(row, 'model'),
    ts: shortenLocalTs(str(row, 'ts_local')),
    p10: roundCount(num(row, 'p10')),
    p50: roundCount(num(row, 'p50')),
    p90: roundCount(num(row, 'p90')),
    weather_source: str(row, 'weather_source') as WeatherSource,
  }));
  hourlyRows.sort((a, b) => a.ts.localeCompare(b.ts) || a.model.localeCompare(b.model));

  if (dailyRows.length === 0 || hourlyRows.length === 0) {
    throw new BuildDataError(`Venuen ${venueId} ennustetiedostot ovat tyhjia.`);
  }

  const dates = dailyRows.map((row) => row.date).sort();
  return {
    venue_id: venueId,
    origin_date: addDays(dates[0]!, -1),
    first_day: dates[0]!,
    last_day: dates[dates.length - 1]!,
    forecast_weather_days: forecastWeatherDays(dailyRows),
    daily: splitByModel(dailyRows),
    hourly: splitByModel(hourlyRows),
    mae: {},
  };
}

function buildVenueQuality(venueId: number): VenueQuality {
  const path = resolve(FORECAST_DIR, `venue_${venueId}`, 'metrics.json');
  const metrics = assertKeys(
    readJson(path, `Venuen ${venueId} metrics.json`),
    METRICS_KEYS,
    `data/forecasts/latest/venue_${venueId}/metrics.json`,
  );

  const table = forecastTable(venueId, 'backtest.csv');
  const allRows: (BacktestRow & { model: ModelName })[] = table.rows.map((row) => ({
    model: str(row, 'model'),
    origin_date: str(row, 'origin_date'),
    horizon_days: int(row, 'horizon_days'),
    y_true: roundCount(num(row, 'y_true')),
    y_pred: roundCount(num(row, 'y_pred')),
    p10: roundCount(num(row, 'p10')),
    p90: roundCount(num(row, 'p90')),
  }));

  const byModel = groupBy(allRows, (row) => row.model);
  const maeCurves: Record<ModelName, HorizonPoint[]> = {};
  for (const [model, rows] of byModel) maeCurves[model] = maeByHorizon(rows);

  const q = metrics as unknown as VenueQuality;
  return {
    venue_id: Number(metrics.venue_id),
    venue_name: String(metrics.venue_name),
    origin_date: String(metrics.origin_date),
    n_training_days: Number(metrics.n_training_days),
    training_window: metrics.training_window as [string, string],
    n_origins: Number(metrics.n_origins),
    backtest_window: metrics.backtest_window as [string, string],
    horizon_buckets: metrics.horizon_buckets as string[],
    models: metrics.models as string[],
    benchmarks: metrics.benchmarks as string[],
    coverage_method: String(metrics.coverage_method),
    hourly_profile: q.hourly_profile,
    metrics: q.metrics,
    benchmark_comparison: q.benchmark_comparison,
    interval_bands: q.interval_bands,
    do_not_trust: localisedList(metrics.do_not_trust),
    warnings: localisedList(metrics.warnings),
    backtest: Object.fromEntries(
      Object.entries(splitByModel(allRows.filter((row) => BACKTEST_ROW_MODELS.has(row.model)))).map(
        ([model, rows]) => [model, toBacktestColumns(rows)],
      ),
    ),
    mae_by_horizon: maeCurves,
  };
}


// --- Arviointiajot ---------------------------------------------------------

/** Yhden ajon luetut tiedostot ennen muunnosta. */
interface RawEvaluationRun {
  entry: Record<string, unknown>;
  verdicts: Record<string, unknown>;
  /** Ajon paasaan tilan rivit venuen mukaan. Kooste ei kirjoita omia rivejaan. */
  predictions: Map<string, PredictionRow[]>;
  /** MASE-nimittaja venuelta. Ei ole `predictions.csv`-tiedostossa. */
  maseDenominator: Map<string, number>;
  ref: RunRef;
}

function evaluationPath(runId: string, file: string): string {
  return resolve(EVALUATIONS_DIR, runId, file);
}

function relativeEvaluationPath(runId: string, file: string): string {
  return `data/evaluations/${runId}/${file}`;
}

/**
 * Lukee ajon `predictions.csv`-tiedoston ja rajaa sen ajon paasaan tilaan.
 *
 * Muut kaksi tilaa ovat ylaraja ja alaraja, eivat tulos, ja niiden ottaminen mukaan
 * kolminkertaistaisi paketin koon. Sään kolme tilaa nakyvat sivulla `verdicts.json`:in
 * `weather_sensitivity`-kentasta.
 */
function readPredictions(runId: string, weatherMode: string): Map<string, PredictionRow[]> {
  const path = evaluationPath(runId, 'predictions.csv');
  const byVenue = new Map<string, PredictionRow[]>();
  if (!existsSync(path)) return byVenue;

  const table = readTable(path, PREDICTIONS_SCHEMA);
  for (const row of table.rows) {
    if (str(row, 'weather_mode') !== weatherMode) continue;
    const key = str(row, 'venue_id');
    const parsed: PredictionRow = {
      venue_id: int(row, 'venue_id'),
      date: str(row, 'date'),
      horizon_days: int(row, 'horizon_days'),
      model: str(row, 'model'),
      weather_mode: str(row, 'weather_mode'),
      y_true: num(row, 'y_true'),
      p10: num(row, 'p10'),
      p50: num(row, 'p50'),
      p90: num(row, 'p90'),
    };
    const bucket = byVenue.get(key);
    if (bucket) bucket.push(parsed);
    else byVenue.set(key, [parsed]);
  }
  for (const rows of byVenue.values()) {
    rows.sort((a, b) => a.date.localeCompare(b.date) || a.model.localeCompare(b.model));
  }
  return byVenue;
}

/**
 * MASE-nimittaja venueittain. `metrics.json` on ainoa paikka jossa koulutusdatan
 * seasonal naive -MAE on; ilman sita MASE jaa taulukossa tyhjaksi.
 */
function readMaseDenominators(runId: string): Map<string, number> {
  const path = evaluationPath(runId, 'metrics.json');
  const out = new Map<string, number>();
  if (!existsSync(path)) return out;
  const metrics = assertEvaluationVersion(
    readJson(path, `Ajon ${runId} metrics.json`),
    runId,
    relativeEvaluationPath(runId, 'metrics.json'),
  );
  const venues = Array.isArray(metrics['venues']) ? (metrics['venues'] as Record<string, unknown>[]) : [];
  for (const venue of venues) {
    const diagnostics = venue['diagnostics'] as Record<string, unknown> | undefined;
    const value = diagnostics?.['mase_denominator'];
    if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
      out.set(String(venue['venue_id']), value);
    }
  }
  return out;
}

function asRecord(value: unknown, what: string): Record<string, unknown> {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) {
    throw new BuildDataError(`${what} ei ole JSON-objekti.`);
  }
  return value as Record<string, unknown>;
}

function asArray(value: unknown, what: string): Record<string, unknown>[] {
  if (!Array.isArray(value)) throw new BuildDataError(`${what} ei ole taulukko.`);
  return value.map((entry, index) => asRecord(entry, `${what}[${index}]`));
}

function numberAt(record: Record<string, unknown>, key: string): number {
  const value = record[key];
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new BuildDataError(`Arviointidatan kentta ${key} ei ole luku: ${JSON.stringify(value)}`);
  }
  return value;
}

function verdictAt(record: Record<string, unknown>, key: string): Verdict {
  const value = String(record[key]);
  if (value !== 'better' && value !== 'no_difference' && value !== 'worse') {
    throw new BuildDataError(`Tuntematon verdikti "${value}". Odotettu better, no_difference tai worse.`);
  }
  return value;
}

function toWindow(record: Record<string, unknown>): AccuracyWindow {
  return {
    origin: String(record['origin']),
    test_start: String(record['test_start']),
    test_end: String(record['test_end']),
    horizon_days: numberAt(record, 'horizon_days'),
    train_window: String(record['train_window']),
  };
}

function toComparison(record: Record<string, unknown>, runId: string): AccuracyComparison {
  assertKeys(record, VERDICT_COMPARISON_KEYS, relativeEvaluationPath(runId, 'verdicts.json'));
  return {
    reference: String(record['reference']),
    n: numberAt(record, 'n'),
    mean_difference: count1(numberAt(record, 'mean_difference')),
    ci_low: count1(numberAt(record, 'ci_low')),
    ci_high: count1(numberAt(record, 'ci_high')),
    verdict: verdictAt(record, 'verdict'),
    model_mae: count1(numberAt(record, 'model_mae')),
    reference_mae: count1(numberAt(record, 'reference_mae')),
    skill_score: share3(numberAt(record, 'skill_score')),
    skill_ci_low: share3(numberAt(record, 'skill_ci_low')),
    skill_ci_high: share3(numberAt(record, 'skill_ci_high')),
    mde: count1(numberAt(record, 'mde')),
    mde_pct: count1(numberAt(record, 'mde_pct')),
    dm_statistic: share3(numberAt(record, 'dm_statistic')),
    dm_p_value: share3(numberAt(record, 'dm_p_value')),
    dm_lag: numberAt(record, 'dm_lag'),
  };
}

function toBias(record: Record<string, unknown>): AccuracyBias {
  return {
    mean_error: count1(numberAt(record, 'mean_error')),
    ci_low: count1(numberAt(record, 'ci_low')),
    ci_high: count1(numberAt(record, 'ci_high')),
    verdict: String(record['verdict']),
    mean_actual: count1(numberAt(record, 'mean_actual')),
    pct_of_actual: count1(numberAt(record, 'pct_of_actual')),
  };
}

function toCalibration(record: Record<string, unknown>): AccuracyCalibration {
  return {
    covered: numberAt(record, 'covered'),
    n: numberAt(record, 'n'),
    coverage: share3(numberAt(record, 'coverage')),
    ci_low: share3(numberAt(record, 'ci_low')),
    ci_high: share3(numberAt(record, 'ci_high')),
    target: share3(numberAt(record, 'target')),
    verdict: String(record['verdict']),
  };
}

function toTotal(record: Record<string, unknown>): AccuracyTotal {
  const label = record['label'];
  return {
    ...(typeof label === 'string' ? { label } : {}),
    predicted: count1(numberAt(record, 'predicted')),
    actual: count1(numberAt(record, 'actual')),
    difference: count1(numberAt(record, 'difference')),
    difference_pct: count1(numberAt(record, 'difference_pct')),
    p10: count1(numberAt(record, 'p10')),
    p90: count1(numberAt(record, 'p90')),
    covers_actual: record['covers_actual'] === true,
    summed_daily_p10: count1(numberAt(record, 'summed_daily_p10')),
    summed_daily_p90: count1(numberAt(record, 'summed_daily_p90')),
    n_ratio_samples: numberAt(record, 'n_ratio_samples'),
    is_thin: record['is_thin'] === true,
    median_ratio: share3(numberAt(record, 'median_ratio')),
    is_drifted: record['is_drifted'] === true,
  };
}

function toWeatherSensitivity(record: Record<string, unknown>): AccuracyWeatherSensitivity {
  return {
    perfect: count1(numberAt(record, 'perfect')),
    operational: count1(numberAt(record, 'operational')),
    climatology: count1(numberAt(record, 'climatology')),
    gap: count1(numberAt(record, 'gap')),
    gap_pct: count1(numberAt(record, 'gap_pct')),
  };
}

function toPooled(record: Record<string, unknown>, runId: string): AccuracyPooled {
  assertKeys(record, VERDICT_POOLED_KEYS, relativeEvaluationPath(runId, 'verdicts.json'));
  return {
    reference: String(record['reference']),
    n_windows: numberAt(record, 'n_windows'),
    n_days: numberAt(record, 'n_days'),
    mean_difference: count1(numberAt(record, 'mean_difference')),
    ci_low: count1(numberAt(record, 'ci_low')),
    ci_high: count1(numberAt(record, 'ci_high')),
    verdict: verdictAt(record, 'verdict'),
    windows_favouring: numberAt(record, 'windows_favouring'),
    windows_opposing: numberAt(record, 'windows_opposing'),
    windows_neutral: numberAt(record, 'windows_neutral'),
    mde: count1(numberAt(record, 'mde')),
    mde_pct: count1(numberAt(record, 'mde_pct')),
    reference_mae: count1(numberAt(record, 'reference_mae')),
  };
}

function toPerWindow(record: Record<string, unknown>, windows: AccuracyWindowRef[]): AccuracyPerWindow {
  const origin = String(record['origin']);
  const match = windows.find((window) => window.origin === origin);
  return {
    label: String(record['label']),
    origin,
    ...(match ? { run_id: match.run_id } : {}),
    reference: String(record['reference']),
    model_mae: count1(numberAt(record, 'model_mae')),
    reference_mae: count1(numberAt(record, 'reference_mae')),
    mean_difference: count1(numberAt(record, 'mean_difference')),
    ci_low: count1(numberAt(record, 'ci_low')),
    ci_high: count1(numberAt(record, 'ci_high')),
    verdict: verdictAt(record, 'verdict'),
    mde: count1(numberAt(record, 'mde')),
    mde_pct: count1(numberAt(record, 'mde_pct')),
    raw_p_value: share3(numberAt(record, 'raw_p_value')),
    holm_p_value: share3(numberAt(record, 'holm_p_value')),
  };
}


/**
 * Paketoi `data/evaluations/` sivuston luettavaksi.
 *
 * Arviointi on valinnainen tyovaihe, toisin kuin ingest ja forecast: puuttuva tai tyhja
 * hakemisto tuottaa tyhjan `runs`-listan eika kaada buildia. Skeeman versio sen sijaan
 * tarkistetaan, koska tuntemattoman version hiljainen renderointi olisi pahempi kuin
 * epaonnistunut build.
 */
function buildAccuracy(holidays: Record<string, string>): AccuracyData {
  const empty: AccuracyData = { runs: [], default_run: null, horizon_buckets: [...HORIZON_BUCKETS] };
  const indexPath = resolve(EVALUATIONS_DIR, 'index.json');
  if (!existsSync(EVALUATIONS_DIR) || !existsSync(indexPath)) return empty;

  const index = assertEvaluationVersion(
    readJson(indexPath, 'Arviointien rekisteri'),
    '(rekisteri)',
    'data/evaluations/index.json',
  );
  assertKeys(index, EVALUATION_INDEX_KEYS, 'data/evaluations/index.json');
  const entries = asArray(index['runs'], 'data/evaluations/index.json runs');
  if (entries.length === 0) return empty;

  // Ensimmainen kierros lukee tiedostot, toinen rakentaa. Kooste piirretaan
  // jasenajojensa riveista, joten ne on oltava luettuina ennen koosteen rakentamista.
  const raw = new Map<string, RawEvaluationRun>();
  for (const entry of entries) {
    assertKeys(entry, EVALUATION_RUN_KEYS, 'data/evaluations/index.json');
    const runId = String(entry['run_id']);
    const verdictsFile = relativeEvaluationPath(runId, 'verdicts.json');
    const verdicts = assertEvaluationVersion(
      readJson(evaluationPath(runId, 'verdicts.json'), `Ajon ${runId} verdicts.json`),
      runId,
      verdictsFile,
    );
    assertKeys(verdicts, VERDICTS_KEYS, verdictsFile);

    const kind = String(entry['kind']) === 'sweep' ? 'sweep' : 'window';
    const members = Array.isArray(entry['members']) ? (entry['members'] as unknown[]).map(String) : [];
    const window = entry['window'] === null ? null : toWindow(asRecord(entry['window'], 'window'));
    const lastDay = window ? window.test_end : String(verdicts['last_day'] ?? '');

    raw.set(runId, {
      entry,
      verdicts,
      predictions: readPredictions(runId, String(entry['primary_weather_mode'])),
      maseDenominator: readMaseDenominators(runId),
      ref: { run_id: runId, kind, created_at: String(entry['created_at']), members, last_day: lastDay },
    });
  }

  const keepSeries = selectSeriesRuns([...raw.values()].map((run) => run.ref));
  const runs = sortRuns([...raw.values()].map((run) => run.ref)).map((ref) =>
    buildAccuracyRun(raw.get(ref.run_id)!, raw, keepSeries.has(ref.run_id), holidays),
  );

  return { runs, default_run: runs[0]?.run_id ?? null, horizon_buckets: [...HORIZON_BUCKETS] };
}

function buildAccuracyRun(
  run: RawEvaluationRun,
  raw: Map<string, RawEvaluationRun>,
  keepSeries: boolean,
  holidays: Record<string, string>,
): AccuracyRun {
  const { entry, verdicts, ref } = run;
  const runId = ref.run_id;
  const isSweep = ref.kind === 'sweep';
  const mainModels = Array.isArray(entry['models']) ? (entry['models'] as unknown[]).map(String) : [];
  const window = entry['window'] === null ? undefined : toWindow(asRecord(entry['window'], 'window'));

  const windows: AccuracyWindowRef[] = Array.isArray(verdicts['windows'])
    ? asArray(verdicts['windows'], 'windows').map((record) => ({
        run_id: String(record['run_id']),
        ...toWindow(record),
      }))
    : [];

  // Koosteella ei ole omia ennusterivejaan: se lukee jasenikkunoidensa rivit. Sama
  // paiva voi esiintya kahdessa ikkunassa vain liukuvassa sweepissa, ja silloin
  // ensimmainen esiintyma voittaa, jotta aikajana pysyy yksikasitteisena.
  const predictionsByVenue = new Map<string, PredictionRow[]>();
  const memberIds = isSweep ? (windows.length > 0 ? windows.map((w) => w.run_id) : ref.members) : [runId];
  for (const memberId of memberIds) {
    const member = raw.get(memberId);
    if (!member) continue;
    for (const [venueKey, rows] of member.predictions) {
      const bucket = predictionsByVenue.get(venueKey) ?? [];
      bucket.push(...rows);
      predictionsByVenue.set(venueKey, bucket);
    }
  }
  for (const [venueKey, rows] of predictionsByVenue) {
    const seen = new Set<string>();
    const unique = rows.filter((row) => {
      const key = `${row.model}|${row.date}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    unique.sort((a, b) => a.date.localeCompare(b.date) || a.model.localeCompare(b.model));
    predictionsByVenue.set(venueKey, unique);
  }

  const venues = asArray(verdicts['venues'], `${runId} venues`).map((venue) =>
    buildAccuracyVenue(venue, {
      runId,
      isSweep,
      mainModels,
      windows,
      rows: predictionsByVenue.get(String(venue['venue_id'])) ?? [],
      maseDenominator: run.maseDenominator.get(String(venue['venue_id'])) ?? null,
      holidays,
    }),
  );

  const series: Record<string, ReturnType<typeof buildSeries>> = {};
  // Koosteen sarjaa ei tallenneta erikseen: se on jasentensa sarjojen jatko, ja
  // kahdentaminen kaksinkertaistaisi paketin painavimman osan.
  if (keepSeries && !isSweep) {
    for (const [venueKey, rows] of predictionsByVenue) {
      series[venueKey] = buildSeries(rows, mainModels, holidays);
    }
  }

  return {
    run_id: runId,
    kind: ref.kind,
    created_at: ref.created_at,
    models: mainModels,
    reference_rule: String(entry['reference_rule']),
    primary_weather_mode: String(entry['primary_weather_mode']) as WeatherMode,
    family_size: Number(verdicts['family_size'] ?? 0),
    summary_fi: String(verdicts['summary_fi'] ?? ''),
    summary_en: String(verdicts['summary_en'] ?? ''),
    first_day: window ? window.test_start : String(verdicts['first_day'] ?? ''),
    last_day: window ? window.test_end : String(verdicts['last_day'] ?? ''),
    ...(window ? { window } : {}),
    ...(isSweep ? { sweep: String(entry['sweep'] ?? '') } : {}),
    ...(windows.length > 0 ? { windows } : {}),
    members: isSweep ? memberIds : [],
    venues,
    ...(Object.keys(series).length > 0 ? { series } : {}),
  };
}

interface VenueContext {
  runId: string;
  isSweep: boolean;
  mainModels: string[];
  windows: AccuracyWindowRef[];
  rows: PredictionRow[];
  maseDenominator: number | null;
  holidays: Record<string, string>;
}

function buildAccuracyVenue(venue: Record<string, unknown>, context: VenueContext): AccuracyVenue {
  const { runId, isSweep, mainModels, windows, rows, holidays } = context;
  const file = relativeEvaluationPath(runId, 'verdicts.json');

  const models: AccuracyModel[] = asArray(venue['models'], `${runId} models`).map((model) => {
    const name = String(model['model']);
    if (isSweep) {
      assertKeys(model, VERDICT_SWEEP_MODEL_KEYS, file);
      return {
        model: name,
        pooled: toPooled(asRecord(model['pooled'], 'pooled'), runId),
        per_window: asArray(model['per_window'], 'per_window').map((record) =>
          toPerWindow(record, windows),
        ),
        totals: asArray(model['totals'], 'totals').map(toTotal),
      };
    }
    assertKeys(model, VERDICT_WINDOW_MODEL_KEYS, file);
    return {
      model: name,
      comparison: toComparison(asRecord(model['comparison'], 'comparison'), runId),
      bias: toBias(asRecord(model['bias'], 'bias')),
      calibration: toCalibration(asRecord(model['calibration'], 'calibration')),
      total: toTotal(asRecord(model['total'], 'total')),
      weather_sensitivity: toWeatherSensitivity(asRecord(model['weather_sensitivity'], 'weather_sensitivity')),
      raw_p_value: share3(numberAt(model, 'raw_p_value')),
      holm_p_value: share3(numberAt(model, 'holm_p_value')),
    };
  });

  if (!isSweep) assertKeys(venue, VERDICT_WINDOW_VENUE_KEYS, file);

  // Mallit ensin, sitten vertailukohdat kiinteassa jarjestyksessa. Sama jarjestys
  // taulukoissa ja kuvaajissa, jotta rivit vastaavat toisiaan sivulta toiselle.
  const present = new Set(rows.map((row) => row.model));
  const order = [
    ...mainModels.filter((model) => present.has(model)),
    ...EVALUATION_BASELINES.filter((model) => present.has(model)),
  ];
  const byModel = new Map<string, PredictionRow[]>();
  for (const row of rows) {
    const bucket = byModel.get(row.model);
    if (bucket) bucket.push(row);
    else byModel.set(row.model, [row]);
  }

  const baselineMae = venue['baseline_mae'];
  const primaryModel = order[0];

  return {
    venue_id: Number(venue['venue_id']),
    venue_name: String(venue['venue_name']),
    reference: String(venue['reference'] ?? models[0]?.pooled?.reference ?? ''),
    ...(typeof baselineMae === 'object' && baselineMae !== null
      ? {
          baseline_mae: Object.fromEntries(
            Object.entries(baselineMae as Record<string, number>).map(([model, value]) => [
              model,
              count1(Number(value)),
            ]),
          ),
        }
      : {}),
    models,
    // MASE tarvitsee koulutusdatan nimittajan, joka on ikkunakohtainen. Koosteessa
    // ikkunoita on monta eika yhta oikeaa nimittajaa ole, joten se jaa tyhjaksi.
    metrics: order.map((model) =>
      modelMetrics(model, byModel.get(model) ?? [], isSweep ? null : context.maseDenominator),
    ),
    horizon: horizonRows(rows, order),
    worst_days: primaryModel === undefined ? [] : worstDays(byModel.get(primaryModel) ?? [], holidays),
  };
}

// --- Kirjoitus -------------------------------------------------------------

function write(file: string, value: unknown): { file: string; bytes: number } {
  const json = JSON.stringify(value);
  writeFileSync(resolve(OUT_DIR, file), `${json}\n`, 'utf8');
  return { file, bytes: Buffer.byteLength(json, 'utf8') };
}

// --- Ajo -------------------------------------------------------------------

try {
  main();
} catch (error) {
  if (error instanceof BuildDataError) {
    process.stderr.write(`\nbuild-data epaonnistui.\n\n${error.message}\n\n`);
    process.exit(1);
  }
  throw error;
}
