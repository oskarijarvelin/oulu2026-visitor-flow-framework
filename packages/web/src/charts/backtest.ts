/**
 * Backtest: ennuste vs. toteuma. x on ennusteen mediaani, y toteuma, ja lavistaja on
 * taydellinen osuma. Pisteet varjataan horisonttikorin mukaan ja valin ulkopuolelle
 * jaaneet merkitaan omalla symbolilla.
 */

import { chartStrings, type ChartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, SERIES } from '../lib/colors.ts';
import { addDays } from '../lib/dates.ts';
import { formatters } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import { Plot, baseOptions, chartFormat, createChartFrame, createToggleGroup, mountResponsive } from './base.ts';

export interface BacktestPoint {
  model: string;
  origin_date: string;
  horizon_days: number;
  y_true: number;
  y_pred: number;
  p10: number;
  p90: number;
}

export interface BacktestProps {
  lang: Lang;
  ariaLabel: string;
  points: BacktestPoint[];
  models: { name: string; label: string }[];
  defaultModel: string;
  buckets: string[];
  [key: string]: unknown;
}

interface Point extends BacktestPoint {
  bucket: string;
  covered: boolean;
}

const BUCKET_COLOR: Record<string, string> = {
  '1-7': '#0072b2',
  '8-14': '#009e73',
  '15-30': '#d55e00',
};

const BUCKET_SYMBOL: Record<string, string> = {
  '1-7': 'circle',
  '8-14': 'square',
  '15-30': 'triangle',
};

export default island<BacktestProps>((element, props) => {
  const strings = chartStrings(props.lang);
  const f = formatters(props.lang);
  const frame = createChartFrame(element);
  let selected = props.defaultModel;

  let redraw = (): void => {};
  const toggle = createToggleGroup(
    strings.modelLabel,
    props.models.map((model) => ({ value: model.name, label: model.label })),
    selected,
    (value) => {
      selected = value;
      redraw();
      updateNote();
    },
  );
  frame.controls.append(toggle.element);

  const note = document.createElement('p');
  note.className = 'mt-3 text-xs leading-5 text-ink-muted';
  frame.legend.append(note);

  const updateNote = (): void => {
    const points = enrich(props.points.filter((point) => point.model === selected), props.buckets);
    const covered = points.filter((point) => point.covered).length;
    const share = points.length === 0 ? 0 : Math.round((covered / points.length) * 100);
    note.textContent = strings.backtestNote(f.int(points.length), share);
  };
  updateNote();

  redraw = mountResponsive(
    frame.plot,
    (width) =>
      draw(
        width,
        enrich(props.points.filter((point) => point.model === selected), props.buckets),
        props.lang,
        strings,
      ),
    { ariaLabel: props.ariaLabel },
  );
});

function bucketOf(horizon: number, buckets: string[]): string {
  for (const bucket of buckets) {
    const [from, to] = bucket.split('-').map(Number);
    if (from !== undefined && to !== undefined && horizon >= from && horizon <= to) return bucket;
  }
  return buckets.at(-1) ?? '';
}

function enrich(points: BacktestPoint[], buckets: string[]): Point[] {
  return points.map((point) => ({
    ...point,
    bucket: bucketOf(point.horizon_days, buckets),
    covered: point.y_true >= point.p10 && point.y_true <= point.p90,
  }));
}

function draw(
  width: number,
  points: Point[],
  lang: Lang,
  strings: ChartStrings,
): SVGSVGElement | HTMLElement {
  const f = formatters(lang);
  const format = chartFormat(lang);
  const size = Math.max(240, Math.min(420, Math.round(width * 0.6)));
  const values = points.flatMap((point) => [point.y_true, point.y_pred]);
  const max = values.length === 0 ? 100 : Math.max(...values) * 1.05;
  // Korit jarjestetaan horisontin mukaan, ei merkkijonona: "15-30" ei kuulu "1-7":n ja
  // "8-14":n valiin.
  const buckets = [...new Set(points.map((point) => point.bucket))].sort(
    (a, b) => Number(a.split('-')[0]) - Number(b.split('-')[0]),
  );

  const inside = points.filter((point) => point.covered);
  const outside = points.filter((point) => !point.covered);

  const title = (point: Point): string =>
    strings.backtestTip(
      f.date(point.origin_date),
      point.horizon_days,
      f.date(addDays(point.origin_date, point.horizon_days)),
      f.int(point.y_pred),
      f.int(point.y_true),
      f.int(point.p10),
      f.int(point.p90),
    ) + (point.covered ? '' : `\n${strings.backtestOutside}`);

  return Plot.plot({
    ...baseOptions(width, size),
    marginBottom: 44,
    aspectRatio: undefined,
    x: {
      label: strings.backtestAxis,
      labelAnchor: 'center',
      labelOffset: 36,
      domain: [0, max],
      tickFormat: format.count,
      grid: true,
    },
    y: { label: null, domain: [0, max], tickFormat: format.count, grid: true },
    color: {
      domain: buckets,
      range: buckets.map((bucket) => BUCKET_COLOR[bucket] ?? SERIES.light),
      legend: true,
      label: strings.backtestBucketLabel,
    },
    symbol: {
      domain: buckets,
      range: buckets.map((bucket) => BUCKET_SYMBOL[bucket] ?? 'circle'),
    },
    marks: [
      Plot.line(
        [
          { x: 0, y: 0 },
          { x: max, y: max },
        ],
        { x: 'x', y: 'y', stroke: NEUTRAL.muted, strokeDasharray: '4 4', strokeWidth: 1.2 },
      ),
      Plot.dot(inside, {
        x: 'y_pred',
        y: 'y_true',
        fill: 'bucket',
        symbol: 'bucket',
        r: 3.2,
        fillOpacity: 0.72,
        title,
        tip: true,
      }),
      Plot.dot(outside, {
        x: 'y_pred',
        y: 'y_true',
        stroke: 'bucket',
        symbol: () => 'cross',
        r: 3.8,
        strokeWidth: 1.6,
        title,
        tip: true,
      }),
    ],
  });
}
