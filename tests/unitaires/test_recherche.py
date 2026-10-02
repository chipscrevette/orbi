"""La recherche dans le règlement : par les mots (BM25) et par le sens (embeddings), fusionnés. Les tests tournent sur un petit
index fabriqué pour l'occasion et un faux serveur d'embeddings : on vérifie les filtres (chapitres, articles, exclusions), la
règle « le meilleur résultat par les mots est toujours gardé » et l'absence de doublons."""
import json

import pytest

from orbi.reglement import recherche
from orbi.reglement.recherche import Recherche, mots

# trois axes de sens : « distance », « hauteur », « clôture »
MORCEAUX = [
    {"chapitre": "UD", "ref": "UD 7", "pages": [69, 69], "texte": "Les constructions peuvent s'implanter sur les limites séparatives "
     "ou à au moins 3 mètres de celles-ci.", "v": [1.0, 0.0, 0.0]},
    {"chapitre": "UD", "ref": "UD 10", "pages": [70, 71], "texte": "La hauteur maximale est fixée à 9 m à l'égout du toit.",
     "v": [0.0, 1.0, 0.0]},
    {"chapitre": "UD", "ref": "UD 11", "pages": [71, 75], "texte": "L'emploi à nu de parpaings de béton est interdit. Les clôtures "
     "ne peuvent excéder 2 mètres.", "v": [0.0, 0.2, 0.98]},
    {"chapitre": "UD", "ref": "UD 11", "pages": [71, 75], "texte": "Les clôtures sur rue ne peuvent excéder 1,50 m.",
     "v": [0.0, 0.0, 1.0]},
    {"chapitre": "UC", "ref": "UC 7", "pages": [57, 57], "texte": "Les constructions peuvent s'implanter sur les limites séparatives.",
     "v": [0.9, 0.0, 0.1]},
    {"chapitre": "DG", "ref": "DG B-5", "pages": [9, 9], "texte": "L'emprise au sol est la projection verticale du volume.",
     "v": [0.1, 0.1, 0.1]},
]
SENS = {"distance": [1.0, 0.0, 0.0], "hauteur": [0.0, 1.0, 0.0], "clôture": [0.0, 0.0, 1.0]}


@pytest.fixture
def index(tmp_path, monkeypatch):
    chemin = tmp_path / "index-recherche.json"
    chemin.write_text(json.dumps(MORCEAUX), encoding="utf-8")
    monkeypatch.setattr(recherche, "INDEX", str(chemin))
    monkeypatch.setattr(recherche, "vecteurs", lambda textes: [SENS.get(t, [0.3, 0.3, 0.3]) for t in textes])
    return Recherche()


# ------------------------------------------------------------------------------------------------ les mots
@pytest.mark.parametrize("texte, attendu", [
    ("Les Clôtures", ["cloture"]),
    ("hauteurs et égouts", ["hauteur", "egout"]),
    ("a l'abri de la limite", ["abri", "limite"]),
    ("UD 7 : 3 mètres", ["ud", "metre"]),
], ids=["accents et majuscules", "pluriels en s et x", "mots vides et lettres seules", "chiffres d'une lettre écartés"])
def test_les_mots_sont_ramenes_a_leur_forme_simple(texte, attendu):
    assert mots(texte) == attendu


def test_un_mot_rare_du_reglement_devient_une_recherche(index):
    """Les plus rares d'abord ; à rareté égale, l'ordre alphabétique : une même question, une même recherche."""
    assert index.mots_rares("Ai-je le droit aux parpaings nus dans ma clôture ?") == "nu parpaing cloture"


def test_un_mot_trop_courant_n_est_pas_rare(index):
    assert index.mots_rares("Ai-je le droit aux parpaings nus dans ma clôture ?", df_max=1) == "nu parpaing"


def test_les_mots_de_l_adresse_et_les_mots_outils_ne_comptent_pas(index):
    assert index.mots_rares("parpaing rue des clôtures", adresse="rue des clôtures", df_max=25) == "parpaing"


def test_un_mot_absent_du_reglement_n_est_pas_rare(index):
    assert index.mots_rares("trampoline") == ""


def test_bm25_classe_d_abord_le_morceau_qui_contient_le_mot(index):
    scores = index._bm25("parpaing", range(len(MORCEAUX)))
    assert max(scores, key=scores.get) == 2
    assert scores[0] == 0


# ------------------------------------------------------------------------------------------------ la recherche hybride
def test_la_recherche_reste_dans_les_chapitres_donnes(index):
    res = index.chercher(["distance"], ["UD"], k=3)
    assert res and all(r["ref"].startswith("UD") for r in res)


def test_le_sens_trouve_l_article_sans_les_memes_mots(index):
    assert index.chercher(["hauteur"], ["UD"], k=1)[0]["ref"] == "UD 10"


def test_le_meilleur_resultat_par_les_mots_est_toujours_garde(index):
    """« parpaing » : 1er par les mots, loin par le sens (sa requête n'a aucun sens connu) — il passe quand même (V18)."""
    res = index.chercher(["parpaing"], ["UD"], k=1)
    assert res[0]["ref"] == "UD 11" and "parpaings" in res[0]["texte"]


def test_refs_limite_la_recherche_a_ces_articles(index):
    res = index.chercher(["distance"], ["UD"], k=2, refs=["UD 11"])
    assert {r["ref"] for r in res} == {"UD 11"}


def test_un_article_deja_lu_est_exclu(index):
    res = index.chercher(["distance"], ["UD", "UC"], k=3, exclure=("UD 7",))
    assert "UD 7" not in {r["ref"] for r in res}


def test_un_par_article_varie_les_sources(index):
    res = index.chercher(["clôture"], ["UD"], k=3, un_par_article=True)
    refs = [r["ref"] for r in res]
    assert len(refs) == len(set(refs))


def test_deux_requetes_ne_donnent_pas_deux_fois_le_meme_morceau(index):
    res = index.chercher(["clôture", "clôture"], ["UD"], k=2)
    textes = [r["texte"] for r in res]
    assert len(textes) == len(set(textes))


def test_aucun_morceau_dans_les_chapitres_donne_une_liste_vide(index):
    assert index.chercher(["distance"], ["Ncu"]) == []


def test_un_resultat_garde_sa_reference_ses_pages_et_ses_scores(index):
    r = index.chercher(["distance"], ["UD"], k=1)[0]
    assert r["ref"] == "UD 7" and r["pages"] == [69, 69] and r["requete"] == "distance"
    assert r["sens"] == 1.0 and "mots" in r


# ------------------------------------------------------------------------------------------------ le serveur d'embeddings
def test_les_vecteurs_viennent_du_serveur_local(monkeypatch):
    envoye = {}

    class Reponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"vecteurs": [[0.1, 0.2]]}

    def faux_post(url, json=None, timeout=None):
        envoye.update(url=url, corps=json)
        return Reponse()

    monkeypatch.setattr(recherche.requests, "post", faux_post)
    assert recherche.vecteurs(["une question"]) == [[0.1, 0.2]]
    assert envoye["url"].startswith("http://127.0.0.1:11600") and envoye["corps"] == {"textes": ["une question"]}


def test_construire_l_index_vectorise_chaque_morceau(tmp_path, monkeypatch):
    chemin = tmp_path / "index.json"
    monkeypatch.setattr(recherche, "INDEX", str(chemin))
    monkeypatch.setattr(recherche, "morceaux", lambda: [{"texte": f"morceau {i}"} for i in range(20)])
    monkeypatch.setattr(recherche, "vecteurs", lambda textes: [[0.123456789] for _ in textes])
    recherche.construire()
    ecrit = json.loads(chemin.read_text(encoding="utf-8"))
    assert len(ecrit) == 20 and all(m["v"] == [0.12346] for m in ecrit)
