/**
 * Arviointisivun esitysmuunnokset.
 *
 * Nama ajetaan build-aikana `AccuracyView.astro`-komponentissa, eivat selaimessa.
 * Tilastoja ei lasketa taalla: `accuracy.json` sisaltaa jo verdiktin, valit ja
 * mittarit, ja tama tiedosto vain jarjestaa ne kuvaajien ja taulukoiden muotoon.
 *
 * Yksi poikkeus on englanninkielinen verdikkikappale. `verdicts.json` sisaltaa valmiin
 * suomenkielisen kappaleen, joka naytetaan suomeksi sellaisenaan; englanninkielinen
 * vastine kootaan samoista rakenteisista kentista eika kaanneta merkkijonona.
 */

import type { AccuracySeriesPayload } from '../charts/accuracyseries.ts';
import type { AccuracyBarsPayload } from '../charts/accuracybars.ts';
import type { AccuracyIntervalsPayload, AccuracyIntervalRow } from '../charts/accuracyintervals.ts';
import type { AccuracyTotalsPayload } from '../charts/accuracytotals.ts';
import type { Lang } from '../i18n/index.ts';
import { ui, type Translation } from '../i18n/ui/index.ts';
import { MODEL_STYLE, SERIES, VERDICT_COLOR, VERDICT_MARK, modelStyle } from './colors.ts';
import { formatters, type Formatters } from './format.ts';
import { modelLabel, referenceLabel } from './labels.ts';
import type {
  AccuracyRun,
  AccuracyTotal,
  AccuracyVenue,
  Verdict,
} from './types.ts';

/** Ajot tunnuksen mukaan. Kooste lukee jasenikkunoidensa luvut tasta. */
export type RunIndex = Map<string, AccuracyRun>;

export function indexRuns(runs: AccuracyRun[]): RunIndex {
  return new Map(runs.map((run) => [run.run_id, run]));
}

export function venueOf(run: AccuracyRun | undefined, venueId: number): AccuracyVenue | undefined {
  return run?.venues.find((venue) => venue.venue_id === venueId);
}

/** Koosteen jasenikkunat jarjestyksessa, ikkuna-ajolla vain ajo itse. */
export function memberRuns(run: AccuracyRun, index: RunIndex): AccuracyRun[] {
  if (run.kind !== 'sweep') return [run];
  const ids = run.windows?.map((window) => window.run_id) ?? run.members;
  return ids.map((id) => index.get(id)).filter((entry): entry is AccuracyRun => entry !== undefined);
}

// --- Nimet -----------------------------------------------------------------

export function verdictWord(verdict: Verdict, t: Translation): string {
  if (verdict === 'better') return t.accuracy.verdictBetter;
  if (verdict === 'worse') return t.accuracy.verdictWorse;
  return t.accuracy.verdictNoDifference;
}

export function verdictShort(verdict: Verdict, t: Translation): string {
  if (verdict === 'better') return t.accuracy.verdictBetterShort;
  if (verdict === 'worse') return t.accuracy.verdictWorseShort;
  return t.accuracy.verdictNoDifferenceShort;
}

export function verdictMark(verdict: Verdict): string {
  return VERDICT_MARK[verdict] ?? VERDICT_MARK['no_difference']!;
}

export function verdictColor(verdict: Verdict): string {
  return VERDICT_COLOR[verdict] ?? VERDICT_COLOR['no_difference']!;
}

export function calibrationWord(verdict: string, t: Translation): string {
  if (verdict === 'too_narrow') return t.accuracy.calibrationTooNarrow;
  if (verdict === 'too_wide') return t.accuracy.calibrationTooWide;
  return t.accuracy.calibrationCalibrated;
}

export function biasWord(verdict: string, t: Translation): string {
  if (verdict === 'over_forecast') return t.accuracy.biasOver;
  if (verdict === 'under_forecast') return t.accuracy.biasUnder;
  return t.accuracy.biasUnbiased;
}

/** Etumerkillinen luku: nolla ei saa etumerkkia, positiivinen saa plussan. */
export function signed(value: number, f: Formatters, decimals = 1): string {
  return `${value > 0 ? '+' : ''}${f.decimal(value, decimals)}`;
}

export function signedPct(value: number, f: Formatters): string {
  return f.signedPct(value);
}

/** "1.4.2026 - 30.4.2026" tai "1 Apr 2026 - 30 Apr 2026". */
export function periodLabel(run: AccuracyRun, f: Formatters): string {
  return f.dateRange(run.first_day, run.last_day);
}

/** "2026-04-01..2026-04-30" -> lyhyt kielikohtainen vali. */
export function windowLabel(label: string, f: Formatters): string {
  const [from, to] = label.split('..');
  if (from === undefined || to === undefined) return label;
  return `${f.dateShort(from)} - ${f.dateShort(to)}`;
}

// --- Verdikkikappale -------------------------------------------------------

/**
 * Ajon verdikki kappaleena.
 *
 * Osio 3 kirjoittaa kappaleen molemmilla kielilla samoista luvuista samana paivana, joten
 * se naytetaan sellaisenaan. Kappaletta ei kaanneta selaimessa. Ennen kaksikielisyytta
 * tallennetuilla ajoilla toinen kappale puuttuu, ja se kootaan rakenteisista kentista.
 */
export function summaryParagraph(run: AccuracyRun, lang: Lang): string {
  const stored = lang === 'fi' ? run.summary_fi : run.summary_en;
  if (stored !== '') return stored;
  return composeSummary(run, lang);
}

export function composeSummary(run: AccuracyRun, lang: Lang): string {
  const t = ui(lang);
  const f = formatters(lang);
  const parts: string[] = [];

  if (run.kind === 'sweep') {
    parts.push(
      t.accuracy.summarySweepIntro(
        run.sweep ?? '',
        f.int(run.windows?.length ?? run.members.length),
        f.date(run.first_day),
        f.date(run.last_day),
        run.primary_weather_mode,
        run.reference_rule,
      ),
    );
  } else if (run.window) {
    parts.push(
      t.accuracy.summaryWindowIntro(
        f.date(run.window.test_start),
        f.date(run.window.test_end),
        f.int(run.window.horizon_days),
        f.date(run.window.origin),
        run.window.train_window,
        run.primary_weather_mode,
      ),
    );
  }

  for (const venue of run.venues) {
    for (const model of venue.models) {
      const name = modelLabel(model.model, lang);
      if (model.pooled) {
        const pooled = model.pooled;
        parts.push(
          t.accuracy.summaryVenueSweep(
            venue.venue_name,
            name,
            referenceLabel(pooled.reference, lang),
            f.int(pooled.n_windows),
            f.int(pooled.n_days),
          ),
          t.accuracy.windowSplit(
            f.int(pooled.windows_favouring),
            f.int(pooled.windows_opposing),
            f.int(pooled.windows_neutral),
          ),
          verdictSentence(pooled.verdict, pooled.mean_difference, pooled.ci_low, pooled.ci_high, t, f),
        );
        if (pooled.verdict === 'no_difference') {
          parts.push(
            t.accuracy.summaryMde(
              t.accuracy.pooledScope(f.int(pooled.n_windows), f.int(pooled.n_days)),
              f.decimal(pooled.mde),
              f.pct(pooled.mde_pct),
            ),
          );
        }
        continue;
      }

      const comparison = model.comparison;
      if (!comparison) continue;
      parts.push(
        t.accuracy.summaryVenueWindow(
          venue.venue_name,
          name,
          f.decimal(comparison.model_mae),
          referenceLabel(comparison.reference, lang),
          f.decimal(comparison.reference_mae),
        ),
        verdictSentence(
          comparison.verdict,
          comparison.mean_difference,
          comparison.ci_low,
          comparison.ci_high,
          t,
          f,
        ),
      );
      if (comparison.verdict === 'no_difference') {
        parts.push(
          t.accuracy.summaryMde(
            t.accuracy.windowScope(f.int(comparison.n)),
            f.decimal(comparison.mde),
            f.pct(comparison.mde_pct),
          ),
        );
      }
      if (model.total) {
        parts.push(
          t.accuracy.summaryTotal(
            f.int(model.total.predicted),
            f.int(model.total.actual),
            f.signedPct(model.total.difference_pct),
          ),
        );
      }
    }
  }

  parts.push(run.kind === 'sweep' ? t.accuracy.summarySweepClosing : t.accuracy.summaryWindowClosing);
  return parts.join(' ');
}

function verdictSentence(
  verdict: Verdict,
  difference: number,
  low: number,
  high: number,
  t: Translation,
  f: Formatters,
): string {
  const value = signed(difference, f);
  const lowText = signed(low, f);
  const highText = signed(high, f);
  if (verdict === 'better') return t.accuracy.summaryBetter(value, lowText, highText);
  if (verdict === 'worse') return t.accuracy.summaryWorse(value, lowText, highText);
  return t.accuracy.summaryNoDifference(value, lowText, highText);
}

// --- Kuvaajien syotteet ----------------------------------------------------

/**
 * Kuvaaja 1. Kooste piirtaa jasenikkunansa perakkain; sama paiva otetaan vain kerran,
 * jotta aikajana pysyy yksikasitteisena myos liukuvassa sweepissa.
 */
export function seriesPayload(
  run: AccuracyRun,
  venueId: number,
  index: RunIndex,
  lang: Lang,
): AccuracySeriesPayload | null {
  const members = memberRuns(run, index);
  const key = String(venueId);
  const dates: string[] = [];
  const seen = new Set<string>();
  const actual: number[] = [];
  const holidays: [string, string][] = [];
  const values = new Map<string, Map<string, { p50: number; p10?: number; p90?: number }>>();
  const mainModels = new Set<string>();

  for (const member of members) {
    const series = member.series?.[key];
    if (!series) continue;
    for (const model of member.models) mainModels.add(model);
    series.dates.forEach((date, position) => {
      if (seen.has(date)) return;
      seen.add(date);
      dates.push(date);
      actual.push(series.y_true[position] ?? 0);
      const name = series.holidays[date];
      if (name !== undefined) holidays.push([date, name]);
      for (const [model, columns] of Object.entries(series.models)) {
        const perDate = values.get(model) ?? new Map();
        perDate.set(date, {
          p50: columns.p50[position] ?? 0,
          ...(columns.p10 ? { p10: columns.p10[position] ?? 0 } : {}),
          ...(columns.p90 ? { p90: columns.p90[position] ?? 0 } : {}),
        });
        values.set(model, perDate);
      }
    });
  }

  if (dates.length === 0) return null;

  const order = [...dates].sort();
  const orderedActual = order.map((date) => actual[dates.indexOf(date)] ?? 0);
  const models = [...values.entries()]
    .sort(
      (a, b) =>
        Number(mainModels.has(b[0])) - Number(mainModels.has(a[0])) || a[0].localeCompare(b[0]),
    )
    .map(([name, perDate]) => {
      const main = mainModels.has(name);
      const payload = {
        name,
        label: modelLabel(name, lang),
        main,
        p50: order.map((date) => perDate.get(date)?.p50 ?? null),
        ...(main
          ? {
              p10: order.map((date) => perDate.get(date)?.p10 ?? null),
              p90: order.map((date) => perDate.get(date)?.p90 ?? null),
            }
          : {}),
      };
      return payload;
    });

  return {
    dates: order,
    y_true: orderedActual,
    holidays: holidays.sort((a, b) => a[0].localeCompare(b[0])),
    models,
  };
}

/** Kuvaaja 2: MAE horisonttikoreittain, ryhmana malli. */
export function horizonPayload(
  venue: AccuracyVenue | undefined,
  buckets: string[],
  lang: Lang,
): AccuracyBarsPayload | null {
  if (!venue || venue.horizon.length === 0) return null;
  const models = [...new Set(venue.horizon.map((row) => row.model))];
  return {
    bars: venue.horizon
      .filter((row) => buckets.includes(row.bucket))
      .map((row) => ({
        label: horizonLabel(row.bucket, lang),
        group: row.model,
        value: row.mae,
        n: row.n,
      })),
    groups: models.map((model, position) => ({
      key: model,
      label: modelLabel(model, lang),
      color: modelStyle(model).color,
      // Joka toinen viivoitetaan, jotta ryhmat erottuvat myos harmaasavyisena.
      hatch: position % 2 === 1,
    })),
  };
}

function horizonLabel(bucket: string, lang: Lang): string {
  return lang === 'fi' ? `${bucket} vrk` : `${bucket} days`;
}

/**
 * Kuvaaja 3: ero vertailukohtaan. Koosteessa yksi rivi per ikkuna ja kooste alimpana,
 * korostettuna: se on ajon paatulos, ei paras ikkuna.
 */
export function differencePayload(
  venue: AccuracyVenue | undefined,
  lang: Lang,
): AccuracyIntervalsPayload | null {
  if (!venue) return null;
  const t = ui(lang);
  const f = formatters(lang);
  const rows: AccuracyIntervalRow[] = [];
  const many = venue.models.length > 1;

  for (const model of venue.models) {
    const prefix = many ? `${modelLabel(model.model, lang)}: ` : '';
    for (const window of model.per_window ?? []) {
      rows.push({
        label: `${prefix}${windowLabel(window.label, f)}`,
        value: window.mean_difference,
        low: window.ci_low,
        high: window.ci_high,
        color: verdictColor(window.verdict),
        mark: verdictMark(window.verdict),
        tip: [
          `${modelLabel(model.model, lang)} vs. ${referenceLabel(window.reference, lang)}`,
          `${verdictShort(window.verdict, t)}: ${signed(window.mean_difference, f)}`,
          t.accuracy.intervalLabel(signed(window.ci_low, f), signed(window.ci_high, f)),
          `MDE ${f.decimal(window.mde)} (${f.pct(window.mde_pct)})`,
        ].join('\n'),
      });
    }
    const pooled = model.pooled;
    if (pooled) {
      rows.push({
        label: `${prefix}${t.accuracy.diffPooledRow}`,
        value: pooled.mean_difference,
        low: pooled.ci_low,
        high: pooled.ci_high,
        color: verdictColor(pooled.verdict),
        mark: verdictMark(pooled.verdict),
        emphasis: true,
        tip: [
          `${modelLabel(model.model, lang)} vs. ${referenceLabel(pooled.reference, lang)}`,
          `${verdictShort(pooled.verdict, t)}: ${signed(pooled.mean_difference, f)}`,
          t.accuracy.intervalLabel(signed(pooled.ci_low, f), signed(pooled.ci_high, f)),
          t.accuracy.pooledScope(f.int(pooled.n_windows), f.int(pooled.n_days)),
        ].join('\n'),
      });
    }
    const comparison = model.comparison;
    if (comparison) {
      rows.push({
        label: modelLabel(model.model, lang),
        value: comparison.mean_difference,
        low: comparison.ci_low,
        high: comparison.ci_high,
        color: verdictColor(comparison.verdict),
        mark: verdictMark(comparison.verdict),
        emphasis: true,
        tip: [
          `${modelLabel(model.model, lang)} vs. ${referenceLabel(comparison.reference, lang)}`,
          `${verdictShort(comparison.verdict, t)}: ${signed(comparison.mean_difference, f)}`,
          t.accuracy.intervalLabel(signed(comparison.ci_low, f), signed(comparison.ci_high, f)),
          `MDE ${f.decimal(comparison.mde)} (${f.pct(comparison.mde_pct)})`,
        ].join('\n'),
      });
    }
  }

  return rows.length === 0 ? null : { rows, reference: 0, referenceLabel: t.accuracy.diffZeroLabel, decimals: 1 };
}

/** Kuvaaja 4: jakson kokonaismaara. Koosteessa yksi pari per ikkuna. */
export function totalsPayload(
  venue: AccuracyVenue | undefined,
  lang: Lang,
  /** Ikkuna-ajon kokonaismaaralla ei ole omaa nimilappua, joten sivu antaa sen. */
  fallbackLabel: string,
): AccuracyTotalsPayload | null {
  if (!venue) return null;
  const f = formatters(lang);
  const many = venue.models.length > 1;
  const rows = venue.models.flatMap((model) => {
    const prefix = many ? `${modelLabel(model.model, lang)}: ` : '';
    const totals: AccuracyTotal[] = model.totals ?? (model.total ? [model.total] : []);
    return totals.map((total) => ({
      label: `${prefix}${total.label === undefined ? fallbackLabel : windowLabel(total.label, f)}`,
      predicted: total.predicted,
      actual: total.actual,
      p10: total.p10,
      p90: total.p90,
      unreliable: total.is_thin || total.is_drifted,
      differencePct: f.signedPct(total.difference_pct),
    }));
  });
  return rows.length === 0 ? null : { rows };
}

/** Kuvaaja 5: peittavyys ja Clopper-Pearsonin vali. Koosteessa yksi rivi per ikkuna. */
export function calibrationPayload(
  run: AccuracyRun,
  venueId: number,
  index: RunIndex,
  lang: Lang,
): AccuracyIntervalsPayload | null {
  const t = ui(lang);
  const f = formatters(lang);
  const members = memberRuns(run, index);
  const isSweep = run.kind === 'sweep';
  const rows: AccuracyIntervalRow[] = [];

  for (const member of members) {
    const venue = venueOf(member, venueId);
    if (!venue) continue;
    for (const model of venue.models) {
      const calibration = model.calibration;
      if (!calibration) continue;
      const word = calibrationWord(calibration.verdict, t);
      const label = isSweep
        ? `${modelLabel(model.model, lang)}: ${f.dateShort(member.first_day)}`
        : modelLabel(model.model, lang);
      rows.push({
        label,
        value: calibration.coverage,
        low: calibration.ci_low,
        high: calibration.ci_high,
        color: calibration.verdict === 'calibrated' ? SERIES.history : SERIES.forecast,
        mark: calibration.verdict === 'calibrated' ? VERDICT_MARK['no_difference']! : VERDICT_MARK['worse']!,
        emphasis: !isSweep,
        tip: [
          modelLabel(model.model, lang),
          `${f.pct(calibration.coverage * 100, 0)} (${f.int(calibration.covered)}/${f.int(calibration.n)})`,
          t.accuracy.intervalLabel(f.decimal(calibration.ci_low, 2), f.decimal(calibration.ci_high, 2)),
          word,
        ].join('\n'),
      });
    }
  }

  return rows.length === 0
    ? null
    : { rows, reference: 0.8, referenceLabel: t.accuracy.calibrationTarget, decimals: 3 };
}

/** Kuvaaja 6: sään kolme tilaa. `perfect` merkitaan aina ylarajaksi, ei tulokseksi. */
export function weatherPayload(
  run: AccuracyRun,
  venueId: number,
  index: RunIndex,
  lang: Lang,
): AccuracyBarsPayload | null {
  const t = ui(lang);
  const f = formatters(lang);
  const members = memberRuns(run, index);
  const isSweep = run.kind === 'sweep';
  const bars: AccuracyBarsPayload['bars'] = [];

  for (const member of members) {
    const venue = venueOf(member, venueId);
    if (!venue) continue;
    for (const model of venue.models) {
      const weather = model.weather_sensitivity;
      if (!weather) continue;
      const label = isSweep
        ? `${modelLabel(model.model, lang)}, ${f.dateShort(member.first_day)}`
        : modelLabel(model.model, lang);
      bars.push(
        { label, group: 'perfect', value: weather.perfect, note: t.accuracy.weatherPerfect },
        { label, group: 'operational', value: weather.operational },
        { label, group: 'climatology', value: weather.climatology },
      );
    }
  }

  return bars.length === 0
    ? null
    : {
        bars,
        groups: [
          // Perfect on viivoitettu, koska se ei ole tulos vaan ylaraja. Merkinta nakyy
          // sekä pylvaassa etta selitteessa.
          { key: 'perfect', label: t.accuracy.weatherPerfect, color: MODEL_STYLE['climatology_dow']!.color, hatch: true },
          { key: 'operational', label: t.accuracy.weatherOperational, color: SERIES.history },
          { key: 'climatology', label: t.accuracy.weatherClimatology, color: SERIES.compare },
        ],
      };
}
