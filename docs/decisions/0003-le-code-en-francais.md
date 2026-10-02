# 0003 · Le code est écrit en français

*Décidé le 2 octobre 2026 · statut : en place*

## Contexte
Le métier est français et précis : PLU, emprise au sol, unité foncière, déclaration préalable, site patrimonial remarquable.
Les traductions anglaises sont approximatives ; le code existant (2 600 lignes) était déjà en français.

## Décision
Noms de modules, de fonctions, de variables, docstrings et commentaires en français, sans accents dans les identifiants
(`decider`, `controler`, `emprise_exclue`). Les termes techniques sans équivalent restent tels quels (`schema`, `pipeline`).

## Conséquences
- \+ Le code se lit avec le vocabulaire du règlement ; un instructeur d'urbanisme peut suivre une règle du texte au test.
- − Moins standard pour une équipe internationale : le README et les schémas expliquent l'architecture sans lire le code.
