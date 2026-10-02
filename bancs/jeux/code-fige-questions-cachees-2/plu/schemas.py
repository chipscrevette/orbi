"""La grille : le vocabulaire que le modèle remplit et que le code lit.

Le modèle ne rend plus de verdict. Pour chaque règle du règlement qui touche le projet, il remplit une ligne
(SCHEMA_ANALYSE). Le code vérifie les lignes (controle.py), en tire le verdict (decision.py) et compose la fiche
(fiche.py). Un modèle de 7 milliards de paramètres écrit « Respectée », « respecté », « non respecté »… et le serveur ne
ramène à l'énumération que les champs du premier niveau : les valeurs fermées sont donc normalisées ici.

Une ligne, une fois normalisée :
  passage        « C » : la lettre du passage du règlement donné au modèle (A, B, C…)
  citation       un extrait exact du règlement (8 à 20 mots) qui porte la règle
  nature         interdit · limite (un chiffre) · condition · exception · information
  vaut_ici       oui · non (autre secteur, autre situation, autre projet) · incertain
  exigence       ce que la règle exige, en une phrase
  constat        ce que la question ou les faits disent du projet sur ce point
  seuil, sens, valeur_projet   pour une règle chiffrée : le code compare lui-même les deux nombres
  statut         respectee · violee · inconnue
  manque         pour une règle inconnue : le fait qui manque est-il une caractéristique du « projet » (la distance qu'on
                 choisira) ou un fait sur l'« existant » (la date de la maison) ? Le code en tire seul le caractère décisif.
  fait_manquant  ce fait
"""
import re
import unicodedata

NATURES = ("interdit", "limite", "condition", "exception", "information")
VAUT = ("oui", "non", "incertain")
STATUTS = ("respectee", "violee", "inconnue")
SENS = ("au_plus", "au_moins", "limite_ou_au_moins")  # le dernier : « sur la limite ou à au moins 3 mètres »

SCHEMA_ANALYSE = {
    "type": "object",
    "properties": {
        "regles": {"type": "array", "items": {"type": "object", "properties": {
            "passage": {"type": "string"},
            "citation": {"type": "string"},
            "nature": {"type": "string", "enum": list(NATURES)},
            "vaut_ici": {"type": "string", "enum": list(VAUT)},
            "exigence": {"type": "string"},
            "constat": {"type": "string"},
            "seuil": {"type": ["number", "null"]},
            "sens": {"type": "string", "enum": list(SENS) + ["aucun"]},
            "valeur_projet": {"type": ["number", "null"]},
            "statut": {"type": "string", "enum": list(STATUTS)},
            "manque": {"type": "string", "enum": ["projet", "existant", "aucun"]},
            "fait_manquant": {"type": ["string", "null"]}},
            "required": ["passage", "citation", "nature", "vaut_ici", "exigence", "constat", "statut"]}},
        },
    "required": ["regles"]}


def sans_accent(t):
    t = unicodedata.normalize("NFD", str(t if t is not None else "").lower())
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


def nombre(x):
    """« 0,5 m » → 0.5 ; 3 → 3.0 ; rien ou texte sans chiffre → None."""
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    m = re.search(r"-?\d+(?:[.,]\d+)?", str(x))
    return float(m.group(0).replace(",", ".")) if m else None


def _choisir(valeur, table, defaut):
    v = sans_accent(valeur)
    for cle, motifs in table:
        if any(m in v for m in motifs):
            return cle
    return defaut


_NATURE = [("interdit", ["interdi", "prohib"]), ("exception", ["exception", "derog", "dispense", "toutefois"]),
           ("limite", ["limite", "maxim", "minim", "plafond", "seuil", "chiffr"]),
           ("information", ["info", "definition", "renvoi"]), ("condition", ["condition", "exigence", "oblig", "aspect"])]
_VAUT = [("non", ["non", "faux", "false", "pas "]), ("oui", ["oui", "vrai", "true"]), ("incertain", ["incertain", "peut", "possible"])]
# « non respecté » contient « respect » : les violations d'abord
_STATUT = [("violee", ["non respect", "viol", "enfreint", "depasse", "irrespect"]),
           ("respectee", ["respect", "conforme"]), ("inconnue", ["inconnu", "incertain", "manque", "verifier", "ne sait"])]
_MANQUE = [("existant", ["existant", "deja", "actuel"]), ("projet", ["projet", "conception", "choisi"])]
_SENS = [("limite_ou_au_moins", ["limite_ou", "limite ou"]), ("au_plus", ["au_plus", "plus", "max"]),
         ("au_moins", ["au_moins", "moins", "min"])]


def normaliser(brute):
    """Une ligne du modèle, ramenée au vocabulaire fermé. Ne juge rien : le contrôle est dans controle.py."""
    b = brute if isinstance(brute, dict) else {}
    m = re.search(r"[A-Za-z]{1,2}|\d+", re.sub(r"^\W*[Pp]assage\W*", "", str(b.get("passage") or "")))
    decisif = b.get("decisif")  # ancien champ : toujours lu, si le modèle l'écrit
    if isinstance(decisif, str):
        decisif = sans_accent(decisif).startswith(("true", "vrai", "oui"))
    manque = _choisir(b.get("manque"), _MANQUE, None)
    if manque is not None:  # un fait sur un bâtiment ou un terrain déjà là décide ; une donnée du projet se choisit
        decisif = manque == "existant"
    fait = b.get("fait_manquant")
    return {
        "passage": m.group(0).upper() if m else "",
        "citation": str(b.get("citation") or "").strip(),
        "nature": _choisir(b.get("nature"), _NATURE, "condition"),
        "vaut_ici": _choisir(b.get("vaut_ici"), _VAUT, "incertain"),
        "exigence": str(b.get("exigence") or "").strip(),
        "constat": str(b.get("constat") or "").strip(),
        "seuil": nombre(b.get("seuil")),
        "sens": _choisir(b.get("sens"), _SENS, None),
        "valeur_projet": nombre(b.get("valeur_projet")),
        "statut": _choisir(b.get("statut"), _STATUT, "inconnue"),
        "decisif": bool(decisif),
        "fait_manquant": (str(fait).strip() or None) if fait and sans_accent(fait) not in ("null", "none", "aucun") else None,
    }
