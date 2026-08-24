/**
 * Hajontakuvio saan ja kavijamaarien suhteesta. x on paivan keskilampotila, y paivan
 * kavijatapahtumat, vari ja symboli saatilaluokka ja koko sademaara.
 *
 * Mukana on pienimman nelionsumman suora. Se kuvaa yhteisvaihtelua, ei syysuhdetta.
 */

import { chartStrings, type ChartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { NEUTRAL, WEATHER_GROUP_COLOR } from '../lib/colors.ts';
import { formatters } from '../lib/format.ts';
import { linearFit } from '../lib/series.ts';
import { island } from '../renderer/index.ts';
import { WEATHER_GROUP_ORDER, weatherGroupLabel } from '../lib/weather.ts';
import type { WeatherGroup } from '../lib/types.ts';
import { Plot, baseOptions, chartFormat, createChartFrame, mountResponsive } from './base.ts';

export interface ScatterPoint {
  date: string;
  venue: string;
  temp: number;
  visitors: number;
  precip: number;
  group: WeatherGroup;
}

export interface ScatterProps {
  lang: Lang;
  ariaLabel: string;
  points: ScatterPoint[];
  [key: string]: unknown;
}

const SYMBOLS: Record<string, string> = {
  clear: 'circle',
  cloudy: 'square',
  rain: 'triangle',
  snow: 'diamond',
  other: 'cross',
};

export default island<ScatterProps>((element, props) => {
  const strings = chartStrings(props.lang);
  const f = formatters(props.lang);
  const frame = createChartFrame(element);
  const venues = [...new Set(props.points.map((point) => point.venue))];
  let selected = venues[0] ?? '';

  let redraw = (): void => {};
  if (venues.length > 1) {
    const toggle = createToggleGroup(strings.venueLabel, venues, selected, (value) => {
      selected = value;
      redraw();
    });
    frame.controls.append(toggle);
  }

  const fitNote = document.createElement('p');
  fitNote.className = 'mt-3 text-xs leading-5 text-ink-muted';
  frame.legend.append(fitNote);

  redraw = mountResponsive(
    frame.plot,
    (width) => {
      const points = props.points.filter((point) => point.venue === selected);
      const fit = linearFit(points.map((point) => ({ x: point.temp, y: point.visitors })));
      fitNote.textContent = fit
        ? strings.scatterFit(f.decimal(fit.slope), f.decimal(fit.r, 2), fit.n)
        : strings.scatterFitMissing;
      return draw(width, points, selected, props.lang, strings);
    },
    { ariaLabel: props.ariaLabel },
  );
});

function createToggleGroup(
  legend: string,
  venues: string[],
  initial: string,
  onChange: (value: string) => void,
): HTMLElement {
  const group = document.createElement('div');
  group.className = 'flex flex-wrap items-center gap-2';
  group.setAttribute('role', 'group');
  group.setAttribute('aria-label', legend);
  const label = document.createElement('span');
  label.className = 'text-xs font-medium text-ink-muted';
  label.textContent = legend;
  group.append(label);

  const buttons: HTMLButtonElement[] = [];
  let current = initial;
  for (const venue of venues) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = venue;
    button.dataset.value = venue;
    button.className =
      'rounded-md border px-2.5 py-1 text-xs font-medium transition-colors ' +
      'aria-pressed:border-series-1 aria-pressed:bg-series-1 aria-pressed:text-white ' +
      'border-line bg-white text-ink hover:border-ink-muted';
    button.setAttribute('aria-pressed', String(venue === current));
    button.addEventListener('click', () => {
      if (current === venue) return;
      current = venue;
      for (const other of buttons) other.setAttribute('aria-pressed', String(other.dataset.value === current));
      onChange(current);
    });
    buttons.push(button);
    group.append(button);
  }
  return group;
}

function draw(
  width: number,
  points: ScatterPoint[],
  venue: string,
  lang: Lang,
  strings: ChartStrings,
): SVGSVGElement | HTMLElement {
  const f = formatters(lang);
  const format = chartFormat(lang);
  const height = Math.max(240, Math.min(400, Math.round(width * 0.55)));
  const fit = linearFit(points.map((point) => ({ x: point.temp, y: point.visitors })));
  const temps = points.map((point) => point.temp);
  const domain: [number, number] =
    temps.length === 0 ? [-20, 20] : [Math.min(...temps), Math.max(...temps)];

  const marks: Plot.Markish[] = [
    Plot.gridY({ stroke: NEUTRAL.grid }),
    Plot.ruleY([0], { stroke: NEUTRAL.line }),
  ];

  if (fit) {
    marks.push(
      Plot.line(
        [
          { x: domain[0], y: fit.predict(domain[0]) },
          { x: domain[1], y: fit.predict(domain[1]) },
        ],
        { x: 'x', y: 'y', stroke: NEUTRAL.muted, strokeWidth: 1.5, strokeDasharray: '5 4' },
      ),
    );
  }

  marks.push(
    Plot.dot(points, {
      x: 'temp',
      y: 'visitors',
      fill: 'group',
      symbol: 'group',
      r: (point: ScatterPoint) => 3 + Math.min(7, Math.sqrt(point.precip) * 2.2),
      fillOpacity: 0.75,
      stroke: NEUTRAL.ink,
      strokeOpacity: 0.25,
      strokeWidth: 0.6,
      title: (point: ScatterPoint) =>
        strings.scatterTip(
          f.date(point.date),
          f.count(point.visitors),
          f.celsius(point.temp),
          f.mm(point.precip),
          weatherGroupLabel(point.group, lang),
        ),
      tip: true,
    }),
  );

  return Plot.plot({
    ...baseOptions(width, height),
    marginBottom: 44,
    x: {
      label: strings.scatterAxis,
      labelAnchor: 'center',
      labelOffset: 36,
      tickFormat: (value: number) => f.decimal(value, 0),
      grid: true,
    },
    y: {
      label: null,
      tickFormat: format.count,
      grid: true,
      zero: true,
    },
    color: {
      domain: WEATHER_GROUP_ORDER,
      range: WEATHER_GROUP_ORDER.map((group) => WEATHER_GROUP_COLOR[group] ?? NEUTRAL.muted),
      legend: true,
      tickFormat: (group: string) => weatherGroupLabel(group as WeatherGroup, lang),
      label: strings.scatterClass(venue),
    },
    symbol: {
      domain: WEATHER_GROUP_ORDER,
      range: WEATHER_GROUP_ORDER.map((group) => SYMBOLS[group] ?? 'circle'),
    },
    marks,
  });
}
