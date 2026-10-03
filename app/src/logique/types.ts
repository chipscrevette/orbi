/**
 * Le contrat avec le serveur Orbi (port 4770) et avec le fichier de démo `donnees/demo.json`.
 * Les noms des champs sont ceux du serveur : ils ne sont pas traduits.
 */

/** [longitude, latitude] en WGS 84. */
export type Point = readonly [number, number];

export interface Lieu {
  adresse: string | null;
  commune: string | null;
  point: Point | null;
  parcelle: string | null;
  surface_m2: number | null;
  zone: string | null;
  servitudes: string[];
  site_patrimonial: boolean;
}

export interface Regle {
  article: string;
  citation: string;
  page: number | null;
  verifiee: boolean;
}

export interface TexteDeLoi {
  texte: string;
  url: string;
}

export interface Demarche {
  type: string;
  pourquoi: string | null;
  delai: string | null;
  textes: TexteDeLoi[];
}

export interface Reponse {
  verdict: string;
  texte: string;
  regles: Regle[];
  a_verifier: string[];
  demarche: Demarche | null;
  zone: string | null;
  duree_s: number | null;
  demo: boolean;
}

/** Une étape franchie par l'agent : `t` = secondes écoulées depuis le début de la question. */
export interface EvenementEtape {
  id: string;
  t: number;
}

/** Un événement du flux `POST /api/question`, déjà lu et vérifié. */
export type EvenementFlux =
  | { type: 'etape'; etape: EvenementEtape }
  | { type: 'lieu'; lieu: Lieu }
  | { type: 'reponse'; reponse: Reponse }
  | { type: 'erreur'; message: string }
  /** Une réponse de conversation (« coucou ») : un texte d'Orbi, sans verdict. */
  | { type: 'message'; texte: string; dureeS: number | null }
  | { type: 'inconnu'; nom: string };

/** Une réponse enregistrée, rejouée en mode démo. */
export interface EntreeDemo {
  id: string;
  question: string;
  lieu: Lieu | null;
  etapes: EvenementEtape[];
  reponse: Reponse;
  duree_s: number | null;
}

export interface EtatGpu {
  nom: string;
  utilise_go: number | null;
  total_go: number | null;
}

export interface EtatMemoire {
  utilise_go: number | null;
  total_go: number | null;
}

/**
 * `GET /api/etat`. `mode` vaut « demo » dès qu'un service local (K2 ou le serveur d'embeddings) est éteint :
 * `services` dit lequel.
 */
export interface EtatServeur {
  mode: 'local' | 'demo';
  modele: { nom: string; en_ligne: boolean };
  services: Record<string, boolean>;
  gpu: EtatGpu | null;
  memoire: EtatMemoire | null;
  temps_reponse_s: number | null;
  base: {
    plu: {
      connectee: boolean;
      commune: string | null;
      articles: number | null;
      passages: number | null;
      zones: number | null;
    };
    cadastre: { connectee: boolean; source: string | null };
  };
  banc: { juste: number; total: number; date: string | null } | null;
}
