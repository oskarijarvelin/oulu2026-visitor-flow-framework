/**
 * Viikonpaiva x tunti -lampokartta. Rivit ma-su, sarakkeet 0-23, arvo keskimaarainen
 * `visitors_total`.
 *
 * Nolla ja puuttuva erotetaan toisistaan: nolla saa skaalan vaaleimman savyn, puuttuva
 * ruutu piirretaan harmaana viivoituksena. Ero nakyy myos harmaasavyisena.
 */

import { MISSING_FILL, NEUTRAL } from '../lib/colors.ts';
import { formatDecimal } from '../lib/format.ts';
import { WEEKDAYS_SHORT } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import type { ProfileCell } from '../lib/types.ts';
import { Plot, createChartFrame, createLegend, createToggleGroup, mountResponsive } from './base.ts';

export interface HeatmapProps {
  ariaLabel: string;
  cells: ProfileCell[];
  openHours: number[];
  [key: string]: unknown;
}

type Metric = 'mean' | 'median';

interface Cell extends ProfileCell {
  day: string;
  value: number | null;
}

/** Lampokartta tarvitsee vahintaan taman leveyden, jotta 24 saraketta pysyy luettavana. */
const MIN_PLOT_WIDTH = 620;

export default island<HeatmapProps>((element, props) => {
  const frame = createChartFrame(element);
  frame.plot.classList.add('overflow-x-auto');
  let metric: Metric = 'mean';

  let redraw = (): void => {};
  const toggle = createToggleGroup<Metric>(
    'Tunnusluku',
    [
      { value: 'mean', label: 'Keskiarvo' },
      { value: 'median', label: 'Mediaani' },
    ],
    metric,
    (value) => {
      metric = value;
      redraw();
    },
  );
  frame.controls.append(toggle.element);

  frame.legend.append(
    createLegend([
      { label: 'Ei havaintoja', color: MISSING_FILL, swatch: true },
      { label: 'Nolla kävijätapahtumaa', color: '#ffffd9', swatch: true },
    ]),
  );

  const note = document.createElement('p');
  note.className = 'mt-2 text-xs text-ink-muted';
  note.textContent =
    'Väriskaala on vaaleasta tummaan ja säilyttää järjestyksensä myös harmaasävyisenä. ' +
    'Aukioloaikojen ulkopuoliset tunnit näkyvät vaaleina, koska niissä on aitoja nollia.';
  frame.legend.append(note);

  redraw = mountResponsive(
    frame.plot,
    (width) => draw(Math.max(width, MIN_PLOT_WIDTH), props.cells, metric),
    { ariaLabel: props.ariaLabel, minWidth: MIN_PLOT_WIDTH },
  );
});

function draw(width: number, source: ProfileCell[], metric: Metric): SVGSVGElement | HTMLElement {
  const cells: Cell[] = source.map((cell) => ({
    ...cell,
    day: WEEKDAYS_SHORT[cell.dow] ?? String(cell.dow),
    value: cell.n === 0 ? null : (metric === 'mean' ? cell.mean : cell.median),
  }));
  const present = cells.filter((cell) => cell.value !== null);
  const missing = cells.filter((cell) => cell.value === null);
  const maxValue = present.length === 0 ? 1 : Math.max(1, ...present.map((cell) => cell.value ?? 0));

  const height = 260;
  const metricLabel = metric === 'mean' ? 'Keskiarvo' : 'Mediaani';

  return Plot.plot({
    width,
    height,
    marginLeft: 40,
    marginRight: 12,
    marginTop: 28,
    marginBottom: 34,
    padding: 0,
    style: { background: 'transparent', color: NEUTRAL.ink, fontSize: '11px' },
    x: {
      domain: Array.from({ length: 24 }, (_, hour) => hour),
      label: 'Tunti, Suomen aikaa',
      labelAnchor: 'center',
      labelOffset: 30,
      tickFormat: (hour: number) => String(hour).padStart(2, '0'),
      ticks: 24,
    },
    y: {
      domain: [...WEEKDAYS_SHORT],
      label: null,
    },
    // `width` ja `marginLeft` ovat Plotin selitteen asetuksia. Ne toimivat ajossa mutta
    // puuttuvat kirjaston ScaleOptions-tyypista, joten tyyppi vahvistetaan tassa.
    color: {
      type: 'linear',
      scheme: 'ylgnbu',
      domain: [0, maxValue],
      legend: true,
      label: `${metricLabel}, kävijätapahtumaa tunnissa`,
      width: Math.min(width, 320),
      marginLeft: 10,
    } as Plot.ScaleOptions,
    marks: [
      Plot.cell(missing, {
        x: 'hour',
        y: 'day',
        fill: MISSING_FILL,
        stroke: '#ffffff',
        strokeWidth: 1,
        title: (cell: Cell) => `${cell.day} klo ${String(cell.hour).padStart(2, '0')}:00\nEi havaintoja`,
        tip: true,
      }),
      Plot.text(missing, {
        x: 'hour',
        y: 'day',
        text: () => '×',
        fill: NEUTRAL.muted,
        fontSize: 9,
      }),
      Plot.cell(present, {
        x: 'hour',
        y: 'day',
        fill: 'value',
        stroke: '#ffffff',
        strokeWidth: 1,
        title: (cell: Cell) =>
          `${cell.day} klo ${String(cell.hour).padStart(2, '0')}:00\n` +
          `${metricLabel} ${formatDecimal(cell.value ?? 0)} kävijätapahtumaa\n` +
          `${cell.n} havaintoa, joista ${cell.n_zero} nollaa`,
        tip: true,
      }),
    ],
  });
}
