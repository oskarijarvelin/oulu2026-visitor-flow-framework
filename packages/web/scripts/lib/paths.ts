import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

/** packages/web */
export const WEB_ROOT = resolve(here, '..', '..');
/** Repo juuri */
export const REPO_ROOT = resolve(WEB_ROOT, '..', '..');
export const PROCESSED_DIR = resolve(REPO_ROOT, 'data', 'processed');
export const FORECAST_DIR = resolve(REPO_ROOT, 'data', 'forecasts', 'latest');
export const CONFIG_DIR = resolve(REPO_ROOT, 'config');
export const OUT_DIR = resolve(WEB_ROOT, 'src', 'data');
