/** Tiedostojen luku ja laatuportit. Erotettu muunnoksista, jotta muunnokset ovat testattavia. */

import { existsSync, readFileSync, statSync } from 'node:fs';
import { basename } from 'node:path';

import { BuildDataError, parseCsv, type Table } from './csv.ts';
import { assertColumns } from './schema.ts';

export function readTable(path: string, expected: readonly string[]): Table {
  if (!existsSync(path)) {
    throw new BuildDataError(
      `Syotetiedosto puuttuu: ${path}\n` +
        '  Aja ensin Python-osiot: make ingest && make forecast.',
    );
  }
  const table = parseCsv(readFileSync(path, 'utf8'), basename(path));
  assertColumns(table, expected);
  return table;
}

export function readJson(path: string, what: string): unknown {
  if (!existsSync(path)) {
    throw new BuildDataError(
      `${what} puuttuu: ${path}\n` + '  Aja ensin Python-osiot: make ingest && make forecast.',
    );
  }
  try {
    return JSON.parse(readFileSync(path, 'utf8'));
  } catch (error) {
    throw new BuildDataError(`${what} ei ole kelvollista JSONia: ${path}\n  ${String(error)}`);
  }
}

export function requireDirectory(path: string, what: string): void {
  if (!existsSync(path) || !statSync(path).isDirectory()) {
    throw new BuildDataError(
      `${what} puuttuu: ${path}\n` + '  Aja ensin Python-osiot: make ingest && make forecast.',
    );
  }
}
