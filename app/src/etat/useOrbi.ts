/**
 * Le cœur de l'interface : connexion au moteur local (sondée toutes les 10 s), bascule en démo, envoi des questions
 * (flux du serveur ou rejeu d'une réponse enregistrée), vue affichée et brouillon de la question.
 */
import { useCallback, useEffect, useMemo, useReducer, useRef, useState } from 'react';
import { chargerEtat, chargerJsonStatique, poserQuestion } from '../api/client.ts';
import { lancerRejeu } from '../api/rejeu.ts';
import { CHRONO_REEL } from '../logique/chrono.ts';
import { lireEntreesDemo } from '../logique/contrat.ts';
import { dureeMoyenneDemo, dureeTypiqueEtape, planifierRejeu, trouverEntreeDemo } from '../logique/demo.ts';
import type { CollectionZones } from '../logique/geo.ts';
import { validerQuestion } from '../logique/question.ts';
import type { EntreeDemo } from '../logique/types.ts';
import { FIL_VIDE, echangeEnCours, modeDepuis, reduireFil, type Connexion, type Echange } from './fil.ts';

export type Vue = 'chat' | 'cartes' | 'documents' | 'parametres';

export interface CibleDocuments {
  chapitre: string | null;
  article: string | null;
}

export const INTERVALLE_ETAT_MS = 10_000;

let compteur = 0;
function nouvelId(prefixe: string): string {
  compteur += 1;
  return `${prefixe}-${Date.now().toString(36)}-${compteur}`;
}

function messageErreur(erreur: unknown): string {
  if (erreur instanceof TypeError) return 'Le moteur local ne répond pas (connexion impossible).';
  if (erreur instanceof Error && erreur.message) return erreur.message;
  return 'Erreur inattendue pendant la réponse.';
}

function nouvelEchange(id: string, question: string, champs: Partial<Echange>): Echange {
  return {
    genre: 'echange',
    id,
    question,
    source: 'serveur',
    idDemo: null,
    statut: 'en_cours',
    debutMs: Date.now(),
    finMs: null,
    chrono: CHRONO_REEL,
    facteur: 1,
    etapes: [],
    lieu: null,
    reponse: null,
    message: null,
    erreur: null,
    ...champs,
  };
}

export function useOrbi() {
  const [vue, setVue] = useState<Vue>('chat');
  const [fil, dispatch] = useReducer(reduireFil, FIL_VIDE);
  const [connexion, setConnexion] = useState<Connexion>({ statut: 'recherche', etat: null });
  const [demos, setDemos] = useState<EntreeDemo[]>([]);
  const [zones, setZones] = useState<CollectionZones | null>(null);
  const [moteur, setMoteur] = useState<StatutMoteurOrbi | null>(null);
  const [brouillon, setBrouillon] = useState('');
  const [alerte, setAlerte] = useState<string | null>(null);
  const [cibleDocuments, setCibleDocuments] = useState<CibleDocuments | null>(null);

  const arretRef = useRef<(() => void) | null>(null);
  const occupeRef = useRef(false);
  const sondageRef = useRef<Promise<Connexion> | null>(null);
  const connexionRef = useRef(connexion);
  const demosRef = useRef(demos);
  const enCours = echangeEnCours(fil);

  useEffect(() => {
    connexionRef.current = connexion;
  }, [connexion]);
  useEffect(() => {
    demosRef.current = demos;
  }, [demos]);
  useEffect(() => {
    occupeRef.current = enCours !== null;
  }, [enCours]);

  // Données statiques livrées avec l'interface.
  useEffect(() => {
    let actif = true;
    chargerJsonStatique('donnees/demo.json')
      .then((json) => actif && setDemos(lireEntreesDemo(json)))
      .catch(() => actif && setDemos([]));
    chargerJsonStatique('donnees/zones.geojson')
      .then((json) => actif && setZones(json as CollectionZones))
      .catch(() => actif && setZones(null));
    return () => {
      actif = false;
    };
  }, []);

  const sonder = useCallback((): Promise<Connexion> => {
    if (__SANS_API__) return Promise.resolve({ statut: 'injoignable', etat: null });
    const promesse = chargerEtat().then((etat): Connexion => {
      const suivante: Connexion = etat ? { statut: 'joignable', etat } : { statut: 'injoignable', etat: null };
      setConnexion(suivante);
      return suivante;
    });
    sondageRef.current = promesse;
    return promesse;
  }, []);

  useEffect(() => {
    if (__SANS_API__) return;
    void sonder();
    const minuteur = setInterval(() => void sonder(), INTERVALLE_ETAT_MS);
    return () => clearInterval(minuteur);
  }, [sonder]);

  // Dans Electron : l'état du moteur que le processus principal démarre.
  useEffect(() => {
    const pont = window.orbi;
    if (!pont) return;
    let actif = true;
    pont.moteur
      .statut()
      .then((s) => actif && setMoteur(s))
      .catch(() => undefined);
    const arreterEcoute = pont.moteur.surStatut((s) => {
      setMoteur(s);
      if (s.etat === 'pret' || s.etat === 'externe') void sonder();
    });
    return () => {
      actif = false;
      arreterEcoute();
    };
  }, [sonder]);

  // Arrêter un rejeu ou un flux en cours si l'interface disparaît.
  useEffect(() => () => arretRef.current?.(), []);

  const lancerServeur = useCallback(async (question: string) => {
    const id = nouvelId('q');
    const controleur = new AbortController();
    occupeRef.current = true;
    arretRef.current = () => controleur.abort();
    dispatch({ type: 'debut', echange: nouvelEchange(id, question, {}) });
    try {
      await poserQuestion(
        question,
        (evenement) => dispatch({ type: 'evenement', id, evenement, maintenantMs: Date.now() }),
        controleur.signal,
      );
      dispatch({ type: 'fin_flux', id, maintenantMs: Date.now() });
    } catch (erreur) {
      if (controleur.signal.aborted) dispatch({ type: 'interrompu', id, maintenantMs: Date.now() });
      else dispatch({ type: 'echec', id, message: messageErreur(erreur), maintenantMs: Date.now() });
    } finally {
      arretRef.current = null;
    }
  }, []);

  const lancerDemo = useCallback((entree: EntreeDemo) => {
    const id = nouvelId('d');
    const plan = planifierRejeu(entree);
    occupeRef.current = true;
    dispatch({
      type: 'debut',
      echange: nouvelEchange(id, entree.question, {
        source: 'rejeu',
        idDemo: entree.id,
        chrono: { type: 'rejeu', reperes: plan.reperes },
        facteur: plan.facteur,
      }),
    });
    const arreterRejeu = lancerRejeu(
      plan,
      (evenement) => dispatch({ type: 'evenement', id, evenement, maintenantMs: Date.now() }),
      () => {
        dispatch({ type: 'fin_flux', id, maintenantMs: Date.now() });
        arretRef.current = null;
      },
    );
    arretRef.current = () => {
      arreterRejeu();
      dispatch({ type: 'interrompu', id, maintenantMs: Date.now() });
    };
  }, []);

  const envoyer = useCallback(
    async (brut: string, origine: 'saisie' | 'suggestion' = 'suggestion') => {
      const validation = validerQuestion(brut);
      if (!validation.valide) {
        setAlerte(validation.raison);
        return;
      }
      if (occupeRef.current) return;
      setAlerte(null);
      if (origine === 'saisie') setBrouillon('');
      setVue('chat');
      let connue = connexionRef.current;
      if (!__SANS_API__ && connue.statut === 'recherche') connue = await (sondageRef.current ?? sonder());
      const mode = modeDepuis(__SANS_API__, connue);
      if (mode.type === 'local') {
        void lancerServeur(validation.question);
        return;
      }
      const entree = trouverEntreeDemo(validation.question, demosRef.current);
      if (entree) lancerDemo(entree);
      else {
        dispatch({
          type: 'info',
          info: { genre: 'info', id: nouvelId('i'), question: validation.question, sorte: 'demo-libre' },
        });
      }
    },
    [lancerDemo, lancerServeur, sonder],
  );

  const comparer = useCallback(() => {
    setVue('chat');
    dispatch({
      type: 'info',
      info: { genre: 'info', id: nouvelId('i'), question: 'Comparer deux parcelles', sorte: 'comparer' },
    });
  }, []);

  const arreter = useCallback(() => {
    arretRef.current?.();
    arretRef.current = null;
  }, []);

  const effacer = useCallback(() => {
    arretRef.current?.();
    arretRef.current = null;
    dispatch({ type: 'effacer' });
  }, []);

  const ouvrirDocuments = useCallback((cible: CibleDocuments) => {
    setCibleDocuments(cible);
    setVue('documents');
  }, []);

  const activerLieu = useCallback((id: string) => dispatch({ type: 'lieu_actif', id }), []);

  const relancerMoteur = useCallback(async () => {
    if (window.orbi) setMoteur(await window.orbi.moteur.relancer());
    await sonder();
  }, [sonder]);

  const statistiques = useMemo(
    () => ({ dureeMoyenne: dureeMoyenneDemo(demos), dureeAnalyse: dureeTypiqueEtape(demos, 4) }),
    [demos],
  );

  return {
    vue,
    setVue,
    fil,
    mode: modeDepuis(__SANS_API__, connexion),
    moteur,
    demos,
    zones,
    brouillon,
    setBrouillon,
    alerte,
    setAlerte,
    cibleDocuments,
    enCours,
    statistiques,
    envoyer,
    comparer,
    arreter,
    effacer,
    ouvrirDocuments,
    activerLieu,
    sonder,
    relancerMoteur,
  };
}

export type Orbi = ReturnType<typeof useOrbi>;
