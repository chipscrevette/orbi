"""Le point d'étape d'Orbi (Excalidraw) : ce qui marche, ce qui est en cours, ce qui reste, avec un vrai exemple.
docs/schemas/orbi-etat-AAAA-MM-JJ.excalidraw ; le PNG se fait avec rendre.py.
  uv run python docs/outils/schema_etat.py"""
import os
import sys
import textwrap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from excali import BLEU, GRIS, GRISTEXTE, JAUNE, VERT, Schema  # noqa: E402
from orbi.chemins import SCHEMAS  # noqa: E402

DATE = "2026-10-02"


def c(t, n=62):
    return "\n".join("\n".join(textwrap.wrap(l, n)) for l in t.split("\n"))


s = Schema()
s.texte(60, 30, 2300, "Orbi · où on en est (2 octobre 2026)", 44)
s.texte(60, 96, 2300, "Oui, ça marche : une vraie question, jamais vue, répondue en 69 s sur la carte graphique de la machine. "
        "Pas encore assez fiable pour se passer d'un humain.", 22, "#1971c2")

COLONNES = [
    (60, "Ça marche", VERT, [
        ("L'agent répond", "adresse → parcelle → zone du PLU → articles → verdict, citations vérifiées mot à mot, démarche "
                           "et délai. 100 % local : K2 sur une RTX 3060."),
        ("Le serveur local", "l'application lui pose la question ; chaque étape revient en direct : tri 9 s, terrain 4 s, "
                             "articles, grille 55 s, contrôle, verdict."),
        ("Le filet de sécurité", "1 078 tests et 3 rejeux, 88 % du code couvert : 25 vrais défauts trouvés par les tests "
                                 "et corrigés le 2 octobre."),
        ("Le dépôt GitHub", "github.com/chipscrevette/orbi : le code, les tests, les bancs scellés, la documentation."),
    ]),
    (840, "En cours", JAUNE, [
        ("L'interface", "React + TypeScript : la maquette reproduite, les étapes qui se cochent en direct, la carte des "
                        "zones, les règles citées cliquables."),
        ("Le lancement", "Electron démarre le serveur local tout seul ; fenêtre sans cadre, icône, installateur Windows. "
                         "Il manque une commande : npm install."),
        ("La démo en ligne", "le même écran publié sur GitHub Pages rejoue 8 vraies réponses enregistrées : Orbi se montre "
                             "sans carte graphique."),
        ("La mascotte", "le rendu 3D de la brique bleue, à poser dans l'application à la place du dessin provisoire."),
    ]),
    (1620, "À faire", GRIS, [
        ("La fiabilité", "27/40 sur le banc caché, 6 contresens. Plan v4 : outils locaux, chiffres calculés par le code, "
                         "filtres d'applicabilité, puis un 3e banc caché."),
        ("La faisabilité", "deux parcelles : ce qu'on peut y construire, comparé, avec un plan."),
        ("Apprendre des retours", "un avis d'utilisateur relu devient un cas de test, puis une règle : jamais un "
                                  "apprentissage sans contrôle."),
        ("La vitrine", "la page portfolio et le film de présentation (brag)."),
    ]),
]
for x, titre, couleur, cartes in COLONNES:
    s.texte(x, 170, 720, titre, 28, GRISTEXTE)
    for i, (t, detail) in enumerate(cartes):
        s.carte(x, 225 + i * 190, 720, 170, t, c(detail), couleur, 24, 17)

ex = s.carte(60, 1010, 2280, 210, "Un vrai exemple, posé à l'application le 2 octobre",
             c("« Je veux construire une véranda de 15 m² sur ma maison au 10 rue Gambetta à Biarritz. Est-ce possible ? » → "
               "parcelle BC 0074 (90 m²), zone UAs, site patrimonial remarquable → « oui, sous conditions », en 69 s. "
               "Le défaut visible : la réponse cite aussi une exclusion qui ne la concerne pas (les piscines). C'est exactement "
               "le bruit que les filtres d'applicabilité de la v4 doivent retirer.", 190), BLEU, 24, 18)

s.texte(60, 1270, 2300, c("Dans la vie courante : un restaurant. La salle (l'application) prend la commande ; le passe (le serveur "
        "local) annonce chaque plat en préparation ; en cuisine, le commis (K2) prépare et le chef (le code) goûte et signe ; le "
        "garde-manger (le PLU, le cadastre) fournit. La cuisine et le passe tournent ; la salle se monte.", 165), 22, "#e8590c")

s.ecrire(os.path.join(SCHEMAS, f"orbi-etat-{DATE}.excalidraw"))
print("bornes", [round(v) for v in s.bornes()])
