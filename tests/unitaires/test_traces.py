"""Retrouver la trace d'une réponse. Les passages gardent le chemin absolu de leur trace, pris au moment du passage, parfois dans
l'ancien dossier assistant-plu : trace_locale() le rend tel quel s'il est dans le projet, sinon cherche la trace par son nom dans
bancs/resultats/traces/. On joue un faux projet dans tmp_path (RACINE et TRACES redirigés)."""
import os

import pytest

import orbi.evaluation.traces as traces
from orbi.evaluation.traces import trace_locale

NOM = "20261002-141623-353351.jsonl"


@pytest.fixture
def projet(tmp_path, monkeypatch):
    """Un faux projet orbi/ avec son dossier de traces vide."""
    racine = tmp_path / "orbi"
    dossier = racine / "bancs" / "resultats" / "traces"
    dossier.mkdir(parents=True)
    monkeypatch.setattr(traces, "RACINE", str(racine))
    monkeypatch.setattr(traces, "TRACES", str(dossier))
    return racine


def creer(chemin):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text('{"etape": "tri"}\n', encoding="utf-8")
    return chemin


@pytest.mark.parametrize("chemin", [pytest.param(None, id="aucun chemin"), pytest.param("", id="chemin vide")])
def test_sans_chemin_pas_de_trace(projet, chemin):
    assert trace_locale(chemin) is None


def test_une_trace_du_projet_est_rendue_telle_quelle(projet):
    trace = creer(projet / "labo" / "vitesse" / NOM)  # hors de bancs/resultats/traces/ : seul son chemin la retrouve
    assert trace_locale(str(trace)) == str(trace)


@pytest.mark.parametrize("ancien", [
    pytest.param("D:\\PORTFOLIO\\CLAUDE\\assistant-plu\\resultats\\traces\\" + NOM, id="ancien dossier assistant-plu (Windows)"),
    pytest.param("/home/kevin/assistant-plu/resultats/traces/" + NOM, id="ancien dossier (barres obliques)"),
    pytest.param("resultats/traces/" + NOM, id="chemin relatif"),
])
def test_un_chemin_d_un_autre_dossier_est_retrouve_par_son_nom(projet, ancien):
    trace = creer(projet / "bancs" / "resultats" / "traces" / NOM)
    assert trace_locale(ancien) == str(trace)


def test_une_trace_deplacee_dans_le_projet_est_retrouvee_par_son_nom(projet):
    """Le chemin est dans le projet mais la trace n'y est plus : on la cherche dans bancs/resultats/traces/."""
    trace = creer(projet / "bancs" / "resultats" / "traces" / NOM)
    assert trace_locale(str(projet / "resultats" / "traces" / NOM)) == str(trace)


@pytest.mark.parametrize("chemin", [  # chaque chemin est construit à partir de la racine du faux projet
    pytest.param(lambda racine: "D:\\PORTFOLIO\\CLAUDE\\assistant-plu\\resultats\\traces\\" + NOM, id="ancien dossier"),
    pytest.param(lambda racine: "resultats/traces/" + NOM, id="chemin relatif"),
    pytest.param(lambda racine: str(racine / "labo" / NOM), id="chemin dans le projet"),
])
def test_une_trace_absente_donne_none(projet, chemin):
    assert trace_locale(chemin(projet)) is None


@pytest.mark.skipif(os.name != "nt", reason="la casse des chemins ne compte que sous Windows")
def test_sous_windows_la_casse_du_chemin_ne_compte_pas(projet):
    """Un passage enregistré avec « d:\\portfolio\\… » désigne le même fichier que « D:\\PORTFOLIO\\… »."""
    trace = creer(projet / "labo" / NOM)
    assert trace_locale(str(trace).upper()) == str(trace).upper()


def test_un_dossier_voisin_au_nom_proche_n_est_pas_le_projet(projet, tmp_path):
    voisin = creer(tmp_path / "orbi-ancien" / "resultats" / "traces" / NOM)
    trace = creer(projet / "bancs" / "resultats" / "traces" / NOM)
    assert trace_locale(str(voisin)) == str(trace)
