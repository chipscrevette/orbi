"""Le schéma de la grille (Excalidraw) : docs/schemas/grille-v1.excalidraw ; le PNG se fait avec docs/outils/rendre.py.
Le modèle lit et remplit une grille ; le code vérifie, décide et écrit. Un exemple réel (C01) coule sous les quatre étapes."""
import json
import os
import sys
import textwrap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from excali import *  # noqa: E402,F401,F403
from orbi.chemins import SCHEMAS  # noqa: E402


def c(t, n=34):
    return "\n".join("\n".join(textwrap.wrap(l, n)) for l in t.split("\n"))


s = Schema()
s.texte(60, 30, 2200, "Orbi · la grille : le modèle lit, le code juge", 40)
s.texte(60, 92, 2250, "Au banc caché, le modèle retrouvait la bonne règle, la citait exactement, puis concluait l'inverse. "
        "Lire une règle et la comparer au projet sont deux métiers : le premier va au modèle, le second à une table de décision.",
        21, "#1971c2")

# ---------------------------------------------------------------- l'entrée, inchangée
W, H, G = 340, 150, 40
xs = [60 + k * (W + G) for k in range(6)]
s.texte(60, 150, 900, "Avant la grille : l'entrée, comme avant", 22, GRISTEXTE)
entree = [("Question", c("« Je veux poser un abri de 8 m² à 50 cm du mur du voisin, au 5 impasse Monnier »", 30), GRIS),
          ("Tri · modèle", c("lit la question : projet, surfaces, sujet, adresse", 30), VIOLET),
          ("Outils · code", c("adresse → parcelle → zone UD → servitudes (API publiques, en cache)", 30), BLEU),
          ("Périmètre · code", c("hors Biarritz, taxes, recours : réponse sans modèle", 30), BLEU),
          ("Démarche · code", c("rien, déclaration préalable ou permis, avec son délai", 30), BLEU),
          ("Articles · code", c("la recette du projet + la recherche (mots et sens) : 12 passages lettrés A, B, C…", 30), BLEU)]
prec = None
for k, (t, d, col) in enumerate(entree):
    e = s.carte(xs[k], 190, W, H, t, d, col, 24, 17)
    if prec:
        s.fleche([(xs[k] - G, 265), (xs[k], 265)], prec, e)
    prec = e

# ---------------------------------------------------------------- la grille, en quatre temps (plus le verrou)
y1 = 470
s.texte(60, y1 - 40, 1200, "Le chemin « puis-je faire X ? » : quatre temps", 22, GRISTEXTE)
s.arrow = s.fleche([(xs[5] + W / 2, 340), (xs[5] + W / 2, 400), (xs[1] + W / 2 + 20, 400), (xs[1] + W / 2 + 20, y1 + 5)], prec, None)
v = s.carte(xs[0], y1, W, 200, "Verrou de zone · code", c("maison neuve en Ncu, UG… : le règlement décide seul, sans appeler le modèle.", 30), ORANGE, 24, 17)
gr = s.carte(xs[1], y1, W + 110, 200, "1 · La grille · modèle",
             c("une ligne par règle : extrait exact, nature, vaut-elle ici ?, chiffres, statut. AUCUN verdict.", 38), VIOLET, 24, 17)
x2 = xs[1] + W + 110 + G
co = s.carte(x2, y1, W + 110, 200, "2 · Le contrôle · code",
             c("preuve : la phrase existe-t-elle mot pour mot ? secteur : la règle vise-t-elle cette parcelle ? "
               "nombres : Python compare lui-même.", 38), BLEU, 24, 17)
x3 = x2 + W + 110 + G
de = s.carte(x3, y1, W + 110, 200, "3 · La décision · code",
             c("une table testée sans modèle : règle violée → non · fait décisif manquant → impossible à dire · "
               "rien de prouvé → pas d'autorisation.", 38), VERT, 24, 17)
x4 = x3 + W + 110 + G
fi = s.carte(x4, y1, W + 20, 200, "4 · La fiche · code",
             c("le texte sort du verdict : il ne peut plus se contredire.", 30), BLEU, 24, 17)
s.fleche([(xs[1] + W + 110, y1 + 100), (x2, y1 + 100)], gr, co)
s.fleche([(x2 + W + 110, y1 + 100), (x3, y1 + 100)], co, de)
s.fleche([(x3 + W + 110, y1 + 100), (x4, y1 + 100)], de, fi)

# ---------------------------------------------------------------- l'exemple C01, de haut en bas sous chaque étape
y2 = y1 + 260
s.texte(60, y2 + 10, 330, "Le même cas, pas à pas\n(banc caché C01 : l'ancien\nagent répondait « oui sous\nconditions »)", 20, GRISTEXTE)
ex = [(gr, xs[1], W + 110, "UD 7 · limite · « sur la limite ou à au moins 3 mètres »\nseuil 3 m · valeur du projet 0,5 m", VIOLET),
      (co, x2, W + 110, "0,5 m < 3 m\nstatut recalculé par le code : violée\n(le modèle avait écrit « respectée »)", BLEU),
      (de, x3, W + 110, "une règle violée, aucune exception applicable\n→ NON", VERT),
      (fi, x4, W + 20, "« Non, ce projet n'est pas possible. La règle impose la limite ou 3 m (UD 7) — votre abri est à 0,5 m. »", BLEU)]
for src, x, w, t, col in ex:
    e = s.carte(x, y2, w, 130, "", c(t, 42 if w > 400 else 30), col, 4, 17)
    s.fleche([(x + w / 2, y1 + 200), (x + w / 2, y2)], src, e, pointille=True)

# ---------------------------------------------------------------- les tests, sans modèle
y3 = y2 + 210
s.texte(60, y3 - 40, 1500, "Du code qu'on teste : tout ce qui n'est pas le modèle se rejoue en une seconde", 22, GRISTEXTE)
tests = [("56 cas de logique", "décision : permis, interdit, information manquante, zones strictes, portée des exceptions"),
         ("41 cas de contrôle", "de vrais articles du PLU : citation inventée, secteur, chiffre recopié de la règle, fait décisif"),
         ("7 pannes injectées", "on casse le moteur exprès : les tests en détectent 7 sur 7"),
         ("Rejeu : 40 sur 40", "le banc caché rejoué sans modèle sur les réponses enregistrées redonne exactement les mêmes verdicts")]
wt = (2280 - 3 * 30) // 4
for k, (t, d) in enumerate(tests):
    s.carte(60 + k * (wt + 30), y3, wt, 130, t, c(d, 44), VERT, 24, 17)

y4 = y3 + 170
s.texte(60, y4, 2250, "Dans la vie courante : le modèle est le stagiaire qui lit le dossier et remplit la fiche ; le code est le chef de service "
        "qui vérifie chaque pièce, compare les chiffres et signe.", 22, "#e8590c")

doc = s.ecrire(os.path.join(SCHEMAS, "grille-v1.excalidraw"))
m = open(os.path.join(ICI, "_modele-rendu.html"), encoding="utf-8").read()
d0 = m.index("const data = ") + len("const data = ")
f0 = m.index(";\ntry {")
open(os.path.join(ICI, "rendu-grille.html"), "w", encoding="utf-8").write(m[:d0] + json.dumps(doc, ensure_ascii=False) + m[f0:])
print("bornes", [round(v) for v in s.bornes()])
