/** Les jauges de la carte « Modèle local » et les libellés d'état, tirés de `GET /api/etat`. */
import { formatEnviron, formatGo, formatNombre, pluriel } from './format.ts';
import type { EtatGpu, EtatMemoire, EtatServeur } from './types.ts';

/** La jauge « temps de réponse » est pleine à 120 s. */
export const TEMPS_JAUGE_PLEINE_S = 120;

export type TonJauge = 'vert' | 'bleu' | 'ambre' | 'rouge';

export interface Jauge {
  /** Entre 0 et 1. */
  ratio: number;
  texte: string;
  ton: TonJauge;
}

function borne(x: number): number {
  return Math.min(1, Math.max(0, x));
}

function tonOccupation(ratio: number, tonNormal: TonJauge): TonJauge {
  if (ratio >= 0.95) return 'rouge';
  if (ratio >= 0.85) return 'ambre';
  return tonNormal;
}

export function jaugeGpu(gpu: EtatGpu | null): Jauge | null {
  if (!gpu || gpu.utilise_go === null || gpu.total_go === null || gpu.total_go <= 0) return null;
  const ratio = borne(gpu.utilise_go / gpu.total_go);
  return { ratio, texte: formatGo(gpu.utilise_go, gpu.total_go), ton: tonOccupation(ratio, 'vert') };
}

export function jaugeMemoire(memoire: EtatMemoire | null): Jauge | null {
  if (!memoire || memoire.utilise_go === null || memoire.total_go === null || memoire.total_go <= 0) return null;
  const ratio = borne(memoire.utilise_go / memoire.total_go);
  return { ratio, texte: formatGo(memoire.utilise_go, memoire.total_go), ton: tonOccupation(ratio, 'bleu') };
}

export function jaugeTemps(secondes: number | null): Jauge | null {
  if (secondes === null || !Number.isFinite(secondes) || secondes < 0) return null;
  const ratio = borne(secondes / TEMPS_JAUGE_PLEINE_S);
  return { ratio, texte: formatEnviron(secondes), ton: secondes > 90 ? 'ambre' : 'vert' };
}

/** « Biarritz · 189 articles · 493 passages · 178 zones » (seulement ce que le serveur donne). */
export function resumeBasePlu(etat: EtatServeur): string {
  const plu = etat.base.plu;
  const morceaux: string[] = [];
  if (plu.commune) morceaux.push(plu.commune);
  if (plu.articles !== null) morceaux.push(pluriel(plu.articles, 'article', 'articles'));
  if (plu.passages !== null) morceaux.push(pluriel(plu.passages, 'passage', 'passages'));
  if (plu.zones !== null) morceaux.push(pluriel(plu.zones, 'zone', 'zones'));
  return morceaux.join(' · ');
}

const NOMS_SERVICES: Readonly<Record<string, string>> = {
  k2: 'le modèle K2',
  embeddings: 'le serveur d’embeddings',
};

/** Les services locaux éteints, en clair (« le modèle K2 », « le serveur d’embeddings »). */
export function servicesEteints(etat: EtatServeur): string[] {
  return Object.entries(etat.services)
    .filter(([, actif]) => !actif)
    .map(([nom]) => NOMS_SERVICES[nom] ?? nom);
}

/** « 27 / 40 » */
export function resumeBanc(etat: EtatServeur): string | null {
  return etat.banc ? `${formatNombre(etat.banc.juste)} / ${formatNombre(etat.banc.total)}` : null;
}
