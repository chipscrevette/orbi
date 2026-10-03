/**
 * Les zones du PLU de Biarritz : familles de couleur pour la carte, caractère de chaque zone et chapitre du règlement.
 * Les descriptions sont celles de la table des matières du règlement (PLU de Biarritz, modification n° 13, p. 2-3).
 */

export type CleFamille = 'dense' | 'moyenne' | 'faible' | 'specifique' | 'a_urbaniser' | 'naturelle' | 'autre';

export interface FamilleZone {
  cle: CleFamille;
  /** Les codes de zone, tels qu'ils apparaissent dans les réponses (« zone UH »). */
  codes: string;
  /** Deux ou trois mots, collés à la couleur dans la légende. */
  libelle: string;
  couleur: string;
}

export const FAMILLES: readonly FamilleZone[] = [
  { cle: 'dense', codes: 'UA', libelle: 'dense', couleur: '#E5484D' },
  { cle: 'moyenne', codes: 'UB UC', libelle: 'moyenne densité', couleur: '#F2883A' },
  { cle: 'faible', codes: 'UD', libelle: 'faible densité', couleur: '#EDBE2C' },
  { cle: 'specifique', codes: 'UG UH UP UY', libelle: 'équipements, hauteur, activités', couleur: '#8B5CF0' },
  { cle: 'a_urbaniser', codes: 'AU', libelle: 'à urbaniser', couleur: '#E36AA5' },
  { cle: 'naturelle', codes: 'N', libelle: 'naturelle', couleur: '#3BA55C' },
];

const AUTRE: FamilleZone = { cle: 'autre', codes: '', libelle: 'autre', couleur: '#8A96AD' };

export function familleDeZone(libelle: string | null | undefined, typezone?: string | null): FamilleZone {
  const code = (libelle ?? '').trim().toUpperCase();
  const type = (typezone ?? '').trim().toUpperCase();
  const famille = (cle: CleFamille) => FAMILLES.find((f) => f.cle === cle) ?? AUTRE;
  if (/^(I{1,2}|1|2)?AU/.test(code) || type.startsWith('AU')) return famille('a_urbaniser');
  if (code.startsWith('UA')) return famille('dense');
  if (code.startsWith('UB') || code.startsWith('UC')) return famille('moyenne');
  if (code.startsWith('UD')) return famille('faible');
  if (/^U[GHPY]/.test(code)) return famille('specifique');
  if (code.startsWith('N') || type === 'N') return famille('naturelle');
  return AUTRE;
}

export const TYPES_ZONE: Readonly<Record<string, string>> = {
  U: 'Zone urbaine',
  AUc: 'Zone à urbaniser',
  AUs: 'Zone à urbaniser (urbanisation différée)',
  A: 'Zone agricole',
  N: 'Zone naturelle',
};

/** Table des matières du règlement, p. 2-3 : « Chapitre / Zone et secteurs / Caractéristiques ». */
export const CARACTERE_ZONES: Readonly<Record<string, string>> = {
  UA: 'L’urbain aggloméré dense',
  UAc: 'Secteur de plan de masse',
  UAg: 'Secteur d’extension des équipements en sous-sol',
  UAh: 'Avec prescriptions particulières pour les hauteurs',
  UAs: 'Avec prescriptions particulières pour les aires de stationnement',
  UB: 'L’urbain aggloméré de densité moyenne',
  UBa: 'Petits quartiers',
  UBc: 'Secteur de Beaurivage',
  UBi: 'Secteur sous nuisance aérodrome (P.E.B)',
  UC: 'L’urbain aggloméré de densité moyenne',
  'UC*': 'Avec prescriptions particulières pour les hauteurs',
  UCc: 'Secteur de plan de masse',
  UD: 'L’urbain aggloméré de faible densité',
  UDa: 'Pavillonnaire aéré',
  'UDa*': 'Pavillonnaire aéré',
  UDb: 'Lotissements à villas balnéaires',
  UDc: 'Secteur destiné au développement de l’habitat inclusif',
  UDi: 'Habitat sous nuisances aérodrome',
  'UDi*': 'Habitat sous nuisances aérodrome et où certains types d’activités sont interdites',
  UDs: 'En site',
  UDt: 'Secteur destiné aux activités touristiques, essentiellement à l’hôtellerie',
  UDti: 'Secteur destiné aux activités touristiques, bureaux, services, sous nuisances aérodrome',
  UG: 'Zone destinée aux équipements',
  UGi: 'Équipements sous nuisances aérodrome',
  'UGi*': 'Équipements sous nuisances aérodrome et où certains types d’activités sont interdits',
  UGvi: 'Jardin familial et habitat adapté sous nuisances aérodrome',
  UGa: 'ZAC des Rocailles transformée en zone à plan de masse',
  UGai: 'Secteur destiné au Centre Technique Municipal',
  UGbi: 'Secteur en espaces proches du rivage',
  UP: 'Zone de mixité fonctionnelle et sociale',
  UH: 'Constructions de grande hauteur',
  UY: 'Commerce et activités industrielles',
  UYi: 'Secteur d’activités sous nuisances aérien',
  UYt: 'Secteur d’activité à vocation d’accueil-hébergement',
  'UY*': 'Secteur d’activités à fonctions limitées',
  IAUy: 'Zone à urbaniser simple, de type UY',
  IIAU: 'Urbanisation différée',
  IIAUg: 'Urbanisation destinée aux équipements',
  IIAUy: 'Urbanisation destinée aux activités',
  N: 'Zone naturelle protégée',
  Ncu: 'Zone naturelle protégée + coupure d’urbanisation',
  Ner: 'Zone naturelle, en application L 146-6',
};

/** Le chapitre du règlement qui couvre une zone : le plus long préfixe parmi les chapitres connus. */
export function chapitreDeZone(libelle: string | null | undefined, chapitres: readonly string[]): string | null {
  const code = (libelle ?? '').trim().toLowerCase();
  if (code === '') return null;
  let meilleur: string | null = null;
  for (const chapitre of chapitres) {
    if (chapitre === 'DG') continue;
    if (code.startsWith(chapitre.toLowerCase()) && (meilleur === null || chapitre.length > meilleur.length)) {
      meilleur = chapitre;
    }
  }
  return meilleur;
}

/** Le caractère d'une zone ou de son secteur, sinon celui de sa zone mère, sinon `null`. */
export function caractereZone(libelle: string | null | undefined, libelong?: string | null): string | null {
  const candidats = [libelong, libelle].map((c) => (c ?? '').trim()).filter((c) => c !== '');
  for (const c of candidats) {
    const exact = CARACTERE_ZONES[c];
    if (exact) return exact;
  }
  const cles = Object.keys(CARACTERE_ZONES);
  for (const c of candidats) {
    const sansCasse = cles.find((k) => k.toLowerCase() === c.toLowerCase());
    if (sansCasse) return CARACTERE_ZONES[sansCasse] ?? null;
  }
  for (const c of candidats) {
    const mere = chapitreDeZone(c.replace(/\*$/, ''), cles);
    if (mere) return CARACTERE_ZONES[mere] ?? null;
  }
  return null;
}

export function libelleChapitre(chapitre: string): string {
  return chapitre === 'DG' ? 'Dispositions générales' : `Zone ${chapitre}`;
}
