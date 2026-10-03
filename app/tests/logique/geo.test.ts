import { describe, expect, it } from 'vitest';
import { lireEntreesDemo } from '../../src/logique/contrat.ts';
import {
  emprise,
  empriseCollection,
  pointDansGeometrie,
  zoneAuPoint,
  type CollectionZones,
  type EntiteZone,
} from '../../src/logique/geo.ts';
import { lireJson } from '../outils.ts';

const ZONES = lireJson('public', 'donnees', 'zones.geojson') as CollectionZones;
const DEMO = lireEntreesDemo(lireJson('public', 'donnees', 'demo.json'));

const carre = (x0: number, y0: number, cote: number) => [
  [x0, y0],
  [x0 + cote, y0],
  [x0 + cote, y0 + cote],
  [x0, y0 + cote],
  [x0, y0],
];

describe('point dans polygone', () => {
  it('distingue dedans, dehors et trou', () => {
    const avecTrou = { type: 'Polygon', coordinates: [carre(0, 0, 10), carre(4, 4, 2)] };
    expect(pointDansGeometrie([1, 1], avecTrou)).toBe(true);
    expect(pointDansGeometrie([11, 1], avecTrou)).toBe(false);
    expect(pointDansGeometrie([5, 5], avecTrou)).toBe(false);
  });

  it('gère les multipolygones et les géométries absentes', () => {
    const multi = { type: 'MultiPolygon', coordinates: [[carre(0, 0, 1)], [carre(5, 5, 1)]] };
    expect(pointDansGeometrie([5.5, 5.5], multi)).toBe(true);
    expect(pointDansGeometrie([3, 3], multi)).toBe(false);
    expect(pointDansGeometrie([0.5, 0.5], null)).toBe(false);
    expect(pointDansGeometrie([0.5, 0.5], { type: 'Point', coordinates: [0.5, 0.5] })).toBe(false);
  });

  it('calcule les emprises', () => {
    expect(emprise({ type: 'Polygon', coordinates: [carre(1, 2, 3)] })).toEqual([1, 2, 4, 5]);
    expect(emprise(null)).toBeNull();
    const e = empriseCollection(ZONES.features)!;
    expect(e[0]).toBeCloseTo(-1.57719, 5);
    expect(e[3]).toBeCloseTo(43.49449, 5);
  });
});

describe('les zones du PLU et les lieux enregistrés', () => {
  it('trouve, pour chaque lieu de démo, une zone dont le code commence comme celui de la réponse', () => {
    for (const entree of DEMO) {
      const lieu = entree.lieu!;
      const zone: EntiteZone | null = zoneAuPoint(ZONES.features, lieu.point!);
      expect(zone, entree.id).not.toBeNull();
      const libelle = String(zone!.properties?.libelle ?? '');
      expect(libelle.toLowerCase().startsWith(lieu.zone!.toLowerCase().slice(0, 2)), `${entree.id} : ${libelle} / ${lieu.zone}`).toBe(true);
    }
  });

  it('ne trouve rien hors de Biarritz', () => {
    expect(zoneAuPoint(ZONES.features, [2.35, 48.85])).toBeNull();
  });
});
