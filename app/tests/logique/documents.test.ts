import { describe, expect, it } from 'vitest';
import {
  decouperReference,
  indexerReglement,
  lienPage,
  lireReglement,
  normaliserPourRecherche,
  rechercherArticles,
  referenceArticle,
  segmenter,
  termesRecherche,
  titreArticle,
} from '../../src/logique/documents.ts';
import { existe, lireJson } from '../outils.ts';

describe('titres et références', () => {
  it('sépare le titre en capitales du début du texte', () => {
    expect(
      titreArticle('LES OCCUPATIONS ET UTILISATIONS DU SOL SOUMISES A DES CONDITIONS PARTICULIERES  Sauf en U'),
    ).toBe('LES OCCUPATIONS ET UTILISATIONS DU SOL SOUMISES A DES CONDITIONS PARTICULIERES');
    expect(titreArticle('LES OCCUPATIONS ET UTILISATIONS DU SOL SOUMISES - les insta')).toBe(
      'LES OCCUPATIONS ET UTILISATIONS DU SOL SOUMISES',
    );
    expect(titreArticle("CHAMP D'APPLICATION TERRITORIAL DU PLAN Le présent règlement")).toBe(
      "CHAMP D'APPLICATION TERRITORIAL DU PLAN",
    );
    expect(titreArticle('Dispositions générales')).toBe('Dispositions générales');
  });

  it('signale un titre coupé par l’extraction', () => {
    const coupe = 'LES CONDITIONS DE DESSERTE DES TERRAINS PAR LES VOIES PUBLIQUES OU PRIVEES ET D’ACCES AUX VOIES';
    expect(titreArticle(coupe)).toBe(`${coupe}…`);
  });

  it('écrit et découpe les références d’articles', () => {
    expect(referenceArticle('UH', '10')).toBe('UH 10');
    expect(referenceArticle('DG', 'A-I')).toBe('DG A-I');
    expect(referenceArticle('DG', '0')).toBe('DG');
    expect(decouperReference('UH 10')).toEqual({ chapitre: 'UH', article: '10' });
    expect(decouperReference(' DG A-I ')).toEqual({ chapitre: 'DG', article: 'A-I' });
    expect(decouperReference('N')).toEqual({ chapitre: 'N', article: null });
    expect(decouperReference('')).toBeNull();
    expect(lienPage(93)).toBe('donnees/reglement-biarritz.pdf#page=93');
  });
});

describe('recherche plein texte', () => {
  it('normalise sans changer la longueur du texte', () => {
    const t = 'Clôtures, L’ÉMPRISE au sol : 50 %';
    expect(normaliserPourRecherche(t)).toHaveLength(t.length);
    expect(normaliserPourRecherche(t)).toBe("clotures, l'emprise au sol : 50 %");
    expect(termesRecherche('  Clôture  de  2 m ')).toEqual(['cloture', 'de']);
  });

  it('surligne les occurrences dans le texte d’origine', () => {
    const texte = 'Les clôtures sur rue : clôture à claire-voie.';
    const segments = segmenter(texte, normaliserPourRecherche(texte), ['cloture']);
    expect(segments.filter((s) => s.surligne).map((s) => s.texte)).toEqual(['clôture', 'clôture']);
    expect(segments.map((s) => s.texte).join('')).toBe(texte);
  });

  const AVEC_REGLEMENT = existe('..', 'donnees', 'articles.json');

  it.skipIf(!AVEC_REGLEMENT)('lit les 189 articles du règlement de Biarritz', () => {
    const chapitres = lireReglement(lireJson('..', 'donnees', 'articles.json'));
    expect(chapitres.map((c) => c.cle)).toEqual(['DG', 'UA', 'UB', 'UC', 'UD', 'UG', 'UH', 'UP', 'UY', 'IIAU', 'N', 'Ncu', 'Ner']);
    expect(chapitres.reduce((s, c) => s + c.articles.length, 0)).toBe(189);
    const uh10 = chapitres.find((c) => c.cle === 'UH')!.articles.find((a) => a.cle === '10')!;
    expect(uh10).toMatchObject({ reference: 'UH 10', titre: 'LA HAUTEUR MAXIMALE DES CONSTRUCTIONS', pages: [93, 94] });
  });

  it.skipIf(!AVEC_REGLEMENT)('trouve les articles qui contiennent tous les termes, sans accents ni casse', () => {
    const index = indexerReglement(lireReglement(lireJson('..', 'donnees', 'articles.json')));
    const clotures = rechercherArticles(index, 'CLOTURE');
    expect(clotures.length).toBeGreaterThan(5);
    expect(clotures.map((r) => r.article.reference)).toContain('UH 11');
    for (const r of clotures) {
      const surlignes = r.extrait.filter((s) => s.surligne).map((s) => normaliserPourRecherche(s.texte));
      expect(surlignes.length, r.article.reference).toBeGreaterThan(0);
      expect(surlignes.every((s) => s.includes('cloture'))).toBe(true);
    }
    const deux = rechercherArticles(index, 'clôture hauteur', { chapitre: 'UH' });
    expect(deux.every((r) => r.article.chapitre === 'UH')).toBe(true);
    expect(rechercherArticles(index, '')).toEqual([]);
    expect(rechercherArticles(index, 'xylophonequantique')).toEqual([]);
  });
});
