"""La fiche du terrain : une question sans projet (« que faut-il savoir sur cette adresse ? ») ne reçoit pas de verdict,
mais ce que le PLU fixe sur le terrain, avec une phrase exacte du règlement par thème. Le règlement est le vrai
(donnees/articles.json) ; le modèle et les outils réseau sont remplacés."""
import pytest

from orbi.agent import grille, historique
from orbi.domaine import terrain
from orbi.modele import cerveau
from orbi.reglement.donnees import cite_bien
from tests.faux import FausseRecherche, FauxCerveau, faits, tri


# ------------------------------------------------------------------------------------------------ les pièces
@pytest.mark.parametrize("texte, attendu", [
    ("Le titre de l'article. Les constructions sont implantées à 4 m au moins de la limite. Autre phrase.",
     "Les constructions sont implantées à 4 m au moins de la limite."),
    ("Une phrase sans chiffre. Une autre sans chiffre.", "Une phrase sans chiffre."),
    ("", ""),
], ids=["la phrase qui porte un chiffre", "sinon la première", "vide"])
def test_l_extrait_est_la_phrase_qui_porte_la_regle(texte, attendu):
    assert terrain.extrait(texte) == attendu


def test_un_extrait_trop_long_est_coupe_a_un_mot_pres_sans_etre_reecrit():
    phrase = "La hauteur des constructions est limitée à 9 m " + "et cette phrase continue encore " * 20 + "."
    e = terrain.extrait(phrase, longueur=80)
    assert e.endswith("…") and len(e) <= 81 and phrase.startswith(e[:-1])


def test_le_texte_dit_ou_est_le_terrain_et_invite_a_donner_un_projet():
    t = terrain.composer(faits(zone="UH", surface=10683, spr=True), "UH", ["emprise au sol maximale : 50 %"], 4)
    assert t.startswith("Pas de projet précis : voici ce que le PLU fixe pour la parcelle AB 0001 (10 683 m²), en zone UH.")
    assert "Architecte des Bâtiments de France" in t and "Emprise au sol maximale : 50 %." in t
    assert t.endswith("je vérifie s'il passe.")
    assert "—" not in t


def test_les_servitudes_et_prescriptions_sont_a_retenir():
    f = faits(spr=True, prescriptions=["Espace boisé classé"], hauteurs=("R+2",))
    assert terrain.a_retenir(f) == ["servitude : Site patrimonial remarquable de Biarritz", "prescription : Espace boisé classé",
                                    "hauteur fixée au plan : niveau « R+2 »"]


# ------------------------------------------------------------------------------------------------ de bout en bout
@pytest.fixture
def agent(monkeypatch):
    monkeypatch.setenv("PLU_SANS_TRACE", "1")
    monkeypatch.setattr(historique, "Recherche", FausseRecherche)

    def fabriquer(zone, *reponses, **k):
        faux = FauxCerveau(*reponses)
        monkeypatch.setattr(cerveau, "demander", faux)
        monkeypatch.setattr(historique, "outils_faits", lambda adresse, question, parcelle=None: faits(zone=zone, **k))
        return grille.AgentGrille(), faux
    return fabriquer


def test_sans_projet_la_reponse_est_la_fiche_du_terrain_pas_un_verdict(agent):
    """Le cas réel du 3 octobre : « Avenue Temerland, que faut-il savoir ? » recevait un « Non »."""
    a, faux = agent("UH", tri("aucun", adresse="Avenue Temerland, Biarritz", sujet="autre"), surface=10683, spr=True)
    res = a.repondre("Au Avenue Temerland 64200 Biarritz, que y a-t-il à savoir ?")
    assert res["verdict_type"] == "information" and res["par"] == "code"
    assert len(faux.appels) == 1, "seul le tri appelle le modèle"
    articles = [r["article"] for r in res["regles"]]
    assert "UH 9" in articles and "UH 10" in articles
    assert all(cite_bien(r["article"], r["citation"].rstrip("…")) for r in res["regles"]), "chaque phrase est mot pour mot"
    assert "50%" in next(r["citation"] for r in res["regles"] if r["article"] == "UH 9")
    assert "site patrimonial" in " ".join(res["a_verifier"]).lower()


def test_l_emprise_maximale_est_calculee_par_le_code_quand_la_zone_la_fixe(agent):
    a, _ = agent("UD", tri("aucun", sujet="autre"), surface=610)
    res = a.repondre("Au 5 impasse Monnier à Biarritz, que faut-il savoir ?")
    assert "50 % de 610 m², soit 305 m²" in res["reponse"]


def test_un_projet_garde_son_verdict(agent):
    a, _ = agent("Ncu", tri("maison neuve"))
    assert a.repondre("Puis-je construire une maison neuve au 5 impasse Monnier à Biarritz ?")["verdict_type"] == "non"
