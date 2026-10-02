"""Le moteur de décision : du Python pur, sans modèle. Il reçoit les lignes de la grille, déjà contrôlées, et en tire le verdict.

Pourquoi un moteur à part. Au banc caché, le modèle retrouvait la bonne règle, la citait exactement, puis concluait
l'inverse (un abri à 0,5 m de la limite, là où l'article impose la limite ou 3 m : « oui sous conditions »). Lire une
règle et la comparer au projet sont deux métiers : le premier va au modèle, le second est une table de décision, qu'on
teste, qu'on rejoue et qu'on explique.

La table, dans l'ordre :
  1. verrou de zone (verrou.py)                         → le verdict est fixé par le règlement, avant toute analyse
  2. une règle qui vaut ici est violée                  → NON   (sauf exception, ci-dessous)
       … et une exception applicable la lève            → au mieux « oui sous conditions »
       … et une exception qui vaut ici dépend d'un fait inconnu → IMPOSSIBLE À DIRE (« non » exige la preuve qu'aucune exception
         ne s'applique ; V14 : une saillie peut être admise dans la bande de 3 m)
  3. zone stricte (N, Ncu, Ner, IIAU : « tout est interdit sauf… ») : sans exception établie, pas d'autorisation
       … une exception dépend d'un fait inconnu       → IMPOSSIBLE À DIRE
       … les exceptions examinées ne couvrent pas le projet → NON
       … aucune exception examinée                    → IMPOSSIBLE À DIRE
  3b. une règle dont l'applicabilité est incertaine est violée → IMPOSSIBLE À DIRE (on ne conclut pas « non » sur un doute)
  4. un fait déjà fixé manque (date de la maison…)       → IMPOSSIBLE À DIRE
  5. aucune règle établie                                → IMPOSSIBLE À DIRE : l'absence de preuve n'est pas une autorisation
  6. une condition reste à vérifier, ou avis de l'ABF    → OUI SOUS CONDITIONS
  7. tout est respecté, rien ne manque                   → OUI
Une règle « écartée » (autre secteur, autre projet) ne pèse jamais, ni pour ni contre."""


def _ids(rs):
    return [r["id"] for r in rs]


def _vise(exception, regle):
    """Une exception porte sur la règle de son article (ou sur toutes, si c'est une disposition générale « DG »)."""
    a = exception.get("article")
    return a == regle.get("article") or str(a or "").startswith("DG")


def decider(regles, verrou=None, abf=False, zone_stricte=False):
    """regles : lignes normalisées et contrôlées (id, nature, vaut_ici, statut, decisif, fait_manquant…).
    verrou : le dict de verrou.verrou(), ou None. abf : la parcelle est en site patrimonial remarquable (avis obligatoire).
    zone_stricte : la zone interdit tout sauf des exceptions listées (verrou.ZONES_STRICTES).
    Renvoie {verdict, raison, violations, levees, decisives, inconnues, respectees, ecartees, a_verifier}."""
    ecartees = [r for r in regles if r["vaut_ici"] == "non"]
    actives = [r for r in regles if r["vaut_ici"] != "non" and r["nature"] != "information"]
    for r in actives:  # un doute sur l'applicabilité d'une règle violée ne permet pas de conclure
        if r["vaut_ici"] == "incertain" and r["statut"] == "violee":
            r["statut"], r["decisif"] = "inconnue", True
            r["fait_manquant"] = r.get("fait_manquant") or "si cette règle vise bien la parcelle et le projet"

    violations = [r for r in actives if r["statut"] == "violee" and r["nature"] in ("interdit", "limite", "condition")]
    exceptions_ok = [r for r in actives if r["nature"] == "exception" and r["statut"] == "respectee"]
    exceptions_inconnues = [r for r in actives if r["nature"] == "exception" and r["statut"] == "inconnue"]
    exceptions_violees = [r for r in actives if r["nature"] == "exception" and r["statut"] == "violee"]
    exceptions_incertaines = [r for r in exceptions_inconnues if r["decisif"] or r["vaut_ici"] == "oui"]
    decisives = [r for r in actives if r["statut"] == "inconnue" and r["decisif"]]
    inconnues = [r for r in actives if r["statut"] == "inconnue" and not r["decisif"]]
    respectees = [r for r in actives if r["statut"] == "respectee"]
    levees = []

    def a_verifier(*groupes):
        out = []
        for g in groupes:
            for r in g:
                x = r.get("fait_manquant")
                if x and x not in out:
                    out.append(x)
        if abf and not any("abf" in x.lower() or "architecte des bâtiments" in x.lower() for x in out):
            out.append("l'avis de l'Architecte des Bâtiments de France (site patrimonial remarquable)")
        return out

    def rendre(verdict, raison):
        return {"verdict": verdict, "raison": raison, "violations": _ids(violations), "levees": _ids(levees),
                "decisives": _ids(decisives), "inconnues": _ids(inconnues), "respectees": _ids(respectees),
                "ecartees": _ids(ecartees), "a_verifier": [] if verdict == "non" else a_verifier(decisives, inconnues)}

    # 1. le verrou de zone
    if verrou:
        permis = verrou.get("verdicts") or []
        if permis == ["non"]:
            return rendre("non", "verrou")
        if "non" in permis and "impossible à dire" in permis:
            # « non » si une violation est établie, sinon le fait qui manque (la date de la maison…) décide
            if violations:
                return rendre("non", "violation")
            return rendre("impossible à dire", "verrou_incertain")

    # 2. une violation, que seule une exception peut lever (hors zone stricte : là, l'exception lève l'interdiction de la zone,
    #    pas une autre règle violée). Une exception ne lève que les violations de son article : celle d'UD 7 (saillies) ne change rien
    #    à un abri de 15 m² qui dépasse les 9 m² d'UD 2 (V06).
    if violations:
        if zone_stricte:
            return rendre("non", "violation")
        ouvertes = []
        for v in violations:
            (levees if any(_vise(e, v) for e in exceptions_ok) else ouvertes).append(v)
        violations = ouvertes
        if violations:
            if any(not any(_vise(e, v) for e in exceptions_incertaines) for v in violations):
                return rendre("non", "violation")  # au moins une violation qu'aucune exception ne pourrait lever
            decisives = [e for e in exceptions_incertaines if any(_vise(e, v) for v in violations)]
            return rendre("impossible à dire", "exception_incertaine")

    # 3. zone stricte : sans exception établie, le projet n'est pas démontré autorisé
    if zone_stricte and not exceptions_ok:
        if exceptions_inconnues:
            decisives = exceptions_inconnues
            return rendre("impossible à dire", "exception_incertaine")
        if exceptions_violees:
            violations = exceptions_violees
            return rendre("non", "aucune_exception")
        return rendre("impossible à dire", "aucune_regle")

    # 3b, 4. un fait déjà fixé manque
    if decisives:
        return rendre("impossible à dire", "inconnu_decisif")

    # 5. l'absence de preuve n'est pas une autorisation
    if not respectees and not inconnues and not levees:
        return rendre("impossible à dire", "aucune_regle")

    # 6, 7. possible : sous conditions s'il reste quelque chose à vérifier, sinon oui
    if levees:
        return rendre("oui sous conditions", "exception_levee")
    if inconnues:
        return rendre("oui sous conditions", "a_verifier")
    if abf:
        return rendre("oui sous conditions", "abf")
    return rendre("oui", "tout_respecte")
