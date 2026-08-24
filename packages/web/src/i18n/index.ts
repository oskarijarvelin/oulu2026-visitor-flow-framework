/**
 * Kaksikielisyyden perusta. Suomi on oletuskieli ja se asuu juuressa, englanti
 * etuliitteen `/en` takana. Osoitteet vastaavat toisiaan yksi yhteen, joten
 * kielivalitsin voi aina osoittaa saman sivun toiseen kieliversioon.
 *
 * The site is bilingual. Finnish is the default locale and lives at the root, English
 * sits behind the `/en` prefix. The two route trees mirror each other one to one, so the
 * language switch can always point at the same page in the other language.
 */

export const LANGS = ['fi', 'en'] as const;

export type Lang = (typeof LANGS)[number];

export const DEFAULT_LANG: Lang = 'fi';

/** BCP 47 -tunnisteet `lang`- ja `hreflang`-attribuutteihin seka Intl-muotoiluun. */
export const LOCALE: Record<Lang, string> = {
  fi: 'fi-FI',
  en: 'en-GB',
};

export const LANG_NAME: Record<Lang, string> = {
  fi: 'Suomi',
  en: 'English',
};

/** Lyhenne kielivalitsimen painikkeeseen. */
export const LANG_SHORT: Record<Lang, string> = {
  fi: 'FI',
  en: 'EN',
};

export function isLang(value: string): value is Lang {
  return (LANGS as readonly string[]).includes(value);
}

/**
 * Polku ilman kielietuliitetta. `/en/venue/1` ja `/venue/1` palauttavat molemmat
 * `/venue/1`, joten polkuja voi verrata kielestä riippumatta.
 */
export function canonicalPath(pathname: string): string {
  const trimmed = pathname.replace(/\/+$/, '') || '/';
  for (const lang of LANGS) {
    if (lang === DEFAULT_LANG) continue;
    if (trimmed === `/${lang}`) return '/';
    if (trimmed.startsWith(`/${lang}/`)) return trimmed.slice(lang.length + 1);
  }
  return trimmed;
}

/** Kanoninen polku annetulla kielellä. */
export function localizedPath(path: string, lang: Lang): string {
  const canonical = canonicalPath(path);
  if (lang === DEFAULT_LANG) return canonical;
  return canonical === '/' ? `/${lang}` : `/${lang}${canonical}`;
}

/** Kieli osoitteesta. Kaytetaan vain varmistuksena; sivut saavat kielen propsina. */
export function langFromPath(pathname: string): Lang {
  const trimmed = pathname.replace(/\/+$/, '') || '/';
  for (const lang of LANGS) {
    if (lang === DEFAULT_LANG) continue;
    if (trimmed === `/${lang}` || trimmed.startsWith(`/${lang}/`)) return lang;
  }
  return DEFAULT_LANG;
}

/** Toinen kieli. Kahdella kielella tama on yksikasitteinen. */
export function otherLangs(lang: Lang): Lang[] {
  return LANGS.filter((candidate) => candidate !== lang);
}
