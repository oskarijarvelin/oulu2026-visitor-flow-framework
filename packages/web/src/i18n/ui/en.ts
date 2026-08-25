/**
 * English strings. Typed against the Finnish source, so a missing key or a changed
 * signature fails the type check rather than silently falling back.
 *
 * Every timestamp on the site is Finnish local time, in both languages. The English
 * pages describe the same instants, they do not convert them.
 */

import type { Translation } from './fi.ts';

export const en: Translation = {
  site: {
    name: 'Oulu2026 visitor flows',
    titleSuffix: 'Oulu2026 visitor flows',
    updatedAt: (when: string) => `Updated ${when}`,
    skipToContent: 'Skip to content',
    footerUnit:
      'Every figure is a visitor event: visitors_total is the sum of entries and exits, not a count of unique visitors. All times are Finnish local time.',
    footerRuns: (ingest: string, forecast: string) =>
      `Data fetched ${ingest}, forecast run ${forecast}. The site is static and is rebuilt on every run.`,
    footerAboutLink: 'Where the data comes from',
  },

  nav: {
    label: 'Main navigation',
    overview: 'Overview',
    weather: 'Weather',
    forecast: 'Forecast',
    quality: 'Quality',
    about: 'About',
    languageLabel: 'Language',
    switchTo: (language: string) => `Switch language to ${language}`,
    currentLanguage: (language: string) => `Current language: ${language}`,
  },

  banner: {
    region: 'Data quality',
    ok: 'Data is up to date',
    issues: 'Data quality needs attention',
    fetched: (when: string, hours: string) => `Last fetched ${when}, ${hours} hours ago.`,
    coverage: (last: string) => `Observations run through ${last}.`,
    source: (name: string, status: string) => `Source ${name}: ${status}`,
    forecastPrefix: 'Forecast:',
    skippedModels: (models: string) => `Skipped models: ${models}.`,
  },

  common: {
    textAlternative: 'Text alternative and table',
    day: 'Day',
    venue: 'Venue',
    model: 'Model',
    horizon: 'Horizon',
    observations: 'Observations',
    observationCount: (count: string) => `${count} observations`,
    days: 'Days',
    mean: 'Mean',
    median: 'Median',
    largest: 'Highest',
    hour: 'Hour',
    visitorEvents: 'Visitor events',
    countUnit: 'visitor events',
    temperature: 'Temperature',
    precipitation: 'Precipitation',
    weather: 'Weather',
    notes: 'Notes',
    holiday: 'holiday',
    rain: 'rain',
    partialDay: 'partial day',
    forecastRow: 'forecast',
    climatologyRow: 'weather from climatology',
    entries: 'In',
    exits: 'Out',
    production: 'production',
  },

  home: {
    title: 'Overview',
    heading: 'Visitor flows at a glance',
    description: 'Oulu2026: visitor counts, weather, tickets and a seven-day forecast for two venues.',
    lead: (historyDays: number, forecastDays: number, from: string, to: string) =>
      `The last ${historyDays} days and the next ${forecastDays} days for both venues, side by side. Observations start ${from} and run through ${to}.`,
    keyFigures: 'Key figures',
    keyFiguresNote:
      'Every figure is a visitor event: the sum of entries and exits, not unique visitors. One visit typically produces two events.',
    last30Total: 'Last 30 days, combined',
    last30TotalNote: 'Both venues together.',
    venueMean: (venue: string) => `${venue}, 30-day average`,
    perDay: '/ day',
    changeNote: (peakDate: string, peak: string) =>
      `Compared with the preceding 30 days. Busiest day ${peakDate}: ${peak}.`,
    next7: 'Forecast, next 7 days',
    next7Note: (model: string) => `Median, ${model}. The uncertainty band is shown in the charts below.`,
    panelTitle: (venue: string, historyDays: number, forecastDays: number) =>
      `${venue}: last ${historyDays} days and next ${forecastDays} days`,
    panelDescription: (model: string, mm: string) =>
      `The solid line is the observed count, the dashed line is the median forecast from ${model}, and the pale band is its p10 to p90 interval. A bluish background marks a day with at least ${mm} mm of rain.`,
    panelFootnote: (capacity: string, hours: string) =>
      `Capacity ${capacity} people. Opening hours derived from the data: ${hours}.`,
    panelAria: (venue: string, historyDays: number, forecastDays: number) =>
      `Time series: ${venue}, visitor events per day for the last ${historyDays} days and the forecast for the next ${forecastDays} days.`,
    panelAlternative: (from: string, to: string, total: string, mean: string, next7: string) =>
      `Between ${from} and ${to} the venue recorded ${total}, an average of ${mean} per day. The forecast for the next seven days is ${next7} as a median.`,
    tableCaption: (venue: string) => `${venue}: observed and forecast counts by day`,
    actual: 'Observed',
    forecastP50: 'Forecast p50',
    interval: 'p10 to p90',
    freshness: 'Data freshness',
    noMissingHours: 'No missing hours.',
    missingHours: (count: string) => `${count} missing hours.`,
    staleTitle: 'The forecast starts from a stale level',
    staleBody: (lastDay: string, runDate: string, lagDays: number) =>
      `The last observed day is ${lastDay}, while the forecast was run on ${runDate}, ${lagDays} days later. The forecast starts at the end of the observations, not today. The same warning is recorded in the forecast manifest.`,
    freshTitle: 'The forecast starts at the end of the observations',
    freshBody: (runDate: string, lastDay: string) =>
      `The forecast was run on ${runDate} and starts from ${lastDay}, the last observed day. Observations and forecast are therefore in step.`,
    contextHeading: 'Context data: the city traffic counter',
    contextBody: (site: string) =>
      `The Oulu traffic counter at ${site} is one measurement point in the city. It belongs to neither venue and is never combined into a venue-level visitor metric. It is here only as background on how the city moves.`,
    contextNumbers: (from: string, to: string, pedestrians: string, cyclists: string) =>
      `Between ${from} and ${to} the counter logged ${pedestrians} pedestrians and ${cyclists} cyclists.`,
    contextLink: 'More on the weather page',
  },

  venue: {
    description: (venue: string) =>
      `${venue}: visitor events by hour and by day, weekday profile, capacity and a ticket comparison.`,
    lead: (from: string, to: string, days: string, capacity: string) =>
      `The sensor has reported since ${from}. The data runs through ${to}, which is ${days} reporting days. Capacity ${capacity} people.`,
    wholePeriod: 'Whole period',
    wholePeriodNote: (entries: string, exits: string) => `In ${entries}, out ${exits}.`,
    dailyMean: 'Daily average',
    dailyMeanNote: (median: string) =>
      `Median ${median}. Variation is wide, so the median describes a typical day better.`,
    last30: 'Last 30 days',
    last30Note: 'Compared with the preceding 30 days.',
    busiestHour: 'Busiest hour',
    busiestHourNote: (hours: string) => `Opening hours derived from the data: ${hours}.`,

    dailyTitle: 'Visitor events by day',
    dailyDescription: (model: string, mm: string) =>
      `The solid line is the observed count, the dashed line the median forecast and the pale band its p10 to p90 interval. The forecast model is ${model}. A bluish background marks a day with at least ${mm} mm of rain, a dashed vertical line marks a public holiday.`,
    dailyFootnote:
      'The range selector changes the visible period. The forecast always starts at the end of the observations.',
    dailyAria: (venue: string) =>
      `Time series: ${venue}, visitor events per day plus a 30-day forecast.`,
    dailyAlternative: (
      from: string,
      to: string,
      total: string,
      mean: string,
      median: string,
      peakDate: string,
      peak: string,
      rainyDays: string,
      holidays: string,
    ) =>
      `Between ${from} and ${to} the venue recorded ${total}, an average of ${mean} per day and a median of ${median}. The busiest day was ${peakDate} with ${peak}. The period held ${rainyDays} rainy days and ${holidays} public holidays.`,
    dailyTableCaption: (venue: string) => `${venue}: the last 30 observed days`,

    hourlyTitle: 'Visitor events by hour',
    hourlyDescription: (days: string, from: string) =>
      `The hourly series covers the last ${days} days, starting ${from}. A bluish background marks an hour with at least 0.1 mm of rain.`,
    hourlyFootnote:
      'At night and outside opening hours the values are real zeros, not missing data.',
    hourlyAria: (venue: string, days: number) =>
      `Time series: ${venue}, visitor events per hour for the last ${days} days.`,
    hourlyAlternative: (hours: string, from: string, to: string, peak: string, rainHours: string, rainShare: string) =>
      `The hourly series holds ${hours} hours between ${from} and ${to}. The busiest single hour across the whole observation period was ${peak}. The window contains ${rainHours} rainy hours, or ${rainShare} percent. Hourly averages are in the weekday profile table below.`,

    heatmapTitle: 'Weekday and hour',
    heatmapDescription: (from: string, to: string, days: string) =>
      `Average visitor events by weekday and hour across the whole reporting period ${from} to ${to}, ${days} days.`,
    heatmapFootnote:
      'The map scrolls sideways on a narrow screen. A cell with no observations at all is grey and marked with a cross; a real zero is the lightest shade of the scale.',
    heatmapAria: (venue: string) => `Heatmap: ${venue}, average visitor events by weekday and hour.`,
    heatmapAlternative: (best: string) => `The busiest cell is ${best}. The table lists all 168 cells.`,
    heatmapBest: (weekday: string, hour: string, value: string) =>
      `${weekday} at ${hour}, on average ${value} visitor events per hour`,
    heatmapNoData: 'no observations',
    heatmapTableCaption: (venue: string) => `${venue}: average by weekday and hour`,

    capacityTitle: 'Entries relative to capacity',
    capacityDescription: (days: number, capacity: string) =>
      `Entries per hour during opening hours over the last ${days} days. The dashed line is the capacity of ${capacity} people.`,
    capacityFootnote:
      'This is not a simultaneous headcount. Dwell time is not measured, so the number of entries in an hour does not say how many people were present at the same time. It describes the pace of arrivals, not occupancy.',
    capacityAria: (venue: string) => `Line chart: ${venue}, entries per hour relative to capacity.`,
    capacityAlternative: (peak: string, over: string, observed: string, share: string) =>
      `The highest entries in a single hour during the period was ${peak}. Capacity was exceeded in ${over} of ${observed} observed hours, or ${share} percent.`,
    capacityTableCaption: (venue: string) => `${venue}: entries by hour`,
    capacityMean: 'Mean',
    capacityP95: '95th percentile',
    capacityUnit: 'entries per hour',
    capacityReference: (capacity: string) => `Capacity ${capacity}`,
    capacityAxis: 'Hour, Finnish local time →',

    ticketsTitle: 'Ticket comparison',
    ticketsDescription: (days: string, from: string, to: string) =>
      `Tickets sold and visitor events over the same period. Ticket data is maintained by hand and covers ${days} days between ${from} and ${to}.`,
    ticketsFootnote:
      'The two charts are drawn separately because the magnitudes differ. A ticket is not the same thing as a visitor event: one ticket can produce several events, and a group ticket covers many people.',
    ticketsVisitorsHeading: 'Visitor events',
    ticketsSoldHeading: 'Tickets sold',
    ticketsVisitorsAria: (venue: string) =>
      `Time series: ${venue}, visitor events per day for the ticket comparison.`,
    ticketsSoldAria: (venue: string) => `Time series: ${venue}, tickets sold per day.`,
    ticketsTotal: 'Tickets total',
    ticketsSingle: 'Single tickets',
    ticketsGroups: 'Group tickets',
    ticketsUnit: 'tickets',
    ticketsPerTicket: 'Events / ticket',
    ticketsNotComputable: 'not computable',
    ticketsRatio: (ratio: string) => `${ratio} visitor events per ticket sold`,
    ticketsAlternative: (sold: string, events: string, ratio: string) =>
      `The period sold ${sold} tickets and recorded ${events}. The ratio is ${ratio}. Do not read that ratio as a visitor count: some visitors arrive without a ticket, a group ticket covers several people, and every visit produces both an entry and an exit.`,
    ticketsTableCaption: (venue: string) =>
      `${venue}: tickets and visitor events, the last 30 days with ticket data`,
    ticketsTableLabel: (venue: string) => `${venue}: tickets and visitor events`,

    ticketWeekdayTitle: 'Tickets by weekday, rainy and dry days',
    ticketWeekdayDescription: (rainMm: string, days: string) =>
      `Mean tickets per day by weekday, split into dry and rainy days. A day counts as rainy when precipitation reaches ${rainMm} mm. Based on ${days} days that have both a ticket row and a weather observation.`,
    ticketWeekdayFootnote:
      'Each weekday holds only a few dozen observations, so the gap in any single pair is easily noise. Read this as a direction rather than a measure of what weather does: the summer season, public holidays and events fall on the same days as the weather, and this chart does not separate them.',
    ticketWeekdayAria: (venue: string) =>
      `Grouped bar chart: ${venue}, mean tickets per weekday with dry and rainy days side by side.`,
    ticketWeekdayDry: 'Dry',
    ticketWeekdayRainy: 'Rain',
    ticketWeekdayMeanColumn: 'Mean',
    ticketWeekdayMedianColumn: 'Median',
    ticketWeekdayDaysColumn: 'Days',
    ticketWeekdayDiffColumn: 'Difference',
    ticketWeekdayTooFew: (min: string) => `fewer than ${min} observations, not drawn`,
    ticketWeekdayAlternative: (dry: string, rainy: string, diff: string) =>
      `Dry days average ${dry} and rainy days ${rainy} tickets per day, a difference of ${diff}. The table below breaks the same split down by weekday.`,
    ticketWeekdayTableCaption: (venue: string) =>
      `${venue}: mean tickets by weekday and weather`,
    ticketWeekdayTableLabel: (venue: string) => `${venue}: tickets by weekday, rain and dry`,

    meaningTitle: 'What the figures mean',
    meaningBody1:
      'visitors_total is the sum of entries and exits. One visit typically produces two events, so the figure is not a count of unique visitors and it cannot simply be halved into visits: someone turning around at the door, staff walking through and the same person visiting twice all land in the same number.',
    meaningBody2: (from: string) =>
      `The sensor went live on ${from}. The zeros before that date are excluded from every average and profile, because they describe an uninstalled device rather than an empty space.`,
    compareLink: (venue: string) => `Compare with the other venue: ${venue}.`,
    contextNote: 'The city traffic counter is context data and belongs to neither venue, see the',
    contextNoteLink: 'about page',
  },

  weather: {
    title: 'Weather',
    heading: 'Weather and visitor counts',
    description:
      'How weather and visitor counts move together: a scatter plot, rainy versus dry days, and the distribution by weather class.',
    lead: 'Weather moves in step with the season, the programme and the school holidays. Everything on this page is covariation, not causation. Four and a half months of data cannot separate weather from season.',

    scatterTitle: 'Temperature and visitor events',
    scatterDescription:
      'One point is one day. The horizontal axis is the mean temperature of the day, the vertical axis the visitor events. Colour and symbol give the weather class, the size of the point the rainfall.',
    scatterFootnote:
      'The dashed line is a least-squares fit. It describes how the two quantities vary together and says nothing about causation.',
    scatterAria:
      'Scatter plot: mean daily temperature on the horizontal axis and visitor events on the vertical axis, coloured by weather class.',
    scatterAlternative: (days: string, min: string, max: string, mm: string, rainyDays: string) =>
      `The data holds ${days} days across both venues. The temperature axis spans ${min} to ${max} degrees Celsius. Rainfall reached at least ${mm} mm on ${rainyDays} days.`,
    scatterTableCaption: 'The ten busiest days with their weather',

    rainyTitle: 'Rainy and dry days',
    rainyDescription: (mm: string) =>
      `Average visitor events per day depending on whether at least ${mm} mm of rain fell. The same threshold as the model feature is_rainy_day.`,
    rainyFootnote:
      'Sample sizes are small and the distributions are skewed, so the gap between two bars is not a statistically strong result.',
    rainyAria: 'Bar chart: average visitor events on rainy and dry days, by venue.',
    rainyTableCaption: 'Rainy and dry days',
    dryLabel: (venue: string) => `${venue}, dry`,
    rainyLabel: (venue: string) => `${venue}, rainy`,
    dryNote: (mm: string) => `Rain below ${mm} mm`,
    rainyNote: (mm: string) => `Rain at least ${mm} mm`,
    group: 'Group',

    groupsTitle: 'Distribution by weather class',
    groupsDescription:
      'Average visitor events per day by WMO weather code group. The grouping is the same one the forecast model uses for its weather_group feature.',
    groupsFootnote:
      'Sample sizes vary a great deal between groups. The data holds only a handful of snow days, so their average is unstable.',
    groupsAria: 'Bar chart: average visitor events by weather class, by venue.',
    groupsTableCaption: 'Weather classes',
    venueAndWeather: 'Venue and weather class',

    trafficTitle: 'Context data: the city traffic counter',
    trafficDescription: (site: string) =>
      `The Oulu traffic counter at ${site}, pedestrians and cyclists per day. This is city traffic, not the visitor count of either venue.`,
    trafficFootnote:
      'The counter is one measurement point in Oulu. It is never combined into a venue-level metric and it is not venue 2 visitor data. It is here only as background on how the weather shows up in city movement.',
    trafficAria: (site: string) => `Time series: pedestrians and cyclists per day at the ${site} counter.`,
    trafficAlternative: (from: string, to: string, pedestrians: string, cyclists: string, pedMean: string, cycMean: string) =>
      `Between ${from} and ${to} the counter logged ${pedestrians} pedestrians and ${cyclists} cyclists, an average of ${pedMean} and ${cycMean} per day. Cycling rises steeply in spring, which shows in this series far more clearly than in any venue data.`,
    pedestrians: 'Pedestrians',
    cyclists: 'Cyclists',
    trafficUnit: 'passes',

    causationTitle: 'Why the effect of weather cannot be isolated',
    causationBody:
      'The data covers January to May 2026. Over that period the temperature climbs from about twenty degrees below zero to summer warmth, and everything else changes with it: the programme, the school holidays, the daylight and the tourist season. The model uses weather as a feature and it improves the forecast slightly, but the feature importances put wind ahead of temperature. That is a sign that the weather variables act as a stand-in for the season rather than as a mechanism.',
  },

  forecast: {
    title: 'Forecast',
    heading: 'Forecast: 7 days by hour, 30 days by day',
    description: 'Visitor forecasts for both venues, the uncertainty interval and a model comparison.',
    lead: (runAt: string, origin: string, model: string) =>
      `The forecast was run ${runAt} and starts from ${origin}, the last observed day. ${model} is shown by default, which is the production model. Every forecast is presented with its uncertainty interval, never as a single number.`,
    warningTitle: 'Read this before you use the numbers',
    warningWeather: (days: string) =>
      `Days 1 to ${days} use the weather forecast. After that the weather is climatology, a ten-year average. Average weather produces an average visitor count, so the far end of the horizon is systematically too flat. The boundary is marked in every chart.`,
    warningIntervals:
      'The prediction intervals are wide. They come from measured backtest error rather than from the model assumptions, and they honestly describe what four and a half months of data can say. For precise resourcing they are too wide.',
    next7: (venue: string) => `${venue}, next 7 days`,
    next7Note: (low: string, high: string) =>
      `Interval ${low} to ${high}. The sum is a sum of per-day intervals, so it is wider than the interval of the period itself.`,
    dailyMean: (venue: string) => `${venue}, daily average`,
    dailyMeanNote: (mean: string) => `For comparison, the last 30 observed days: ${mean} per day.`,
    panelTitle: (venue: string) => `${venue}: forecast`,
    panelDescription:
      'The dashed line is the median forecast and the pale band its p10 to p90 interval. The model selector switches models, the granularity selector switches between hourly and daily. The legend gives each model backtest MAE at the near horizon.',
    panelFootnote: (from: string) =>
      `From ${from} onwards the background is pale brown and the line becomes dotted: the weather for those days is climatology, not a weather forecast. The difference survives in greyscale.`,
    panelAria: (venue: string) =>
      `Forecast chart: ${venue}, median forecast and p10 to p90 interval for 30 days and for 7 days by hour.`,
    panelAlternative: (
      venue: string,
      model: string,
      from: string,
      to: string,
      total: string,
      weatherDays: number,
      climFrom: number,
      horizon: number,
      mae: string,
    ) =>
      `${venue}: ${model} forecasts a total of ${total} as a median for ${from} to ${to}. Days 1 to ${weatherDays} rest on the weather forecast, days ${climFrom} to ${horizon} on climatology. Backtest MAE at the near horizon is ${mae} visitor events per day.`,
    tableCaption: (venue: string, model: string) => `${venue}: ${model}, the 30-day forecast`,
    horizonColumn: 'Day',
    weatherSource: 'Weather source',
    weatherAndHolidays: 'Weather and holidays',
    comparisonHeading: 'Model comparison',
    comparisonLead: (model: string) =>
      `The same figure for both models by horizon bucket. Lower MAE is better. The production model is ${model}, because it is the only one that beats both benchmarks at both venues. Fuller metrics and benchmarks are on the`,
    comparisonLink: 'quality page',
    comparisonCaption: 'Backtest MAE by model and horizon bucket',
    maeFor: (bucket: string) => `MAE ${bucket}`,
    granularityDaily: '30 days, daily',
    granularityHourly: '7 days, hourly',
    bothModels: 'Both',
    maeNote: (value: string) => `backtest MAE 1-7 days ${value}`,
  },

  quality: {
    title: 'Quality',
    heading: 'Model quality: what the backtest says',
    description:
      'Backtest metrics, forecast versus actual, coverage and a comparison against simple benchmarks.',
    lead: 'Every figure on this page is measured, not estimated. They come from a rolling origin backtest, where the model is retrained at each past origin and asked for 30 days ahead. Coverage is measured by leaving the scored origin out of the interval fit, so it is not 80 percent by definition.',
    scaleTitle: 'Put the numbers next to the level',
    scaleBody: (venue: string, mae: string, mean: string, share: string) =>
      `The best baseline MAE at ${venue} is ${mae} visitor events per day, while an average day at that venue is ${mean}. The error is therefore about ${share} percent of the level. These forecasts describe the weekly rhythm and the rough level, not the count of any single day.`,
    venueLead: (trainingDays: string, origins: string, from: string, to: string) =>
      `${trainingDays} training days, ${origins} origins, backtest window ${from} to ${to}. Training always stops at the origin, including the level features and the hourly profile.`,

    maeTitle: 'MAE by horizon',
    maeDescription:
      'Mean absolute error by how many days the forecast is from its origin. Two simple benchmarks are included: the same weekday last time, and a 28-day moving average.',
    maeFootnote:
      'Each point averages only 8 to 10 observations, so the curves wobble. What matters is the level and the ordering of the models, not any single spike.',
    maeAria: (venue: string) =>
      `Line chart: ${venue}, mean absolute error as a function of horizon for four models.`,
    maeAxis: 'Horizon, days from the origin →',
    metricsCaption: (venue: string) => `${venue}: metrics by model and horizon bucket`,
    bias: 'Bias',
    coverage80: 'Coverage 80%',

    backtestTitle: 'Forecast versus actual',
    backtestDescription:
      'Each point is one forecast and the actual value that followed it in the backtest. The diagonal is a perfect hit: the distance from it is the error. Colour and symbol give the horizon bucket.',
    backtestFootnote:
      'The crosses are pairs where the actual value fell outside the p10 to p90 interval. The target is 20 percent.',
    backtestAria: (venue: string) =>
      `Scatter plot: ${venue}, forecast on the horizontal axis and actual on the vertical axis in the backtest.`,
    backtestAlternative: (pairs: string, origins: string) =>
      `The backtest holds ${pairs} forecast and actual pairs from ${origins} origins. Coverage and the other metrics are in the table above. Bias is positive almost everywhere: the models overestimate, because the visitor count falls through the spring and a level frozen at the origin does not follow it down.`,
    bandsCaption: (venue: string) => `${venue}: interval factors by horizon bucket`,
    p10Factor: 'p10 factor',
    p90Factor: 'p90 factor',

    benchmarkTitle: 'Does the model beat the benchmarks',
    benchmarkLead:
      'A ratio below one means the model is better than the benchmark. The benchmarks are deliberately naive: a model that cannot beat them is not worth maintaining.',
    benchmarkCaption: (venue: string) => `${venue}: ratio against the benchmarks`,
    benchmarkColumn: (benchmark: string) => `MAE ratio: ${benchmark}`,

    limitsHeading: 'Known limits',
    limitsLead:
      'These are recorded in the do_not_trust field of each venue metrics.json. They are not guesses about what might go wrong, but a list of situations where the measured accuracy does not hold.',
    lowCoverage: (entries: string) =>
      `Coverage fell below 70 percent in these: ${entries}. Their prediction intervals are too narrow.`,
    lowCoverageEntry: (venue: string, model: string, bucket: string, coverage: string) =>
      `${venue}, ${model}, ${bucket} (${coverage}%)`,
    limitBenchmarks:
      'The benchmarks are close. A 28-day moving average, which ignores the weekday entirely, trails the baseline by only a few percent at the near horizon. Most of the value of the model is in the weekly rhythm.',
    limitWeather:
      'At horizons 1 to 16 the backtest uses observed weather, while production uses a weather forecast. The error of the weather forecast therefore does not appear in these numbers. This is a known optimism.',
    limitYearly:
      'Neither model learns yearly seasonality, because the data does not hold a single full year. The seasonal features here measure the progress of spring, not a yearly cycle.',
  },

  about: {
    title: 'About',
    heading: 'Where the data comes from and what the figures mean',
    description: 'Sources, concepts, limits, and what the figures do not mean.',
    lead: 'This site is static. All data is computed at build time and the browser fetches nothing at runtime. The site is rebuilt after every data run.',

    conceptsHeading: 'Key concepts',
    conceptEventTitle: 'Visitor event, visitors_total',
    conceptEventBody1:
      'The sum of entries and exits. One visit typically produces two events: one in and one out. The figure is',
    conceptEventStrong: 'not',
    conceptEventBody2:
      'a count of unique visitors, and it cannot be halved into visits: someone turning around at the door, staff walking through and the same person visiting twice all land in the same number. The column is deliberately kept as a sum, because that is exactly what the counter measures.',
    conceptZeroTitle: 'A real zero and a missing observation',
    conceptZeroBody1: 'Each hourly row carries the column',
    conceptZeroBody2:
      ', which says whether the row came from the API or was filled with a zero. A closed hour is a real zero. The heatmap keeps the two apart: a real zero gets the lightest shade of the scale, a cell with no observations is drawn grey and marked with a cross.',
    conceptSensorTitle: 'Sensor commissioning',
    conceptSensorVenue: (venue: string, from: string) => `${venue} has reported since ${from}`,
    conceptSensorBody:
      'The zeros before that describe an uninstalled device, not an empty space. They are excluded from every average, every profile and the training of the forecast model.',
    conceptIntervalTitle: 'The p10 and p90 of the interval',
    conceptIntervalBody:
      'The tenth and ninetieth percentile of the forecast distribution. They are computed from measured backtest error, not from the internal assumptions of the model. The interval is wide, and it is an honest description of what four and a half months of data can say. This site never presents a forecast as a single number without its interval.',
    conceptRainTitle: 'Rainy day and rainy hour',
    conceptRainBody1: (mm: string) =>
      `A day is rainy when rainfall reaches at least ${mm} mm. An hour is a rainy hour when rainfall reaches at least 0.1 mm. The daily threshold is the same one used by the model feature`,
    conceptRainBody2: ', so the site and the model talk about the same weather.',
    conceptCapacityTitle: 'Capacity',
    conceptCapacityBody1: (venues: string) => `Capacity per venue is ${venues} people.`,
    conceptCapacityBody2:
      'The site compares hourly entries against it. That is not an occupancy rate: dwell time is not measured, so a simultaneous headcount cannot be derived from this data.',

    sourcesHeading: 'Sources',
    sourcesLead: (when: string, version: string) => `Last fetched ${when}, ingest version ${version}.`,
    sourcesCaption: 'Data sources and their status in the latest run',
    sourcesLabel: 'Data sources and their status',
    sourceColumn: 'Source',
    statusColumn: 'Status',
    rowsColumn: 'Rows',
    windowColumn: 'Window',
    sourceVisitors: 'Visitor counters',
    sourceVisitorsBody:
      'come from the Jaskaretail IoT API at hourly resolution, entries and exits separately.',
    sourceWeather: 'Weather',
    sourceWeatherBody: (days: number) =>
      `comes from Open-Meteo. Past weather is archive data; the future is a weather forecast for at most ${days} days ahead. After that the site uses climatology, a ten-year average.`,
    sourceTickets: 'Ticket sales',
    sourceTicketsBody:
      'is a hand-maintained CSV file. It does not update automatically and does not cover every day.',
    sourceCalendar: 'Holiday calendar',
    sourceCalendarBody: 'is a maintained file covering Finnish public holidays.',
    sourceTraffic: 'Traffic counter',
    sourceTrafficBody: 'is the Eco-Counter API of Oulu traffic. See the note below.',

    trafficHeading: 'Traffic data is context data',
    trafficBody1: (site: string, id: string) =>
      `The counter at ${site} (identifier ${id}) is one measurement point in Oulu. It measures walking and cycling on the street, not the visitors of either venue.`,
    trafficBody2Strong: 'is never combined',
    trafficBody2a: 'It',
    trafficBody2b:
      'into a venue-level visitor metric, and it is not venue 2 data. The previous application wired traffic data to a venue, which was misleading. Here it is its own series, marked as context data. It helps judge whether the city is moving more or less than usual, not how many people visited a venue.',
    trafficBody3: (from: string, to: string, pedestrians: string, cyclists: string, hours: string) =>
      `Between ${from} and ${to}: ${pedestrians} pedestrians and ${cyclists} cyclists, ${hours} measured hours.`,

    forecastHeading: 'About the forecast',
    forecastLead1: (production: string, comparison: string) =>
      `The production model is ${production}. ${comparison} runs alongside it as a benchmark, and its results appear on the`,
    forecastLink1: 'forecast page',
    forecastAnd: 'and the',
    forecastLink2: 'quality page',
    forecastLead2:
      'Both models forecast at the daily level; the hourly level comes from a shared hourly profile, so the hourly forecasts sum exactly to the daily one.',
    forecastCaption: 'Forecast basics by venue',
    forecastLabel: 'Forecast basics',
    originColumn: 'Origin',
    horizonColumn: 'Horizon',
    weatherNearColumn: 'Weather source, near days',
    weatherFarColumn: 'Weather source, far horizon',
    openingColumn: 'Opening hours',
    daysRange: (from: number, to: number) => `days ${from}-${to}:`,
    daysUnit: (days: number) => `${days} days`,
    openingHours: (hours: string) => hours,

    notHeading: 'What the figures do not mean',
    not1Strong: 'A visitor event is not a visitor.',
    not1Body:
      'It is one observation by the counter at the door. Dividing by two gives a rough estimate of visits, but it is an estimate rather than a measurement.',
    not2Strong: 'The link between weather and visitor counts is not causal.',
    not2Body:
      'The data covers January to May. Over that period everything besides the weather changes too: the programme, the school holidays, the daylight and the tourist season. This data cannot separate them.',
    not3Strong: 'The forecast does not know about future events.',
    not3Body:
      'The model sees past spikes in the data but knows nothing about next week concert. This is the single largest source of error.',
    not4Strong: 'The forecast is not accurate for an individual day.',
    not4Body: 'It describes the weekly rhythm and the rough level. The measured errors and their size relative to the level are on the',
    not4Link: 'quality page',
    not5Strong: 'The capacity comparison is not an occupancy rate.',
    not5Body: 'Dwell time is not measured.',
    not6Strong: 'Tickets are not visitors.',
    not6Body: 'A group ticket covers several people, and some visitors arrive without a ticket.',

    technicalHeading: 'Technical notes',
    technical1:
      'The site is a static Astro site. Data is packaged into JSON at build time and the browser fetches nothing at runtime. No server routes, no APIs, no external scripts.',
    technical2:
      'The build fails if the ingest manifest is more than 48 hours old, if the forecast files are missing, or if the input columns differ from what is expected. Stale data is never published as current.',
    technical3:
      'All times are Finnish local time, in the English version too. Daylight saving is already handled in the data: a local day can hold 23 or 25 hours, and the hourly shares are normalised over the hours the day actually has.',
    technical4: (built: string, age: string) =>
      `The site was built ${built}, when the ingest manifest was ${age} hours old.`,
  },
};
