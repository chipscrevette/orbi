# La documentation d'Orbi

## Les schémas (`schemas/`)
Chaque schéma existe en `.excalidraw` (à ouvrir et retoucher sur excalidraw.com) et en `.png`. Ils sont générés par du code
(`outils/`), pour que les chiffres affichés viennent des vrais résultats et ne vieillissent pas sans qu'on le voie.

| schéma | ce qu'il montre |
|---|---|
| `orbi-architecture` | les couches du paquet, qui parle à qui, ce qui tourne sur la machine, ce qui est testé |
| `grille-v1` | le chemin d'une question « puis-je faire X ? » : le modèle remplit la grille, le code contrôle, décide et écrit |
| `cadrage-v1`, `cadrage-v2` | le cadrage du projet et du premier banc d'essai (septembre 2026) |

Refaire un schéma : `uv run python docs/outils/schema_architecture.py <tests> <couverture> <rejeux>` puis
`uv run python docs/outils/rendre.py docs/schemas/orbi-architecture.excalidraw` (Chrome et Internet nécessaires pour le rendu).

## Les décisions (`decisions/`)
Une fiche par choix d'architecture : le contexte, la décision, ses conséquences, et comment on l'a mesurée.

1. [Le modèle lit, le code décide](decisions/0001-le-modele-lit-le-code-decide.md)
2. [On ne se chiffre que sur un banc caché, scellé](decisions/0002-bancs-caches-scelles.md)
3. [Le code est écrit en français](decisions/0003-le-code-en-francais.md)
4. [L'organisation des dossiers et la règle de dépendance](decisions/0004-organisation-des-dossiers.md)
5. [100 % local](decisions/0005-cent-pour-cent-local.md)
