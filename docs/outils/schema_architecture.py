"""Le schéma d'architecture d'Orbi (Excalidraw) : docs/schemas/orbi-architecture.excalidraw ; le PNG se fait avec rendre.py.
Les couches du paquet, qui parle à qui, ce qui tourne sur la machine, ce qui sort vers les API publiques, et ce qui est testé.
Les chiffres des tests viennent des arguments (pour ne jamais afficher un chiffre périmé) :
  uv run python docs/outils/schema_architecture.py <tests unitaires> <couverture %> <rejeux identiques>"""
import os
import sys
import textwrap

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from excali import BLEU, GRIS, GRISTEXTE, JAUNE, ORANGE, VERT, VIOLET, Schema  # noqa: E402
from orbi.chemins import SCHEMAS  # noqa: E402

TESTS, COUVERTURE, REJEUX = (sys.argv[1:4] + ["?", "?", "?"])[:3]


def c(t, n=40):
    return "\n".join("\n".join(textwrap.wrap(l, n)) for l in t.split("\n"))


s = Schema()
s.texte(60, 30, 2300, "Orbi · l'architecture", 44)
s.texte(60, 96, 2300, "Le modèle lit, le code décide. Le domaine ne connaît ni le réseau ni le modèle : tout ce qui juge se teste "
        "sans carte graphique.", 22, "#1971c2")

# ---------------------------------------------------------------- la question
q = s.carte(60, 230, 380, 190, "Une question", c("« Puis-je poser un abri de 8 m² à 50 cm du mur du voisin, 5 impasse Monnier "
                                                  "à Biarritz ? »", 34), GRIS, 26, 17)

# ---------------------------------------------------------------- le paquet orbi
s.cadre(500, 170, 1160, 860, GRIS, pointille=True)
s.texte(520, 180, 600, "src/orbi · le paquet", 22, GRISTEXTE)
ag = s.carte(540, 230, 1080, 190, "agent/ · l'orchestration",
             c("tri de la question → faits de la parcelle → articles à lire → verrou de zone → grille remplie par le modèle → "
               "contrôle → décision → fiche. historique.py (l'agent d'origine) et grille.py (le modèle lit, le code décide).", 96),
             VIOLET, 26, 17)
do = s.carte(540, 490, 520, 250, "domaine/ · juger",
             c("schemas (la grille) · controle (preuve, secteur, chiffres) · decision (la table) · fiche (le texte sort du verdict) · "
               "verrou de zone · exclusions · demarche (déclaration ou permis, délai). Sans réseau, sans modèle.", 50), VERT, 26, 17)
re_ = s.carte(1100, 490, 520, 250, "reglement/ · le texte",
              c("donnees : 189 articles du PLU de Biarritz, citations vérifiées mot pour mot, page exacte · recherche : mots (BM25) "
                "+ sens (bge-m3), fusionnés · savoir : textes nationaux vérifiés.", 50), BLEU, 26, 17)
ou = s.carte(540, 800, 520, 200, "outils/ · les faits",
             c("adresse → parcelle → zone du PLU → prescriptions et servitudes, avec un cache disque : un banc rejoué ne refait "
               "aucune requête.", 50), BLEU, 26, 17)
mo = s.carte(1100, 800, 520, 200, "modele/ · le client du modèle",
             c("cerveau : appel HTTP local, réponse JSON imposée · analyse : la consigne de la grille (aucun verdict demandé).", 50),
             VIOLET, 26, 17)
s.fleche([(440, 325), (540, 325)], q, ag)
s.fleche([(800, 420), (800, 490)], ag, do)
s.fleche([(1360, 420), (1360, 490)], ag, re_)
s.fleche([(620, 420), (620, 445), (520, 445), (520, 900), (540, 900)], ag, ou)
s.fleche([(1540, 420), (1540, 445), (1640, 445), (1640, 900), (1620, 900)], ag, mo)
s.fleche([(1060, 615), (1100, 615)], do, re_, pointille=True)

# ---------------------------------------------------------------- ce qui tourne sur la machine, ce qui sort
s.texte(1740, 180, 600, "Sur la machine", 22, GRISTEXTE)
k2 = s.carte(1740, 230, 560, 170, "services/k2 · port 11500",
             c("K2 Horizon 7B, quantifié en 4 bits, sur une carte graphique de 12 Go. Aucun modèle distant.", 50), ORANGE, 24, 17)
em = s.carte(1740, 430, 560, 150, "services/embeddings · port 11600",
             c("bge-m3 : le sens des questions et des articles.", 50), ORANGE, 24, 17)
s.fleche([(1620, 950), (1680, 950), (1680, 315), (1740, 315)], mo, k2)
s.fleche([(1620, 560), (1700, 560), (1700, 505), (1740, 505)], re_, em)
api = s.carte(1740, 640, 560, 190, "API publiques de l'État, sans clé",
              c("Géoplateforme (adresse) · API Carto : cadastre et Géoportail de l'Urbanisme (zones, prescriptions, servitudes).", 50),
              GRIS, 24, 17, pointille=True)
s.fleche([(1060, 990), (1060, 1010), (1720, 1010), (1720, 735), (1740, 735)], ou, api, pointille=True)

# ---------------------------------------------------------------- la mesure
s.texte(60, 1080, 1200, "La mesure : ce qui prouve que ça marche", 22, GRISTEXTE)
ev = s.carte(60, 1130, 520, 210, "evaluation/ · bancs",
             c("notation des passages · rejeu sans modèle · scellé SHA-256 des questions et du code · pages de rapport.", 46),
             JAUNE, 26, 17)
ba = s.carte(620, 1130, 520, 210, "bancs/ · les questions",
             c("mise au point : 30 (on corrige dessus) · cachés : 20 puis 40, scellés avant le passage, passés une seule fois.", 46),
             JAUNE, 26, 17)
tu = s.carte(1180, 1130, 360, 210, f"{TESTS} tests unitaires",
             c(f"sans modèle ni réseau ; couverture {COUVERTURE} % ; l'agent entier tourne avec un faux modèle.", 32), VERT, 24, 17)
tm = s.carte(1580, 1130, 340, 210, "7 pannes injectées",
             c("on casse le moteur de décision exprès : les tests les détectent toutes.", 30), VERT, 24, 17)
ti = s.carte(1960, 1130, 340, 210, f"{REJEUX} rejeux",
             c("les passages enregistrés, rejoués sans modèle, redonnent les mêmes réponses.", 30), VERT, 24, 17)
s.fleche([(560, 1130), (560, 1052), (470, 1052), (470, 380), (540, 380)], ev, ag, pointille=True)  # l'évaluation fait tourner l'agent

s.texte(60, 1390, 2300, c("Dans la vie courante : un service d'urbanisme. Le stagiaire (le modèle) lit le dossier et remplit la fiche ; "
        "le chef de service (le code) vérifie chaque pièce, compare les chiffres et signe ; les archives (les bancs) gardent "
        "chaque dossier pour pouvoir le rejouer.", 150), 22, "#e8590c")

s.ecrire(os.path.join(SCHEMAS, "orbi-architecture.excalidraw"))
print("bornes", [round(v) for v in s.bornes()])
