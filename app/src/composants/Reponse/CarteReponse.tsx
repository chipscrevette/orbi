/**
 * La réponse d'Orbi : le verdict dans un bandeau coloré (la couleur est collée au mot), le texte, le lieu (cliquable :
 * il s'éclaire sur l'aperçu carte), les règles citées mot à mot avec leur page, ce qui reste à vérifier, la démarche.
 */
import {
  BadgeCheck,
  BookOpen,
  CircleCheck,
  CircleHelp,
  CircleX,
  ExternalLink,
  Info,
  Landmark,
  MapPin,
  TriangleAlert,
  type LucideIcon,
} from 'lucide-react';
import { useState } from 'react';
import { DATE_DEMO } from '../../logique/demo.ts';
import { decouperReference, lienPage } from '../../logique/documents.ts';
import { formatDateCourte, formatDuree, formatSurface } from '../../logique/format.ts';
import type { Lieu, Regle, Reponse } from '../../logique/types.ts';
import { lireVerdict, type Ton } from '../../logique/verdict.ts';
import { cx } from '../cx.ts';
import styles from './CarteReponse.module.css';

const ICONES: Record<Ton, LucideIcon> = {
  vert: CircleCheck,
  ambre: TriangleAlert,
  rouge: CircleX,
  gris: CircleHelp,
  bleu: Info,
};

/** Au-delà, une citation est repliée sur quelques lignes. */
const CITATION_LONGUE = 280;

interface Props {
  reponse: Reponse;
  lieu: Lieu | null;
  /** La réponse vient d'un rejeu de démo (et non du serveur). */
  rejeu: boolean;
  nomModele: string;
  lieuActif: boolean;
  /** Animation d'entrée : seulement quand la réponse vient d'arriver. */
  nouvelle: boolean;
  onLieu: () => void;
  onArticle: (chapitre: string, article: string | null) => void;
}

export function CarteReponse({ reponse, lieu, rejeu, nomModele, lieuActif, nouvelle, onLieu, onArticle }: Props) {
  const verdict = lireVerdict(reponse.verdict);
  const Icone = ICONES[verdict.ton];
  const duree = reponse.duree_s !== null ? formatDuree(reponse.duree_s) : null;

  return (
    <article className={cx(styles.carte, nouvelle && styles.nouvelle)} data-ton={verdict.ton} aria-label={`Réponse : ${verdict.libelle}`}>
      <header className={styles.bandeau}>
        <Icone className={styles.iconeVerdict} aria-hidden="true" strokeWidth={2.2} />
        <p className={styles.verdict} data-testid="verdict">
          {verdict.libelle}
        </p>
        {reponse.demo && (
          <p className={styles.badgeDemo}>
            Démo · réponse enregistrée{rejeu ? ` le ${formatDateCourte(DATE_DEMO)}` : ''}
            {duree ? ` (temps réel : ${duree})` : ''}
          </p>
        )}
      </header>

      <div className={styles.corps}>
        {reponse.texte && <p className={styles.texte}>{reponse.texte}</p>}

        {lieu && <PuceLieu lieu={lieu} actif={lieuActif} onClick={onLieu} />}

        {reponse.regles.length > 0 && (
          <section className={styles.section}>
            <h4 className={styles.sectionTitre}>Règles citées</h4>
            <ul className={styles.regles}>
              {reponse.regles.map((regle, i) => (
                <LigneRegle key={`${regle.article}-${i}`} regle={regle} onArticle={onArticle} />
              ))}
            </ul>
          </section>
        )}

        {reponse.a_verifier.length > 0 && (
          <section className={styles.section}>
            <h4 className={styles.sectionTitre}>À vérifier</h4>
            <ul className={styles.aVerifier}>
              {reponse.a_verifier.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </section>
        )}

        {reponse.demarche && (
          <section className={styles.section}>
            <h4 className={styles.sectionTitre}>Démarche</h4>
            <div className={styles.demarche}>
              <Landmark className={styles.iconeDemarche} aria-hidden="true" strokeWidth={1.9} />
              <div>
                <p className={styles.demarcheType}>
                  {reponse.demarche.type.charAt(0).toUpperCase() + reponse.demarche.type.slice(1)}
                  {reponse.demarche.pourquoi && <span className={styles.demarchePourquoi}> · {reponse.demarche.pourquoi}</span>}
                </p>
                {reponse.demarche.delai && (
                  <p className={styles.demarcheLigne}>
                    <strong>Délai</strong> : {reponse.demarche.delai}
                  </p>
                )}
                {reponse.demarche.textes.length > 0 && (
                  <p className={styles.demarcheLigne}>
                    <strong>Textes</strong> :{' '}
                    {reponse.demarche.textes.map((t, i) => (
                      <span key={t.texte}>
                        {i > 0 && ', '}
                        {t.url ? (
                          <a className={styles.lienTexte} href={t.url} target="_blank" rel="noreferrer">
                            {t.texte}
                            <ExternalLink aria-hidden="true" strokeWidth={2} />
                          </a>
                        ) : (
                          t.texte
                        )}
                      </span>
                    ))}
                  </p>
                )}
              </div>
            </div>
          </section>
        )}
      </div>

      <footer className={styles.pied}>
        {duree ? `Répondu en ${duree}` : 'Répondu'} · {nomModele} · 100 % local
      </footer>
    </article>
  );
}

function PuceLieu({ lieu, actif, onClick }: { lieu: Lieu; actif: boolean; onClick: () => void }) {
  const morceaux = [
    lieu.parcelle ? `parcelle ${lieu.parcelle}` : null,
    lieu.zone ? `zone ${lieu.zone}` : null,
    lieu.surface_m2 !== null ? formatSurface(lieu.surface_m2) : null,
  ].filter((m): m is string => m !== null);
  return (
    <button
      type="button"
      className={cx(styles.lieu, actif && styles.lieuActif)}
      onClick={onClick}
      title={`${lieu.adresse ?? 'Lieu'} : voir sur l'aperçu carte`}
      aria-pressed={actif}
    >
      <MapPin aria-hidden="true" strokeWidth={2} />
      <span className={styles.lieuTexte}>{morceaux.join(' · ') || lieu.adresse}</span>
      {lieu.servitudes.map((s) => (
        <span key={s} className={styles.servitude}>
          {s}
        </span>
      ))}
    </button>
  );
}

function LigneRegle({ regle, onArticle }: { regle: Regle; onArticle: (chapitre: string, article: string | null) => void }) {
  const [entiere, setEntiere] = useState(false);
  const reference = decouperReference(regle.article);
  const longue = regle.citation.length > CITATION_LONGUE;
  return (
    <li className={styles.regle}>
      <div className={styles.regleTete}>
        {reference ? (
          <button
            type="button"
            className={styles.article}
            onClick={() => onArticle(reference.chapitre, reference.article)}
            title="Lire l'article dans le règlement"
          >
            <BookOpen aria-hidden="true" strokeWidth={2} />
            {regle.article}
          </button>
        ) : (
          <span className={styles.article}>{regle.article}</span>
        )}
        {regle.verifiee ? (
          <span className={styles.verifiee}>
            <BadgeCheck aria-hidden="true" strokeWidth={2} />
            vérifiée mot à mot
          </span>
        ) : (
          <span className={styles.nonVerifiee}>citation non retrouvée telle quelle</span>
        )}
        {regle.page !== null && (
          <a className={styles.page} href={lienPage(regle.page)} target="_blank" rel="noreferrer" title="Ouvrir le règlement à cette page">
            p. {regle.page}
            <ExternalLink aria-hidden="true" strokeWidth={2} />
          </a>
        )}
      </div>
      {regle.citation && (
        <blockquote className={cx(styles.citation, longue && !entiere && styles.citationRepliee)}>« {regle.citation} »</blockquote>
      )}
      {longue && (
        <button type="button" className={styles.suite} onClick={() => setEntiere((v) => !v)}>
          {entiere ? 'Replier la citation' : 'Lire toute la citation'}
        </button>
      )}
    </li>
  );
}
