import { describe, expect, it } from 'vitest';
import { lireEtat } from '../../src/logique/contrat.ts';
import {
  jaugeGpu,
  jaugeMemoire,
  jaugeTemps,
  resumeBanc,
  resumeBasePlu,
  servicesEteints,
} from '../../src/logique/etat.ts';

/** La réponse réelle de `GET /api/etat` (machine de développement, 2 octobre 2026). */
const ETAT_REEL = {
  mode: 'local',
  modele: { nom: 'K2 Horizon 7B', en_ligne: true },
  services: { k2: true, embeddings: true },
  gpu: { nom: 'RTX 3060', utilise_go: 8.3, total_go: 12.0 },
  memoire: { utilise_go: 15.0, total_go: 15.9 },
  temps_reponse_s: 65.6,
  base: {
    plu: { connectee: true, commune: 'Biarritz', articles: 189, passages: 493, zones: 178 },
    cadastre: { connectee: true, source: 'API Carto IGN' },
  },
  banc: { juste: 27, total: 40, date: '2026-10-02' },
};

describe('lireEtat', () => {
  it('lit l’état réel du serveur', () => {
    const etat = lireEtat(ETAT_REEL)!;
    expect(etat.mode).toBe('local');
    expect(etat.modele).toEqual({ nom: 'K2 Horizon 7B', en_ligne: true });
    expect(etat.gpu).toEqual({ nom: 'RTX 3060', utilise_go: 8.3, total_go: 12 });
    expect(etat.base.plu.passages).toBe(493);
    expect(etat.banc).toEqual({ juste: 27, total: 40, date: '2026-10-02' });
  });

  it('accepte les champs nuls ou absents', () => {
    const etat = lireEtat({ ...ETAT_REEL, mode: 'demo', gpu: null, memoire: null, services: { k2: false, embeddings: true }, banc: undefined })!;
    expect(etat.mode).toBe('demo');
    expect(etat.gpu).toBeNull();
    expect(etat.memoire).toBeNull();
    expect(etat.banc).toBeNull();
    expect(servicesEteints(etat)).toEqual(['le modèle K2']);
  });

  it('refuse ce qui ne ressemble pas à un état Orbi', () => {
    expect(lireEtat(null)).toBeNull();
    expect(lireEtat({})).toBeNull();
    expect(lireEtat('<html>')).toBeNull();
    expect(lireEtat({ detail: 'Not Found' })).toBeNull();
  });
});

describe('jauges', () => {
  it('donne des vraies valeurs, avec une couleur qui s’inquiète près du plein', () => {
    expect(jaugeGpu({ nom: 'RTX 3060', utilise_go: 8.3, total_go: 12 })).toEqual({
      ratio: 8.3 / 12,
      texte: '8,3 / 12 Go',
      ton: 'vert',
    });
    expect(jaugeGpu({ nom: 'RTX 3060', utilise_go: 11.6, total_go: 12 })!.ton).toBe('rouge');
    expect(jaugeMemoire({ utilise_go: 15, total_go: 15.9 })).toMatchObject({ texte: '15 / 15,9 Go', ton: 'ambre' });
    expect(jaugeMemoire({ utilise_go: 6, total_go: 16 })!.ton).toBe('bleu');
  });

  it('remplit la jauge de temps à 120 s', () => {
    expect(jaugeTemps(65.6)).toEqual({ ratio: 65.6 / 120, texte: '~66 s', ton: 'vert' });
    expect(jaugeTemps(130)!.ratio).toBe(1);
    expect(jaugeTemps(130)!.ton).toBe('ambre');
  });

  it('ne fabrique pas de jauge sans donnée', () => {
    expect(jaugeGpu(null)).toBeNull();
    expect(jaugeGpu({ nom: 'GPU', utilise_go: null, total_go: 12 })).toBeNull();
    expect(jaugeMemoire({ utilise_go: 3, total_go: 0 })).toBeNull();
    expect(jaugeTemps(null)).toBeNull();
  });

  it('résume la base et le banc', () => {
    const etat = lireEtat(ETAT_REEL)!;
    expect(resumeBasePlu(etat)).toBe('Biarritz · 189 articles · 493 passages · 178 zones');
    expect(resumeBanc(etat)).toBe('27 / 40');
  });
});
