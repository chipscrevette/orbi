"""Le banc d'essai v1 : 20 questions réelles sur Biarritz, avec la bonne réponse écrite à partir du règlement.
Sorties : bancs/jeux/questions.json (pour la notation automatique) et bancs/jeux/questions.html (pour validation)."""
import html, json, os, re
from orbi.chemins import DONNEES, JEUX  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
D = DONNEES
B = JEUX
pages = json.load(open(os.path.join(D, "pages.json"), encoding="utf-8"))
C = {c["adresse"]: c for c in json.load(open(os.path.join(B, "adresses-candidates.json"), encoding="utf-8"))}


ARTICLES = json.load(open(os.path.join(D, "articles.json"), encoding="utf-8"))


def page(article, phrase):
    """La page où se trouve vraiment la phrase, cherchée UNIQUEMENT dans les pages de l'article cité : la même phrase
    revient souvent d'une zone à l'autre (« Les piscines, spas et jacuzzis… » en UB, UC et UD)."""
    if article.startswith("DG"):  # « DG B-5 » : l'article B-5 des dispositions générales
        zone, num = "DG", (article.split()[1] if len(article.split()) > 1 and article.split()[1] in ARTICLES["DG"] else "0")
    else:
        zone, num = article.split()
    p0, p1 = ARTICLES[zone][num]["pages"]
    norme = lambda s: " ".join(s.replace("", " ").split())  # le PDF met des puces «  » dans les listes
    cle = norme(phrase)
    for p, t in pages:
        if p0 <= p <= p1 and cle[:60] in norme(t):
            return p
    # la phrase peut chevaucher deux pages : on la cherche dans le texte complet de l'article
    if cle[:60] in norme(ARTICLES[zone][num]["texte"]):
        return p0
    raise ValueError(f"phrase introuvable dans {article} (p. {p0}-{p1}) : {cle[:60]}")


def r(article, phrase, dit):
    return {"article": article, "page": page(article, phrase), "citation": phrase, "dit": dit}


SPR = "servitude AC4 : site patrimonial remarquable, l'Architecte des Bâtiments de France (ABF) donne son avis"
EMPRISE_DG = r("DG B-5", "toutefois les installations sportives de plein-air telles que piscines non couvertes",
               "une piscine non couverte ne compte pas dans l'emprise au sol")
