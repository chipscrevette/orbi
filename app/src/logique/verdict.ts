/**
 * Du verdict brut du serveur (« oui sous conditions »…) au mot affiché et à sa couleur.
 * La couleur est collée au mot : vert pour oui, ambre pour oui sous conditions, rouge pour non, gris pour
 * « impossible à dire ». Un verdict inattendu reste lisible (en gris), jamais une erreur.
 */

export type Ton = 'vert' | 'ambre' | 'rouge' | 'gris' | 'bleu';
export type Humeur = 'repos' | 'reflechit' | 'contente' | 'inquiete';

export interface VerdictAffiche {
  cle: 'oui' | 'oui_conditions' | 'non' | 'impossible' | 'information' | 'hors_perimetre' | 'autre';
  libelle: string;
  ton: Ton;
  humeur: Humeur;
}

/** Minuscules, sans accents ni ponctuation, espaces simples. */
export function normaliserVerdict(brut: string): string {
  return brut
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function majuscule(texteBrut: string): string {
  const t = texteBrut.trim();
  return t ? t.charAt(0).toUpperCase() + t.slice(1) : t;
}

export function lireVerdict(brut: string | null | undefined): VerdictAffiche {
  const cle = normaliserVerdict(brut ?? '');
  if (cle === 'oui') return { cle: 'oui', libelle: 'Oui', ton: 'vert', humeur: 'contente' };
  if (/^oui sous conditions?$/.test(cle)) {
    return { cle: 'oui_conditions', libelle: 'Oui, sous conditions', ton: 'ambre', humeur: 'contente' };
  }
  if (cle === 'non') return { cle: 'non', libelle: 'Non', ton: 'rouge', humeur: 'inquiete' };
  if (cle === 'impossible a dire' || cle === 'impossible') {
    return { cle: 'impossible', libelle: 'Impossible à dire', ton: 'gris', humeur: 'inquiete' };
  }
  if (cle === 'information') return { cle: 'information', libelle: 'Information', ton: 'bleu', humeur: 'repos' };
  if (cle === 'hors perimetre') {
    return { cle: 'hors_perimetre', libelle: 'Hors périmètre', ton: 'gris', humeur: 'repos' };
  }
  return { cle: 'autre', libelle: majuscule(brut ?? '') || 'Sans verdict', ton: 'gris', humeur: 'repos' };
}
