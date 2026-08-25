/**
 * Ryhmitelty pylvaskaavio arviointisivulle: virhe horisonttikoreittain ja sään kolme
 * tilaa. Molemmat ovat sama kuvio, yksi lokero per luokka ja lokeron sisalla yksi
 * pylvas per ryhma, joten ne jakavat saman saarekkeen.
 *
 * Ryhma erottuu varin lisaksi viivoituksella ja selitteesta, joten kuva toimii myos
 * harmaasavyisena.
 */

import type { Lang } from '../i18n/index.ts';
import { NEUTRAL } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
import { currentRun, onRunChange } from '../lib/runstate.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  appendHatchPattern,
  baseOptions,
  chartFormat,
  createChartFrame,
  createLegend,
  mountResponsive,
  nextHatchId,
  type LegendEntry,
} from './base.ts';

export interface AccuracyBar {
  /** Ulompi lokero, esimerkiksi horisonttikori tai ikkuna. */
  label: string;
  /** Ryhman avain lokeron sisalla, esimerkiksi malli tai sään tila. */
  group: string;
  value: number;
  n?: number;
  note?: string;
}

export interface AccuracyBarGroup {
  key: string;
  label: string;
  color: string;
  hatch?: boolean;
}

export interface AccuracyBarsPayload {
  bars: AccuracyBar[];
  groups: AccuracyBarGroup[];
}

export interface AccuracyBarsProps {
  lang: Lang;
  ariaLabel: string;
  defaultRun: string;
  runs: Record<string, AccuracyBarsPayload | null>;
  missingLabel: string;
  /** Pystyakselin selite vihjeessa, esimerkiksi MAE. */
  valueLabel: string;
  [key: string]: unknown;
}

export default island<AccuracyBarsProps>((element, props) => {
  const frame = createChartFrame(element);
  frame.controls.remove();
  const hatchId = nextHatchId();

  let run = currentRun(props.defaultRun);
  let redraw = (): void => {};

  const renderLegend = (): void => {
    const payload = props.runs[run];
    const entries: LegendEntry[] = (payload?.groups ?? []).map((group) => ({
      label: group.label,
      color: group.color,
      swatch: true,
      hatch: group.hatch === true,
    }));
    frame.legend.replaceChildren(entries.length === 0 ? document.createDocumentFragment() : createLegend(entries));
  };

  renderLegend();
  redraw = mountResponsive(frame.plot, (width) => draw(width, props, run, hatchId), {
    ariaLabel: props.ariaLabel,
  });

  onRunChange((next) => {
    if (next === run) return;
    run = next;
    renderLegend();
    redraw();
  });
});

function draw(
  width: number,
  props: AccuracyBarsProps,
  run: string,
  hatchId: string,
): SVGSVGElement | HTMLElement {
  const payload = props.runs[run];
  if (!payload || payload.bars.length === 0) {
    const element = document.createElement('p');
    element.className = 'rounded-md border border-line bg-canvas px-4 py-6 text-sm leading-6 text-ink-muted';
    element.textContent = props.missingLabel;
    return element;
  }

  const f = formatters(props.lang);
  const format = chartFormat(props.lang);
  const labels = [...new Set(payload.bars.map((bar) => bar.label))];
  const keys = payload.groups.map((group) => group.key);
  const height = Math.max(230, Math.min(360, Math.round(width * 0.44)));
  const colorOf = (key: string): string =>
    payload.groups.find((group) => group.key === key)?.color ?? NEUTRAL.line;
  const labelOf = (key: string): string =>
    payload.groups.find((group) => group.key === key)?.label ?? key;
  const hatched = payload.bars.filter(
    (bar) => payload.groups.find((group) => group.key === bar.group)?.hatch === true,
  );

  const shared = { fx: 'label', x: 'group', y: 'value' } as const;
  const title = (bar: AccuracyBar): string =>
    `${labelOf(bar.group)}\n${bar.label}\n${props.valueLabel} ${f.decimal(bar.value)}` +
    (bar.n === undefined ? '' : `\n${f.int(bar.n)} d`) +
    (bar.note ? `\n${bar.note}` : '');

  const marks: Plot.Markish[] = [
    Plot.barY(payload.bars, { ...shared, fill: (bar: AccuracyBar) => colorOf(bar.group), title, tip: true }),
  ];
  if (hatched.length > 0) marks.push(Plot.barY(hatched, { ...shared, fill: `url(#${hatchId})` }));
  marks.push(
    Plot.barY(payload.bars, { ...shared, fill: 'none', stroke: NEUTRAL.line, strokeWidth: 0.6 }),
    Plot.ruleY([0], { stroke: NEUTRAL.line }),
  );

  const figure = Plot.plot({
    ...baseOptions(width, height),
    marginBottom: labels.some((label) => label.length > 12) ? 52 : 34,
    fx: {
      label: null,
      domain: labels,
      padding: width < 480 ? 0.12 : 0.2,
      tickRotate: labels.some((label) => label.length > 12) ? -20 : 0,
    },
    x: { axis: null, domain: keys },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    color: { domain: keys, range: payload.groups.map((group) => group.color) },
    marks,
  });

  if (hatched.length > 0) appendHatchPattern(figure, hatchId);
  return figure;
}
