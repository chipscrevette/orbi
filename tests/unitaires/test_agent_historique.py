"""L'agent historique : ses garde-fous (ce que le code refuse dans une réponse rédigée par le modèle), la forme des références,
les chiffres inventés, et le chemin de rédaction avec sa correction unique."""
import pytest

from orbi.agent import historique
from orbi.agent.historique import Agent, chiffres_inventes, ref_norme, schema_reponse
from orbi.modele import cerveau
from tests.faux import FausseRecherche, FauxCerveau, faits, tri

PHRASE_UD7 = "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."
PASSAGES = [{"ref": "UD 7", "pages": [69, 69], "texte": PHRASE_UD7}]


@pytest.fixture(autouse=True)
def isolement(monkeypatch):
    monkeypatch.setenv("PLU_SANS_TRACE", "1")
    monkeypatch.setattr(historique, "Recherche", FausseRecherche)


@pytest.fixture
def agent():
    a = Agent()
    a.t0, a.trace = 0, []
    return a


def rep(**autres):
    base = {"verdict_type": "non", "zone": "UD", "reponse": "Non, ce projet n'est pas possible.",
            "regles": [{"article": "UD 7", "citation": PHRASE_UD7}], "a_verifier": []}
    base.update(autres)
    return base


# ------------------------------------------------------------------------------------------------ la forme des références
@pytest.mark.parametrize("brute, attendue", [
    ("UD7", "UD 7"), ("Article UD 7", "UD 7"), ("UD 11 2°)", "UD 11"), ("UDa 7", "UD 7"), ("DG B5", "DG B-5"),
    ("l'article UA 10", "UA 10"), ("P.L.U. DE BIARRITZ, article DG B-5", "DG B-5"), ("Ncu 2", "Ncu 2"), ("rien", "rien"),
], ids=lambda x: str(x))
def test_une_reference_est_ramenee_a_la_forme_du_reglement(brute, attendue):
    assert ref_norme(brute) == attendue


# ------------------------------------------------------------------------------------------------ les chiffres inventés
def test_un_chiffre_absent_du_contexte_est_signale():
    fautes = chiffres_inventes("L'emprise est de 108 m².", "emprise au sol maximale : 85.5 m²")
    assert fautes and "108" in fautes[0]


def test_un_chiffre_du_contexte_passe():
    assert chiffres_inventes("Au plus 85,5 m².", "emprise maximale 85.5 m²") == []


def test_un_delai_ecrit_en_lettres_doit_venir_de_la_demarche():
    assert chiffres_inventes("Comptez trois mois.", "délai d'instruction : 1 mois")
    assert chiffres_inventes("Comptez trois mois.", "délai d'instruction : 3 mois") == []


# ------------------------------------------------------------------------------------------------ les garde-fous
def test_pas_de_reponse_est_une_faute(agent):
    assert agent.garde_fous(None, "UD", PASSAGES, "") == ["réponse illisible (pas de JSON)"]


def test_une_reponse_conforme_passe(agent):
    assert agent.garde_fous(rep(), "UD", PASSAGES, PHRASE_UD7) == []


@pytest.mark.parametrize("modif, motif", [
    ({"zone": "UC"}, "la zone doit être"),
    ({"regles": [{"article": "UD 9", "citation": "une phrase"}]}, "ne fait pas partie des articles fournis"),
    ({"regles": [{"article": "UD 7", "citation": "Les constructions doivent être à 10 mètres."}]}, "n'existe pas mot pour mot"),
    ({"reponse": "Non, tu ne peux pas poser ton abri."}, "tutoie"),
    ({"verdict_type": "oui", "reponse": "Oui. L'abri est interdit par l'article UD 7."}, "mets-les d'accord"),
    ({"verdict_type": "non", "reponse": "Oui, vous pouvez."}, "commence par « Oui »"),
    ({"reponse": "Une. Deux. Trois. Quatre. Cinq."}, "4 au plus"),
    ({"reponse": "Non : en secteur Nh, c'est autre chose."}, "ne transpose pas"),
], ids=["zone", "article non fourni", "citation inventée", "tutoiement", "oui contre interdit", "non contre oui",
        "trop long", "autre secteur"])
def test_chaque_garde_fou_attrape_sa_faute(agent, modif, motif):
    fautes = agent.garde_fous(rep(**modif), "UD", PASSAGES, PHRASE_UD7)
    assert any(motif in f for f in fautes), fautes


# ------------------------------------------------------------------------------------------------ les citations réparées
def test_une_reference_mal_ecrite_et_une_citation_presque_exacte_sont_reparees(agent):
    r = {"regles": [{"article": "UD7", "citation": PHRASE_UD7.replace("celles-ci", "celle-ci")}]}
    agent.reparer_citations(r)
    assert r["regles"][0]["article"] == "UD 7"
    assert r["regles"][0]["citation"] == PHRASE_UD7.rstrip(".") or "celles-ci" in r["regles"][0]["citation"]


def test_un_texte_national_non_verifiable_est_retire(agent):
    r = {"regles": [{"article": "Code de l'urbanisme, article R421-9", "citation": "une phrase que le savoir métier ne contient pas"}]}
    agent.reparer_citations(r)
    assert r["regles"] == [] and r["sources_citees"] == []


def test_la_fiche_finale_dit_si_chaque_citation_est_verifiee(agent):
    res = agent.finaliser(rep(regles=[{"article": "UD 7", "citation": PHRASE_UD7}, {"article": "UD 7", "citation": "inventée"}]),
                          "UD", [], question="q")
    assert [g["verifiee"] for g in res["regles"]] == [True, False]
    assert res["regles"][0]["page"] == 69


def test_le_schema_de_reponse_impose_les_verdicts_permis():
    s = schema_reponse(["information"])
    assert s["properties"]["verdict_type"]["enum"] == ["information"]


# ------------------------------------------------------------------------------------------------ le chemin de rédaction
def test_une_faute_declenche_une_seule_correction(monkeypatch):
    """La 1re rédaction tutoie ; le code le dit au modèle, une fois ; la 2e rédaction est gardée."""
    faute = rep(verdict_type="oui sous conditions", reponse="Oui, sous conditions : ton abri doit être à 3 m.", regles=[])
    bonne = rep(verdict_type="oui sous conditions", reponse="Oui, sous conditions : votre abri doit être à 3 m.", regles=[])
    faux = FauxCerveau(tri("abri de jardin", surface=8), faute, bonne)
    monkeypatch.setattr(cerveau, "demander", faux)
    monkeypatch.setattr(historique, "outils_faits", lambda adresse, question, parcelle=None: faits(zone="UD"))
    res = Agent().repondre("Je veux un abri de jardin de 8 m² au 5 impasse Monnier à Biarritz.")
    assert len(faux.appels) == 3, "le tri, la rédaction, une correction"
    assert "Vérification automatique" in faux.appels[2]["utilisateur"]
    assert "votre abri" in res["reponse"] and not res["garde_fous"]


def test_sans_adresse_une_explication_repond_avec_les_dispositions_generales(monkeypatch):
    explication = {"verdict_type": "information", "zone": "", "reponse": "L'emprise au sol est la projection verticale du bâtiment.",
                   "regles": [], "a_verifier": []}
    faux = FauxCerveau(tri("aucun", adresse=None, sujet="explication"), explication)
    monkeypatch.setattr(cerveau, "demander", faux)
    monkeypatch.setattr(historique, "outils_faits", lambda adresse, question, parcelle=None: None)
    res = Agent().repondre("Qu'est-ce que l'emprise au sol ?")
    assert res["verdict_type"] == "information"
    assert "aucune adresse donnée" in faux.appels[1]["utilisateur"]
