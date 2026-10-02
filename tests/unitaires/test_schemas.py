"""Le vocabulaire de la grille (schemas.py) : le modèle écrit « Respectée », « non respecté », « Interdiction »… et le code ramène
chaque ligne au vocabulaire fermé que le contrôle et la décision lisent. Ce que le module garantit :
  · normaliser() ne rend que des valeurs de l'énumération (nature, vaut_ici, statut, sens), et chaque valeur de l'énumération se
    relit à l'identique ;
  · « non respecté » est une violation, bien qu'il contienne « respect » ; « sur la limite ou à au moins 3 m » n'est pas « au moins » ;
  · une ligne illisible prend les valeurs prudentes : statut inconnu, applicabilité incertaine, rien de décisif, aucune citation ;
  · le fait qui manque fixe seul le caractère décisif : un fait sur l'existant décide, un choix du projet non ;
  · nombre() lit un chiffre écrit à la française (« 0,5 m ») et refuse ce qui n'en est pas (rien, du texte, un booléen) ;
  · sans_accent() rend un texte comparable."""
import pytest

from orbi.domaine.controle import indice_passage
from orbi.domaine.schemas import NATURES, SENS, STATUTS, VAUT, nombre, normaliser, sans_accent


def ids(cas):
    """« Non respectée » → violee : le nom lisible de chaque variante."""
    return [f"« {c[0]} » → {c[1]}" if c[0] is not None else f"rien → {c[1]}" for c in cas]


# ------------------------------------------------------------------------------------------------ statut
STATUT = [("Non respectée", "violee"), ("non respecté", "violee"), ("Violée", "violee"), ("enfreint la règle", "violee"),
          ("dépasse le plafond", "violee"), ("irrespect", "violee"),
          ("Respectée", "respectee"), ("respecté", "respectee"), ("Conforme", "respectee"),
          ("Inconnue", "inconnue"), ("incertain", "inconnue"), ("il manque la hauteur", "inconnue"), ("à vérifier", "inconnue"),
          ("on ne sait pas", "inconnue"), ("autre chose", "inconnue"), ("", "inconnue"), (None, "inconnue")]


@pytest.mark.parametrize("brut, attendu", STATUT, ids=ids(STATUT))
def test_le_statut_libre_est_ramene_au_vocabulaire(brut, attendu):
    assert normaliser({"statut": brut})["statut"] == attendu


@pytest.mark.parametrize("brut", ["Non conforme", "Non-respectée", "pas respectée", "ne respecte pas la règle"])
def test_une_violation_ecrite_autrement_reste_une_violation(brut):
    assert normaliser({"statut": brut})["statut"] == "violee"


# ------------------------------------------------------------------------------------------------ vaut_ici
VAUT_ICI = [("Oui", "oui"), ("vrai", "oui"), ("True", "oui"), ("Non", "non"), ("faux", "non"), ("false", "non"),
            ("pas ici : autre secteur", "non"), ("Incertain", "incertain"), ("Peut-être", "incertain"), ("possible", "incertain"),
            ("", "incertain"), (None, "incertain")]


@pytest.mark.parametrize("brut, attendu", VAUT_ICI, ids=ids(VAUT_ICI))
def test_l_applicabilite_libre_est_ramenee_au_vocabulaire(brut, attendu):
    assert normaliser({"vaut_ici": brut})["vaut_ici"] == attendu


@pytest.mark.parametrize("brut", ["pas sûr", "Non déterminé", "non établi"])
def test_un_doute_sur_l_applicabilite_reste_incertain(brut):
    assert normaliser({"vaut_ici": brut})["vaut_ici"] == "incertain"


def test_ne_s_applique_pas_en_fin_de_phrase_veut_dire_non():
    assert normaliser({"vaut_ici": "Ne s'applique pas"})["vaut_ici"] == "non"


# ------------------------------------------------------------------------------------------------ nature
NATURE = [("Interdiction", "interdit"), ("Prohibé", "interdit"),
          ("Exception", "exception"), ("Dérogation", "exception"), ("dispense", "exception"), ("Toutefois", "exception"),
          ("Limite", "limite"), ("limitée", "limite"), ("maximum", "limite"), ("Minimum", "limite"), ("plafond", "limite"),
          ("seuil", "limite"), ("règle chiffrée", "limite"),
          ("Information", "information"), ("Définition", "information"), ("renvoi", "information"),
          ("Condition", "condition"), ("Exigence", "condition"), ("obligation", "condition"), ("Aspect", "condition"),
          ("autre chose", "condition"), ("", "condition"), (None, "condition")]


@pytest.mark.parametrize("brut, attendu", NATURE, ids=ids(NATURE))
def test_la_nature_libre_est_ramenee_au_vocabulaire(brut, attendu):
    assert normaliser({"nature": brut})["nature"] == attendu


def test_une_exception_a_l_interdiction_reste_une_exception():
    assert normaliser({"nature": "Exception à l'interdiction"})["nature"] == "exception"


# ------------------------------------------------------------------------------------------------ sens
SENS_LIBRE = [("au_plus", "au_plus"), ("au plus", "au_plus"), ("Maximum", "au_plus"), ("au_moins", "au_moins"),
              ("au moins", "au_moins"), ("Minimum", "au_moins"), ("limite_ou_au_moins", "limite_ou_au_moins"),
              ("sur la limite ou à au moins 3 m", "limite_ou_au_moins"), ("aucun", None), ("", None), (None, None)]


@pytest.mark.parametrize("brut, attendu", SENS_LIBRE, ids=ids(SENS_LIBRE))
def test_le_sens_de_la_comparaison_est_ramene_au_vocabulaire(brut, attendu):
    """« Sur la limite ou à au moins 3 m » contient « moins » : elle doit rester « limite_ou_au_moins », où 0 m est permis."""
    assert normaliser({"sens": brut})["sens"] == attendu


@pytest.mark.parametrize("champ, valeurs", [("nature", NATURES), ("vaut_ici", VAUT), ("statut", STATUTS), ("sens", SENS)],
                         ids=["nature", "vaut_ici", "statut", "sens"])
def test_les_valeurs_de_l_enumeration_se_relisent_a_l_identique(champ, valeurs):
    for v in valeurs:
        assert normaliser({champ: v})[champ] == v


# ------------------------------------------------------------------------------------------------ passage
PASSAGE = [("C", "C", 3), ("c", "C", 3), ("Passage C", "C", 3), ("passage : b", "B", 2), ("(B)", "B", 2), ("AA", "AA", 27),
           ("Passage AB", "AB", 28), ("3", "3", 3), (3, "3", 3), ("Passage 3", "3", 3), ("", "", 0), (None, "", 0)]


@pytest.mark.parametrize("brut, attendu, rang", PASSAGE,
                         ids=[f"« {b} » → passage {r}" if b is not None else "rien → aucun passage" for b, _, r in PASSAGE])
def test_l_identifiant_de_passage_designe_le_bon_passage(brut, attendu, rang):
    p = normaliser({"passage": brut})["passage"]
    assert (p, indice_passage(p)) == (attendu, rang)


@pytest.mark.parametrize("brut", ["P3", "p3", "P 3"])
def test_un_identifiant_p3_designe_le_troisieme_passage(brut):
    assert indice_passage(normaliser({"passage": brut})["passage"]) == 3


# ------------------------------------------------------------------------------------------------ décisif, fait manquant
DECISIF = [(True, True), (False, False), (None, False), ("true", True), ("Vrai", True), ("oui", True), ("false", False),
           ("non", False), ("", False)]


@pytest.mark.parametrize("brut, attendu", DECISIF, ids=ids(DECISIF))
def test_l_ancien_champ_decisif_est_toujours_lu(brut, attendu):
    assert normaliser({"decisif": brut})["decisif"] is attendu


MANQUE = [("existant", False, True), ("déjà construit", False, True), ("l'état actuel", False, True),
          ("projet", True, False), ("conception", True, False), ("choisi par le demandeur", True, False),
          ("aucun", True, True), ("aucun", False, False), (None, True, True), (None, False, False)]


@pytest.mark.parametrize("manque, decisif, attendu", MANQUE,
                         ids=[f"« {m} », décisif écrit {d} → {a}" for m, d, a in MANQUE])
def test_le_fait_qui_manque_decide_seul_du_caractere_decisif(manque, decisif, attendu):
    """Un fait sur un bâtiment ou un terrain déjà là décide ; une donnée du projet se choisit. Sans « manque », le modèle garde la main."""
    assert normaliser({"manque": manque, "decisif": decisif})["decisif"] is attendu


FAIT = [(None, None), ("", None), ("   ", None), ("null", None), ("NULL", None), ("None", None), ("aucun", None), ("Aucun", None),
        ("  la date de la maison  ", "la date de la maison")]


@pytest.mark.parametrize("brut, attendu", FAIT, ids=ids(FAIT))
def test_un_fait_manquant_vide_ne_reclame_rien(brut, attendu):
    assert normaliser({"fait_manquant": brut})["fait_manquant"] == attendu


@pytest.mark.parametrize("brut", ["Aucune", " null "])
def test_un_fait_manquant_vide_ecrit_autrement_ne_reclame_rien(brut):
    assert normaliser({"fait_manquant": brut})["fait_manquant"] is None


# ------------------------------------------------------------------------------------------------ la ligne entière
@pytest.mark.parametrize("brute", [None, "une phrase au lieu d'un objet", [], 42], ids=["rien", "du texte", "une liste", "un nombre"])
def test_une_ligne_illisible_prend_les_valeurs_prudentes(brute):
    """Sans citation ni passage, la ligne ne peut ni interdire ni autoriser ; rien n'y est décisif."""
    assert normaliser(brute) == {"passage": "", "citation": "", "nature": "condition", "vaut_ici": "incertain", "exigence": "",
                                 "constat": "", "seuil": None, "sens": None, "valeur_projet": None, "statut": "inconnue",
                                 "decisif": False, "fait_manquant": None}


def test_les_textes_libres_sont_debarrasses_de_leurs_espaces():
    r = normaliser({"citation": "  Les piscines, spas et jacuzzis sont exclus de cette règle.  ", "exigence": None,
                    "constat": " à 0,5 m de la limite "})
    assert (r["citation"], r["exigence"], r["constat"]) == ("Les piscines, spas et jacuzzis sont exclus de cette règle.", "",
                                                            "à 0,5 m de la limite")


def test_le_seuil_et_la_valeur_du_projet_sont_lus_comme_des_nombres():
    r = normaliser({"seuil": "3 mètres", "valeur_projet": "0,5 m"})
    assert (r["seuil"], r["valeur_projet"]) == (3.0, 0.5)


# ------------------------------------------------------------------------------------------------ nombre, sans_accent
NOMBRES = [(3, 3.0), (2.5, 2.5), (0, 0.0), ("0,5 m", 0.5), ("3 mètres", 3.0), ("12,50 m", 12.5), ("-2,5", -2.5), ("25 %", 25.0)]


@pytest.mark.parametrize("brut, attendu", NOMBRES,
                         ids=["3", "2.5", "0 : sur la limite, une vraie valeur", "« 0,5 m »", "« 3 mètres »", "« 12,50 m »",
                              "« -2,5 »", "« 25 % »"])
def test_un_chiffre_ecrit_a_la_francaise_est_lu(brut, attendu):
    assert nombre(brut) == attendu


@pytest.mark.parametrize("brut", [None, True, False, "", "pas de chiffre", "aucun"],
                         ids=["rien", "True ne vaut pas 1", "False ne vaut pas 0", "texte vide", "texte sans chiffre", "« aucun »"])
def test_ce_qui_n_est_pas_un_nombre_ne_devient_pas_un_nombre(brut):
    assert nombre(brut) is None


@pytest.mark.parametrize("brut", ["1 000 m²", "1 000 m²", "1 000 m²"], ids=["espace", "espace insécable", "espace fine"])
def test_un_nombre_avec_espace_de_milliers_est_lu_en_entier(brut):
    assert nombre(brut) == 1000.0


@pytest.mark.parametrize("brut, attendu", [("Respectée", "respectee"), ("ÉVIDEMMENT", "evidemment"), ("Ça dépasse", "ca depasse"),
                                           ("déjà", "deja"), (None, ""), (12, "12")],
                         ids=["Respectée", "majuscule accentuée", "cédille", "déjà", "rien", "un nombre"])
def test_sans_accent_rend_un_texte_comparable(brut, attendu):
    assert sans_accent(brut) == attendu
