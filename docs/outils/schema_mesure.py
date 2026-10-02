"""Le schéma « comment on mesure » (Excalidraw) : docs/schemas/orbi-mesure.excalidraw ; le PNG se fait avec rendre.py.
Les deux sortes de bancs, le scellé, le passage unique, le rejeu sans modèle, et l'histoire des chiffres (vrais résultats)."""
import os
import sys
import textwrap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from excali import BLEU, GRIS, GRISTEXTE, JAUNE, ORANGE, ROUGE, VERT, VIOLET, Schema  # noqa: E402
from orbi.chemins import SCHEMAS  # noqa: E402


def c(t, n=40):
    return "\n".join("\n".join(textwrap.wrap(l, n)) for l in t.split("\n"))


s = Schema()
s.texte(60, 30, 2300, "Orbi · comment on mesure", 44)
s.texte(60, 96, 2300, "Un agent ne se juge que sur des questions qu'il n'a jamais vues : écrites, étiquetées et scellées avant le "
        "passage, passées une seule fois.", 22, "#1971c2")

# ---------------------------------------------------------------- les deux bancs
s.texte(60, 170, 900, "Deux bancs, deux rôles", 24, GRISTEXTE)
mp = s.carte(60, 220, 520, 230, "Le banc de mise au point",
             c("30 questions réelles (forums, FAQ de mairies) transposées à Biarritz. On lit chaque échec et on corrige l'agent "
               "dessus : son score est donc flatteur.", 48), BLEU, 26, 17)
bc = s.carte(620, 220, 520, 230, "Les bancs cachés",
             c("20 puis 40 questions neuves, sur des parcelles jamais vues, en 4 groupes : permis, interdit, information "
               "manquante, zones strictes. On ne corrige jamais dessus.", 48), ORANGE, 26, 17)
s.texte(60, 470, 1080, c("Dans la vie courante : le cahier d'exercices corrigés, et l'examen sous enveloppe scellée.", 90), 20, "#e8590c")

# ---------------------------------------------------------------- le protocole
s.texte(60, 560, 900, "Le protocole d'un banc caché", 24, GRISTEXTE)
etapes = [("1 · Écrire", "les questions et les réponses attendues, citations vérifiées mot pour mot par le code", VIOLET),
          ("2 · Sceller", "empreinte SHA-256 des questions, puis du code de l'agent ; copie du code archivée", JAUNE),
          ("3 · Passer", "une fois par agent, noté par le même code ; règles d'exception écrites avant de lire", VERT),
          ("4 · Rejouer", "les traces, sans le modèle : mêmes verdicts, sinon le code a changé", BLEU)]
prec = None
for k, (t, d, col) in enumerate(etapes):
    e = s.carte(60 + k * 280, 610, 250, 210, t, c(d, 26), col, 24, 16)
    if prec:
        s.fleche([(60 + k * 280 - 30, 715), (60 + k * 280, 715)], prec, e)
    prec = e

# ---------------------------------------------------------------- l'histoire des chiffres
s.texte(1240, 170, 1100, "L'histoire des chiffres (verdicts exacts)", 24, GRISTEXTE)
lignes = [
    ("26 sept.", "mise au point, 1er passage", "14 / 30", GRIS),
    ("27 sept.", "mise au point, 4e passage (onze corrections du harnais)", "25 / 30", BLEU),
    ("27 sept.", "1er banc caché : l'écart dit ce qui avait été appris par cœur", "12 / 20 · 4 contresens", ROUGE),
    ("2 oct.", "la grille : le modèle lit, le code décide · mise au point", "25 / 30 · 0 contresens", BLEU),
    ("2 oct.", "2e banc caché · ancien agent", "29 / 40 · 9 trop permissifs", ORANGE),
    ("2 oct.", "2e banc caché · grille", "27 / 40 · 4 trop permissifs", VERT),
]
for k, (date, quoi, chiffre, col) in enumerate(lignes):
    y = 220 + k * 105
    s.texte(1240, y + 28, 120, date, 20, GRISTEXTE)
    s.carte(1370, y, 600, 88, "", c(quoi, 60), col, 4, 17)
    s.texte(2000, y + 26, 360, chiffre, 24)

s.texte(60, 880, 2300, c("Ce que la grille a changé : deux fois moins de « oui » trop permissifs, et chaque erreur se rattache "
                            "à une étape. Ce qu'elle n'a pas encore changé : le total. Le code décide bien, mais le modèle lui "
                            "donne des chiffres mal posés : la suite les fait calculer par le code.", 190), 22, "#e8590c")

s.ecrire(os.path.join(SCHEMAS, "orbi-mesure.excalidraw"))
print("bornes", [round(v) for v in s.bornes()])
