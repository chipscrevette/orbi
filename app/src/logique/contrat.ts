/**
 * Lecture prudente des données reçues (serveur, demo.json) : tout ce qui manque ou n'a pas le bon type
 * devient `null` ou une liste vide, jamais une exception. L'interface ne plante pas sur un champ imprévu.
 */
import type {
  Demarche,
  EntreeDemo,
  EtatServeur,
  EvenementEtape,
  Lieu,
  Point,
  Regle,
  Reponse,
  TexteDeLoi,
} from './types.ts';

type Objet = Record<string, unknown>;

export function estObjet(v: unknown): v is Objet {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

/** Un texte non vide, sinon `null`. */
export function texte(v: unknown): string | null {
  return typeof v === 'string' && v.trim() !== '' ? v : null;
}

/** Un nombre fini, sinon `null`. */
export function nombre(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null;
}

function listeDeTextes(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === 'string' && x.trim() !== '') : [];
}

function objet(v: unknown): Objet {
  return estObjet(v) ? v : {};
}

function lirePoint(v: unknown): Point | null {
  if (!Array.isArray(v) || v.length < 2) return null;
  const lon = nombre(v[0]);
  const lat = nombre(v[1]);
  if (lon === null || lat === null) return null;
  if (Math.abs(lon) > 180 || Math.abs(lat) > 90) return null;
  return [lon, lat];
}

export function lireLieu(v: unknown): Lieu | null {
  if (!estObjet(v)) return null;
  return {
    adresse: texte(v.adresse),
    commune: texte(v.commune),
    point: lirePoint(v.point),
    parcelle: texte(v.parcelle),
    surface_m2: nombre(v.surface_m2),
    zone: texte(v.zone),
    servitudes: listeDeTextes(v.servitudes),
    site_patrimonial: v.site_patrimonial === true,
  };
}

function lireRegle(v: unknown): Regle | null {
  if (!estObjet(v)) return null;
  const article = texte(v.article);
  const citation = texte(v.citation);
  if (article === null && citation === null) return null;
  const page = nombre(v.page);
  return {
    article: article ?? '',
    citation: citation ?? '',
    page: page !== null && page > 0 ? Math.round(page) : null,
    verifiee: v.verifiee === true,
  };
}

function lireTexteDeLoi(v: unknown): TexteDeLoi | null {
  if (!estObjet(v)) return null;
  const libelle = texte(v.texte);
  const url = texte(v.url);
  if (libelle === null) return null;
  return { texte: libelle, url: url !== null && /^https?:\/\//i.test(url) ? url : '' };
}

function lireDemarche(v: unknown): Demarche | null {
  if (!estObjet(v)) return null;
  const type = texte(v.type);
  if (type === null) return null;
  return {
    type,
    pourquoi: texte(v.pourquoi),
    delai: texte(v.delai),
    textes: Array.isArray(v.textes)
      ? v.textes.map(lireTexteDeLoi).filter((t): t is TexteDeLoi => t !== null)
      : [],
  };
}

export function lireReponse(v: unknown): Reponse | null {
  if (!estObjet(v)) return null;
  const verdict = texte(v.verdict);
  const corps = texte(v.texte);
  if (verdict === null && corps === null) return null;
  return {
    verdict: verdict ?? '',
    texte: corps ?? '',
    regles: Array.isArray(v.regles) ? v.regles.map(lireRegle).filter((r): r is Regle => r !== null) : [],
    a_verifier: listeDeTextes(v.a_verifier),
    demarche: lireDemarche(v.demarche),
    zone: texte(v.zone),
    duree_s: nombre(v.duree_s),
    demo: v.demo === true,
  };
}

export function lireEtape(v: unknown): EvenementEtape | null {
  if (!estObjet(v)) return null;
  const id = texte(v.id);
  if (id === null) return null;
  return { id, t: Math.max(0, nombre(v.t) ?? 0) };
}

/** `donnees/demo.json` : une liste de réponses enregistrées. Les entrées illisibles sont écartées. */
export function lireEntreesDemo(v: unknown): EntreeDemo[] {
  if (!Array.isArray(v)) return [];
  const entrees: EntreeDemo[] = [];
  for (const brut of v) {
    if (!estObjet(brut)) continue;
    const id = texte(brut.id);
    const question = texte(brut.question);
    const reponse = lireReponse(brut.reponse);
    if (id === null || question === null || reponse === null) continue;
    const etapes = Array.isArray(brut.etapes)
      ? brut.etapes.map(lireEtape).filter((e): e is EvenementEtape => e !== null)
      : [];
    entrees.push({ id, question, lieu: lireLieu(brut.lieu), etapes, reponse, duree_s: nombre(brut.duree_s) });
  }
  return entrees;
}

/** `GET /api/etat`. `null` si la forme ne ressemble pas à un état Orbi. */
export function lireEtat(v: unknown): EtatServeur | null {
  if (!estObjet(v) || !estObjet(v.modele)) return null;
  const modele = v.modele;
  const gpu = estObjet(v.gpu) ? v.gpu : null;
  const memoire = estObjet(v.memoire) ? v.memoire : null;
  const base = objet(v.base);
  const plu = objet(base.plu);
  const cadastre = objet(base.cadastre);
  const banc = estObjet(v.banc) ? v.banc : null;
  const services = objet(v.services);
  const bancJuste = banc ? nombre(banc.juste) : null;
  const bancTotal = banc ? nombre(banc.total) : null;
  return {
    mode: v.mode === 'local' ? 'local' : 'demo',
    modele: { nom: texte(modele.nom) ?? 'K2 Horizon 7B', en_ligne: modele.en_ligne === true },
    services: Object.fromEntries(
      Object.entries(services).filter((e): e is [string, boolean] => typeof e[1] === 'boolean'),
    ),
    gpu: gpu
      ? { nom: texte(gpu.nom) ?? 'GPU', utilise_go: nombre(gpu.utilise_go), total_go: nombre(gpu.total_go) }
      : null,
    memoire: memoire ? { utilise_go: nombre(memoire.utilise_go), total_go: nombre(memoire.total_go) } : null,
    temps_reponse_s: nombre(v.temps_reponse_s),
    base: {
      plu: {
        connectee: plu.connectee === true,
        commune: texte(plu.commune),
        articles: nombre(plu.articles),
        passages: nombre(plu.passages),
        zones: nombre(plu.zones),
      },
      cadastre: { connectee: cadastre.connectee === true, source: texte(cadastre.source) },
    },
    banc:
      bancJuste !== null && bancTotal !== null && bancTotal > 0
        ? { juste: bancJuste, total: bancTotal, date: texte(banc?.date) }
        : null,
  };
}
