#!/bin/sh
# Le 2e banc caché : un passage de la grille puis un passage de l'ancien agent, dans cet ordre, sans retouche du code entre les deux.
# À lancer après python -m orbi.evaluation.scellement (les empreintes du code sont alors dans bancs/jeux/questions-cachees-2.sha256).
# Historique : ce passage a été fait le 2 octobre 2026 avec l'ancienne organisation (python -m plu.banc).
cd "$(dirname "$0")/.." || exit 1
export PYTHONIOENCODING=utf-8 PYTHONUNBUFFERED=1 UV_CACHE_DIR=/d/tools/uv-cache
uv run --no-sync orbi-banc --grille --cache2 > bancs/resultats/banc-cache2-grille.log 2>&1
uv run --no-sync orbi-banc --cache2 > bancs/resultats/banc-cache2-historique.log 2>&1
echo "passages terminés"
