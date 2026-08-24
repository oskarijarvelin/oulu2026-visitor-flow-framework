/**
 * Skeeman validointi oikeita tiedostoja vasten.
 *
 * Jos `data/processed/`- tai `data/forecasts/latest/`-tiedostojen sarakkeet muuttuvat,
 * nama testit kaatuvat selkealla viestilla ennen kuin build ehtii tuottaa vaaraa dataa.
 * Sama tarkistus ajetaan buildissa; talla se nakyy myos CI:n testivaiheessa.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { BuildDataError, parseCsv } from '../scripts/lib/csv.ts';
import { FORECAST_DIR, PROCESSED_DIR } from '../scripts/lib/paths.ts';
import {
  FORECAST_MANIFEST_KEYS,
  FORECAST_SCHEMA,
  INGEST_MANIFEST_KEYS,
  METRICS_KEYS,
  PROCESSED_SCHEMA,
  assertColumns,
  assertKeys,
} from '../scripts/lib/schema.ts';

const hasData = existsSync(resolve(PROCESSED_DIR, 'manifest.json'));
const describeWithData = hasData ? describe : describe.skip;

function table(path: string, name: string) {
  return parseCsv(readFileSync(path, 'utf8'), name);
}

describe('skeeman tarkistus', () => {
  it('kertoo puuttuvan sarakkeen nimeltä', () => {
    const parsed = parseCsv('venue_id,date\n1,2026-01-01\n', 'testi.csv');
    expect(() => assertColumns(parsed, ['venue_id', 'date', 'visitors_total'])).toThrow(
      /Puuttuvat sarakkeet: visitors_total/,
    );
  });

  it('kertoo odottamattoman sarakkeen nimeltä', () => {
    const parsed = parseCsv('venue_id,date,extra\n1,2026-01-01,x\n', 'testi.csv');
    expect(() => assertColumns(parsed, ['venue_id', 'date'])).toThrow(/Odottamattomat sarakkeet: extra/);
  });

  it('hyvaksyy eri sarakejarjestyksen', () => {
    const parsed = parseCsv('date,venue_id\n2026-01-01,1\n', 'testi.csv');
    expect(() => assertColumns(parsed, ['venue_id', 'date'])).not.toThrow();
  });

  it('kertoo puuttuvan JSON-kentan nimeltä', () => {
    expect(() => assertKeys({ generated_at: 'x' }, ['generated_at', 'sources'], 'testi.json')).toThrow(
      /Puuttuvat kentat: sources/,
    );
  });

  it('lukee lainausmerkeissa olevat kentat ja pilkut niiden sisalla', () => {
    const parsed = parseCsv('a,b\n"yksi, kaksi","kolme ""neljä"""\n', 'testi.csv');
    expect(parsed.rows[0]).toEqual({ a: 'yksi, kaksi', b: 'kolme "neljä"' });
  });

  it('kaataa rivin jolla on vaara maara kenttia', () => {
    expect(() => parseCsv('a,b\n1,2,3\n', 'testi.csv')).toThrow(BuildDataError);
  });
});

describeWithData('data/processed vastaa sovittua skeemaa', () => {
  for (const [file, columns] of Object.entries(PROCESSED_SCHEMA)) {
    it(file, () => {
      const path = resolve(PROCESSED_DIR, file);
      expect(existsSync(path), `Tiedosto puuttuu: ${path}`).toBe(true);
      const parsed = table(path, file);
      expect(() => assertColumns(parsed, columns)).not.toThrow();
      expect(parsed.rows.length, `${file} on tyhja`).toBeGreaterThan(0);
    });
  }

  it('manifest.json sisaltaa vaaditut kentat', () => {
    const manifest = JSON.parse(readFileSync(resolve(PROCESSED_DIR, 'manifest.json'), 'utf8'));
    expect(() => assertKeys(manifest, INGEST_MANIFEST_KEYS, 'manifest.json')).not.toThrow();
  });
});

describeWithData('data/forecasts/latest vastaa sovittua skeemaa', () => {
  const manifest = JSON.parse(readFileSync(resolve(FORECAST_DIR, 'manifest.json'), 'utf8'));
  const venueIds: number[] = (manifest.venues ?? []).map((venue: { venue_id: number }) => venue.venue_id);

  it('manifest.json sisaltaa vaaditut kentat', () => {
    expect(() => assertKeys(manifest, FORECAST_MANIFEST_KEYS, 'manifest.json')).not.toThrow();
    expect(venueIds.length).toBeGreaterThan(0);
  });

  for (const venueId of venueIds) {
    for (const [file, columns] of Object.entries(FORECAST_SCHEMA)) {
      it(`venue_${venueId}/${file}`, () => {
        const path = resolve(FORECAST_DIR, `venue_${venueId}`, file);
        expect(existsSync(path), `Tiedosto puuttuu: ${path}`).toBe(true);
        const parsed = table(path, file);
        expect(() => assertColumns(parsed, columns)).not.toThrow();
        expect(parsed.rows.length).toBeGreaterThan(0);
      });
    }

    it(`venue_${venueId}/metrics.json`, () => {
      const metrics = JSON.parse(
        readFileSync(resolve(FORECAST_DIR, `venue_${venueId}`, 'metrics.json'), 'utf8'),
      );
      expect(() => assertKeys(metrics, METRICS_KEYS, 'metrics.json')).not.toThrow();
    });
  }
});

describeWithData('ennustetiedostojen sisalto on kayttokelpoinen', () => {
  const manifest = JSON.parse(readFileSync(resolve(FORECAST_DIR, 'manifest.json'), 'utf8'));
  const venueIds: number[] = (manifest.venues ?? []).map((venue: { venue_id: number }) => venue.venue_id);

  for (const venueId of venueIds) {
    it(`venue_${venueId}: p10 <= p50 <= p90 kaikilla riveilla`, () => {
      const parsed = table(resolve(FORECAST_DIR, `venue_${venueId}`, 'daily_30d.csv'), 'daily_30d.csv');
      for (const row of parsed.rows) {
        const p10 = Number(row['p10']);
        const p50 = Number(row['p50']);
        const p90 = Number(row['p90']);
        expect(p10, `${row['date']} ${row['model']}`).toBeLessThanOrEqual(p50);
        expect(p50, `${row['date']} ${row['model']}`).toBeLessThanOrEqual(p90);
      }
    });

    it(`venue_${venueId}: weather_source on tunnettu arvo`, () => {
      const parsed = table(resolve(FORECAST_DIR, `venue_${venueId}`, 'daily_30d.csv'), 'daily_30d.csv');
      const sources = new Set(parsed.rows.map((row) => row['weather_source']));
      for (const source of sources) {
        expect(['archive', 'forecast', 'climatology']).toContain(source);
      }
    });
  }
});
