/**
 * Valittu arviointiajo jaettuna sivun skriptin ja kaaviosaarekkeiden valilla.
 *
 * Tila asuu juurielementin data-attribuutissa eika muuttujassa, koska saarekkeet
 * heraavat `client:visible`-direktiivilla eri aikoina: myohassa heraava saareke lukee
 * voimassa olevan ajon suoraan dokumentista sen sijaan etta jaisi odottamaan seuraavaa
 * tapahtumaa. Selain on ainoa paikka jossa tama koodi ajetaan.
 */

/** Tapahtuma jonka sivun skripti lahettaa kun ajo vaihtuu. */
export const RUN_EVENT = 'ovf:accuracy-run';

/** `document.documentElement.dataset`-avain. HTML-muodossa `data-accuracy-run`. */
export const RUN_DATASET_KEY = 'accuracyRun';

export interface RunChangeDetail {
  run: string;
}

/** Voimassa oleva ajo, tai `fallback` jos sivun skripti ei ole viela ehtinyt ajaa. */
export function currentRun(fallback: string): string {
  const value = document.documentElement.dataset[RUN_DATASET_KEY];
  return value === undefined || value === '' ? fallback : value;
}

/** Kirjaa ajon vaihtumisen kuuntelijan. Palauttaa funktion joka purkaa kuuntelun. */
export function onRunChange(handler: (run: string) => void): () => void {
  const listener = (event: Event): void => {
    const detail = (event as CustomEvent<RunChangeDetail>).detail;
    if (detail && typeof detail.run === 'string' && detail.run !== '') handler(detail.run);
  };
  document.addEventListener(RUN_EVENT, listener);
  return () => document.removeEventListener(RUN_EVENT, listener);
}

/** Ajon tunnus osoitteen hash-osasta, esimerkiksi `#run=eval_v1_...`. */
export function runFromHash(hash: string): string | null {
  const match = /(?:^#|&)run=([^&]+)/.exec(hash);
  if (!match || match[1] === undefined) return null;
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return match[1];
  }
}
