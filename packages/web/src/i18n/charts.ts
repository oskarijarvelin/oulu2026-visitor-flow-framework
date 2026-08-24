/**
 * Kaaviosaarekkeiden tekstit.
 *
 * Nama ovat erillaan sivujen sanastosta, koska saarekkeet paketoidaan selaimeen: vain
 * tama tiedosto paatyy asiakaspuolen nippuun, ei sivujen pitka leipateksti.
 *
 * Chart island strings live apart from the page dictionary because islands are bundled
 * for the browser. Only this file ships to the client.
 */

import type { Lang } from './index.ts';

export interface ChartStrings {
  rangeLabel: string;
  rangeDays: (days: number) => string;
  rangeAll: string;
  rangeDaysDescription: (days: number) => string;
  rangeAllDescription: string;

  metricLabel: string;
  mean: string;
  median: string;

  modelLabel: string;
  granularityLabel: string;
  granularityDaily: string;
  granularityHourly: string;
  bothModels: string;
  venueLabel: string;

  actual: string;
  forecastMedian: string;
  interval: string;
  climatologyBand: (fromDay: number) => string;
  /** Lyhyt selite; pitka muoto on vihjeessa. */
  climatologyLegend: string;
  climatologyTip: string;
  rainHours: string;
  rainDays: string;
  holiday: string;
  climatologyRule: (fromDay: number) => string;

  /** Vihjeen rivi valmiiksi muotoillulle maaralle. */
  forecastTip: (amount: string) => string;
  intervalTip: (low: string, high: string) => string;

  noObservations: string;
  zeroEvents: string;
  heatmapNote: string;
  heatmapAxis: string;
  heatmapCellTip: (weekday: string, hour: string) => string;
  heatmapMissingTip: string;
  heatmapValueTip: (metric: string, value: string) => string;
  heatmapCountTip: (n: number, zeros: number) => string;
  heatmapColorLabel: (metric: string) => string;

  scatterFit: (slope: string, r: string, n: number) => string;
  scatterFitMissing: string;
  scatterAxis: string;
  scatterClass: (venue: string) => string;
  scatterTip: (date: string, events: string, temp: string, rain: string, group: string) => string;

  backtestNote: (pairs: string, coverage: number) => string;
  backtestAxis: string;
  backtestBucketLabel: string;
  backtestTip: (origin: string, horizon: number, target: string, forecast: string, actual: string, low: string, high: string) => string;
  backtestOutside: string;

  capacityReference: string;
}

const FI: ChartStrings = {
  rangeLabel: 'Aikajakso',
  rangeDays: (days) => `${days} vrk`,
  rangeAll: 'Kaikki',
  rangeDaysDescription: (days) => `Viimeiset ${days} vuorokautta`,
  rangeAllDescription: 'Koko jakso',

  metricLabel: 'Tunnusluku',
  mean: 'Keskiarvo',
  median: 'Mediaani',

  modelLabel: 'Malli',
  granularityLabel: 'Tarkkuus',
  granularityDaily: '30 vrk, päivä',
  granularityHourly: '7 vrk, tunti',
  bothModels: 'Molemmat',
  venueLabel: 'Venue',

  actual: 'Toteuma',
  forecastMedian: 'Ennuste, mediaani',
  interval: 'Ennusteväli p10 - p90',
  climatologyBand: (fromDay) => `Sää klimatologiasta, vrk ${fromDay} alkaen`,
  climatologyLegend: 'Sää klimatologiasta',
  climatologyTip: 'Sää klimatologiasta, ei dynaamista ennustetta',
  rainHours: 'Sadetunnit',
  rainDays: 'Sadepäivät',
  holiday: 'Pyhäpäivä',
  climatologyRule: (fromDay) => `Vrk ${fromDay} alkaen: sää klimatologiaa`,

  forecastTip: (amount) => `Ennuste ${amount}`,
  intervalTip: (low, high) => `Väli ${low} - ${high}`,

  noObservations: 'Ei havaintoja',
  zeroEvents: 'Nolla kävijätapahtumaa',
  heatmapNote:
    'Väriskaala on vaaleasta tummaan ja säilyttää järjestyksensä myös harmaasävyisenä. Aukioloaikojen ulkopuoliset tunnit näkyvät vaaleina, koska niissä on aitoja nollia.',
  heatmapAxis: 'Tunti, Suomen aikaa',
  heatmapCellTip: (weekday, hour) => `${weekday} klo ${hour}`,
  heatmapMissingTip: 'Ei havaintoja',
  heatmapValueTip: (metric, value) => `${metric} ${value} kävijätapahtumaa`,
  heatmapCountTip: (n, zeros) => `${n} havaintoa, joista ${zeros} nollaa`,
  heatmapColorLabel: (metric) => `${metric}, kävijätapahtumaa tunnissa`,

  scatterFit: (slope, r, n) =>
    `Sovite: ${slope} kävijätapahtumaa lämpöastetta kohti, korrelaatiokerroin r = ${r}, ${n} vuorokautta. ` +
    'Korrelaatio ei ole syysuhde: lämpötila kulkee Oulussa käsi kädessä vuodenajan, ohjelmiston ja koulujen lomien kanssa, eikä sitä voi erottaa niistä tällä aineistolla.',
  scatterFitMissing: 'Sovitetta ei laskettu: havaintoja on liian vähän.',
  scatterAxis: 'Vuorokauden keskilämpötila, °C →',
  scatterClass: (venue) => `${venue}: säätilaluokka`,
  scatterTip: (date, events, temp, rain, group) =>
    `${date}\n${events}\n${temp}, sade ${rain}\n${group}`,

  backtestNote: (pairs, coverage) =>
    `${pairs} ennuste ja toteuma -paria. Toteuma osui p10 - p90 -välille ${coverage} prosentissa ` +
    'tapauksista; tavoite on 80. Lävistäjän yläpuolella oleva piste tarkoittaa että malli aliarvioi ' +
    'kyseisen vuorokauden, alapuolella että se yliarvioi.',
  backtestAxis: 'Ennuste, kävijätapahtumaa →',
  backtestBucketLabel: 'Horisontti, vuorokautta',
  backtestTip: (origin, horizon, target, forecast, actual, low, high) =>
    `Origo ${origin}, horisontti ${horizon} vrk\nKohdepäivä ${target}\n` +
    `Ennuste ${forecast}, toteuma ${actual}\nVäli ${low} - ${high}`,
  backtestOutside: 'Toteuma välin ulkopuolella',

  capacityReference: 'Kapasiteetti',
};

const EN: ChartStrings = {
  rangeLabel: 'Period',
  rangeDays: (days) => `${days} days`,
  rangeAll: 'All',
  rangeDaysDescription: (days) => `The last ${days} days`,
  rangeAllDescription: 'The whole period',

  metricLabel: 'Statistic',
  mean: 'Mean',
  median: 'Median',

  modelLabel: 'Model',
  granularityLabel: 'Granularity',
  granularityDaily: '30 days, daily',
  granularityHourly: '7 days, hourly',
  bothModels: 'Both',
  venueLabel: 'Venue',

  actual: 'Observed',
  forecastMedian: 'Forecast, median',
  interval: 'Interval p10 to p90',
  climatologyBand: (fromDay) => `Weather from climatology, day ${fromDay} onwards`,
  climatologyLegend: 'Weather from climatology',
  climatologyTip: 'Weather from climatology, not a dynamic forecast',
  rainHours: 'Rainy hours',
  rainDays: 'Rainy days',
  holiday: 'Public holiday',
  climatologyRule: (fromDay) => `Day ${fromDay} onwards: weather is climatology`,

  forecastTip: (amount) => `Forecast ${amount}`,
  intervalTip: (low, high) => `Interval ${low} to ${high}`,

  noObservations: 'No observations',
  zeroEvents: 'Zero visitor events',
  heatmapNote:
    'The colour scale runs light to dark and keeps its order in greyscale. Hours outside opening times stay pale because they hold real zeros.',
  heatmapAxis: 'Hour, Finnish local time',
  heatmapCellTip: (weekday, hour) => `${weekday} at ${hour}`,
  heatmapMissingTip: 'No observations',
  heatmapValueTip: (metric, value) => `${metric} ${value} visitor events`,
  heatmapCountTip: (n, zeros) => `${n} observations, ${zeros} of them zero`,
  heatmapColorLabel: (metric) => `${metric}, visitor events per hour`,

  scatterFit: (slope, r, n) =>
    `Fit: ${slope} visitor events per degree, correlation coefficient r = ${r}, ${n} days. ` +
    'Correlation is not causation: in Oulu the temperature moves hand in hand with the season, the programme and the school holidays, and this data cannot separate them.',
  scatterFitMissing: 'No fit was computed: too few observations.',
  scatterAxis: 'Mean daily temperature, °C →',
  scatterClass: (venue) => `${venue}: weather class`,
  scatterTip: (date, events, temp, rain, group) =>
    `${date}\n${events}\n${temp}, rain ${rain}\n${group}`,

  backtestNote: (pairs, coverage) =>
    `${pairs} forecast and actual pairs. The actual value fell inside the p10 to p90 interval in ` +
    `${coverage} percent of cases; the target is 80. A point above the diagonal means the model ` +
    'underestimated that day, below it that it overestimated.',
  backtestAxis: 'Forecast, visitor events →',
  backtestBucketLabel: 'Horizon, days',
  backtestTip: (origin, horizon, target, forecast, actual, low, high) =>
    `Origin ${origin}, horizon ${horizon} days\nTarget day ${target}\n` +
    `Forecast ${forecast}, actual ${actual}\nInterval ${low} to ${high}`,
  backtestOutside: 'Actual outside the interval',

  capacityReference: 'Capacity',
};

const CHART_STRINGS: Record<Lang, ChartStrings> = { fi: FI, en: EN };

export function chartStrings(lang: Lang): ChartStrings {
  return CHART_STRINGS[lang];
}
