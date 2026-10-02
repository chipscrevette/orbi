"""Les exclusions expresses du règlement (exclusions.py), appliquées par le code plutôt que laissées au modèle (V01, V03, V04 : il
citait l'exclusion, puis comptait quand même la piscine). Ce que le module garantit :
  · pour une piscine, chaque article lu qui écrit « Les piscines, spas et jacuzzis sont exclus de cette règle » est rendu, pour que
    le contrôle écarte ses règles : les articles 6, 7 et 8 (implantations) des zones UA, UB, UC, UD, UG, UH, UY, N et Ncu ; aucun
    autre (ni l'emprise, ni la hauteur, ni l'aspect) ;
  · l'exclusion se lit dans l'article entier, pas dans le morceau que la recherche a remonté ;
  · aucun autre projet n'est exclu ;
  · une piscine non couverte ne compte pas dans l'emprise au sol (DG B-5) ; couverte, si."""
import pytest

from orbi.domaine.exclusions import PHRASE_EMPRISE, articles_excluant, emprise_exclue
from orbi.reglement.donnees import article, cite_bien, propre

ZONES_EXCLUANTES = ("UA", "UB", "UC", "UD", "UG", "UH", "UY", "N", "Ncu")
EXCLUANTS = [f"{z} {n}" for z in ZONES_EXCLUANTES for n in ("6", "7", "8")]
# l'occupation du sol, l'emprise, la hauteur, l'aspect ; DG B-5 ne retire la piscine que de l'emprise (emprise_exclue) ; UP, Ner et
# IIAU n'écrivent pas l'exclusion dans leurs articles d'implantation (IIAU 7 est rangé dans IIAU 6 par le découpage)
NON_EXCLUANTS = ["UD 2", "UD 9", "UD 10", "UD 11", "N 2", "DG B-5", "UP 6", "UP 7", "UP 8", "Ner 7", "IIAU 6"]


def passage(ref, texte=None):
    """Un passage tel que la recherche le rend : sa référence, ses pages, son texte (ou un morceau)."""
    a = article(ref)
    return {"ref": ref, "pages": a["pages"], "texte": propre(a["texte"]) if texte is None else texte}


@pytest.mark.parametrize("ref", EXCLUANTS)
def test_une_piscine_est_exclue_des_regles_d_implantation(ref):
    assert articles_excluant("piscine", [passage(ref)]) == {ref}


@pytest.mark.parametrize("ref", NON_EXCLUANTS)
def test_les_autres_articles_s_appliquent_a_la_piscine(ref):
    assert articles_excluant("piscine", [passage(ref)]) == set()


def test_parmi_les_passages_lus_seuls_les_articles_excluants_sont_rendus():
    lus = [passage(r) for r in ("UD 2", "UD 6", "UD 7", "UD 9", "UD 10", "UD 11", "DG B-5")]
    assert articles_excluant("piscine", lus) == {"UD 6", "UD 7"}


def test_l_exclusion_se_lit_dans_l_article_entier_pas_dans_le_morceau_lu():
    """La recherche coupe les longs articles ; la phrase d'exclusion est en tête : le morceau remonté peut ne pas la contenir."""
    morceau = propre(article("UD 7")["texte"])[-400:]
    assert "exclus" not in morceau
    assert articles_excluant("piscine", [passage("UD 7", morceau)]) == {"UD 7"}


@pytest.mark.parametrize("projet", ["abri de jardin", "extension", "véranda", "surélévation", "maison neuve", "clôture", "autre", None])
def test_seule_la_piscine_est_exclue(projet):
    assert articles_excluant(projet, [passage("UD 6"), passage("UD 7"), passage("UD 8")]) == set()


def test_sans_passage_lu_rien_n_est_exclu():
    assert articles_excluant("piscine", []) == set()


@pytest.mark.parametrize("ref", [f"{z} 7" for z in ("UA", "UB", "UC", "UD", "UG", "UH")])
def test_la_phrase_d_exclusion_des_articles_7_existe_mot_pour_mot(ref):
    """La docstring du module s'appuie sur cette phrase : si une modification du PLU la retire, l'exclusion doit tomber avec elle."""
    assert cite_bien(ref, "Les piscines, spas et jacuzzis sont exclus de cette règle")


EMPRISE = [("piscine", False, True), ("piscine", True, False), ("abri de jardin", False, False), ("extension", False, False),
           ("véranda", False, False), ("maison neuve", False, False)]


@pytest.mark.parametrize("projet, couverte, attendu", EMPRISE,
                         ids=["piscine non couverte : hors emprise", "piscine couverte : dans l'emprise", "abri de jardin",
                              "extension", "véranda", "maison neuve"])
def test_seule_une_piscine_non_couverte_sort_de_l_emprise_au_sol(projet, couverte, attendu):
    assert emprise_exclue(projet, couverte) is attendu


def test_la_phrase_de_dg_b5_qui_fonde_l_exclusion_d_emprise_existe_mot_pour_mot():
    assert cite_bien("DG B-5", PHRASE_EMPRISE)
