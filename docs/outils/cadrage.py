"""La planche de cadrage v2 (Excalidraw) : cadrage/cadrage-v2.excalidraw + outils/rendu-cadrage.html (pour le PNG).
v2 : la démarche (rien, déclaration préalable ou permis) entre dans le périmètre ; le banc d'essai part de vraies questions."""
import json, os, sys, textwrap
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from excali import *
from orbi.chemins import JEUX, SCHEMAS  # noqa: E402

Q = json.load(open(os.path.join(JEUX, "questions-v2.json"), encoding="utf-8"))
n_vraies = sum(x["origine"] == "vraie question" for x in Q)
n_hors = sum(x["nature"] == "hors périmètre" for x in Q)


def c(t, n=54):
    return "\n".join("\n".join(textwrap.wrap(l, n)) for l in t.split("\n"))


s = Schema()
s.texte(60, 30, 1800, "Assistant PLU · cadrage v2", 40)
s.texte(60, 90, 2250, "La mission : répondre à « puis-je construire X à cette adresse ? » en disant quelle démarche faire, "
        "en citant les articles exacts du PLU, et ce qui reste à vérifier en mairie.", 22, "#1971c2")
L, H, G = 740, 270, 30
xs = [60, 60 + L + G, 60 + 2 * (L + G)]
ys = [150, 150 + H + G, 150 + 2 * (H + G)]
cartes = [
    ("Le problème", c("Le règlement de Biarritz fait 152 pages : 13 zones, 14 articles chacune, des renvois. "
                      "La zone est sur une carte, les servitudes ailleurs. Sur les forums, les gens se trompent "
                      "de règle, de commune ou de démarche."), GRIS),
    ("Pour qui", c("Un particulier qui prépare un petit projet, ou qui se demande si son voisin en a le droit.\n"
                   "En portfolio : les cabinets de conseil Data & IA (secteur public, IA qui tourne en local)."), GRIS),
    ("La réponse, toujours sous cette forme", c("1. le verdict : oui · sous conditions · non · impossible à dire\n"
                                                "2. la démarche : rien, déclaration préalable ou permis\n"
                                                "3. les règles du PLU : article, page, citation\n"
                                                "4. les contraintes de la parcelle\n"
                                                "5. ce qu'il faut vérifier en mairie"), BLEU),
    ("Dans le périmètre", c("Une commune : Biarritz, PLU en vigueur.\nSix projets : véranda, extension, piscine, abri de jardin, "
                            "clôture, surélévation.\nLes règles du PLU et la démarche (Code de l'urbanisme). "
                            "Questions du propriétaire comme du voisin."), VERT),
    ("Hors périmètre", c("Recours et contentieux · dérogations · taxes · autres communes (v2) · règles privées "
                         "(lotissement, copropriété) · prix de l'immobilier · autres projets (garage, panneaux solaires…). "
                         "Réponse : une phrase qui le dit, et vers qui se tourner."), ROUGE),
    ("Les données : ouvertes, sans aucune clé", c("API Adresse (IGN) · cadastre (API Carto) · Géoportail de l'Urbanisme : "
                                                  "zonage, prescriptions, servitudes, règlement PDF · Code de l'urbanisme "
                                                  "(Légifrance).\nMise à jour : chaque nuit, on compare la date du document publié."), GRIS),
    ("Le cerveau : K2 Horizon 7B, en local", c("Sur la carte graphique du PC (RTX 3060). Réflexion moyenne pour la réponse "
                                               "finale (environ 34 s), courte pour les étapes intermédiaires.\nChoisi sur mesure : "
                                               "sur le même cas, K2 juste, granite faux."), ORANGE),
    ("Réussi si… (le banc d'essai)", c(f"{len(Q)} questions, dont {n_vraies} vraies (forums, FAQ de mairies, avocats).\n"
                                       "Verdict juste : 26 sur 30 au moins.\nDémarche juste : 28 sur 30 au moins.\n"
                                       f"Citations inventées : zéro. Hors périmètre : {n_hors} sur {n_hors}.\n"
                                       "Moins de 60 s par question."), VIOLET),
    ("Risques et parades", c("Réponse fausse → citation obligatoire + « à vérifier en mairie ».\n"
                             "Règle d'une autre commune → ne répondre qu'avec le règlement de Biarritz.\n"
                             "Mot rare noyé → questions courtes + recherche hybride.\n"
                             "Garde-fou naïf → champs structurés vérifiés.\n"
                             "PLU modifié → veille de la date."), ROUGE),
]
for k, (titre, detail, coul) in enumerate(cartes):
    s.carte(xs[k % 3], ys[k // 3], L, H, titre, detail, coul, 26, 21)

y = ys[2] + H + 50
s.texte(60, y, 900, "Les étapes : chacune a une porte de validation", 24, ENCRE)
etapes = [("1. Cadrage", "cette planche", True), ("2. Banc d'essai", f"{len(Q)} questions, {n_vraies} vraies", True),
          ("3. Harnais", "outils, champs vérifiés", False), ("4. RAG par article", "citations exactes", False),
          ("5. Interface", "carte + réponse", False), ("6. Page portfolio", "le cas raconté", False)]
w = (2280 - 5 * 30) // 6
prec = None
for k, (t, d, fait) in enumerate(etapes):
    x = 60 + k * (w + 30)
    e = s.carte(x, y + 50, w, 110, t, ("à valider · " if fait else "") + d, ("#fff3bf", "#f08c00") if fait else BLANC, 22, 16)
    if prec:
        s.fleche([(x - 30, y + 105), (x, y + 105)], prec, e)
    prec = e

doc = s.ecrire(os.path.join(SCHEMAS, "cadrage-v2.excalidraw"))
b = s.bornes()
m = open(os.path.join(ICI, "_modele-rendu.html"), encoding="utf-8").read()
d0 = m.index("const data = ") + len("const data = ")
f0 = m.index(";\ntry {")
open(os.path.join(ICI, "rendu-cadrage.html"), "w", encoding="utf-8").write(m[:d0] + json.dumps(doc, ensure_ascii=False) + m[f0:])
print("bornes", [round(v) for v in b])
