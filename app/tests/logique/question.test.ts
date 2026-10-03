import { describe, expect, it } from 'vitest';
import { lireEntreesDemo, lireReponse } from '../../src/logique/contrat.ts';
import { insererAdresse, validerQuestion } from '../../src/logique/question.ts';
import { lireJson } from '../outils.ts';

describe('validerQuestion', () => {
  it('refuse ce que le serveur refuserait (moins de 3 ou plus de 2000 caractères)', () => {
    expect(validerQuestion('  ok ').valide).toBe(false);
    expect(validerQuestion('oui').valide).toBe(true);
    expect(validerQuestion('a'.repeat(2000))).toEqual({ valide: true, question: 'a'.repeat(2000) });
    const trop = validerQuestion('a'.repeat(2001));
    expect(trop.valide).toBe(false);
    if (!trop.valide) expect(trop.raison).toContain('2001');
  });
});

describe('insererAdresse', () => {
  it('commence une question vide par l’adresse, complète sinon', () => {
    expect(insererAdresse('', '12 Avenue de la Gare 64200 Biarritz')).toBe('Au 12 Avenue de la Gare 64200 Biarritz, ');
    expect(insererAdresse('Puis-je poser un abri de jardin  ', '8 Avenue Notre-Dame 64200 Biarritz')).toBe(
      'Puis-je poser un abri de jardin au 8 Avenue Notre-Dame 64200 Biarritz',
    );
  });
});

describe('lecture prudente des données', () => {
  it('lit les 8 réponses enregistrées de la démo', () => {
    const entrees = lireEntreesDemo(lireJson('public', 'donnees', 'demo.json'));
    expect(entrees.map((e) => e.id)).toEqual(['D04', 'D06', 'D11', 'D14', 'D21', 'D40', 'D35', 'D03']);
    for (const e of entrees) {
      expect(e.etapes.at(-1)?.id, e.id).toBe('fin');
      expect(e.lieu?.point, e.id).not.toBeNull();
    }
  });

  it('écarte les pages et les liens impossibles', () => {
    const r = lireReponse({
      verdict: 'non',
      texte: 'Non.',
      regles: [{ article: 'N 2', citation: 'Sont interdites…', page: null, verifiee: true }, { page: 4 }, 'rien'],
      demarche: { type: 'déclaration préalable', textes: [{ texte: 'R421-11', url: 'javascript:alert(1)' }] },
    })!;
    expect(r.regles).toEqual([{ article: 'N 2', citation: 'Sont interdites…', page: null, verifiee: true }]);
    expect(r.demarche?.textes).toEqual([{ texte: 'R421-11', url: '' }]);
    expect(r.a_verifier).toEqual([]);
    expect(lireReponse({})).toBeNull();
    expect(lireEntreesDemo('pas une liste')).toEqual([]);
  });
});
