/**
 * L'accueil du chat : la mascotte, la question d'ouverture et quatre cartes. Un clic sur une carte envoie
 * directement une vraie question d'exemple : on voit Orbi travailler. « Comparer » est une fonction à venir.
 */
import { ArrowRight, FileText, Layers, Map as IconeCarte, Search, type LucideIcon } from 'lucide-react';
import type { EntreeDemo } from '../../logique/types.ts';
import { Mascotte } from '../Mascotte/Mascotte.tsx';
import styles from './Accueil.module.css';

interface Suggestion {
  cle: string;
  titre: string;
  icone: LucideIcon;
  /** La question de démo envoyée (identifiant dans donnees/demo.json) ; sans elle, fonction à venir. */
  idDemo: string | null;
}

export const SUGGESTIONS: readonly Suggestion[] = [
  { cle: 'reglement', titre: 'Règlement PLU', icone: FileText, idDemo: 'D04' },
  { cle: 'parcelle', titre: 'Parcelle cadastrale', icone: IconeCarte, idDemo: 'D14' },
  { cle: 'occupation', titre: 'Analyse d’occupation', icone: Layers, idDemo: 'D06' },
  { cle: 'comparer', titre: 'Comparer', icone: Search, idDemo: null },
];

interface Props {
  demos: readonly EntreeDemo[];
  occupe: boolean;
  onEnvoyer: (question: string) => void;
  onComparer: () => void;
}

export function Accueil({ demos, occupe, onEnvoyer, onComparer }: Props) {
  return (
    <div className={styles.accueil}>
      <Mascotte taille="clamp(132px, 20.3vh, 208px)" className={styles.mascotte} libelle="Orbi" />
      <h1 className={styles.titre}>Comment puis-je vous aider ?</h1>
      <p className={styles.sousTitre}>
        Je réponds à vos questions sur les PLU et les plans cadastraux
        <br />
        en utilisant vos données locales.
      </p>
      <ul className={styles.suggestions}>
        {SUGGESTIONS.map(({ cle, titre, icone: Icone, idDemo }) => {
          const question = idDemo ? demos.find((d) => d.id === idDemo)?.question : undefined;
          const bientot = idDemo === null;
          return (
            <li key={cle}>
              <button
                type="button"
                className={styles.suggestion}
                disabled={occupe || (!bientot && !question)}
                title={question ?? (bientot ? 'Comparer deux parcelles : bientôt' : undefined)}
                onClick={() => (bientot ? onComparer() : question && onEnvoyer(question))}
              >
                {bientot && <span className={styles.bientot}>bientôt</span>}
                <Icone className={styles.icone} aria-hidden="true" strokeWidth={2} />
                <span className={styles.libelle}>
                  {titre}
                  <ArrowRight className={styles.fleche} aria-hidden="true" strokeWidth={1.8} />
                </span>
                {question && <span className="visuellement-cache">. Pose la question : {question}</span>}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
