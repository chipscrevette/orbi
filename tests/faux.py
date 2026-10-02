"""Les doublures des tests : un faux modèle, de faux outils, une fausse recherche. Elles permettent de faire tourner l'agent entier
(tri, outils, verrou, grille, contrôle, décision, fiche) sans carte graphique, sans réseau et sans serveur d'embeddings."""


class FauxCerveau:
    """Remplace orbi.modele.cerveau.demander : rend les réponses préparées dans l'ordre, et note chaque appel."""

    def __init__(self, *reponses):
        self.reponses = list(reponses)
        self.appels = []

    def __call__(self, systeme, utilisateur, schema, effort="low", max_jetons=1200, temperature=0.2, historique=None):
        self.appels.append({"systeme": systeme, "utilisateur": utilisateur, "effort": effort, "max_jetons": max_jetons})
        obj = self.reponses.pop(0) if self.reponses else None
        return obj, {"secondes": 0.0, "jetons": 0, "effort": effort, "reflexion": "", "brut": ""}


class FausseRecherche:
    """Remplace orbi.reglement.recherche.Recherche : pour un long article de la recette, le « meilleur passage » est l'article
    entier ; la recherche libre ne trouve rien. Les passages restent donc ceux de la recette, ce que les tests veulent maîtriser."""

    def __init__(self, *a, **k):
        pass

    def mots_rares(self, question, adresse=""):
        return ""

    def chercher(self, requetes, chapitres, k=1, un_par_article=False, exclure=(), refs=None):
        from orbi.reglement.donnees import article, propre
        return [{"ref": r, "pages": article(r)["pages"], "texte": propre(article(r)["texte"])} for r in (refs or [])]


def faits(zone="UD", surface=610, prescriptions=(), spr=False, hauteurs=(), commune="Biarritz", dans_le_perimetre=True):
    """Les faits d'une parcelle, comme les rend orbi.outils.geo.faits."""
    return {"trouvee": True, "dans_le_perimetre": dans_le_perimetre,
            "adresse": {"label": f"5 Impasse Monnier 64200 {commune}", "lon": -1.55, "lat": 43.47, "commune": commune,
                        "code_insee": "64122" if commune == "Biarritz" else "64024", "fiabilite": 0.97},
            "parcelle": {"parcelle": "AB 0001", "surface_m2": surface},
            "zonage": {"zone": zone, "type_zone": "N" if zone.startswith("N") else "U", "document": "64122_PLU"},
            "contraintes": {"prescriptions": list(prescriptions), "informations": [],
                            "servitudes": ["Site patrimonial remarquable de Biarritz"] if spr else [],
                            "hauteurs_au_plan": list(hauteurs), "site_patrimonial": spr}}


def tri(projet="abri de jardin", adresse="5 impasse Monnier, Biarritz", surface=None, existante=None, sujet="droit", **autres):
    """La lecture de la question par le modèle (étape « tri »)."""
    return {"adresse": adresse, "parcelle": None, "projet": projet, "surface_m2": surface, "surface_existante_m2": existante,
            "piscine_couverte": False, "point_de_vue": "propriétaire", "sujet": sujet, "recherches": [projet], **autres}


def ligne(citation, nature="limite", statut="respectee", vaut_ici="oui", passage="A", seuil=None, sens=None, valeur=None,
          manque=None, fait=None, exigence="une règle", constat=""):
    """Une ligne de la grille, comme le modèle la remplit."""
    return {"passage": passage, "citation": citation, "nature": nature, "vaut_ici": vaut_ici, "exigence": exigence,
            "constat": constat, "seuil": seuil, "sens": sens or "aucun", "valeur_projet": valeur, "statut": statut,
            "manque": manque or "aucun", "fait_manquant": fait}
