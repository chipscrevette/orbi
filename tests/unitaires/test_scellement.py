"""Le scellé du banc caché : l'empreinte SHA-256 de chaque fichier de l'agent est ajoutée au fichier de scellé, une seule fois, et
une copie du code figé est gardée à côté. Qui retouche une ligne après coup change l'empreinte. On joue un faux projet dans tmp_path
(RACINE redirigée) : le vrai scellé de bancs/jeux/ n'est jamais touché."""
import hashlib
import re

import pytest

import orbi.evaluation.scellement as scellement
from orbi.evaluation.scellement import empreinte, fichiers

SCELLE = "bancs/jeux/questions-cachees-9.sha256"
DEJA_SCELLE = "3a4d147e  questions-cachees-9.json  scellé avant tout passage de l'agent\n"
CODE = {  # le code du paquet : scellé et copié avec le serveur du modèle
    "src/orbi/__init__.py": b"",
    "src/orbi/chemins.py": b"RACINE = '.'\n",
    "src/orbi/agent/grille.py": b"class AgentGrille:\n    pass\n",
    "src/orbi/evaluation/notation.py": b"def noter(x, res):\n    return {}\n",  # la notation, elle, est scellée
}
DONNEES = {  # scellés ; le serveur du modèle est du code, il est copié, les données non ; index-recherche.json et
    # zones-biarritz.geojson manquent : ils ne sont pas listés
    "services/k2/serveur_k2.py": b"# le serveur du modele\n",
    "donnees/articles.json": b"{}\n",
}
HORS_SCELLE = {  # chemin → pourquoi il n'est pas scellé
    "src/orbi/evaluation/pages/rapport.py": "page de rapport",
    "src/orbi/agent/__pycache__/grille.py": "dans __pycache__",
    "src/orbi/agent/notes.md": "pas du Python",
    "labo/vitesse/essai.py": "hors du paquet",
}


@pytest.fixture
def projet(tmp_path, monkeypatch):
    """Un faux projet orbi/ : du code, des données, des fichiers qui ne se scellent pas, et le scellé des questions."""
    racine = tmp_path / "orbi"
    hors = {f: b"# hors du scelle\n" for f in HORS_SCELLE}
    for rel, octets in {**CODE, **DONNEES, **hors, SCELLE: DEJA_SCELLE.encode("utf-8")}.items():
        (racine / rel).parent.mkdir(parents=True, exist_ok=True)
        (racine / rel).write_bytes(octets)
    monkeypatch.setattr(scellement, "RACINE", str(racine))
    return racine


def partie_figee(racine):
    """Les empreintes ajoutées par le scellement (lignes « empreinte  fichier »), par fichier."""
    texte = (racine / SCELLE).read_bytes().decode("utf-8")
    lignes = texte.split("avant le passage du banc caché :\n", 1)[1].splitlines()
    return {f: h for h, f in (l.split("  ", 1) for l in lignes)}


# ── fichiers et empreinte ────────────────────────────────────────────────────────────────────────────────────────────────────

def test_fichiers_scelles_le_code_du_paquet_puis_les_donnees(projet):
    assert fichiers() == sorted(CODE) + ["services/k2/serveur_k2.py", "donnees/articles.json"]


@pytest.mark.parametrize("chemin", list(HORS_SCELLE), ids=list(HORS_SCELLE.values()))
def test_ce_qui_n_est_pas_l_agent_n_est_pas_scelle(projet, chemin):
    assert chemin not in fichiers()


def test_les_chemins_scelles_s_ecrivent_avec_des_barres_obliques(projet):
    """Le scellé se relit pareil sous Windows et ailleurs."""
    assert all("\\" not in f for f in fichiers())


def test_l_empreinte_est_le_sha256_des_octets(projet):
    assert empreinte("src/orbi/agent/grille.py") == hashlib.sha256(CODE["src/orbi/agent/grille.py"]).hexdigest()


def test_une_ligne_retouchee_change_l_empreinte(projet):
    avant = empreinte("src/orbi/chemins.py")
    (projet / "src/orbi/chemins.py").write_bytes(b"RACINE = '..'\n")
    assert empreinte("src/orbi/chemins.py") != avant


# ── main : figer le code sous l'empreinte des questions ──────────────────────────────────────────────────────────────────────

def test_les_empreintes_sont_ajoutees_sous_celle_des_questions(projet, capsys):
    scellement.main(SCELLE)
    octets = (projet / SCELLE).read_bytes()
    texte = octets.decode("utf-8")
    assert texte.startswith(DEJA_SCELLE + "\ncode de l'agent figé le "), "l'empreinte des questions reste en tête, intacte"
    assert re.search(r"code de l'agent figé le \d{4}-\d{2}-\d{2} \d{2}:\d{2}, avant le passage du banc caché :\n", texte)
    assert partie_figee(projet) == {f: hashlib.sha256((projet / f).read_bytes()).hexdigest() for f in fichiers()}
    assert octets.endswith(b"\n") and b"\r\n" not in octets, "fins de ligne Unix, même sous Windows"
    assert "6 fichiers figés" in capsys.readouterr().out


def test_la_copie_du_code_fige_est_faite(projet):
    scellement.main(SCELLE)
    copie = projet / "bancs" / "jeux" / "code-fige-questions-cachees-9"
    copies = sorted(p.relative_to(copie).as_posix() for p in copie.rglob("*") if p.is_file())
    assert copies == sorted([*CODE, "services/k2/serveur_k2.py"]), "le code du paquet et le serveur du modèle, pas les données"
    assert all((copie / f).read_bytes() == octets for f, octets in CODE.items())


def test_on_ne_fige_pas_deux_fois(projet):
    scellement.main(SCELLE)
    avant = (projet / SCELLE).read_bytes()
    with pytest.raises(AssertionError, match="on ne le fige pas deux fois"):
        scellement.main(SCELLE)
    assert (projet / SCELLE).read_bytes() == avant, "le scellé n'a pas bougé"


def test_apres_une_retouche_la_copie_garde_les_empreintes_verifiables(projet):
    """Après un découpage ou une retouche du code, la copie figée correspond toujours au scellé."""
    scellement.main(SCELLE)
    (projet / "src/orbi/agent/grille.py").write_bytes(b"class AgentGrille:\n    pass  # retouche\n")
    scelles = partie_figee(projet)
    assert empreinte("src/orbi/agent/grille.py") != scelles["src/orbi/agent/grille.py"], "la retouche se voit"
    copie = projet / "bancs" / "jeux" / "code-fige-questions-cachees-9" / "src" / "orbi" / "agent" / "grille.py"
    assert hashlib.sha256(copie.read_bytes()).hexdigest() == scelles["src/orbi/agent/grille.py"]
