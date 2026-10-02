"""Le filet anti-régression : les passages enregistrés du banc, rejoués sans le modèle, doivent redonner exactement les mêmes
réponses. Tout ce qui entoure le modèle est déterministe (outils en cache, recherche, verrou, contrôle, décision, fiche) : une
différence est un changement de comportement du code, voulu ou non. Demande le serveur d'embeddings local (port 11600).
Lancer : uv run pytest -m integration"""
import os

import pytest
import requests

from orbi.chemins import RESULTATS
from orbi.evaluation.rejeu import rejouer

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def serveur_d_embeddings():
    try:
        requests.post("http://127.0.0.1:11600/emb", json={"textes": ["test"]}, timeout=30)
    except requests.RequestException:
        pytest.skip("serveur d'embeddings absent : node services/embeddings/emb_serveur.mjs 11600")


# passage enregistré → questions qui diffèrent AUJOURD'HUI, et pourquoi (chaque écart est un changement de code voulu et daté)
PASSAGES = [
    ("banc-cache2-grille-20261002-1520-reprise.json", {
        "D33": "02/10 (lot 1, citations vérifiées morceau par morceau) : « soumises la condition » (il manque « à ») n'est plus "
               "acceptée ; verdict inchangé, une condition à vérifier en moins. À reprendre : le recalage devrait combler un mot court"}),
    ("banc-grille-20261002-1434.json", {
        "V07": "02/10 : l'emprise déjà construite n'est plus un fait décisif",
        "V14": "02/10 : une surélévation ne viole pas la distance de murs existants",
        "V26": "02/10 : une parcelle à deux hauteurs au plan rend la hauteur décisive"}),
    ("banc-20260927-1058.json", {
        "V01": "28/09 : la surface après travaux n'est plus donnée pour une piscine (le 108 m² devient un chiffre sans source)",
        "V10": "28/09 : un texte national passe dans les sources nationales"}),
]


@pytest.mark.parametrize("fichier, ecarts_connus", PASSAGES, ids=[p[0] for p in PASSAGES])
def test_le_passage_rejoue_a_l_identique(fichier, ecarts_connus):
    identiques, n, diffs, _ = rejouer(os.path.join(RESULTATS, fichier))
    differents = {i for i, _ in diffs}
    assert differents == set(ecarts_connus), f"écarts inattendus : {differents - set(ecarts_connus)} ; disparus : {set(ecarts_connus) - differents}"
    assert identiques == n - len(ecarts_connus)
