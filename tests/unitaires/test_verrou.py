"""Le verrou de zone (verrou.py) : les projets que l'article 1 d'une zone interdit sans exception possible, décidés par le code
avant toute lecture du modèle (V29 : « la maison neuve est possible dans la zone Ncu »). Ce que le module garantit :
  · une maison neuve est verrouillée (« non ») en Ncu, Ner, UG, UY, IIAU et dans toute la zone N sauf Nh, Nh*, Nhi* et Nhd ;
  · un abri de jardin est verrouillé (« non ») en Ncu et Ner ;
  · un abri ou une piscine en zone N, hors secteurs habitables et Nf, dépend de la date de la maison (« non » ou « impossible à
    dire », N 2 b) ;
  · partout ailleurs, le verrou se tait (None) : la question reste au modèle et au moteur de décision ;
  · chaque citation du verrou existe mot pour mot dans son article, et chaque exemption s'appuie sur une phrase du règlement.
Les zones testées sont celles du plan de Biarritz (donnees/zones-biarritz.geojson)."""
import json
import os

import pytest

from orbi.chemins import DONNEES
from orbi.domaine.decision import decider
from orbi.domaine.verrou import ANNEXES_N, HABITABLES_N, INTERDIT_NEUF, verrou
from orbi.reglement.donnees import cite_bien


def _zones_du_plan():
    with open(os.path.join(DONNEES, "zones-biarritz.geojson"), encoding="utf-8") as f:
        return sorted({x["properties"]["libelle"] for x in json.load(f)["features"]})


ZONES_DU_PLAN = _zones_du_plan()


# ------------------------------------------------------------------------------------------------ maison neuve
MAISON_INTERDITE = [("Ncu", "Ncu 1"), ("Ner", "Ner 1"),
                    ("UG", "UG 1"), ("UGA", "UG 1"), ("UGai", "UG 1"), ("UGbi", "UG 1"), ("UGi", "UG 1"), ("UGi*", "UG 1"),
                    ("UGvi", "UG 1"), ("UY", "UY 1"), ("UY*", "UY 1"), ("UYi", "UY 1"), ("UYt", "UY 1"),
                    ("IIAUg", "IIAU 1"), ("IIAUy", "IIAU 1"),
                    ("N", "N 1"), ("Na", "N 1"), ("Nb", "N 1"), ("Nd", "N 1"), ("Ng", "N 1"), ("Nr", "N 1"), ("NF", "N 1")]


@pytest.mark.parametrize("zone, art", MAISON_INTERDITE, ids=[z for z, _ in MAISON_INTERDITE])
def test_une_maison_neuve_est_verrouillee(zone, art):
    v = verrou("maison neuve", zone)
    assert v is not None, f"une maison neuve en {zone} doit être verrouillée par {art}"
    assert (v["verdicts"], v["article"]) == (["non"], art)
    assert v["citation"] == INTERDIT_NEUF[art.split()[0]][1]
    assert v["pourquoi"].startswith(f"une maison neuve n'entre dans aucune exception de l'article {art} en {zone}")


@pytest.mark.parametrize("zone", ["UG", "UGi", "UGvi"])
def test_en_ug_le_pourquoi_rappelle_les_logements_de_fonction(zone):
    """UG 1 admet les logements liés à la fonction d'un équipement : le pourquoi le dit, pour qu'on ne lise pas « jamais »."""
    assert cite_bien("UG 1", "sauf pour logements liés à la fonction de l’équipement sous les conditions fixées à l’article UG 2")
    assert verrou("maison neuve", zone)["pourquoi"].endswith("(seuls des logements de fonction liés à un équipement y sont prévus)")


@pytest.mark.parametrize("zone", ["Ncu", "Ner", "UY", "IIAUg", "N"])
def test_hors_ug_le_pourquoi_ne_parle_pas_de_logements_de_fonction(zone):
    assert "logements de fonction" not in verrou("maison neuve", zone)["pourquoi"]


MAISON_OUVERTE = ["Nh", "Nh*", "Nhi*", "Nhd", "UA", "UAc", "UB", "UBa", "UC", "UC*", "UD", "UDa", "UDti", "UH", "UP"]


@pytest.mark.parametrize("zone", MAISON_OUVERTE)
def test_une_maison_neuve_n_est_pas_verrouillee_la_ou_l_article_1_l_admet(zone):
    assert verrou("maison neuve", zone) is None


# la phrase de N 1 qui ouvre chaque secteur habitable de la zone N
HABITATION_EN_N = {
    "Nh": "En Nh, la transformation et l’extension mesurée des constructions existantes, l’aménagement ou les constructions à "
          "usage d’habitation individuelle",
    "Nh*": "En Nh* & Nhi*, l’aménagement ou les constructions à usage d’habitation individuelle",
    "Nhi*": "En Nh* & Nhi*, l’aménagement ou les constructions à usage d’habitation individuelle",
    "Nhd": "En Nhd, la transformation et l’extension mesurée des constructions existantes, l’aménagement ou la construction d’une "
           "seule habitation en maison individuelle",
}


@pytest.mark.parametrize("secteur", sorted(HABITABLES_N))
def test_chaque_secteur_habitable_de_la_zone_n_s_appuie_sur_l_article_n_1(secteur):
    assert cite_bien("N 1", HABITATION_EN_N[secteur])


def test_les_secteurs_habitables_du_code_existent_sur_le_plan():
    """Si le plan renommait un secteur, le verrou fermerait en silence un secteur où l'on peut habiter."""
    assert HABITABLES_N <= set(ZONES_DU_PLAN)


@pytest.mark.parametrize("zone", [None, "", "   "], ids=["sans zone", "zone vide", "espaces seuls"])
@pytest.mark.parametrize("projet", ["maison neuve", "abri de jardin", "piscine"])
def test_sans_zone_connue_le_verrou_se_tait(projet, zone):
    assert verrou(projet, zone) is None


def test_une_zone_entouree_d_espaces_se_lit_comme_la_zone():
    """Les espaces autour du code de zone ne doivent ni fermer un secteur habitable, ni changer le pourquoi."""
    assert verrou("maison neuve", " Nh ") is None
    assert verrou("abri de jardin", "Nhd ") is None
    assert verrou("maison neuve", " Ncu ")["pourquoi"].endswith("de l'article Ncu 1 en Ncu")


# ------------------------------------------------------------------------------------------------ abri de jardin, piscine
@pytest.mark.parametrize("zone", ["Ncu", "Ner"])
def test_un_abri_de_jardin_est_verrouille_en_ncu_et_ner(zone):
    assert verrou("abri de jardin", zone) == {
        "verdicts": ["non"], "article": f"{zone} 1", "citation": INTERDIT_NEUF[zone][1],
        "pourquoi": f"un abri de jardin est une construction nouvelle, qu'aucune exception de l'article {zone} 2 ne prévoit"}


ANNEXES_1995 = ["N", "Na", "Nb", "Nd", "Ng", "Nr"]


@pytest.mark.parametrize("projet", ["abri de jardin", "piscine"])
@pytest.mark.parametrize("zone", ANNEXES_1995)
def test_en_zone_n_une_annexe_depend_de_la_date_de_la_maison(zone, projet):
    """N 2 b) : les annexes ne sont admises que pour une construction qui existait en mars 1995 ; la question ne le dit pas."""
    v = verrou(projet, zone)
    assert v is not None
    assert v["verdicts"] == ["non", "impossible à dire"]
    assert (v["article"], v["citation"]) == ANNEXES_N
    assert "mars 1995" in v["fait_manquant"]


@pytest.mark.parametrize("projet", ["abri de jardin", "piscine"])
@pytest.mark.parametrize("zone", ["Nh", "Nh*", "Nhi*", "Nhd", "NF", "Nf"])
def test_dans_les_secteurs_habitables_et_nf_une_annexe_n_est_pas_verrouillee(zone, projet):
    assert verrou(projet, zone) is None


def test_l_exemption_des_annexes_s_appuie_sur_l_article_n_2():
    """N 2 b) écarte Nf, Nh, Nh* et Nhi* de la règle de 1995 ; en Nhd, la villa est admise avec « ses annexes »."""
    assert cite_bien("N 2", "à l'exclusion du secteur Nf, Nh, Nh* et Nhi*")
    assert cite_bien("N 2", "En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire, sous condition "
                            "d’insertion dans l’espace naturel, et de ses annexes (telles que garage, piscine, abri de jardin)")


def test_une_piscine_n_est_pas_verrouillee_en_ncu_qui_admet_une_piscine_non_couverte():
    assert cite_bien("Ncu 2", "une piscine non couverte par unité foncière")
    assert verrou("piscine", "Ncu") is None


@pytest.mark.parametrize("projet", ["abri de jardin", "piscine"])
@pytest.mark.parametrize("zone", ["UD", "UDa", "UG", "UY", "IIAUg"])
def test_hors_zone_naturelle_une_annexe_n_est_pas_verrouillee(zone, projet):
    assert verrou(projet, zone) is None


@pytest.mark.parametrize("projet", ["extension", "véranda", "surélévation", "clôture", "autre", None])
def test_les_autres_projets_restent_au_modele(projet):
    """Une extension en Ncu (« confortation de l'existant »), une clôture en N… : l'article 1 ne les ferme pas sans exception."""
    for zone in ("Ncu", "Ner", "N", "Na", "UG", "UY", "IIAUg", "UD"):
        assert verrou(projet, zone) is None, zone


@pytest.mark.xfail(strict=True, reason=(
    "Ner 1 interdit toute construction qui n'est pas justifiée par la sécurité, l'équipement sanitaire, les services publics ou la "
    "confortation de l'existant, et Ner 2 n'admet aucune piscine (Ncu 2 a, lui, admet « une piscine non couverte par unité "
    "foncière ») : par la définition même du verrou, une piscine en Ner devrait être verrouillée comme l'abri de jardin"))
def test_une_piscine_en_ner_est_verrouillee():
    v = verrou("piscine", "Ner")
    assert v is not None and (v["verdicts"], v["article"]) == (["non"], "Ner 1")


@pytest.mark.xfail(strict=True, reason=(
    "IAUy a son propre chapitre dans le règlement (p. 117 à 123 : « Sont interdits en zone IAUy : Les constructions destinées à "
    "l'habitation »), absent d'articles.json (son texte est fondu dans celui d'UY 14), et chapitre('IAUy') renvoie IIAU : le "
    "verrou dit « non » à raison, mais cite IIAU 1, un article qui ne régit pas cette zone"))
def test_une_maison_neuve_en_iauy_cite_l_article_de_sa_zone():
    v = verrou("maison neuve", "IAUy")
    assert v is not None and v["article"] == "IAUy 1"


# ------------------------------------------------------------------------------------------------ les citations, la décision
@pytest.mark.parametrize("chap", sorted(INTERDIT_NEUF))
def test_chaque_citation_d_interdiction_existe_mot_pour_mot(chap):
    assert cite_bien(*INTERDIT_NEUF[chap])


def test_la_citation_des_annexes_en_zone_n_existe_mot_pour_mot():
    assert cite_bien(*ANNEXES_N)


@pytest.mark.parametrize("projet", ["maison neuve", "abri de jardin", "piscine"])
def test_sur_toutes_les_zones_du_plan_le_verrou_cite_une_phrase_exacte(projet):
    """La phrase affichée sous un « non » du verrou est toujours celle du règlement, quelle que soit la zone du plan."""
    verrous = [(zone, v) for zone in ZONES_DU_PLAN if (v := verrou(projet, zone))]
    assert verrous
    for zone, v in verrous:
        assert cite_bien(v["article"], v["citation"]), (zone, v)


def test_le_verrou_d_une_maison_neuve_suffit_a_decider_non():
    d = decider([], verrou=verrou("maison neuve", "Ncu"))
    assert (d["verdict"], d["raison"]) == ("non", "verrou")


def test_le_verrou_des_annexes_en_zone_n_laisse_la_date_de_la_maison_decider():
    """Sans violation établie, le moteur ne conclut ni « oui » ni « non » : il demande la date de la maison."""
    d = decider([], verrou=verrou("abri de jardin", "N"))
    assert (d["verdict"], d["raison"]) == ("impossible à dire", "verrou_incertain")
