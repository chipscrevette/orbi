"""La fiche : le texte de la réponse, composé par le code à partir de la décision et des lignes contrôlées.

Le verdict et le texte ne peuvent plus se contredire (« Oui, vous pouvez… » puis « l'abri est interdit »), puisque le texte sort
du verdict. Les phrases libres du modèle (exigence, constat) ne servent que d'illustration, après contrôle des chiffres."""


import re

# le modèle écrit parfois un constat à la place du fait qui manque : « le projet ne précise pas si X » → « si X »
_CONSTAT = re.compile(r"^(?:le projet|la question|le texte|la demande)\s+ne\s+(?:précise|dit|donne|mentionne|indique)\s+pas\s+", re.I)


def _manque(s):
    """Un fait qui manque, dit comme un fait (« si le rehaussement est une saillie », « la hauteur actuelle »)."""
    return _CONSTAT.sub("", " ".join((s or "").split())).strip()


def _p(s):
    """Une phrase : majuscule, un seul point final."""
    s = (s or "").strip()
    return (s[0].upper() + s[1:]).rstrip(" .;") + "." if s else ""


def _court(s, n=150):
    """Un texte coupé à un mot, avec « … »."""
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[:n].rsplit(" ", 1)[0] + "…"


def _etat(r):
    """« L'exigence (UD 7) : le constat » : la ligne d'une règle dans le texte."""
    exigence = r["exigence"] or _court(r.get("citation"), 140)
    t = f"{exigence.rstrip(' .')} ({r['article']})"
    return f"{t} — {r['constat'].rstrip(' .')}" if r.get("constat") else t


def composer(dec, regles, dem, verrou=None, a_verifier_modele=()):
    """→ {reponse, lignes, a_verifier}. regles : les lignes contrôlées. dem : la démarche calculée par le code."""
    par_id = {r["id"]: r for r in regles}
    v, raison = dec["verdict"], dec["raison"]
    phrases = []
    if raison == "verrou":
        phrases = ["Non, ce projet n'est pas possible à cet endroit.", _p(f"{verrou['pourquoi']} (article {verrou['article']})")]
    elif v == "non":
        motifs = [_p(_etat(par_id[i])) for i in dec["violations"][:2]]
        entete = ("Non : dans cette zone, tout est interdit sauf ce que le règlement admet, et le projet n'entre dans aucune de ces exceptions."
                  if raison == "aucune_exception" else "Non, ce projet n'est pas possible tel que vous le décrivez.")
        phrases = [entete] + motifs
    elif v == "impossible à dire":
        if raison == "aucune_regle":
            phrases = ["Je n'ai trouvé aucune règle du PLU qui permette de trancher ce cas avec les éléments donnés."]
        elif raison == "verrou_incertain":
            phrases = ["Je ne peux pas conclure en l'état.", _p(verrou["pourquoi"]),
                       _p("Il me faut " + (verrou.get("fait_manquant") or "un fait que la question ne donne pas"))]
        else:
            phrases = ["Je ne peux pas conclure en l'état."]
            faits = [_court(_manque(par_id[i].get("fait_manquant")), 110) for i in dec["decisives"] if par_id[i].get("fait_manquant")]
            if raison == "exception_incertaine":
                phrases.append("Ce projet est interdit sauf exception, et l'exception dépend d'un fait que la question ne donne pas.")
            if faits:
                phrases.append("Il me manque : " + " ; ".join(f.rstrip(" .") for f in faits[:3]) + ".")
    elif v == "oui sous conditions":
        conditions = [_etat(par_id[i]) for i in (dec["inconnues"] + dec["levees"])[:3]]
        phrases = ["Oui, sous conditions."] + [_p(_court(c, 180)) for c in conditions]
        if raison == "exception_levee":
            phrases.append("Une exception du règlement s'applique.")
    else:  # oui
        phrases = ["Oui, ce projet respecte les règles du PLU que j'ai pu vérifier."]
        etats = [par_id[i]["exigence"] or par_id[i]["citation"][:100] for i in dec["respectees"][:2]]
        if etats:
            phrases.append(_p("Règles vérifiées : " + "; ".join(e.rstrip(" .") for e in etats)))
    if dem and dem.get("type") not in (None, "sans objet") and v != "non":
        phrases.append(_p(f"Démarche : {dem['type']} ({dem['pourquoi']})" + (f", délai d'instruction : {dem['delai']}" if dem.get("delai") else "")))

    lignes = []
    if verrou and raison in ("verrou", "verrou_incertain"):
        lignes.append({"id": "V", "statut": "violee" if raison == "verrou" else "inconnue", "nature": "interdit", "vaut_ici": "oui",
                       "article": verrou["article"], "exigence": verrou["pourquoi"], "constat": "", "citation": verrou["citation"]})
    for r in regles:
        if r["nature"] == "information":
            continue
        lignes.append({"id": r["id"], "statut": "ecartee" if r["vaut_ici"] == "non" else r["statut"], "nature": r["nature"],
                       "vaut_ici": r["vaut_ici"], "article": r["article"], "page": r.get("page"), "exigence": r["exigence"],
                       "constat": r["constat"], "citation": r["citation"], "decisif": r["decisif"],
                       "compare_par_le_code": r.get("compare_par_le_code", False)})
    a_verifier = [_court(_manque(x), 160) for x in dec["a_verifier"]]
    for x in a_verifier_modele:
        if x and x not in a_verifier and len(a_verifier) < 5:
            a_verifier.append(_court(x, 160))
    return {"reponse": " ".join(p for p in phrases if p), "lignes": lignes, "a_verifier": a_verifier}
