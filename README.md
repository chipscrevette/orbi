# Orbi

**L'assistant d'urbanisme qui lit le PLU, vérifie chaque citation, compare les chiffres et décide — 100 % local.**

« Puis-je poser un abri de jardin de 8 m² à 50 cm du mur du voisin, au 5 impasse Monnier à Biarritz ? »
Orbi retrouve la parcelle et sa zone, lit les articles du règlement qui s'appliquent, et répond : un verdict
(*oui*, *oui sous conditions*, *non*, *impossible à dire*), les articles cités mot pour mot avec leur page, la démarche
(déclaration préalable ou permis) et son délai. Quand une information manque, il le dit au lieu de deviner.

> Projet en cours : la v1 couvre Biarritz. L'application de bureau (Electron, dossier `app/`) marche de bout en bout ; voir la feuille de route.

## L'application

![Orbi répond à une vraie question](docs/captures/reponse.png)

Une application de bureau (Electron, React, TypeScript) : on pose la question, Orbi montre où il en est pendant la minute
d'analyse (six étapes qui se cochent), puis répond : le verdict, les règles citées mot à mot avec leur page, les points à
vérifier, la démarche, et la parcelle sur la carte des zones du PLU. La colonne de droite montre la vraie machine : la
carte graphique, la mémoire, le temps de réponse mesuré. Un « bonjour » reçoit une réponse de conversation en quelques
secondes. Sans moteur local (sur GitHub Pages, par exemple), l'interface rejoue de vraies réponses enregistrées.

| Accueil | Orbi travaille |
|---|---|
| ![Accueil](docs/captures/accueil.png) | ![Les étapes en direct](docs/captures/travail.png) |

## Le principe : le modèle lit, le code décide

Un modèle de langage local (K2 Horizon 7B) remplit une grille, une ligne par règle du règlement : la phrase exacte, ce
qu'elle exige, les chiffres du projet. **Il ne donne aucun verdict.** Le code vérifie chaque ligne (la citation existe-t-elle
mot pour mot ? la règle vise-t-elle cette parcelle ? les chiffres viennent-ils de la question ?), compare lui-même les
nombres, puis une table de décision testée sans modèle tire le verdict, et le texte de la réponse est composé à partir du
verdict : il ne peut plus le contredire.

![La grille](docs/schemas/grille-v1.png)

## Des chiffres honnêtes

Un agent ne se juge que sur des questions qu'il n'a jamais vues. Les bancs cachés sont écrits, étiquetés et **scellés
par une empreinte SHA-256** (questions et code) avant le passage, puis passés une seule fois.

| banc | questions | ancien agent | grille |
|---|---|---|---|
| mise au point (sert à corriger, donc flatteur) | 30 | 24 | 25 |
| 1er banc caché | 20 | 12 | — |
| 2e banc caché (2 octobre 2026) | 40 | 29 | 27 |

Sur le 2e banc caché, la grille divise par deux les « oui » trop permissifs (9 → 4), mais elle n'est pas encore meilleure au
total. Chaque échec est expliqué dans `labo/vitesse/PLAN-v4.md` : ce que le code reçoit du modèle est encore trop pauvre.

## La qualité

**1 099 tests unitaires et de mutation** (quelques secondes, sans modèle), **3 rejeux d'intégration** (les passages
enregistrés du banc, rejoués sans le modèle, doivent redonner exactement les mêmes réponses), **88 % de couverture**, et 75 tests de l'interface (Vitest).
Les 7 défauts connus restants sont écrits comme des tests marqués `xfail`, avec leur explication : un défaut corrigé fait
échouer son marqueur, on ne peut pas l'oublier.

## L'organisation

```
orbi/
├─ src/orbi/
│  ├─ chemins.py      tous les chemins du projet
│  ├─ domaine/        la grille, le contrôle, la décision, la fiche, le verrou de zone, la démarche : sans réseau ni modèle
│  ├─ reglement/      le règlement découpé, les citations exactes, la recherche (mots + sens), le savoir métier
│  ├─ outils/         les API publiques (adresse, cadastre, Géoportail de l'Urbanisme), avec cache disque
│  ├─ modele/         le client du modèle local et ses consignes
│  ├─ agent/          l'orchestration : l'agent historique et la grille
│  ├─ evaluation/     la notation des bancs, le rejeu sans modèle, le scellé, les pages de rapport
│  └─ api/            le serveur local de l'application : l'état de la machine, les réponses en direct
├─ tests/             unitaires, mutations (on casse le moteur exprès), intégration
├─ bancs/             les questions (jeux/), les générateurs, les passages et leurs traces (resultats/)
├─ donnees/           le règlement, l'index de recherche, les zones du PLU, le cache des API
├─ app/               l'application de bureau : Electron (electron/), l'interface React (src/), ses tests (tests/)
├─ services/          le serveur du modèle (k2/) et le serveur d'embeddings (embeddings/)
├─ docs/              les schémas Excalidraw (schemas/) et leur générateur (outils/), les décisions d'architecture
├─ labo/              les expériences en cours (vitesse : citations par numéro de phrase)
└─ scripts/           la préparation des données
```

## Lancer

Prérequis : Python 3.12 et [uv](https://docs.astral.sh/uv/), Node 22, une carte graphique de 12 Go pour le modèle.

```bash
uv sync --group dev                         # le paquet orbi et les outils de test
uv run pytest                               # les tests unitaires et de mutation (sans modèle, quelques secondes)
uv run pytest -m integration                # le rejeu des traces enregistrées (serveur d'embeddings requis)
uv run orbi-banc --grille                   # le banc de mise au point, avec le modèle
uv run orbi-serveur                         # le serveur local de l'application : http://127.0.0.1:4770 (API : /api/docs)
node scripts/installer-app.mjs              # les dépendances de l'application de bureau (caches sur D:/tools s'il existe)
cd app && npm run dev                       # l'application : elle démarre le serveur, la recherche et le modèle, et les arrête en se fermant
cd app && npm test                          # les tests de l'interface
cd app && npm run build:web                 # le site de démonstration (réponses enregistrées), pour GitHub Pages
```

Le serveur local répond en direct : chaque étape de l'agent part vers l'application au moment où elle se termine
(Server-Sent Events), puis le lieu (parcelle, zone, servitudes), puis la réponse. Une vraie question, jamais vue :
« Je veux construire une véranda de 15 m² sur ma maison au 10 rue Gambetta à Biarritz » → parcelle BC 0074, zone UAs,
site patrimonial remarquable, *oui sous conditions*, en 69 secondes sur une RTX 3060.

Les deux services locaux : `services/k2/serveur_k2.py` (port 11500) et `services/embeddings/emb_serveur.mjs` (port 11600).
L'application les lance depuis ces dossiers ; si ta machine les fait tourner ailleurs, copie `services.exemple.json` en
`services.local.json` (hors dépôt) et indique-y leurs dossiers et variables d'environnement. Journaux : `conversations/journaux/`.

## Feuille de route

1. **Fondations** — dossiers, tests, documentation *(fait)*
2. **Fiabilité** — outils locaux, moteur de chiffres dans le code, filtres d'applicabilité, 3e banc caché
3. **Le chatbot** — application Electron, réponses en flux, carte de la parcelle, questions de relance *(en cours)*
4. **Le design** — Orbi, la mascotte, et une direction artistique tirée du sujet
5. **La faisabilité** — plusieurs parcelles : ce qu'on peut y construire, comparé, avec un plan
6. **Apprendre des retours** — avis des utilisateurs relus, devenus cas de test et règles
7. **La vitrine** — page portfolio et film de présentation
