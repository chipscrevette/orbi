"""Les tests du contrôle de la grille : vrais articles du PLU de Biarritz, sans modèle. Chaque cas est une erreur que le modèle
a faite (ou pourrait faire) et que le code doit rattraper."""
import pytest

from orbi.domaine.controle import comparer, controler, derives, nombres
from orbi.reglement.donnees import article, norme, propre
from orbi.agent.grille import hauteurs_ambigues, sources_nombres

UD7 = propre(article("UD 7")["texte"])
N2 = propre(article("N 2")["texte"])
UD11 = propre(article("UD 11")["texte"])
PASSAGES = [{"ref": "UD 7", "pages": [69, 69], "texte": UD7}, {"ref": "N 2", "pages": [132, 134], "texte": N2},
            {"ref": "UD 11", "pages": [71, 75], "texte": UD11}]
PHRASE_UD7 = "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."
SRC_PROJET = nombres("un abri de 8 m² à 50 cm du mur du voisin et à 1 m de la limite du fond ; parcelle de 586 m²")
SRC_REGLE = nombres(UD7 + " " + N2 + " " + UD11)
CAS = []


def cas(nom, brute, attendu, zone="UDa", passages=PASSAGES, **options):
    CAS.append((nom, brute, attendu, zone, passages, options))


def ligne(**kw):
    base = {"passage": "A", "citation": PHRASE_UD7, "nature": "limite", "vaut_ici": "oui", "exigence": "sur la limite ou à 3 m",
            "constat": "Votre abri est à 0,5 m", "seuil": 3, "sens": "limite_ou_au_moins", "valeur_projet": 0.5,
            "statut": "violee", "decisif": False, "fait_manquant": None}
    base.update(kw)
    return base


# le modèle écrit « respectée » alors que 0,5 m < 3 m : le code recalcule (C01 du banc caché)
cas("le code recalcule un statut faux : 0,5 m pour une règle « limite ou 3 m »", ligne(statut="respectee"),
    lambda r, j: r[0]["statut"] == "violee" and any("recalculé" in x for x in j))
cas("sur la limite elle-même (distance 0, dite dans la question), la règle est respectée", ligne(valeur_projet=0, statut="violee"),
    lambda r, j: r[0]["statut"] == "respectee", zero_ok=True)
cas("une distance de 0 que la question ne dit pas est refusée", ligne(valeur_projet=0, statut="respectee"),
    lambda r, j: r[0]["statut"] == "inconnue")
cas("la conversion 50 cm → 0,5 m est acceptée", ligne(valeur_projet=0.5),
    lambda r, j: r[0]["compare_par_le_code"] and r[0]["statut"] == "violee")
cas("une valeur inventée (12 m) est refusée : plus de verdict dessus", ligne(valeur_projet=12, statut="violee"),
    lambda r, j: r[0]["statut"] == "inconnue" and r[0]["valeur_projet"] is None)
cas("un seuil inventé (7 m) est refusé", ligne(seuil=7, statut="violee"), lambda r, j: r[0]["statut"] == "inconnue")
cas("une citation inventée : la ligne ne peut plus interdire",
    ligne(citation="Il est interdit de construire à moins de 10 mètres de toute limite."),
    lambda r, j: r[0]["statut"] == "inconnue" and not r[0]["citation_ok"])
cas("une citation presque exacte est recalée sur le règlement",
    ligne(citation="Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celle-ci.", seuil=None,
          sens="aucun", valeur_projet=None, statut="violee"),
    lambda r, j: r[0]["citation_ok"] and "celles-ci" in r[0]["citation"])
cas("le modèle se trompe d'identifiant de passage : la citation décide", ligne(passage="C"),
    lambda r, j: r[0]["article"] == "UD 7" and any("identifiant" in x for x in j))
cas("un identifiant inexistant et pas de citation : ligne écartée", ligne(passage="Z", citation=""), lambda r, j: r == [])
cas("une règle de secteur Nh ne vaut pas pour une parcelle en N",
    ligne(passage="B", citation="En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire, sous condition "
                                 "d’insertion dans l’espace naturel", nature="exception", seuil=None, sens="aucun", valeur_projet=None,
          statut="respectee"),
    lambda r, j: r[0]["vaut_ici"] == "non", zone="N")
cas("la même phrase vaut pour une parcelle en Nh",
    ligne(passage="B", citation="En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire, sous condition "
                                 "d’insertion dans l’espace naturel", nature="exception", seuil=None, sens="aucun", valeur_projet=None,
          statut="respectee"),
    lambda r, j: r[0]["vaut_ici"] == "oui", zone="Nh")
cas("une phrase « sauf en secteur UDti » vaut pour UDa", ligne(citation="Dans toute la zone et tous les secteurs, sauf en secteur UDti",
                                                              seuil=None, sens="aucun", valeur_projet=None),
    lambda r, j: r == [] or r[0]["vaut_ici"] == "oui")
cas("le vocabulaire est normalisé (« Non respectée », « Inconnu », « Interdiction »)",
    ligne(statut="Non respectée", nature="Interdiction", vaut_ici="Oui", seuil=None, sens="aucun", valeur_projet=None),
    lambda r, j: r[0]["statut"] == "violee" and r[0]["nature"] == "interdit" and r[0]["vaut_ici"] == "oui")
cas("deux fois la même citation : un doublon est écarté", [ligne(), ligne()], lambda r, j: len(r) == 1 and any("doublon" in x for x in j))
cas("un chiffre sur une exception ne se compare pas (V14 : 2 m < 3 m a fait « violer » une exception)",
    ligne(nature="exception", statut="respectee"), lambda r, j: r[0]["statut"] == "respectee" and r[0]["sens"] is None)
cas("le règlement exclut les piscines de la règle de distance : le code écarte la ligne (V03)", ligne(),
    lambda r, j: r[0]["vaut_ici"] == "non" and any("exclut" in x for x in j), exclus={"UD 7"})
cas("la phrase d'exclusion elle-même reste une règle qui vaut ici",
    ligne(citation="Les piscines, spas et jacuzzis sont exclus de cette règle", nature="exception", seuil=None, sens="aucun", valeur_projet=None,
          statut="respectee"),
    lambda r, j: r[0]["vaut_ici"] == "oui", exclus={"UD 7"})
cas("une ligne sans preuve ne réclame rien à vérifier", ligne(citation="Une phrase qui n'existe pas dans le règlement de Biarritz.",
                                                              exigence="une règle inventée", statut="inconnue", seuil=None, sens="aucun",
                                                              valeur_projet=None),
    lambda r, j: r[0]["fait_manquant"] is None and not r[0]["citation_ok"])


cas("une piscine non couverte ne compte pas dans l'emprise : la règle d'emprise est écartée (V04)",
    ligne(passage="B", citation="L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa, UDa* et UDb", exigence="emprise au sol maximale",
          seuil=85.5, sens="au_plus", valeur_projet=8, statut="violee"),
    lambda r, j: r[0]["vaut_ici"] == "non", emprise_exclue=True, passages=[PASSAGES[0], {"ref": "UD 9", "pages": [70, 70], "texte": propre(article("UD 9")["texte"])}])
cas("« 25 % » écrit 0,25 n'est pas un seuil sourcé : la comparaison est refusée (V04)",
    ligne(passage="B", citation="L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa, UDa* et UDb", seuil=0.25, sens="au_plus",
          valeur_projet=8, statut="violee"),
    lambda r, j: r[0]["statut"] == "inconnue", passages=[PASSAGES[0], {"ref": "UD 9", "pages": [70, 70], "texte": propre(article("UD 9")["texte"])}])


cas("le fait qui manque est « la hauteur actuelle » : un fait déjà fixé, il décide (V14, V26)",
    ligne(statut="inconnue", seuil=None, sens="aucun", valeur_projet=None, fait_manquant="la hauteur actuelle du bâtiment"),
    lambda r, j: r[0]["decisif"] and any("déjà fixé" in x for x in j))
cas("« la distance de l'abri à la limite » reste un choix de conception : elle ne décide pas",
    ligne(statut="inconnue", seuil=None, sens="aucun", valeur_projet=None, fait_manquant="la distance de l'abri à la limite"),
    lambda r, j: not r[0]["decisif"])
cas("surélévation : la distance du bâtiment à la limite est déjà fixée (V26)",
    ligne(statut="inconnue", seuil=None, sens="aucun", valeur_projet=None,
          fait_manquant="la distance horizontale entre le bâtiment et la limite séparative arrière"),
    lambda r, j: r[0]["decisif"], travaux_existant=True)
cas("hors surélévation, la même phrase ne décide pas (on choisit où étendre)",
    ligne(statut="inconnue", seuil=None, sens="aucun", valeur_projet=None,
          fait_manquant="la distance horizontale entre le bâtiment et la limite séparative arrière"),
    lambda r, j: not r[0]["decisif"])
cas("une condition d'aspect qui nomme le bâtiment ne décide pas, même en surélévation",
    ligne(nature="condition", statut="inconnue", seuil=None, sens="aucun", valeur_projet=None,
          fait_manquant="l'harmonie de la surélévation avec le bâtiment"),
    lambda r, j: not r[0]["decisif"], travaux_existant=True)
cas("la date de la maison (avant mars 1995) est un fait déjà fixé",
    ligne(statut="inconnue", seuil=None, sens="aucun", valeur_projet=None, fait_manquant="si la maison existait avant mars 1995"),
    lambda r, j: r[0]["decisif"])

cas("l'emprise des constructions déjà présentes s'ajoute : une somme à vérifier, elle ne décide pas (V07)",
    ligne(nature="condition", statut="inconnue", manque="existant", seuil=None, sens="aucun", valeur_projet=None,
          fait_manquant="la surface au sol des constructions déjà présentes sur la parcelle"),
    lambda r, j: not r[0]["decisif"] and any("s'ajoute" in x for x in j))
cas("la surface de plancher d'avant 1995 reste un fait qui décide",
    ligne(nature="condition", statut="inconnue", manque="existant", seuil=None, sens="aucun", valeur_projet=None,
          fait_manquant="la surface de plancher de la maison avant mars 1995"),
    lambda r, j: r[0]["decisif"])

SRC_HAUTEUR = nombres("9 m à l'égout, un étage de 3 m")
cas("surélévation : la distance des murs existants (2 m < 3 m) n'est pas une violation du projet (V14)",
    ligne(valeur_projet=2, seuil=3, sens="au_moins", statut="violee"),
    lambda r, j: r[0]["vaut_ici"] == "incertain" and any("ne modifie pas" in x for x in j), travaux_existant=True,
    src_projet=nombres("mes murs sont à 2 m de la limite, je rehausse le toit de 60 cm"))
cas("hors surélévation, la même distance trop courte reste une violation",
    ligne(valeur_projet=2, seuil=3, sens="au_moins", statut="violee"),
    lambda r, j: r[0]["vaut_ici"] == "oui" and r[0]["statut"] == "violee",
    src_projet=nombres("mes murs sont à 2 m de la limite, je rehausse le toit de 60 cm"))
cas("surélévation : un plafond de hauteur dépassé reste une violation",
    ligne(citation="en zone UD et en secteur UDb : R + 2 + Comble (3 niveaux + combles) et 9 m à l'acrotère ou égout du toit",
          exigence="9 m à l'égout du toit au plus", seuil=9, sens="au_plus", valeur_projet=12, statut="violee", passage="C"),
    lambda r, j: r[0]["vaut_ici"] == "oui" and r[0]["statut"] == "violee", travaux_existant=True,
    src_projet=SRC_HAUTEUR | derives(SRC_HAUTEUR),
    passages=[PASSAGES[0], PASSAGES[1], {"ref": "UD 10", "pages": [70, 71], "texte": propre(article("UD 10")["texte"])}])


BASE = ("Question : Je veux surélever le bâtiment du 2 rue de la Bergerie.\n\nPROJET (lu dans la question) : surélévation\n\n"
        "FAITS (outils publics) :\n- parcelle : AB 0433, 3470 m²\n\nDÉMARCHE (calculée) : dépend ; délai d'instruction : 1 mois\n")
CHIFFRES = ["hauteur fixée au plan pour cette parcelle : niveau « 3 » = 12,50 m à l'égout", "emprise au sol maximale en UD : 50 % de 3470 m² = 1735 m²",
            "surface de la maison après travaux : 90 + 8 = 98 m²"]
FAITS = {"parcelle": {"parcelle": "AB 0433", "surface_m2": 3470}}
QUESTION = "Ma maison fait 90 m² d'emprise ; j'ajoute un abri de 8 m² à 4 m de la limite, au 2 rue de la Bergerie."


def sources_ok():
    """Les limites de la règle ne passent pas pour des chiffres du projet ; les sommes de la question, si."""
    projet, regle = sources_nombres(QUESTION, BASE, CHIFFRES, [{"texte": "hauteur de 12,50 m à l'égout, 3 mètres de la limite"}], FAITS)
    return (12.5 not in projet and 1735.0 not in projet and 1.0 not in projet  # la hauteur au plan, l'emprise maximale, « 1 mois »
            and 12.5 in regle and 1735.0 in regle and 3.0 in regle
            and 98.0 in projet and 3470.0 in projet and 4.0 in projet)  # la somme 90 + 8, la parcelle, la question


def hauteurs_ok():
    """Deux hauteurs au plan et une surélévation sans dimension : un fait décisif ajouté par le code ; dans les autres cas, rien."""
    deux = {"contraintes": {"hauteurs_au_plan": ["3", "5"]}}
    une = {"contraintes": {"hauteurs_au_plan": ["3"]}}
    q = "Je veux surélever d'un étage le bâtiment du 2 rue de la Bergerie. C'est possible ?"
    ligne_code = hauteurs_ambigues("surélévation", q, deux, "UA", [])
    return (ligne_code is not None and ligne_code["decisif"] and ligne_code["article"] == "UA 10" and "« 3 » et « 5 »" in ligne_code["fait_manquant"]
            and hauteurs_ambigues("surélévation", q, une, "UA", []) is None  # une seule hauteur : pas d'ambiguïté
            and hauteurs_ambigues("surélévation", q + " Je monte de 3 m.", deux, "UA", []) is None  # la question donne une dimension
            and hauteurs_ambigues("extension", q, deux, "UA", []) is None  # une extension n'a pas de hauteur à choisir ici
            and hauteurs_ambigues("surélévation", q, deux, "UD", []) is None)  # UD 10 ne renvoie pas au plan


def nombres_ok():
    return (nombres("1.000 m² et 1 000 m² et 12,50 m") >= {1000.0, 12.5}) and (nombres("0,60 m") == {0.6})


@pytest.mark.parametrize("nom, brute, attendu, zone, passages, options", CAS, ids=[c[0] for c in CAS])
def test_le_controle_rattrape(nom, brute, attendu, zone, passages, options):
    options = dict(options)
    src_projet = options.pop("src_projet", SRC_PROJET)
    regles, journal = controler(brute if isinstance(brute, list) else [brute], passages, zone, src_projet, SRC_REGLE, **options)
    assert attendu(regles, journal), (regles, journal)


def test_dg_b5_ne_compte_pas_les_piscines_non_couvertes():
    texte = norme(propre(article("DG B-5")["texte"])).replace("’", "'")
    assert "piscines non couvertes, tennis ne sont pas comprises dans l'emprise au sol" in texte


def test_ud7_exclut_les_piscines():
    assert "sont exclus de cette règle" in norme(propre(article("UD 7")["texte"]))


@pytest.mark.parametrize("valeur, seuil, sens, attendu", [
    (0.5, 3, "limite_ou_au_moins", "violee"), (0, 3, "limite_ou_au_moins", "respectee"),
    (3, 3, "au_moins", "respectee"), (1.8, 1.5, "au_plus", "violee"), (1.5, 1.5, "au_plus", "respectee"),
])
def test_comparer(valeur, seuil, sens, attendu):
    assert comparer(valeur, seuil, sens) == attendu


def test_nombres():
    assert nombres_ok()


def test_sources_des_chiffres():
    assert sources_ok()


def test_hauteurs_ambigues():
    assert hauteurs_ok()
