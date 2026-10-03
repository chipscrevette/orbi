/** Géométrie minimale pour les zones du PLU (GeoJSON en WGS 84) : point dans polygone, emprise. */
import type { Point } from './types.ts';

export type Position = readonly number[];
export type Anneau = readonly Position[];

export type Geometrie =
  | { type: 'Polygon'; coordinates: readonly Anneau[] }
  | { type: 'MultiPolygon'; coordinates: readonly (readonly Anneau[])[] }
  | { type: string; coordinates?: unknown };

export interface ProprietesZone {
  libelle?: string;
  libelong?: string;
  typezone?: string;
  [cle: string]: unknown;
}

export interface EntiteZone {
  type: 'Feature';
  id?: string | number;
  geometry: Geometrie | null;
  properties: ProprietesZone | null;
}

export interface CollectionZones {
  type: 'FeatureCollection';
  features: EntiteZone[];
}

/** [ouest, sud, est, nord] */
export type Emprise = readonly [number, number, number, number];

/** Lancer de rayon : le point est-il dans l'anneau (bord exclu ou inclus selon l'arrondi, sans importance ici) ? */
export function pointDansAnneau(point: Point, anneau: Anneau): boolean {
  const [x, y] = point;
  let dedans = false;
  for (let i = 0, j = anneau.length - 1; i < anneau.length; j = i, i += 1) {
    const a = anneau[i];
    const b = anneau[j];
    if (!a || !b) continue;
    const xi = a[0] ?? 0;
    const yi = a[1] ?? 0;
    const xj = b[0] ?? 0;
    const yj = b[1] ?? 0;
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) dedans = !dedans;
  }
  return dedans;
}

/** Dans l'anneau extérieur et dans aucun trou. */
export function pointDansPolygone(point: Point, polygone: readonly Anneau[]): boolean {
  const [exterieur, ...trous] = polygone;
  if (!exterieur || !pointDansAnneau(point, exterieur)) return false;
  return !trous.some((trou) => pointDansAnneau(point, trou));
}

function polygones(geometrie: Geometrie | null): readonly (readonly Anneau[])[] {
  if (!geometrie || !Array.isArray(geometrie.coordinates)) return [];
  if (geometrie.type === 'Polygon') return [geometrie.coordinates as readonly Anneau[]];
  if (geometrie.type === 'MultiPolygon') return geometrie.coordinates as readonly (readonly Anneau[])[];
  return [];
}

export function pointDansGeometrie(point: Point, geometrie: Geometrie | null): boolean {
  return polygones(geometrie).some((polygone) => pointDansPolygone(point, polygone));
}

/** La première zone qui contient le point, sinon `null`. */
export function zoneAuPoint<E extends EntiteZone>(entites: readonly E[], point: Point): E | null {
  return entites.find((e) => pointDansGeometrie(point, e.geometry)) ?? null;
}

export function emprise(geometrie: Geometrie | null): Emprise | null {
  let ouest = Infinity;
  let sud = Infinity;
  let est = -Infinity;
  let nord = -Infinity;
  for (const polygone of polygones(geometrie)) {
    for (const anneau of polygone) {
      for (const position of anneau) {
        const x = position[0];
        const y = position[1];
        if (x === undefined || y === undefined) continue;
        ouest = Math.min(ouest, x);
        sud = Math.min(sud, y);
        est = Math.max(est, x);
        nord = Math.max(nord, y);
      }
    }
  }
  return Number.isFinite(ouest) ? [ouest, sud, est, nord] : null;
}

/** Emprise de toute une collection. */
export function empriseCollection(entites: readonly EntiteZone[]): Emprise | null {
  let total: Emprise | null = null;
  for (const entite of entites) {
    const e = emprise(entite.geometry);
    if (!e) continue;
    total = total
      ? [Math.min(total[0], e[0]), Math.min(total[1], e[1]), Math.max(total[2], e[2]), Math.max(total[3], e[3])]
      : e;
  }
  return total;
}
