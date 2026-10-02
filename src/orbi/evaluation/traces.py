"""Retrouver la trace d'une réponse. Les passages enregistrés gardent le chemin absolu de leur trace, pris au moment du passage
(parfois dans l'ancien dossier assistant-plu) : on la cherche d'abord à cet endroit s'il est dans le projet, sinon par son nom dans
bancs/resultats/traces/."""
import os

from orbi.chemins import RACINE, TRACES


def trace_locale(chemin):
    """Le chemin d'une trace dans ce projet, ou None si elle n'existe pas."""
    if not chemin:
        return None
    if os.path.isabs(chemin) and os.path.exists(chemin):
        try:  # dans le projet, et pas dans un dossier voisin au nom proche (orbi-ancien/)
            if os.path.commonpath([os.path.normcase(chemin), os.path.normcase(RACINE)]) == os.path.normcase(RACINE):
                return chemin
        except ValueError:  # deux disques différents
            pass
    nom = os.path.basename(chemin.replace("\\", "/"))
    candidat = os.path.join(TRACES, nom)
    return candidat if os.path.exists(candidat) else None
