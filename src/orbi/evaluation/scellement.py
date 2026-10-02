"""Fige le code de l'agent avant un passage du banc caché : l'empreinte SHA-256 de chaque fichier est ajoutée au fichier de scellé,
sous l'empreinte des questions. Qui modifie une ligne de code après coup change l'empreinte : le passage n'est plus celui qu'on a scellé.
Une copie du code figé est gardée à côté du scellé : après un découpage ou une retouche, les empreintes restent vérifiables.
Usage : uv run python -m orbi.evaluation.scellement bancs/jeux/questions-cachees-N.sha256"""
import hashlib
import os
import shutil
import sys
from datetime import datetime

from orbi.chemins import RACINE

# les pages de rapport ne sont pas l'agent ; la notation (notation.py), elle, est scellée
EXCLUS = (os.path.join("src", "orbi", "evaluation", "pages"),)
DONNEES_SCELLEES = ["services/k2/serveur_k2.py", "donnees/index-recherche.json", "donnees/articles.json", "donnees/zones-biarritz.geojson"]


def fichiers():
    """Les fichiers dont l'empreinte est scellée : tout le code du paquet orbi (hors pages de rapport), le serveur du modèle, les données."""
    out = []
    for dossier, _, noms in os.walk(os.path.join(RACINE, "src", "orbi")):
        rel = os.path.relpath(dossier, RACINE)
        if "__pycache__" in rel or any(rel.startswith(x) for x in EXCLUS):
            continue
        out += [os.path.join(rel, n).replace(os.sep, "/") for n in noms if n.endswith(".py")]
    return sorted(out) + [f for f in DONNEES_SCELLEES if os.path.exists(os.path.join(RACINE, f))]


def empreinte(chemin):
    return hashlib.sha256(open(os.path.join(RACINE, chemin), "rb").read()).hexdigest()


def main(scelle):
    chemin = os.path.join(RACINE, scelle)
    existant = open(chemin, encoding="utf-8").read().rstrip("\n")
    assert "code de l'agent figé" not in existant, "le code est déjà figé dans ce scellé : on ne le fige pas deux fois"
    liste = fichiers()
    lignes = [f"{empreinte(f)}  {f}" for f in liste]
    texte = (existant + f"\n\ncode de l'agent figé le {datetime.now():%Y-%m-%d %H:%M}, avant le passage du banc caché :\n"
             + "\n".join(lignes) + "\n")
    open(chemin, "w", encoding="utf-8", newline="\n").write(texte)
    copie = os.path.join(os.path.dirname(chemin), "code-fige-" + os.path.basename(scelle).replace(".sha256", ""))
    for f in liste:
        if f.startswith(("src/", "services/")):  # le code, y compris le serveur du modèle ; pas les données
            os.makedirs(os.path.dirname(os.path.join(copie, f)), exist_ok=True)
            shutil.copy2(os.path.join(RACINE, f), os.path.join(copie, f))
    print(len(lignes), "fichiers figés dans", scelle, "; copie du code dans", os.path.relpath(copie, RACINE))


if __name__ == "__main__":
    main(sys.argv[1])
