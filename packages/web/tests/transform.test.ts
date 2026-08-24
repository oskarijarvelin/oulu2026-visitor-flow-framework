/**
 * build-data.ts:n muunnokset ja aggregaatit. Nama ovat puhtaita funktioita, joten ne
 * testataan ilman tiedostojarjestelmaa.
 */

import { describe, expect, it } from 'vitest';

import { BuildDataError } from '../scripts/lib/csv.ts';
import {
  buildProfileCells,
  changePct,
  coverage,
  deriveOpenHours,
  forecastWeatherDays,
  maeByHorizon,
  manifestAgeHours,
  mean,
  median,
  round1,
  roundCount,
  shortenLocalTs,
  sum,
  sumForecast,
  summarisePeriod,
} from '../scripts/lib/transform.ts';
import { toBacktestRows, toDailyRows } from '../src/lib/series.ts';
import type {
  BacktestRow,
  DailyColumns,
  DailyRow,
  ForecastDailyRow,
  HourlySeries,
} from '../src/lib/types.ts';

function daily(date: string, total: number, reporting = true): DailyRow {
  return {
    date,
    visitors_in: Math.round(total / 2),
    visitors_out: total - Math.round(total / 2),
    visitors_total: total,
    is_complete: true,
    is_reporting: reporting,
    is_holiday: false,
  };
}

describe('numeroiden pyoristys', () => {
  it('pyoristaa yhteen desimaaliin', () => {
    expect(round1(1.24)).toBe(1.2);
    expect(round1(1.25)).toBe(1.3);
    expect(round1(-1.25)).toBe(-1.2);
    expect(round1(10)).toBe(10);
  });

  it('pyoristaa kavijamaarat kokonaisluvuiksi', () => {
    expect(roundCount(491.447)).toBe(491);
    expect(roundCount(0.5)).toBe(1);
  });
});

describe('tunnusluvut', () => {
  it('laskee keskiarvon, mediaanin ja summan', () => {
    expect(mean([1, 2, 3, 4])).toBe(2.5);
    expect(median([1, 2, 3, 4])).toBe(2.5);
    expect(median([3, 1, 2])).toBe(2);
    expect(sum([1, 2, 3])).toBe(6);
  });

  it('palauttaa nollan tyhjalle joukolle sen sijaan etta kaatuisi', () => {
    expect(mean([])).toBe(0);
    expect(median([])).toBe(0);
  });
});

describe('aikaleimat', () => {
  it('lyhentaa paikallisen aikaleiman seinakelloksi', () => {
    expect(shortenLocalTs('2026-05-22T14:00:00+03:00')).toBe('2026-05-22T14');
    expect(shortenLocalTs('2026-01-01T00:00:00+02:00')).toBe('2026-01-01T00');
  });

  it('kaataa buildin tuntemattomasta muodosta', () => {
    expect(() => shortenLocalTs('2026-05-22 14:00')).toThrow(BuildDataError);
  });

  it('laskee manifestin ian tunteina', () => {
    const now = new Date('2026-08-24T10:00:00Z');
    expect(manifestAgeHours('2026-08-24T08:00:00Z', now)).toBe(2);
    expect(manifestAgeHours('2026-08-22T10:00:00Z', now)).toBe(48);
  });

  it('kaataa buildin kelvottomasta aikaleimasta', () => {
    expect(() => manifestAgeHours('eilen', new Date())).toThrow(BuildDataError);
  });
});

describe('jaksojen yhteenveto', () => {
  const rows = [
    daily('2026-01-01', 0, false),
    daily('2026-01-02', 100),
    daily('2026-01-03', 200),
    daily('2026-01-04', 300),
  ];

  it('laskee vain raportoivilta paivilta', () => {
    const summary = summarisePeriod(rows, '2026-01-04', 4);
    expect(summary.days).toBe(3);
    expect(summary.visitors_total).toBe(600);
    expect(summary.mean_daily).toBe(200);
  });

  it('rajaa ikkunan oikein', () => {
    const summary = summarisePeriod(rows, '2026-01-04', 2);
    expect(summary.days).toBe(2);
    expect(summary.visitors_total).toBe(500);
  });

  it('laskee muutosprosentin ja palauttaa null kun vertailujaksoa ei ole', () => {
    const current = { days: 3, visitors_total: 600, mean_daily: 200 };
    expect(changePct(current, { days: 3, visitors_total: 300, mean_daily: 100 })).toBe(100);
    expect(changePct(current, { days: 0, visitors_total: 0, mean_daily: 0 })).toBeNull();
  });
});

describe('viikonpaiva x tunti -profiili', () => {
  /** 2026-01-05 on maanantai, 2026-01-06 tiistai. */
  const series: HourlySeries = {
    ts: ['2026-01-05T10', '2026-01-12T10', '2026-01-05T03', '2026-01-06T10'],
    visitors_in: [5, 15, 0, 20],
    visitors_total: [10, 30, 0, 40],
    imputed_idx: [],
    rain_idx: [],
  };
  const cells = buildProfileCells(series);

  it('tuottaa taydellisen 7 x 24 -matriisin', () => {
    expect(cells).toHaveLength(168);
  });

  it('laskee keskiarvon ja mediaanin havainnoista', () => {
    const monday10 = cells.find((cell) => cell.dow === 0 && cell.hour === 10)!;
    expect(monday10.n).toBe(2);
    expect(monday10.mean).toBe(20);
    expect(monday10.median).toBe(20);
  });

  it('erottaa aidon nollan puuttuvasta havainnosta', () => {
    const monday3 = cells.find((cell) => cell.dow === 0 && cell.hour === 3)!;
    expect(monday3.n).toBe(1);
    expect(monday3.n_zero).toBe(1);
    expect(monday3.mean).toBe(0);

    const wednesday10 = cells.find((cell) => cell.dow === 2 && cell.hour === 10)!;
    expect(wednesday10.n).toBe(0);
    expect(wednesday10.mean).toBeNull();
    expect(wednesday10.median).toBeNull();
  });

  it('johtaa aukiolotunnit ei-nolla-osuudesta', () => {
    const open = deriveOpenHours(cells);
    expect(open).toContain(10);
    expect(open).not.toContain(3);
  });

  it('pitaa tunnin auki kun ei-nolla-osuus ylittaa kynnyksen', () => {
    const many = Array.from({ length: 20 }, (_, index) => `2026-01-0${(index % 3) + 5}T09`);
    const partial: HourlySeries = {
      ts: many,
      visitors_in: many.map(() => 0),
      visitors_total: many.map((_, index) => (index === 0 ? 5 : 0)),
      imputed_idx: [],
      rain_idx: [],
    };
    const partialCells = buildProfileCells(partial);
    expect(deriveOpenHours(partialCells, 0.04)).toContain(9);
    expect(deriveOpenHours(partialCells, 0.5)).not.toContain(9);
  });
});

describe('backtest-koosteet', () => {
  const rows: BacktestRow[] = [
    { origin_date: '2026-05-01', horizon_days: 1, y_true: 100, y_pred: 120, p10: 80, p90: 160 },
    { origin_date: '2026-05-08', horizon_days: 1, y_true: 200, y_pred: 180, p10: 150, p90: 260 },
    { origin_date: '2026-05-01', horizon_days: 2, y_true: 100, y_pred: 400, p10: 300, p90: 500 },
  ];

  it('laskee MAE:n horisontin mukaan', () => {
    const curve = maeByHorizon(rows);
    expect(curve).toEqual([
      { horizon_days: 1, mae: 20, n: 2 },
      { horizon_days: 2, mae: 300, n: 1 },
    ]);
  });

  it('laskee peittavyyden valin sisalle osuneista', () => {
    expect(coverage(rows)).toBe(0.6667);
    expect(coverage([])).toBe(0);
  });
});

describe('ennusteen koosteet', () => {
  const rows: ForecastDailyRow[] = [
    { date: '2026-05-23', horizon_days: 1, p10: 10, p50: 20, p90: 30, weather_source: 'forecast', is_holiday: false },
    { date: '2026-05-24', horizon_days: 2, p10: 12, p50: 22, p90: 32, weather_source: 'forecast', is_holiday: false },
    {
      date: '2026-06-08',
      horizon_days: 17,
      p10: 14,
      p50: 24,
      p90: 34,
      weather_source: 'climatology',
      is_holiday: false,
    },
  ];

  it('summaa vain valitun horisontin', () => {
    expect(sumForecast(rows, 2)).toEqual({ days: 2, p10: 22, p50: 42, p90: 62 });
  });

  it('palauttaa null kun sarjassa ei ole rivejä', () => {
    expect(sumForecast([], 7)).toBeNull();
  });

  it('tunnistaa viimeisen dynaamisen saan vuorokauden', () => {
    expect(forecastWeatherDays(rows)).toBe(2);
    expect(forecastWeatherDays([])).toBe(0);
  });
});

describe('sarakemuodon purku', () => {
  it('palauttaa saman rivin kuin siihen kirjoitettiin', () => {
    const columns: DailyColumns = {
      date: ['2026-01-01', '2026-01-02'],
      visitors_in: [10, 20],
      visitors_out: [11, 21],
      visitors_total: [21, 41],
      temp_mean: [-5.5, null],
      temp_max: [-2, null],
      precip_sum: [0, null],
      weather_group: [1, -1],
      tickets_sold: [5, null],
      groups_sold: [1, null],
      tickets_total: [6, null],
      incomplete_idx: [1],
      not_reporting_idx: [0],
      holidays: { '2026-01-01': 'Uudenvuodenpäivä' },
    };
    const rows = toDailyRows(columns, ['clear', 'cloudy', 'rain', 'snow', 'other']);

    expect(rows).toHaveLength(2);
    expect(rows[0]).toEqual({
      date: '2026-01-01',
      visitors_in: 10,
      visitors_out: 11,
      visitors_total: 21,
      is_complete: true,
      is_reporting: false,
      is_holiday: true,
      holiday_name: 'Uudenvuodenpäivä',
      temp_mean: -5.5,
      temp_max: -2,
      precip_sum: 0,
      weather_group: 'cloudy',
      tickets_sold: 5,
      groups_sold: 1,
      tickets_total: 6,
    });
    expect(rows[1]).toEqual({
      date: '2026-01-02',
      visitors_in: 20,
      visitors_out: 21,
      visitors_total: 41,
      is_complete: false,
      is_reporting: true,
      is_holiday: false,
    });
  });

  it('erottaa nollan puuttuvasta myos sademaarassa', () => {
    const rows = toDailyRows(
      {
        date: ['2026-01-01', '2026-01-02'],
        visitors_in: [0, 0],
        visitors_out: [0, 0],
        visitors_total: [0, 0],
        temp_mean: [0, null],
        temp_max: [0, null],
        precip_sum: [0, null],
        weather_group: [-1, -1],
        tickets_sold: [null, null],
        groups_sold: [null, null],
        tickets_total: [null, null],
        incomplete_idx: [],
        not_reporting_idx: [],
        holidays: {},
      },
      [],
    );
    expect(rows[0]!.precip_sum).toBe(0);
    expect(rows[1]!.precip_sum).toBeUndefined();
  });

  it('purkaa backtestin origo-indeksit takaisin paivamaariksi', () => {
    const rows = toBacktestRows({
      origins: ['2026-05-01', '2026-05-08'],
      origin: [0, 0, 1],
      horizon_days: [1, 2, 1],
      y_true: [100, 110, 120],
      y_pred: [90, 105, 130],
      p10: [70, 80, 100],
      p90: [130, 140, 160],
    });
    expect(rows).toHaveLength(3);
    expect(rows[0]!.origin_date).toBe('2026-05-01');
    expect(rows[2]).toEqual({
      origin_date: '2026-05-08',
      horizon_days: 1,
      y_true: 120,
      y_pred: 130,
      p10: 100,
      p90: 160,
    });
  });

  it('palauttaa tyhjan taulukon kun sarakkeita ei ole', () => {
    expect(toDailyRows(undefined, [])).toEqual([]);
    expect(toBacktestRows(undefined)).toEqual([]);
  });
});
