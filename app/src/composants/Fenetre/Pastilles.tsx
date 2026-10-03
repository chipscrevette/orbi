/**
 * Les trois pastilles de la fenêtre. Dans Electron (fenêtre sans cadre), elles ferment, réduisent et agrandissent ;
 * dans un navigateur, elles restent décoratives, comme sur la maquette.
 */
import styles from './Pastilles.module.css';

export function Pastilles() {
  const pont = typeof window !== 'undefined' ? window.orbi : undefined;
  if (!pont) {
    return (
      <div className={styles.pastilles} aria-hidden="true">
        <span className={styles.pastille} data-couleur="rouge" />
        <span className={styles.pastille} data-couleur="jaune" />
        <span className={styles.pastille} data-couleur="verte" />
      </div>
    );
  }
  return (
    <div className={styles.pastilles} role="group" aria-label="Fenêtre">
      <button
        type="button"
        className={styles.pastille}
        data-couleur="rouge"
        onClick={() => pont.fenetre.fermer()}
        aria-label="Fermer"
        title="Fermer"
      >
        <svg viewBox="0 0 10 10" aria-hidden="true">
          <path d="M3 3l4 4M7 3l-4 4" />
        </svg>
      </button>
      <button
        type="button"
        className={styles.pastille}
        data-couleur="jaune"
        onClick={() => pont.fenetre.reduire()}
        aria-label="Réduire"
        title="Réduire"
      >
        <svg viewBox="0 0 10 10" aria-hidden="true">
          <path d="M2.5 5h5" />
        </svg>
      </button>
      <button
        type="button"
        className={styles.pastille}
        data-couleur="verte"
        onClick={() => pont.fenetre.agrandir()}
        aria-label="Agrandir ou rétablir"
        title="Agrandir"
      >
        <svg viewBox="0 0 10 10" aria-hidden="true">
          <path d="M3 3h4v4M7 3L3 7" />
        </svg>
      </button>
    </div>
  );
}
