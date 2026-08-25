/**
 * Arviointidatan paketointi.
 *
 * Puhtaat muunnokset testataan suoraan, portit ajamalla oikea `build-data.ts`
 * aliprosessina: puuttuva arviointidata ei saa kaataa buildia, mutta tuntematon
 * skeemaversio saa.
 */

import { execFileSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { resolve } from 'node:path';

import { afterAll, describe, expect, it } from 'vitest';

import {
  HORIZON_BUCKETS,
  buildSeries,
  count1,
  horizonBucket,
  horizonRows,
  modelMetrics,
  selectSeriesRuns,
  share3,
  sortRuns,
  worstDays,
  type PredictionRow,
  type RunRef,
} from '../scripts/lib/accuracy.ts';
import { OUT_DIR, PROCESSED_DIR, WEB_ROOT } from '../scripts/lib/paths.ts';
import type { AccuracyData } from '../src/lib/types.ts';

const hasData = existsSync(resolve(PROCESSED_DIR, 'manifest.json'));
const describeWithData = hasData ? describe : describe.skip;

// --- Apurit ----------------------------------------------------------------

function prediction(overrides: Partial<PredictionRow> & { date: string }): PredictionRow {
  return {
    venue_id: 1,
    horizon_days: 1,
    model: 'baseline',
    weather_mode: 'operational',
    y_true: 100,
    p10: 80,
    p50: 100,
    p90: 120,
    ...overrides,
  };
}

function run(overrides: Partial<RunRef> & { run_id: string }): RunRef {
  return {
    kind: 'window',
    created_at: '2026-08-25T19:44:24Z',
    members: [],
    last_day: '2026-04-30',
    ...overrides,
  };
}

interface RunResult {
  status: number;
  stdout: string;
  stderr: string;
}

function runBuildData(env: Record<string, string>): RunResult {
  try {
    const stdout = execFileSync('npx', ['tsx', 'scripts/build-data.ts'], {
      cwd: WEB_ROOT,
      env: { ...process.env, ...env },
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    return { status: 0, stdout, stderr: '' };
  } catch (error) {
    const failure = error as { status?: number; stdout?: string; stderr?: string };
    return { status: failure.status ?? 1, stdout: failure.stdout ?? '', stderr: failure.stderr ?? '' };
  }
}

function readAccuracy(): AccuracyData {
  return JSON.parse(readFileSync(resolve(OUT_DIR, 'accuracy.json'), 'utf8')) as AccuracyData;
}

// --- Pyoristys -------------------------------------------------------------

describe('pyoristys', () => {
  it('pyoristaa kavijamaarat yhteen desimaaliin', () => {
    expect(count1(102.9112)).toBe(102.9);
    expect(count1(96.197)).toBe(96.2);
    expect(count1(-3.2381)).toBe(-3.2);
    expect(count1(108.06223187358225)).toBe(108.1);
  });

  it('pyoristaa osuudet kolmeen desimaaliin', () => {
    expect(share3(0.9)).toBe(0.9);
    expect(share3(-0.06983)).toBe(-0.07);
    expect(share3(0.73472)).toBe(0.735);
  });
});

// --- Karsinta --------------------------------------------------------------

describe('aikasarjojen karsinta', () => {
  it('ottaa enintaan 12 uusinta ikkuna-ajoa', () => {
    const runs = Array.from({ length: 15 }, (_, index) =>
      run({
        run_id: `ikkuna-${index}`,
        created_at: `2026-08-${String(index + 1).padStart(2, '0')}T00:00:00Z`,
      }),
    );
    const keep = selectSeriesRuns(runs);
    expect(keep.size).toBe(12);
    expect(keep.has('ikkuna-14')).toBe(true);
    expect(keep.has('ikkuna-3')).toBe(true);
    expect(keep.has('ikkuna-2')).toBe(false);
  });

  it('ottaa aina ajot joihin kooste viittaa, vaikka ne olisivat vanhoja', () => {
    const runs = [
      ...Array.from({ length: 14 }, (_, index) =>
        run({
          run_id: `ikkuna-${index}`,
          created_at: `2026-08-${String(index + 1).padStart(2, '0')}T00:00:00Z`,
        }),
      ),
      run({
        run_id: 'kooste',
        kind: 'sweep',
        created_at: '2026-08-25T00:00:00Z',
        members: ['ikkuna-0', 'ikkuna-1'],
      }),
    ];
    const keep = selectSeriesRuns(runs);
    expect(keep.has('ikkuna-0')).toBe(true);
    expect(keep.has('ikkuna-1')).toBe(true);
  });

  it('noudattaa annettua rajaa', () => {
    const runs = Array.from({ length: 5 }, (_, index) =>
      run({ run_id: `ikkuna-${index}`, created_at: `2026-08-0${index + 1}T00:00:00Z` }),
    );
    expect(selectSeriesRuns(runs, 2).size).toBe(2);
  });
});

describe('ajojen jarjestys', () => {
  it('nostaa koosteet ensin ja uusimman kummankin ryhman karkeen', () => {
    const runs = [
      run({ run_id: 'ikkuna-vanha', created_at: '2026-05-01T00:00:00Z' }),
      run({ run_id: 'kooste-vanha', kind: 'sweep', created_at: '2026-05-01T00:00:00Z' }),
      run({ run_id: 'ikkuna-uusi', created_at: '2026-08-25T00:00:00Z' }),
      run({ run_id: 'kooste-uusi', kind: 'sweep', created_at: '2026-08-25T00:00:00Z' }),
    ];
    expect(sortRuns(runs).map((entry) => entry.run_id)).toEqual([
      'kooste-uusi',
      'kooste-vanha',
      'ikkuna-uusi',
      'ikkuna-vanha',
    ]);
  });
});

// --- Horisonttikorit -------------------------------------------------------

describe('horisonttikorit', () => {
  it('jakaa vuorokaudet kolmeen koriin', () => {
    expect(horizonBucket(1)).toBe('1-7');
    expect(horizonBucket(7)).toBe('1-7');
    expect(horizonBucket(8)).toBe('8-14');
    expect(horizonBucket(14)).toBe('8-14');
    expect(horizonBucket(15)).toBe('15-30');
    expect(horizonBucket(30)).toBe('15-30');
    // Yli 30 vrk osuu viimeiseen koriin eika omaansa.
    expect(horizonBucket(31)).toBe('15-30');
  });

  it('laskee MAE:n koreittain ja malleittain', () => {
    const rows: PredictionRow[] = [
      prediction({ date: '2026-04-01', horizon_days: 1, y_true: 100, p50: 110 }),
      prediction({ date: '2026-04-02', horizon_days: 7, y_true: 100, p50: 80 }),
      prediction({ date: '2026-04-09', horizon_days: 9, y_true: 100, p50: 160 }),
      prediction({ date: '2026-04-20', horizon_days: 20, model: 'climatology_dow', y_true: 100, p50: 90 }),
    ];
    expect(horizonRows(rows, ['baseline', 'climatology_dow'])).toEqual([
      { bucket: '1-7', model: 'baseline', mae: 15, n: 2 },
      { bucket: '8-14', model: 'baseline', mae: 60, n: 1 },
      { bucket: '15-30', model: 'climatology_dow', mae: 10, n: 1 },
    ]);
  });

  it('jattaa pois mallit joilta ei ole rivejä kyseisessa korissa', () => {
    const rows = [prediction({ date: '2026-04-01', horizon_days: 1 })];
    const buckets = horizonRows(rows, ['baseline', 'seasonal_naive']);
    expect(buckets).toHaveLength(1);
    expect(HORIZON_BUCKETS).toEqual(['1-7', '8-14', '15-30']);
  });
});

// --- Paivatason mittarit ---------------------------------------------------

describe('paivatason mittarit', () => {
  const rows: PredictionRow[] = [
    prediction({ date: '2026-04-01', y_true: 100, p10: 80, p50: 110, p90: 130 }),
    prediction({ date: '2026-04-02', y_true: 200, p10: 150, p50: 180, p90: 260 }),
    prediction({ date: '2026-04-03', y_true: 300, p10: 320, p50: 340, p90: 380 }),
  ];

  it('laskee MAE:n, RMSE:n ja harhan', () => {
    const metrics = modelMetrics('baseline', rows, null);
    // Virheet: +10, -20, +40.
    expect(metrics.mae).toBe(23.3);
    expect(metrics.rmse).toBe(26.5);
    expect(metrics.bias).toBe(10);
    expect(metrics.n).toBe(3);
  });

  it('laskee peittavyyden p10 - p90 -valilta', () => {
    // Kolmas paiva jaa valin ulkopuolelle: 300 < 320.
    expect(modelMetrics('baseline', rows, null).coverage_80).toBe(0.667);
  });

  it('laskee MASEn kun nimittaja on tiedossa ja jattaa sen muuten tyhjaksi', () => {
    expect(modelMetrics('baseline', rows, 100).mase).toBe(0.233);
    expect(modelMetrics('baseline', rows, null).mase).toBeNull();
    expect(modelMetrics('baseline', rows, 0).mase).toBeNull();
  });

  it('merkitsee sMAPEn epaluotettavaksi kun jaksolla on nollapaivia', () => {
    const reliable = modelMetrics('baseline', rows, null);
    expect(reliable.smape_reliable).toBe(true);
    expect(reliable.zero_days).toBe(0);

    const withZero = modelMetrics(
      'baseline',
      [...rows, prediction({ date: '2026-04-04', y_true: 0, p10: 0, p50: 3, p90: 10 })],
      null,
    );
    expect(withZero.smape_reliable).toBe(false);
    expect(withZero.zero_days).toBe(1);
    // Nollapaiva saavuttaa 200 %:n katon riippumatta siita kuinka lahella ennuste oli.
    expect(withZero.smape).toBeGreaterThan(reliable.smape);
  });

  it('laskee pinballin oikealla kvantiililla', () => {
    const metrics = modelMetrics('baseline', rows, null);
    // q10 rankaisee liian korkeaa rajaa painolla 0,9: kolmas paiva jai p10:n alle.
    expect(metrics.pinball_q10).toBe(8.3);
    expect(metrics.pinball_q50).toBe(11.7);
    expect(metrics.pinball_q90).toBe(5.7);
  });

  it('kestaa tyhjan syotteen', () => {
    const metrics = modelMetrics('baseline', [], null);
    expect(metrics.n).toBe(0);
    expect(metrics.mae).toBe(0);
    expect(metrics.smape_reliable).toBe(true);
  });
});

// --- Pahiten menneet paivat ------------------------------------------------

describe('pahiten menneet paivat', () => {
  const rows: PredictionRow[] = [
    prediction({ date: '2026-04-16', y_true: 788, p50: 386 }),
    prediction({ date: '2026-04-24', y_true: 683, p50: 471.8 }),
    prediction({ date: '2026-04-03', y_true: 100, p50: 300 }),
    prediction({ date: '2026-04-05', y_true: 100, p50: 105 }),
    prediction({ date: '2026-04-06', y_true: 100, p50: 90 }),
    prediction({ date: '2026-04-07', y_true: 100, p50: 101 }),
  ];
  const holidays = { '2026-04-03': 'Pitkäperjantai', '2026-04-06': 'Toinen pääsiäispäivä' };

  it('jarjestaa viisi suurinta virhetta itseisarvon mukaan', () => {
    const worst = worstDays(rows, holidays);
    expect(worst).toHaveLength(5);
    // Virheet: 402, 211,2, 200, 10, 5. Kuudes paiva (virhe 1) jaa listalta pois.
    expect(worst.map((day) => day.date)).toEqual([
      '2026-04-16',
      '2026-04-24',
      '2026-04-03',
      '2026-04-06',
      '2026-04-05',
    ]);
  });

  it('sailyttaa virheen etumerkin ja viikonpaivan', () => {
    const [worst] = worstDays(rows, holidays);
    // Malli aliarvioi 16.4.: ennuste 386, toteuma 788.
    expect(worst?.error).toBe(-402);
    expect(worst?.y_true).toBe(788);
    expect(worst?.p50).toBe(386);
    // 16.4.2026 on torstai, ja 0 = maanantai.
    expect(worst?.dow).toBe(3);
  });

  it('merkitsee pyhapaivat nimella', () => {
    const worst = worstDays(rows, holidays);
    const goodFriday = worst.find((day) => day.date === '2026-04-03');
    expect(goodFriday?.is_holiday).toBe(true);
    expect(goodFriday?.holiday_name).toBe('Pitkäperjantai');
    expect(worst.find((day) => day.date === '2026-04-16')?.is_holiday).toBe(false);
  });

  it('ratkaisee tasapelin paivamaaralla, jotta paketti on deterministinen', () => {
    const tied = [
      prediction({ date: '2026-04-10', y_true: 100, p50: 150 }),
      prediction({ date: '2026-04-02', y_true: 100, p50: 50 }),
    ];
    expect(worstDays(tied, {}).map((day) => day.date)).toEqual(['2026-04-02', '2026-04-10']);
  });

  it('noudattaa annettua rajaa', () => {
    expect(worstDays(rows, holidays, 2)).toHaveLength(2);
  });
});

// --- Aikasarja -------------------------------------------------------------

describe('aikasarjan rakennus', () => {
  const rows: PredictionRow[] = [
    prediction({ date: '2026-04-02', horizon_days: 2, y_true: 200, p10: 150, p50: 180, p90: 260 }),
    prediction({ date: '2026-04-01', horizon_days: 1, y_true: 100, p10: 80, p50: 110, p90: 130 }),
    prediction({
      date: '2026-04-01',
      horizon_days: 1,
      model: 'climatology_dow',
      y_true: 100,
      p10: 90,
      p50: 95,
      p90: 140,
    }),
    prediction({
      date: '2026-04-02',
      horizon_days: 2,
      model: 'climatology_dow',
      y_true: 200,
      p10: 90,
      p50: 105,
      p90: 140,
    }),
  ];

  it('jarjestaa paivat ja pitaa sarakkeet samanpituisina', () => {
    const series = buildSeries(rows, ['baseline'], {});
    expect(series.dates).toEqual(['2026-04-01', '2026-04-02']);
    expect(series.y_true).toEqual([100, 200]);
    expect(series.horizon_days).toEqual([1, 2]);
    expect(series.models['baseline']?.p50).toEqual([110, 180]);
  });

  it('tallentaa valin vain paamalleille', () => {
    const series = buildSeries(rows, ['baseline'], {});
    expect(series.models['baseline']?.p10).toEqual([80, 150]);
    expect(series.models['baseline']?.p90).toEqual([130, 260]);
    // Vertailukohdista riittaa p50: ne piirretaan ohuina viivoina ilman valia.
    expect(series.models['climatology_dow']?.p10).toBeUndefined();
    expect(series.models['climatology_dow']?.p90).toBeUndefined();
    expect(series.models['climatology_dow']?.p50).toEqual([95, 105]);
  });

  it('ottaa mukaan vain jaksolle osuvat pyhapaivat', () => {
    const series = buildSeries(rows, ['baseline'], {
      '2026-04-01': 'Testipyhä',
      '2026-05-01': 'Vappu',
    });
    expect(series.holidays).toEqual({ '2026-04-01': 'Testipyhä' });
  });
});

// --- Buildin portit --------------------------------------------------------

describeWithData('arviointidatan portit', () => {
  const temporary = mkdtempSync(resolve(tmpdir(), 'ovf-accuracy-'));

  afterAll(() => {
    rmSync(temporary, { recursive: true, force: true });
    // Palautetaan oikea data, jotta myohemmat ajot eivat nae fixtuureja.
    runBuildData({});
  });

  it('kirjoittaa tyhjan paketin kun arviointihakemistoa ei ole', () => {
    const missing = resolve(temporary, 'ei-hakemistoa');
    const result = runBuildData({ OVF_EVALUATIONS_DIR: missing });

    expect(result.stderr, result.stderr).toBe('');
    expect(result.status).toBe(0);
    expect(result.stdout).toContain('ei arviointiajoja');

    const accuracy = readAccuracy();
    expect(accuracy.runs).toEqual([]);
    expect(accuracy.default_run).toBeNull();
  }, 60_000);

  it('kirjoittaa tyhjan paketin kun rekisterissa ei ole ajoja', () => {
    const empty = resolve(temporary, 'tyhja');
    mkdirSync(empty, { recursive: true });
    writeFileSync(resolve(empty, 'index.json'), JSON.stringify({ schema_version: 'v1', runs: [] }));

    const result = runBuildData({ OVF_EVALUATIONS_DIR: empty });
    expect(result.status).toBe(0);
    expect(readAccuracy().runs).toEqual([]);
  }, 60_000);

  it('kaataa buildin tuntemattomasta skeemaversiosta ja nimeaa ajon', () => {
    const bad = resolve(temporary, 'vaara-versio');
    mkdirSync(resolve(bad, 'eval_v2_testi'), { recursive: true });
    writeFileSync(
      resolve(bad, 'index.json'),
      JSON.stringify({
        schema_version: 'v1',
        runs: [
          {
            run_id: 'eval_v2_testi',
            kind: 'window',
            window: {
              origin: '2026-03-31',
              test_start: '2026-04-01',
              test_end: '2026-04-30',
              horizon_days: 30,
              train_window: 'all',
            },
            sweep: null,
            windows: null,
            models: ['baseline'],
            reference_rule: 'best',
            primary_weather_mode: 'operational',
            verdicts: [],
            members: [],
            created_at: '2026-08-25T19:44:24Z',
          },
        ],
      }),
    );
    writeFileSync(
      resolve(bad, 'eval_v2_testi', 'verdicts.json'),
      JSON.stringify({
        schema_version: 'v9',
        kind: 'window',
        run_id: 'eval_v2_testi',
        primary_weather_mode: 'operational',
        reference_rule: 'best',
        family_size: 1,
        summary_fi: 'testi',
        venues: [],
      }),
    );

    const result = runBuildData({ OVF_EVALUATIONS_DIR: bad });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain('Arviointidatan skeemaversio ei ole tuettu');
    expect(result.stderr).toContain('eval_v2_testi');
    expect(result.stderr).toContain('verdicts.json');
    expect(result.stderr).toContain('Odotettu: v1');
    expect(result.stderr).toContain('Luettu:   "v9"');
  }, 60_000);
});

// --- Paketti oikealla datalla ----------------------------------------------

describeWithData('accuracy.json oikealla datalla', () => {
  const accuracy = readAccuracy();
  const byId = new Map(accuracy.runs.map((entry) => [entry.run_id, entry]));

  it('pysyy alle 150 kilotavun', () => {
    const bytes = Buffer.byteLength(readFileSync(resolve(OUT_DIR, 'accuracy.json'), 'utf8'), 'utf8');
    expect(bytes, `accuracy.json on ${(bytes / 1024).toFixed(1)} kB`).toBeLessThan(150 * 1024);
  });

  it('listaa koosteen ensimmaisena', () => {
    expect(accuracy.runs.length).toBeGreaterThan(0);
    expect(accuracy.runs[0]?.kind).toBe('sweep');
    expect(accuracy.default_run).toBe(accuracy.runs[0]?.run_id);
  });

  it('antaa koosteelle verdiktin molemmille venueille', () => {
    const sweep = byId.get('eval_v1_sweep_monthly_2026-04-01_2026-08-25_baseline');
    expect(sweep, 'kuukausikooste puuttuu').toBeDefined();

    const first = sweep?.venues.find((venue) => venue.venue_id === 1)?.models[0]?.pooled;
    expect(first?.verdict).toBe('worse');
    expect(first?.mean_difference).toBe(60);
    expect(first?.ci_low).toBe(3.1);
    expect(first?.ci_high).toBe(124.4);
    expect(first?.windows_favouring).toBe(1);
    expect(first?.windows_opposing).toBe(4);

    const second = sweep?.venues.find((venue) => venue.venue_id === 2)?.models[0]?.pooled;
    expect(second?.verdict).toBe('worse');
    expect(second?.mean_difference).toBe(17.1);
    expect(second?.ci_low).toBe(3.7);
    expect(second?.ci_high).toBe(32.7);
  });

  it('antaa huhtikuun ikkunalle verdiktin ja MDE:n', () => {
    const april = byId.get('eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline');
    expect(april, 'huhtikuun ikkuna puuttuu').toBeDefined();

    const first = april?.venues.find((venue) => venue.venue_id === 1)?.models[0]?.comparison;
    expect(first?.verdict).toBe('no_difference');
    expect(first?.mean_difference).toBe(6.7);
    expect(first?.ci_low).toBe(-3.2);
    expect(first?.ci_high).toBe(30.7);
    expect(first?.mde).toBe(34.5);
    expect(first?.mde_pct).toBe(35.9);

    const second = april?.venues.find((venue) => venue.venue_id === 2)?.models[0]?.comparison;
    expect(second?.verdict).toBe('worse');
    expect(second?.mean_difference).toBe(20.4);
  });

  it('sailyttaa huhtikuun vertailukohtien MAE:t', () => {
    const april = byId.get('eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline');
    expect(april?.venues.find((venue) => venue.venue_id === 1)?.baseline_mae).toEqual({
      seasonal_naive: 129.5,
      moving_average_28d: 197.6,
      climatology_dow: 96.2,
    });
  });

  it('sailyttaa huhtikuun kokonaismaaran', () => {
    const april = byId.get('eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline');
    const total = april?.venues.find((venue) => venue.venue_id === 1)?.models[0]?.total;
    expect(total?.predicted).toBe(13639.2);
    expect(total?.actual).toBe(13189);
    expect(total?.difference_pct).toBe(3.4);
  });

  it('ei tallenna koosteelle omaa aikasarjaa, koska se kootaan jasenista', () => {
    const sweep = accuracy.runs.find((entry) => entry.kind === 'sweep');
    expect(sweep?.series).toBeUndefined();
    expect(sweep?.members.length).toBeGreaterThan(0);
    for (const member of sweep?.members ?? []) {
      expect(byId.get(member)?.series, `jasenen ${member} sarja puuttuu`).toBeDefined();
    }
  });

  it('rajaa ennusterivit ajon paasaan tilaan', () => {
    const april = byId.get('eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline');
    expect(april?.primary_weather_mode).toBe('operational');
    const venue = april?.venues.find((entry) => entry.venue_id === 1);
    // Yksi rivi per paiva per malli: kolme saan tilaa kolminkertaistaisi taman.
    expect(venue?.metrics.find((entry) => entry.model === 'baseline')?.n).toBe(30);
    expect(venue?.metrics.find((entry) => entry.model === 'baseline')?.mae).toBe(102.9);
  });
});
