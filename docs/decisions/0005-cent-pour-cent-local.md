# 0005 · 100 % local

*Décidé le 26 septembre 2026 · statut : en place*

## Contexte
Une question d'urbanisme contient une adresse et un projet personnel. Le règlement, lui, est public.

## Décision
- Le modèle de langage (K2 Horizon 7B, quantifié en 4 bits) et les embeddings (bge-m3) tournent sur la machine, sur une carte
  graphique de 12 Go. Aucun modèle distant, aucune clé d'API.
- Seules sortent les requêtes aux **API publiques sans clé** de l'État : adresse (Géoplateforme), cadastre et Géoportail de
  l'Urbanisme (API Carto). Leurs réponses sont gardées en cache sur disque : un banc rejoué ne refait aucune requête.

## Conséquences
- \+ Confidentialité, coût nul à l'usage, résultats rejouables.
- − La vitesse dépend de la carte graphique (16 jetons/s : 30 à 60 s par question aujourd'hui) ; la vitesse viendra du harnais
  (moins de jetons demandés au modèle), pas d'un modèle distant.
