/**
 * Vertailuviikot: yhden backtest-origon ennuste vastaan se mita todella tapahtui.
 *
 * Laatusivun hajontakuvio kertoo kuinka kaukana pisteet ovat lavistajasta, mutta se on
 * ajaton: siita ei nae milloin malli oli pielessa eika mihin suuntaan se ajautui paiva
 * paivalta. Tama kaavio ottaa yhden origon kerrallaan ja piirtaa sen ennusteen
 * kohdepaivien paalle, joten virhe luetaan aikajanalta.
 *
 * Toteuma on yhtenainen viiva, mallin mediaani katkoviiva ja p10 - p90 vaalea alue.
 * Valin ulkopuolelle jaaneet vuorokaudet saavat oman merkkinsa, samalla tavalla kuin
 * hajontakuviossa, jotta kaksi kaaviota luetaan samoilla silmilla.
 */

import { chartStrings, type ChartStrings } from '../i18n/charts.ts';
import type { Lang } from '../i18n/index.ts';
import { BAND_FILL, NEUTRAL, SERIES, modelStyle } from '../lib/colors.ts';
import { addDays, plotDay } from '../lib/dates.ts';
import { formatters } from '../lib/format.ts';
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

export interface OriginWeekPoint {
  model: string;
  origin_date: string;
  horizon_days: number;
  y_true: number;
  y_pred: number;
  p10: number;
  p90: number;
}

export interface OriginWeeksProps {
  lang: Lang;
  ariaLabel: string;
  points: OriginWeekPoint[];
  models: { name: string; label: string }[];
  defaultModel: string;
  /** Origot vanhimmasta uusimpaan. Oletuksena valitaan viimeisin. */
  origins: string[];
  [key: string]: unknown;
}

interface Row {
  at: Date;
  target_date: string;
  horizon_days: number;
  y_true: number;
  y_pred: number;
  p10: number;
  p90: number;
  covered: boolean;
}

export default island<OriginWeeksProps>((element, props) => {
  const strings = chartStrings(props.lang);
  const f = formatters(props.lang);
  const frame = createChartFrame(element);

  // Uusin origo on se jonka kayttaja haluaa nahda ensimmaisena: "mita viime viikolle
  // luvattiin ja miten siina kavi".
  let origin = props.origins.at(-1) ?? '';
  let model = props.defaultModel;
  let redraw = (): void => {};

  const rowsNow = (): Row[] => rowsFor(props.points, origin, model);

  const note = document.createElement('p');
  note.className = 'mt-3 text-xs leading-5 text-ink-muted';

  const updateNote = (): void => {
    const rows = rowsNow();
    if (rows.length === 0) {
      note.textContent = strings.originWeekEmpty;
      return;
    }
    const mae = rows.reduce((sum, row) => sum + Math.abs(row.y_pred - row.y_true), 0) / rows.length;
    const bias = rows.reduce((sum, row) => sum + (row.y_pred - row.y_true), 0) / rows.length;
    const outside = rows.filter((row) => !row.covered).length;
    note.textContent = strings.originWeekNote(
      f.date(origin),
      rows.length,
      f.decimal(mae),
      f.decimal(Math.abs(bias)),
      bias >= 0 ? strings.originWeekOver : strings.originWeekUnder,
      outside,
    );
  };

  const renderLegend = (): void => {
    const style = modelStyle(model);
    const label = props.models.find((entry) => entry.name === model)?.label ?? model;
    const entries: LegendEntry[] = [
      { label: strings.actual, color: SERIES.history },
      { label, color: style.color, dash: style.dash },
      { label: strings.interval, color: BAND_FILL, swatch: true },
    ];
    frame.legend.replaceChildren(createLegend(entries), note);
    updateNote();
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
    const toggle = createToggleGroup(
      strings.modelLabel,
      props.models.map((entry) => ({ value: entry.name, label: entry.label })),
      model,
      (value) => {
        model = value;
        renderLegend();
        redraw();
      },
    );
    frame.controls.append(toggle.element);
  }

  renderLegend();

  redraw = mountResponsive(
    frame.plot,
    (width) => draw(width, rowsNow(), modelStyle(model), props.lang, strings),
    { ariaLabel: props.ariaLabel },
  );
});

function rowsFor(points: OriginWeekPoint[], origin: string, model: string): Row[] {
  return points
    .filter((point) => point.origin_date === origin && point.model === model)
    .map((point) => {
      const target = addDays(point.origin_date, point.horizon_days);
      return {
        at: plotDay(target),
        target_date: target,
        horizon_days: point.horizon_days,
        y_true: point.y_true,
        y_pred: point.y_pred,
        p10: point.p10,
        p90: point.p90,
        covered: point.y_true >= point.p10 && point.y_true <= point.p90,
      };
    })
    .sort((a, b) => a.horizon_days - b.horizon_days);
}

function draw(
  width: number,
  rows: Row[],
  style: { color: string; dash: string | null },
  lang: Lang,
  strings: ChartStrings,
): SVGSVGElement | HTMLElement {
  if (rows.length === 0) return note(strings.originWeekEmpty);

  const f = formatters(lang);
  const format = chartFormat(lang);
  const height = Math.max(220, Math.min(380, Math.round(width * 0.45)));
  const outside = rows.filter((row) => !row.covered);

  const title = (row: Row): string =>
    strings.originWeekTip(
      format.titleDate(row.at),
      row.horizon_days,
      f.int(row.y_true),
      f.int(row.y_pred),
      f.int(row.p10),
      f.int(row.p90),
    ) + (row.covered ? '' : `\n${strings.backtestOutside}`);

  return Plot.plot({
    ...baseOptions(width, height),
    x: { type: 'utc', label: null, tickFormat: format.tickDay, ticks: width < 480 ? 4 : 7 },
    y: { label: null, tickFormat: format.count, grid: true, zero: true },
    marks: [
      Plot.areaY(rows, {
        x: 'at',
        y1: 'p10',
        y2: 'p90',
        fill: BAND_FILL,
        fillOpacity: 0.55,
        curve: 'monotone-x',
      }),
      Plot.ruleY([0], { stroke: NEUTRAL.line }),
      Plot.line(rows, {
        x: 'at',
        y: 'y_pred',
        stroke: style.color,
        strokeWidth: 2,
        strokeDasharray: style.dash ?? undefined,
        curve: 'linear',
      }),
      Plot.line(rows, { x: 'at', y: 'y_true', stroke: SERIES.history, strokeWidth: 2.2, curve: 'linear' }),
      Plot.dot(rows, {
        x: 'at',
        y: 'y_true',
        fill: SERIES.history,
        r: rows.length > 20 ? 2.2 : 3,
        title,
        tip: true,
      }),
      // Valin ulkopuoliset paivat samalla merkilla kuin hajontakuviossa: risti.
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
    ],
  });
}

/** Tyhja tila kaavion tilalla. Sama sailio, jotta sivun korkeus ei hyppaa. */
function note(message: string): HTMLElement {
  const element = document.createElement('p');
  element.className = 'rounded-md border border-line bg-canvas px-4 py-6 text-sm leading-6 text-ink-muted';
  element.textContent = message;
  return element;
}
