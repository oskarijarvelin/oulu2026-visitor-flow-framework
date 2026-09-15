/**
 * Vertailuviikot: yhden backtest-origon ennuste vastaan se mita todella tapahtui.
 *
 * Laatusivun hajontakuvio kertoo kuinka kaukana pisteet ovat lavistajasta, mutta se on
 * ajaton: siita ei nae milloin malli oli pielessa eika mihin suuntaan se ajautui paiva
 * paivalta. Tama kaavio ottaa yhden origon kerrallaan ja piirtaa sen ennusteen
 * kohdepaivien paalle, joten virhe luetaan aikajanalta.
 *
 * Toteuma on yhtenainen viiva, mallien mediaanit katkoviivoja ja p10 - p90 vaaleita
 * alueita. Mallivalitsin tuntee myos vaihtoehdon "molemmat", jolloin samalta origolta
 * nakee kumpi malli osui: molemmat vyohykkeet piirtyvat paallekkain samalle toteumalle
 * ja kaavion alla on kummankin MAE, harha ja osumien maara.
 */

import { chartStrings, type ChartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { BAND_FILL, BAND_FILL_COMPARE, NEUTRAL, SERIES, modelStyle } from '../lib/colors.ts';
import { addDays, plotDay } from '../lib/dates.ts';
import { formatters, type Formatters } from '../lib/format.ts';
import { island } from '../renderer/index.ts';
import {
  Plot,
  baseOptions,
  chartFormat,
  createChartFrame,
  createLegend,
  createSelectControl,
  createToggleGroup,
  mountResponsive,
  type LegendEntry,
} from './base.ts';

/** Mallivalitsimen arvo: mallin nimi tai kaikki mallit kerralla. */
const ALL_MODELS = 'all';

export interface OriginWeekPoint {
  model: string;
  origin_date: string;
  horizon_days: number;
  y_true: number;
  y_pred: number;
  p10: number;
  p90: number;
}

export interface OriginWeeksModel {
  name: string;
  label: string;
}

export interface OriginWeeksProps {
  lang: Lang;
  ariaLabel: string;
  points: OriginWeekPoint[];
  models: OriginWeeksModel[];
  defaultModel: string;
  /** Origot vanhimmasta uusimpaan. Oletuksena valitaan viimeisin. */
  origins: string[];
  [key: string]: unknown;
}

/** Yhden mallin ennuste yhdelle kohdepaivalle. */
interface Prediction {
  model: string;
  y_pred: number;
  p10: number;
  p90: number;
  covered: boolean;
}

/**
 * Yksi kohdepaiva. Toteuma on paivan ominaisuus eika mallin, joten se elaa tasolla
 * ylempana: kaikki mallit ennustavat samaa lukua.
 */
interface Day {
  at: Date;
  target_date: string;
  horizon_days: number;
  y_true: number;
  predictions: Prediction[];
}

/** Yhden mallin yhteenveto valitulta origolta. */
interface Summary {
  model: string;
  label: string;
  days: number;
  mae: number;
  bias: number;
  inside: number;
}

export default island<OriginWeeksProps>((element, props) => {
  const strings = chartStrings(props.lang);
  const f = formatters(props.lang);
  const frame = createChartFrame(element);

  // Uusin origo on se jonka kayttaja haluaa nahda ensimmaisena: "mita viime viikolle
  // luvattiin ja miten siina kavi".
  let origin = props.origins.at(-1) ?? '';
  let selection = props.defaultModel;
  let redraw = (): void => {};

  const activeModels = (): OriginWeeksModel[] =>
    selection === ALL_MODELS ? props.models : props.models.filter((model) => model.name === selection);

  const daysNow = (): Day[] => daysFor(props.points, origin, activeModels());

  const note = document.createElement('div');
  note.className = 'mt-3 space-y-1 text-xs leading-5 text-ink-muted';

  const renderNote = (): void => {
    const days = daysNow();
    if (days.length === 0) {
      const empty = document.createElement('p');
      empty.textContent = strings.originWeekEmpty;
      note.replaceChildren(empty);
      return;
    }
    const header = document.createElement('p');
    header.textContent = strings.originWeekHeader(f.date(origin), days.length);
    const lines = summarise(days, activeModels()).map((summary) => {
      const line = document.createElement('p');
      line.textContent = strings.originWeekModel(
        summary.label,
        f.decimal(summary.mae),
        f.decimal(Math.abs(summary.bias)),
        summary.bias >= 0 ? strings.originWeekOver : strings.originWeekUnder,
        summary.inside,
        summary.days,
      );
      return line;
    });
    note.replaceChildren(header, ...lines);
  };

  const renderLegend = (): void => {
    const models = activeModels();
    const entries: LegendEntry[] = [{ label: strings.actual, color: SERIES.history }];
    for (const model of models) {
      const style = modelStyle(model.name);
      entries.push({ label: model.label, color: style.color, dash: style.dash });
      entries.push({
        label: models.length > 1 ? `${model.label}: ${strings.interval}` : strings.interval,
        color: bandFill(model.name, props.defaultModel),
        swatch: true,
      });
    }
    frame.legend.replaceChildren(createLegend(entries), note);
    renderNote();
  };

  const originSelect = createSelectControl(
    strings.originLabel,
    props.origins.map((value) => ({ value, label: f.date(value) })),
    origin,
    (value) => {
      origin = value;
      renderLegend();
      redraw();
    },
  );
  frame.controls.append(originSelect.element);

  if (props.models.length > 1) {
    const options = [
      ...props.models.map((model) => ({ value: model.name, label: model.label })),
      { value: ALL_MODELS, label: strings.bothModels },
    ];
    const toggle = createToggleGroup(strings.modelLabel, options, selection, (value) => {
      selection = value;
      renderLegend();
      redraw();
    });
    frame.controls.append(toggle.element);
  }

  renderLegend();

  redraw = mountResponsive(
    frame.plot,
    (width) => draw(width, daysNow(), activeModels(), props.defaultModel, props.lang, strings),
    { ariaLabel: props.ariaLabel },
  );
});

/** Oletusmalli saa saman vyohykevarin kuin muualla sivustolla, vertailtava toisen. */
function bandFill(model: string, defaultModel: string): string {
  return model === defaultModel ? BAND_FILL : BAND_FILL_COMPARE;
}

function daysFor(points: OriginWeekPoint[], origin: string, models: OriginWeeksModel[]): Day[] {
  const wanted = new Set(models.map((model) => model.name));
  const byTarget = new Map<string, Day>();

  for (const point of points) {
    if (point.origin_date !== origin || !wanted.has(point.model)) continue;
    const target = addDays(point.origin_date, point.horizon_days);
    let day = byTarget.get(target);
    if (!day) {
      day = {
        at: plotDay(target),
        target_date: target,
        horizon_days: point.horizon_days,
        y_true: point.y_true,
        predictions: [],
      };
      byTarget.set(target, day);
    }
    day.predictions.push({
      model: point.model,
      y_pred: point.y_pred,
      p10: point.p10,
      p90: point.p90,
      covered: point.y_true >= point.p10 && point.y_true <= point.p90,
    });
  }

  return [...byTarget.values()].sort((a, b) => a.horizon_days - b.horizon_days);
}

function summarise(days: Day[], models: OriginWeeksModel[]): Summary[] {
  return models.flatMap((model) => {
    const entries = days.flatMap((day) => {
      const prediction = day.predictions.find((item) => item.model === model.name);
      return prediction ? [{ day, prediction }] : [];
    });
    if (entries.length === 0) return [];
    return [
      {
        model: model.name,
        label: model.label,
        days: entries.length,
        mae:
          entries.reduce((sum, { day, prediction }) => sum + Math.abs(prediction.y_pred - day.y_true), 0) /
          entries.length,
        bias:
          entries.reduce((sum, { day, prediction }) => sum + (prediction.y_pred - day.y_true), 0) /
          entries.length,
        inside: entries.filter(({ prediction }) => prediction.covered).length,
      },
    ];
  });
}

/** Yhden mallin rivit piirtoa varten: vyohyke ja mediaani tarvitsevat litteän taulun. */
interface ModelRow {
  at: Date;
  y_pred: number;
  p10: number;
  p90: number;
}

function modelRows(days: Day[], model: string): ModelRow[] {
  return days.flatMap((day) => {
    const prediction = day.predictions.find((item) => item.model === model);
    return prediction
      ? [{ at: day.at, y_pred: prediction.y_pred, p10: prediction.p10, p90: prediction.p90 }]
      : [];
  });
}

function draw(
  width: number,
  days: Day[],
  models: OriginWeeksModel[],
  defaultModel: string,
  lang: Lang,
  strings: ChartStrings,
): SVGSVGElement | HTMLElement {
  if (days.length === 0) return note(strings.originWeekEmpty);

  const f = formatters(lang);
  const format = chartFormat(lang);
  const height = Math.max(220, Math.min(380, Math.round(width * 0.45)));
  const marks: Plot.Markish[] = [];

  for (const model of models) {
    const rows = modelRows(days, model.name);
    if (rows.length === 0) continue;
    marks.push(
      Plot.areaY(rows, {
        x: 'at',
        y1: 'p10',
        y2: 'p90',
        fill: bandFill(model.name, defaultModel),
        fillOpacity: models.length > 1 ? 0.42 : 0.55,
        curve: 'monotone-x',
      }),
    );
  }

  marks.push(Plot.ruleY([0], { stroke: NEUTRAL.line }));

  for (const model of models) {
    const rows = modelRows(days, model.name);
    if (rows.length === 0) continue;
    const style = modelStyle(model.name);
    marks.push(
      Plot.line(rows, {
        x: 'at',
        y: 'y_pred',
        stroke: style.color,
        strokeWidth: 2,
        strokeDasharray: style.dash ?? undefined,
        curve: 'linear',
      }),
    );
  }

  const title = (day: Day): string => tooltip(day, models, f, format.titleDate(day.at), strings);

  marks.push(
    Plot.line(days, { x: 'at', y: 'y_true', stroke: SERIES.history, strokeWidth: 2.2, curve: 'linear' }),
    Plot.dot(days, {
      x: 'at',
      y: 'y_true',
      fill: SERIES.history,
      r: days.length > 20 ? 2.2 : 3,
      title,
      tip: true,
    }),
  );

  // Valin ulkopuoliset paivat samalla merkilla kuin hajontakuviossa: risti. Vain yhden
  // mallin nakymassa, koska kahdella mallilla samassa pisteessa merkki ei kertoisi
  // kumman vali petti; silloin vastaus luetaan vyohykkeista ja kaavion alta.
  if (models.length === 1) {
    const only = models[0];
    const outside = only
      ? days.filter((day) => day.predictions.some((item) => item.model === only.name && !item.covered))
      : [];
    if (outside.length > 0) {
      marks.push(
        Plot.dot(outside, {
          x: 'at',
          y: 'y_true',
          stroke: SERIES.history,
          symbol: () => 'cross',
          r: 5,
          strokeWidth: 1.8,
          title,
          tip: true,
        }),
      );
    }
  }

  return Plot.plot({
    ...baseOptions(width, height),
    x: { type: 'utc', label: null, tickFormat: format.tickDay, ticks: width < 480 ? 4 : 7 },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    marks,
  });
}

function tooltip(
  day: Day,
  models: OriginWeeksModel[],
  f: Formatters,
  when: string,
  strings: ChartStrings,
): string {
  const lines = [strings.originWeekTipHead(when, day.horizon_days, f.int(day.y_true))];
  for (const model of models) {
    const prediction = day.predictions.find((item) => item.model === model.name);
    if (!prediction) continue;
    lines.push(
      strings.originWeekTipModel(
        model.label,
        f.int(prediction.y_pred),
        f.int(prediction.p10),
        f.int(prediction.p90),
      ) + (prediction.covered ? '' : ` ${strings.originWeekTipOutside}`),
    );
  }
  return lines.join('\n');
}

/** Tyhja tila kaavion tilalla. Sama sailio, jotta sivun korkeus ei hyppaa. */
function note(message: string): HTMLElement {
  const element = document.createElement('p');
  element.className = 'rounded-md border border-line bg-canvas px-4 py-6 text-sm leading-6 text-ink-muted';
  element.textContent = message;
  return element;
}
