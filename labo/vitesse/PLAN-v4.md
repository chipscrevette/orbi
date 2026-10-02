# Plan de la v4 (écrit le 2026-10-02 pendant le 2e banc caché, mis à jour après lecture du passage de la grille)

Le code du passage est scellé (`banc-essai/questions-cachees-2.sha256`, copie dans `banc-essai/code-fige-questions-cachees-2/`).
Rien de ce qui suit n'est dans `plu/` : ni les correctifs, ni le prototype de `vitesse/`.

## Ce que le passage de la grille a montré (24/40, 6 contresens ; lu dans les traces, sans rien corriger)
16 échecs, en cinq familles. Ce n'est PAS « le modèle conclut mal » : la table de décision a presque toujours raison sur ce qu'on lui
donne ; ce qu'on lui donne est pauvre.

| famille | cas | cause |
|---|---|---|
| **API publiques muettes** (5) | D33, D34, D38, D39, D40 | « je ne trouve pas cette adresse / la zone » : le géocodeur n'a pas répondu (61 à 282 s), l'agent le dit comme si l'adresse n'existait pas. Le point choisi dans une grande parcelle (moyenne des sommets) peut aussi tomber hors de sa zone. |
| **Chiffres mal posés par le modèle** (4) | D19, D18, D02/D06 (osc juste par chance), D13 | pourcentage écrit comme surface (« seuil 0,3, valeur 0,3 »), limite recopiée comme valeur du projet (refusée à juste titre), hauteur existante prise pour hauteur du projet (9 m au lieu de 12), ligne de la limite jamais écrite (mur de 2,40 m) |
| **Article jamais lu** (1) | D20 | la recette « maison neuve » ne contient que les articles 1, 2 et 9 : la hauteur (article 10) n'est jamais donnée au modèle |
| **Règle hors champ appliquée** (2) | D08, D09 | sens inversé (« 15 m² au moins 630 m² ») + liste « parcs et espaces verts protégés » (UD 2) appliquée à une parcelle sans espace vert ; mixité sociale (4 logements ou plus) appliquée à une maison seule |
| **Limite alternative / zone stricte** (4) | D24, D25, D31, D32 (+ D29 : parcelle à cheval sur N et Nh) | la limite de 40 % (parcelle d'avant 2003) rangée « limite » et non « exception » : « non » au lieu de « impossible à dire » ; en Nh, la villa admise « sous condition d'insertion » rangée « condition » : « aucune règle » au lieu de « oui sous conditions » |

Autres constats : des questions à plus de 100 s (D21 120 s, D25 142 s, D27 147 s, D34 282 s) : réflexion qui mange les 2 400 jetons puis
nouvel essai, ou API muettes. Moyenne 65,6 s contre 36,5 s au banc de mise au point.

## Pistes, par ordre (chacune testée sans modèle, rejouée sur les sorties enregistrées, certifiée sur un banc neuf)
**P0 · Les outils d'abord** (rien ne vaut un modèle qui répond sans faits)
- `_get` : séparer « pas de réponse » de « rien trouvé » ; délai court, reprises espacées ; message « le Géoportail ne répond pas, réessayez ».
- Zone : la décider LOCALEMENT, avec `donnees/zones-biarritz.geojson` (shapely) : la zone qui recouvre le plus de la parcelle, et la liste
  des zones touchées (une parcelle à cheval sur N et Nh se dit). Plus d'API, plus de point hors zone.
- Adresse : un extrait local de la base adresse de Biarritz, en priorité ; l'API en secours.

**P1 · Les recettes** : maison neuve = 1, 2, 7, 9, 10, 11, 12 ; un test qui vérifie, pour chaque projet, que l'article de chaque grandeur
(hauteur, distance, emprise, clôture) est dans la recette.

**P2 · Le moteur de chiffres du code** : le modèle extrait des grandeurs (emprise existante, surface créée, hauteur existante,
hauteur ajoutée, distance à la limite, hauteur de clôture), le code les compare aux limites de la zone (pourcentage × parcelle,
somme existant + projet, « R+N »), avec la phrase du règlement comme preuve. La grille du modèle ne garde que les conditions,
les exceptions et l'applicabilité.

**P3 · Capteurs d'applicabilité** : une phrase dont la clause nomme « parcs et espaces verts protégés », « espaces boisés classés »,
« linéaire commercial », « zone d'implantation obligatoire » ne vaut que si les faits de la parcelle le disent ; la mixité sociale ne vaut pas
pour une maison seule. (31 clauses d'espaces verts protégés dans 28 articles, 21 d'espaces boisés classés, 10 de linéaire commercial.)

**P4 · Le plan du règlement comme règle** : article 1 = ce qui est interdit, article 2 = ce qui est admis sous conditions : en zone stricte,
une phrase de l'article 2 est une exception, quoi qu'en dise le modèle ; une exception dont seule une condition de conception manque
(insertion, aspect) donne « oui sous conditions », pas « impossible à dire ».

**P5 · Limites alternatives** : 25 % / 40 % si la parcelle date d'avant 2003 / 30 % si moins de 1 000 m² : une violation contestée par une
alternative respectée dont la condition est inconnue = « impossible à dire ».

**P6 · Sens vérifié par le code** (« maximale » → au_plus), « violée » non chiffrée ≠ preuve d'un « non », la phrase citée doit contenir le seuil.

**P7 · Vitesse** (`vitesse/grille_rapide.py`) : phrases numérotées, plus de recopie, plus de constat écrit par le modèle ; premier essai à
1 600 jetons. Prototype prêt, jamais lancé sur K2.

**P8 · Preuve minimale** : « oui sous conditions » exige au moins une règle établie par le code ou une exclusion expresse ; sinon « impossible à dire ».

## Certification
Le 2e banc caché est connu après lecture. Un 3e banc (24 questions neuves, parcelles jamais utilisées, **sans parcelle à cheval sur deux zones**,
étiquettes écrites avant tout passage) sera scellé avant la v4 ; la v4 repasse aussi le banc de mise au point (non-régression).
