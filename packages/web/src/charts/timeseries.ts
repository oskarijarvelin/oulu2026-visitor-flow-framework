/**
 * Aikasarja: historia yhtenaisena viivana, ennuste katkoviivana ja p10 - p90 vaaleana
 * alueena. Sadetunnit ovat taustavarina ja pyhapaivat pystyviivoina. Rajausvalitsin
 * vaihtaa nakyvan jakson.
 */

import { chartStrings, type ChartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { BAND_FILL, CLIMATOLOGY_FILL, HOLIDAY_LINE, NEUTRAL, RAIN_FILL, SERIES } from '../lib/colors.ts';
import { plotDate, plotDay } from '../lib/dates.ts';
import { formatters } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  baseOptions,
  chartFormat,
  createChartFrame,
  createLegend,
  createToggleGroup,
  mountResponsive,
  type ChartFormat,
  type LegendEntry,
} from './base.ts';

export interface TimeseriesPoint {
  /** "2026-05-22" paivatasolla, "2026-05-22T14" tuntitasolla. */
  t: string;
  v: number;
}

export interface TimeseriesForecastPoint {
  t: string;
  p10: number;
  p50: number;
  p90: number;
  /** true kun paivan saa on klimatologiaa eika dynaamista sääennustetta. */
  clim?: boolean;
}

export interface TimeseriesProps {
  lang: Lang;
  ariaLabel: string;
  mode: 'day' | 'hour';
  history: TimeseriesPoint[];
  forecast?: TimeseriesForecastPoint[];
  /** Sateiset paivat tai tunnit samassa muodossa kuin `t`. */
  rain?: string[];
  holidays?: { t: string; name: string }[];
  /** Rajausvaihtoehdot vuorokausina. `null` tarkoittaa koko sarjaa. */
  ranges?: (number | null)[];
  initialRange?: number | null;
  /** Yksikko vihjeisiin. Oletuksena kavijatapahtuma. */
  unit?: string;
  [key: string]: unknown;
}

interface Row {
  at: Date;
  t: string;
  v: number;
}

interface ForecastRow {
  at: Date;
  t: string;
  p10: number;
  p50: number;
  p90: number;
  clim: boolean;
}

export default island<TimeseriesProps>((element, props) => {
  const strings = chartStrings(props.lang);
  const format = chartFormat(props.lang);
  const parse = props.mode === 'hour' ? plotDate : plotDay;
  const step = props.mode === 'hour' ? 3_600_000 : 86_400_000;

  const history: Row[] = props.history.map((point) => ({ at: parse(point.t), t: point.t, v: point.v }));
  const forecast: ForecastRow[] = (props.forecast ?? []).map((point) => ({
    at: parse(point.t),
    t: point.t,
    p10: point.p10,
    p50: point.p50,
    p90: point.p90,
    clim: point.clim === true,
  }));
  const rainSet = new Set(props.rain ?? []);
  const holidays = (props.holidays ?? []).map((entry) => ({ at: parse(entry.t), name: entry.name }));

  const ranges = props.ranges ?? [7, 30, 90, null];

  const frame = createChartFrame(element);
  let selectedDays: number | null = props.initialRange === undefined ? 30 : props.initialRange;

  const legendEntries: LegendEntry[] = [{ label: strings.actual, color: SERIES.history }];
  if (forecast.length > 0) {
    legendEntries.push(
      { label: strings.forecastMedian, color: SERIES.forecast, dash: '6 4' },
      { label: strings.interval, color: BAND_FILL, swatch: true },
    );
    if (forecast.some((row) => row.clim)) {
      legendEntries.push({ label: strings.climatologyLegend, color: CLIMATOLOGY_FILL, swatch: true });
    }
  }
  if (rainSet.size > 0) {
    legendEntries.push({
      label: props.mode === 'hour' ? strings.rainHours : strings.rainDays,
      color: RAIN_FILL,
      swatch: true,
    });
  }
  if (holidays.length > 0) legendEntries.push({ label: strings.holiday, color: HOLIDAY_LINE, dash: '3 3' });
  frame.legend.append(createLegend(legendEntries));

  let redraw = (): void => {};

  if (ranges.length > 1) {
    const toggle = createToggleGroup(
      strings.rangeLabel,
      ranges.map((days, index) => ({
        value: String(index),
        label: days === null ? strings.rangeAll : strings.rangeDays(days),
        description: days === null ? strings.rangeAllDescription : strings.rangeDaysDescription(days),
      })),
      String(Math.max(0, ranges.indexOf(selectedDays))),
      (value) => {
        selectedDays = ranges[Number(value)] ?? null;
        redraw();
      },
    );
    frame.controls.append(toggle.element);
  }

  redraw = mountResponsive(
    frame.plot,
    (width) => {
      const [from, to] = windowBounds(history, forecast, selectedDays, step);
      const visibleHistory = history.filter((row) => row.at >= from);
      // Ennuste rajataan samalle pituudelle kuin historia, jotta lyhyt rajaus ei nayta
      // seitsemaa vuorokautta historiaa ja kolmeakymmenta vuorokautta ennustetta.
      const visibleForecast = forecast.filter((row) => row.at >= from && row.at <= to);
      return draw(width, visibleHistory, visibleForecast, rainSet, holidays, props, step, strings, format);
    },
    { ariaLabel: props.ariaLabel },
  );
});

/** Rajaus ankkuroidaan historian loppuun, ei ennusteen loppuun. */
function windowBounds(
  history: Row[],
  forecast: ForecastRow[],
  days: number | null,
  step: number,
): [Date, Date] {
  const far: [Date, Date] = [new Date(-8_640_000_000_000), new Date(8_640_000_000_000)];
  if (days === null) return far;
  const anchor = history.at(-1)?.at ?? forecast[0]?.at;
  if (!anchor) return far;
  const span = step === 3_600_000 ? days * 24 * step : days * step;
  return [new Date(anchor.getTime() - span + step), new Date(anchor.getTime() + span)];
}

function draw(
  width: number,
  history: Row[],
  forecast: ForecastRow[],
  rainSet: Set<string>,
  holidays: { at: Date; name: string }[],
  props: TimeseriesProps,
  step: number,
  strings: ChartStrings,
  format: ChartFormat,
): SVGSVGElement | HTMLElement {
  const height = Math.max(200, Math.min(360, Math.round(width * 0.42)));
  const values = [...history.map((row) => row.v), ...forecast.map((row) => row.p90)];
  const yMax = values.length === 0 ? 10 : Math.max(10, Math.max(...values) * 1.08);

  const xDomain = domainOf(history, forecast, step);
  const visibleHolidays = holidays.filter((entry) => entry.at >= xDomain[0] && entry.at <= xDomain[1]);

  const rainBands = bandsFrom(
    [...history.map((row) => ({ at: row.at, t: row.t }))],
    rainSet,
    step,
  );

  const climatologyStart = forecast.find((row) => row.clim)?.at ?? null;
  const climatologyEnd = [...forecast].reverse().find((row) => row.clim)?.at ?? null;

  const marks: Plot.Markish[] = [];

  if (climatologyStart && climatologyEnd) {
    marks.push(
      Plot.rect([{ x1: climatologyStart, x2: new Date(climatologyEnd.getTime() + step) }], {
        x1: 'x1',
        x2: 'x2',
        y1: 0,
        y2: yMax,
        fill: CLIMATOLOGY_FILL,
        fillOpacity: 0.75,
      }),
    );
  }

  if (rainBands.length > 0) {
    marks.push(
      Plot.rect(rainBands, {
        x1: 'from',
        x2: 'to',
        y1: 0,
        y2: yMax,
        fill: RAIN_FILL,
        fillOpacity: 0.85,
      }),
    );
  }

  if (forecast.length > 0) {
    marks.push(
      Plot.areaY(forecast, {
        x: 'at',
        y1: 'p10',
        y2: 'p90',
        fill: BAND_FILL,
        fillOpacity: 0.65,
        curve: 'monotone-x',
      }),
    );
  }

  if (visibleHolidays.length > 0) {
    marks.push(
      Plot.ruleX(visibleHolidays, {
        x: 'at',
        stroke: HOLIDAY_LINE,
        strokeDasharray: '3 3',
        strokeWidth: 1,
      }),
    );
    // Nimet piirretaan vain kun tilaa on. Kapealla naytolla perakkaiset pyhat, kuten
    // juhannusaatto ja juhannuspaiva, menisivat paallekkain. Pyhat loytyvat aina myos
    // kaavion tekstivastineesta, joten tieto ei katoa.
    const minLabelGap = (xDomain[1].getTime() - xDomain[0].getTime()) / Math.max(1, width / 70);
    if (width >= 520 && visibleHolidays.length <= 8) {
      let previous = Number.NEGATIVE_INFINITY;
      let row = 0;
      const labelled = visibleHolidays.map((entry) => {
        row = entry.at.getTime() - previous < minLabelGap ? (row + 1) % 3 : 0;
        previous = entry.at.getTime();
        return { ...entry, row };
      });
      // Plotin `dy` on vakio, ei kanava, joten jokainen rivi on oma merkkinsa.
      for (const level of [0, 1, 2]) {
        const onLevel = labelled.filter((entry) => entry.row === level);
        if (onLevel.length === 0) continue;
        marks.push(
          Plot.text(onLevel, {
            x: 'at',
            y: yMax,
            text: 'name',
            dy: -4 - level * 11,
            dx: 2,
            textAnchor: 'start',
            fontSize: 10,
            fill: HOLIDAY_LINE,
          }),
        );
      }
    }
  }

  marks.push(Plot.ruleY([0], { stroke: NEUTRAL.line }));

  // Kytkentaviiva historian viimeisesta havainnosta ennusteen ensimmaiseen, jos ne
  // ovat perakkain. Ilman tata kaavioon jaa nakyva aukko.
  const lastHistory = history.at(-1);
  const firstForecast = forecast[0];
  if (lastHistory && firstForecast && firstForecast.at.getTime() - lastHistory.at.getTime() <= step * 1.5) {
    marks.push(
      Plot.line(
        [
          { at: lastHistory.at, v: lastHistory.v },
          { at: firstForecast.at, v: firstForecast.p50 },
        ],
        { x: 'at', y: 'v', stroke: SERIES.forecast, strokeDasharray: '6 4', strokeWidth: 2 },
      ),
    );
  }

  if (forecast.length > 0) {
    marks.push(
      Plot.line(forecast, {
        x: 'at',
        y: 'p50',
        stroke: SERIES.forecast,
        strokeDasharray: '6 4',
        strokeWidth: 2,
        curve: 'monotone-x',
      }),
    );
  }

  marks.push(
    Plot.line(history, {
      x: 'at',
      y: 'v',
      stroke: SERIES.history,
      strokeWidth: history.length > 400 ? 1 : 1.6,
      curve: 'linear',
    }),
  );

  if (history.length <= 60) {
    marks.push(Plot.dot(history, { x: 'at', y: 'v', fill: SERIES.history, r: 2.4 }));
  }

  const titleOf = step === 3_600_000 ? format.titleDateTime : format.titleDate;
  const f = formatters(props.lang);
  const amount = (value: number): string =>
    props.unit === undefined ? f.count(value) : `${f.int(value)} ${props.unit}`;

  if (history.length > 0) {
    marks.push(
      Plot.tip(
        history,
        Plot.pointerX({
          x: 'at',
          y: 'v',
          title: (row: Row) => `${titleOf(row.at)}\n${amount(row.v)}`,
          fontSize: 12,
        }),
      ),
    );
  }
  if (forecast.length > 0) {
    marks.push(
      Plot.tip(
        forecast,
        Plot.pointerX({
          x: 'at',
          y: 'p50',
          title: (row: ForecastRow) =>
            `${titleOf(row.at)}\n${strings.forecastTip(amount(row.p50))}` +
            `\n${strings.intervalTip(f.int(row.p10), f.int(row.p90))}` +
            (row.clim ? `\n${strings.climatologyTip}` : ''),
          fontSize: 12,
        }),
      ),
    );
  }

  return Plot.plot({
    ...baseOptions(width, height),
    // Ylamarginaali antaa tilaa pyhapaivien nimille kaavion ylareunassa.
    marginTop: visibleHolidays.length > 0 && width >= 520 ? 34 : 16,
    x: {
      type: 'utc',
      domain: xDomain,
      tickFormat: step === 3_600_000 && spanDays(xDomain) <= 3 ? format.tickHour : format.tickDay,
      ticks: width < 480 ? 4 : 7,
      label: null,
      grid: false,
    },
    y: {
      domain: [0, yMax],
      label: null,
      tickFormat: format.count,
      grid: true,
      ticks: 5,
    },
    marks,
  });
}

function spanDays(domain: [Date, Date]): number {
  return (domain[1].getTime() - domain[0].getTime()) / 86_400_000;
}

function domainOf(history: Row[], forecast: ForecastRow[], step: number): [Date, Date] {
  const times = [...history.map((row) => row.at.getTime()), ...forecast.map((row) => row.at.getTime())];
  if (times.length === 0) return [new Date(0), new Date(step)];
  return [new Date(Math.min(...times)), new Date(Math.max(...times) + step)];
}

/** Yhtenaiset jaksot niista pisteista jotka kuuluvat joukkoon. */
function bandsFrom(
  points: { at: Date; t: string }[],
  members: Set<string>,
  step: number,
): { from: Date; to: Date }[] {
  const bands: { from: Date; to: Date }[] = [];
  let start: Date | null = null;
  let previous: Date | null = null;
  for (const point of points) {
    if (members.has(point.t)) {
      if (start === null) start = point.at;
      previous = point.at;
      continue;
    }
    if (start !== null && previous !== null) {
      bands.push({ from: start, to: new Date(previous.getTime() + step) });
      start = null;
      previous = null;
    }
  }
  if (start !== null && previous !== null) {
    bands.push({ from: start, to: new Date(previous.getTime() + step) });
  }
  return bands;
}
