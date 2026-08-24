/** Pieni RFC 4180 -yhteensopiva CSV-lukija. Ei riippuvuuksia, koska tiedostot ovat pienia. */

export type Row = Record<string, string>;

export interface Table {
  /** Tiedoston nimi virheilmoituksia varten. */
  name: string;
  columns: string[];
  rows: Row[];
}

export function parseCsv(text: string, name: string): Table {
  const records = parseRecords(text);
  if (records.length === 0) {
    throw new BuildDataError(`Tiedosto ${name} on tyhja.`);
  }
  const columns = records[0]!;
  const rows: Row[] = [];
  for (let i = 1; i < records.length; i += 1) {
    const record = records[i]!;
    if (record.length === 1 && record[0] === '') continue;
    if (record.length !== columns.length) {
      throw new BuildDataError(
        `Tiedoston ${name} rivilla ${i + 1} on ${record.length} kenttaa, otsikossa ${columns.length}.`,
      );
    }
    const row: Row = {};
    for (let c = 0; c < columns.length; c += 1) row[columns[c]!] = record[c]!;
    rows.push(row);
  }
  return { name, columns, rows };
}

function parseRecords(text: string): string[][] {
  const clean = text.charCodeAt(0) === 0xfeff ? text.slice(1) : text;
  const records: string[][] = [];
  let record: string[] = [];
  let field = '';
  let quoted = false;
  let i = 0;
  while (i < clean.length) {
    const ch = clean[i]!;
    if (quoted) {
      if (ch === '"') {
        if (clean[i + 1] === '"') {
          field += '"';
          i += 2;
          continue;
        }
        quoted = false;
        i += 1;
        continue;
      }
      field += ch;
      i += 1;
      continue;
    }
    if (ch === '"') {
      quoted = true;
      i += 1;
      continue;
    }
    if (ch === ',') {
      record.push(field);
      field = '';
      i += 1;
      continue;
    }
    if (ch === '\n' || ch === '\r') {
      record.push(field);
      records.push(record);
      record = [];
      field = '';
      i += ch === '\r' && clean[i + 1] === '\n' ? 2 : 1;
      continue;
    }
    field += ch;
    i += 1;
  }
  if (field !== '' || record.length > 0) {
    record.push(field);
    records.push(record);
  }
  return records;
}

/** Virhe joka lopettaa buildin. Viesti tulostetaan sellaisenaan, ilman pinoa. */
export class BuildDataError extends Error {
  override name = 'BuildDataError';
}

// --- Kenttien lukeminen tyypitettyina -------------------------------------

export function str(row: Row, key: string): string {
  const value = row[key];
  if (value === undefined) throw new BuildDataError(`Sarake ${key} puuttuu rivilta.`);
  return value;
}

export function optionalStr(row: Row, key: string): string | null {
  const value = row[key];
  return value === undefined || value === '' ? null : value;
}

export function num(row: Row, key: string): number {
  const value = optionalStr(row, key);
  if (value === null) throw new BuildDataError(`Sarake ${key} on tyhja, vaikka sen pitaisi olla luku.`);
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    throw new BuildDataError(`Sarakkeen ${key} arvoa "${value}" ei voi lukea lukuna.`);
  }
  return parsed;
}

export function optionalNum(row: Row, key: string): number | null {
  const value = optionalStr(row, key);
  if (value === null) return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

export function int(row: Row, key: string): number {
  return Math.round(num(row, key));
}

/** Python kirjoittaa boolit muodossa True/False. */
export function bool(row: Row, key: string): boolean {
  const value = str(row, key).trim().toLowerCase();
  if (value === 'true' || value === '1') return true;
  if (value === 'false' || value === '0' || value === '') return false;
  throw new BuildDataError(`Sarakkeen ${key} arvoa "${value}" ei voi lukea totuusarvona.`);
}
