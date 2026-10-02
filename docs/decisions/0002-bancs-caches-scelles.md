# 0002 · On ne se chiffre que sur un banc caché, scellé

*Décidé le 27 septembre 2026 · statut : en place*

## Contexte
Le banc de mise au point sert à corriger l'agent : chaque correction apprend un peu ses questions. 80 % de verdicts justes en
mise au point sont devenus 60 % sur 20 questions neuves.

## Décision
- Deux sortes de bancs : la **mise au point** (on corrige dessus) et les **bancs cachés** (on ne corrige jamais dessus).
- Les réponses attendues d'un banc caché sont écrites **avant** tout passage, avec leurs citations vérifiées par le code.
- Les questions et le code de l'agent sont **scellés par SHA-256** avant le passage (`orbi.evaluation.scellement`), et une copie
  du code figé est archivée à côté du scellé.
- **Un seul passage** par agent, noté par le même code. Les règles particulières (panne d'API rejouée…) sont écrites avant la
  lecture des résultats (`bancs/jeux/questions-cachees-2.regles.txt`).
- Un banc caché lu devient connu : la version suivante de l'agent demande un banc neuf.

## Conséquences
- \+ Des chiffres publiables, vérifiables par un tiers (empreintes, traces, rejeu sans modèle).
- − Écrire 40 questions étiquetées, sur des parcelles jamais vues, prend du temps ; deux étiquettes du 2e banc se sont
  révélées discutables (parcelles à cheval sur deux zones) : désormais, chaque parcelle est vérifiée zone par zone.
