/**
 * Datasopimus web-osion ja Python-osioiden valilla.
 *
 * Naita tyyppeja vasten `scripts/build-data.ts` validoi luetun datan ja niita vasten
 * sivut lukevat `src/data/*.json`. Jos `data/processed/`- tai `data/forecasts/`-tiedostojen
 * sarakkeet muuttuvat, build kaatuu `scripts/lib/schema.ts`-tarkistuksessa eika taalla.
 */

/** Viikonpaiva Pythonin `date.weekday()`-konventiolla: 0 = maanantai, 6 = sunnuntai. */
export type Dow = 0 | 1 | 2 | 3 | 4 | 5 | 6;

/** Saan lahde ennusteriveilla ja havaintoriveilla. */
export type WeatherSource = 'archive' | 'forecast' | 'climatology';

/** Karkea saatilaluokka, johdettu `weathercode_str`-sarakkeesta. */
export type WeatherGroup = 'clear' | 'cloudy' | 'rain' | 'snow' | 'other';

/** Mallien nimet sellaisina kuin osio 3 ne kirjoittaa. */
export type ModelName = string;

/** Horisonttikori backtest-mittareissa, esim. "1-7". */
export type HorizonBucket = string;

// ---------------------------------------------------------------------------
// meta.json
// ---------------------------------------------------------------------------

export interface SourceStatus {
  name: string;
  status: string;
  rows?: number;
  window?: [string, string];
  error?: string;
}

export interface CoverageEntry {
  first: string;
  last: string;
  missing_hours: number;
}

export interface IngestMeta {
  generated_at: string;
  age_hours: number;
  version: string;
  sources: SourceStatus[];
  coverage: Record<string, CoverageEntry>;
  quality_gates: { passed: boolean; warnings: string[] };
  /** Lahteet joiden status ei ole "ok". */
  degraded: SourceStatus[];
}

export interface ForecastMeta {
  generated_at: string;
  age_hours: number;
  version: string;
  models: ModelName[];
  skipped_models: ModelName[];
  warnings: string[];
  origin_date: string;
  horizon_days: number;
  hourly_days: number;
}

export interface VenueSummary {
  venue_id: number;
  name: string;
  city: string;
  capacity: number;
  /** Ensimmainen paiva jolla sensori raportoi nollasta poikkeavan luvun. */
  first_day: string;
  last_day: string;
  observed_days: number;
  /** Havaitut paivat joilla visitors_total > 0. */
  reporting_days: number;
  visitors_total: number;
  visitors_in: number;
  visitors_out: number;
  mean_daily: number;
  median_daily: number;
  max_daily: number;
  max_daily_date: string;
  max_hourly: number;
  /** Aukiolotunnit tuntiprofiilista johdettuna, paikallista aikaa. */
  open_hours: number[];
  last30: { days: number; visitors_total: number; mean_daily: number };
  prev30: { days: number; visitors_total: number; mean_daily: number };
  /** Muutos edellisiin 30 vrk verrattuna, prosenttia. null jos vertailujaksoa ei ole. */
  change_pct: number | null;
  tickets_total: number;
  /** Seuraavan 7 vrk summa tuotantomallilla, kvantiileittain. */
  next7: { p10: number; p50: number; p90: number; days: number } | null;
  origin_date: string;
  warnings: string[];
}

export interface TrafficSummary {
  site_id: string;
  site_name: string;
  first_day: string;
  last_day: string;
  hours: number;
  pedestrians: number;
  cyclists: number;
}

export interface Meta {
  built_at: string;
  production_model: ModelName;
  venues: VenueSummary[];
  ingest: IngestMeta;
  forecast: ForecastMeta;
  /** Kontekstidataa, yksi mittauspiste Oulussa. Ei venuekohtainen mittari. */
  traffic: TrafficSummary | null;
}

// ---------------------------------------------------------------------------
// daily.json
// ---------------------------------------------------------------------------

export interface DailyRow {
  date: string;
  visitors_in: number;
  visitors_out: number;
  /** Sisaan- ja ulosmenojen summa, ei uniikkeja kavijoita. */
  visitors_total: number;
  /** false jos vuorokaudesta puuttuu tunteja. */
  is_complete: boolean;
  /** false ennen kuin venuen sensori on otettu kayttoon. */
  is_reporting: boolean;
  is_holiday: boolean;
  /** Puuttuu kun paiva ei ole pyha. */
  holiday_name?: string;
  /** Saakentat puuttuvat jos paivalle ei ole saahavaintoa. */
  temp_mean?: number;
  temp_max?: number;
  precip_sum?: number;
  weather_group?: WeatherGroup;
  /** Lippukentat puuttuvat jos paivalle ei ole lippuriviä. */
  tickets_sold?: number;
  groups_sold?: number;
  tickets_total?: number;
}

/**
 * Sarakemuotoinen paivasarja. Rivimuotoiset objektit kolminkertaistaisivat koon, ja
 * sarja kasvaa joka vuorokausi, joten JSON on sarakemuodossa. Rivimuotoon paastaan
 * apurilla `toDailyRows()` (src/lib/series.ts).
 */
export interface DailyColumns {
  date: string[];
  visitors_in: number[];
  visitors_out: number[];
  visitors_total: number[];
  /** null kun paivalle ei ole saahavaintoa. */
  temp_mean: (number | null)[];
  temp_max: (number | null)[];
  precip_sum: (number | null)[];
  /** Indeksi `DailyData.weather_groups`-taulukkoon, -1 kun luokkaa ei ole. */
  weather_group: number[];
  /** null kun paivalle ei ole lippurivia. */
  tickets_sold: (number | null)[];
  groups_sold: (number | null)[];
  tickets_total: (number | null)[];
  /** Indeksit vuorokausille joista puuttuu tunteja. */
  incomplete_idx: number[];
  /** Indeksit vuorokausille ennen sensorin kayttoonottoa. */
  not_reporting_idx: number[];
  /** Pyhapaivat: paivamaara -> nimi. */
  holidays: Record<string, string>;
}

export interface TrafficDailyRow {
  date: string;
  pedestrians: number;
  cyclists: number;
}

export interface DailyData {
  /** Saatilaluokkien nimet; `DailyColumns.weather_group` indeksoi tahan. */
  weather_groups: WeatherGroup[];
  /** Avain on venue_id merkkijonona. */
  venues: Record<string, DailyColumns>;
  /** Kontekstidataa: yksi mittauspiste kaupungissa, ei venuekohtainen mittari. */
  traffic: TrafficDailyRow[];
}

// ---------------------------------------------------------------------------
// hourly.json
// ---------------------------------------------------------------------------

/**
 * Sarakemuotoinen tuntisarja. Rivimuotoiset objektit kolminkertaistaisivat koon,
 * joten saarekkeet kayttavat `toHourlyRows()`-apuria (src/lib/series.ts).
 */
export interface HourlySeries {
  /**
   * Paikallinen seinakelloaika muodossa "2026-05-22T14". Siirtymaa ei tallenneta,
   * koska koko sarja on Suomen aikaa. Syksyn kesaajan paattyessa toistuva tunti saa
   * saman leiman kahdesti; se on tiedostettu kosmeettinen rajoite.
   */
  ts: string[];
  visitors_in: number[];
  visitors_total: number[];
  /** Indeksit riveille joilla `is_imputed` on tosi. */
  imputed_idx: number[];
  /** Indeksit tunneille joilla sademaara on vahintaan 0,1 mm. */
  rain_idx: number[];
}

export interface HourlyData {
  /** Kuinka monta viimeisinta vuorokautta sarja kattaa. */
  days: number;
  first_day: string;
  last_day: string;
  venues: Record<string, HourlySeries>;
}

// ---------------------------------------------------------------------------
// profile.json
// ---------------------------------------------------------------------------

export interface ProfileCell {
  dow: Dow;
  hour: number;
  /** Keskimaarainen visitors_total. null jos havaintoja ei ole lainkaan. */
  mean: number | null;
  median: number | null;
  /** Havaintopaivien maara talle ruudulle. 0 tarkoittaa puuttuvaa, ei nollaa. */
  n: number;
  /** Kuinka moni havainto oli tasan nolla. */
  n_zero: number;
}

export interface VenueProfile {
  cells: ProfileCell[];
  open_hours: number[];
  max_mean: number;
  days: number;
  first_day: string;
  last_day: string;
}

export interface ProfileData {
  venues: Record<string, VenueProfile>;
}

// ---------------------------------------------------------------------------
// forecast.json
// ---------------------------------------------------------------------------

export interface ForecastDailyRow {
  date: string;
  horizon_days: number;
  p10: number;
  p50: number;
  p90: number;
  weather_source: WeatherSource;
  temp_mean?: number;
  precip_sum?: number;
  weather_group?: WeatherGroup;
  is_holiday: boolean;
  holiday_name?: string;
}

export interface ForecastHourlyRow {
  /** Paikallinen seinakelloaika, sama muoto kuin HourlySeries.ts. */
  ts: string;
  p10: number;
  p50: number;
  p90: number;
  weather_source: WeatherSource;
}

export interface VenueForecast {
  venue_id: number;
  origin_date: string;
  /** Ensimmainen ja viimeinen ennustepaiva. */
  first_day: string;
  last_day: string;
  /** Suurin horisontti jolla saa on dynaamista ennustetta, tyypillisesti 16. */
  forecast_weather_days: number;
  /** Avaimena mallin nimi. Rivit ovat horisonttijarjestyksessa. */
  daily: Record<ModelName, ForecastDailyRow[]>;
  hourly: Record<ModelName, ForecastHourlyRow[]>;
  /** Backtest-MAE horisonttikoreittain, legendaa varten. */
  mae: Record<ModelName, Record<HorizonBucket, number>>;
}

export interface ForecastData {
  generated_at: string;
  models: ModelName[];
  default_model: ModelName;
  venues: Record<string, VenueForecast>;
}

// ---------------------------------------------------------------------------
// quality.json
// ---------------------------------------------------------------------------

export interface BucketMetrics {
  mae: number;
  rmse: number;
  smape: number;
  bias: number;
  coverage_80: number;
  n: number;
}

export interface IntervalBand {
  bucket: HorizonBucket;
  q10: number;
  q90: number;
  n: number;
  is_default: boolean;
}

export interface BacktestRow {
  origin_date: string;
  /** Kohdepaiva on `addDays(origin_date, horizon_days)`, sita ei tallenneta erikseen. */
  horizon_days: number;
  y_true: number;
  y_pred: number;
  p10: number;
  p90: number;
}

/** Sarakemuotoinen backtest. Rivimuotoon apurilla `toBacktestRows()`. */
export interface BacktestColumns {
  /** Uniikit origot. `origin` on indeksi tahan taulukkoon. */
  origins: string[];
  origin: number[];
  horizon_days: number[];
  y_true: number[];
  y_pred: number[];
  p10: number[];
  p90: number[];
}

export interface HorizonPoint {
  horizon_days: number;
  mae: number;
  n: number;
}

export interface VenueQuality {
  venue_id: number;
  venue_name: string;
  origin_date: string;
  n_training_days: number;
  training_window: [string, string];
  n_origins: number;
  backtest_window: [string, string];
  horizon_buckets: HorizonBucket[];
  models: ModelName[];
  benchmarks: ModelName[];
  coverage_method: string;
  /**
   * Mallin oma tuntiprofiili: eri asia kuin profile.json, joka lasketaan koko
   * havaintohistoriasta. Malli katsoo vain viimeiset `lookback_days` vuorokautta.
   */
  hourly_profile: { lookback_days: number; observed_days: number; open_hours: number[] };
  metrics: Record<ModelName, Record<HorizonBucket, BucketMetrics>>;
  benchmark_comparison: Record<ModelName, Record<HorizonBucket, Record<string, number | boolean>>>;
  interval_bands: Record<ModelName, IntervalBand[]>;
  do_not_trust: string[];
  warnings: string[];
  /** Ennuste vs. toteuma mallin nimella avattuna, vain paamallit. */
  backtest: Record<ModelName, BacktestColumns>;
  /** MAE horisontin funktiona, kaikki mallit ja vertailukohdat. */
  mae_by_horizon: Record<ModelName, HorizonPoint[]>;
}

export interface QualityData {
  venues: Record<string, VenueQuality>;
}
