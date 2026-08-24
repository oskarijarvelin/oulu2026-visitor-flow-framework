/**
 * Kaksikielisyyden invariantit.
 *
 * Sanastot tyypitetaan toisiaan vasten, joten puuttuva avain kaatuu jo
 * tyyppitarkistuksessa. Nama testit varmistavat sen mita tyypit eivat nae:
 * ettei kaannos ole jaanyt kopioksi lahdekielesta ja etta osoitteet vastaavat
 * toisiaan molempiin suuntiin.
 */

import { describe, expect, it } from 'vitest';

import { chartStrings } from '../src/i18n/charts.ts';
import {
  DEFAULT_LANG,
  LANGS,
  canonicalPath,
  isLang,
  langFromPath,
  localizedPath,
  otherLangs,
} from '../src/i18n/index.ts';
import { en } from '../src/i18n/ui/en.ts';
import { fi } from '../src/i18n/ui/fi.ts';

type Dict = Record<string, unknown>;

/** Kaikki avaimet pistenotaatiolla, esim. "home.keyFigures". */
function flatten(value: unknown, prefix = ''): Map<string, unknown> {
  const out = new Map<string, unknown>();
  if (typeof value !== 'object' || value === null) return out;
  for (const [key, entry] of Object.entries(value as Dict)) {
    const path = prefix === '' ? key : `${prefix}.${key}`;
    if (typeof entry === 'object' && entry !== null) {
      for (const [nested, nestedValue] of flatten(entry, path)) out.set(nested, nestedValue);
    } else {
      out.set(path, entry);
    }
  }
  return out;
}

const fiKeys = flatten(fi);
const enKeys = flatten(en);

describe('sanastot', () => {
  it('sisaltavat samat avaimet', () => {
    expect([...enKeys.keys()].sort()).toEqual([...fiKeys.keys()].sort());
  });

  it('sisaltavat saman tyypin jokaisella avaimella', () => {
    for (const [key, value] of fiKeys) {
      expect(typeof enKeys.get(key), `avain ${key}`).toBe(typeof value);
    }
  });

  it('eivat sisalla tyhjia arvoja', () => {
    for (const [key, value] of [...fiKeys, ...enKeys]) {
      if (typeof value === 'string') expect(value.trim(), `avain ${key}`).not.toBe('');
    }
  });

  /**
   * Kaannos joka on tavulleen sama kuin lahde on yleensa unohtunut kaantaa. Sallitut
   * poikkeukset ovat oikeasti samoja molemmilla kielilla: lyhenteet, mallien nimet ja
   * tekniset tunnisteet.
   */
  it('eivat jata suomenkielista tekstia englanniksi', () => {
    const allowed = new Set([
      'site.titleSuffix',
      'about.openingHours',
      'venue.ticketsPerTicket',
    ]);
    const identical: string[] = [];
    for (const [key, value] of fiKeys) {
      if (typeof value !== 'string' || allowed.has(key)) continue;
      // Lyhyet merkkijonot voivat sattua olemaan samat, esim. "MAE".
      if (value.length < 8) continue;
      if (enKeys.get(key) === value) identical.push(key);
    }
    expect(identical, `kaantamatta: ${identical.join(', ')}`).toEqual([]);
  });

  it('tuottavat eri tuloksen funktioavaimilla', () => {
    const fiTitle = fi.home.panelTitle('Pekuri', 30, 7);
    const enTitle = en.home.panelTitle('Pekuri', 30, 7);
    expect(fiTitle).not.toBe(enTitle);
    expect(fiTitle).toContain('Pekuri');
    expect(enTitle).toContain('Pekuri');
  });
});

describe('kaavioiden tekstit', () => {
  it('loytyvat molemmille kielille ja eroavat toisistaan', () => {
    const finnish = chartStrings('fi');
    const english = chartStrings('en');
    expect(finnish.rangeLabel).not.toBe(english.rangeLabel);
    expect(finnish.rangeDays(7)).toBe('7 vrk');
    expect(english.rangeDays(7)).toBe('7 days');
    expect(finnish.climatologyBand(17)).toContain('17');
    expect(english.climatologyBand(17)).toContain('17');
  });
});

describe('osoitteet', () => {
  it('lisaavat etuliitteen vain muille kuin oletuskielelle', () => {
    expect(localizedPath('/', 'fi')).toBe('/');
    expect(localizedPath('/', 'en')).toBe('/en');
    expect(localizedPath('/venue/1', 'fi')).toBe('/venue/1');
    expect(localizedPath('/venue/1', 'en')).toBe('/en/venue/1');
  });

  it('palauttavat kanonisen polun kummasta kieliversiosta tahansa', () => {
    expect(canonicalPath('/en/venue/1')).toBe('/venue/1');
    expect(canonicalPath('/venue/1')).toBe('/venue/1');
    expect(canonicalPath('/en')).toBe('/');
    expect(canonicalPath('/en/')).toBe('/');
    expect(canonicalPath('/')).toBe('/');
  });

  it('eivat sekoita polkua joka alkaa kielitunnuksen kaltaisella osalla', () => {
    expect(canonicalPath('/energy')).toBe('/energy');
    expect(langFromPath('/energy')).toBe('fi');
  });

  it('ovat kaannettavissa molempiin suuntiin', () => {
    for (const path of ['/', '/venue/1', '/venue/2', '/weather', '/forecast', '/quality', '/about']) {
      for (const lang of LANGS) {
        const localized = localizedPath(path, lang);
        expect(langFromPath(localized)).toBe(lang);
        expect(canonicalPath(localized)).toBe(path);
      }
    }
  });

  it('tunnistavat kielen', () => {
    expect(isLang('fi')).toBe(true);
    expect(isLang('en')).toBe(true);
    expect(isLang('sv')).toBe(false);
    expect(otherLangs('fi')).toEqual(['en']);
    expect(otherLangs(DEFAULT_LANG)).not.toContain(DEFAULT_LANG);
  });
});
