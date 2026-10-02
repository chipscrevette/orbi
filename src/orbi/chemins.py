"""Les chemins du projet, en un seul endroit. Tout le code passe par ici : aucun module ne recompose la racine à la main.

  orbi/
  ├─ donnees/              le règlement découpé, l'index de recherche, les zones du PLU, le cache des API publiques
  ├─ bancs/jeux/           les questions des bancs d'essai (mise au point, bancs cachés scellés)
  ├─ bancs/resultats/      les passages notés et leurs traces
  └─ docs/schemas/         les schémas Excalidraw (.excalidraw + .png)
"""
import os

RACINE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DONNEES = os.path.join(RACINE, "donnees")
BANCS = os.path.join(RACINE, "bancs")
JEUX = os.path.join(BANCS, "jeux")
RESULTATS = os.path.join(BANCS, "resultats")
TRACES = os.path.join(RESULTATS, "traces")
SCHEMAS = os.path.join(RACINE, "docs", "schemas")
