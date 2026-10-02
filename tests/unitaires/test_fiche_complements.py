"""Compléments à la fiche (fiche.py) : les points à vérifier proposés par le modèle s'ajoutent à ceux du moteur de décision, sans
doublon ni point vide, coupés à un mot vers 160 caractères, cinq au plus : la liste reste lisible d'un regard."""
import pytest

from orbi.domaine.decision import decider
from orbi.domaine.fiche import composer

DISTANCE = "la distance de l'abri à la limite"
REGLE = {"id": "R1", "nature": "limite", "vaut_ici": "oui", "statut": "inconnue", "decisif": False, "fait_manquant": DISTANCE,
         "article": "UD 7", "exigence": "sur la limite ou à 3 m au moins", "constat": "", "page": 69,
         "citation": "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."}
LONG = "la hauteur de l'abri au droit de la limite séparative, " * 4  # 220 caractères


def a_verifier(*du_modele):
    """Les points à vérifier de la fiche d'un abri « oui sous conditions » (la distance reste à prévoir)."""
    regles = [dict(REGLE)]
    return composer(decider(regles), regles, None, a_verifier_modele=du_modele)["a_verifier"]


def test_les_points_du_modele_s_ajoutent_apres_ceux_du_moteur():
    assert a_verifier("la hauteur de l'abri") == [DISTANCE, "la hauteur de l'abri"]


def test_un_point_deja_present_ou_vide_n_est_pas_repete():
    assert a_verifier(DISTANCE, "", None, "la hauteur de l'abri", "la hauteur de l'abri") == [DISTANCE, "la hauteur de l'abri"]


def test_cinq_points_a_verifier_au_plus():
    assert a_verifier(*(f"point {i}" for i in range(10))) == [DISTANCE, "point 0", "point 1", "point 2", "point 3"]


def test_un_point_trop_long_est_coupe_a_un_mot():
    point = a_verifier(LONG)[1]
    assert len(point) <= 161 and point.endswith("limite…")


def test_un_long_point_donne_deux_fois_n_apparait_qu_une_fois():
    assert len(a_verifier(LONG, LONG)) == 2
