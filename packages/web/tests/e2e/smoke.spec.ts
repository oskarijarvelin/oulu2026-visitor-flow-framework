/**
 * Savutesti: jokainen sivu latautuu ilman konsolivirheita, paakaavio renderoityy ja
 * sivu ei vieri vaakasuunnassa.
 */

import { expect, test, type ConsoleMessage, type Page } from '@playwright/test';

interface PageUnderTest {
  path: string;
  title: string;
  heading: RegExp;
  /** Vahimmaismaara kaaviosaarekkeita. Jokaisen loydetyn on renderoiduttava. */
  minCharts: number;
}

const PAGES: PageUnderTest[] = [
  { path: '/', title: 'Yleiskuva', heading: /Kävijävirrat yhdellä silmäyksellä/, minCharts: 2 },
  { path: '/venue/1', title: 'Pekuri', heading: /Pekuri/, minCharts: 5 },
  { path: '/venue/2', title: 'Kaupungintalo', heading: /Kaupungintalo/, minCharts: 5 },
  { path: '/weather', title: 'Sää', heading: /Sää ja kävijämäärät/, minCharts: 3 },
  { path: '/forecast', title: 'Ennuste', heading: /Ennuste/, minCharts: 2 },
  { path: '/quality', title: 'Laatu', heading: /Mallien laatu/, minCharts: 4 },
  { path: '/about', title: 'Tietoja', heading: /Mistä data tulee/, minCharts: 0 },
];

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

for (const target of PAGES) {
  test(`${target.path} latautuu ilman konsolivirheita`, async ({ page }) => {
    const errors = collectErrors(page);

    const response = await page.goto(target.path);
    expect(response?.status(), `${target.path} vastasi virheellä`).toBe(200);

    await expect(page).toHaveTitle(new RegExp(`${target.title}.*Oulu2026`));
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(target.heading);

    // Datan laatu -banneri on jokaisella sivulla.
    await expect(page.getByRole('region', { name: 'Datan laatu' })).toBeVisible();

    await hydrateIslands(page);
    expect(errors, `${target.path}: ${errors.join(' | ')}`).toEqual([]);
  });

  if (target.minCharts > 0) {
    test(`${target.path} renderöi kaaviot`, async ({ page }) => {
      await page.goto(target.path);

      // Jokainen saareke korvaa paikanvaraajansa oikealla SVG:lla.
      const count = await hydrateIslands(page);
      expect(count, `${target.path}: kaavioita odotettua vähemmän`).toBeGreaterThanOrEqual(
        target.minCharts,
      );
      await expect(page.locator('.chart-placeholder')).toHaveCount(0);
    });
  }

  test(`${target.path} ei vieri vaakasuunnassa`, async ({ page }) => {
    await page.goto(target.path);
    await hydrateIslands(page);
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
    );
    expect(overflow, `${target.path} vierii vaakasuunnassa ${overflow} pikselia`).toBeLessThanOrEqual(1);
  });
}

test('kaaviolla on tekstivastine ja saavutettava nimi', async ({ page }) => {
  await page.goto('/venue/1');
  await hydrateIslands(page);

  const alternatives = page.getByText('Tekstivastine ja taulukko');
  expect(await alternatives.count()).toBeGreaterThan(0);

  // Tekstivastine avautuu ja sisaltaa taulukon.
  const first = alternatives.first();
  await first.click();
  await expect(page.locator('table.data-table').first()).toBeVisible();

  const labelledCharts = page.locator('astro-island svg[role="img"][aria-label]');
  expect(await labelledCharts.count()).toBeGreaterThan(0);
});

test('rajausvalitsin toimii nappaimistolla', async ({ page }) => {
  await page.goto('/venue/1');
  await hydrateIslands(page);

  const group = page.getByRole('group', { name: 'Aikajakso' }).first();
  const sevenDays = group.getByRole('button', { name: 'Viimeiset 7 vuorokautta' });
  await sevenDays.scrollIntoViewIfNeeded();
  await sevenDays.focus();
  await page.keyboard.press('Enter');
  await expect(sevenDays).toHaveAttribute('aria-pressed', 'true');
});

test('ennustenäkymä erottaa klimatologiavuorokaudet', async ({ page }) => {
  await page.goto('/forecast');
  await hydrateIslands(page);

  // Selite kertoo mista vuorokaudesta saa on klimatologiaa.
  await expect(page.getByText(/Sää klimatologiasta, vrk \d+ alkaen/).first()).toBeVisible();

  // Mallivalitsimessa on oletuksena vain tuotantomalli.
  const modelGroup = page.getByRole('group', { name: 'Malli' }).first();
  await expect(modelGroup.getByRole('button', { name: 'Perusmalli' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(modelGroup.getByRole('button', { name: 'Prophet + XGBoost' })).toHaveAttribute(
    'aria-pressed',
    'false',
  );
});
