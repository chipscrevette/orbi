/**
 * Le fil de conversation et le mode de fonctionnement, en fonctions pures : un réducteur et des sélecteurs.
 * Aucune horloge ni réseau ici : les instants sont passés dans les actions.
 */
import type { Chrono } from '../logique/chrono.ts';
import type { EtatServeur, EvenementEtape, EvenementFlux, Lieu, Reponse } from '../logique/types.ts';
import { lireVerdict, type Humeur } from '../logique/verdict.ts';

export type StatutEchange = 'en_cours' | 'termine' | 'erreur' | 'interrompu';

/** Une question et tout ce qu'Orbi a renvoyé pour elle. */
export interface Echange {
  genre: 'echange';
  id: string;
  question: string;
  /** « serveur » : le moteur local répond ; « rejeu » : une réponse enregistrée est rejouée (démo). */
  source: 'serveur' | 'rejeu';
  idDemo: string | null;
  statut: StatutEchange;
  debutMs: number;
  finMs: number | null;
  chrono: Chrono;
  /** Secondes réelles par seconde affichée (1 en local, ~8 en démo accélérée). */
  facteur: number;
  etapes: EvenementEtape[];
  lieu: Lieu | null;
  reponse: Reponse | null;
  /** La réponse d'une conversation (« coucou ») : un simple texte d'Orbi, sans verdict ni étapes. */
  message: string | null;
  erreur: string | null;
}

/** Un message d'Orbi qui n'est pas une réponse : question libre en démo, fonction à venir. */
export interface MessageInfo {
  genre: 'info';
  id: string;
  question: string | null;
  sorte: 'demo-libre' | 'comparer';
}

export type ElementFil = Echange | MessageInfo;

export interface EtatFil {
  elements: ElementFil[];
  /** L'échange dont le lieu est mis en évidence sur la carte. */
  lieuActifId: string | null;
}

export const FIL_VIDE: EtatFil = { elements: [], lieuActifId: null };

export type ActionFil =
  | { type: 'debut'; echange: Echange }
  | { type: 'evenement'; id: string; evenement: EvenementFlux; maintenantMs: number }
  | { type: 'fin_flux'; id: string; maintenantMs: number }
  | { type: 'echec'; id: string; message: string; maintenantMs: number }
  | { type: 'interrompu'; id: string; maintenantMs: number }
  | { type: 'info'; info: MessageInfo }
  | { type: 'lieu_actif'; id: string | null }
  | { type: 'effacer' };

export const MESSAGE_FLUX_COUPE = 'La réponse s’est interrompue avant la fin. Vous pouvez reposer la question.';

function appliquer(echange: Echange, evenement: EvenementFlux, maintenantMs: number): Echange {
  if (echange.statut !== 'en_cours') return echange;
  switch (evenement.type) {
    case 'etape':
      return { ...echange, etapes: [...echange.etapes, evenement.etape] };
    case 'lieu':
      // Le lieu peut arriver deux fois (après les outils, puis avec la zone retenue) : le second remplace le premier.
      return { ...echange, lieu: evenement.lieu };
    case 'reponse':
      return { ...echange, reponse: evenement.reponse, statut: 'termine', finMs: maintenantMs };
    case 'message':
      return { ...echange, message: evenement.texte, statut: 'termine', finMs: maintenantMs };
    case 'erreur':
      return { ...echange, erreur: evenement.message, statut: 'erreur', finMs: maintenantMs };
    case 'inconnu':
      return echange;
  }
}

function modifier(etat: EtatFil, id: string, f: (e: Echange) => Echange): EtatFil {
  let change = false;
  const elements = etat.elements.map((el) => {
    if (el.genre !== 'echange' || el.id !== id) return el;
    const nouveau = f(el);
    if (nouveau !== el) change = true;
    return nouveau;
  });
  return change ? { ...etat, elements } : etat;
}

export function reduireFil(etat: EtatFil, action: ActionFil): EtatFil {
  switch (action.type) {
    case 'debut':
      return { ...etat, elements: [...etat.elements, action.echange] };
    case 'info':
      return { ...etat, elements: [...etat.elements, action.info] };
    case 'evenement': {
      const suivant = modifier(etat, action.id, (e) => appliquer(e, action.evenement, action.maintenantMs));
      return action.evenement.type === 'lieu' && suivant !== etat ? { ...suivant, lieuActifId: action.id } : suivant;
    }
    case 'fin_flux':
      return modifier(etat, action.id, (e) => {
        if (e.statut !== 'en_cours') return e;
        return e.reponse || e.message !== null
          ? { ...e, statut: 'termine', finMs: action.maintenantMs }
          : { ...e, statut: 'erreur', erreur: MESSAGE_FLUX_COUPE, finMs: action.maintenantMs };
      });
    case 'echec':
      return modifier(etat, action.id, (e) =>
        e.statut === 'en_cours' ? { ...e, statut: 'erreur', erreur: action.message, finMs: action.maintenantMs } : e,
      );
    case 'interrompu':
      return modifier(etat, action.id, (e) =>
        e.statut === 'en_cours' ? { ...e, statut: 'interrompu', finMs: action.maintenantMs } : e,
      );
    case 'lieu_actif':
      return { ...etat, lieuActifId: action.id };
    case 'effacer':
      return FIL_VIDE;
  }
}

/** Un échange déjà fini, tel que le serveur le relit : la question, ce qu'Orbi a répondu, le lieu trouvé. */
export interface EchangePasse {
  question: string;
  reponse: string | null;
  adresse: string | null;
}

/**
 * Les derniers échanges finis de la conversation (le plus ancien d'abord) : le serveur s'en sert pour qu'Orbi ne se
 * répète pas et pour qu'une relance (« et pour une piscine ? ») garde le lieu de la question précédente.
 */
export function historiquePourServeur(etat: EtatFil, n = 4): EchangePasse[] {
  return etat.elements
    .filter((e): e is Echange => e.genre === 'echange' && e.statut === 'termine')
    .slice(-n)
    .map((e) => ({
      question: e.question,
      reponse: e.message ?? e.reponse?.texte ?? null,
      adresse: e.lieu?.adresse ?? (e.lieu?.parcelle ? `parcelle ${e.lieu.parcelle}` : null),
    }));
}

export function echangeEnCours(etat: EtatFil): Echange | null {
  for (const el of etat.elements) if (el.genre === 'echange' && el.statut === 'en_cours') return el;
  return null;
}

export function dernierEchange(etat: EtatFil): Echange | null {
  for (let i = etat.elements.length - 1; i >= 0; i -= 1) {
    const el = etat.elements[i];
    if (el?.genre === 'echange') return el;
  }
  return null;
}

/** Le lieu à montrer sur la carte : celui de l'échange choisi, sinon celui du dernier échange qui en a un. */
export function lieuAffiche(etat: EtatFil): { id: string; lieu: Lieu } | null {
  const echanges = etat.elements.filter((el): el is Echange => el.genre === 'echange' && el.lieu !== null);
  const choisi = echanges.find((e) => e.id === etat.lieuActifId) ?? echanges.at(-1);
  return choisi && choisi.lieu ? { id: choisi.id, lieu: choisi.lieu } : null;
}

/** L'humeur de la mascotte : elle réfléchit pendant une réponse, puis réagit au dernier verdict. */
export function humeurOrbi(etat: EtatFil): Humeur {
  const dernier = dernierEchange(etat);
  if (!dernier) return 'repos';
  if (dernier.statut === 'en_cours') return 'reflechit';
  if (dernier.statut === 'erreur') return 'inquiete';
  return dernier.reponse ? lireVerdict(dernier.reponse.verdict).humeur : 'repos';
}

/* ------------------------------------------------------------------ mode */

export type Connexion =
  | { statut: 'recherche'; etat: null }
  | { statut: 'joignable'; etat: EtatServeur }
  | { statut: 'injoignable'; etat: null };

/** Pourquoi l'interface est en démo : site sans API, moteur injoignable, ou service local éteint. */
export type RaisonDemo = 'sans-api' | 'injoignable' | 'services';

export type Mode =
  | { type: 'recherche' }
  | { type: 'local'; etat: EtatServeur }
  | { type: 'demo'; raison: RaisonDemo; etat: EtatServeur | null };

export function modeDepuis(sansApi: boolean, connexion: Connexion): Mode {
  if (sansApi) return { type: 'demo', raison: 'sans-api', etat: null };
  if (connexion.statut === 'recherche') return { type: 'recherche' };
  if (connexion.statut === 'injoignable') return { type: 'demo', raison: 'injoignable', etat: null };
  return connexion.etat.mode === 'local'
    ? { type: 'local', etat: connexion.etat }
    : { type: 'demo', raison: 'services', etat: connexion.etat };
}
