/**
 * Le règlement du PLU tel que découpé dans `donnees/articles.json` ({ chapitre: { article: { titre, pages, texte } } }),
 * sa recherche plein texte (sans accents ni casse) et les références d'articles (« UH 10 », « DG A-I »).
 */
import { estObjet, nombre, texte } from './contrat.ts';
import { libelleChapitre } from './zones.ts';

export interface ArticleReglement {
  chapitre: string;
  cle: string;
  reference: string;
  titre: string;
  pages: readonly [number, number] | null;
  texte: string;
}

export interface ChapitreReglement {
  cle: string;
  libelle: string;
  articles: ArticleReglement[];
}

export interface Segment {
  texte: string;
  surligne: boolean;
}

/** « UH » + « 10 » → « UH 10 » ; le préambule des dispositions générales (« 0 ») → « DG ». */
export function referenceArticle(chapitre: string, cle: string): string {
  return chapitre === 'DG' && cle === '0' ? 'DG' : `${chapitre} ${cle}`;
}

/** « UH 10 » → { chapitre: « UH », article: « 10 » } ; « DG A-I » → { « DG », « A-I » }. */
export function decouperReference(reference: string): { chapitre: string; article: string | null } | null {
  const m = /^\s*(\S+)(?:\s+(.+?))?\s*$/.exec(reference);
  if (!m || !m[1]) return null;
  return { chapitre: m[1], article: m[2] ?? null };
}

/**
 * Le titre d'un article : les titres extraits du PDF collent le titre en capitales au début du texte
 * (« LES OCCUPATIONS … PARTICULIERES  Sauf en U »). On garde les mots en capitales du début.
 */
export function titreArticle(brut: string): string {
  const propre = brut.replace(/\s+/g, ' ').trim();
  const mots = propre.split(' ');
  const gardes: string[] = [];
  let jusquAuBout = true;
  for (const mot of mots) {
    const lettres = mot.replace(/[^A-Za-zÀ-ÖØ-öø-ÿ]/g, '');
    if (lettres === '') {
      if (gardes.length > 0) gardes.push(mot);
      continue;
    }
    if (lettres !== lettres.toUpperCase()) {
      jusquAuBout = false;
      break;
    }
    gardes.push(mot);
  }
  while (gardes.length > 0 && !/[A-Za-zÀ-ÿ]/.test(gardes[gardes.length - 1] ?? '')) gardes.pop();
  const titre = gardes.join(' ');
  if (titre.length < 4) return propre.slice(0, 80);
  // Les titres extraits sont coupés vers 90 caractères : un titre en capitales qui va jusqu'au bout est tronqué.
  return jusquAuBout && propre.length >= LONGUEUR_TITRE_SOURCE ? `${titre}…` : titre;
}

/** Longueur à laquelle l'extraction du PDF a coupé les titres. */
const LONGUEUR_TITRE_SOURCE = 85;

function lirePages(v: unknown): readonly [number, number] | null {
  if (!Array.isArray(v) || v.length === 0) return null;
  const debut = nombre(v[0]);
  const fin = nombre(v[1]) ?? debut;
  if (debut === null || fin === null || debut <= 0) return null;
  return [Math.round(debut), Math.round(Math.max(debut, fin))];
}

export function lireReglement(json: unknown): ChapitreReglement[] {
  if (!estObjet(json)) return [];
  const chapitres: ChapitreReglement[] = [];
  for (const [cle, brut] of Object.entries(json)) {
    if (!estObjet(brut)) continue;
    const articles: ArticleReglement[] = [];
    for (const [cleArticle, a] of Object.entries(brut)) {
      if (!estObjet(a)) continue;
      const corps = texte(a.texte);
      if (corps === null) continue;
      articles.push({
        chapitre: cle,
        cle: cleArticle,
        reference: referenceArticle(cle, cleArticle),
        titre: titreArticle(texte(a.titre) ?? ''),
        pages: lirePages(a.pages),
        texte: corps,
      });
    }
    chapitres.push({ cle, libelle: libelleChapitre(cle), articles });
  }
  return chapitres;
}

/**
 * Minuscules sans accents, caractère par caractère : le texte rendu a la même longueur que l'original,
 * ce qui permet de surligner l'original aux positions trouvées dans la version normalisée.
 */
export function normaliserPourRecherche(s: string): string {
  let sortie = '';
  for (let i = 0; i < s.length; i += 1) {
    const c = s.charAt(i);
    if (c === '’' || c === 'ʼ' || c === '`') {
      sortie += "'";
      continue;
    }
    const base = c.normalize('NFD').charAt(0) || c;
    sortie += base.toLowerCase().charAt(0) || base;
  }
  return sortie;
}

export function termesRecherche(requete: string): string[] {
  const termes = normaliserPourRecherche(requete)
    .split(/\s+/)
    .map((t) => t.replace(/^[^a-z0-9]+|[^a-z0-9]+$/g, ''))
    .filter((t) => t.length >= 2);
  return [...new Set(termes)];
}

function positions(normalise: string, terme: string): number[] {
  const trouvees: number[] = [];
  let i = normalise.indexOf(terme);
  while (i !== -1) {
    trouvees.push(i);
    i = normalise.indexOf(terme, i + terme.length);
  }
  return trouvees;
}

/** Découpe `texte[debut, fin)` en segments, les occurrences des termes étant surlignées. */
export function segmenter(original: string, normalise: string, termes: readonly string[], debut = 0, fin = original.length): Segment[] {
  const plages: [number, number][] = [];
  for (const terme of termes) {
    for (const p of positions(normalise, terme)) {
      if (p + terme.length > debut && p < fin) plages.push([Math.max(p, debut), Math.min(p + terme.length, fin)]);
    }
  }
  plages.sort((a, b) => a[0] - b[0]);
  const fusion: [number, number][] = [];
  for (const plage of plages) {
    const derniere = fusion.at(-1);
    if (derniere && plage[0] <= derniere[1]) derniere[1] = Math.max(derniere[1], plage[1]);
    else fusion.push([plage[0], plage[1]]);
  }
  const segments: Segment[] = [];
  let curseur = debut;
  for (const [a, b] of fusion) {
    if (a > curseur) segments.push({ texte: original.slice(curseur, a), surligne: false });
    segments.push({ texte: original.slice(a, b), surligne: true });
    curseur = b;
  }
  if (curseur < fin) segments.push({ texte: original.slice(curseur, fin), surligne: false });
  return segments;
}

export interface ArticleIndexe {
  article: ArticleReglement;
  titreNormalise: string;
  texteNormalise: string;
}

export function indexerReglement(chapitres: readonly ChapitreReglement[]): ArticleIndexe[] {
  return chapitres.flatMap((c) =>
    c.articles.map((article) => ({
      article,
      titreNormalise: normaliserPourRecherche(article.titre),
      texteNormalise: normaliserPourRecherche(article.texte),
    })),
  );
}

export interface ResultatRecherche {
  article: ArticleReglement;
  occurrences: number;
  extrait: Segment[];
}

/**
 * Les articles qui contiennent tous les termes (dans le titre ou le texte), les plus riches en occurrences d'abord,
 * chacun avec un extrait centré sur la première occurrence.
 */
export function rechercherArticles(
  index: readonly ArticleIndexe[],
  requete: string,
  options: { chapitre?: string | null; limite?: number; rayon?: number } = {},
): ResultatRecherche[] {
  const termes = termesRecherche(requete);
  if (termes.length === 0) return [];
  const rayon = options.rayon ?? 110;
  const resultats: ResultatRecherche[] = [];
  index.forEach(({ article, titreNormalise, texteNormalise }) => {
    if (options.chapitre && article.chapitre !== options.chapitre) return;
    let occurrences = 0;
    for (const terme of termes) {
      const n = positions(texteNormalise, terme).length + positions(titreNormalise, terme).length;
      if (n === 0) return;
      occurrences += n;
    }
    const premieres = termes.map((t) => texteNormalise.indexOf(t)).filter((p) => p >= 0);
    const centre = premieres.length > 0 ? Math.min(...premieres) : 0;
    let debut = Math.max(0, centre - rayon);
    let fin = Math.min(article.texte.length, centre + rayon * 2);
    if (debut > 0) {
      const espace = article.texte.indexOf(' ', debut);
      if (espace !== -1 && espace < centre) debut = espace + 1;
    }
    if (fin < article.texte.length) {
      const espace = article.texte.lastIndexOf(' ', fin);
      if (espace > centre) fin = espace;
    }
    const extrait = segmenter(article.texte, texteNormalise, termes, debut, fin);
    if (debut > 0) extrait.unshift({ texte: '… ', surligne: false });
    if (fin < article.texte.length) extrait.push({ texte: ' …', surligne: false });
    resultats.push({ article, occurrences, extrait });
  });
  resultats.sort((a, b) => b.occurrences - a.occurrences);
  return resultats.slice(0, options.limite ?? 80);
}

/** Lien vers une page du règlement en PDF (chemin relatif au site). */
export function lienPage(page: number): string {
  return `donnees/reglement-biarritz.pdf#page=${page}`;
}
