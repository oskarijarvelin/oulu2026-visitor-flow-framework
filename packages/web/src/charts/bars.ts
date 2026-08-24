/**
 * Pylvaskaavio ryhmien vertailuun: sateiset vs. poutaiset paivat, saatilaluokat,
 * tuntikohtaiset sisaantulot suhteessa kapasiteettiin.
 */

import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, SERIES } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import { Plot, baseOptions, chartFormat, createChartFrame, mountResponsive } from './base.ts';

export interface BarDatum {
  label: string;
  value: number;
  /** Havaintojen maara, naytetaan vihjeessa. */
  n?: number;
  /** Valmis teksti havaintomaaralle, esim. "12 havaintoa". */
  nLabel?: string;
  color?: string;
  note?: string;
}

export interface BarsProps {
  lang: Lang;
  ariaLabel: string;
  data: BarDatum[];
  /** Vaakasuora viiva, esimerkiksi kapasiteetti. */
  reference?: { value: number; label: string } | null;
  /** Yksikko vihjeisiin. Oletuksena kavijatapahtuma. */
  unit?: string;
  horizontal?: boolean;
  [key: string]: unknown;
}

export default island<BarsProps>((element, props) => {
  const frame = createChartFrame(element);
  frame.controls.remove();
  mountResponsive(frame.plot, (width) => draw(width, props), { ariaLabel: props.ariaLabel });
});

function draw(width: number, props: BarsProps): SVGSVGElement | HTMLElement {
  const f = formatters(props.lang);
  const format = chartFormat(props.lang);
  const horizontal = props.horizontal === true;
  const height = horizontal
    ? Math.max(160, props.data.length * 34 + 60)
    : Math.max(200, Math.min(320, Math.round(width * 0.4)));

  const amount = (value: number): string =>
    props.unit === undefined ? f.count(value, 1) : `${f.decimal(value)} ${props.unit}`;

  const title = (datum: BarDatum): string =>
    `${datum.label}\n${amount(datum.value)}` +
    (datum.n === undefined ? '' : `\n${datum.nLabel ?? f.int(datum.n)}`) +
    (datum.note ? `\n${datum.note}` : '');

  const marks: Plot.Markish[] = [];

  if (horizontal) {
    marks.push(
      Plot.barX(props.data, {
        y: 'label',
        x: 'value',
        fill: (datum: BarDatum) => datum.color ?? SERIES.history,
        title,
        tip: true,
      }),
      Plot.ruleX([0], { stroke: NEUTRAL.line }),
      Plot.text(props.data, {
        y: 'label',
        x: 'value',
        text: (datum: BarDatum) => f.decimal(datum.value),
        textAnchor: 'start',
        dx: 6,
        fontSize: 11,
        fill: NEUTRAL.muted,
      }),
    );
  } else {
    marks.push(
      Plot.barY(props.data, {
        x: 'label',
        y: 'value',
        fill: (datum: BarDatum) => datum.color ?? SERIES.history,
        title,
        tip: true,
      }),
      Plot.ruleY([0], { stroke: NEUTRAL.line }),
    );
  }

  if (props.reference) {
    const reference = props.reference;
    if (horizontal) {
      marks.push(
        Plot.ruleX([reference.value], { stroke: SERIES.forecast, strokeWidth: 1.6, strokeDasharray: '5 4' }),
      );
    } else {
      marks.push(
        Plot.ruleY([reference.value], { stroke: SERIES.forecast, strokeWidth: 1.6, strokeDasharray: '5 4' }),
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
  }

  return Plot.plot({
    ...baseOptions(width, height),
    marginLeft: horizontal ? Math.min(160, Math.max(70, width * 0.28)) : 56,
    marginBottom: horizontal ? 34 : 42,
    x: horizontal
      ? { label: null, tickFormat: format.count, grid: true }
      : { label: null, tickRotate: props.data.length > 6 ? -30 : 0 },
    y: horizontal ? { label: null } : { label: null, tickFormat: format.count, grid: true, zero: true },
    marks,
  });
}
