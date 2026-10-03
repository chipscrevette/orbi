"""La fiche du terrain : quand la question ne porte sur aucun projet (« que faut-il savoir sur cette adresse ? »), Orbi ne
donne pas de verdict. Il dit ce que le PLU fixe sur ce terrain, thème par thème, avec une phrase exacte du règlement pour
chacun. Tout est composé par le code, sans modèle : rien à inventer, rien à vérifier après coup."""
import re

# les thèmes de la fiche : l'article du chapitre de la zone, son titre, la recherche qui trouve le bon passage
THEMES = [
    ("6", "implantation par rapport aux voies", "implantation par rapport aux voies et emprises publiques recul alignement"),
    ("7", "implantation par rapport aux voisins", "implantation par rapport aux limites séparatives distance"),
    ("9", "emprise au sol", "emprise au sol maximale"),
    ("10", "hauteur", "hauteur maximale égout faîtage niveaux"),
    ("11", "clôtures", "clôtures hauteur grillage haie mur"),
]
LONGUEUR = 320


def phrases(texte):
    return [p.strip() for p in re.split(r"(?<=[.;])\s+", texte or "") if p.strip()]


def extrait(texte, longueur=LONGUEUR):
    """La phrase qui porte la règle : la première qui contient un chiffre (une distance, une hauteur, un pourcentage),
    sinon la première. Coupée à un mot près si elle est trop longue, mais jamais réécrite : elle reste mot pour mot."""
    ps = phrases(texte)
    if not ps:
        return ""
    choisie = next((p for p in ps if re.search(r"\d", p) and len(p) > 25), ps[0])
    if len(choisie) <= longueur:
        return choisie
    coupe = choisie[:longueur].rsplit(" ", 1)[0]
    return coupe.rstrip(",;:") + "…"


def nombre(x):
    return f"{x:,.0f}".replace(",", " ") if isinstance(x, (int, float)) else str(x)


def composer(faits, zone, chiffres, nb_regles):
    """Le texte de la fiche : où est le terrain, ce qui le distingue, et l'invitation à donner un projet."""
    p = (faits or {}).get("parcelle") or {}
    c = (faits or {}).get("contraintes") or {}
    terrain = f"la parcelle {p['parcelle']}" if p.get("parcelle") else "ce terrain"
    if p.get("surface_m2"):
        terrain += f" ({nombre(p['surface_m2'])} m²)"
    morceaux = [f"Pas de projet précis : voici ce que le PLU fixe pour {terrain}, en zone {zone}."]
    if c.get("site_patrimonial"):
        morceaux.append("Le terrain est dans le site patrimonial remarquable : l'Architecte des Bâtiments de France donne "
                        "son avis sur tout projet.")
    morceaux += [x[0].upper() + x[1:] + "." for x in chiffres]
    if nb_regles:
        morceaux.append("Les règles principales sont ci-dessous, avec leur page.")
    morceaux.append("Dites-moi votre projet (abri de jardin, extension, piscine, clôture…) et je vérifie s'il passe.")
    return " ".join(morceaux)


def a_retenir(faits):
    """Ce qui touche la parcelle en plus de la zone : servitudes, prescriptions, hauteurs fixées au plan."""
    c = (faits or {}).get("contraintes") or {}
    out = [f"servitude : {s}" for s in c.get("servitudes") or []]
    out += [f"prescription : {s}" for s in c.get("prescriptions") or []]
    out += [f"hauteur fixée au plan : niveau « {h} »" for h in c.get("hauteurs_au_plan") or []]
    return out
