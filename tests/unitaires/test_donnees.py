"""Les tests du règlement découpé (reglement/donnees.py), sur les vraies phrases du PLU de Biarritz (donnees/articles.json).

La garantie centrale d'Orbi : aucune citation inventée. Une citation exacte passe, un mot changé échoue ; le recalage ne
corrige qu'une coquille (un accord), jamais un chiffre ni une négation ; le raccord remet les « … » entre des passages
exacts, dans leur ordre. Les tests marqués xfail montrent un défaut trouvé, laissé tel quel : ils passeront quand il sera
corrigé (strict : il faudra alors retirer la marque)."""
import re

import pytest

from orbi.reglement import donnees
from orbi.reglement.donnees import (ARTICLES, PAGES, article, chapitre, cite_bien, existe, morceaux, norme, page_citation,
                                    propre, raccorder, recaler, references)

PHRASE_UD7 = "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."
PISCINES = "Les piscines, spas et jacuzzis sont exclus de cette règle."
DGB5_PISCINES = ("les installations sportives de plein-air telles que piscines non couvertes, tennis ne sont pas comprises "
                 "dans l’emprise au sol")
CLOTURE = "La hauteur de la clôture ne peut excéder 2,00 mètres."  # UD 11, imprimé en page 74
# UD 9, dans l'ordre du texte ; entre les deux premiers, la ligne du secteur UDb (« à 0,30… ») que le modèle sautait
UD9_25 = "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa, UDa* et UDb ; toutefois elle peut être portée :"
UD9_040 = ("à 0,40 pour les parcelles de surface inférieure à 1.000m² en secteurs Uda et UDa*existants antérieurement à la "
           "révision du P.L.U. de 2003.")
UD9_250 = "l’emprise au sol est limitée à 250 m² au maximum pour les parcelles de surface inférieures à 1000 m²."
UD9_UDC = "En secteur UDc : L’emprise au sol maximale est fixée à 60% de l’unité foncière."
UD9_50 = "L'emprise au sol maximale en UD et en secteurs UDi et UDi*, et UDt est fixée à 50%."
MS = morceaux()


# --- propre, norme : le texte montré au modèle, le texte comparé ---

def test_propre_retire_les_puces_du_pdf_d_un_vrai_article():
    brut = article("UD 7")["texte"]
    assert "" in brut  # la puce de la police Symbol, telle que l'extraction du PDF la rend
    assert not donnees.PUCES.search(propre(brut))
    assert "En outre, Dans toute la zone et tous les secteurs, sauf en secteur UDti" in propre(brut)


@pytest.mark.parametrize("brut, attendu", [
    ("Une   ligne\ncoupée\tpar le PDF ", "Une ligne coupée par le PDF"),
    (" Dans toute la zone  voir B-5", "Dans toute la zone voir B-5"),
    ("L’emprise « au sol »", "L’emprise « au sol »"),
], ids=["espaces et retours à la ligne unifiés", "puces Symbol et Wingdings retirées",
        "apostrophe courbe et guillemets gardés : c'est le texte montré"])
def test_propre(brut, attendu):
    assert propre(brut) == attendu


@pytest.mark.parametrize("a, b", [
    ("L’emprise au sol", "l'emprise au sol"),
    ("‘annexes’", "'annexes'"),
    ("« dispositions générales »", '" dispositions générales "'),
    ("LES CONSTRUCTIONS", "les constructions"),
    ("une  espace\nde trop", "une espace de trop"),
    (" Dans toute la zone", "dans toute la zone"),
], ids=["apostrophe courbe", "apostrophes simples courbes", "guillemets français", "majuscules", "espaces et retours à la ligne",
        "puce du PDF"])
def test_norme_rend_comparables_deux_ecritures_d_une_meme_phrase(a, b):
    assert norme(a) == norme(b)


def test_norme_garde_les_accents():
    """Une citation sans accent n'est pas mot pour mot."""
    assert norme("séparatives") != norme("separatives")


# --- chapitre : la zone du plan → le chapitre du règlement ---

@pytest.mark.parametrize("zone, attendu", [
    ("UDa", "UD"), ("UAs", "UA"), ("UDti", "UD"), ("UYi", "UY"), ("Nh", "N"), ("Nhd", "N"), ("Ncu", "Ncu"), ("Ner", "Ner"),
    ("IIAU", "IIAU"), ("IAU", "IIAU"), ("1AU", "IIAU"), (" UDa ", "UD"), ("", None), (None, None), ("AU", None), ("ZZ", None),
], ids=["UDa → UD", "UAs → UA", "UDti → UD", "UYi → UY", "Nh → N", "Nhd → N", "Ncu reste Ncu (pas N)", "Ner reste Ner (pas N)",
        "IIAU", "IAU → IIAU", "1AU → IIAU", "espaces autour", "zone vide", "pas de zone", "AU : inconnue", "ZZ : inconnue"])
def test_chapitre(zone, attendu):
    assert chapitre(zone) == attendu


@pytest.mark.parametrize("chap", [c for c in ARTICLES if c != "DG"])
def test_chaque_chapitre_du_reglement_est_reconnu(chap):
    assert chapitre(chap) == chap


# --- article, existe, references ---

@pytest.mark.parametrize("ref, attendu", [
    ("UD 7", True), ("DG B-5", True), ("Ncu 1", True), ("IIAU 8", True),
    ("IIAU 7", False), ("UD 99", False), ("ZZ 1", False), ("UD7", False), ("UD", False), ("", False),
], ids=["UD 7", "DG B-5 (dispositions générales)", "Ncu 1", "IIAU 8", "IIAU 7 : absent du règlement", "UD 99", "ZZ 1",
        "« UD7 » sans espace", "chapitre seul", "référence vide"])
def test_existe(ref, attendu):
    assert existe(ref) is attendu


def test_article_rend_titre_pages_et_texte():
    a = article("UD 7")
    assert set(a) == {"titre", "pages", "texte"}
    assert PHRASE_UD7 in propre(a["texte"])
    p0, p1 = a["pages"]
    assert 1 <= p0 <= p1 <= len(PAGES)


def test_article_des_dispositions_generales():
    assert "piscines non couvertes, tennis ne sont pas comprises dans l’emprise au sol" in propre(article("DG B-5")["texte"])


@pytest.mark.parametrize("ref, erreur", [("UD 99", KeyError), ("UD", ValueError)], ids=["article absent", "sans numéro"])
def test_article_inconnu_leve_une_erreur(ref, erreur):
    with pytest.raises(erreur):
        article(ref)


def test_les_pages_des_articles_existent():
    assert [p for p, _ in PAGES] == list(range(1, len(PAGES) + 1))
    assert all(1 <= a["pages"][0] <= a["pages"][1] <= len(PAGES) for arts in ARTICLES.values() for a in arts.values())


def test_references_dans_l_ordre_des_articles():
    """« UD 10 » vient après « UD 9 », pas après « UD 1 » (ordre des nombres, pas des lettres)."""
    assert references("UD") == [f"UD {n}" for n in range(1, 15)]


def test_references_sautent_un_article_absent():
    refs = references("IIAU")
    assert "IIAU 7" not in refs and refs[5:7] == ["IIAU 6", "IIAU 8"]


def test_references_des_dispositions_generales_dans_l_ordre_du_document():
    refs = [r for r in references("DG") if r != "DG 0"]
    assert refs == [f"DG {n}" for n in ARTICLES["DG"] if n != "0"]
    assert refs[0] == "DG A-I" and refs.index("DG B-5") < refs.index("DG B-10")


def test_chaque_reference_rendue_existe():
    assert all(existe(r) for chap in ARTICLES for r in references(chap))


# --- cite_bien : la citation existe-t-elle mot pour mot dans l'article ? ---

def test_une_citation_exacte_passe():
    assert cite_bien("UD 7", PHRASE_UD7)


@pytest.mark.parametrize("citation", [
    PHRASE_UD7.replace("3 mètres", "5 mètres"),
    PHRASE_UD7.replace("peuvent", "doivent"),
    PHRASE_UD7.replace("celles-ci", "celle-ci"),
    PHRASE_UD7.replace("constructions peuvent", "constructions ne peuvent pas"),
    PHRASE_UD7.replace("séparatives", "separatives"),
], ids=["un chiffre changé", "un mot changé", "un accord changé", "une négation ajoutée", "un accent oublié"])
def test_un_mot_change_echoue(citation):
    assert not cite_bien("UD 7", citation)


def test_une_phrase_exacte_d_un_autre_article_echoue():
    """Une citation renvoie à un article exact : la phrase de UD 7 ne prouve rien pour UD 9."""
    assert not cite_bien("UD 9", PHRASE_UD7)


@pytest.mark.parametrize("citation", [
    "« Les constructions peuvent s’implanter sur les limites séparatives »",
    "LES CONSTRUCTIONS PEUVENT S'IMPLANTER sur les limites  séparatives",
    "Les constructions peuvent s'implanter\nsur les limites séparatives.",
], ids=["guillemets et apostrophe courbe", "majuscules et espace de trop", "retour à la ligne et point final"])
def test_la_typographie_ne_compte_pas(citation):
    assert cite_bien("UD 7", citation)


@pytest.mark.parametrize("sep", [" … ", " ... ", " [...] "], ids=["points de suspension", "trois points", "crochets"])
def test_des_points_de_suspension_relient_deux_passages_exacts(sep):
    assert cite_bien("UD 7", PISCINES.rstrip(".") + sep + "à au moins 3 mètres de celles-ci")


def test_deux_passages_dont_un_invente_echouent():
    assert not cite_bien("UD 7", PISCINES.rstrip(".") + " … à au moins 5 mètres de celles-ci")


@pytest.mark.parametrize("citation", ["Les constructions", "3 mètres", "", "… …"],
                         ids=["moins de 20 caractères", "moins de 12 caractères", "citation vide", "rien que des « … »"])
def test_une_citation_trop_courte_ne_prouve_rien(citation):
    assert not cite_bien("UD 7", citation)


def test_une_reference_inconnue_ne_prouve_rien():
    assert not cite_bien("UD 99", PHRASE_UD7)


@pytest.mark.parametrize("citation", [
    "Les constructions peuvent s'implanter sur les limites séparatives … à 5 mètres",
    "Les constructions peuvent s'implanter sur les limites séparatives … sauf en UDa",
], ids=["un chiffre inventé après « … »", "une exception inventée après « … »"])
def test_un_petit_morceau_invente_apres_les_points_de_suspension_echoue(citation):
    assert not cite_bien("UD 7", citation)


@pytest.mark.parametrize("fonction, args, attendu", [
    (existe, (None,), False), (cite_bien, ("UD 7", None), False), (page_citation, ("UD 7", None), None),
], ids=["existe(None)", "cite_bien(ref, None)", "page_citation(ref, None)"])
def test_une_valeur_absente_ne_fait_pas_planter_la_verification(fonction, args, attendu):
    assert fonction(*args) is attendu


# --- page_citation : la page exacte, cherchée dans les pages de l'article ---

@pytest.mark.parametrize("ref, citation, page", [
    ("UD 7", PHRASE_UD7, 69),
    ("UD 11", "Le projet peut être refusée ou n'être accordée que sous réserve de l'observation de prescriptions spéciales", 72),
    ("UD 11", "l’occultation de balcons ou loggias est interdite", 73),
    ("UD 11", CLOTURE, 74),
    ("UD 11", "l’installation de panneaux solaires est interdite sur les pans de toitures", 75),
    ("UD 11", "a - clôtures en limites séparatives … " + CLOTURE, 74),
], ids=["UD 7, une seule page", "UD 11, p. 72", "UD 11, p. 73", "UD 11, p. 74", "UD 11, p. 75",
        "avec « … » : la page du premier passage"])
def test_la_page_est_celle_de_la_citation(ref, citation, page):
    assert cite_bien(ref, citation)
    assert page_citation(ref, citation) == page


def test_une_citation_introuvable_renvoie_la_premiere_page_de_l_article():
    assert page_citation("UD 11", "Une phrase qui n'existe nulle part dans le règlement") == article("UD 11")["pages"][0]


def test_une_reference_inconnue_n_a_pas_de_page():
    assert page_citation("UD 99", PHRASE_UD7) is None


@pytest.mark.parametrize("citation", [
    "« " + CLOTURE + " »",
    "a - clôtures en limites séparatives [...] " + CLOTURE,
], ids=["citation entre guillemets", "passages reliés par [...]"])
def test_la_page_ne_depend_pas_de_la_typographie(citation):
    assert cite_bien("UD 11", citation)
    assert page_citation("UD 11", citation) == 74


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="DONNÉES : articles.json décale d'une page la plage d'une cinquantaine d'articles (UD 7 noté "
                          "69-69 finit en p. 70 ; UD 8 noté 69-70 commence en p. 70) : page_citation ne cherche pas la "
                          "bonne page, ou trouve la phrase identique de l'article précédent")
@pytest.mark.parametrize("ref, citation, page", [
    ("UD 7", "Une implantation différente de celle résultant de l'application des alinéas précédents peut être acceptée", 70),
    ("UD 8", PISCINES, 70),
], ids=["fin de UD 7, imprimée en p. 70", "phrase de UD 8 identique à celle de UD 7 (p. 69)"])
def test_la_page_suit_l_article_imprime(ref, citation, page):
    assert cite_bien(ref, citation)
    assert page_citation(ref, citation) == page


ENTETE = re.compile(r"P\.L\.U\. DE BIARRITZ appr\. le 22/12/2003 – Modification.*?"
                    r"(?:ZONE [A-Za-z ]*?[A-Za-z]|DISPOSITIONS GENERALES) (\d+)")


def pages_mal_bornees():
    """Les articles dont la plage de pages ne couvre pas leur impression : l'en-tête d'une page hors de la plage dans leur
    texte, ou (dans une zone) leur titre « ARTICLE UD 8 » absent de leur première page."""
    pages = {p: norme(t) for p, t in PAGES}
    fautes = []
    for z, arts in ARTICLES.items():
        for n, a in arts.items():
            p0, p1 = a["pages"]
            fautes += [f"{z} {n} ({p0}-{p1}) : imprimé en p. {m.group(1)}" for m in ENTETE.finditer(propre(a["texte"]))
                       if not p0 <= int(m.group(1)) <= p1]
            if z != "DG" and not re.search(rf"\barticle {z.lower()} ?{n}\b", pages[p0]):
                fautes.append(f"{z} {n} ({p0}-{p1}) : titre absent de la p. {p0}")
    return fautes


def test_l_en_tete_des_pages_est_bien_reconnu():
    """Garde-fou du test suivant : l'expression trouve l'en-tête de chaque page de zone et des dispositions générales."""
    nums = [int(m.group(1)) for p, t in PAGES for m in [ENTETE.search(propre(t))] if m]
    assert len(nums) > 120 and all(p in dict(PAGES) for p in nums)
    assert [int(m.group(1)) for m in ENTETE.finditer(propre(article("UD 7")["texte"]))] == [70]


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="DONNÉES : une cinquantaine d'articles ont une plage de pages décalée d'une page (début ou fin) "
                          "dans donnees/articles.json")
def test_les_pages_d_un_article_sont_celles_ou_il_est_imprime():
    fautes = pages_mal_bornees()
    assert not fautes, f"{len(fautes)} écarts, dont : {fautes[:4]}"


# --- recaler : une coquille corrigée, jamais un changement de sens ---

@pytest.mark.parametrize("ref, citation, exact", [
    ("UD 11", "Les dispositions énoncées ci-après s’appliquent aux ajouts et modifications des constructions existants",
     "modifications des constructions existantes"),
    ("UD 7", PHRASE_UD7.replace("celles-ci", "celle-ci"), "à au moins 3 mètres de celles-ci"),
    ("UD 2", "L’extension mesurée des constructions existante, avec au plus 25 m2 d’emprise au sol",
     "constructions existantes, avec au plus 25 m2 d’emprise au sol"),
], ids=["« existants » → « existantes »", "« celle-ci » → « celles-ci »", "un accord corrigé, les chiffres gardés"])
def test_recaler_corrige_un_accord(ref, citation, exact):
    assert not cite_bien(ref, citation)
    r = recaler(ref, citation)
    assert r is not None and exact in r
    assert cite_bien(ref, r)  # ce qui s'affiche est le texte du règlement


@pytest.mark.parametrize("ref, citation", [
    ("UD 7", PHRASE_UD7.replace("3 mètres", "5 mètres")),
    ("UD 2", "L’extension mesurée des constructions existantes, avec au plus 30 m2 d’emprise au sol"),
    ("DG B-5", DGB5_PISCINES.replace("ne sont pas comprises", "sont comprises")),
    ("DG B-5", DGB5_PISCINES.replace("piscines non couvertes", "piscines couvertes")),
    ("UY 11", "La pose de volet roulant avec coffre extérieur est autorisée."),
], ids=["3 mètres → 5 mètres", "25 m2 → 30 m2", "« ne … pas » enlevé", "« non » enlevé", "« interdite » → « autorisée »"])
def test_recaler_refuse_un_chiffre_ou_une_negation_change(ref, citation):
    assert recaler(ref, citation) is None
    # même en acceptant des passages bien moins proches, le refus tient : c'est le sens qui bloque, pas la ressemblance
    assert recaler(ref, citation, seuil=0.5) is None


@pytest.mark.parametrize("ref, citation", [
    ("UD 7", PHRASE_UD7.replace("au moins", "au plus")),
    ("UD 8", "La distance maximum entre deux constructions non contiguës est fixée au quart de la somme de leurs hauteurs"),
    ("UD 9", "à 0,30 pour les parcelles de surface supérieure à 1.000 m² en secteur UDb"),
    ("UD 7", "Les piscines, spas et jacuzzis sont inclus dans cette règle."),
], ids=["« au moins » → « au plus »", "« minimum » → « maximum »", "« inférieure » → « supérieure »",
        "« exclus de » → « inclus dans »"])
def test_recaler_refuse_un_contraire(ref, citation):
    assert recaler(ref, citation) is None


def test_recaler_rend_une_citation_deja_exacte():
    assert recaler("UD 7", PHRASE_UD7) == PHRASE_UD7.rstrip(".")


def test_recaler_garde_les_points_de_suspension():
    r = recaler("UD 7", PISCINES.rstrip(".") + " … Les constructions peuvent s'implanter sur les limite séparatives")
    assert r == PISCINES.rstrip(".") + " … Les constructions peuvent s'implanter sur les limites séparatives"
    assert cite_bien("UD 7", r)


@pytest.mark.parametrize("ref, citation", [
    ("UD 7", "Il est interdit de construire à moins de 10 mètres de toute limite."),
    ("UD 7", "3 mètres"),
    ("UD 7", ""),
    ("UD 7", None),
    ("UD 99", PHRASE_UD7),
], ids=["phrase inventée", "trop courte pour être recalée", "citation vide", "pas de citation", "article inconnu"])
def test_recaler_ne_rend_rien(ref, citation):
    assert recaler(ref, citation) is None


# --- raccorder : des passages exacts mis bout à bout, les « … » remis ---

def test_raccorder_remet_les_points_de_suspension_la_ou_le_modele_a_saute():
    """Le cas du 3e passage : dans UD 9, le modèle sautait sans le dire la ligne du secteur UDb (« à 0,30… »)."""
    cit = UD9_25 + " " + UD9_040
    assert not cite_bien("UD 9", cit)
    r = raccorder("UD 9", cit)
    assert r == UD9_25 + " … " + UD9_040.rstrip(".")
    assert "0,30" not in r and cite_bien("UD 9", r)


def test_raccorder_rend_le_texte_du_reglement_pas_celui_du_modele():
    r = raccorder("UD 9", (UD9_25 + " " + UD9_040).upper())
    assert r == UD9_25 + " … " + UD9_040.rstrip(".")


def test_raccorder_trois_passages():
    r = raccorder("UD 9", " ".join([UD9_25, UD9_040, UD9_250]))
    assert r is not None and r.split(" … ") == [UD9_25, UD9_040, UD9_250.rstrip(".")]


def test_raccorder_refuse_plus_de_trois_passages():
    cit = " ".join([UD9_25, UD9_040, UD9_250, UD9_UDC])
    assert raccorder("UD 9", cit) is None
    assert len(raccorder("UD 9", cit, morceaux_max=4).split(" … ")) == 4


def test_raccorder_refuse_des_passages_dans_le_desordre():
    assert raccorder("UD 9", UD9_040 + " " + UD9_25) is None


def test_raccorder_refuse_un_saut_de_plus_de_300_caracteres():
    """Une coupure trop longue pourrait changer le sens : entre 50 % et le secteur UDc, il y a les autres secteurs."""
    cit = UD9_50 + " " + UD9_UDC
    assert raccorder("UD 9", cit) is None
    assert raccorder("UD 9", cit, saut_max=2000) == UD9_50 + " … " + UD9_UDC.rstrip(".")


@pytest.mark.parametrize("ref, citation", [
    ("UD 9", UD9_50 + " Les vérandas sont interdites partout."),
    ("UD 9", UD9_25 + " à 0,30 pour"),
    ("UD 9", UD9_50),
    ("UD 9", ""),
    ("UD 9", None),
    ("UD 99", UD9_25 + " " + UD9_040),
], ids=["une fin inventée", "un morceau de moins de 20 caractères", "un seul passage : rien à raccorder", "citation vide",
        "pas de citation", "article inconnu"])
def test_raccorder_ne_rend_rien(ref, citation):
    assert raccorder(ref, citation) is None


def test_raccorder_refuse_un_texte_dont_la_minuscule_change_la_longueur(monkeypatch):
    """« İ » (I pointé) devient deux caractères en minuscules : les positions trouvées ne désigneraient plus le texte
    d'origine, et la citation rendue serait décalée. Le raccord refuse plutôt que de rendre un texte faux."""
    texte = UD9_25 + " - à 0,30 pour les parcelles de surface inférieure à 1.000 m² en secteur UDb. - " + UD9_040
    monkeypatch.setitem(ARTICLES["UD"], "98", {"titre": "", "pages": [70, 70], "texte": texte})
    monkeypatch.setitem(ARTICLES["UD"], "99", {"titre": "", "pages": [70, 70], "texte": "İ " + texte})
    cit = UD9_25 + " " + UD9_040
    assert raccorder("UD 98", cit) == UD9_25 + " … " + UD9_040.rstrip(".")  # le même texte sans « İ » se raccorde
    assert raccorder("UD 99", cit) is None


# --- morceaux : les morceaux de la recherche, chacun avec sa référence ---

def test_les_dispositions_generales_entieres_ne_sont_pas_un_morceau():
    """« DG 0 » est le bloc entier des dispositions générales : ses articles ont déjà leurs propres morceaux."""
    assert all(m["ref"] != "DG 0" for m in MS)


def test_chaque_article_a_ses_morceaux_et_chaque_morceau_sa_reference():
    attendues = {f"{z} {n}" for z, arts in ARTICLES.items() for n in arts} - {"DG 0"}
    assert {m["ref"] for m in MS} == attendues
    for m in MS:
        assert m["chapitre"] == m["ref"].split()[0] and m["pages"] == article(m["ref"])["pages"]


def test_un_article_court_est_un_seul_morceau():
    ud8 = [m for m in MS if m["ref"] == "UD 8"]
    assert len(ud8) == 1 and ud8[0]["texte"] == propre(article("UD 8")["texte"])


def test_les_morceaux_sont_le_texte_montre_au_modele():
    assert not any(donnees.PUCES.search(m["texte"]) for m in MS)


@pytest.mark.parametrize("taille, recouvrement", [(1200, 200), (500, 100)], ids=["réglage par défaut", "petits morceaux"])
def test_un_long_article_est_coupe_avec_recouvrement(taille, recouvrement):
    texte = propre(article("UD 11")["texte"])
    ms = [m["texte"] for m in morceaux(taille, recouvrement) if m["ref"] == "UD 11"]
    pas = taille - recouvrement
    assert len(ms) > 1
    assert all(t == texte[i * pas:i * pas + taille] for i, t in enumerate(ms))  # chaque morceau reprend la fin du précédent
    assert (len(ms) - 1) * pas + len(ms[-1]) == len(texte)  # rien ne se perd à la coupe


@pytest.mark.xfail(strict=True, raises=AssertionError,
                   reason="DÉFAUT : quand la fin d'un article tient dans le recouvrement, morceaux() ajoute une queue déjà "
                          "contenue dans le morceau précédent (16 articles ; « nt et de sa situation. » pour UP 12) ; courte, "
                          "BM25 la gonfle et elle passe avant le vrai passage")
def test_aucun_morceau_n_est_deja_contenu_dans_le_precedent():
    doublons = [b["ref"] for a, b in zip(MS, MS[1:]) if a["ref"] == b["ref"] and b["texte"] in a["texte"]]
    assert doublons == []
