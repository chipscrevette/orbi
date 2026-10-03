/**
 * Le mode démo : sans moteur local, l'interface rejoue les vraies réponses enregistrées de `donnees/demo.json`,
 * avec leurs étapes et leurs temps réels, en compressant le temps (~7 s au lieu d'une minute, proportions gardées).
 */
import type { RepereChrono } from './chrono.ts';
import { etapeDeEvenement, regrouperEtapes } from './etapes.ts';
import type { EntreeDemo, EvenementFlux, Reponse } from './types.ts';

/** Date du passage enregistré dans `donnees/demo.json`. */
export const DATE_DEMO = '2026-10-02';
/** Durée visée pour rejouer une réponse. */
export const CIBLE_DEMO_S = 7;
/** Écart minimal entre deux événements rejoués, pour que les étapes se cochent l'une après l'autre. */
export const ECART_MIN_DEMO_S = 0.15;

export interface OptionsCompression {
  cible_s?: number;
  ecart_min_s?: number;
}

export interface Compression {
  /** Combien de secondes réelles pour une seconde de démo. */
  facteur: number;
  temps_demo: number[];
}

/**
 * Compresse une suite de temps réels (secondes depuis le début) pour qu'elle tienne en `cible_s` secondes,
 * en gardant les proportions. Une réponse plus courte que la cible n'est jamais ralentie.
 */
export function compresserTemps(tempsReels: readonly number[], options: OptionsCompression = {}): Compression {
  const cible = options.cible_s ?? CIBLE_DEMO_S;
  const ecart = options.ecart_min_s ?? ECART_MIN_DEMO_S;
  if (tempsReels.length === 0) return { facteur: 1, temps_demo: [] };
  const propres = tempsReels.map((t) => (Number.isFinite(t) && t > 0 ? t : 0));
  const total = Math.max(...propres);
  const facteur = cible > 0 && total > cible ? total / cible : 1;
  const temps_demo: number[] = [];
  let precedent = 0;
  for (const t of propres) {
    const demo = Math.max(t / facteur, precedent + ecart);
    temps_demo.push(demo);
    precedent = demo;
  }
  return { facteur, temps_demo };
}

export interface EvenementPlanifie {
  /** Secondes de démo après le début. */
  a_s: number;
  evenement: EvenementFlux;
}

export interface PlanRejeu {
  evenements: EvenementPlanifie[];
  reperes: RepereChrono[];
  facteur: number;
  duree_reelle_s: number;
  duree_demo_s: number;
}

function dureeReelle(entree: EntreeDemo): number {
  const derniere = entree.etapes.at(-1)?.t ?? 0;
  return entree.duree_s ?? entree.reponse.duree_s ?? derniere;
}

/** La réponse enregistrée, complétée comme le serveur la complète (zone, durée, marque « démo »). */
export function reponseDeDemo(entree: EntreeDemo): Reponse {
  return {
    ...entree.reponse,
    zone: entree.reponse.zone ?? entree.lieu?.zone ?? null,
    duree_s: dureeReelle(entree),
    demo: true,
  };
}

/** Le calendrier des événements à rejouer : étapes, lieu (dès que le terrain est situé), puis la réponse. */
export function planifierRejeu(entree: EntreeDemo, options: OptionsCompression = {}): PlanRejeu {
  const { facteur, temps_demo } = compresserTemps(
    entree.etapes.map((e) => e.t),
    options,
  );
  const evenements: EvenementPlanifie[] = [];
  const reperes: RepereChrono[] = [];
  let lieuEnvoye = entree.lieu === null;
  entree.etapes.forEach((etape, i) => {
    const a_s = temps_demo[i] ?? 0;
    evenements.push({ a_s, evenement: { type: 'etape', etape } });
    reperes.push({ demo_s: a_s, reel_s: etape.t });
    // Le lieu est connu dès que l'étape « Je situe le terrain » est franchie.
    if (!lieuEnvoye && entree.lieu && etapeDeEvenement(etape.id) === 1) {
      evenements.push({ a_s, evenement: { type: 'lieu', lieu: entree.lieu } });
      lieuEnvoye = true;
    }
  });
  const fin_s = temps_demo.at(-1) ?? options.ecart_min_s ?? ECART_MIN_DEMO_S;
  if (!lieuEnvoye && entree.lieu) evenements.push({ a_s: fin_s, evenement: { type: 'lieu', lieu: entree.lieu } });
  evenements.push({ a_s: fin_s, evenement: { type: 'reponse', reponse: reponseDeDemo(entree) } });
  return { evenements, reperes, facteur, duree_reelle_s: dureeReelle(entree), duree_demo_s: fin_s };
}

/** Clé de comparaison d'une question : sans accents, casse, ponctuation ni espaces superflus. */
export function cleQuestion(question: string): string {
  return question
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

/** L'entrée de démo dont la question est celle posée (à la ponctuation et aux accents près), sinon `null`. */
export function trouverEntreeDemo(question: string, entrees: readonly EntreeDemo[]): EntreeDemo | null {
  const cle = cleQuestion(question);
  if (cle === '') return null;
  return entrees.find((e) => cleQuestion(e.question) === cle) ?? null;
}

/**
 * Durée médiane d'une étape (numérotée de 1 à 6) dans les réponses enregistrées où elle a eu lieu,
 * `null` si elle n'a jamais eu lieu. Sert à dire « d'habitude ~48 s » pendant la longue étape.
 */
export function dureeTypiqueEtape(entrees: readonly EntreeDemo[], numero: number): number | null {
  const durees = entrees
    .map((e) => regrouperEtapes(e.etapes, { termine: true }).etapes[numero - 1])
    .filter((etape) => etape !== undefined && etape.statut === 'fait')
    .map((etape) => etape!.duree_s)
    .sort((a, b) => a - b);
  if (durees.length === 0) return null;
  const milieu = Math.floor(durees.length / 2);
  return durees.length % 2 === 1 ? durees[milieu]! : (durees[milieu - 1]! + durees[milieu]!) / 2;
}

/** Durée moyenne des réponses enregistrées, `null` s'il n'y en a pas. */
export function dureeMoyenneDemo(entrees: readonly EntreeDemo[]): number | null {
  const durees = entrees.map(dureeReelle).filter((d) => d > 0);
  if (durees.length === 0) return null;
  return durees.reduce((a, b) => a + b, 0) / durees.length;
}
