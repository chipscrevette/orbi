/**
 * Le règlement du PLU, chapitre par chapitre (dispositions générales, puis chaque zone), avec une recherche plein texte
 * sans accents ni casse, et pour chaque article le lien vers sa page du PDF.
 */
import { ChevronDown, ExternalLink, Search, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { CibleDocuments } from '../etat/useOrbi.ts';
import { useReglement } from '../etat/useReglement.ts';
import {
  indexerReglement,
  lienPage,
  normaliserPourRecherche,
  rechercherArticles,
  referenceArticle,
  segmenter,
  termesRecherche,
  type ArticleReglement,
  type Segment,
} from '../logique/documents.ts';
import { pluriel } from '../logique/format.ts';
import { caractereZone } from '../logique/zones.ts';
import styles from './Vues.module.css';

function idArticle(reference: string): string {
  return `article-${reference.replace(/[^A-Za-z0-9]+/g, '-')}`;
}

function Segments({ segments }: { segments: readonly Segment[] }) {
  return (
    <>
      {segments.map((s, i) => (s.surligne ? <mark key={i}>{s.texte}</mark> : <span key={i}>{s.texte}</span>))}
    </>
  );
}

export function VueDocuments({ cible }: { cible: CibleDocuments | null }) {
  const reglement = useReglement();
  const chapitres = reglement.chapitres;
  const [chapitre, setChapitre] = useState<string>(cible?.chapitre ?? 'DG');
  const [recherche, setRecherche] = useState('');
  const [ouverts, setOuverts] = useState<ReadonlySet<string>>(new Set());

  const index = useMemo(() => (chapitres ? indexerReglement(chapitres) : []), [chapitres]);
  const termes = useMemo(() => termesRecherche(recherche), [recherche]);
  const resultats = useMemo(() => (termes.length > 0 ? rechercherArticles(index, recherche) : null), [index, recherche, termes]);

  // Arrivée depuis une réponse (« UH 10 ») ou depuis la carte (« zone UD ») : le chapitre, et l'article ouvert.
  useEffect(() => {
    if (!cible) return;
    setRecherche('');
    if (cible.chapitre) setChapitre(cible.chapitre);
    if (cible.chapitre && cible.article) {
      const reference = referenceArticle(cible.chapitre, cible.article);
      setOuverts(new Set([reference]));
      const minuteur = setTimeout(() => document.getElementById(idArticle(reference))?.scrollIntoView({ block: 'start' }), 60);
      return () => clearTimeout(minuteur);
    }
    return undefined;
  }, [cible, chapitres]);

  const basculer = (reference: string) =>
    setOuverts((actuels) => {
      const suivants = new Set(actuels);
      if (suivants.has(reference)) suivants.delete(reference);
      else suivants.add(reference);
      return suivants;
    });

  const courant = chapitres?.find((c) => c.cle === chapitre) ?? chapitres?.[0] ?? null;

  return (
    <section className={styles.page} aria-labelledby="titre-documents">
      <header className={styles.enteteVue}>
        <h1 id="titre-documents" className={styles.titreVue}>
          Règlement du PLU de Biarritz
        </h1>
        <label className={styles.recherche}>
          <Search aria-hidden="true" strokeWidth={2} />
          <span className="visuellement-cache">Rechercher dans le règlement</span>
          <input
            type="search"
            value={recherche}
            onChange={(e) => setRecherche(e.target.value)}
            placeholder="Rechercher : clôture, hauteur, emprise au sol…"
          />
          {recherche && (
            <button type="button" onClick={() => setRecherche('')} aria-label="Effacer la recherche">
              <X aria-hidden="true" strokeWidth={2} />
            </button>
          )}
        </label>
        <a className={styles.lienPdf} href="donnees/reglement-biarritz.pdf" target="_blank" rel="noreferrer">
          Le PDF complet
          <ExternalLink aria-hidden="true" strokeWidth={2} />
        </a>
      </header>

      {reglement.statut === 'absent' && (
        <p className={styles.vide}>
          Le règlement découpé (donnees/articles.json) est introuvable : lancez « npm run preparer » pour le copier.
        </p>
      )}
      {reglement.statut === 'chargement' && <p className={styles.vide}>Chargement du règlement…</p>}

      {chapitres && (
        <div className={styles.documents}>
          <nav className={styles.chapitres} aria-label="Chapitres du règlement">
            {chapitres.map((c) => (
              <button
                key={c.cle}
                type="button"
                className={styles.chapitre}
                aria-current={!resultats && courant?.cle === c.cle ? 'true' : undefined}
                onClick={() => {
                  setRecherche('');
                  setChapitre(c.cle);
                }}
              >
                <strong>{c.libelle}</strong>
                <span>{c.cle === 'DG' ? 'Toute la commune' : (caractereZone(c.cle) ?? '')}</span>
              </button>
            ))}
          </nav>

          <div className={styles.articles}>
            {resultats ? (
              <>
                <p className={styles.compte}>
                  {resultats.length === 0
                    ? `Aucun article ne contient « ${recherche.trim()} ».`
                    : `${pluriel(resultats.length, 'article contient', 'articles contiennent')} « ${recherche.trim()} »`}
                </p>
                <ol className={styles.listeArticles}>
                  {resultats.map((r) => (
                    <Article
                      key={r.article.reference}
                      article={r.article}
                      ouvert={ouverts.has(r.article.reference)}
                      onBasculer={() => basculer(r.article.reference)}
                      extrait={r.extrait}
                      termes={termes}
                    />
                  ))}
                </ol>
              </>
            ) : (
              courant && (
                <>
                  <h2 className={styles.titreChapitre}>{courant.libelle}</h2>
                  <ol className={styles.listeArticles}>
                    {courant.articles.map((a) => (
                      <Article
                        key={a.reference}
                        article={a}
                        ouvert={ouverts.has(a.reference)}
                        onBasculer={() => basculer(a.reference)}
                        extrait={null}
                        termes={[]}
                      />
                    ))}
                  </ol>
                </>
              )
            )}
          </div>
        </div>
      )}
    </section>
  );
}

interface PropsArticle {
  article: ArticleReglement;
  ouvert: boolean;
  onBasculer: () => void;
  extrait: readonly Segment[] | null;
  termes: readonly string[];
}

function Article({ article, ouvert, onBasculer, extrait, termes }: PropsArticle) {
  const texte = useMemo(
    () =>
      ouvert && termes.length > 0
        ? segmenter(article.texte, normaliserPourRecherche(article.texte), termes)
        : [{ texte: article.texte, surligne: false }],
    [article.texte, ouvert, termes],
  );
  const pages = article.pages;
  return (
    <li className={styles.article} id={idArticle(article.reference)}>
      <div className={styles.articleTete}>
        <span className={styles.reference}>{article.reference}</span>
        <h3 className={styles.titreArticle}>{article.titre}</h3>
        {pages && (
          <a className={styles.lienNumeroPage} href={lienPage(pages[0])} target="_blank" rel="noreferrer" title="Ouvrir le PDF à cette page">
            {pages[0] === pages[1] ? `p. ${pages[0]}` : `p. ${pages[0]}-${pages[1]}`}
            <ExternalLink aria-hidden="true" strokeWidth={2} />
          </a>
        )}
      </div>
      {!ouvert && extrait ? (
        <p className={styles.extrait}>
          <Segments segments={extrait} />
        </p>
      ) : (
        <p className={ouvert ? styles.texteArticle : `${styles.texteArticle} ${styles.texteReplie}`}>
          <Segments segments={texte} />
        </p>
      )}
      <button type="button" className={styles.basculer} onClick={onBasculer} aria-expanded={ouvert}>
        {ouvert ? 'Replier' : 'Lire l’article'}
        <ChevronDown aria-hidden="true" strokeWidth={2} data-ouvert={ouvert} />
      </button>
    </li>
  );
}
