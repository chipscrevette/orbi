# 0004 · L'organisation des dossiers et la règle de dépendance

*Décidé le 2 octobre 2026 · statut : en place*

## Contexte
Le prototype tenait dans un paquet plat (`plu/`, 20 modules), des scripts épars (`outils/`, 26 fichiers) et des tests lancés à
la main. Pour devenir une application (un chatbot), il fallait des frontières nettes.

## Décision
- Un paquet `orbi` en *src layout*, découpé en couches : `domaine` (règles, contrôle, décision, fiche : sans réseau ni
  modèle), `reglement` (le texte et la recherche), `outils` (API publiques), `modele` (client du modèle local), `agent`
  (orchestration), `evaluation` (bancs, rejeu, scellé).
- **Règle de dépendance** : le domaine ne dépend que du règlement ; seul l'agent parle aux outils et au modèle ; l'évaluation
  dépend de l'agent, jamais l'inverse.
- Les services lourds (modèle, embeddings) sont des processus à part (`services/`), appelés en HTTP local.
- Tous les chemins passent par `orbi/chemins.py`.
- Tests au format pytest : `tests/unitaires`, `tests/mutations`, `tests/integration` (rejeu des passages enregistrés).

## Comment on a vérifié que rien n'a changé
La migration est une **copie** (l'ancien dossier reste intact) avec imports et chemins réécrits, puis trois passages
enregistrés ont été rejoués sans modèle : 40/40, 27/30 et 28/30 identiques, les écarts étant exactement ceux, connus et datés,
d'avant la migration. Ce rejeu est devenu un test d'intégration permanent.
