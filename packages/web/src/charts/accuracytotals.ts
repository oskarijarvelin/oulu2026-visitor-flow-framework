/**
 * Jakson kokonaismaara: ennuste ja toteuma pylvaina, ennusteen simuloitu 80 prosentin
 * vali pylvaan paalla.
 *
 * Vali on simuloitu koulutusikkunan sisaisesta backtestista, ei summattu paivien
 * valeista. Kun ajo on merkinnyt sen kalibroimattomaksi, se piirretaan katkoviivana ja
 * merkitaan vihjeessa; silloin luetaan ero ja harha, ei valia.
 */

import { chartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, SERIES } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
import { currentRun, onRunChange } from '../lib/runstate.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  baseOptions,
  chartFormat,
  createChartFrame,
  createLegend,
  mountResponsive,
} from './base.ts';

export interface AccuracyTotalRow {
  label: string;
  predicted: number;
  actual: number;
  p10: number;
  p90: number;
  /** `is_thin` tai `is_drifted`: valia ei pida lukea. */
  unreliable: boolean;
  differencePct: string;
}

export interface AccuracyTotalsPayload {
  rows: AccuracyTotalRow[];
}

export interface AccuracyTotalsProps {
  lang: Lang;
  ariaLabel: string;
  defaultRun: string;
  runs: Record<string, AccuracyTotalsPayload | null>;
  missingLabel: string;
  forecastLabel: string;
  actualLabel: string;
  intervalLabel: string;
  [key: string]: unknown;
}

interface Bar {
  label: string;
  group: 'forecast' | 'actual';
  value: number;
  row: AccuracyTotalRow;
}

export default island<AccuracyTotalsProps>((element, props) => {
  const frame = createChartFrame(element);
  frame.controls.remove();

  let run = currentRun(props.defaultRun);
  frame.legend.append(
    createLegend([
      { label: props.forecastLabel, color: SERIES.forecast, swatch: true },
      { label: props.actualLabel, color: SERIES.history, swatch: true },
      { label: props.intervalLabel, color: NEUTRAL.ink },
    ]),
  );

  const redraw = mountResponsive(frame.plot, (width) => draw(width, props, run), {
    ariaLabel: props.ariaLabel,
  });

  onRunChange((next) => {
    if (next === run) return;
    run = next;
    redraw();
  });
});

function draw(width: number, props: AccuracyTotalsProps, run: string): SVGSVGElement | HTMLElement {
  const payload = props.runs[run];
  if (!payload || payload.rows.length === 0) {
    const element = document.createElement('p');
    element.className = 'rounded-md border border-line bg-canvas px-4 py-6 text-sm leading-6 text-ink-muted';
    element.textContent = props.missingLabel;
    return element;
  }

  const f = formatters(props.lang);
  const strings = chartStrings(props.lang);
  const format = chartFormat(props.lang);
  const rows = payload.rows;
  const height = Math.max(230, Math.min(360, Math.round(width * 0.44)));
  const labels = rows.map((row) => row.label);

  const bars: Bar[] = rows.flatMap((row) => [
    { label: row.label, group: 'forecast' as const, value: row.predicted, row },
    { label: row.label, group: 'actual' as const, value: row.actual, row },
  ]);

  const title = (bar: Bar): string =>
    `${bar.label}\n${strings.accuracyTotalTip(f.int(bar.row.predicted), f.int(bar.row.actual))}\n` +
    `${bar.row.differencePct}\n${props.intervalLabel} ${f.int(bar.row.p10)} - ${f.int(bar.row.p90)}` +
    (bar.row.unreliable ? `\n${strings.accuracyIntervalUnreliable}` : '');

  const shared = { fx: 'label', x: 'group', y: 'value' } as const;
  const marks: Plot.Markish[] = [
    Plot.barY(bars, {
      ...shared,
      fill: (bar: Bar) => (bar.group === 'forecast' ? SERIES.forecast : SERIES.history),
      title,
      tip: true,
    }),
    Plot.barY(bars, { ...shared, fill: 'none', stroke: NEUTRAL.line, strokeWidth: 0.6 }),
    // Vali piirretaan vain ennusteen pylvaan paalle: toteumalla ei ole valia.
    // Kalibroimaton vali piirretaan katkoviivana, jotta se erottuu myos ilman vihjetta.
    Plot.ruleX(rows.filter((row) => !row.unreliable), {
      fx: 'label',
      x: () => 'forecast',
      y1: 'p10',
      y2: 'p90',
      stroke: NEUTRAL.ink,
      strokeWidth: 1.6,
    }),
    Plot.ruleX(rows.filter((row) => row.unreliable), {
      fx: 'label',
      x: () => 'forecast',
      y1: 'p10',
      y2: 'p90',
      stroke: NEUTRAL.ink,
      strokeWidth: 1.6,
      strokeDasharray: '3 3',
    }),
    Plot.tickY(rows, { fx: 'label', x: () => 'forecast', y: 'p10', stroke: NEUTRAL.ink, strokeWidth: 1.6 }),
    Plot.tickY(rows, { fx: 'label', x: () => 'forecast', y: 'p90', stroke: NEUTRAL.ink, strokeWidth: 1.6 }),
    Plot.ruleY([0], { stroke: NEUTRAL.line }),
  ];

  return Plot.plot({
    ...baseOptions(width, height),
    marginBottom: labels.some((label) => label.length > 12) ? 52 : 34,
    fx: {
      label: null,
      domain: labels,
      padding: width < 480 ? 0.12 : 0.2,
      tickRotate: labels.some((label) => label.length > 12) ? -20 : 0,
    },
    x: { axis: null, domain: ['forecast', 'actual'] },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    marks,
  });
}
