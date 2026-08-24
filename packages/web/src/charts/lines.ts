/**
 * Monisarjainen viivakaavio numeeriselle tai paivamaara-akselille. Kaytetaan MAE:n
 * horisonttikayriin, lippujen ja kavijoiden vertailuun seka kontekstidataan.
 */

import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, SERIES } from '../lib/colors.ts';
import { plotDay } from '../lib/dates.ts';
import { formatters } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  baseOptions,
  chartFormat,
  createChartFrame,
  createLegend,
  mountResponsive,
  type LegendEntry,
} from './base.ts';

export interface LineSeries {
  name: string;
  color: string;
  dash?: string | null;
  note?: string;
  points: { x: number | string; y: number }[];
}

export interface LinesProps {
  lang: Lang;
  ariaLabel: string;
  series: LineSeries[];
  /** 'number' piirtaa numeerisen akselin, 'date' odottaa "YYYY-MM-DD"-merkkijonoja. */
  xType: 'number' | 'date';
  xLabel?: string;
  unit?: string;
  showPoints?: boolean;
  /** Vaakasuora viitearvo, esimerkiksi kapasiteetti. */
  reference?: { value: number; label: string } | null;
  [key: string]: unknown;
}

interface Point {
  x: number | Date;
  y: number;
  name: string;
}

export default island<LinesProps>((element, props) => {
  const frame = createChartFrame(element);
  frame.controls.remove();

  const entries: LegendEntry[] = props.series.map((series) => ({
    label: series.name,
    color: series.color,
    dash: series.dash ?? null,
    note: series.note,
  }));
  if (props.reference) {
    entries.push({ label: props.reference.label, color: SERIES.forecast, dash: '5 4' });
  }
  frame.legend.append(createLegend(entries));

  mountResponsive(frame.plot, (width) => draw(width, props), { ariaLabel: props.ariaLabel });
});

function draw(width: number, props: LinesProps): SVGSVGElement | HTMLElement {
  const f = formatters(props.lang);
  const format = chartFormat(props.lang);
  const height = Math.max(200, Math.min(340, Math.round(width * 0.4)));
  const unit = props.unit ?? '';
  const isDate = props.xType === 'date';

  const marks: Plot.Markish[] = [Plot.ruleY([0], { stroke: NEUTRAL.line })];

  if (props.reference) {
    const reference = props.reference;
    marks.push(
      Plot.ruleY([reference.value], {
        stroke: SERIES.forecast,
        strokeWidth: 1.6,
        strokeDasharray: '5 4',
      }),
      Plot.text([reference], {
        y: 'value',
        text: 'label',
        frameAnchor: 'right',
        dy: -8,
        dx: -4,
        fontSize: 11,
        fill: SERIES.forecast,
      }),
    );
  }

  for (const series of props.series) {
    const points: Point[] = series.points.map((point) => ({
      x: isDate ? plotDay(String(point.x)) : Number(point.x),
      y: point.y,
      name: series.name,
    }));
    marks.push(
      Plot.line(points, {
        x: 'x',
        y: 'y',
        stroke: series.color,
        strokeWidth: 2,
        strokeDasharray: series.dash ?? undefined,
        curve: 'linear',
      }),
    );
    if (props.showPoints !== false && points.length <= 40) {
      marks.push(
        Plot.dot(points, {
          x: 'x',
          y: 'y',
          fill: series.color,
          r: 2.6,
          title: (point: Point) =>
            `${series.name}\n${point.x instanceof Date ? format.titleDate(point.x) : f.int(point.x)}\n` +
            `${f.decimal(point.y)} ${unit}`.trim(),
          tip: true,
        }),
      );
    }
  }

  return Plot.plot({
    ...baseOptions(width, height),
    marginBottom: props.xLabel ? 44 : 34,
    x: isDate
      ? { type: 'utc', label: props.xLabel ?? null, labelOffset: 36, tickFormat: format.tickDay, grid: false }
      : {
          label: props.xLabel ?? null,
          labelAnchor: 'center',
          labelOffset: 36,
          tickFormat: (value: number) => f.int(value),
          grid: true,
        },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    marks,
  });
}
