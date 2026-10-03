/** Le bandeau qui dit clairement dans quel mode on est quand Orbi ne répond pas en local. */
import { Info, LoaderCircle, PlugZap, RefreshCw } from 'lucide-react';
import type { Mode } from '../../etat/fil.ts';
import { DATE_DEMO } from '../../logique/demo.ts';
import { servicesEteints } from '../../logique/etat.ts';
import { formatDateCourte } from '../../logique/format.ts';
import styles from './Bandeau.module.css';

interface Props {
  mode: Mode;
  moteur: StatutMoteurOrbi | null;
  onReessayer: () => void;
}

export function Bandeau({ mode, moteur, onReessayer }: Props) {
  if (mode.type === 'local') return null;

  if (moteur?.etat === 'demarrage') {
    return (
      <p className={styles.bandeau} data-ton="info" role="status">
        <LoaderCircle className={styles.tourne} aria-hidden="true" strokeWidth={2} />
        Démarrage du moteur local…
      </p>
    );
  }
  if (mode.type === 'recherche') return null;

  if (mode.raison === 'sans-api') {
    return (
      <p className={styles.bandeau} data-ton="demo" role="status">
        <Info aria-hidden="true" strokeWidth={2} />
        <span>
          <strong>Démo</strong> · Orbi rejoue des réponses enregistrées le {formatDateCourte(DATE_DEMO)} : il tourne en local,
          sur un PC avec carte graphique.
        </span>
      </p>
    );
  }

  const eteints = mode.raison === 'services' && mode.etat ? servicesEteints(mode.etat) : [];
  const texte =
    mode.raison === 'services' && eteints.length > 0
      ? `Démo : ${eteints.join(' et ')} ${eteints.length > 1 ? 'sont éteints' : 'est éteint'}, Orbi rejoue des réponses enregistrées.`
      : 'Le moteur local ne répond pas : démo.';
  return (
    <div className={styles.bandeau} data-ton="alerte" role="status">
      <PlugZap aria-hidden="true" strokeWidth={2} />
      <span>
        {texte}
        {moteur?.message && <span className={styles.detail}> {moteur.message}</span>}
      </span>
      <button type="button" className={styles.bouton} onClick={onReessayer}>
        <RefreshCw aria-hidden="true" strokeWidth={2} />
        Réessayer
      </button>
    </div>
  );
}
