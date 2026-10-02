"""La démarche (rien, déclaration préalable ou permis), calculée par le code à partir du Code de l'urbanisme :
une règle nationale, stable, qu'un modèle n'a aucune raison de deviner. Chaque résultat dit pourquoi et renvoie au texte."""

LEGIFRANCE = {
    "R421-2": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050497056",
    "R421-9": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037799137/",
    "R421-11": "https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006074075/LEGISCTA000006188272/",
    "R421-12": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000034355392",
    "R421-14": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031764577",
    "R431-2": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000038682379",
}


def nb(x):
    """Une surface écrite à la française : 12,5 et non 12.5."""
    return f"{x:g}".replace(".", ",")


def _r(type_, pourquoi, *textes, delai=None):
    return {"type": type_, "pourquoi": pourquoi, "textes": [{"texte": t, "url": LEGIFRANCE[t]} for t in textes],
            "delai": delai}


def delai(type_, protege):
    if type_ == "déclaration préalable":
        return "2 mois (1 mois, plus 1 pour l'avis de l'ABF en site patrimonial)" if protege else "1 mois"
    if type_.startswith("permis"):
        return "2 mois en principe, davantage en site patrimonial (avis de l'ABF)" if protege else "2 mois en principe"
    if type_.startswith("dépend"):  # sans ces délais dans le contexte, l'agent en inventait (« trois mois », V14)
        return (f"{delai('déclaration préalable', protege)} pour une déclaration préalable ; "
                f"{delai('permis de construire', protege)} pour un permis")
    return None


def demarche(projet, surface=None, surface_totale_apres=None, zone_urbaine=True, protege=False, couverte=False,
             clotures_declarees=True):
    """projet : véranda, extension, piscine, abri de jardin, clôture, surélévation, maison neuve.
    surface : m² créés (emprise ou surface de plancher) ; surface_totale_apres : surface de la maison après travaux.
    clotures_declarees : la commune a soumis toutes les clôtures à déclaration (R421-12 d). Vrai à Biarritz : délibération
    du 21/09/2007, rappelée à l'article DG B-8 du règlement (trouvée par l'agent au 2e passage du banc)."""
    def fin(t, pourquoi, *textes):
        return _r(t, pourquoi, *textes, delai=delai(t, protege))

    if projet == "clôture":
        if protege:
            return fin("déclaration préalable", "clôture en site patrimonial remarquable", "R421-12")
        if clotures_declarees:
            return fin("déclaration préalable", "la commune soumet toutes les clôtures à déclaration (délibération du "
                       "21/09/2007, article DG B-8 du règlement)", "R421-12")
        return fin("aucune formalité", "clôture hors secteur protégé, dans une commune qui ne l'impose pas", "R421-2", "R421-12")
    if projet == "piscine":
        if couverte:  # R421-9 : un abri de 1,80 m ou plus fait passer la piscine au permis, même sans surface donnée
            return fin("permis de construire", "piscine couverte d'un abri de 1,80 m ou plus", "R421-9")
        if surface is None:
            return fin("dépend de la surface du bassin", "rien jusqu'à 10 m² hors secteur protégé, déclaration jusqu'à 100 m², permis au-delà",
                       "R421-2", "R421-9")
        if surface <= 10 and not protege:
            return fin("aucune formalité", "bassin de 10 m² au plus, hors secteur protégé", "R421-2")
        if surface <= 100:
            return fin("déclaration préalable", "bassin de 100 m² au plus, non couvert" + (" ; en site patrimonial, pas de dispense" if protege and surface <= 10 else ""),
                       "R421-9", *(["R421-2"] if protege and surface <= 10 else []))
        return fin("permis de construire", "bassin de plus de 100 m²", "R421-9")
    if projet == "abri de jardin":
        if surface is None:
            return fin("dépend de la surface", "rien jusqu'à 5 m² hors secteur protégé, déclaration jusqu'à 20 m², permis au-delà",
                       "R421-2", "R421-9")
        if surface <= 5 and not protege:
            return fin("aucune formalité", "5 m² au plus, hors secteur protégé", "R421-2")
        if surface <= 20:
            return fin("déclaration préalable", "de 5 à 20 m²" + (" ; en site patrimonial, même sous 5 m²" if protege else ""),
                       "R421-11" if protege else "R421-9")
        return fin("permis de construire", "plus de 20 m²", "R421-9")
    if projet in ("véranda", "extension"):
        if surface is None:
            return fin("dépend de la surface", "déclaration jusqu'à 20 m² (40 m² en zone urbaine), permis au-delà", "R421-14")
        seuil = 40 if zone_urbaine else 20
        if surface > 150:  # R431-2 : plus de 150 m² créés, la maison dépasse 150 m² quelle que soit sa surface d'avant
            return fin("permis de construire + architecte", f"{nb(surface)} m² créés : au-delà de 150 m²", "R421-14", "R431-2")
        if surface_totale_apres and surface_totale_apres > 150 and surface > 20:
            return fin("permis de construire + architecte", f"{nb(surface_totale_apres)} m² après travaux : au-delà de 150 m²",
                       "R421-14", "R431-2")
        if surface <= seuil:
            return fin("déclaration préalable", f"{nb(surface)} m² créés, sous le seuil de {seuil} m²" + (" (zone urbaine)" if zone_urbaine else ""),
                       "R421-14")
        return fin("permis de construire", f"{nb(surface)} m² créés, au-delà de {seuil} m²", "R421-14")
    if projet == "surélévation":
        if surface is None:
            return fin("dépend de la surface créée", "au moins une déclaration préalable (aspect extérieur modifié) ; permis si plus "
                       "de 40 m² sont créés en zone urbaine", "R421-14")
        return demarche("extension", surface, surface_totale_apres, zone_urbaine, protege)
    if projet == "maison neuve":
        if surface and surface > 150:  # R431-2 : un particulier qui construit plus de 150 m² pour lui-même fait appel à un architecte
            return fin("permis de construire + architecte", f"maison neuve de {nb(surface)} m² : au-delà de 150 m²", "R421-9", "R431-2")
        return fin("permis de construire", "construction neuve d'habitation", "R421-9")
    return _r("sans objet", "question sans projet de travaux")
