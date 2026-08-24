/**
 * Viikonpaiva x tunti -lampokartta. Rivit ma-su, sarakkeet 0-23, arvo keskimaarainen
 * `visitors_total`.
 *
 * Nolla ja puuttuva erotetaan toisistaan: nolla saa skaalan vaaleimman savyn, puuttuva
 * ruutu piirretaan harmaana viivoituksena. Ero nakyy myos harmaasavyisena.
 */

import { chartStrings, type ChartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { MISSING_FILL, NEUTRAL } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import type { ProfileCell } from '../lib/types.ts';
import { Plot, createChartFrame, createLegend, createToggleGroup, mountResponsive } from './base.ts';

export interface HeatmapProps {
  lang: Lang;
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
  const strings = chartStrings(props.lang);
  const frame = createChartFrame(element);
  frame.plot.classList.add('overflow-x-auto');
  let metric: Metric = 'mean';

  let redraw = (): void => {};
  const toggle = createToggleGroup<Metric>(
    strings.metricLabel,
    [
      { value: 'mean', label: strings.mean },
      { value: 'median', label: strings.median },
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
      { label: strings.noObservations, color: MISSING_FILL, swatch: true },
      { label: strings.zeroEvents, color: '#ffffd9', swatch: true },
    ]),
  );

  const note = document.createElement('p');
  note.className = 'mt-2 text-xs text-ink-muted';
  note.textContent = strings.heatmapNote;
  frame.legend.append(note);

  redraw = mountResponsive(
    frame.plot,
    (width) => draw(Math.max(width, MIN_PLOT_WIDTH), props.cells, metric, props.lang, strings),
    { ariaLabel: props.ariaLabel, minWidth: MIN_PLOT_WIDTH },
  );
});

function draw(
  width: number,
  source: ProfileCell[],
  metric: Metric,
  lang: Lang,
  strings: ChartStrings,
): SVGSVGElement | HTMLElement {
  const f = formatters(lang);
  const weekdays = f.weekdaysShort();
  const cells: Cell[] = source.map((cell) => ({
    ...cell,
    day: weekdays[cell.dow] ?? String(cell.dow),
    value: cell.n === 0 ? null : (metric === 'mean' ? cell.mean : cell.median),
  }));
  const present = cells.filter((cell) => cell.value !== null);
  const missing = cells.filter((cell) => cell.value === null);
  const maxValue = present.length === 0 ? 1 : Math.max(1, ...present.map((cell) => cell.value ?? 0));

  const height = 260;
  const metricLabel = metric === 'mean' ? strings.mean : strings.median;

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
      label: strings.heatmapAxis,
      labelAnchor: 'center',
      labelOffset: 30,
      tickFormat: (hour: number) => String(hour).padStart(2, '0'),
      ticks: 24,
    },
    y: {
      domain: [...weekdays],
      label: null,
    },
    // `width` ja `marginLeft` ovat Plotin selitteen asetuksia. Ne toimivat ajossa mutta
    // puuttuvat kirjaston ScaleOptions-tyypista, joten tyyppi vahvistetaan tassa.
    color: {
      type: 'linear',
      scheme: 'ylgnbu',
      domain: [0, maxValue],
      legend: true,
      label: strings.heatmapColorLabel(metricLabel),
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
        title: (cell: Cell) =>
          `${strings.heatmapCellTip(cell.day, hourLabel(cell.hour))}\n${strings.heatmapMissingTip}`,
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
          `${strings.heatmapCellTip(cell.day, hourLabel(cell.hour))}\n` +
          `${strings.heatmapValueTip(metricLabel, f.decimal(cell.value ?? 0))}\n` +
          `${strings.heatmapCountTip(cell.n, cell.n_zero)}`,
        tip: true,
      }),
    ],
  });
}

function hourLabel(hour: number): string {
  return `${String(hour).padStart(2, '0')}:00`;
}
