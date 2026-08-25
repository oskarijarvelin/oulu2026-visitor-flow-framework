/**
 * Arviointiajon ennuste vastaan toteuma.
 *
 * Toteuma on yhtenainen viiva, mallin mediaani katkoviiva ja sen p10 - p90 vaalea alue.
 * Vertailukohdat ovat ohuita viivoja ja oletuksena piilossa, koska kolme ylimaaraista
 * sarjaa peittaa sen mita kuvasta luetaan. Pyhapaivat ovat pystyviivoja.
 *
 * Kaavio vaihtaa ajoa sivun valitsimen mukana: props sisaltaa jokaisen ajon sarjan ja
 * saareke piirtaa sen joka on valittuna.
 */

import { chartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { BAND_FILL, HOLIDAY_LINE, NEUTRAL, SERIES, modelStyle } from '../lib/colors.ts';
import { plotDay } from '../lib/dates.ts';
import { formatters } from '../lib/format.ts';
import { currentRun, onRunChange } from '../lib/runstate.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  baseOptions,
  chartFormat,
  createChartFrame,
  createLegend,
  createToggleGroup,
  mountResponsive,
  type LegendEntry,
} from './base.ts';

export interface AccuracySeriesModelPayload {
  name: string;
  label: string;
  /** Paamallilla on vali, vertailukohdalla ei. */
  main: boolean;
  p50: (number | null)[];
  p10?: (number | null)[];
  p90?: (number | null)[];
}

export interface AccuracySeriesPayload {
  dates: string[];
  y_true: number[];
  /** Pyhapaivat: [paivamaara, nimi]. Objekti ei sailyisi jarjestyksessa yhta selvasti. */
  holidays: [string, string][];
  models: AccuracySeriesModelPayload[];
}

export interface AccuracySeriesProps {
  lang: Lang;
  ariaLabel: string;
  defaultRun: string;
  /** Ajon tunnus -> sarja. `null` kun sarjaa ei ole paketissa. */
  runs: Record<string, AccuracySeriesPayload | null>;
  /** Teksti joka naytetaan kun ajon sarjaa ei ole paketissa. */
  missingLabel: string;
  [key: string]: unknown;
}

type ReferenceChoice = string;

interface Point {
  at: Date;
  value: number;
  date: string;
}

export default island<AccuracySeriesProps>((element, props) => {
  const strings = chartStrings(props.lang);
  const frame = createChartFrame(element);

  let run = currentRun(props.defaultRun);
  let choice: ReferenceChoice = 'none';
  let redraw = (): void => {};

  const references = (): AccuracySeriesModelPayload[] =>
    (props.runs[run]?.models ?? []).filter((model) => !model.main);

  const toggleHost = document.createElement('div');
  frame.controls.append(toggleHost);

  const renderToggle = (): void => {
    const options = [
      { value: 'none', label: strings.referencesNone },
      ...references().map((model) => ({ value: model.name, label: model.label })),
    ];
    if (references().length > 1) options.push({ value: 'all', label: strings.referencesAll });
    if (!options.some((option) => option.value === choice)) choice = 'none';
    const group = createToggleGroup<ReferenceChoice>(strings.referencesLabel, options, choice, (value) => {
      choice = value;
      renderLegend();
      redraw();
    });
    toggleHost.replaceChildren(group.element);
  };

  const renderLegend = (): void => {
    const payload = props.runs[run];
    if (!payload) {
      frame.legend.replaceChildren();
      return;
    }
    const entries: LegendEntry[] = [{ label: strings.actual, color: SERIES.history }];
    for (const model of visibleModels(payload, choice)) {
      const style = modelStyle(model.name);
      entries.push({ label: model.label, color: style.color, dash: style.dash });
      if (model.main) entries.push({ label: strings.interval, color: BAND_FILL, swatch: true });
    }
    if (payload.holidays.length > 0) {
      entries.push({ label: strings.holiday, color: HOLIDAY_LINE, dash: '2 3' });
    }
    frame.legend.replaceChildren(createLegend(entries));
  };

  renderToggle();
  renderLegend();

  redraw = mountResponsive(frame.plot, (width) => draw(width, props, run, choice), {
    ariaLabel: props.ariaLabel,
  });

  onRunChange((next) => {
    if (next === run) return;
    run = next;
    renderToggle();
    renderLegend();
    redraw();
  });
});

function visibleModels(
  payload: AccuracySeriesPayload,
  choice: ReferenceChoice,
): AccuracySeriesModelPayload[] {
  return payload.models.filter(
    (model) => model.main || choice === 'all' || model.name === choice,
  );
}

function toPoints(dates: string[], values: (number | null)[]): Point[] {
  const points: Point[] = [];
  for (let i = 0; i < dates.length; i += 1) {
    const value = values[i];
    const date = dates[i];
    if (value === null || value === undefined || date === undefined) continue;
    points.push({ at: plotDay(date), value, date });
  }
  return points;
}

function draw(
  width: number,
  props: AccuracySeriesProps,
  run: string,
  choice: ReferenceChoice,
): SVGSVGElement | HTMLElement {
  const payload = props.runs[run];
  if (!payload || payload.dates.length === 0) return note(props.missingLabel);

  const f = formatters(props.lang);
  const strings = chartStrings(props.lang);
  const format = chartFormat(props.lang);
  const height = Math.max(220, Math.min(380, Math.round(width * 0.45)));
  const models = visibleModels(payload, choice);

  const marks: Plot.Markish[] = [];

  for (const model of models) {
    if (!model.main || !model.p10 || !model.p90) continue;
    const band = payload.dates
      .map((date, index) => ({
        at: plotDay(date),
        p10: model.p10?.[index] ?? null,
        p90: model.p90?.[index] ?? null,
      }))
      .filter((row): row is { at: Date; p10: number; p90: number } => row.p10 !== null && row.p90 !== null);
    if (band.length === 0) continue;
    marks.push(
      Plot.areaY(band, {
        x: 'at',
        y1: 'p10',
        y2: 'p90',
        fill: BAND_FILL,
        fillOpacity: models.length > 2 ? 0.4 : 0.55,
        curve: 'monotone-x',
      }),
    );
  }

  if (payload.holidays.length > 0) {
    const holidays = payload.holidays.map(([date, name]) => ({ at: plotDay(date), name, date }));
    marks.push(
      Plot.ruleX(holidays, {
        x: 'at',
        stroke: HOLIDAY_LINE,
        strokeWidth: 1.2,
        strokeDasharray: '2 3',
        title: (row: { name: string; date: string }) =>
          `${strings.holiday}: ${row.name}\n${f.date(row.date)}`,
        tip: true,
      }),
    );
  }

  marks.push(Plot.ruleY([0], { stroke: NEUTRAL.line }));

  const actual = toPoints(payload.dates, payload.y_true);
  marks.push(
    Plot.line(actual, { x: 'at', y: 'value', stroke: SERIES.history, strokeWidth: 2.2, curve: 'linear' }),
  );

  for (const model of models) {
    const style = modelStyle(model.name);
    const points = toPoints(payload.dates, model.p50);
    if (points.length === 0) continue;
    marks.push(
      Plot.line(points, {
        x: 'at',
        y: 'value',
        stroke: style.color,
        strokeWidth: model.main ? 2 : 1.1,
        strokeOpacity: model.main ? 1 : 0.85,
        strokeDasharray: style.dash ?? undefined,
        curve: 'linear',
      }),
    );
  }

  // Vihje asuu toteuman pisteissa, koska paivan kaikki luvut luetaan yhdesta kohdasta.
  marks.push(
    Plot.dot(actual, {
      x: 'at',
      y: 'value',
      fill: SERIES.history,
      r: actual.length > 60 ? 1.6 : 2.6,
      title: (point: Point) => {
        const index = payload.dates.indexOf(point.date);
        const lines = [format.titleDate(point.at), `${strings.actual} ${f.count(point.value)}`];
        for (const model of models) {
          const value = model.p50[index];
          if (value === null || value === undefined) continue;
          lines.push(`${model.label} ${f.decimal(value)}`);
          if (model.main && model.p10 && model.p90) {
            const low = model.p10[index];
            const high = model.p90[index];
            if (low !== null && low !== undefined && high !== null && high !== undefined) {
              lines.push(strings.intervalTip(f.int(low), f.int(high)));
            }
          }
        }
        return lines.join('\n');
      },
      tip: true,
    }),
  );

  return Plot.plot({
    ...baseOptions(width, height),
    x: { type: 'utc', label: null, tickFormat: format.tickDay, ticks: width < 480 ? 4 : 7 },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    marks,
  });
}

/** Tyhja tila kaavion tilalla. Sama sailio, jotta sivun korkeus ei hyppaa. */
function note(message: string): HTMLElement {
  const element = document.createElement('p');
  element.className = 'rounded-md border border-line bg-canvas px-4 py-6 text-sm leading-6 text-ink-muted';
  element.textContent = message;
  return element;
}
