import { FileText, Gpu, Map as IconeCarte, MessageSquare, Settings, type LucideIcon } from 'lucide-react';
import type { Mode } from '../../etat/fil.ts';
import type { Vue } from '../../etat/useOrbi.ts';
import type { Humeur } from '../../logique/verdict.ts';
import { cx } from '../cx.ts';
import { Pastilles } from '../Fenetre/Pastilles.tsx';
import { Mascotte } from '../Mascotte/Mascotte.tsx';
import styles from './BarreLaterale.module.css';

const LIENS: readonly { vue: Vue; libelle: string; icone: LucideIcon }[] = [
  { vue: 'chat', libelle: 'Chat', icone: MessageSquare },
  { vue: 'cartes', libelle: 'Cartes', icone: IconeCarte },
  { vue: 'documents', libelle: 'Documents', icone: FileText },
  { vue: 'parametres', libelle: 'Paramètres', icone: Settings },
];

interface Props {
  vue: Vue;
  onVue: (vue: Vue) => void;
  humeur: Humeur;
  mode: Mode;
}

export function BarreLaterale({ vue, onVue, humeur, mode }: Props) {
  return (
    <aside className={styles.barre}>
      <Pastilles />
      <div className={styles.marque}>
        <Mascotte taille={92} humeur={humeur} className={styles.mascotte} libelle="Orbi, la mascotte" />
        <p className={styles.nom}>ORBI</p>
        <p className={styles.sousTitre}>Assistant géodata</p>
      </div>
      <nav className={styles.navigation} aria-label="Vues">
        {LIENS.map(({ vue: cible, libelle, icone: Icone }) => (
          <button
            key={cible}
            type="button"
            className={styles.lien}
            aria-current={vue === cible ? 'page' : undefined}
            onClick={() => onVue(cible)}
          >
            <Icone aria-hidden="true" strokeWidth={1.9} />
            <span>{libelle}</span>
          </button>
        ))}
      </nav>
      <CarteMateriel mode={mode} />
    </aside>
  );
}

/** En bas de la colonne : la carte graphique, le modèle et où il tourne (alimentée par /api/etat). */
function CarteMateriel({ mode }: { mode: Mode }) {
  let titre = 'Recherche…';
  let ligne3 = 'Connexion au moteur';
  let ton: 'vert' | 'rouge' | 'gris' = 'gris';
  let modele = 'K2 Horizon 7B';
  if (mode.type === 'local') {
    titre = mode.etat.gpu?.nom ?? 'Sans GPU';
    modele = mode.etat.modele.nom;
    ligne3 = 'En local';
    ton = mode.etat.modele.en_ligne ? 'vert' : 'rouge';
  } else if (mode.type === 'demo') {
    titre = 'Démo';
    modele = mode.etat?.modele.nom ?? modele;
    ligne3 = 'Réponses enregistrées';
  }
  return (
    <div className={styles.materiel}>
      <p className={styles.materielTitre}>
        <Gpu aria-hidden="true" strokeWidth={1.9} />
        <span>{titre}</span>
        <span className={cx(styles.voyant, styles[ton])} aria-label={ton === 'vert' ? 'en ligne' : ton === 'rouge' ? 'hors ligne' : 'inactif'} />
      </p>
      <p className={styles.materielModele}>{modele}</p>
      <p className={styles.materielLieu}>{ligne3}</p>
    </div>
  );
}
