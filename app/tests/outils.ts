/** Lecture des fichiers de données depuis les tests (chemins relatifs au dossier app/). */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const RACINE_APP = resolve(dirname(fileURLToPath(import.meta.url)), '..');

export function cheminApp(...morceaux: string[]): string {
  return resolve(RACINE_APP, ...morceaux);
}

export function lireJson(...morceaux: string[]): unknown {
  return JSON.parse(readFileSync(cheminApp(...morceaux), 'utf8'));
}

export function existe(...morceaux: string[]): boolean {
  return existsSync(cheminApp(...morceaux));
}
