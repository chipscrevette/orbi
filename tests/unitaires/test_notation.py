"""La notation des bancs d'essai, sans modèle. noter() juge une réponse critère par critère (verdict, sens, erreur grave, démarche,
articles, citations, garde-fous) ; renoter() relit un passage avec les étiquettes d'aujourd'hui ; main() fait passer un faux agent
sur un faux jeu de questions. Tout se passe dans tmp_path : rien n'est lu ni écrit dans bancs/."""
import json
import re

import pytest

import orbi.agent.grille as grille
import orbi.evaluation.notation as notation
from orbi.evaluation.notation import normer_dem, noter, renoter

ILLISIBLE = "réponse illisible (pas de JSON)"
CRITERES = ("verdict", "sens", "grave", "demarche", "articles", "citations", "garde_fous")


def question(verdict="oui sous conditions", demarche="déclaration préalable", articles=("UD 7", "UD 9"), id="V01",
             texte="Puis-je poser un abri de jardin de 8 m² à 4 m de la limite au 20 avenue du Docteur Claisse ?"):
    """Une question du banc, réduite à ce que la notation lit."""
    return {"id": id, "question": texte, "attendu": {"verdict_type": verdict, "demarche_type": demarche, "articles": list(articles)}}


def reponse(verdict="oui sous conditions", demarche="déclaration préalable", cites=("UD 7",), garde_fous=()):
    """Une réponse de l'agent ; chaque article cité l'est avec une citation vérifiée."""
    return {"verdict_type": verdict, "demarche": {"type": demarche}, "regles": [{"article": a, "verifiee": True} for a in cites],
            "garde_fous": list(garde_fous)}


def ecrire(chemin, donnees):
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=1), encoding="utf-8")
    return chemin


# ── noter : critère par critère ──────────────────────────────────────────────────────────────────────────────────────────────

# « grave » vaut True quand il n'y a PAS d'erreur grave (✓ au banc) ; None quand le critère ne s'applique pas
VERDICTS = [
    pytest.param("oui", "oui", True, True, True, id="oui juste"),
    pytest.param("oui sous conditions", "oui", False, True, True, id="oui pour oui sous conditions : une nuance, même sens"),
    pytest.param("oui", "oui sous conditions", False, True, True, id="oui sous conditions pour oui : même sens"),
    pytest.param("non", "oui sous conditions", False, False, False, id="oui quand c'est non : erreur grave"),
    pytest.param("oui", "non", False, False, False, id="non quand c'est oui : erreur grave"),
    pytest.param("oui sous conditions", "impossible à dire", False, False, True, id="impossible à dire devant un oui : prudent"),
    pytest.param("non", "impossible à dire", False, False, True, id="impossible à dire devant un non : prudent"),
    pytest.param("impossible à dire", "impossible à dire", True, True, None, id="impossible à dire juste"),
    pytest.param("impossible à dire", "oui", False, False, None, id="oui devant un impossible à dire : pas de sens opposé"),
    pytest.param("non", "erreur", False, False, True, id="l'agent a planté"),
    pytest.param("information", "information", True, None, None, id="une information n'a pas de sens à juger"),
    pytest.param("hors périmètre", "oui", False, None, None, id="hors périmètre manqué"),
]


@pytest.mark.parametrize("attendu, obtenu, verdict, sens, grave", VERDICTS)
def test_verdict_sens_et_erreur_grave(attendu, obtenu, verdict, sens, grave):
    n = noter(question(attendu), reponse(obtenu))
    assert (n["verdict"], n["sens"], n["grave"]) == (verdict, sens, grave)


@pytest.mark.parametrize("attendu", [pytest.param("impossible à dire", id="même quand c'est la valeur attendue"),
                                     pytest.param("oui", id="attendu oui")])
def test_une_reponse_illisible_n_est_jamais_un_verdict_juste(attendu):
    """Sans JSON, l'agent affiche « impossible à dire » par défaut : ce n'est pas un verdict (V16 et V26 au 1er passage)."""
    n = noter(question(attendu), reponse("impossible à dire", garde_fous=[ILLISIBLE]))
    assert (n["verdict"], n["sens"], n["garde_fous"]) == (False, False, False)


DEMARCHES = [
    pytest.param("déclaration préalable", "déclaration préalable", True, id="la bonne démarche"),
    pytest.param("déclaration préalable", "  déclaration préalable ", True, id="espaces autour"),
    pytest.param("dépend de la surface créée", "dépend de la surface du bassin", True, id="« dépend… » : une seule réponse"),
    pytest.param("permis de construire", "déclaration préalable", False, id="la mauvaise démarche"),
    pytest.param("déclaration préalable", None, False, id="aucune démarche donnée"),
    pytest.param("sans objet", "déclaration préalable", None, id="la question n'en appelle pas"),
]


@pytest.mark.parametrize("attendue, obtenue, note", DEMARCHES)
def test_demarche(attendue, obtenue, note):
    assert noter(question(demarche=attendue), reponse(demarche=obtenue))["demarche"] is note


@pytest.mark.parametrize("brut, norme", [
    pytest.param(None, "", id="rien"),
    pytest.param("  déclaration préalable  ", "déclaration préalable", id="espaces retirés"),
    pytest.param("dépend de la surface créée", "dépend", id="dépend de la surface créée"),
    pytest.param("dépend de la surface du bassin", "dépend", id="dépend de la surface du bassin"),
    pytest.param("permis de construire + architecte", "permis de construire + architecte", id="le reste ne bouge pas"),
])
def test_normer_dem(brut, norme):
    assert normer_dem(brut) == norme


ARTICLES = [
    pytest.param(["UD 7", "UD 9"], "oui", ["UD 9"], True, id="un des articles attendus"),
    pytest.param(["UD 7"], "oui", ["UD 11", "UD 7"], True, id="parmi d'autres"),
    pytest.param(["UD 7"], "oui", ["UD 11"], False, id="aucun des articles attendus"),
    pytest.param(["UD 7"], "oui", [], False, id="aucun article cité"),
    pytest.param([], "information", ["DG B-5"], None, id="aucun article attendu"),
    pytest.param(["Ncu 1"], "hors périmètre", [], None, id="hors périmètre : les articles ne comptent pas"),
]


@pytest.mark.parametrize("attendus, verdict, cites, note", ARTICLES)
def test_articles(attendus, verdict, cites, note):
    assert noter(question(verdict, articles=attendus), reponse(verdict, cites=cites))["articles"] is note


@pytest.mark.parametrize("verifiees, note", [pytest.param([True, True], True, id="toutes vérifiées"),
                                             pytest.param([True, False], False, id="une citation introuvable dans l'article"),
                                             pytest.param([], True, id="aucune citation")])
def test_citations(verifiees, note):
    res = {**reponse(), "regles": [{"article": "UD 7", "verifiee": v} for v in verifiees]}
    assert noter(question(), res)["citations"] is note


@pytest.mark.parametrize("garde_fous, note", [pytest.param([], True, id="aucune faute"), pytest.param(None, True, id="absents"),
                                              pytest.param(["zone citée ≠ zone trouvée"], False, id="une faute restante")])
def test_garde_fous(garde_fous, note):
    assert noter(question(), {**reponse(), "garde_fous": garde_fous})["garde_fous"] is note


def test_une_reponse_vide_se_note_sans_planter():
    """Une réponse sans aucun champ (agent interrompu) : rien n'est juste, mais rien n'est inventé non plus."""
    assert noter(question("oui", "déclaration préalable", ["UD 9"]), {}) == {
        "verdict": False, "sens": False, "grave": True, "demarche": False, "articles": False, "citations": True, "garde_fous": True}


# ── renoter : un passage relu avec les étiquettes d'aujourd'hui ──────────────────────────────────────────────────────────────

@pytest.fixture
def jeux(tmp_path, monkeypatch):
    """Un faux bancs/jeux/ : les questions telles qu'elles sont étiquetées aujourd'hui."""
    dossier = tmp_path / "jeux"
    dossier.mkdir()
    monkeypatch.setattr(notation, "JEUX", str(dossier))
    return dossier


def ligne(x, verdict, demarche_obtenue, cites):
    """Une ligne de passage enregistrée : l'attendu et la note d'alors, et la réponse de l'agent, qui, elle, ne change pas."""
    return {"id": x["id"], "question": x["question"],
            "attendu": {"verdict_type": "oui", "demarche_type": "déclaration préalable", "articles": []},
            "obtenu": {"verdict_type": verdict, "reponse": "…", "regles": [{"article": a, "verifiee": True} for a in cites],
                       "a_verifier": [], "garde_fous": [], "secondes": 20.0, "par": "K2 · grille", "trace": None},
            "demarche_obtenue": demarche_obtenue, "note": {k: True for k in CRITERES}}


def test_renoter_relit_un_passage_avec_les_etiquettes_d_aujourd_hui(jeux, tmp_path):
    # V01 a été réétiqueté depuis le passage : « oui » alors, « non » aujourd'hui
    v01 = question("non", "sans objet", ["UD 7"], id="V01")
    v02 = question("oui sous conditions", "déclaration préalable", ["UD 9"], id="V02", texte="Puis-je agrandir ma maison de 30 m² ?")
    ecrire(jeux / "questions-test.json", [v01, v02])
    lignes = [ligne(v01, "oui", "déclaration préalable", ["UD 7"]), ligne(v02, "oui sous conditions", "déclaration préalable", ["UD 9"])]
    publies = {k: [2, 2] for k in CRITERES}
    chemin = ecrire(tmp_path / "banc-test.json", {"resume": {"banc": "questions-test.json", "scores": publies}, "lignes": lignes})
    avant = chemin.read_bytes()

    d = renoter(str(chemin))

    assert d["lignes"][0]["attendu"] == v01["attendu"]
    assert d["lignes"][0]["note"] == {"verdict": False, "sens": False, "grave": False, "demarche": None, "articles": True,
                                      "citations": True, "garde_fous": True}
    assert d["lignes"][1]["note"] == {k: True for k in CRITERES}, "la démarche enregistrée (demarche_obtenue) est relue"
    assert d["resume"]["scores_publies"] == publies
    assert d["resume"]["scores"] == {"verdict": (1, 2), "sens": (1, 2), "grave": (1, 2), "demarche": (1, 1), "articles": (2, 2),
                                     "citations": (2, 2), "garde_fous": (2, 2)}
    assert [l["obtenu"] for l in d["lignes"]] == [l["obtenu"] for l in lignes], "les réponses ne changent pas"
    assert chemin.read_bytes() == avant, "renoter ne réécrit pas le passage"


def test_sans_banc_indique_c_est_le_banc_de_mise_au_point(jeux, tmp_path):
    """Les premiers passages n'écrivaient pas leur banc : c'était questions-v2.json. Ils n'avaient pas non plus la démarche."""
    v01 = question("oui sous conditions", "déclaration préalable", ["UD 7"], id="V01")
    ecrire(jeux / "questions-v2.json", [v01])
    ancienne = ligne(v01, "oui sous conditions", None, ["UD 7"])
    del ancienne["demarche_obtenue"]
    d = renoter(str(ecrire(tmp_path / "banc-ancien.json", {"resume": {"scores": {}}, "lignes": [ancienne]})))
    assert d["lignes"][0]["attendu"] == v01["attendu"]
    assert d["resume"]["scores"]["verdict"] == (1, 1)
    assert d["resume"]["scores"]["demarche"] == (0, 1), "sans démarche enregistrée, la démarche n'est pas comptée juste"


# ── main : le banc complet, avec un faux agent ───────────────────────────────────────────────────────────────────────────────

ABRI = question("oui sous conditions", "déclaration préalable", ["UD 7"], id="V01")
MAISON = question("non", "sans objet", ["Ncu 1"], id="V02", texte="Puis-je construire une maison neuve au 93 avenue de Bidart, en Ncu ?")
DELAI = question("information", "sans objet", [], id="V03", texte="Quel est le délai d'instruction d'une déclaration préalable ?")
CACHEE = question("non", "sans objet", ["N 1"], id="C01", texte="Puis-je construire une maison en zone N ?")
CACHEE_2 = question("oui", "déclaration préalable", ["UD 9"], id="D01", texte="Puis-je poser une véranda de 15 m² en UD ?")
PREVU = {
    ABRI["question"]: {"verdict_type": "oui sous conditions", "reponse": "Oui, sous conditions.", "secondes": 30.0,
                       "regles": [{"article": "UD 7", "verifiee": True}], "a_verifier": [], "garde_fous": [],
                       "trace": "traces/v01.jsonl", "demarche": {"type": "déclaration préalable"}},
    MAISON["question"]: RuntimeError("serveur K2 injoignable"),
    DELAI["question"]: {"verdict_type": "information", "reponse": "Un mois.", "secondes": 13.0},
    CACHEE["question"]: {"verdict_type": "non", "regles": [{"article": "N 1", "verifiee": True}], "secondes": 8.0},
    CACHEE_2["question"]: {"verdict_type": "oui", "regles": [{"article": "UD 9", "verifiee": True}], "secondes": 9.0},
}


class FauxAgent:
    """Joue l'agent historique : pour chaque question, la réponse ou l'erreur prévue. Aucun modèle n'est appelé."""
    par = "K2 · historique"
    prevu = {}

    def repondre(self, question):
        r = self.prevu[question]
        if isinstance(r, Exception):
            raise r
        return {**r, "par": self.par}


class FauxAgentGrille(FauxAgent):
    """Joue la voie « grille »."""
    par = "K2 · grille"


@pytest.fixture
def banc(jeux, tmp_path, monkeypatch):
    """Le banc complet sans modèle : faux agents, faux jeux de questions, résultats écrits dans tmp_path."""
    ecrire(jeux / "questions-v2.json", [ABRI, MAISON, DELAI])
    ecrire(jeux / "questions-cachees.json", [CACHEE])
    ecrire(jeux / "questions-cachees-2.json", [CACHEE_2])
    resultats = tmp_path / "resultats"
    monkeypatch.setattr(notation, "RESULTATS", str(resultats))
    monkeypatch.setattr(notation, "Agent", FauxAgent)
    monkeypatch.setattr(grille, "AgentGrille", FauxAgentGrille)
    monkeypatch.setattr(FauxAgent, "prevu", dict(PREVU))

    def lancer(*options):
        monkeypatch.setattr(notation.sys, "argv", ["orbi-banc", *options])
        notation.main()
        (fichier,) = resultats.glob("banc-*.json")
        return fichier.name, json.loads(fichier.read_text(encoding="utf-8"))
    return lancer


def test_le_banc_note_chaque_question_et_publie_les_scores(banc, capsys):
    nom, d = banc()
    r = d["resume"]
    assert (r["questions"], r["banc"], r["pipeline"]) == (3, "questions-v2.json", "historique")
    assert r["scores"] == {"verdict": [2, 3], "sens": [1, 2], "grave": [2, 2], "demarche": [1, 1], "articles": [1, 2],
                           "citations": [3, 3], "garde_fous": [2, 3]}
    assert (r["temps_moyen_s"], r["temps_max_s"]) == (21.5, 30.0), "la question en erreur n'a pas de temps"
    assert r["efforts"] == [e for e, _ in notation.EFFORTS]
    v01 = d["lignes"][0]
    assert v01["attendu"] == ABRI["attendu"] and v01["demarche_obtenue"] == "déclaration préalable"
    assert set(v01["obtenu"]) == {"verdict_type", "reponse", "regles", "a_verifier", "garde_fous", "secondes", "par", "trace"}
    sortie = capsys.readouterr().out
    assert "V02  None s  attendu « non » obtenu « erreur »" in sortie
    assert nom in sortie


def test_une_erreur_de_l_agent_compte_comme_un_echec_sans_arreter_le_banc(banc):
    _, d = banc()
    v02 = d["lignes"][1]["obtenu"]
    assert (v02["verdict_type"], v02["reponse"], v02["garde_fous"]) == ("erreur", "RuntimeError: serveur K2 injoignable", ["erreur"])
    assert d["lignes"][1]["note"]["verdict"] is False and d["lignes"][1]["note"]["garde_fous"] is False
    assert d["lignes"][2]["id"] == "V03", "la question suivante a bien été posée"


def test_ids_limite_le_banc_aux_questions_choisies(banc):
    _, d = banc("--ids", "V01,V03")
    assert [l["id"] for l in d["lignes"]] == ["V01", "V03"] and d["resume"]["questions"] == 2


def test_sans_temps_mesure_pas_de_moyenne(banc, monkeypatch):
    monkeypatch.setattr(FauxAgent, "prevu", {ABRI["question"]: {"verdict_type": "oui sous conditions"}})
    _, d = banc("--ids", "V01")
    assert (d["resume"]["temps_moyen_s"], d["resume"]["temps_max_s"]) == (None, None)


BANCS = [
    pytest.param([], "questions-v2.json", "banc-", "historique", ["V01", "V02", "V03"], id="mise au point"),
    pytest.param(["--cache"], "questions-cachees.json", "banc-cache-", "historique", ["C01"], id="1er banc caché"),
    pytest.param(["--cache2"], "questions-cachees-2.json", "banc-cache2-", "historique", ["D01"], id="2e banc caché"),
    pytest.param(["--grille"], "questions-v2.json", "banc-grille-", "grille", ["V01", "V02", "V03"], id="voie grille"),
    pytest.param(["--cache2", "--grille"], "questions-cachees-2.json", "banc-cache2-grille-", "grille", ["D01"],
                 id="2e banc caché, voie grille"),
]


@pytest.mark.parametrize("options, fichier, prefixe, pipeline, ids", BANCS)
def test_le_banc_et_la_voie_choisis_se_retrouvent_dans_le_resultat(banc, options, fichier, prefixe, pipeline, ids):
    nom, d = banc(*options)
    assert re.fullmatch(re.escape(prefixe) + r"\d{8}-\d{4}\.json", nom), nom
    assert (d["resume"]["banc"], d["resume"]["pipeline"]) == (fichier, pipeline)
    assert [l["id"] for l in d["lignes"]] == ids
    assert d["lignes"][0]["obtenu"]["par"] == ("K2 · grille" if pipeline == "grille" else "K2 · historique")
