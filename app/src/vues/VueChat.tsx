/** Le chat : l'accueil tant que rien n'est demandé, puis le fil ; le champ de question reste en bas. */
import { Accueil } from '../composants/Accueil/Accueil.tsx';
import { Fil } from '../composants/Fil/Fil.tsx';
import { Saisie } from '../composants/Saisie/Saisie.tsx';
import type { Orbi } from '../etat/useOrbi.ts';
import styles from './Vues.module.css';

interface Props {
  orbi: Orbi;
  nomModele: string;
}

export function VueChat({ orbi, nomModele }: Props) {
  const occupe = orbi.enCours !== null;
  return (
    <div className={styles.chat}>
      {orbi.fil.elements.length === 0 ? (
        <Accueil demos={orbi.demos} occupe={occupe} onEnvoyer={(q) => void orbi.envoyer(q)} onComparer={orbi.comparer} />
      ) : (
        <Fil
          elements={orbi.fil.elements}
          lieuActifId={orbi.fil.lieuActifId}
          demos={orbi.demos}
          nomModele={nomModele}
          dureeAnalyse={orbi.statistiques.dureeAnalyse}
          occupe={occupe}
          onEnvoyer={(q) => void orbi.envoyer(q)}
          onLieu={orbi.activerLieu}
          onArticle={(chapitre, article) => orbi.ouvrirDocuments({ chapitre, article })}
          onNouvelle={orbi.effacer}
        />
      )}
      <div className={styles.zoneSaisie}>
        <Saisie
          valeur={orbi.brouillon}
          onChange={(v) => {
            orbi.setBrouillon(v);
            if (orbi.alerte) orbi.setAlerte(null);
          }}
          onEnvoyer={(q) => void orbi.envoyer(q, 'saisie')}
          onArreter={orbi.arreter}
          onOuvrirCarte={() => orbi.setVue('cartes')}
          occupe={occupe}
          alerte={orbi.alerte}
        />
      </div>
    </div>
  );
}
