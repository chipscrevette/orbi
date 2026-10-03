/**
 * La fenêtre d'Orbi : colonne de navigation, vue centrale (chat, cartes, documents, paramètres) et colonne d'état.
 * Le chat reste monté quand on change de vue : le fil et sa position de lecture sont gardés.
 */
import { PanelRight } from 'lucide-react';
import { useState } from 'react';
import styles from './App.module.css';
import { Bandeau } from './composants/Bandeau/Bandeau.tsx';
import { BarreLaterale } from './composants/BarreLaterale/BarreLaterale.tsx';
import { PanneauDroit } from './composants/Panneau/PanneauDroit.tsx';
import { humeurOrbi, lieuAffiche } from './etat/fil.ts';
import { useOrbi } from './etat/useOrbi.ts';
import { insererAdresse } from './logique/question.ts';
import { VueCartes } from './vues/VueCartes.tsx';
import { VueChat } from './vues/VueChat.tsx';
import { VueDocuments } from './vues/VueDocuments.tsx';
import { VueParametres } from './vues/VueParametres.tsx';

export function App() {
  const orbi = useOrbi();
  const [panneauOuvert, setPanneauOuvert] = useState(false);
  const lieu = lieuAffiche(orbi.fil);
  const etat = orbi.mode.type === 'recherche' ? null : orbi.mode.etat;
  const nomModele = etat?.modele.nom ?? 'K2 Horizon 7B';

  const relancer = () => void (window.orbi ? orbi.relancerMoteur() : orbi.sonder());

  return (
    <div className={styles.bureau}>
      <div className={styles.fenetre}>
        <div className={styles.zoneGlisser} aria-hidden="true" />
        <BarreLaterale vue={orbi.vue} onVue={orbi.setVue} humeur={humeurOrbi(orbi.fil)} mode={orbi.mode} />

        <main className={styles.centre}>
          <Bandeau mode={orbi.mode} moteur={orbi.moteur} onReessayer={relancer} />
          <button
            type="button"
            className={styles.boutonPanneau}
            onClick={() => setPanneauOuvert(true)}
            aria-label="Afficher le modèle et l’aperçu carte"
            title="Modèle et aperçu carte"
          >
            <PanelRight aria-hidden="true" strokeWidth={2} />
          </button>

          <div className={styles.vue} hidden={orbi.vue !== 'chat'}>
            <VueChat orbi={orbi} nomModele={nomModele} />
          </div>
          {orbi.vue === 'cartes' && (
            <VueCartes
              zones={orbi.zones}
              lieu={lieu?.lieu ?? null}
              onLireChapitre={(chapitre) => orbi.ouvrirDocuments({ chapitre, article: null })}
              onUtiliserAdresse={(adresse) => {
                orbi.setBrouillon(insererAdresse(orbi.brouillon, adresse));
                orbi.setVue('chat');
              }}
            />
          )}
          {orbi.vue === 'documents' && <VueDocuments cible={orbi.cibleDocuments} />}
          {orbi.vue === 'parametres' && (
            <VueParametres
              mode={orbi.mode}
              moteur={orbi.moteur}
              nombreEchanges={orbi.fil.elements.length}
              occupe={orbi.enCours !== null}
              onEffacer={orbi.effacer}
              onReessayer={relancer}
            />
          )}
        </main>

        <PanneauDroit
          mode={orbi.mode}
          zones={orbi.zones}
          lieu={lieu?.lieu ?? null}
          dureeMoyenneDemo={orbi.statistiques.dureeMoyenne}
          onOuvrirCarte={() => {
            setPanneauOuvert(false);
            orbi.setVue('cartes');
          }}
          ouvert={panneauOuvert}
          onFermer={() => setPanneauOuvert(false)}
        />
      </div>
    </div>
  );
}
