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

/**
 * Yksi teksti molemmilla kielilla. Osiot 1 ja 3 kirjoittavat varoituksensa tassa
 * muodossa, joten sivusto valitsee vain avaimen eika arvaile kaannosta.
 */
export interface LocalisedText {
  fi: string;
  en: string;
}

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
  quality_gates: { passed: boolean; warnings: LocalisedText[] };
  /** Lahteet joiden status ei ole "ok". */
  degraded: SourceStatus[];
}

export interface ForecastMeta {
  generated_at: string;
  age_hours: number;
  version: string;
  models: ModelName[];
  skipped_models: ModelName[];
  warnings: LocalisedText[];
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
  warnings: LocalisedText[];
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
  do_not_trust: LocalisedText[];
  warnings: LocalisedText[];
  /** Ennuste vs. toteuma mallin nimella avattuna, vain paamallit. */
  backtest: Record<ModelName, BacktestColumns>;
  /** MAE horisontin funktiona, kaikki mallit ja vertailukohdat. */
  mae_by_horizon: Record<ModelName, HorizonPoint[]>;
}

export interface QualityData {
  venues: Record<string, VenueQuality>;
}

// ---------------------------------------------------------------------------
// accuracy.json
// ---------------------------------------------------------------------------

/**
 * Verdikti sellaisena kuin osio 3 sen kirjoittaa. Sivu ei laske naita uudelleen:
 * `verdicts.json` on jo laskettu, ja sen luvut luetaan sellaisenaan.
 */
export type Verdict = 'better' | 'no_difference' | 'worse';

/** Sään kolme tilaa. Verdikti lasketaan aina `operational`-tilasta. */
export type WeatherMode = 'perfect' | 'operational' | 'climatology';

export interface AccuracyWindow {
  origin: string;
  test_start: string;
  test_end: string;
  horizon_days: number;
  train_window: string;
}

/** Koosteen jasenikkuna. `run_id` osoittaa erikseen tallennettuun ikkuna-ajoon. */
export interface AccuracyWindowRef extends AccuracyWindow {
  run_id: string;
}

export interface AccuracyComparison {
  reference: string;
  n: number;
  /** Mallin ja vertailukohdan paivavirheiden keskiero. Negatiivinen = malli lahempana. */
  mean_difference: number;
  ci_low: number;
  ci_high: number;
  verdict: Verdict;
  model_mae: number;
  reference_mae: number;
  skill_score: number;
  skill_ci_low: number;
  skill_ci_high: number;
  /** Pienin ero jonka tama otos olisi erottanut. Pakollinen osa "ei eroa" -verdiktia. */
  mde: number;
  mde_pct: number;
  dm_statistic: number;
  dm_p_value: number;
  dm_lag: number;
}

export interface AccuracyBias {
  mean_error: number;
  ci_low: number;
  ci_high: number;
  verdict: string;
  mean_actual: number;
  pct_of_actual: number;
}

export interface AccuracyCalibration {
  covered: number;
  n: number;
  coverage: number;
  /** Clopper-Pearsonin eksakti binomivali. */
  ci_low: number;
  ci_high: number;
  target: number;
  verdict: string;
}

export interface AccuracyTotal {
  /** Koosteessa ikkunan tunnus, ikkuna-ajossa puuttuu. */
  label?: string;
  predicted: number;
  actual: number;
  difference: number;
  difference_pct: number;
  p10: number;
  p90: number;
  covers_actual: boolean;
  summed_daily_p10: number;
  summed_daily_p90: number;
  n_ratio_samples: number;
  /** Sisakkaisessa backtestissa oli liian vahan origoja: valia ei pida lukea. */
  is_thin: boolean;
  median_ratio: number;
  /** Sisakkaisten mallien virheissa on tasosiirtyma: vali perii sen. */
  is_drifted: boolean;
}

/** Sään kolmen tilan MAE. `perfect` on ylaraja, ei tulos. */
export interface AccuracyWeatherSensitivity {
  perfect: number;
  operational: number;
  climatology: number;
  gap: number;
  gap_pct: number;
}

/** Koosteen paatulos: bootstrap uudelleenottaa kokonaisia ikkunoita, ei paivia. */
export interface AccuracyPooled {
  reference: string;
  n_windows: number;
  n_days: number;
  mean_difference: number;
  ci_low: number;
  ci_high: number;
  verdict: Verdict;
  windows_favouring: number;
  windows_opposing: number;
  windows_neutral: number;
  mde: number;
  mde_pct: number;
  reference_mae: number;
}

export interface AccuracyPerWindow {
  label: string;
  origin: string;
  run_id?: string;
  reference: string;
  model_mae: number;
  reference_mae: number;
  mean_difference: number;
  ci_low: number;
  ci_high: number;
  verdict: Verdict;
  mde: number;
  mde_pct: number;
  raw_p_value: number;
  holm_p_value: number;
}

/** Yksi malli yhden venuen kohdalla. Ikkuna- ja koosteajolla on eri kentat. */
export interface AccuracyModel {
  model: string;
  /** Ikkuna-ajo. */
  comparison?: AccuracyComparison;
  bias?: AccuracyBias;
  calibration?: AccuracyCalibration;
  total?: AccuracyTotal;
  weather_sensitivity?: AccuracyWeatherSensitivity;
  raw_p_value?: number;
  holm_p_value?: number;
  /** Koosteajo. */
  pooled?: AccuracyPooled;
  per_window?: AccuracyPerWindow[];
  totals?: AccuracyTotal[];
}

/**
 * Paivatason mittarit yhdelle mallille. Nama lasketaan build-aikana
 * `predictions.csv`-tiedostosta ajon paasaan tilassa, koska `verdicts.json` ei niita
 * sisalla. MASE tarvitsee koulutusdatan nimittajan, joka luetaan `metrics.json`:sta;
 * ilman sita se on null.
 */
export interface AccuracyMetrics {
  model: string;
  n: number;
  mae: number;
  rmse: number;
  mase: number | null;
  bias: number;
  pinball_q10: number;
  pinball_q50: number;
  pinball_q90: number;
  coverage_80: number;
  smape: number;
  /** false kun testijaksolla on nollapaivia: sMAPE saavuttaa silloin kattonsa. */
  smape_reliable: boolean;
  zero_days: number;
}

export interface AccuracyHorizonRow {
  bucket: HorizonBucket;
  model: string;
  mae: number;
  n: number;
}

export interface AccuracyWorstDay {
  date: string;
  dow: Dow;
  y_true: number;
  p50: number;
  /** Ennuste miinus toteuma: positiivinen tarkoittaa yliarviota. */
  error: number;
  is_holiday: boolean;
  holiday_name?: string;
}

export interface AccuracyVenue {
  venue_id: number;
  venue_name: string;
  /** Paavertailukohta talla ikkunalla. Koosteessa voi olla "best-per-window". */
  reference: string;
  /** Kaikkien kolmen vertailukohdan MAE. Puuttuu koosteesta. */
  baseline_mae?: Record<string, number>;
  models: AccuracyModel[];
  metrics: AccuracyMetrics[];
  horizon: AccuracyHorizonRow[];
  worst_days: AccuracyWorstDay[];
}

/**
 * Paivasarja sarakemuodossa. Vain paamalleilla on vali; vertailukohdista riittaa p50,
 * koska ne piirretaan ohuina viivoina.
 */
export interface AccuracySeriesModel {
  p50: number[];
  p10?: number[];
  p90?: number[];
}

export interface AccuracySeries {
  dates: string[];
  horizon_days: number[];
  y_true: number[];
  /** Pyhapaivat: paivamaara -> nimi. */
  holidays: Record<string, string>;
  models: Record<string, AccuracySeriesModel>;
}

export interface AccuracyRun {
  run_id: string;
  kind: 'window' | 'sweep';
  created_at: string;
  models: string[];
  reference_rule: string;
  primary_weather_mode: WeatherMode;
  family_size: number;
  /**
   * Ajon kirjoittama verdikkikappale. Osio 3 kirjoittaa molemmat kielet; ennen
   * kaksikielisyytta tallennetuilla ajoilla `summary_en` on tyhja, ja se kootaan
   * silloin rakenteisista kentista.
   */
  summary_fi: string;
  summary_en: string;
  first_day: string;
  last_day: string;
  /** Ikkuna-ajo. */
  window?: AccuracyWindow;
  /** Kooste. */
  sweep?: string;
  windows?: AccuracyWindowRef[];
  /** Koosteen jasenajot, tallennusjarjestyksessa. Tyhja ikkuna-ajolla. */
  members: string[];
  venues: AccuracyVenue[];
  /**
   * Venue_id merkkijonona -> paivasarja. Puuttuu kun sarja on karsittu paketista tai
   * kun ajo on kooste: kooste kootaan jasenajoistaan, jottei sama sarja ole kahdesti.
   */
  series?: Record<string, AccuracySeries>;
}

export interface AccuracyData {
  runs: AccuracyRun[];
  /** Valittu ajo kun osoitteessa ei ole hashia. Null kun ajoja ei ole. */
  default_run: string | null;
  /** Horisonttikorit joihin virhe on ryhmitelty. */
  horizon_buckets: HorizonBucket[];
}
