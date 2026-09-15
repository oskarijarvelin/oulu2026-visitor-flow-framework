/**
 * Valittu sarja jaettuna sivun skriptin ja kaaviosaarekkeiden valilla.
 *
 * Sama ratkaisu kuin `runstate.ts`: tila asuu juurielementin data-attribuutissa eika
 * muuttujassa, koska saarekkeet heraavat `client:visible`-direktiivilla eri aikoina.
 * Myohassa heraava saareke lukee voimassa olevan sarjan suoraan dokumentista sen sijaan
 * etta jaisi odottamaan seuraavaa tapahtumaa. Selain on ainoa paikka jossa tama ajetaan.
 */

/** Tapahtuma jonka sivun skripti lahettaa kun sarja vaihtuu. */
export const SERIES_EVENT = 'ovf:series';

/** `document.documentElement.dataset`-avain. HTML-muodossa `data-series`. */
export const SERIES_DATASET_KEY = 'series';

export interface SeriesChangeDetail {
  series: string;
}

/** Voimassa oleva sarja, tai `fallback` jos sivun skripti ei ole viela ehtinyt ajaa. */
export function currentSeries(fallback: string): string {
  const value = document.documentElement.dataset[SERIES_DATASET_KEY];
  return value === undefined || value === '' ? fallback : value;
}

/** Kirjaa sarjan vaihtumisen kuuntelijan. Palauttaa funktion joka purkaa kuuntelun. */
export function onSeriesChange(handler: (series: string) => void): () => void {
  const listener = (event: Event): void => {
    const detail = (event as CustomEvent<SeriesChangeDetail>).detail;
    if (detail && typeof detail.series === 'string' && detail.series !== '') handler(detail.series);
  };
  document.addEventListener(SERIES_EVENT, listener);
  return () => document.removeEventListener(SERIES_EVENT, listener);
}

/** Sarjan tunnus osoitteen hash-osasta, esimerkiksi `#series=tickets_sold`. */
export function seriesFromHash(hash: string): string | null {
  const match = /(?:^#|&)series=([^&]+)/.exec(hash);
  if (!match || match[1] === undefined) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}
