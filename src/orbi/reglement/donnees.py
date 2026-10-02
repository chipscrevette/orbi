"""Le règlement du PLU de Biarritz, découpé : articles (zone × numéro) et morceaux pour la recherche.
Une référence s'écrit comme dans le règlement : « UD 9 », « UA 11 », « DG B-5 » (dispositions générales)."""
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher

from orbi.chemins import DONNEES, RACINE  # noqa: F401  (RACINE : importé ailleurs depuis ce module)

ARTICLES = json.load(open(os.path.join(DONNEES, "articles.json"), encoding="utf-8"))
# les puces du PDF (polices Symbol et Wingdings) arrivent en caractères privés : U+F0B7, U+F0E0 (flèche), U+F0A7…
PUCES = re.compile("[\ue000-\uf8ff]")


def propre(t):
    """Texte du règlement tel qu'on le montre au modèle : puces retirées, espaces unifiés."""
    return " ".join(PUCES.sub(" ", t).split())


def norme(t):
    """Texte comparable : puces du PDF retirées, apostrophes et espaces unifiés, minuscules."""
    t = PUCES.sub(" ", t)
    t = t.replace("’", "'").replace("‘", "'").replace("«", '"').replace("»", '"')
    return " ".join(t.split()).lower()


def chapitre(zone):
    """Le chapitre du règlement qui s'applique à une zone du plan : UDa → UD, UAs → UA, Nh → N, Ncu → Ncu."""
    z = (zone or "").strip()
    for c in ("Ncu", "Ner"):
        if z.startswith(c):
            return c
    if z.startswith("N"):
        return "N"
    if z.startswith(("IIAU", "IAU", "1AU")):
        return "IIAU"
    for c in ("UA", "UB", "UC", "UD", "UG", "UH", "UP", "UY"):
        if z.startswith(c):
            return c
    return None


def article(ref):
    """« UD 9 » → l'article ; « DG B-5 » → l'article B-5 des dispositions générales."""
    z, n = ref.split(maxsplit=1)
    return ARTICLES[z][n]


def existe(ref):
    """L'article existe-t-il ? Une référence absente (un champ null du modèle) n'existe pas, sans planter."""
    if not ref or not isinstance(ref, str):
        return False
    try:
        article(ref)
        return True
    except (KeyError, ValueError):
        return False


def _morceaux_de(citation):
    """Les morceaux d'une citation : coupés aux « … » ou « [...] », sans guillemets ni ponctuation de bord."""
    return [m.strip(" .\"'") for m in re.split(r"\[\.\.\.\]|\.\.\.|…", norme(citation or ""))]


def references(chap):
    """Toutes les références d'un chapitre, dans l'ordre des articles."""
    return [f"{chap} {n}" for n in sorted(ARTICLES[chap], key=lambda n: int(n) if n.isdigit() else 99)]


def morceaux(taille=1200, recouvrement=200):
    """Les morceaux de recherche : un article court = un morceau ; un long article est coupé, mais chaque morceau
    garde sa référence (« UD 11 ») : une citation renvoie toujours à un article exact."""
    out = []
    for z, arts in ARTICLES.items():
        for n, a in arts.items():
            if z == "DG" and n == "0":
                continue  # le bloc entier des dispositions générales : ses articles sont déjà séparés
            t = propre(a["texte"])
            ref = f"{z} {n}"
            if len(t) <= taille:
                out.append({"ref": ref, "chapitre": z, "pages": a["pages"], "texte": t})
                continue
            i = 0
            while i < len(t):
                out.append({"ref": ref, "chapitre": z, "pages": a["pages"], "texte": t[i:i + taille]})
                i += taille - recouvrement
    return out


PAGES = json.load(open(os.path.join(DONNEES, "pages.json"), encoding="utf-8"))


def page_citation(ref, citation):
    """La page exacte où se trouve la citation, cherchée dans les pages de son article (pas seulement sa première page)."""
    if not citation or not existe(ref):
        return None
    p0, p1 = article(ref)["pages"]
    debut = [m for m in _morceaux_de(citation) if len(m) >= 12]
    cle = (debut[0] if debut else norme(citation))[:50]
    for p, t in PAGES:
        if p0 <= p <= p1 and cle in norme(t):
            return p
    return p0


def cite_bien(ref, citation):
    """La citation existe-t-elle mot pour mot dans l'article ? (au moins 20 caractères, points de suspension permis). Chaque
    morceau affiché est vérifié, même court : « … à 5 mètres » après une phrase exacte ne passe plus."""
    if not citation or not existe(ref):
        return False
    texte = norme(article(ref)["texte"])
    morceaux_cit = [m for m in _morceaux_de(citation) if m]
    longs = [m for m in morceaux_cit if len(m) >= 12]
    return bool(longs) and sum(len(m) for m in morceaux_cit) >= 20 and all(m in texte for m in morceaux_cit)


NEGATIONS = {"ne", "n", "pas", "non", "sauf", "aucun", "aucune", "ni", "jamais", "interdit", "interdits", "interdite",
             "interdites", "autorise", "autorises", "autorisee", "autorisees"}


# les mots qui fixent le sens d'une limite : changer l'un pour son contraire n'est jamais une coquille
POLARITES = ("plus", "moins", "minim", "maxim", "inferieur", "superieur", "exclu", "inclu", "oblig", "facult", "autoris",
             "interdi", "admis", "refus", "avant", "apres", "dessus", "dessous")


def _signature(t):
    """Ce qu'un recalage n'a pas le droit de changer : les chiffres, les négations, et les mots de sens (au moins / au plus,
    minimum / maximum, inférieure / supérieure, exclus / inclus)."""
    t = "".join(c for c in unicodedata.normalize("NFD", norme(t)) if unicodedata.category(c) != "Mn")
    mots = re.findall(r"[a-z]+", t)
    return (re.findall(r"\d+(?:[.,]\d+)?", t), sorted(w for w in mots if w in NEGATIONS),
            sorted(p for w in mots for p in POLARITES if w.startswith(p)))


def recaler(ref, citation, seuil=0.9):
    """Une citation presque exacte (un accord « corrigé », une espace de trop) est remplacée par le passage exact de
    l'article : ce qui s'affiche est toujours le texte du règlement. Refusé si le passage le plus proche diffère par
    un chiffre ou une négation (là, le modèle a changé le sens : c'est une faute, pas une coquille). Renvoie le
    passage exact, ou None."""
    if not existe(ref) or not citation:
        return None
    mots_art = propre(article(ref)["texte"]).split()
    morceaux_cit = [m.strip(" .\"'") for m in re.split(r"\.\.\.|…|\[\.\.\.\]", citation)]
    exacts = []
    for m in (m for m in morceaux_cit if len(m) >= 12):
        if norme(m) in norme(article(ref)["texte"]):
            exacts.append(m)
            continue
        cible, n = norme(m), len(m.split())
        meilleur, score = None, 0.0
        for L in (n - 1, n, n + 1):
            for i in range(max(1, len(mots_art) - L + 1)):
                cand = " ".join(mots_art[i:i + L])
                sm = SequenceMatcher(None, norme(cand), cible)
                if sm.quick_ratio() > max(score, seuil) and sm.ratio() > max(score, seuil - 1e-9):
                    meilleur, score = cand, sm.ratio()
        if not meilleur or _signature(meilleur) != _signature(m):
            return None
        exacts.append(meilleur.strip(" ,;"))
    return " … ".join(exacts) if exacts else None


def raccorder(ref, citation, morceaux_max=3, mini=20, saut_max=300):
    """Une citation faite de passages exacts mis bout à bout sans « … » : au 3e passage, le modèle sautait dans UD 9 la
    ligne du secteur UDb, qui ne le concernait pas. On remet les « … » : chaque morceau garde les mots exacts du
    règlement, dans son ordre, et ce qui est sauté se voit (300 caractères au plus entre deux morceaux, pour qu'une
    coupure ne change pas le sens). Renvoie la citation raccordée, ou None."""
    if not existe(ref) or not citation:
        return None
    base = propre(article(ref)["texte"])
    comp = base.replace("’", "'").replace("‘", "'").replace("«", '"').replace("»", '"').lower()
    if len(comp) != len(base):  # norme() doit garder les positions pour qu'on retrouve le texte d'origine
        return None
    c = norme(citation).strip(" .\"'")
    morceaux, pos = [], None
    while c:
        if len(morceaux) == morceaux_max:
            return None
        debut = 0 if pos is None else pos
        k = 0
        while k < len(c) and comp.find(c[:k + 1], debut) != -1:
            k += 1
        if k < len(c):  # finir sur un mot entier, et plutôt sur une ponctuation proche (« portée : … à 0,40 »)
            coupe = c.rfind(" ", 0, k + 1)
            k = coupe if coupe > 0 else k
            p = max(c.rfind(x, 0, k) for x in (":", ";", "."))
            if p > 0 and k - p < 12:
                k = p + 1
        m = c[:k].strip()
        i = comp.find(m, debut)
        if len(m) < mini or i == -1 or (pos is not None and i - pos > saut_max):
            return None
        morceaux.append(base[i:i + len(m)])
        pos = i + len(m)
        c = c[k:].strip(" ,;.-")
    return " … ".join(morceaux) if len(morceaux) > 1 else None

