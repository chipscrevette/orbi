"""Compléments au contrôle de la grille (controle.py), sans modèle : ce que le module garantit au-delà de test_controle.py.
  · une lettre de passage et son rang se correspondent dans les deux sens (A ↔ 1, AA ↔ 27), et « 3 » ou « P3 » désigne le 3e passage ;
  · un nombre écrit avec plusieurs points de milliers est lu en entier (« 1.000.000 m² ») ;
  · sans sens connu (au plus, au moins, limite ou au moins), le code ne juge pas un chiffre ;
  · la grille garde 8 règles au plus, prises dans les 12 premières lignes du modèle ;
  · de bout en bout (normaliser, contrôler, décider), une violation reste une violation et une ligne garde son passage."""
import pytest

from orbi.domaine.controle import MAX_REGLES, comparer, controler, indice_passage, lettre, nombres
from orbi.domaine.decision import decider
from orbi.reglement.donnees import article, propre

UD7 = {"ref": "UD 7", "pages": [69, 69], "texte": propre(article("UD 7")["texte"])}
UD11 = {"ref": "UD 11", "pages": [71, 75], "texte": propre(article("UD 11")["texte"])}
PHRASE_UD7 = "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."


# ------------------------------------------------------------------------------------------------ passages
RANGS = [("A", 1), ("c", 3), ("Z", 26), ("AA", 27), ("AZ", 52), ("3", 3), ("P3", 3), ("p12", 12), (" 7 ", 7), ("", 0), (None, 0),
         ("A1", 0)]


@pytest.mark.parametrize("pid, rang", RANGS,
                         ids=[f"« {p} » → {r}" if p is not None else "rien → 0" for p, r in RANGS])
def test_un_identifiant_de_passage_donne_son_rang(pid, rang):
    """0 ne désigne aucun passage : c'est alors la citation qui retrouve le bon (« A1 » mêle lettre et chiffre)."""
    assert indice_passage(pid) == rang


LETTRES = [(0, ""), (1, "A"), (26, "Z"), (27, "AA"), (52, "AZ"), (53, "BA"), (702, "ZZ"), (703, "AAA")]


@pytest.mark.parametrize("rang, attendu", LETTRES, ids=[f"{r} → « {a} »" for r, a in LETTRES])
def test_un_rang_donne_sa_lettre(rang, attendu):
    assert lettre(rang) == attendu


def test_lettre_et_rang_se_correspondent_dans_les_deux_sens():
    """Les passages sont donnés au modèle sous une lettre et relus par leur rang : l'aller-retour ne perd aucun passage."""
    assert [indice_passage(lettre(i)) for i in range(1, 1000)] == list(range(1, 1000))


# ------------------------------------------------------------------------------------------------ nombres, comparaison
def test_un_nombre_a_plusieurs_points_de_milliers_est_lu_en_entier():
    assert nombres("une unité foncière de 1.000.000 m²") == {1000000.0}


@pytest.mark.parametrize("sens", [None, "aucun", "egal"], ids=["sans sens", "« aucun »", "sens inconnu"])
def test_sans_sens_connu_le_code_ne_juge_pas_un_chiffre(sens):
    assert comparer(2, 3, sens) is None


# ------------------------------------------------------------------------------------------------ longueur de la grille
def ligne(i):
    """Une ligne lisible mais sans citation : elle est gardée (sans preuve), jamais dédoublonnée."""
    return {"passage": "A", "citation": "", "nature": "condition", "vaut_ici": "oui", "exigence": f"exigence {i}", "constat": "",
            "statut": "inconnue"}


def test_la_grille_garde_au_plus_8_regles():
    regles, _ = controler([ligne(i) for i in range(12)], [UD7], "UDa", set(), set())
    assert MAX_REGLES == 8
    assert [r["id"] for r in regles] == [f"R{i}" for i in range(1, 9)]
    assert [r["exigence"] for r in regles] == [f"exigence {i}" for i in range(8)]


def test_au_dela_des_12_premieres_lignes_le_modele_n_est_plus_lu():
    valide = {"passage": "A", "citation": PHRASE_UD7, "nature": "limite", "vaut_ici": "oui", "exigence": "sur la limite ou à 3 m",
              "constat": "", "statut": "inconnue"}
    assert len(controler([valide], [UD7], "UDa", set(), set())[0]) == 1
    regles, journal = controler([{"passage": "Z", "citation": ""}] * 12 + [valide], [UD7], "UDa", set(), set())
    assert regles == []
    assert len(journal) == 12 and all("passage introuvable" in x for x in journal)


# ------------------------------------------------------------------------------------------------ de bout en bout
MANSART = "Les toitures dites à la Mansart sont interdites."  # UD 11 : un interdit sans chiffre, le code ne recalcule rien


@pytest.mark.parametrize("statut", [pytest.param(s, id=f"« {s} »") for s in ("Non respectée", "Non conforme", "Non-respectée",
                                                                              "ne respecte pas")])
def test_une_toiture_a_la_mansart_jugee_contraire_a_la_regle_donne_non(statut):
    brute = {"passage": "A", "citation": MANSART, "nature": "interdit", "vaut_ici": "oui", "exigence": "pas de toiture à la Mansart",
             "constat": "le projet est une toiture à la Mansart", "statut": statut}
    regles, journal = controler([brute], [UD11], "UDa", set(), set())
    assert regles[0]["citation_ok"], journal
    assert decider(regles)["verdict"] == "non"


PRESQUE = PHRASE_UD7.replace("celles-ci", "celle-ci")  # un accord « corrigé » par le modèle : seul le recalage la sauve


@pytest.mark.parametrize("pid", [pytest.param("A", id="« A »"), pytest.param("1", id="« 1 »"),
                                 pytest.param("P1", id="« P1 »")])
def test_une_citation_presque_exacte_est_recalee_quelle_que_soit_l_ecriture_du_passage(pid):
    brute = {"passage": pid, "citation": PRESQUE, "nature": "limite", "vaut_ici": "oui", "exigence": "sur la limite ou à 3 m",
             "constat": "", "statut": "inconnue"}
    regles, journal = controler([brute], [UD7], "UDa", set(), set())
    assert len(regles) == 1, journal
    assert regles[0]["citation_ok"] and regles[0]["citation"] == PHRASE_UD7
