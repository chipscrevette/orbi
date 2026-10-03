/** Paramètres : l'état réel des services, le mode (local ou démo), le banc d'essai, et la conversation à effacer. */
import { CircleCheck, CircleX, RefreshCw, Trash2 } from 'lucide-react';
import type { Mode } from '../etat/fil.ts';
import { DATE_DEMO } from '../logique/demo.ts';
import { resumeBasePlu, servicesEteints } from '../logique/etat.ts';
import { formatDateCourte, formatGo, pluriel } from '../logique/format.ts';
import styles from './Vues.module.css';

interface Props {
  mode: Mode;
  moteur: StatutMoteurOrbi | null;
  nombreEchanges: number;
  occupe: boolean;
  onEffacer: () => void;
  onReessayer: () => void;
}

const LIBELLES_MOTEUR: Record<StatutMoteurOrbi['etat'], string> = {
  inconnu: 'état inconnu',
  demarrage: 'démarrage en cours',
  pret: 'lancé par l’application',
  externe: 'déjà en marche au lancement',
  indisponible: 'n’a pas pu démarrer',
};

function Ligne({ ok, libelle, detail }: { ok: boolean | null; libelle: string; detail: string }) {
  return (
    <li className={styles.service}>
      {ok === null ? (
        <span className={styles.serviceNeutre} aria-hidden="true" />
      ) : ok ? (
        <CircleCheck className={styles.serviceOk} aria-hidden="true" strokeWidth={2} />
      ) : (
        <CircleX className={styles.serviceKo} aria-hidden="true" strokeWidth={2} />
      )}
      <span className={styles.serviceNom}>{libelle}</span>
      <span className={styles.serviceDetail}>{detail}</span>
    </li>
  );
}

export function VueParametres({ mode, moteur, nombreEchanges, occupe, onEffacer, onReessayer }: Props) {
  const etat = mode.type === 'recherche' ? null : mode.etat;
  const electron = typeof window !== 'undefined' && Boolean(window.orbi);
  let titreMode = 'Recherche du moteur local…';
  let texteMode = 'L’interface interroge le moteur local (http://127.0.0.1:4770).';
  if (mode.type === 'local') {
    titreMode = 'Local';
    texteMode = 'Les questions partent au moteur local : le modèle K2 lit le règlement sur cette machine, rien ne sort.';
  } else if (mode.type === 'demo') {
    titreMode = 'Démo';
    if (mode.raison === 'sans-api') {
      texteMode = `Cette page rejoue les réponses enregistrées le ${formatDateCourte(DATE_DEMO)}. Orbi tourne en local, sur un PC avec carte graphique.`;
    } else if (mode.raison === 'services') {
      texteMode = `Le moteur répond mais ${servicesEteints(mode.etat!).join(' et ') || 'un service local'} est éteint : les réponses enregistrées sont rejouées.`;
    } else {
      texteMode = 'Le moteur local ne répond pas : les réponses enregistrées sont rejouées.';
    }
  }

  return (
    <section className={styles.page} aria-labelledby="titre-parametres">
      <header className={styles.enteteVue}>
        <h1 id="titre-parametres" className={styles.titreVue}>
          Paramètres
        </h1>
      </header>
      <div className={styles.grilleParametres}>
        <article className={styles.bloc}>
          <h2 className={styles.titreBloc}>Mode : {titreMode}</h2>
          <p className={styles.texteBloc}>{texteMode}</p>
          {mode.type !== 'local' && (
            <button type="button" className={styles.boutonSecondaire} onClick={onReessayer}>
              <RefreshCw aria-hidden="true" strokeWidth={2} />
              {electron ? 'Relancer le moteur local' : 'Réessayer la connexion'}
            </button>
          )}
        </article>

        <article className={styles.bloc}>
          <h2 className={styles.titreBloc}>Services</h2>
          {etat ? (
            <ul className={styles.services}>
              <Ligne ok={etat.modele.en_ligne} libelle="Modèle" detail={etat.modele.nom} />
              {Object.entries(etat.services).map(([nom, actif]) => (
                <Ligne key={nom} ok={actif} libelle={nom === 'k2' ? 'Serveur K2' : nom === 'embeddings' ? 'Embeddings' : nom} detail={actif ? 'en marche' : 'éteint'} />
              ))}
              <Ligne ok={etat.base.plu.connectee} libelle="Base PLU" detail={resumeBasePlu(etat) || '—'} />
              <Ligne ok={etat.base.cadastre.connectee} libelle="Cadastre" detail={etat.base.cadastre.source ?? '—'} />
              <Ligne
                ok={null}
                libelle="Carte graphique"
                detail={
                  etat.gpu
                    ? `${etat.gpu.nom}${etat.gpu.utilise_go !== null && etat.gpu.total_go !== null ? ` · ${formatGo(etat.gpu.utilise_go, etat.gpu.total_go)}` : ''}`
                    : 'non signalée'
                }
              />
            </ul>
          ) : (
            <p className={styles.texteBloc}>Aucun moteur local joignable : l’état des services n’est pas connu.</p>
          )}
          {electron && moteur && (
            <p className={styles.noteBloc}>
              Moteur local : {LIBELLES_MOTEUR[moteur.etat]}
              {moteur.message ? ` (${moteur.message})` : ''}.
            </p>
          )}
        </article>

        {etat?.banc && (
          <article className={styles.bloc}>
            <h2 className={styles.titreBloc}>Banc d’essai caché</h2>
            <p className={styles.chiffre}>
              {etat.banc.juste} / {etat.banc.total}
            </p>
            <p className={styles.texteBloc}>
              questions jamais vues réussies{etat.banc.date ? `, passage du ${formatDateCourte(etat.banc.date)}` : ''}.
            </p>
          </article>
        )}

        <article className={styles.bloc}>
          <h2 className={styles.titreBloc}>Conversation</h2>
          <p className={styles.texteBloc}>
            {nombreEchanges === 0 ? 'Aucun échange pour l’instant.' : `${pluriel(nombreEchanges, 'message', 'messages')} dans le fil.`}
          </p>
          <button type="button" className={styles.boutonDanger} onClick={onEffacer} disabled={nombreEchanges === 0 || occupe}>
            <Trash2 aria-hidden="true" strokeWidth={2} />
            Effacer la conversation
          </button>
        </article>

        <article className={styles.bloc}>
          <h2 className={styles.titreBloc}>Sources</h2>
          <ul className={styles.sourcesListe}>
            <li>Règlement du PLU de Biarritz, modification n° 13 approuvée le 23/03/2024</li>
            <li>Zones du PLU : Géoportail de l’Urbanisme</li>
            <li>Fond de carte : Plan IGN v2 © IGN</li>
            <li>Adresses : Base adresse nationale</li>
          </ul>
        </article>
      </div>
    </section>
  );
}
