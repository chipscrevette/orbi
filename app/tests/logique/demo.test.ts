import { describe, expect, it } from 'vitest';
import { tempsReel } from '../../src/logique/chrono.ts';
import { lireEntreesDemo } from '../../src/logique/contrat.ts';
import {
  compresserTemps,
  dureeMoyenneDemo,
  dureeTypiqueEtape,
  planifierRejeu,
  reponseDeDemo,
  trouverEntreeDemo,
} from '../../src/logique/demo.ts';
import { lireJson } from '../outils.ts';

const ENTREES = lireEntreesDemo(lireJson('public', 'donnees', 'demo.json'));
const D04 = ENTREES.find((e) => e.id === 'D04')!;

describe('compresserTemps', () => {
  it('fait tenir une réponse de 56 s en ~7 s, proportions gardées', () => {
    const { facteur, temps_demo } = compresserTemps([6.2, 7.2, 7.2, 7.3, 56.1, 56.1, 56.2, 56.2]);
    expect(facteur).toBeCloseTo(56.2 / 7, 6);
    expect(temps_demo[0]).toBeCloseTo(6.2 / facteur, 6);
    // la longue étape garde sa place : l'analyse arrive à ~7 s
    expect(temps_demo[4]).toBeCloseTo(7, 1);
    expect(temps_demo.at(-1)!).toBeGreaterThan(6.5);
    expect(temps_demo.at(-1)!).toBeLessThan(8);
  });

  it('espace les événements simultanés pour qu’ils se cochent l’un après l’autre', () => {
    const { temps_demo } = compresserTemps([1, 1, 1], { cible_s: 7, ecart_min_s: 0.15 });
    expect(temps_demo).toEqual([1, 1.15, 1.2999999999999998]);
    for (let i = 1; i < temps_demo.length; i += 1) expect(temps_demo[i]! - temps_demo[i - 1]!).toBeGreaterThanOrEqual(0.15 - 1e-9);
  });

  it('ne ralentit jamais une réponse déjà plus courte que la cible', () => {
    expect(compresserTemps([2, 4], { cible_s: 7, ecart_min_s: 0 })).toEqual({ facteur: 1, temps_demo: [2, 4] });
  });

  it('gère les cas vides et les valeurs illisibles', () => {
    expect(compresserTemps([])).toEqual({ facteur: 1, temps_demo: [] });
    const { temps_demo } = compresserTemps([Number.NaN, -3, 14], { cible_s: 7, ecart_min_s: 0 });
    expect(temps_demo).toEqual([0, 0, 7]);
  });
});

describe('planifierRejeu', () => {
  it('rejoue les étapes, le lieu dès le terrain situé, puis la réponse marquée « démo »', () => {
    const plan = planifierRejeu(D04);
    const types = plan.evenements.map((e) => (e.evenement.type === 'etape' ? e.evenement.etape.id : e.evenement.type));
    expect(types).toEqual(['tri', 'outils', 'lieu', 'démarche', 'articles', 'analyse', 'contrôle', 'décision', 'fin', 'reponse']);
    const derniere = plan.evenements.at(-1)!.evenement;
    expect(derniere.type).toBe('reponse');
    if (derniere.type === 'reponse') {
      expect(derniere.reponse.demo).toBe(true);
      expect(derniere.reponse.duree_s).toBe(56.2);
      expect(derniere.reponse.zone).toBe('UH');
    }
    expect(plan.duree_reelle_s).toBe(56.2);
  });

  it('rejoue chacune des réponses enregistrées en 6 à 8,5 s', () => {
    expect(ENTREES).toHaveLength(8);
    for (const entree of ENTREES) {
      const plan = planifierRejeu(entree);
      expect(plan.duree_demo_s).toBeGreaterThan(6);
      expect(plan.duree_demo_s).toBeLessThan(8.5);
      const instants = plan.evenements.map((e) => e.a_s);
      expect([...instants].sort((a, b) => a - b)).toEqual(instants);
    }
  });

  it('fournit une horloge qui affiche les secondes réelles en accéléré', () => {
    const plan = planifierRejeu(D04);
    const chrono = { type: 'rejeu', reperes: plan.reperes } as const;
    for (const repere of plan.reperes) expect(tempsReel(chrono, repere.demo_s)).toBeCloseTo(repere.reel_s, 6);
    const articles = plan.reperes[3]!;
    const analyse = plan.reperes[4]!;
    const milieu = (articles.demo_s + analyse.demo_s) / 2;
    expect(tempsReel(chrono, milieu)).toBeCloseTo((articles.reel_s + analyse.reel_s) / 2, 6);
    expect(tempsReel(chrono, 1000)).toBe(56.2);
    expect(tempsReel(chrono, -1)).toBe(0);
    expect(tempsReel({ type: 'reel' }, 12.5)).toBe(12.5);
  });

  it('complète la réponse comme le serveur', () => {
    const r = reponseDeDemo(D04);
    expect(r).toMatchObject({ demo: true, duree_s: 56.2, zone: 'UH', verdict: 'oui sous conditions' });
    expect(r.regles[0]).toMatchObject({ article: 'UH 10', page: 93, verifiee: true });
  });
});

describe('trouverEntreeDemo', () => {
  it('retrouve une question de démo malgré la ponctuation, la casse ou les accents', () => {
    expect(trouverEntreeDemo(D04.question, ENTREES)?.id).toBe('D04');
    const bousculee = D04.question.toUpperCase().replace(/[?,.]/g, '').normalize('NFD').replace(/[̀-ͯ]/g, '');
    expect(trouverEntreeDemo(`  ${bousculee} ?? `, ENTREES)?.id).toBe('D04');
  });

  it('ne confond pas une question libre avec une question de démo', () => {
    expect(trouverEntreeDemo('Puis-je construire une piscine au 3 rue du Port ?', ENTREES)).toBeNull();
    expect(trouverEntreeDemo('', ENTREES)).toBeNull();
    expect(trouverEntreeDemo('   ', [])).toBeNull();
  });
});

describe('dureeTypiqueEtape', () => {
  it('donne la médiane de la longue étape dans les réponses enregistrées', () => {
    // étape 4 (analyse − articles) : 48,8 · 53,2 · 46,9 · 45,3 · 57 · 46,3 ; absente quand le verrou de zone tranche
    expect(dureeTypiqueEtape(ENTREES, 4)).toBeCloseTo((46.9 + 48.8) / 2, 6);
    expect(dureeTypiqueEtape([], 4)).toBeNull();
    expect(dureeTypiqueEtape(ENTREES, 9)).toBeNull();
  });
});

describe('dureeMoyenneDemo', () => {
  it('fait la moyenne des durées réelles enregistrées', () => {
    const attendu = ENTREES.reduce((s, e) => s + (e.duree_s ?? 0), 0) / ENTREES.length;
    expect(dureeMoyenneDemo(ENTREES)).toBeCloseTo(attendu, 6);
    expect(dureeMoyenneDemo([])).toBeNull();
  });
});
