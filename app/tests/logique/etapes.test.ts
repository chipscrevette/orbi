import { describe, expect, it } from 'vitest';
import { cleEvenement, etapeDeEvenement, regrouperEtapes } from '../../src/logique/etapes.ts';
import type { EvenementEtape, Lieu } from '../../src/logique/types.ts';

const D04: EvenementEtape[] = [
  { id: 'tri', t: 6.2 },
  { id: 'outils', t: 7.2 },
  { id: 'démarche', t: 7.2 },
  { id: 'articles', t: 7.3 },
  { id: 'analyse', t: 56.1 },
  { id: 'contrôle', t: 56.1 },
  { id: 'décision', t: 56.2 },
  { id: 'fin', t: 56.2 },
];

const LIEU: Lieu = {
  adresse: '32b Rue Petricot 64200 Biarritz',
  commune: 'Biarritz',
  point: [-1.560632, 43.471773],
  parcelle: 'BO 0015',
  surface_m2: 30650,
  zone: 'UH',
  servitudes: [],
  site_patrimonial: true,
};

const statuts = (evenements: EvenementEtape[], options = {}) =>
  regrouperEtapes(evenements, options).etapes.map((e) => e.statut);

describe('regrouperEtapes', () => {
  it('commence par « Je lis votre question » en cours', () => {
    const p = regrouperEtapes([]);
    expect(p.etapes).toHaveLength(6);
    expect(p.etapes.map((e) => e.statut)).toEqual(['en_cours', 'a_venir', 'a_venir', 'a_venir', 'a_venir', 'a_venir']);
    expect(p.dernier_t).toBe(0);
    expect(p.termine).toBe(false);
  });

  it('coche les étapes au fil des événements, l’étape suivante passe en cours', () => {
    expect(statuts(D04.slice(0, 1))).toEqual(['fait', 'en_cours', 'a_venir', 'a_venir', 'a_venir', 'a_venir']);
    expect(statuts(D04.slice(0, 4))).toEqual(['fait', 'fait', 'fait', 'en_cours', 'a_venir', 'a_venir']);
    expect(regrouperEtapes(D04.slice(0, 4)).dernier_t).toBe(7.3);
  });

  it('compte à chaque étape le temps qui la sépare de l’événement précédent', () => {
    const p = regrouperEtapes(D04);
    expect(p.termine).toBe(true);
    expect(p.etapes.every((e) => e.statut === 'fait')).toBe(true);
    const durees = p.etapes.map((e) => Math.round(e.duree_s * 10) / 10);
    expect(durees).toEqual([6.2, 1, 0.1, 48.8, 0, 0.1]);
    expect(p.etapes.reduce((s, e) => s + e.duree_s, 0)).toBeCloseTo(56.2, 6);
  });

  it('marque « non nécessaire » les étapes sautées quand le verrou de zone tranche', () => {
    const D35: EvenementEtape[] = [
      { id: 'tri', t: 5.7 },
      { id: 'outils', t: 47.2 },
      { id: 'démarche', t: 47.2 },
      { id: 'articles', t: 47.2 },
      { id: 'verrou de zone', t: 47.2 },
      { id: 'décision', t: 47.2 },
      { id: 'fin', t: 47.2 },
    ];
    const p = regrouperEtapes(D35, { lieu: { ...LIEU, parcelle: 'AM 0060', zone: 'UG' } });
    expect(p.etapes.map((e) => e.statut)).toEqual(['fait', 'fait', 'fait', 'saute', 'saute', 'fait']);
    expect(p.etapes[3]!.detail).toBe('non nécessaire');
    expect(p.etapes[1]!.detail).toBe('AM 0060 · zone UG · la zone suffit à trancher');
    expect(p.etapes[1]!.duree_s).toBeCloseTo(41.5, 6);
  });

  it('range un nom d’étape inconnu dans l’étape en cours, sans planter', () => {
    const evenements: EvenementEtape[] = [
      { id: 'tri', t: 6 },
      { id: 'outils', t: 7 },
      { id: 'articles', t: 8 },
      { id: 'rédaction', t: 40 },
      { id: 'garde-fous', t: 41 },
    ];
    const enCours = regrouperEtapes(evenements);
    expect(enCours.etapes[3]!.statut).toBe('en_cours');
    expect(enCours.etapes[3]!.extras).toEqual(['rédaction', 'garde-fous']);
    expect(enCours.etapes[3]!.duree_s).toBe(33);

    const fini = regrouperEtapes([...evenements, { id: 'correction', t: 50 }, { id: 'décision', t: 51 }, { id: 'fin', t: 51 }]);
    // L'étape 4 a reçu du travail (événements inconnus) : elle est faite, pas sautée.
    expect(fini.etapes.map((e) => e.statut)).toEqual(['fait', 'fait', 'fait', 'fait', 'saute', 'fait']);
    expect(fini.etapes[3]!.extras).toEqual(['rédaction', 'garde-fous', 'correction']);
  });

  it('range un événement inconnu reçu avant tout autre dans la première étape', () => {
    const p = regrouperEtapes([{ id: 'préparation', t: 0.5 }]);
    expect(p.etapes[0]!.extras).toEqual(['préparation']);
    expect(p.etapes[0]!.statut).toBe('en_cours');
  });

  it('reconnaît les noms sans accents ni casse', () => {
    expect(etapeDeEvenement('controle')).toBe(4);
    expect(etapeDeEvenement('DÉMARCHE')).toBe(2);
    expect(etapeDeEvenement('  Verrou   de zone ')).toBe(1);
    expect(etapeDeEvenement('rédaction')).toBeNull();
    expect(cleEvenement('Citation Recalée')).toBe('citation recalee');
  });

  it('détaille le terrain, les relances de K2 et les citations corrigées', () => {
    const p = regrouperEtapes(
      [
        { id: 'tri', t: 6 },
        { id: 'outils', t: 7 },
        { id: 'articles', t: 8 },
        { id: 'analyse', t: 40 },
        { id: 'nouvelle analyse', t: 70 },
        { id: 'citation recalée', t: 70 },
        { id: 'citation recalée', t: 70 },
        { id: 'référence normalisée', t: 70 },
        { id: 'contrôle', t: 70.1 },
      ],
      { lieu: LIEU },
    );
    expect(p.etapes[1]!.detail).toBe('BO 0015 · zone UH');
    expect(p.etapes[3]!.detail).toBe('2 passages');
    expect(p.etapes[4]!.detail).toBe('2 citations recalées · 1 référence normalisée');
    expect(p.etapes[5]!.statut).toBe('en_cours');
  });

  it('considère tout terminé quand on le dit, même sans « fin »', () => {
    expect(statuts(D04.slice(0, 2), { termine: true })).toEqual(['fait', 'fait', 'saute', 'saute', 'saute', 'saute']);
  });

  it('tolère un temps manquant ou qui recule', () => {
    const p = regrouperEtapes([
      { id: 'tri', t: 6 },
      { id: 'outils', t: Number.NaN },
      { id: 'articles', t: 5 },
    ]);
    expect(p.etapes.map((e) => e.duree_s)).toEqual([6, 0, 0, 0, 0, 0]);
    expect(p.dernier_t).toBe(6);
  });
});
