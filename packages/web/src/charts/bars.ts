/**
 * Pylvaskaavio ryhmien vertailuun: sateiset vs. poutaiset paivat, saatilaluokat,
 * tuntikohtaiset sisaantulot suhteessa kapasiteettiin.
 */

import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, SERIES } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
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

export interface BarDatum {
  label: string;
  value: number;
  /** Havaintojen maara, naytetaan vihjeessa. */
  n?: number;
  /** Valmis teksti havaintomaaralle, esim. "12 havaintoa". */
  nLabel?: string;
  color?: string;
  note?: string;
  /** Ryhman avain kun kaavio on ryhmitelty. Sama label eri ryhmissa piirtyy vierekkain. */
  group?: string;
}

/** Ryhman maarittely ryhmitellylle pylvaskaaviolle. */
export interface BarGroup {
  key: string;
  label: string;
  color: string;
  /** Viivoitetaan, jotta ryhma erottuu ilman variakin. */
  hatch?: boolean;
}

export interface BarsProps {
  lang: Lang;
  ariaLabel: string;
  data: BarDatum[];
  /**
   * Ryhmien jarjestys ja selite. Kun tama on annettu, samaa `label`-arvoa kayttavat
   * pylvaat piirtyvat vierekkain yhteen lokeroon.
   */
  groups?: BarGroup[];
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

  const groups = props.groups;
  const hatchId = nextHatchId();

  if (groups && groups.length > 0) {
    const entries: LegendEntry[] = groups.map((group) => ({
      label: group.label,
      color: group.color,
      swatch: true,
      hatch: group.hatch === true,
    }));
    frame.legend.append(createLegend(entries));
  }

  mountResponsive(frame.plot, (width) => draw(width, props, hatchId), { ariaLabel: props.ariaLabel });
});

function draw(width: number, props: BarsProps, hatchId: string): SVGSVGElement | HTMLElement {
  const f = formatters(props.lang);
  const format = chartFormat(props.lang);
  const groups = props.groups;
  const grouped = groups !== undefined && groups.length > 0;
  const horizontal = props.horizontal === true;
  const height = horizontal
    ? Math.max(160, props.data.length * 34 + 60)
    : Math.max(200, Math.min(320, Math.round(width * 0.4)));

  const amount = (value: number): string =>
    props.unit === undefined ? f.count(value, 1) : `${f.decimal(value)} ${props.unit}`;

  const groupLabel = (key: string | undefined): string =>
    groups?.find((group) => group.key === key)?.label ?? '';

  const title = (datum: BarDatum): string =>
    `${datum.label}${grouped ? `, ${groupLabel(datum.group)}` : ''}\n${amount(datum.value)}` +
    (datum.n === undefined ? '' : `\n${datum.nLabel ?? f.int(datum.n)}`) +
    (datum.note ? `\n${datum.note}` : '');

  if (grouped) return drawGrouped(width, props, groups, title, hatchId);

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

/**
 * Ryhmitelty pylvaskaavio: yksi lokero per `label`, sen sisalla yksi pylvas per ryhma.
 * Sisempi akseli piilotetaan, koska ryhmat erottuvat varista, viivoituksesta ja
 * selitteesta. Lokeron nimi on ulommalla akselilla.
 */
function drawGrouped(
  width: number,
  props: BarsProps,
  groups: BarGroup[],
  title: (datum: BarDatum) => string,
  hatchId: string,
): SVGSVGElement | HTMLElement {
  const format = chartFormat(props.lang);
  const height = Math.max(220, Math.min(340, Math.round(width * 0.42)));
  const keys = groups.map((group) => group.key);
  const colorOf = (key: string | undefined): string =>
    groups.find((group) => group.key === key)?.color ?? NEUTRAL.line;
  const hatched = props.data.filter(
    (datum) => groups.find((group) => group.key === datum.group)?.hatch === true,
  );

  const labels = [...new Set(props.data.map((datum) => datum.label))];
  const shared = { fx: 'label', x: 'group', y: 'value' } as const;

  const marks: Plot.Markish[] = [
    Plot.barY(props.data, {
      ...shared,
      fill: (datum: BarDatum) => colorOf(datum.group),
      title,
      tip: true,
    }),
  ];

  if (hatched.length > 0) {
    marks.push(Plot.barY(hatched, { ...shared, fill: `url(#${hatchId})` }));
  }

  marks.push(
    Plot.barY(props.data, { ...shared, fill: 'none', stroke: NEUTRAL.line, strokeWidth: 0.6 }),
    Plot.ruleY([0], { stroke: NEUTRAL.line }),
  );

  if (props.reference) {
    marks.push(
      Plot.ruleY([props.reference.value], {
        stroke: SERIES.forecast,
        strokeWidth: 1.6,
        strokeDasharray: '5 4',
      }),
    );
  }

  const figure = Plot.plot({
    ...baseOptions(width, height),
    marginBottom: 34,
    fx: { label: null, domain: labels, padding: width < 480 ? 0.12 : 0.2 },
    x: { axis: null, domain: keys },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    color: { domain: keys, range: groups.map((group) => group.color) },
    marks,
  });

  if (hatched.length > 0) appendHatchPattern(figure, hatchId);
  return figure;
}
