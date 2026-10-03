import { describe, expect, it } from 'vitest';
import type { CollectionZones } from '../../src/logique/geo.ts';
import { caractereZone, chapitreDeZone, familleDeZone, libelleChapitre } from '../../src/logique/zones.ts';
import { lireJson } from '../outils.ts';

const CHAPITRES = ['DG', 'UA', 'UB', 'UC', 'UD', 'UG', 'UH', 'UP', 'UY', 'IIAU', 'N', 'Ncu', 'Ner'];

describe('familles de zones', () => {
  it('range chaque code dans sa famille de couleur', () => {
    expect(familleDeZone('UA').cle).toBe('dense');
    expect(familleDeZone('UBa').cle).toBe('moyenne');
    expect(familleDeZone('UC*').cle).toBe('moyenne');
    expect(familleDeZone('UDa').cle).toBe('faible');
    expect(familleDeZone('UH').cle).toBe('specifique');
    expect(familleDeZone('UY*').cle).toBe('specifique');
    expect(familleDeZone('IAUy', 'AUc').cle).toBe('a_urbaniser');
    expect(familleDeZone('IIAUg').cle).toBe('a_urbaniser');
    expect(familleDeZone('Ncu').cle).toBe('naturelle');
    expect(familleDeZone('NF').cle).toBe('naturelle');
    expect(familleDeZone('XYZ').cle).toBe('autre');
    expect(familleDeZone(null).cle).toBe('autre');
  });

  it('donne une famille et un caractère à toutes les zones de Biarritz', () => {
    const zones = lireJson('public', 'donnees', 'zones.geojson') as CollectionZones;
    expect(zones.features).toHaveLength(178);
    for (const z of zones.features) {
      const p = z.properties ?? {};
      expect(familleDeZone(p.libelle, p.typezone).cle, String(p.libelle)).not.toBe('autre');
      expect(caractereZone(p.libelle, p.libelong), String(p.libelle)).not.toBeNull();
    }
  });
});

describe('chapitre du règlement', () => {
  it('prend le plus long chapitre qui préfixe la zone', () => {
    expect(chapitreDeZone('Ncu', CHAPITRES)).toBe('Ncu');
    expect(chapitreDeZone('Ner', CHAPITRES)).toBe('Ner');
    expect(chapitreDeZone('Nh*', CHAPITRES)).toBe('N');
    expect(chapitreDeZone('UGA', CHAPITRES)).toBe('UG');
    expect(chapitreDeZone('UDc', CHAPITRES)).toBe('UD');
    expect(chapitreDeZone('IIAUg', CHAPITRES)).toBe('IIAU');
  });

  it('ne force pas un chapitre qui n’existe pas', () => {
    expect(chapitreDeZone('IAUy', CHAPITRES)).toBeNull();
    expect(chapitreDeZone('', CHAPITRES)).toBeNull();
    expect(chapitreDeZone(undefined, CHAPITRES)).toBeNull();
    expect(chapitreDeZone('DG', CHAPITRES)).toBeNull();
  });

  it('cite le caractère de la zone tel que le règlement le décrit', () => {
    expect(caractereZone('UDc')).toBe('Secteur destiné au développement de l’habitat inclusif');
    expect(caractereZone('UGA', 'UGa')).toBe('ZAC des Rocailles transformée en zone à plan de masse');
    expect(caractereZone('Nh')).toBe('Zone naturelle protégée');
    expect(caractereZone('Nhi*')).toBe('Zone naturelle protégée');
    expect(caractereZone('QQ')).toBeNull();
    expect(libelleChapitre('DG')).toBe('Dispositions générales');
    expect(libelleChapitre('UH')).toBe('Zone UH');
  });
});
