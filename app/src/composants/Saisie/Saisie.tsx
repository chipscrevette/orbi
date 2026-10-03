/**
 * Le champ de question : Entrée envoie, Maj+Entrée va à la ligne. Le trombone est une fonction à venir (désactivé,
 * avec son infobulle) ; l'icône carte ouvre la vue Cartes, où un clic choisit une adresse.
 */
import { Map as IconeCarte, Paperclip, Send, Square } from 'lucide-react';
import { useEffect, useRef, type FormEvent, type KeyboardEvent } from 'react';
import { formatNombre } from '../../logique/format.ts';
import { LONGUEUR_MAX_QUESTION, LONGUEUR_MIN_QUESTION } from '../../logique/question.ts';
import styles from './Saisie.module.css';

interface Props {
  valeur: string;
  onChange: (valeur: string) => void;
  onEnvoyer: (question: string) => void;
  onArreter: () => void;
  onOuvrirCarte: () => void;
  occupe: boolean;
  alerte: string | null;
}

export function Saisie({ valeur, onChange, onEnvoyer, onArreter, onOuvrirCarte, occupe, alerte }: Props) {
  const zone = useRef<HTMLTextAreaElement>(null);
  const longueur = valeur.trim().length;
  const envoyable = !occupe && longueur >= LONGUEUR_MIN_QUESTION && longueur <= LONGUEUR_MAX_QUESTION;

  // Une adresse insérée depuis la carte : le curseur va en fin de texte.
  useEffect(() => {
    const champ = zone.current;
    if (champ && document.activeElement !== champ && valeur !== '') {
      champ.focus();
      champ.setSelectionRange(valeur.length, valeur.length);
    }
    // seulement quand le texte change de l'extérieur
  }, [valeur]);

  const soumettre = (evenement?: FormEvent) => {
    evenement?.preventDefault();
    if (occupe) return;
    onEnvoyer(valeur);
  };

  const touche = (evenement: KeyboardEvent<HTMLTextAreaElement>) => {
    if (evenement.key === 'Enter' && !evenement.shiftKey && !evenement.nativeEvent.isComposing) {
      evenement.preventDefault();
      soumettre();
    }
  };

  return (
    <form className={styles.saisie} onSubmit={soumettre}>
      <label className="visuellement-cache" htmlFor="question">
        Votre question à Orbi
      </label>
      <textarea
        id="question"
        ref={zone}
        className={styles.champ}
        rows={1}
        value={valeur}
        maxLength={LONGUEUR_MAX_QUESTION}
        placeholder="Posez votre question…"
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={touche}
        aria-describedby={alerte ? 'alerte-question' : undefined}
      />
      <div className={styles.outils}>
        <span className={styles.bulle} data-bulle="Joindre un plan — bientôt">
          <button
            type="button"
            className={styles.outil}
            aria-disabled="true"
            aria-label="Joindre un plan (bientôt)"
            onClick={(e) => e.preventDefault()}
          >
            <Paperclip aria-hidden="true" strokeWidth={1.8} />
          </button>
        </span>
        <span className={styles.bulle} data-bulle="Choisir un lieu sur la carte">
          <button type="button" className={styles.outil} onClick={onOuvrirCarte} aria-label="Choisir un lieu sur la carte">
            <IconeCarte aria-hidden="true" strokeWidth={1.8} />
          </button>
        </span>
        <p className={styles.message} id="alerte-question" role={alerte ? 'alert' : undefined}>
          {alerte ??
            (longueur > LONGUEUR_MAX_QUESTION - 200
              ? `${formatNombre(longueur)} / ${formatNombre(LONGUEUR_MAX_QUESTION)} caractères`
              : '')}
        </p>
        {occupe ? (
          <button type="button" className={styles.envoyer} onClick={onArreter} aria-label="Arrêter la réponse" title="Arrêter la réponse">
            <Square aria-hidden="true" fill="currentColor" strokeWidth={0} />
          </button>
        ) : (
          <button type="submit" className={styles.envoyer} disabled={!envoyable} aria-label="Envoyer la question" title="Envoyer">
            <Send aria-hidden="true" strokeWidth={2} />
          </button>
        )}
      </div>
    </form>
  );
}
