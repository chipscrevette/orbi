"""Les cas du moteur de décision : chaque cas décrit une situation réelle sous forme de lignes de grille (nature, statut,
applicabilité…) et le verdict qu'un instructeur en tirerait. Partagés par test_decision, test_fiche et les mutations."""
NON = {"verdicts": ["non"]}
NON_OU_INCERTAIN = {"verdicts": ["non", "impossible à dire"]}
CAS = []


def R(nature="limite", statut="respectee", vaut="oui", decisif=False, exigence="une règle", fait=None, article=None):
    return {"id": None, "nature": nature, "vaut_ici": vaut, "statut": statut, "decisif": decisif, "exigence": exigence,
            "fait_manquant": fait, "article": article}


def cas(groupe, nom, regles, attendu, verrou=None, abf=False, stricte=False):
    for i, r in enumerate(regles, 1):
        r["id"] = f"R{i}"
    CAS.append((groupe, nom, regles, attendu, verrou, abf, stricte))


# ------------------------------------------------------------------------------------------------ 10 projets permis
G = "permis"
cas(G, "piscine non couverte de 28 m², emprise respectée", [R("condition"), R("limite")], "oui")
cas(G, "piscine hors sol collée au mur : la règle de distance exclut les piscines",
    [R("limite", "inconnue", vaut="non"), R("condition")], "oui")
cas(G, "abri de 7 m² : la distance reste à prévoir", [R("limite", "inconnue", fait="distance de l'abri à la limite"), R("limite")],
    "oui sous conditions")
cas(G, "véranda de 25 m² en site patrimonial, tout est respecté", [R("limite"), R("condition")], "oui sous conditions", abf=True)
cas(G, "clôture de 1,40 m sur rue, maximum 1,50 m", [R("limite")], "oui")
cas(G, "maison R+1 en UH, hauteur 7 m sous 15 m", [R("limite"), R("limite")], "oui")
cas(G, "carport sur la limite, hauteur à vérifier", [R("limite"), R("limite", "inconnue", fait="hauteur au droit de la limite")],
    "oui sous conditions")
cas(G, "extension de 6 m² sous le plafond d'emprise", [R("limite")], "oui")
cas(G, "règle d'aspect « pourra être refusée » : une condition, pas un interdit",
    [R("condition", "inconnue", fait="aspect extérieur, laissé à la mairie"), R("limite")], "oui sous conditions")
cas(G, "projet dispensé de formalité mais en site protégé", [R("condition")], "oui sous conditions", abf=True)

# ------------------------------------------------------------------------------------------------ 10 projets interdits
G = "interdit"
cas(G, "abri à 0,5 m de la limite (sur la limite ou à 3 m au moins)", [R("limite", "violee")], "non")
cas(G, "véranda alors que l'emprise maximale est déjà atteinte", [R("limite", "violee")], "non")
cas(G, "clôture de 1,80 m sur rue, maximum 1,50 m", [R("limite", "violee"), R("condition")], "non")
cas(G, "parpaings nus : l'emploi est interdit", [R("interdit", "violee")], "non")
cas(G, "maison neuve en zone Ncu : le verrou décide", [], "non", verrou=NON)
cas(G, "violation levée par une exception applicable (adossé à une façade aveugle)",
    [R("limite", "violee"), R("exception", "respectee")], "oui sous conditions")
cas(G, "violation, exception qui dépend d'un fait inconnu", [R("limite", "violee"), R("exception", "inconnue", decisif=True,
                                                                                         fait="si l'abri est adossé à la façade")],
    "impossible à dire")
cas(G, "violation, exception inapplicable (non adossé)", [R("limite", "violee"), R("exception", "violee")], "non")
cas(G, "violation d'UD 2 que l'exception d'UD 7 (adossement) ne lève pas",
    [R("limite", "violee", article="UD 7"), R("exception", "respectee", article="UD 7"), R("limite", "violee", article="UD 2")], "non")
cas(G, "violation levée par l'exception de son article, une autre règle respectée",
    [R("limite", "violee", article="UD 7"), R("exception", "respectee", article="UD 7"), R("limite", article="UD 9")],
    "oui sous conditions")
cas(G, "violation, exception qui vaut ici sans fait décisif (une saillie ?) : on ne conclut pas « non »",
    [R("limite", "violee", article="UD 7"), R("exception", "inconnue", article="UD 7", fait="si le rehaussement est une saillie")],
    "impossible à dire")
cas(G, "violation, exception dont l'applicabilité est incertaine : « non » reste",
    [R("limite", "violee", article="UD 7"), R("exception", "inconnue", vaut="incertain", article="UD 7")], "non")
cas(G, "violation d'UD 10, exception inconnue d'UD 7 : elle ne la lève pas",
    [R("limite", "violee", article="UD 10"), R("exception", "inconnue", article="UD 7")], "non")
cas(G, "deux violations", [R("limite", "violee"), R("interdit", "violee")], "non")
cas(G, "violation d'une règle écartée (autre secteur), l'autre règle est respectée", [R("limite", "violee", vaut="non"), R("limite")], "oui")

# ------------------------------------------------------------------------------------------------ 10 cas d'information manquante
G = "manquant"
cas(G, "extension en zone N, date de la maison inconnue", [R("exception", "inconnue", decisif=True, fait="la date de la maison")],
    "impossible à dire")
cas(G, "surélévation, hauteur actuelle inconnue", [R("limite", "inconnue", decisif=True, fait="la hauteur actuelle du bâtiment")],
    "impossible à dire")
cas(G, "aucune règle établie : l'absence de preuve n'est pas une autorisation", [], "impossible à dire")
cas(G, "toutes les règles sont écartées", [R(vaut="non"), R(vaut="non")], "impossible à dire")
cas(G, "règles respectées mais un fait décisif manque", [R(), R("limite", "inconnue", decisif=True, fait="la surface déjà construite")],
    "impossible à dire")
cas(G, "violation, mais la règle vise-t-elle la parcelle ? (applicabilité incertaine)", [R("limite", "violee", vaut="incertain")],
    "impossible à dire")
cas(G, "verrou « non ou impossible à dire », aucune violation établie", [R("exception", "inconnue", decisif=True)], "impossible à dire",
    verrou=NON_OU_INCERTAIN)
cas(G, "verrou « non ou impossible à dire », violation établie", [R("limite", "violee")], "non", verrou=NON_OU_INCERTAIN)
cas(G, "seulement des lignes d'information", [R("information")], "impossible à dire")
cas(G, "violation certaine et fait manquant : la violation prime", [R("limite", "violee"), R("limite", "inconnue", decisif=True)], "non")

# ------------------------------------------------------------------------------------------------ 10 zones restrictives et exceptions
G = "restrictif"
cas(G, "maison neuve en zone UG", [], "non", verrou=NON)
cas(G, "maison neuve en Nh : l'exception de la villa individuelle s'applique, l'insertion reste à vérifier",
    [R("exception"), R("condition", "inconnue", fait="insertion dans l'espace naturel")], "oui sous conditions", stricte=True)
cas(G, "abri de jardin en zone N : annexes admises seulement pour une maison de 1995", [], "impossible à dire", verrou=NON_OU_INCERTAIN)
cas(G, "piscine non couverte en Ncu, en site patrimonial", [R("exception"), R("condition")], "oui sous conditions", abf=True,
    stricte=True)
cas(G, "extension de 20 m² en Nh, sous la limite", [R("limite"), R("exception")], "oui", stricte=True)
cas(G, "extension de 30 m² en Nh, surface d'avant 1995 inconnue", [R("exception", "inconnue", decisif=True, fait="la surface de 1995")],
    "impossible à dire", stricte=True)
cas(G, "extension de 25 m² en zone N, limite à 9 m²", [R("limite", "violee"), R("exception", "violee")], "non", stricte=True)
cas(G, "espace vert protégé : règle d'applicabilité incertaine, mais respectée", [R("limite", vaut="incertain")], "oui")
cas(G, "abri de jardin en zone Ncu", [], "non", verrou=NON)
cas(G, "maison neuve en zone IIAU", [], "non", verrou=NON)

cas(G, "piscine couverte en Ncu : la seule exception (piscine non couverte) n'est pas remplie", [R("exception", "violee")], "non",
    stricte=True)
cas(G, "zone N : aucune exception examinée, rien n'est démontré autorisé", [R("limite")], "impossible à dire", stricte=True)
cas(G, "zone N : une exception dépend d'un fait que la question ne donne pas", [R("exception", "inconnue")], "impossible à dire",
    stricte=True)
cas(G, "zone N : l'exception s'applique et tout est respecté", [R("exception"), R("limite")], "oui", stricte=True)
cas(G, "hors zone stricte, une exception inconnue non décisive n'empêche pas « sous conditions »", [R("exception", "inconnue"), R("limite")],
    "oui sous conditions")

# ------------------------------------------------------------------------------------------------ 6 garde-fous du moteur
G = "garde-fous"
cas(G, "le verrou prime sur des lignes respectées", [R(), R()], "non", verrou=NON)
cas(G, "des inconnues sans importance donnent « sous conditions »", [R("condition", "inconnue"), R("condition", "inconnue")],
    "oui sous conditions")
cas(G, "l'avis de l'ABF seul suffit à écarter le « oui »", [R()], "oui sous conditions", abf=True)
cas(G, "une ligne d'information ne compte pas, une règle respectée oui", [R("information", "inconnue"), R()], "oui")
cas(G, "un fait décisif manquant, une violation écartée", [R("limite", "violee", vaut="non"), R("limite", "inconnue", decisif=True)],
    "impossible à dire")
cas(G, "règle d'applicabilité incertaine respectée + règle respectée", [R(vaut="incertain"), R()], "oui")
