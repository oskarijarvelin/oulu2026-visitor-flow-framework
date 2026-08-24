/**
 * Kaaviosaarekkeiden yhteinen pohja: leveyden mukaan skaalautuva piirto, valitsimet ja
 * yhtenaiset akseliasetukset.
 *
 * Kaikki aikaleimat on koodattu seinakelloajaksi UTC-hetkena, joten akselit kayttavat
 * `type: 'utc'`-skaalaa ja UTC-metodeja. Nain akselit nayttavat Suomen aikaa ilman
 * aikavyohykekirjastoja.
 */

import * as Plot from '@observablehq/plot';

import { NEUTRAL } from '../lib/colors.ts';
import { formatDecimal, formatInt } from '../lib/format.ts';

export { Plot };

const MONTHS = ['tammi', 'helmi', 'maalis', 'huhti', 'touko', 'kesä', 'heinä', 'elo', 'syys', 'loka', 'marras', 'joulu'];

/** "22.5." akselille. */
export function tickDay(value: Date): string {
  return `${value.getUTCDate()}.${value.getUTCMonth() + 1}.`;
}

/** "toukokuu" tai "22.5." riippuen tiheydesta. */
export function tickMonth(value: Date): string {
  return value.getUTCDate() === 1 ? `${MONTHS[value.getUTCMonth()]}` : tickDay(value);
}

/** "14:00" akselille. */
export function tickHour(value: Date): string {
  return `${String(value.getUTCHours()).padStart(2, '0')}:00`;
}

/** "22.5.2026 14:00" vihjeeseen. */
export function titleDateTime(value: Date): string {
  const date = `${value.getUTCDate()}.${value.getUTCMonth() + 1}.${value.getUTCFullYear()}`;
  return `${date} ${String(value.getUTCHours()).padStart(2, '0')}:00`;
}

/** "22.5.2026" vihjeeseen. */
export function titleDate(value: Date): string {
  return `${value.getUTCDate()}.${value.getUTCMonth() + 1}.${value.getUTCFullYear()}`;
}

export function tickCount(value: number): string {
  return formatInt(value);
}

export function tickDecimal(value: number): string {
  return formatDecimal(value);
}

/** Yhteiset asetukset kaikille kaavioille. */
export function baseOptions(width: number, height: number): Plot.PlotOptions {
  return {
    width,
    height,
    marginLeft: width < 480 ? 44 : 56,
    marginRight: 12,
    marginTop: 16,
    marginBottom: 34,
    style: {
      background: 'transparent',
      color: NEUTRAL.ink,
      fontSize: width < 480 ? '11px' : '12px',
      overflow: 'visible',
    },
  };
}

export interface MountOptions {
  /** Kaavion tekstivastine, luetaan ruudunlukijalle. */
  ariaLabel: string;
  /** Vahimmaisleveys jolla piirretaan. Kapeammalla kaytetaan tata. */
  minWidth?: number;
}

type Renderer = (width: number) => SVGSVGElement | HTMLElement;

/**
 * Piirtaa kaavion ja piirtaa sen uudelleen kun sailion leveys muuttuu.
 * Palauttaa funktion joka pakottaa uudelleenpiirron, esimerkiksi valitsimen jalkeen.
 */
export function mountResponsive(host: HTMLElement, render: Renderer, options: MountOptions): () => void {
  const minWidth = options.minWidth ?? 280;
  let lastWidth = 0;
  let frame = 0;

  const draw = (): void => {
    const width = Math.max(minWidth, Math.floor(host.clientWidth || host.getBoundingClientRect().width || 640));
    lastWidth = width;
    const figure = render(width);
    labelChart(figure, options.ariaLabel);
    host.replaceChildren(figure);
  };

  const schedule = (): void => {
    if (frame !== 0) cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      frame = 0;
      draw();
    });
  };

  draw();

  if (typeof ResizeObserver !== 'undefined') {
    const observer = new ResizeObserver(() => {
      const width = Math.floor(host.clientWidth);
      if (Math.abs(width - lastWidth) < 8) return;
      schedule();
    });
    observer.observe(host);
  }

  return schedule;
}

/**
 * Nimeaa kaavion ruudunlukijalle ja siivoaa Plotin merkintaryhmien aria-labelit.
 *
 * Plot merkitsee jokaisen mark-ryhman `<g aria-label="dot">` -tyyliin. Yleisella
 * `g`-elementilla ei ole roolia, joten aria-label on siina kiellettya ja se aanestyy
 * lapi kohinana. Kaaviolla on oma nimi ja jokaisella kaaviolla tekstivastine, joten
 * sisaisten ryhmien nimeaminen ei tuo mitaan.
 */
function labelChart(figure: SVGSVGElement | HTMLElement, ariaLabel: string): void {
  const svg = figure instanceof SVGSVGElement ? figure : figure.querySelector('svg');
  if (svg) {
    svg.setAttribute('role', 'img');
    svg.setAttribute('aria-label', ariaLabel);
  } else {
    figure.setAttribute('role', 'img');
    figure.setAttribute('aria-label', ariaLabel);
  }
  for (const group of figure.querySelectorAll('g[aria-label]')) {
    group.removeAttribute('aria-label');
  }
}

export interface ToggleOption<T extends string> {
  value: T;
  label: string;
  /** Ruudunlukijalle, jos nakyva teksti on lyhenne. */
  description?: string;
}

/**
 * Painikeryhma valitsimille. Natiivit painikkeet toimivat nappaimistolla sellaisenaan,
 * ja valinta elaa muistissa: sivu toimii ilman localStoragea.
 */
export function createToggleGroup<T extends string>(
  legend: string,
  options: ToggleOption<T>[],
  initial: T,
  onChange: (value: T) => void,
): { element: HTMLElement; value: () => T } {
  let current = initial;

  const group = document.createElement('div');
  group.className = 'flex flex-wrap items-center gap-2';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', legend);

  const label = document.createElement('span');
  label.className = 'text-xs font-medium text-ink-muted';
  label.textContent = legend;
  group.append(label);

  const buttons: HTMLButtonElement[] = [];
  for (const option of options) {
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.value = option.value;
    button.textContent = option.label;
    if (option.description) button.setAttribute('aria-label', option.description);
    button.className =
      'rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ' +
      'aria-pressed:border-series-1 aria-pressed:bg-series-1 aria-pressed:text-white ' +
      'border-line bg-white text-ink hover:border-ink-muted';
    button.setAttribute('aria-pressed', String(option.value === current));
    button.addEventListener('click', () => {
      if (current === option.value) return;
      current = option.value;
      for (const other of buttons) other.setAttribute('aria-pressed', String(other.dataset.value === current));
      onChange(current);
    });
    buttons.push(button);
    group.append(button);
  }

  return { element: group, value: () => current };
}

/** Selite jonka Plot ei osaa piirtaa: vari, viivatyyli ja teksti. */
export interface LegendEntry {
  label: string;
  color: string;
  dash?: string | null;
  /** Pintaselite viivan sijaan. */
  swatch?: boolean;
  note?: string;
}

export function createLegend(entries: LegendEntry[]): HTMLElement {
  const list = document.createElement('ul');
  list.className = 'mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-ink-muted';
  for (const entry of entries) {
    const item = document.createElement('li');
    item.className = 'flex items-center gap-1.5';
    const mark = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    mark.setAttribute('width', '22');
    mark.setAttribute('height', '12');
    mark.setAttribute('aria-hidden', 'true');
    mark.classList.add('shrink-0');
    if (entry.swatch) {
      const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
      rect.setAttribute('x', '1');
      rect.setAttribute('y', '2');
      rect.setAttribute('width', '20');
      rect.setAttribute('height', '8');
      rect.setAttribute('fill', entry.color);
      rect.setAttribute('stroke', NEUTRAL.line);
      mark.append(rect);
    } else {
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', '1');
      line.setAttribute('y1', '6');
      line.setAttribute('x2', '21');
      line.setAttribute('y2', '6');
      line.setAttribute('stroke', entry.color);
      line.setAttribute('stroke-width', '2.5');
      if (entry.dash) line.setAttribute('stroke-dasharray', entry.dash);
      mark.append(line);
    }
    item.append(mark);
    const text = document.createElement('span');
    text.textContent = entry.note ? `${entry.label} (${entry.note})` : entry.label;
    item.append(text);
    list.append(item);
  }
  return list;
}

/** Kaaviosaarekkeen runko: valitsimet, piirtoalue ja selite. */
export function createChartFrame(element: HTMLElement): {
  controls: HTMLElement;
  plot: HTMLElement;
  legend: HTMLElement;
} {
  const controls = document.createElement('div');
  controls.className = 'mb-3 flex flex-wrap items-center gap-3';

  const plot = document.createElement('div');
  plot.className = 'plot-host w-full';

  const legend = document.createElement('div');

  element.append(controls, plot, legend);
  return { controls, plot, legend };
}
