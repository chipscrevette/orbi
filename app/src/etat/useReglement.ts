/** Le règlement découpé (`donnees/articles.json`), chargé une seule fois et partagé par les vues. */
import { useEffect, useState } from 'react';
import { chargerJsonStatique } from '../api/client.ts';
import { lireReglement, type ChapitreReglement } from '../logique/documents.ts';

let chargement: Promise<ChapitreReglement[]> | null = null;

export function chargerReglement(): Promise<ChapitreReglement[]> {
  if (!chargement) {
    chargement = chargerJsonStatique('donnees/articles.json').then(lireReglement);
    chargement.catch(() => {
      chargement = null;
    });
  }
  return chargement;
}

export type EtatReglement =
  | { statut: 'chargement'; chapitres: null }
  | { statut: 'pret'; chapitres: ChapitreReglement[] }
  | { statut: 'absent'; chapitres: null };

export function useReglement(): EtatReglement {
  const [etat, setEtat] = useState<EtatReglement>({ statut: 'chargement', chapitres: null });
  useEffect(() => {
    let actif = true;
    chargerReglement()
      .then((chapitres) => actif && setEtat({ statut: 'pret', chapitres }))
      .catch(() => actif && setEtat({ statut: 'absent', chapitres: null }));
    return () => {
      actif = false;
    };
  }, []);
  return etat;
}
