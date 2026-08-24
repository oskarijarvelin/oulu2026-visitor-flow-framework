/**
 * Ennustenakyma: 30 vrk paivatasolla ja 7 vrk tuntitasolla, p10 - p90 vyohyke ja
 * mallien vertailu.
 *
 * Vuorokaudet joiden saa tulee klimatologiasta erotetaan omalla taustavarilla,
 * rajaviivalla ja pisteviivalla, koska keskiarvosaa tuottaa keskiarvokavijamaaran.
 * Oletuksena nakyy vain tuotantomalli.
 */

import { BAND_FILL, BAND_FILL_COMPARE, CLIMATOLOGY_FILL, NEUTRAL, SERIES, modelStyle } from '../lib/colors.ts';
import { addDays, plotDate, plotDay } from '../lib/dates.ts';
import { formatDate, formatInt } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  baseOptions,
  createChartFrame,
  createLegend,
  createToggleGroup,
  mountResponsive,
  tickCount,
  tickDay,
  tickHour,
  titleDate,
  titleDateTime,
  type LegendEntry,
} from './base.ts';

export interface ForecastSeriesPoint {
  t: string;
  p10: number;
  p50: number;
  p90: number;
  clim?: boolean;
}

export interface ForecastChartProps {
  ariaLabel: string;
  /** Mallin nimi -> sarja. */
  daily: Record<string, ForecastSeriesPoint[]>;
  hourly: Record<string, ForecastSeriesPoint[]>;
  models: { name: string; label: string; mae: string }[];
  defaultModel: string;
  /** Viimeinen vuorokausi jolla saa on dynaamista ennustetta. */
  forecastWeatherDays: number;
  originDate: string;
  [key: string]: unknown;
}

type Granularity = 'daily' | 'hourly';
type Selection = string;

interface Row {
  at: Date;
  p10: number;
  p50: number;
  p90: number;
  clim: boolean;
  model: string;
}

export default island<ForecastChartProps>((element, props) => {
  const frame = createChartFrame(element);
  let granularity: Granularity = 'daily';
  let selection: Selection = props.defaultModel;

  let redraw = (): void => {};

  const granularityToggle = createToggleGroup<Granularity>(
    'Tarkkuus',
    [
      { value: 'daily', label: '30 vrk, päivä' },
      { value: 'hourly', label: '7 vrk, tunti' },
    ],
    granularity,
    (value) => {
      granularity = value;
      redraw();
      renderLegend();
    },
  );

  const modelOptions = [
    ...props.models.map((model) => ({ value: model.name, label: model.label })),
    ...(props.models.length > 1 ? [{ value: 'all', label: 'Molemmat' }] : []),
  ];
  const modelToggle = createToggleGroup<Selection>('Malli', modelOptions, selection, (value) => {
    selection = value;
    redraw();
    renderLegend();
  });

  frame.controls.append(granularityToggle.element, modelToggle.element);

  const renderLegend = (): void => {
    const active = activeModels(props, selection);
    const entries: LegendEntry[] = [];
    for (const model of active) {
      const style = modelStyle(model.name);
      entries.push({ label: model.label, color: style.color, dash: style.dash, note: model.mae });
      entries.push({
        label: `${model.label}: p10 - p90`,
        color: model.name === props.defaultModel ? BAND_FILL : BAND_FILL_COMPARE,
        swatch: true,
      });
    }
    if (granularity === 'daily') {
      entries.push({
        label: `Sää klimatologiasta, vrk ${props.forecastWeatherDays + 1} alkaen`,
        color: CLIMATOLOGY_FILL,
        swatch: true,
      });
    }
    frame.legend.replaceChildren(createLegend(entries));
  };

  renderLegend();

  redraw = mountResponsive(
    frame.plot,
    (width) => {
      const active = activeModels(props, selection);
      const source = granularity === 'daily' ? props.daily : props.hourly;
      const parse = granularity === 'daily' ? plotDay : plotDate;
      const rows: Row[] = active.flatMap((model) =>
        (source[model.name] ?? []).map((point) => ({
          at: parse(point.t),
          p10: point.p10,
          p50: point.p50,
          p90: point.p90,
          clim: point.clim === true,
          model: model.name,
        })),
      );
      return draw(width, rows, active, granularity, props);
    },
    { ariaLabel: props.ariaLabel },
  );
});

function activeModels(
  props: ForecastChartProps,
  selection: Selection,
): { name: string; label: string; mae: string }[] {
  if (selection === 'all') return props.models;
  return props.models.filter((model) => model.name === selection);
}

function draw(
  width: number,
  rows: Row[],
  models: { name: string; label: string; mae: string }[],
  granularity: Granularity,
  props: ForecastChartProps,
): SVGSVGElement | HTMLElement {
  const height = Math.max(220, Math.min(380, Math.round(width * 0.45)));
  const step = granularity === 'daily' ? 86_400_000 : 3_600_000;
  const yMax = rows.length === 0 ? 10 : Math.max(10, Math.max(...rows.map((row) => row.p90)) * 1.12);
  const times = rows.map((row) => row.at.getTime());
  const domain: [Date, Date] =
    times.length === 0
      ? [new Date(0), new Date(step)]
      : [new Date(Math.min(...times)), new Date(Math.max(...times) + step)];

  const marks: Plot.Markish[] = [];

  const climatologyRows = rows.filter((row) => row.clim);
  if (granularity === 'daily' && climatologyRows.length > 0) {
    const start = new Date(Math.min(...climatologyRows.map((row) => row.at.getTime())));
    marks.push(
      Plot.rect([{ x1: start, x2: domain[1] }], {
        x1: 'x1',
        x2: 'x2',
        y1: 0,
        y2: yMax,
        fill: CLIMATOLOGY_FILL,
        fillOpacity: 0.85,
      }),
      Plot.ruleX([start], { stroke: NEUTRAL.muted, strokeWidth: 1.4 }),
      Plot.text([{ at: start, label: `Vrk ${props.forecastWeatherDays + 1} alkaen: sää klimatologiaa` }], {
        x: 'at',
        y: yMax,
        text: 'label',
        textAnchor: 'start',
        dx: 6,
        dy: 6,
        fontSize: 11,
        fill: NEUTRAL.muted,
      }),
    );
  }

  for (const model of models) {
    const series = rows.filter((row) => row.model === model.name);
    if (series.length === 0) continue;
    marks.push(
      Plot.areaY(series, {
        x: 'at',
        y1: 'p10',
        y2: 'p90',
        fill: model.name === props.defaultModel ? BAND_FILL : BAND_FILL_COMPARE,
        fillOpacity: models.length > 1 ? 0.42 : 0.6,
        curve: 'monotone-x',
      }),
    );
  }

  marks.push(Plot.ruleY([0], { stroke: NEUTRAL.line }));

  const titleOf = granularity === 'daily' ? titleDate : titleDateTime;

  for (const model of models) {
    const series = rows.filter((row) => row.model === model.name);
    if (series.length === 0) continue;
    const style = modelStyle(model.name);
    // Klimatologia-alue piirretaan tiheammalla pisteviivalla, jotta ero nakyy myos
    // silloin kun taustavari ei erotu, esimerkiksi tulostettuna.
    const dynamic = series.filter((row) => !row.clim);
    const climate = series.filter((row) => row.clim);
    marks.push(
      Plot.line(dynamic, {
        x: 'at',
        y: 'p50',
        stroke: style.color,
        strokeWidth: 2.2,
        strokeDasharray: style.dash ?? undefined,
        curve: 'monotone-x',
      }),
    );
    if (climate.length > 0) {
      const bridge = dynamic.at(-1);
      marks.push(
        Plot.line(bridge ? [bridge, ...climate] : climate, {
          x: 'at',
          y: 'p50',
          stroke: style.color,
          strokeWidth: 2.2,
          strokeDasharray: '1 3',
          strokeOpacity: 0.9,
          curve: 'monotone-x',
        }),
      );
    }
    marks.push(
      Plot.dot(series, {
        x: 'at',
        y: 'p50',
        fill: style.color,
        r: granularity === 'daily' ? 2.6 : 1.6,
        title: (row: Row) =>
          `${model.label}\n${titleOf(row.at)}\n` +
          `Mediaani ${formatInt(row.p50)} kävijätapahtumaa\n` +
          `Väli ${formatInt(row.p10)} - ${formatInt(row.p90)}` +
          (row.clim ? '\nSää klimatologiasta, ei dynaamista ennustetta' : ''),
        tip: true,
      }),
    );
  }

  return Plot.plot({
    ...baseOptions(width, height),
    x: {
      type: 'utc',
      domain,
      tickFormat: granularity === 'daily' ? tickDay : tickHour,
      ticks: width < 480 ? 4 : 7,
      label: null,
    },
    y: { domain: [0, yMax], label: null, tickFormat: tickCount, grid: true, ticks: 5 },
    marks,
  });
}

/** Ensimmainen klimatologiavuorokausi tekstivastinetta varten. */
export function climatologyStartDate(originDate: string, forecastWeatherDays: number): string {
  return formatDate(addDays(originDate, forecastWeatherDays + 1));
}

export const FORECAST_ACCENT = SERIES.forecast;
