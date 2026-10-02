# 0001 · Le modèle lit, le code décide

*Décidé le 2 octobre 2026 · statut : en place (v3), à renforcer (v4)*

## Contexte
Au premier banc caché (20 questions jamais vues, 27 septembre), l'agent retrouvait le bon article, le citait mot pour mot,
puis concluait l'inverse : « oui sous conditions » pour un abri à 0,5 m de la limite, là où l'article UD 7 impose la limite
ou 3 m. 12 verdicts justes sur 20 et 4 contresens. Lire une règle et la comparer au projet sont deux métiers différents.

## Décision
- Le modèle (K2 Horizon 7B, local) remplit une **grille** : une ligne par règle, avec la phrase exacte, sa nature, si elle
  vaut ici, les chiffres. **Aucun verdict.**
- Le code **contrôle** chaque ligne : la citation existe-t-elle mot pour mot ? la phrase vise-t-elle ce secteur ? les chiffres
  viennent-ils de la question (pas des limites de la règle) ? Il **compare lui-même** les nombres.
- Une **table de décision** en Python pur tire le verdict ; elle se teste sans modèle.
- La **fiche** (le texte de la réponse) est composée à partir du verdict : elle ne peut plus le contredire.
- Le **verrou de zone** (une maison neuve en zone Ncu…) décide avant tout, sans appeler le modèle.

## Conséquences
- \+ Chaque réponse est traçable ligne par ligne ; chaque erreur se rattache à une étape ; le cœur est testé (décision 100 %).
- \+ Les « oui » trop permissifs sont divisés par deux sur le 2e banc caché (9 → 4).
- − Le code ne vaut que ce qu'on lui donne : au 2e banc caché, 27/40 contre 29/40 pour l'ancien agent. Le modèle pose mal
  les pourcentages, oublie la ligne décisive ou applique une règle hors champ. D'où la v4 : les chiffres et l'applicabilité
  passent dans le code (`labo/vitesse/PLAN-v4.md`).
