/**
 * « Orbi travaille » : les six étapes qui se cochent au fil des événements, chacune avec son temps ; l'étape en cours
 * a un minuteur qui tourne (la longue, « K2 remplit la grille », dure souvent près d'une minute).
 * Une fois la réponse arrivée, le bloc se replie en une ligne qu'on peut déplier.
 */
import { Check, ChevronDown, FastForward, Minus } from 'lucide-react';
import { useEffect, useState } from 'react';
import type { Echange } from '../../etat/fil.ts';
import { tempsReel } from '../../logique/chrono.ts';
import { regrouperEtapes, type EtapeAffichee } from '../../logique/etapes.ts';
import { formatDuree, formatDureeEtape, formatEnviron } from '../../logique/format.ts';
import { cx } from '../cx.ts';
import styles from './Travail.module.css';

/** Rafraîchissement du minuteur. */
const PAS_MINUTEUR_MS = 100;

function useMaintenant(actif: boolean): number {
  const [maintenant, setMaintenant] = useState(() => Date.now());
  useEffect(() => {
    if (!actif) return;
    const minuteur = setInterval(() => setMaintenant(Date.now()), PAS_MINUTEUR_MS);
    return () => clearInterval(minuteur);
  }, [actif]);
  return actif ? maintenant : Date.now();
}

interface Props {
  echange: Echange;
  /** Durée habituelle de l'étape 4, tirée des réponses enregistrées. */
  dureeAnalyse: number | null;
}

export function Travail({ echange, dureeAnalyse }: Props) {
  const enCours = echange.statut === 'en_cours';
  const [deplie, setDeplie] = useState(false);
  const maintenant = useMaintenant(enCours);
  const fin = enCours ? maintenant : (echange.finMs ?? maintenant);
  const ecoule = tempsReel(echange.chrono, (fin - echange.debutMs) / 1000);
  const progression = regrouperEtapes(echange.etapes, { termine: !enCours, lieu: echange.lieu });
  const total = !enCours && echange.reponse?.duree_s != null ? echange.reponse.duree_s : Math.max(ecoule, progression.dernier_t);
  const accelere = echange.source === 'rejeu' && echange.facteur > 1;

  if (!enCours && !deplie) {
    const faites = progression.etapes.filter((e) => e.statut === 'fait').length;
    const reussi = echange.statut === 'termine';
    // rien n'a été fait (erreur dès le départ) : le message d'erreur parle seul, sans résumé vide
    if (!reussi && echange.etapes.length === 0) return null;
    return (
      <button type="button" className={styles.resume} onClick={() => setDeplie(true)} aria-expanded="false">
        <span className={reussi ? styles.pastilleFaite : styles.pastilleArret}>
          {reussi ? <Check aria-hidden="true" strokeWidth={3} /> : <Minus aria-hidden="true" strokeWidth={3} />}
        </span>
        <span>
          {echange.statut === 'termine' ? `${faites} étapes · ${formatDuree(total)}` : `Arrêté après ${formatDuree(total)}`}
        </span>
        <span className={styles.voir}>
          Voir les étapes <ChevronDown aria-hidden="true" strokeWidth={2} />
        </span>
      </button>
    );
  }

  return (
    <section className={cx(styles.travail, !enCours && styles.fige)} aria-label="Étapes de travail d'Orbi" aria-live="polite">
      <header className={styles.entete}>
        <h3 className={styles.titre}>{enCours ? 'Orbi travaille' : 'Comment Orbi a travaillé'}</h3>
        {accelere && (
          <span className={styles.accelere} title="Démo : le temps est compressé, les durées affichées sont les vraies">
            <FastForward aria-hidden="true" strokeWidth={2} /> démo accélérée ×{Math.round(echange.facteur)}
          </span>
        )}
        <span className={styles.total}>{formatDureeEtape(total)}</span>
        {!enCours && (
          <button type="button" className={styles.replier} onClick={() => setDeplie(false)} aria-label="Replier les étapes">
            <ChevronDown aria-hidden="true" strokeWidth={2} />
          </button>
        )}
      </header>
      <ol className={styles.etapes}>
        {progression.etapes.map((etape) => (
          <LigneEtape
            key={etape.numero}
            etape={etape}
            temps={etape.statut === 'en_cours' ? etape.duree_s + Math.max(0, ecoule - progression.dernier_t) : etape.duree_s}
            habitude={etape.numero === 4 && etape.statut === 'en_cours' ? dureeAnalyse : null}
          />
        ))}
      </ol>
    </section>
  );
}

function LigneEtape({ etape, temps, habitude }: { etape: EtapeAffichee; temps: number; habitude: number | null }) {
  return (
    <li className={styles.etape} data-statut={etape.statut}>
      <span className={styles.marque} aria-hidden="true">
        {etape.statut === 'fait' && <Check strokeWidth={3} />}
        {etape.statut === 'saute' && <Minus strokeWidth={2.5} />}
      </span>
      <span className={styles.texte}>
        <span className={styles.libelle}>{etape.libelle}</span>
        {etape.detail && <span className={styles.detail}>{etape.detail}</span>}
        {habitude !== null && <span className={styles.detail}>d’habitude {formatEnviron(habitude)}</span>}
        {etape.extras.length > 0 && <span className={styles.extras}>+ {etape.extras.join(', ')}</span>}
      </span>
      <span className={styles.temps}>
        {etape.statut === 'fait' || etape.statut === 'en_cours' ? formatDureeEtape(temps) : ''}
      </span>
      <span className="visuellement-cache">
        {etape.statut === 'fait' ? ' : fait' : etape.statut === 'en_cours' ? ' : en cours' : etape.statut === 'saute' ? ' : non nécessaire' : ' : à venir'}
      </span>
    </li>
  );
}
