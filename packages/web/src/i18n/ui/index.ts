import type { Lang } from '../index.ts';
import { en } from './en.ts';
import { fi, type Translation } from './fi.ts';

const DICTIONARIES: Record<Lang, Translation> = { fi, en };

/** Kayttoliittyman tekstit yhdelle kielelle. */
export function ui(lang: Lang): Translation {
  return DICTIONARIES[lang];
}

export type { Translation };
export { en, fi };
