"""Le résumé d'un passage du banc, sans modèle : verdicts exacts, bon sens, contresens, « trop permissif » (permis alors que le
projet est interdit ou indéterminé) et « trop timide » (indéterminé ou interdit alors qu'il est permis), par groupe, au total, et
selon que le verdict est imposé par le verrou de zone ou laissé au modèle. Faux jeu de questions et faux passage dans tmp_path
(JEUX redirigé dans la notation et dans l'analyse)."""
import json

import pytest

import orbi.evaluation.analyse_passage as analyse
import orbi.evaluation.notation as notation

ILLISIBLE = "réponse illisible (pas de JSON)"
LONGUE = ("Je voudrais poser un abri de jardin de 12 m² au fond de mon terrain, à 1 m de la limite séparative, dans le quartier "
          "Saint-Charles, est-ce possible ?")
# (id, groupe, projet, zone, verdict attendu, verdict obtenu, garde-fous) ; zone None : la question n'a pas de faits
CAS = [
    ("A1", "A", "véranda", "UDa", "oui", "oui", []),                                   # exact
    ("A2", "A", "extension", "UDc", "oui sous conditions", "oui", []),                 # une nuance : bon sens, pas exact
    ("A3", "A", "abri de jardin", "UD", "non", "oui sous conditions", []),             # contresens, trop permissif
    ("B1", "B", "piscine", "UDa", "oui sous conditions", "impossible à dire", []),     # trop timide
    ("B2", "B", "maison neuve", "Ncu", "non", "non", []),                              # exact, imposé par le verrou de zone
    ("B3", "B", "abri de jardin", "N", "impossible à dire", "oui", []),                # trop permissif, verrou (annexe en N)
    ("C1", None, "véranda", None, "information", "information", []),                   # exact, sans groupe ni sens
    ("C2", "C", "maison neuve", "UDa", "oui", "non", []),                              # contresens, trop timide
    ("D1", "D", "clôture", "UDa", "impossible à dire", "impossible à dire", [ILLISIBLE]),  # le bon mot, mais pas de réponse
]


def ecrire(chemin, donnees):
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


def question(id, groupe, projet, zone, attendu):
    texte = LONGUE if id == "A3" else f"{projet} en zone {zone} ?" if zone else f"{projet} ?"
    x = {"id": id, "question": texte, "projet": projet,
         "attendu": {"verdict_type": attendu, "demarche_type": "sans objet", "articles": []}}
    if groupe:
        x["groupe"] = groupe
    if zone:
        x["faits"] = {"zone": zone}
    return x


@pytest.fixture
def passage(tmp_path, monkeypatch):
    """Un passage du 2e banc caché, voie grille : les réponses enregistrées et une note périmée, que l'analyse refait."""
    jeux = tmp_path / "jeux"
    jeux.mkdir()
    monkeypatch.setattr(notation, "JEUX", str(jeux))
    monkeypatch.setattr(analyse, "JEUX", str(jeux))
    questions = [question(*c[:5]) for c in CAS]
    ecrire(jeux / "questions-test.json", questions)
    lignes = [{"id": x["id"], "question": x["question"], "attendu": x["attendu"], "demarche_obtenue": None,
               "obtenu": {"verdict_type": obtenu, "regles": [], "garde_fous": gf, "par": "K2 · grille", "trace": None},
               "note": {"verdict": True, "sens": True}}  # note périmée : l'analyse renote
              for x, (*_, obtenu, gf) in zip(questions, CAS)]
    resume = {"banc": "questions-test.json", "pipeline": "grille", "questions": len(lignes), "temps_moyen_s": 30.0, "scores": {}}
    return str(ecrire(tmp_path / "banc-cache2-grille-20261002-1520.json", {"resume": resume, "lignes": lignes}))


def compte(n, exact, sens, sens_n, contresens, permissif, timide):
    return {"n": n, "exact": exact, "sens": sens, "sens_n": sens_n, "contresens": contresens, "permissif": permissif,
            "timide": timide}


COMPTES = [
    pytest.param("A", compte(3, 1, 2, 3, 1, 1, 0), id="groupe A"),
    pytest.param("B", compte(3, 1, 1, 3, 0, 1, 1), id="groupe B"),
    pytest.param("C", compte(1, 0, 0, 1, 1, 0, 1), id="groupe C"),
    pytest.param("D", compte(1, 0, 0, 1, 0, 0, 0), id="groupe D (réponse illisible)"),
    pytest.param("-", compte(1, 1, 0, 0, 0, 0, 0), id="sans groupe (une information n'a pas de sens)"),
    pytest.param("verrou", compte(2, 1, 1, 2, 0, 1, 0), id="décidé par le verrou de zone"),
    pytest.param("modèle", compte(7, 2, 2, 6, 2, 1, 2), id="laissé au modèle"),
    pytest.param("TOTAL", compte(9, 3, 3, 8, 2, 2, 2), id="total"),
]


@pytest.mark.parametrize("groupe, attendu", COMPTES)
def test_les_compteurs_par_groupe(passage, groupe, attendu):
    _, par_groupe, _ = analyse.resume(passage)
    assert dict(par_groupe[groupe]) == attendu


def test_verrou_et_modele_se_partagent_le_total(passage):
    _, pg, _ = analyse.resume(passage)
    assert set(pg) == {"A", "B", "C", "D", "-", "verrou", "modèle", "TOTAL"}
    assert all(pg["verrou"][k] + pg["modèle"][k] == pg["TOTAL"][k] for k in pg["TOTAL"])


def test_les_echecs_sont_les_verdicts_faux(passage):
    """Une réponse illisible est un échec même quand son mot est le bon (D1)."""
    _, _, echecs = analyse.resume(passage)
    assert [e[0] for e in echecs] == ["A2", "A3", "B1", "B3", "C2", "D1"]
    assert echecs[1] == ("A3", "A", "non", "oui sous conditions", "K2 · grille", LONGUE[:110]), "la question est coupée à 110 signes"


def test_la_note_enregistree_est_refaite(passage):
    """L'analyse ne croit pas la note du fichier (ici périmée : tout juste) : elle renote avec la notation d'aujourd'hui."""
    d, _, _ = analyse.resume(passage)
    assert d["lignes"][0]["note"]["verdict"] is True and d["lignes"][1]["note"]["verdict"] is False
    assert d["resume"]["scores"]["verdict"] == (3, 9)


def test_afficher_ecrit_un_groupe_par_ligne_puis_les_echecs(passage, capsys):
    analyse.afficher(passage)
    sortie = capsys.readouterr().out
    assert "=== banc-cache2-grille-20261002-1520.json · grille · banc questions-test.json · 9 questions · 30.0 s en moyenne" in sortie
    assert [l.split()[0] for l in sortie.splitlines() if " n=" in l] == ["-", "A", "B", "C", "D", "modèle", "verrou", "TOTAL"]
    assert "  TOTAL  n= 9  exact  3  bon sens  3/ 8  contresens 2  trop permissif 2  trop timide 2" in sortie
    assert sum(l.startswith("   ✗") for l in sortie.splitlines()) == 6
