/**
 * L'horloge affichée pendant le travail d'Orbi. En local, c'est le temps qui passe. En démo, le temps est compressé
 * (une réponse de 56 s rejouée en ~7 s) : l'horloge convertit le temps de démo écoulé en secondes réelles de
 * l'enregistrement, par interpolation entre les événements, pour que le minuteur montre les vraies durées en accéléré.
 */

export interface RepereChrono {
  demo_s: number;
  reel_s: number;
}

export type Chrono = { type: 'reel' } | { type: 'rejeu'; reperes: readonly RepereChrono[] };

export const CHRONO_REEL: Chrono = { type: 'reel' };

/** Secondes « réelles » correspondant à `ecoule_s` secondes écoulées depuis le début. */
export function tempsReel(chrono: Chrono, ecoule_s: number): number {
  const ecoule = Math.max(0, ecoule_s);
  if (chrono.type === 'reel') return ecoule;
  const reperes = chrono.reperes;
  if (reperes.length === 0) return ecoule;
  let precedent: RepereChrono = { demo_s: 0, reel_s: 0 };
  for (const repere of reperes) {
    if (ecoule <= repere.demo_s) {
      const largeur = repere.demo_s - precedent.demo_s;
      if (largeur <= 0) return repere.reel_s;
      const part = (ecoule - precedent.demo_s) / largeur;
      return precedent.reel_s + part * (repere.reel_s - precedent.reel_s);
    }
    precedent = repere;
  }
  return precedent.reel_s;
}
