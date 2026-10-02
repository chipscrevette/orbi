"""La feuille de route d'Orbi (Excalidraw) : docs/schemas/orbi-feuille-de-route.excalidraw ; le PNG se fait avec rendre.py.
Sept étapes sur une orbite (Orbi, comme orbite) : chacune livre du code testé, des schémas et une mesure.
Usage : uv run python docs/outils/schema_feuille_de_route.py [numéro de l'étape en cours]"""
import os
import sys
import textwrap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from excali import BLEU, GRIS, GRISTEXTE, ORANGE, VERT, Schema  # noqa: E402
from orbi.chemins import SCHEMAS  # noqa: E402

EN_COURS = int(sys.argv[1]) if len(sys.argv) > 1 else 2  # les étapes avant sont faites


def c(t, n=26):
    return "\n".join("\n".join(textwrap.wrap(l, n)) for l in t.split("\n"))


ETAPES = [
    ("Fondations", "dossiers en couches, tests pytest, rejeu anti-régression, schémas, fiches de décision"),
    ("Fiabilité", "zone décidée en local, chiffres calculés par le code, filtres d'applicabilité, 3e banc caché"),
    ("Le chatbot", "conversation, questions de relance, réponses en flux, carte de la parcelle"),
    ("Le design", "Orbi, la mascotte ; une direction artistique tirée du sujet ; maquettes validées avant le code"),
    ("La faisabilité", "plusieurs parcelles : le volume constructible de chacune, comparé, avec un plan"),
    ("Les retours", "👍 / 👎 et « la bonne réponse était… », relus, devenus cas de test et règles"),
    ("La vitrine", "la page portfolio et le film de présentation (brag)"),
]

s = Schema()
s.texte(60, 30, 2300, "Orbi · la feuille de route", 44)
s.texte(60, 96, 2300, "Sept étapes. Chacune livre du code testé, ses schémas et une mesure ; aucune ne commence avant que la "
        "précédente tienne ses chiffres.", 22, "#1971c2")

pas, x0, y_orbite = 330, 130, 270
# l'orbite : une ligne qui passe par les sept étapes
points = [(x0 + 70, y_orbite)] + [(x0 + k * pas + 70, y_orbite + (40 if k % 2 else -10)) for k in range(1, 7)]
for k in range(6):
    xa, ya = points[k]
    xb, yb = points[k + 1]
    s.fleche([(xa + 70, ya), (xb - 70, yb)], pointille=k + 1 >= EN_COURS, couleur="#868e96")
for k, (titre, detail) in enumerate(ETAPES, 1):
    fait, courant = k < EN_COURS, k == EN_COURS
    col = VERT if fait else ORANGE if courant else GRIS
    x, y = points[k - 1]
    s.rond(x - 70, y - 70, 140, 140, col, str(k), 44)
    statut = "fait" if fait else "en cours" if courant else "à venir"
    s.carte(x - 150, y + 110, 300, 290, titre, c(detail + "\n\n" + statut, 28), col if (fait or courant) else BLEU, 26, 17,
            pointille=not (fait or courant))

s.texte(60, 760, 2300, c("Dans la vie courante : un satellite qui fait le tour de sa planète. À chaque tour, la même vérification : "
                          "les tests, le rejeu, le banc. On ne change d'orbite qu'avec des chiffres qui tiennent.", 170),
        22, "#e8590c")
s.ecrire(os.path.join(SCHEMAS, "orbi-feuille-de-route.excalidraw"))
print("bornes", [round(v) for v in s.bornes()])
