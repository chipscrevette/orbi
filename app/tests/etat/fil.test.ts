import { describe, expect, it } from 'vitest';
import { CHRONO_REEL } from '../../src/logique/chrono.ts';
import { FIL_VIDE, MESSAGE_FLUX_COUPE, reduireFil, type Echange, type EtatFil } from '../../src/etat/fil.ts';

const ECHANGE: Echange = {
  genre: 'echange',
  id: 'q1',
  question: 'coucou',
  source: 'serveur',
  idDemo: null,
  statut: 'en_cours',
  debutMs: 0,
  finMs: null,
  chrono: CHRONO_REEL,
  facteur: 1,
  etapes: [],
  lieu: null,
  reponse: null,
  message: null,
  erreur: null,
};

function apres(...actions: Parameters<typeof reduireFil>[1][]): Echange {
  const etat = actions.reduce<EtatFil>(reduireFil, reduireFil(FIL_VIDE, { type: 'debut', echange: ECHANGE }));
  return etat.elements[0] as Echange;
}

describe('fil : une conversation', () => {
  it('un message d’Orbi termine l’échange', () => {
    const e = apres(
      { type: 'evenement', id: 'q1', evenement: { type: 'etape', etape: { id: 'conversation', t: 0 } }, maintenantMs: 10 },
      { type: 'evenement', id: 'q1', evenement: { type: 'message', texte: 'Bonjour !', dureeS: 4 }, maintenantMs: 4000 },
    );
    expect(e.statut).toBe('termine');
    expect(e.message).toBe('Bonjour !');
    expect(e.finMs).toBe(4000);
  });

  it('un flux qui se ferme après le message n’est pas une coupure', () => {
    const e = apres(
      { type: 'evenement', id: 'q1', evenement: { type: 'message', texte: 'Bonjour !', dureeS: 4 }, maintenantMs: 4000 },
      { type: 'fin_flux', id: 'q1', maintenantMs: 4001 },
    );
    expect(e.statut).toBe('termine');
    expect(e.erreur).toBeNull();
  });

  it('un flux qui se ferme sans réponse ni message est une coupure', () => {
    const e = apres({ type: 'fin_flux', id: 'q1', maintenantMs: 50 });
    expect(e.statut).toBe('erreur');
    expect(e.erreur).toBe(MESSAGE_FLUX_COUPE);
  });
});
