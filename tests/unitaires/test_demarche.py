"""La démarche administrative (demarche.py), calculée par le code à partir du Code de l'urbanisme. Ce que le module garantit :
  · chaque projet tombe dans la bonne démarche (rien, déclaration préalable, permis, permis + architecte), seuil par seuil :
    juste en dessous, pile sur et juste au-dessus de 5, 10, 20, 40, 100 et 150 m² (R421-2, R421-9, R421-14, R431-2) ;
  · une piscine couverte d'un abri de 1,80 m ou plus passe au permis, quelle que soit sa surface (R421-9) ;
  · le site patrimonial retire les dispenses et allonge les délais (avis de l'ABF) ; à Biarritz, toute clôture se déclare (R421-12 d) ;
  · une surface plus grande, un site protégé ou une zone non urbaine ne demandent jamais une démarche plus légère ;
  · chaque résultat dit pourquoi, cite ses articles avec leur lien et porte le délai de sa propre démarche.
Une règle nationale et stable : le code la calcule, le modèle n'a rien à deviner."""
import pytest

from orbi.domaine.demarche import LEGIFRANCE, delai, demarche
from orbi.reglement.donnees import cite_bien

RIEN, DP, PC = "aucune formalité", "déclaration préalable", "permis de construire"
PC_ARCHITECTE = "permis de construire + architecte"
RANG = {RIEN: 0, DP: 1, PC: 2, PC_ARCHITECTE: 3}  # de la démarche la plus légère à la plus lourde
PROJETS = ("véranda", "extension", "surélévation", "abri de jardin", "piscine", "clôture", "maison neuve")
CHIFFRES = ("véranda", "extension", "surélévation", "abri de jardin", "piscine")  # ceux dont la démarche dépend de la surface
SURFACES = (0.5, 3, 4.9, 5, 5.1, 9.9, 10, 10.1, 15, 19.9, 20, 20.1, 30, 39.9, 40, 40.1, 60, 99.9, 100, 100.1, 149.9, 150, 150.1, 200)


def articles(r):
    """Les articles du Code de l'urbanisme cités par une démarche, dans l'ordre."""
    return [t["texte"] for t in r["textes"]]


def m2(x):
    """« 4,9 m² » : une surface lisible dans le nom d'un cas."""
    return f"{x:g} m²".replace(".", ",")


# ------------------------------------------------------------------------------------------------ abri de jardin (R421-2, R421-9)
ABRI = [(4.9, RIEN, ["R421-2"]), (5, RIEN, ["R421-2"]), (5.1, DP, ["R421-9"]), (19.9, DP, ["R421-9"]), (20, DP, ["R421-9"]),
        (20.1, PC, ["R421-9"])]


@pytest.mark.parametrize("surface, attendu, textes", ABRI, ids=[f"{m2(s)} : {a}" for s, a, _ in ABRI])
def test_un_abri_de_jardin_suit_les_seuils_de_5_et_20_m2(surface, attendu, textes):
    r = demarche("abri de jardin", surface)
    assert (r["type"], articles(r)) == (attendu, textes)


ABRI_PROTEGE = [(3, DP, ["R421-11"]), (5, DP, ["R421-11"]), (5.1, DP, ["R421-11"]), (20, DP, ["R421-11"]), (20.1, PC, ["R421-9"])]


@pytest.mark.parametrize("surface, attendu, textes", ABRI_PROTEGE, ids=[f"{m2(s)} : {a}" for s, a, _ in ABRI_PROTEGE])
def test_en_site_patrimonial_un_abri_de_5_m2_au_plus_se_declare_aussi(surface, attendu, textes):
    r = demarche("abri de jardin", surface, protege=True)
    assert (r["type"], articles(r)) == (attendu, textes)
    assert ("en site patrimonial, même sous 5 m²" in r["pourquoi"]) == (attendu == DP)


def test_un_abri_sans_surface_annonce_les_trois_issues_et_leurs_delais():
    r = demarche("abri de jardin")
    assert (r["type"], articles(r)) == ("dépend de la surface", ["R421-2", "R421-9"])
    assert "5 m²" in r["pourquoi"] and "20 m²" in r["pourquoi"]
    assert r["delai"] == "1 mois pour une déclaration préalable ; 2 mois en principe pour un permis"


# ------------------------------------------------------------------------------------------------ piscine (R421-2, R421-9)
PISCINE = [(9.9, RIEN, ["R421-2"]), (10, RIEN, ["R421-2"]), (10.1, DP, ["R421-9"]), (99.9, DP, ["R421-9"]), (100, DP, ["R421-9"]),
           (100.1, PC, ["R421-9"])]


@pytest.mark.parametrize("surface, attendu, textes", PISCINE, ids=[f"{m2(s)} : {a}" for s, a, _ in PISCINE])
def test_une_piscine_non_couverte_suit_les_seuils_de_10_et_100_m2(surface, attendu, textes):
    r = demarche("piscine", surface)
    assert (r["type"], articles(r)) == (attendu, textes)


PISCINE_PROTEGEE = [(6, DP, ["R421-9", "R421-2"]), (10, DP, ["R421-9", "R421-2"]), (10.1, DP, ["R421-9"]), (100, DP, ["R421-9"]),
                    (100.1, PC, ["R421-9"])]


@pytest.mark.parametrize("surface, attendu, textes", PISCINE_PROTEGEE, ids=[f"{m2(s)} : {a}" for s, a, _ in PISCINE_PROTEGEE])
def test_en_site_patrimonial_un_bassin_de_10_m2_au_plus_se_declare(surface, attendu, textes):
    """Hors site protégé, un bassin de 10 m² au plus est dispensé de toute formalité ; en site patrimonial, plus de dispense."""
    r = demarche("piscine", surface, protege=True)
    assert (r["type"], articles(r)) == (attendu, textes)
    assert ("en site patrimonial, pas de dispense" in r["pourquoi"]) == (surface <= 10)


@pytest.mark.parametrize("protege", [False, True], ids=["hors site protégé", "en site patrimonial"])
@pytest.mark.parametrize("surface", [None, 5, 10, 100, 150], ids=["sans surface", "5 m²", "10 m²", "100 m²", "150 m²"])
def test_une_piscine_couverte_demande_un_permis(surface, protege):
    """R421-9 : un abri de 1,80 m ou plus fait passer la piscine au permis, même sans surface donnée, même sous 10 m²."""
    r = demarche("piscine", surface, protege=protege, couverte=True)
    assert (r["type"], articles(r)) == (PC, ["R421-9"])
    assert "1,80 m" in r["pourquoi"]


def test_une_piscine_sans_surface_annonce_les_trois_issues():
    r = demarche("piscine")
    assert (r["type"], articles(r)) == ("dépend de la surface du bassin", ["R421-2", "R421-9"])
    assert "10 m²" in r["pourquoi"] and "100 m²" in r["pourquoi"]


# ------------------------------------------------------------------------------------------------ véranda, extension (R421-14)
URBAINE = [(39.9, DP), (40, DP), (40.1, PC)]
NON_URBAINE = [(19.9, DP), (20, DP), (20.1, PC)]


@pytest.mark.parametrize("projet", ["extension", "véranda"])
@pytest.mark.parametrize("surface, attendu", URBAINE, ids=[f"{m2(s)} : {a}" for s, a in URBAINE])
def test_en_zone_urbaine_le_permis_commence_au_dela_de_40_m2(projet, surface, attendu):
    r = demarche(projet, surface, zone_urbaine=True)
    assert (r["type"], articles(r)) == (attendu, ["R421-14"])
    assert "40 m²" in r["pourquoi"]
    assert ("(zone urbaine)" in r["pourquoi"]) == (attendu == DP)


@pytest.mark.parametrize("projet", ["extension", "véranda"])
@pytest.mark.parametrize("surface, attendu", NON_URBAINE, ids=[f"{m2(s)} : {a}" for s, a in NON_URBAINE])
def test_hors_zone_urbaine_le_permis_commence_au_dela_de_20_m2(projet, surface, attendu):
    r = demarche(projet, surface, zone_urbaine=False)
    assert (r["type"], articles(r)) == (attendu, ["R421-14"])
    assert "20 m²" in r["pourquoi"] and "zone urbaine" not in r["pourquoi"]


@pytest.mark.parametrize("projet", ["extension", "véranda"])
def test_une_extension_sans_surface_annonce_les_deux_seuils(projet):
    r = demarche(projet)
    assert (r["type"], articles(r)) == ("dépend de la surface", ["R421-14"])
    assert "20 m²" in r["pourquoi"] and "40 m²" in r["pourquoi"]


# ------------------------------------------------------------------------------------------------ l'architecte (R421-14 b, R431-2)
TOTAL = [(149.9, DP), (150, DP), (150.1, PC_ARCHITECTE)]


@pytest.mark.parametrize("total, attendu", TOTAL, ids=[f"{m2(t)} après travaux : {a}" for t, a in TOTAL])
def test_au_dela_de_150_m2_apres_travaux_le_permis_et_l_architecte_reviennent(total, attendu):
    """30 m² en zone urbaine restent sous le seuil de 40 m² ; mais si la maison dépasse 150 m² après travaux, les travaux de plus
    de 20 m² repassent au permis (R421-14 b), et l'architecte devient obligatoire (R431-2)."""
    r = demarche("extension", 30, total)
    assert r["type"] == attendu
    if attendu == PC_ARCHITECTE:
        assert articles(r) == ["R421-14", "R431-2"]
        assert "au-delà de 150 m²" in r["pourquoi"]


GRANDE = [(150, PC), (150.1, PC_ARCHITECTE)]


@pytest.mark.parametrize("total, attendu", GRANDE, ids=[f"{m2(t)} après travaux : {a}" for t, a in GRANDE])
def test_un_permis_de_plus_de_40_m2_prend_l_architecte_au_dela_de_150_m2_apres_travaux(total, attendu):
    assert demarche("extension", 45, total)["type"] == attendu


PETITE = [(19.9, DP), (20, DP), (20.1, PC_ARCHITECTE)]


@pytest.mark.parametrize("surface, attendu", PETITE, ids=[f"{m2(s)} créés : {a}" for s, a in PETITE])
def test_jusqu_a_20_m2_crees_la_declaration_suffit_meme_au_dela_de_150_m2(surface, attendu):
    """R421-14 b : le retour au permis au-delà de 150 m² ne vise que les travaux de plus de 20 m²."""
    assert demarche("extension", surface, 300)["type"] == attendu


@pytest.mark.parametrize("projet", ["extension", "véranda", "surélévation"])
@pytest.mark.parametrize("surface", [150.1, 200], ids=["150,1 m² créés", "200 m² créés"])
def test_plus_de_150_m2_crees_imposent_l_architecte_meme_sans_la_surface_existante(projet, surface):
    assert demarche(projet, surface)["type"] == PC_ARCHITECTE


# ------------------------------------------------------------------------------------------------ surélévation, maison neuve
SURELEVATION = [(10, None, True, False), (40, None, True, False), (40.1, None, True, False), (20.1, None, False, False),
                (30, 160, True, False), (30, 120, True, True)]


@pytest.mark.parametrize("surface, total, zone_urbaine, protege", SURELEVATION,
                         ids=["10 m²", "40 m² pile", "40,1 m²", "20,1 m² hors zone urbaine", "30 m², 160 m² après travaux",
                              "30 m² en site patrimonial"])
def test_une_surelevation_chiffree_suit_les_regles_de_l_extension(surface, total, zone_urbaine, protege):
    assert demarche("surélévation", surface, total, zone_urbaine, protege) == demarche("extension", surface, total, zone_urbaine, protege)


def test_une_surelevation_sans_surface_demande_au_moins_une_declaration():
    """Elle modifie l'aspect extérieur : jamais « aucune formalité », même sans surface créée connue."""
    r = demarche("surélévation")
    assert (r["type"], articles(r)) == ("dépend de la surface créée", ["R421-14"])
    assert r["pourquoi"].startswith("au moins une déclaration préalable")


@pytest.mark.parametrize("zone_urbaine, protege", [(True, False), (False, False), (True, True)],
                         ids=["zone urbaine", "zone naturelle", "site patrimonial"])
@pytest.mark.parametrize("surface", [None, 90, 150], ids=["sans surface", "90 m²", "150 m² pile"])
def test_une_maison_neuve_demande_toujours_un_permis(surface, zone_urbaine, protege):
    r = demarche("maison neuve", surface, zone_urbaine=zone_urbaine, protege=protege)
    assert (r["type"], articles(r)) == (PC, ["R421-9"])


@pytest.mark.parametrize("surface", [150.1, 200], ids=["150,1 m²", "200 m²"])
def test_une_maison_neuve_de_plus_de_150_m2_impose_l_architecte(surface):
    assert demarche("maison neuve", surface)["type"] == PC_ARCHITECTE


# ------------------------------------------------------------------------------------------------ clôture (R421-2, R421-12)
CLOTURE = [(False, True, DP, ["R421-12"]), (True, True, DP, ["R421-12"]), (True, False, DP, ["R421-12"]),
           (False, False, RIEN, ["R421-2", "R421-12"])]


@pytest.mark.parametrize("protege, clotures_declarees, attendu, textes", CLOTURE,
                         ids=["Biarritz, délibération de 2007", "site patrimonial", "site patrimonial, commune sans délibération",
                              "commune sans délibération, hors site protégé"])
def test_une_cloture_se_declare_sauf_hors_site_protege_dans_une_commune_qui_ne_l_impose_pas(protege, clotures_declarees,
                                                                                            attendu, textes):
    r = demarche("clôture", protege=protege, clotures_declarees=clotures_declarees)
    assert (r["type"], articles(r)) == (attendu, textes)


def test_a_biarritz_une_cloture_se_declare_et_le_reglement_le_rappelle_mot_pour_mot():
    """R421-12 d : la commune a soumis les clôtures à déclaration. Le pourquoi renvoie à l'article DG B-8 : la phrase doit y être."""
    r = demarche("clôture")
    assert r["type"] == DP
    assert "DG B-8" in r["pourquoi"] and "21/09/2007" in r["pourquoi"]
    assert cite_bien("DG B-8", "a décidé de soumettre les clôtures à déclaration préalable par délibération du 21/09/2007")


@pytest.mark.parametrize("projet", ["autre", "aucun", None], ids=["autre", "aucun", "sans projet"])
def test_sans_projet_de_travaux_il_n_y_a_pas_de_demarche(projet):
    assert demarche(projet, 30) == {"type": "sans objet", "pourquoi": "question sans projet de travaux", "textes": [], "delai": None}


# ------------------------------------------------------------------------------------------------ jamais plus léger
@pytest.mark.parametrize("projet", CHIFFRES)
def test_une_surface_plus_grande_ne_demande_jamais_une_demarche_plus_legere(projet):
    for total in (None, 120, 200):
        for zone_urbaine in (True, False):
            for protege in (False, True):
                for couverte in (False, True):
                    rangs = [RANG[demarche(projet, s, total, zone_urbaine, protege, couverte)["type"]] for s in SURFACES]
                    assert rangs == sorted(rangs), (total, zone_urbaine, protege, couverte, rangs)


@pytest.mark.parametrize("projet", PROJETS)
def test_un_site_patrimonial_ne_demande_jamais_une_demarche_plus_legere(projet):
    for s in SURFACES:
        for total in (None, 200):
            for zone_urbaine in (True, False):
                for couverte in (False, True):
                    for clotures_declarees in (True, False):
                        options = dict(surface=s, surface_totale_apres=total, zone_urbaine=zone_urbaine, couverte=couverte,
                                       clotures_declarees=clotures_declarees)
                        hors = RANG[demarche(projet, protege=False, **options)["type"]]
                        dans = RANG[demarche(projet, protege=True, **options)["type"]]
                        assert dans >= hors, options


@pytest.mark.parametrize("projet", PROJETS)
def test_une_zone_non_urbaine_ne_demande_jamais_une_demarche_plus_legere(projet):
    for s in SURFACES:
        for total in (None, 200):
            for protege in (False, True):
                options = dict(surface=s, surface_totale_apres=total, protege=protege)
                urbaine = RANG[demarche(projet, zone_urbaine=True, **options)["type"]]
                naturelle = RANG[demarche(projet, zone_urbaine=False, **options)["type"]]
                assert naturelle >= urbaine, options


# ------------------------------------------------------------------------------------------------ pourquoi, textes, délais
OPTIONS = [dict(surface=s, surface_totale_apres=t, zone_urbaine=u, protege=p, couverte=c, clotures_declarees=d)
           for s in (None, 3, 5, 10, 20, 40, 100, 160) for t in (None, 150, 200) for u in (True, False)
           for p in (False, True) for c in (False, True) for d in (True, False)]


@pytest.mark.parametrize("projet", PROJETS)
def test_chaque_demarche_dit_pourquoi_et_renvoie_au_texte(projet):
    for options in OPTIONS:
        r = demarche(projet, **options)
        assert r["type"] in RANG or r["type"].startswith("dépend de la surface"), (options, r)
        assert r["pourquoi"].strip(), (options, r)
        assert r["textes"], (options, r)
        assert all(t["url"] == LEGIFRANCE[t["texte"]] for t in r["textes"]), (options, r)


@pytest.mark.parametrize("projet", PROJETS)
def test_chaque_demarche_porte_le_delai_de_sa_propre_demarche(projet):
    """Une démarche et son délai ne peuvent pas se contredire : le délai est celui du type rendu, site protégé compris."""
    for options in OPTIONS:
        r = demarche(projet, **options)
        assert r["delai"] == delai(r["type"], options["protege"]), (options, r)
        assert (r["delai"] is None) == (r["type"] == RIEN), (options, r)


ABF_PC = "2 mois en principe, davantage en site patrimonial (avis de l'ABF)"
DELAIS = [(DP, False, "1 mois"), (DP, True, "2 mois (1 mois, plus 1 pour l'avis de l'ABF en site patrimonial)"),
          (PC, False, "2 mois en principe"), (PC, True, ABF_PC),
          (PC_ARCHITECTE, False, "2 mois en principe"), (PC_ARCHITECTE, True, ABF_PC),
          (RIEN, False, None), (RIEN, True, None), ("sans objet", False, None)]


@pytest.mark.parametrize("type_, protege, attendu", DELAIS, ids=[f"{t}{' en site patrimonial' if p else ''}" for t, p, _ in DELAIS])
def test_le_delai_d_instruction_suit_la_demarche(type_, protege, attendu):
    assert delai(type_, protege) == attendu


@pytest.mark.parametrize("type_", ["dépend de la surface", "dépend de la surface du bassin", "dépend de la surface créée"])
@pytest.mark.parametrize("protege, attendu", [
    (False, "1 mois pour une déclaration préalable ; 2 mois en principe pour un permis"),
    (True, "2 mois (1 mois, plus 1 pour l'avis de l'ABF en site patrimonial) pour une déclaration préalable ; "
           f"{ABF_PC} pour un permis"),
], ids=["hors site protégé", "en site patrimonial"])
def test_quand_la_demarche_depend_de_la_surface_les_deux_delais_sont_donnes(type_, protege, attendu):
    """Sans ces délais dans le contexte, l'agent en inventait (« trois mois », V14)."""
    assert delai(type_, protege) == attendu



@pytest.mark.parametrize("texte", sorted(LEGIFRANCE))
def test_chaque_article_cite_renvoie_au_texte_sur_legifrance(texte):
    assert LEGIFRANCE[texte].startswith("https://www.legifrance.gouv.fr/")


@pytest.mark.parametrize("surface, total, attendu", [(12.5, None, "12,5 m² créés"), (30, 152.5, "152,5 m² après travaux")],
                         ids=["surface créée", "surface après travaux"])
def test_une_surface_decimale_s_ecrit_avec_une_virgule(surface, total, attendu):
    assert attendu in demarche("extension", surface, total)["pourquoi"]
