/// <reference types="vite/client" />

/** Vrai dans le site statique (GitHub Pages) : il n'y a pas d'API, on ne la cherche même pas. */
declare const __SANS_API__: boolean;

/** État du moteur local tel que le processus principal d'Electron le connaît. */
interface StatutMoteurOrbi {
  etat: 'inconnu' | 'demarrage' | 'pret' | 'externe' | 'indisponible';
  message: string | null;
}

/** L'API minimale exposée par le préchargement d'Electron (absente dans un navigateur). */
interface PontOrbi {
  fenetre: {
    fermer(): void;
    reduire(): void;
    agrandir(): void;
  };
  moteur: {
    statut(): Promise<StatutMoteurOrbi>;
    relancer(): Promise<StatutMoteurOrbi>;
    surStatut(rappel: (statut: StatutMoteurOrbi) => void): () => void;
  };
}

interface Window {
  orbi?: PontOrbi;
}
