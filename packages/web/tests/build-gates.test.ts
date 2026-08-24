/**
 * Buildin laatuportit. Nama ajavat oikean `build-data.ts`-skriptin aliprosessina, koska
 * porttien on toimittava juuri siina muodossa jossa `npm run build` niita kutsuu.
 */

import { execFileSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { BuildDataError } from '../scripts/lib/csv.ts';
import { PROCESSED_DIR, WEB_ROOT } from '../scripts/lib/paths.ts';
import { readJson, readTable, requireDirectory } from '../scripts/lib/read.ts';

const hasData = existsSync(resolve(PROCESSED_DIR, 'manifest.json'));
const describeWithData = hasData ? describe : describe.skip;

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

describe('puuttuvat syotteet', () => {
  it('kertoo puuttuvan CSV-tiedoston polun ja ohjaa ajamaan Python-osiot', () => {
    expect(() => readTable(resolve(PROCESSED_DIR, 'ei-olemassa.csv'), ['a'])).toThrow(BuildDataError);
    expect(() => readTable(resolve(PROCESSED_DIR, 'ei-olemassa.csv'), ['a'])).toThrow(/make ingest/);
  });

  it('kertoo puuttuvan ennustehakemiston', () => {
    expect(() => requireDirectory(resolve(PROCESSED_DIR, 'ei-hakemistoa'), 'Ennustehakemisto')).toThrow(
      /Ennustehakemisto puuttuu/,
    );
  });

  it('kertoo puuttuvan JSON-tiedoston', () => {
    expect(() => readJson(resolve(PROCESSED_DIR, 'ei-olemassa.json'), 'Ennustemanifesti')).toThrow(
      /Ennustemanifesti puuttuu/,
    );
  });
});

describeWithData('manifestin ikaraja', () => {
  it('kaataa buildin kun ingest-manifesti on yli 48 tuntia vanha', () => {
    // Kello siirretaan vuoteen 2030, jolloin manifesti on vaistamatta liian vanha.
    const result = runBuildData({ OVF_NOW: '2030-01-01T00:00:00Z' });

    expect(result.status).toBe(1);
    expect(result.stderr).toContain('build-data epaonnistui');
    expect(result.stderr).toContain('Ingest-manifesti on liian vanha');
    expect(result.stderr).toContain('Sallittu:     48 tuntia');
    expect(result.stderr).toMatch(/Ika:\s+\d/);
  }, 60_000);

  it('menee lapi kun manifesti on tuore', () => {
    const result = runBuildData({});
    expect(result.stderr, result.stderr).toBe('');
    expect(result.status).toBe(0);
    expect(result.stdout).toContain('build-data:');
  }, 60_000);

  it('kaataa buildin kun manifesti on tulevaisuudesta', () => {
    const result = runBuildData({ OVF_NOW: '2020-01-01T00:00:00Z' });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain('tulevaisuudessa');
  }, 60_000);

  it('kaataa buildin kelvottomasta OVF_NOW-arvosta', () => {
    const result = runBuildData({ OVF_NOW: 'huomenna' });
    expect(result.status).toBe(1);
    expect(result.stderr).toContain('OVF_NOW');
  }, 60_000);
});
