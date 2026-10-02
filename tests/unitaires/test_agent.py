"""L'agent entier, du tri à la fiche, avec un faux modèle : on vérifie le chemin que prend chaque question et ce que le code
garantit, quoi que le modèle écrive (un statut faux recalculé, une limite recopiée refusée, un verrou qui décide seul)."""
import pytest

from orbi.agent import grille, historique
from orbi.modele import cerveau
from tests.faux import FausseRecherche, FauxCerveau, faits, ligne, tri

PHRASE_UD7 = "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."


@pytest.fixture(autouse=True)
def isolement(monkeypatch):
    """Ni trace écrite sur disque, ni recherche par embeddings, ni outil réseau."""
    monkeypatch.setenv("PLU_SANS_TRACE", "1")
    monkeypatch.setattr(historique, "Recherche", FausseRecherche)


def agent_avec(monkeypatch, faits_parcelle, *reponses, classe=grille.AgentGrille):
    faux = FauxCerveau(*reponses)
    monkeypatch.setattr(cerveau, "demander", faux)
    monkeypatch.setattr(historique, "outils_faits", lambda adresse, question, parcelle=None: faits_parcelle)
    return classe(), faux


# ------------------------------------------------------------------------------------------------ le verrou de zone
def test_une_maison_neuve_en_ncu_est_refusee_par_le_code_sans_analyse(monkeypatch):
    agent, faux = agent_avec(monkeypatch, faits(zone="Ncu"), tri("maison neuve"))
    res = agent.repondre("Puis-je construire une maison neuve au 5 impasse Monnier à Biarritz ?")
    assert res["verdict_type"] == "non"
    assert res["par"] == "code"
    assert len(faux.appels) == 1, "seul le tri appelle le modèle : le verrou décide sans analyse"
    assert res["regles"][0]["article"] == "Ncu 1" and res["regles"][0]["verifiee"]


def test_une_annexe_en_zone_n_depend_de_la_date_de_la_maison(monkeypatch):
    agent, _ = agent_avec(monkeypatch, faits(zone="N"), tri("abri de jardin", surface=8))
    res = agent.repondre("Puis-je poser un abri de jardin de 8 m² au 5 impasse Monnier à Biarritz ?")
    assert res["verdict_type"] == "impossible à dire"
    assert "1995" in res["reponse"]


# ------------------------------------------------------------------------------------------------ la grille
def test_le_code_recalcule_un_statut_faux_du_modele(monkeypatch):
    """L'abri est à 0,5 m de la limite ; le modèle écrit « respectée » : le code compare 0,5 et 3 et répond non (C01)."""
    analyse = {"regles": [ligne(PHRASE_UD7, seuil=3, sens="limite_ou_au_moins", valeur=0.5, statut="respectee",
                                exigence="sur la limite ou à 3 m au moins")]}
    agent, _ = agent_avec(monkeypatch, faits(zone="UD"), tri("abri de jardin", surface=8), analyse)
    res = agent.repondre("Je veux poser un abri de jardin de 8 m² à 50 cm de la limite du voisin, au 5 impasse Monnier à Biarritz.")
    assert res["verdict_type"] == "non"
    assert res["reponse"].startswith("Non")
    assert any("recalculé" in x for x in res["grille"]["journal"])
    assert "Démarche" not in res["reponse"], "pas de démarche pour un projet interdit"


def test_une_limite_recopiee_comme_valeur_du_projet_ne_prouve_rien(monkeypatch):
    """V26 : le modèle écrit 12,5 m « respecte » 12,5 m ; la parcelle porte deux hauteurs au plan : impossible à dire."""
    analyse = {"regles": [ligne("La hauteur maximale est donnée au document graphique.", seuil=12.5, sens="au_plus", valeur=12.5)]}
    agent, _ = agent_avec(monkeypatch, faits(zone="UA", hauteurs=("3", "5")), tri("surélévation"), analyse)
    res = agent.repondre("Je veux surélever d'un étage le bâtiment du 5 impasse Monnier à Biarritz. C'est possible ?")
    assert res["verdict_type"] == "impossible à dire"
    journal = " ".join(res["grille"]["journal"])
    assert "ne vient ni de la question" in journal and "plusieurs hauteurs" in journal


def test_une_regle_respectee_et_rien_qui_manque_donne_oui(monkeypatch):
    analyse = {"regles": [ligne(PHRASE_UD7, seuil=3, sens="limite_ou_au_moins", valeur=4, statut="respectee")]}
    agent, _ = agent_avec(monkeypatch, faits(zone="UD"), tri("abri de jardin", surface=8, existante=90), analyse)
    res = agent.repondre("Abri de jardin de 8 m² à 4 m de la limite du voisin, au 5 impasse Monnier à Biarritz. Ma maison fait 90 m².")
    assert res["verdict_type"] == "oui"
    assert res["regles"] and all(r["verifiee"] for r in res["regles"])


def test_en_site_patrimonial_le_oui_devient_oui_sous_conditions(monkeypatch):
    analyse = {"regles": [ligne(PHRASE_UD7, seuil=3, sens="limite_ou_au_moins", valeur=4, statut="respectee")]}
    agent, _ = agent_avec(monkeypatch, faits(zone="UD", spr=True), tri("abri de jardin", surface=8, existante=90), analyse)
    res = agent.repondre("Abri de jardin de 8 m² à 4 m de la limite du voisin, au 5 impasse Monnier à Biarritz. Ma maison fait 90 m².")
    assert res["verdict_type"] == "oui sous conditions"
    assert any("Architecte des Bâtiments de France" in x for x in res["a_verifier"])


def test_une_analyse_illisible_ne_donne_jamais_de_verdict(monkeypatch):
    agent, faux = agent_avec(monkeypatch, faits(zone="UD"), tri("abri de jardin", surface=8), None, None)
    res = agent.repondre("Je veux poser un abri de jardin de 8 m² au 5 impasse Monnier à Biarritz.")
    assert res["verdict_type"] == "impossible à dire"
    assert "analyse illisible (pas de JSON)" in res["garde_fous"]
    assert len(faux.appels) == 3, "le tri, puis deux essais d'analyse"


def test_une_citation_inventee_ne_compte_ni_pour_ni_contre(monkeypatch):
    analyse = {"regles": [ligne("Il est interdit de construire à moins de 10 mètres de toute limite.", nature="interdit",
                                statut="violee")]}
    agent, _ = agent_avec(monkeypatch, faits(zone="UD"), tri("abri de jardin", surface=8), analyse)
    res = agent.repondre("Je veux poser un abri de jardin de 8 m² au 5 impasse Monnier à Biarritz.")
    assert res["verdict_type"] != "non", "une interdiction sans preuve ne peut pas faire dire non"
    assert res["regles"] == [], "une citation qui n'existe pas n'est jamais montrée"


# ------------------------------------------------------------------------------------------------ hors du chemin « droit »
def test_une_adresse_d_une_autre_commune_est_hors_perimetre(monkeypatch):
    agent, _ = agent_avec(monkeypatch, faits(commune="Anglet", dans_le_perimetre=False), tri("véranda", adresse="rue X, Anglet"))
    res = agent.repondre("Puis-je faire une véranda rue X à Anglet ?")
    assert res["verdict_type"] == "hors périmètre" and "Anglet" in res["reponse"]


def test_une_adresse_introuvable_est_dite_sans_deviner(monkeypatch):
    agent, _ = agent_avec(monkeypatch, {"trouvee": False}, tri("véranda"))
    res = agent.repondre("Puis-je faire une véranda au 999 rue Imaginaire à Biarritz ?")
    assert res["verdict_type"] == "impossible à dire" and "Je ne trouve pas cette adresse" in res["reponse"]


def test_sans_adresse_l_agent_la_demande(monkeypatch):
    agent, _ = agent_avec(monkeypatch, None, tri("véranda", adresse=None))
    res = agent.repondre("Puis-je faire une véranda ?")
    assert res["verdict_type"] == "impossible à dire" and "adresse exacte" in res["reponse"]


@pytest.mark.parametrize("question, sujet", [
    ("Puis-je obtenir une dérogation pour ma véranda au 5 impasse Monnier à Biarritz ?", "dérogation"),
    ("Combien de taxe d'aménagement pour ma véranda au 5 impasse Monnier à Biarritz ?", "taxe"),
], ids=["dérogation", "taxe"])
def test_les_sujets_hors_perimetre_sont_fixes_par_le_code(monkeypatch, question, sujet):
    agent, _ = agent_avec(monkeypatch, faits(zone="UD"), tri("véranda", sujet="droit"))
    res = agent.repondre(question)
    assert res["verdict_type"] == "hors périmètre"


def test_une_question_sur_le_contenu_du_plu_appelle_une_explication(monkeypatch):
    """V15 : « c'est dans le PLU ? » est une explication, même si le tri l'a rangée en « droit »."""
    redaction = {"verdict_type": "information", "zone": "UD", "reponse": "Le règlement demande des places pour les besoins nouveaux.",
                 "regles": [], "a_verifier": []}
    agent, faux = agent_avec(monkeypatch, faits(zone="UD"), tri("surélévation", sujet="droit"), redaction)
    res = agent.repondre("On me dit qu'il faut une place de parking de plus pour ma surélévation au 5 impasse Monnier : c'est dans le PLU ?")
    assert res["verdict_type"] == "information"
    assert len(faux.appels) == 2


# ------------------------------------------------------------------------------------------------ le tri corrigé par le code
@pytest.mark.parametrize("question, projet_du_modele, projet, couverte", [
    ("Puis-je couvrir ma piscine d'un abri de plus de 1,80 m ?", "autre", "piscine", True),
    ("Je veux construire une maison à étage sur mon terrain", "surélévation", "maison neuve", False),
    ("Je veux surélever ma maison existante d'un étage", "surélévation", "surélévation", False),
], ids=["abri de piscine", "maison à étage", "vraie surélévation"])
def test_le_tri_est_corrige_par_des_mots_cles(question, projet_du_modele, projet, couverte):
    agent = grille.AgentGrille.__new__(grille.AgentGrille)
    agent.trace, agent.t0 = [], 0
    t = agent.corriger_tri(question, {"projet": projet_du_modele, "piscine_couverte": False})
    assert t["projet"] == projet
    assert bool(t.get("piscine_couverte")) == couverte
