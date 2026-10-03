/** Le fil de conversation : chaque question, puis le travail d'Orbi et sa réponse (ou son erreur). */
import { RotateCcw, SquarePen } from 'lucide-react';
import { Fragment, useEffect, useRef, type ReactNode } from 'react';
import type { ElementFil, Echange, MessageInfo } from '../../etat/fil.ts';
import type { EntreeDemo } from '../../logique/types.ts';
import { lireVerdict, type Humeur } from '../../logique/verdict.ts';
import { Mascotte } from '../Mascotte/Mascotte.tsx';
import { CarteReponse } from '../Reponse/CarteReponse.tsx';
import { Travail } from '../Travail/Travail.tsx';
import styles from './Fil.module.css';

/** Une réponse arrivée depuis moins longtemps que ça a droit à son animation d'entrée. */
const FRAICHEUR_MS = 1500;

interface Props {
  elements: readonly ElementFil[];
  lieuActifId: string | null;
  demos: readonly EntreeDemo[];
  nomModele: string;
  dureeAnalyse: number | null;
  occupe: boolean;
  onEnvoyer: (question: string) => void;
  onLieu: (id: string) => void;
  onArticle: (chapitre: string, article: string | null) => void;
  onNouvelle: () => void;
}

function humeurEchange(e: Echange): Humeur {
  if (e.statut === 'en_cours') return 'reflechit';
  if (e.statut === 'erreur') return 'inquiete';
  return e.reponse ? lireVerdict(e.reponse.verdict).humeur : 'repos';
}

export function Fil(props: Props) {
  const { elements } = props;
  const defilement = useRef<HTMLDivElement>(null);
  const dernier = elements.at(-1);
  const signature = dernier
    ? `${elements.length}-${dernier.genre === 'echange' ? `${dernier.statut}-${dernier.etapes.length}-${dernier.reponse ? 1 : 0}` : 'info'}`
    : '0';

  // Suivre la conversation : on descend à chaque nouveauté, sauf si la personne est remontée lire plus haut.
  const nombre = useRef(0);
  useEffect(() => {
    const zone = defilement.current;
    if (!zone) return;
    const nouvelElement = elements.length !== nombre.current;
    nombre.current = elements.length;
    const presDuBas = zone.scrollHeight - zone.scrollTop - zone.clientHeight < 160;
    if (nouvelElement || presDuBas) zone.scrollTo({ top: zone.scrollHeight, behavior: 'smooth' });
  }, [signature, elements.length]);

  return (
    <div className={styles.fil} ref={defilement}>
      <div className={styles.entete}>
        <button type="button" className={styles.nouvelle} onClick={props.onNouvelle} disabled={props.occupe}>
          <SquarePen aria-hidden="true" strokeWidth={2} />
          Nouvelle conversation
        </button>
      </div>
      <ol className={styles.liste} aria-label="Conversation">
        {elements.map((element) => (
          <Fragment key={element.id}>
            {element.genre === 'echange' ? <BlocEchange echange={element} {...props} /> : <BlocInfo info={element} {...props} />}
          </Fragment>
        ))}
      </ol>
    </div>
  );
}

function Question({ texte }: { texte: string }) {
  return (
    <li className={styles.question}>
      <p>{texte}</p>
    </li>
  );
}

function Orbi({ humeur, children }: { humeur: Humeur; children: ReactNode }) {
  return (
    <li className={styles.orbi}>
      <Mascotte taille={46} humeur={humeur} className={styles.avatar} />
      <div className={styles.contenu}>{children}</div>
    </li>
  );
}

/** Un échange de conversation (« coucou », « merci ») : pas d'analyse, Orbi écrit puis répond en quelques mots. */
function estConversation(e: Echange): boolean {
  return e.message !== null || e.etapes.some((x) => x.id === 'conversation');
}

function ReponseConversation({ echange }: { echange: Echange }) {
  if (echange.message !== null) return <p className={styles.message}>{echange.message}</p>;
  if (echange.statut !== 'en_cours') return null;
  return (
    <p className={styles.ecrit} role="status" aria-label="Orbi écrit">
      <span />
      <span />
      <span />
    </p>
  );
}

function BlocEchange({ echange, ...props }: Props & { echange: Echange }) {
  const nouvelle = echange.finMs !== null && Date.now() - echange.finMs < FRAICHEUR_MS;
  return (
    <>
      <Question texte={echange.question} />
      <Orbi humeur={humeurEchange(echange)}>
        {estConversation(echange) ? (
          <ReponseConversation echange={echange} />
        ) : (
          <Travail echange={echange} dureeAnalyse={props.dureeAnalyse} />
        )}
        {echange.reponse && (
          <CarteReponse
            reponse={echange.reponse}
            lieu={echange.lieu}
            rejeu={echange.source === 'rejeu'}
            nomModele={props.nomModele}
            lieuActif={props.lieuActifId === echange.id}
            nouvelle={nouvelle}
            onLieu={() => props.onLieu(echange.id)}
            onArticle={props.onArticle}
          />
        )}
        {echange.statut === 'erreur' && (
          <div className={styles.erreur} role="alert">
            <p className={styles.erreurTitre}>Orbi n’a pas pu répondre</p>
            <p className={styles.erreurTexte}>
              <TexteAvecCode texte={echange.erreur ?? 'Erreur inconnue.'} />
            </p>
            <button
              type="button"
              className={styles.bouton}
              onClick={() => props.onEnvoyer(echange.question)}
              disabled={props.occupe}
            >
              <RotateCcw aria-hidden="true" strokeWidth={2} />
              Reposer la question
            </button>
          </div>
        )}
        {echange.statut === 'interrompu' && (
          <div className={styles.interrompu}>
            <p>Réponse arrêtée.</p>
            <button
              type="button"
              className={styles.bouton}
              onClick={() => props.onEnvoyer(echange.question)}
              disabled={props.occupe}
            >
              <RotateCcw aria-hidden="true" strokeWidth={2} />
              Reposer la question
            </button>
          </div>
        )}
      </Orbi>
    </>
  );
}

function BlocInfo({ info, ...props }: Props & { info: MessageInfo }) {
  return (
    <>
      {info.question && <Question texte={info.question} />}
      <Orbi humeur="repos">
        {info.sorte === 'comparer' ? (
          <div className={styles.info}>
            <p>Comparer deux parcelles et esquisser une faisabilité arrive dans une prochaine version.</p>
          </div>
        ) : (
          <div className={styles.info}>
            <p>
              En démo, Orbi rejoue des réponses enregistrées : il tourne en local sur un PC avec carte graphique. Essayez
              une de ces questions :
            </p>
            <ul className={styles.questionsDemo}>
              {props.demos.map((d) => (
                <li key={d.id}>
                  <button type="button" onClick={() => props.onEnvoyer(d.question)} disabled={props.occupe}>
                    {d.question}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Orbi>
    </>
  );
}

/** Les passages entre accents graves (`uv run …`) sont montrés comme du code. */
function TexteAvecCode({ texte }: { texte: string }) {
  const morceaux = texte.split('`');
  return (
    <>
      {morceaux.map((m, i) => (i % 2 === 1 ? <code key={i}>{m}</code> : <Fragment key={i}>{m}</Fragment>))}
    </>
  );
}
