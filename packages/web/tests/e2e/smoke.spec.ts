/**
 * Savutesti: jokainen sivu latautuu molemmilla kielilla ilman konsolivirheita,
 * paakaavio renderoityy ja sivu ei vieri vaakasuunnassa.
 */

import { expect, test, type ConsoleMessage, type Page } from '@playwright/test';

type Lang = 'fi' | 'en';

interface PageUnderTest {
  /** Kanoninen polku ilman kielietuliitetta. */
  path: string;
  title: Record<Lang, string>;
  heading: Record<Lang, RegExp>;
  /** Vahimmaismaara kaaviosaarekkeita. Jokaisen loydetyn on renderoiduttava. */
  minCharts: number;
}

const PAGES: PageUnderTest[] = [
  {
    path: '/',
    title: { fi: 'Yleiskuva', en: 'Overview' },
    heading: { fi: /Kävijävirrat yhdellä silmäyksellä/, en: /Visitor flows at a glance/ },
    minCharts: 2,
  },
  {
    path: '/venue/1',
    title: { fi: 'Pekuri', en: 'Pekuri' },
    heading: { fi: /Pekuri/, en: /Pekuri/ },
    minCharts: 5,
  },
  {
    path: '/venue/2',
    title: { fi: 'Kaupungintalo', en: 'Kaupungintalo' },
    heading: { fi: /Kaupungintalo/, en: /Kaupungintalo/ },
    minCharts: 5,
  },
  {
    path: '/weather',
    title: { fi: 'Sää', en: 'Weather' },
    heading: { fi: /Sää ja kävijämäärät/, en: /Weather and visitor counts/ },
    minCharts: 3,
  },
  {
    path: '/forecast',
    title: { fi: 'Ennuste', en: 'Forecast' },
    heading: { fi: /Ennuste/, en: /Forecast/ },
    minCharts: 2,
  },
  {
    path: '/quality',
    title: { fi: 'Laatu', en: 'Quality' },
    heading: { fi: /Mallien laatu/, en: /Model quality/ },
    minCharts: 4,
  },
  {
    path: '/accuracy',
    title: { fi: 'Tarkkuus', en: 'Accuracy' },
    heading: { fi: /Ennustemallin tarkkuustestit/, en: /Forecast accuracy tests/ },
    minCharts: 6,
  },
  {
    path: '/about',
    title: { fi: 'Tietoja', en: 'About' },
    heading: { fi: /Mistä data tulee/, en: /Where the data comes from/ },
    minCharts: 0,
  },
];

const LANGS: Lang[] = ['fi', 'en'];

const SITE_NAME: Record<Lang, string> = {
  fi: 'Oulu2026 kävijävirrat',
  en: 'Oulu2026 visitor flows',
};

const BANNER_LABEL: Record<Lang, string> = { fi: 'Datan laatu', en: 'Data quality' };
const RANGE_LABEL: Record<Lang, string> = { fi: 'Aikajakso', en: 'Period' };
const MODEL_LABEL: Record<Lang, string> = { fi: 'Malli', en: 'Model' };
const LANGUAGE_LABEL: Record<Lang, string> = { fi: 'Kieli', en: 'Language' };
const SEVEN_DAYS: Record<Lang, string> = {
  fi: 'Viimeiset 7 vuorokautta',
  en: 'The last 7 days',
};
const TEXT_ALTERNATIVE: Record<Lang, string> = {
  fi: 'Tekstivastine ja taulukko',
  en: 'Text alternative and table',
};
const BASELINE: Record<Lang, string> = { fi: 'Perusmalli', en: 'Baseline' };
const CLIMATOLOGY: Record<Lang, RegExp> = {
  fi: /Sää klimatologiasta/,
  en: /Weather from climatology/,
};

/** Kanoninen polku annetulla kielellä. Sama sääntö kuin src/i18n/index.ts. */
function localized(path: string, lang: Lang): string {
  if (lang === 'fi') return path;
  return path === '/' ? '/en' : `/en${path}`;
}

function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (message: ConsoleMessage) => {
    if (message.type() === 'error') errors.push(`console: ${message.text()}`);
  });
  page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`));
  page.on('requestfailed', (request) => {
    errors.push(`requestfailed: ${request.url()} ${request.failure()?.errorText ?? ''}`);
  });
  return errors;
}

/**
 * Vierittaa jokaisen saarekkeen nakyviin ja odottaa etta se on hydratoitunut.
 *
 * Saarekkeet latautuvat `client:visible`-direktiivilla, joten ne heraavat vasta kun ne
 * tulevat nakyviin. Sivun vierittaminen silmamaaraisin harppauksin ei riita, koska
 * sivun korkeus kasvaa kaavioiden ilmestyessa.
 */
async function hydrateIslands(page: Page): Promise<number> {
  const islands = page.locator('astro-island');
  const count = await islands.count();
  for (let index = 0; index < count; index += 1) {
    const island = islands.nth(index);
    await island.scrollIntoViewIfNeeded();
    await expect(island.locator('svg').first()).toBeVisible({ timeout: 20_000 });
  }
  await page.evaluate(() => window.scrollTo({ top: 0, behavior: 'instant' }));
  return count;
}

for (const lang of LANGS) {
  for (const target of PAGES) {
    const url = localized(target.path, lang);

    test(`[${lang}] ${url} latautuu ilman konsolivirheita`, async ({ page }) => {
      const errors = collectErrors(page);

      const response = await page.goto(url);
      expect(response?.status(), `${url} vastasi virheellä`).toBe(200);

      await expect(page).toHaveTitle(new RegExp(`${target.title[lang]}.*${SITE_NAME[lang]}`));
      await expect(page.getByRole('heading', { level: 1 })).toHaveText(target.heading[lang]);
      await expect(page.locator('html')).toHaveAttribute('lang', lang);

      // Datan laatu -banneri on jokaisella sivulla, kummallakin kielellä.
      await expect(page.getByRole('region', { name: BANNER_LABEL[lang] })).toBeVisible();

      await hydrateIslands(page);
      expect(errors, `${url}: ${errors.join(' | ')}`).toEqual([]);
    });

    if (target.minCharts > 0) {
      test(`[${lang}] ${url} renderöi kaaviot`, async ({ page }) => {
        await page.goto(url);

        const count = await hydrateIslands(page);
        expect(count, `${url}: kaavioita odotettua vähemmän`).toBeGreaterThanOrEqual(target.minCharts);
        await expect(page.locator('.chart-placeholder')).toHaveCount(0);
      });
    }

    test(`[${lang}] ${url} ei vieri vaakasuunnassa`, async ({ page }) => {
      await page.goto(url);
      await hydrateIslands(page);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `${url} vierii vaakasuunnassa ${overflow} pikselia`).toBeLessThanOrEqual(1);
    });
  }
}

test('kielivalitsin vie samaan sivuun toisella kielellä', async ({ page }) => {
  await page.goto('/venue/1');

  const group = page.getByRole('group', { name: LANGUAGE_LABEL.fi });
  await expect(group.getByRole('link', { name: 'FI' })).toHaveAttribute('aria-current', 'true');

  await group.getByRole('link', { name: /English/ }).click();

  await expect(page).toHaveURL(/\/en\/venue\/1$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Pekuri/);

  // Ja takaisin: valitsin palaa samaan sivuun suomeksi.
  const englishGroup = page.getByRole('group', { name: LANGUAGE_LABEL.en });
  await expect(englishGroup.getByRole('link', { name: 'EN' })).toHaveAttribute('aria-current', 'true');
  await englishGroup.getByRole('link', { name: /Suomi/ }).click();

  await expect(page).toHaveURL(/\/venue\/1$/);
  await expect(page.locator('html')).toHaveAttribute('lang', 'fi');
});

test('kielivalitsin toimii myös etusivulla', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('group', { name: LANGUAGE_LABEL.fi }).getByRole('link', { name: /English/ }).click();
  await expect(page).toHaveURL(/\/en$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/Visitor flows at a glance/);
});

test('sivulla on hreflang-vaihtoehdot molemmille kielille', async ({ page }) => {
  await page.goto('/en/weather');
  await expect(page.locator('link[rel="alternate"][hreflang="fi"]')).toHaveAttribute(
    'href',
    /\/weather$/,
  );
  await expect(page.locator('link[rel="alternate"][hreflang="en"]')).toHaveAttribute(
    'href',
    /\/en\/weather$/,
  );
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute('href', /\/en\/weather$/);
});

for (const lang of LANGS) {
  test(`[${lang}] kaaviolla on tekstivastine ja saavutettava nimi`, async ({ page }) => {
    await page.goto(localized('/venue/1', lang));
    await hydrateIslands(page);

    const alternatives = page.getByText(TEXT_ALTERNATIVE[lang]);
    expect(await alternatives.count()).toBeGreaterThan(0);

    await alternatives.first().click();
    await expect(page.locator('table.data-table').first()).toBeVisible();

    const labelledCharts = page.locator('astro-island svg[role="img"][aria-label]');
    expect(await labelledCharts.count()).toBeGreaterThan(0);
  });

  test(`[${lang}] rajausvalitsin toimii nappaimistolla ja on kaannetty`, async ({ page }) => {
    await page.goto(localized('/venue/1', lang));
    await hydrateIslands(page);

    const group = page.getByRole('group', { name: RANGE_LABEL[lang] }).first();
    const sevenDays = group.getByRole('button', { name: SEVEN_DAYS[lang] });
    await sevenDays.scrollIntoViewIfNeeded();
    await sevenDays.focus();
    await page.keyboard.press('Enter');
    await expect(sevenDays).toHaveAttribute('aria-pressed', 'true');
  });

  test(`[${lang}] ennustenäkymä erottaa klimatologiavuorokaudet`, async ({ page }) => {
    await page.goto(localized('/forecast', lang));
    await hydrateIslands(page);

    await expect(page.getByText(CLIMATOLOGY[lang]).first()).toBeVisible();

    // Mallivalitsimessa on oletuksena vain tuotantomalli.
    const modelGroup = page.getByRole('group', { name: MODEL_LABEL[lang] }).first();
    await expect(modelGroup.getByRole('button', { name: BASELINE[lang], exact: true })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await expect(modelGroup.getByRole('button', { name: 'Prophet + XGBoost' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });
}

/**
 * Ajovalitsin. Sivu renderoi jokaisen ajon palvelimella ja piilottaa muut kuin valitun,
 * joten valitsimen on vaihdettava sisalto ilman uutta pyyntoa. Hash-linkin on avattava
 * sama nakyma suoraan.
 */
const RUNS_LABEL: Record<Lang, string> = { fi: 'Valitse arviointiajo', en: 'Choose an evaluation run' };
const SWEEP_RUN = 'eval_v1_sweep_monthly_2026-04-01_2026-08-25_baseline';
const APRIL_RUN = 'eval_v1_2026-03-31_2026-04-01_2026-04-30_baseline';

for (const lang of LANGS) {
  test(`[${lang}] ajovalitsin vaihtaa nakyman ja paivittaa osoitteen`, async ({ page }) => {
    const errors = collectErrors(page);
    await page.goto(localized('/accuracy', lang));

    const selector = page.getByRole('navigation', { name: RUNS_LABEL[lang] });
    const links = selector.getByRole('link');
    await expect(links).toHaveCount(await links.count());
    expect(await links.count()).toBeGreaterThanOrEqual(6);

    // Kooste on ensimmaisena ja valittuna ilman hashia.
    const first = links.first();
    await expect(first).toHaveAttribute('aria-current', 'true');
    await expect(first).toHaveAttribute('href', `#run=${SWEEP_RUN}`);
    expect(await page.locator('html').getAttribute('data-accuracy-run')).toBe(SWEEP_RUN);

    const april = selector.locator(`[data-run-link="${APRIL_RUN}"]`);
    await april.scrollIntoViewIfNeeded();
    await april.click();

    await expect(page).toHaveURL(new RegExp(`#run=${APRIL_RUN}$`));
    await expect(april).toHaveAttribute('aria-current', 'true');
    await expect(first).toHaveAttribute('aria-current', 'false');
    expect(await page.locator('html').getAttribute('data-accuracy-run')).toBe(APRIL_RUN);

    // Vain valitun ajon lohkot ovat nakyvissa.
    await expect(page.locator(`[data-run="${APRIL_RUN}"]`).first()).toBeVisible();
    await expect(page.locator(`[data-run="${SWEEP_RUN}"]`).first()).toBeHidden();

    expect(errors, errors.join(' | ')).toEqual([]);
  });

  test(`[${lang}] hash-linkki avaa oikean ajon suoraan`, async ({ page }) => {
    await page.goto(`${localized('/accuracy', lang)}#run=${APRIL_RUN}`);

    expect(await page.locator('html').getAttribute('data-accuracy-run')).toBe(APRIL_RUN);
    await expect(page.locator(`[data-run="${APRIL_RUN}"]`).first()).toBeVisible();
    await expect(page.locator(`[data-run="${SWEEP_RUN}"]`).first()).toBeHidden();
    await expect(
      page.getByRole('navigation', { name: RUNS_LABEL[lang] }).locator(`[data-run-link="${APRIL_RUN}"]`),
    ).toHaveAttribute('aria-current', 'true');
  });

  test(`[${lang}] tuntematon hash palaa uusimpaan koosteeseen`, async ({ page }) => {
    await page.goto(`${localized('/accuracy', lang)}#run=ei-tallennettu`);
    expect(await page.locator('html').getAttribute('data-accuracy-run')).toBe(SWEEP_RUN);
    await expect(page.locator(`[data-run="${SWEEP_RUN}"]`).first()).toBeVisible();
  });
}

test('kooste esittaa verdiktin sellaisenaan myos mallia vastaan', async ({ page }) => {
  await page.goto('/accuracy');

  // Kooste on mallia vastaan molemmilla venueilla, eika otsikkoon nosteta parasta ikkunaa.
  const verdicts = page.locator(`[data-run="${SWEEP_RUN}"]`).getByText(/huonompi kuin vertailukohta/);
  expect(await verdicts.count()).toBeGreaterThanOrEqual(2);
});

test('"ei havaittavaa eroa" kantaa aina MDE-lauseen', async ({ page }) => {
  await page.goto(`/accuracy#run=${APRIL_RUN}`);

  const panel = page.locator(`[data-run="${APRIL_RUN}"]`);
  await expect(panel.getByText(/ei havaittavaa eroa/).first()).toBeVisible();
  await expect(panel.getByText(/olisi erottanut vasta/).first()).toBeVisible();
});
