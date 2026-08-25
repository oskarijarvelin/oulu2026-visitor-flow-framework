/**
 * Piste ja vali -kuvaaja: ero vertailukohtaan seka ennustevalien peittavyys.
 *
 * Molemmissa luetaan sama asia: osuuko viitearvo valin sisaan. Erossa viitearvo on
 * nolla ja verdikti luetaan siita suoraan; peittavyydessa se on tavoite 0,80.
 * Rivin verdikti nakyy varin lisaksi merkkina, joten kuva toimii harmaasavyisena.
 */

import { chartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, SERIES } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
import { currentRun, onRunChange } from '../lib/runstate.ts';
import { island } from '../renderer/index.ts';
import { Plot, baseOptions, createChartFrame, mountResponsive } from './base.ts';

export interface AccuracyIntervalRow {
  label: string;
  value: number;
  low: number;
  high: number;
  color: string;
  /** Verdiktin merkki, esimerkiksi kolmio. Vari ei kanna tietoa yksin. */
  mark: string;
  /** Kooste piirretaan paksummalla, koska se on koko kuvan paatulos. */
  emphasis?: boolean;
  tip: string;
}

export interface AccuracyIntervalsPayload {
  rows: AccuracyIntervalRow[];
  /** Korostettu viitearvo: nolla erossa, 0,80 peittavyydessa. */
  reference: number;
  referenceLabel: string;
  /** Kuinka monella desimaalilla arvot esitetaan. */
  decimals: number;
}

export interface AccuracyIntervalsProps {
  lang: Lang;
  ariaLabel: string;
  defaultRun: string;
  runs: Record<string, AccuracyIntervalsPayload | null>;
  missingLabel: string;
  axisLabel: string;
  [key: string]: unknown;
}

export default island<AccuracyIntervalsProps>((element, props) => {
  const frame = createChartFrame(element);
  frame.controls.remove();
  frame.legend.remove();

  let run = currentRun(props.defaultRun);
  const redraw = mountResponsive(frame.plot, (width) => draw(width, props, run), {
    ariaLabel: props.ariaLabel,
  });

  onRunChange((next) => {
    if (next === run) return;
    run = next;
    redraw();
  });
});

function draw(width: number, props: AccuracyIntervalsProps, run: string): SVGSVGElement | HTMLElement {
  const payload = props.runs[run];
  if (!payload || payload.rows.length === 0) {
    const element = document.createElement('p');
    element.className = 'rounded-md border border-line bg-canvas px-4 py-6 text-sm leading-6 text-ink-muted';
    element.textContent = props.missingLabel;
    return element;
  }

  const f = formatters(props.lang);
  const strings = chartStrings(props.lang);
  const rows = payload.rows;
  const height = Math.max(150, rows.length * 34 + 74);
  const labels = rows.map((row) => row.label);
  const marks: Plot.Markish[] = [
    Plot.ruleX([payload.reference], { stroke: NEUTRAL.ink, strokeWidth: 1.6 }),
    Plot.ruleY(rows, {
      y: 'label',
      x1: 'low',
      x2: 'high',
      stroke: (row: AccuracyIntervalRow) => row.color,
      strokeWidth: (row: AccuracyIntervalRow) => (row.emphasis === true ? 4 : 2.4),
      strokeLinecap: 'round',
    }),
    // Valin paat omina merkkeinaan: ohut viiva yksin katoaa tulostettuna.
    Plot.tickX(rows, { y: 'label', x: 'low', stroke: (row: AccuracyIntervalRow) => row.color, strokeWidth: 1.4 }),
    Plot.tickX(rows, { y: 'label', x: 'high', stroke: (row: AccuracyIntervalRow) => row.color, strokeWidth: 1.4 }),
    Plot.dot(rows, {
      y: 'label',
      x: 'value',
      fill: (row: AccuracyIntervalRow) => row.color,
      r: (row: AccuracyIntervalRow) => (row.emphasis === true ? 6 : 4.5),
      title: (row: AccuracyIntervalRow) => row.tip,
      tip: true,
    }),
    Plot.text(rows, {
      y: 'label',
      x: 'high',
      text: (row: AccuracyIntervalRow) => `${row.mark} ${f.decimal(row.value, payload.decimals)}`,
      textAnchor: 'start',
      dx: 8,
      fontSize: 11,
      fill: NEUTRAL.muted,
    }),
    Plot.text([{ x: payload.reference, label: payload.referenceLabel }], {
      x: 'x',
      text: 'label',
      frameAnchor: 'top',
      dy: -6,
      dx: 4,
      textAnchor: 'start',
      fontSize: 11,
      fill: NEUTRAL.ink,
    }),
  ];

  return Plot.plot({
    ...baseOptions(width, height),
    marginTop: 26,
    marginBottom: 44,
    marginLeft: Math.min(190, Math.max(78, width * 0.3)),
    marginRight: Math.min(84, Math.max(48, width * 0.16)),
    x: {
      label: props.axisLabel,
      labelAnchor: 'center',
      labelOffset: 36,
      grid: true,
      tickFormat: (value: number) => f.decimal(value, payload.decimals === 3 ? 2 : 0),
      nice: true,
    },
    y: { label: null, domain: labels },
    // Selite luetaan riviteksteista; erillinen varilegenda toistaisi saman tiedon.
    color: { domain: [strings.accuracyZero], range: [SERIES.history] },
    marks,
  });
}
