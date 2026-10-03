import { describe, expect, it } from 'vitest';
import { lireVerdict } from '../../src/logique/verdict.ts';

describe('lireVerdict', () => {
  it('colle la bonne couleur à chaque verdict', () => {
    expect(lireVerdict('oui')).toMatchObject({ libelle: 'Oui', ton: 'vert', humeur: 'contente' });
    expect(lireVerdict('oui sous conditions')).toMatchObject({ libelle: 'Oui, sous conditions', ton: 'ambre' });
    expect(lireVerdict('non')).toMatchObject({ libelle: 'Non', ton: 'rouge', humeur: 'inquiete' });
    expect(lireVerdict('impossible à dire')).toMatchObject({ libelle: 'Impossible à dire', ton: 'gris' });
  });

  it('accepte les variantes d’écriture', () => {
    for (const v of ['Oui, sous conditions', 'OUI SOUS CONDITION', '  oui   sous conditions. ']) {
      expect(lireVerdict(v).cle).toBe('oui_conditions');
    }
    expect(lireVerdict('Impossible a dire').cle).toBe('impossible');
    expect(lireVerdict('NON').cle).toBe('non');
  });

  it('reste lisible pour un verdict imprévu ou absent', () => {
    expect(lireVerdict('information')).toMatchObject({ libelle: 'Information', ton: 'bleu' });
    expect(lireVerdict('hors périmètre')).toMatchObject({ libelle: 'Hors périmètre', ton: 'gris' });
    expect(lireVerdict('peut-être')).toMatchObject({ cle: 'autre', libelle: 'Peut-être', ton: 'gris' });
    expect(lireVerdict('')).toMatchObject({ libelle: 'Sans verdict', ton: 'gris' });
    expect(lireVerdict(null)).toMatchObject({ libelle: 'Sans verdict' });
    expect(lireVerdict(undefined).ton).toBe('gris');
  });
});
