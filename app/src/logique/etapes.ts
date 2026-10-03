/**
 * Les six étapes affichées pendant qu'Orbi travaille, et le rangement des événements `etape` du serveur dans ces six
 * cases. Un nom d'étape inconnu (« rédaction », « garde-fous », « correction »…) ne casse rien : il est rangé dans
 * l'étape en cours.
 */
import type { EvenementEtape, Lieu } from './types.ts';

export interface DefinitionEtape {
  readonly numero: number;
  readonly libelle: string;
  readonly evenements: readonly string[];
}

export const ETAPES: readonly DefinitionEtape[] = [
  { numero: 1, libelle: 'Je lis votre question', evenements: ['tri'] },
  { numero: 2, libelle: 'Je situe le terrain', evenements: ['outils', 'verrou de zone'] },
  { numero: 3, libelle: 'Je cherche les articles du règlement', evenements: ['démarche', 'articles'] },
  { numero: 4, libelle: 'K2 remplit la grille des règles', evenements: ['analyse', 'nouvelle analyse'] },
  {
    numero: 5,
    libelle: 'Je vérifie chaque citation mot à mot',
    evenements: ['contrôle', 'citation recalée', 'citation raccordée', 'référence normalisée'],
  },
  { numero: 6, libelle: 'Je décide le verdict', evenements: ['décision', 'fin'] },
];

export type StatutEtape = 'a_venir' | 'en_cours' | 'fait' | 'saute';

export interface EtapeAffichee {
  numero: number;
  libelle: string;
  statut: StatutEtape;
  /** Temps passé dans l'étape (pour l'étape en cours : jusqu'au dernier événement reçu). */
  duree_s: number;
  /** Les événements connus reçus pour cette étape, dans l'ordre. */
  recus: string[];
  /** Les événements au nom inconnu rangés ici. */
  extras: string[];
  detail: string | null;
}

export interface Progression {
  etapes: EtapeAffichee[];
  /** Le `t` du dernier événement reçu : le minuteur de l'étape en cours repart de là. */
  dernier_t: number;
  termine: boolean;
}

/** Clé de comparaison d'un nom d'événement : sans accents ni casse ni espaces superflus. */
export function cleEvenement(id: string): string {
  return id
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/\s+/g, ' ')
    .trim();
}

const INDEX_ETAPE = new Map<string, number>(
  ETAPES.flatMap((etape, i) => etape.evenements.map((ev) => [cleEvenement(ev), i] as const)),
);

/** Index (0 à 5) de l'étape à laquelle appartient un événement, `null` s'il est inconnu. */
export function etapeDeEvenement(id: string): number | null {
  return INDEX_ETAPE.get(cleEvenement(id)) ?? null;
}

function compter(liste: readonly string[], nom: string): number {
  const cle = cleEvenement(nom);
  return liste.filter((x) => cleEvenement(x) === cle).length;
}

function pluriel(n: number, singulier: string, plurielForme: string): string {
  return `${n} ${n > 1 ? plurielForme : singulier}`;
}

/** Une étape dépassée sans événement connu : faite si du travail y a été rangé (événements inconnus), sinon sautée. */
function statutDepasse(etape: EtapeAffichee): StatutEtape {
  return etape.extras.length > 0 ? 'fait' : 'saute';
}

function detailEtape(etape: EtapeAffichee, lieu: Lieu | null): string | null {
  if (etape.statut === 'saute') return 'non nécessaire';
  if (etape.numero === 2) {
    const morceaux: string[] = [];
    if (lieu?.parcelle) morceaux.push(lieu.parcelle);
    if (lieu?.zone) morceaux.push(`zone ${lieu.zone}`);
    if (compter(etape.recus, 'verrou de zone') > 0) morceaux.push('la zone suffit à trancher');
    return morceaux.length > 0 ? morceaux.join(' · ') : null;
  }
  if (etape.numero === 4) {
    const relances = compter(etape.recus, 'nouvelle analyse');
    return relances > 0 ? `${relances + 1} passages` : null;
  }
  if (etape.numero === 5) {
    const morceaux = [
      [compter(etape.recus, 'citation recalée'), 'citation recalée', 'citations recalées'],
      [compter(etape.recus, 'citation raccordée'), 'citation raccordée', 'citations raccordées'],
      [compter(etape.recus, 'référence normalisée'), 'référence normalisée', 'références normalisées'],
    ] as const;
    const textes = morceaux.filter(([n]) => n > 0).map(([n, s, p]) => pluriel(n, s, p));
    return textes.length > 0 ? textes.join(' · ') : null;
  }
  return null;
}

/**
 * Range les événements reçus dans les six étapes.
 * Le temps entre deux événements est compté à l'étape de l'événement qui le clôt : la somme des durées
 * vaut le `t` du dernier événement. Une étape dépassée sans avoir reçu d'événement est « sautée » (non nécessaire,
 * par exemple quand le verrou de zone tranche avant l'analyse).
 */
export function regrouperEtapes(
  evenements: readonly EvenementEtape[],
  options: { termine?: boolean; lieu?: Lieu | null } = {},
): Progression {
  const etapes: EtapeAffichee[] = ETAPES.map((def) => ({
    numero: def.numero,
    libelle: def.libelle,
    statut: 'a_venir',
    duree_s: 0,
    recus: [],
    extras: [],
    detail: null,
  }));
  const derniere = etapes.length - 1;
  let plusLoin = -1;
  let tPrecedent = 0;
  let finRecue = false;

  for (const ev of evenements) {
    const t = Number.isFinite(ev.t) ? ev.t : tPrecedent;
    const ecart = Math.max(0, t - tPrecedent);
    tPrecedent = Math.max(tPrecedent, t);
    const index = etapeDeEvenement(ev.id);
    if (index === null) {
      const cible = etapes[Math.min(plusLoin + 1, derniere)];
      if (cible) {
        cible.extras.push(ev.id);
        cible.duree_s += ecart;
      }
      continue;
    }
    const etape = etapes[index];
    if (!etape) continue;
    etape.recus.push(ev.id);
    etape.duree_s += ecart;
    etape.statut = 'fait';
    if (cleEvenement(ev.id) === 'fin') finRecue = true;
    if (index > plusLoin) {
      for (let k = plusLoin + 1; k < index; k += 1) {
        const depassee = etapes[k];
        if (depassee && depassee.statut === 'a_venir') depassee.statut = statutDepasse(depassee);
      }
      plusLoin = index;
    }
  }

  const termine = options.termine === true || finRecue;
  if (termine) {
    for (const etape of etapes) if (etape.statut === 'a_venir') etape.statut = statutDepasse(etape);
  } else {
    const enCours = etapes[plusLoin + 1];
    if (enCours) enCours.statut = 'en_cours';
  }
  for (const etape of etapes) etape.detail = detailEtape(etape, options.lieu ?? null);
  return { etapes, dernier_t: tPrecedent, termine };
}
