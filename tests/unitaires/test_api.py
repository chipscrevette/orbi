"""Le serveur local de l'application : l'état de la machine (sondes simulées), le flux d'une réponse (format, ordre des
événements, verrou « une question à la fois », services absents), et l'agent en direct de bout en bout avec un faux modèle."""
import json
import threading

import pytest
from fastapi.testclient import TestClient

from orbi.agent import historique
from orbi.api import etat as sondes
from orbi.api import flux, serveur
from orbi.api.flux import AgentEnDirect, lieu_depuis_faits, repondre_en_direct, reponse_depuis_resultat, sse
from orbi.modele import cerveau
from tests.faux import FausseRecherche, FauxCerveau, faits, ligne, tri

PHRASE_UD7 = "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci."


def lire_flux(texte):
    """Les événements (nom, données) d'un flux SSE ; les battements de cœur (« : … ») sont ignorés."""
    out = []
    for bloc in texte.split("\n\n"):
        lignes = [x for x in bloc.split("\n") if x and not x.startswith(":")]
        if lignes:
            nom = next(x[len("event: "):] for x in lignes if x.startswith("event: "))
            out.append((nom, json.loads(next(x[len("data: "):] for x in lignes if x.startswith("data: ")))))
    return out


# ------------------------------------------------------------------------------------------------ le format
def test_un_evenement_tient_en_deux_lignes_et_une_ligne_vide():
    texte = sse("etape", {"id": "contrôle", "t": 56.1, "note": "une ligne\npuis une autre"})
    assert texte.startswith("event: etape\ndata: {") and texte.endswith("}\n\n")
    assert texte.count("\n") == 3, "le JSON ne doit jamais couper la ligne data"
    assert lire_flux(texte) == [("etape", {"id": "contrôle", "t": 56.1, "note": "une ligne\npuis une autre"})]


def test_le_lieu_reprend_les_faits_des_outils():
    f = faits(zone="UH", surface=345, spr=True)
    lieu = lieu_depuis_faits(f)
    assert lieu["zone"] == "UH" and lieu["surface_m2"] == 345 and lieu["site_patrimonial"] is True
    assert lieu["commune"] == "Biarritz" and lieu["adresse"]
    assert lieu_depuis_faits(f, zone="UHa")["zone"] == "UHa", "la zone retenue par l'agent passe avant celle de l'API"


def test_un_lieu_sans_faits_ne_plante_pas():
    assert lieu_depuis_faits(None) == {"adresse": None, "commune": None, "point": None, "parcelle": None, "surface_m2": None,
                                       "zone": None, "servitudes": [], "site_patrimonial": False}


def test_la_reponse_ne_garde_que_ce_que_l_application_affiche():
    res = {"verdict_type": "non", "reponse": "Non.", "zone": "UD", "secondes": 53.8, "faits": {"x": 1}, "grille": {"y": 2},
           "regles": [{"article": "UD 7", "citation": PHRASE_UD7, "page": 69, "verifiee": True, "passage": "A"}]}
    r = reponse_depuis_resultat(res)
    assert r == {"verdict": "non", "texte": "Non.", "regles": [{"article": "UD 7", "citation": PHRASE_UD7, "page": 69,
                                                                 "verifiee": True}],
                 "a_verifier": [], "demarche": None, "zone": "UD", "duree_s": 53.8, "demo": False}


# ------------------------------------------------------------------------------------------------ les sondes
@pytest.mark.parametrize("sortie, attendu", [
    ("NVIDIA GeForce RTX 3060, 6213, 12288\n", {"nom": "RTX 3060", "utilise_go": 6.1, "total_go": 12.0}),
    ("NVIDIA RTX A4000, 1024, 16376\nNVIDIA RTX A4000, 0, 16376\n", {"nom": "RTX A4000", "utilise_go": 1.0, "total_go": 16.0}),
    ("", None), (None, None), ("pas de carte\n", None), ("RTX, beaucoup, 12288", None),
], ids=["une carte", "la première de deux cartes", "vide", "rien", "message d'erreur", "nombre illisible"])
def test_la_sortie_de_nvidia_smi_est_lue(sortie, attendu):
    assert sondes.lire_nvidia_smi(sortie) == attendu


def test_un_port_ferme_n_est_pas_ouvert():
    assert sondes.port_ouvert(("127.0.0.1", 1), delai=0.2) is False


def test_le_cadastre_n_est_sonde_qu_une_fois_toutes_les_cinq_minutes(monkeypatch):
    appels = []
    monkeypatch.setattr(sondes, "port_ouvert", lambda adresse, delai=0.5: appels.append(adresse) or True)
    monkeypatch.setitem(sondes._memo_cadastre, "ok", None)
    assert sondes.cadastre_joignable(maintenant=1000) and sondes.cadastre_joignable(maintenant=1200)
    assert len(appels) == 1
    sondes.cadastre_joignable(maintenant=1400)
    assert len(appels) == 2


def test_le_dernier_banc_donne_son_score_et_son_temps_moyen():
    b = sondes.dernier_banc()
    assert b == {"juste": 27, "total": 40, "date": "2026-10-02", "temps_moyen_s": 65.6}


def test_un_banc_absent_ne_plante_pas():
    assert sondes.dernier_banc.__wrapped__("banc-qui-n-existe-pas.json") is None


@pytest.fixture
def machine(monkeypatch):
    """Une machine simulée : ports, carte graphique et mémoire choisis par le test."""
    ouverts = {sondes.K2: True, sondes.EMBEDDINGS: True, sondes.CADASTRE: True}
    monkeypatch.setattr(sondes, "port_ouvert", lambda adresse, delai=0.5: ouverts[adresse])
    monkeypatch.setattr(sondes, "gpu", lambda: {"nom": "RTX 3060", "utilise_go": 6.1, "total_go": 12.0})
    monkeypatch.setattr(sondes, "memoire", lambda: {"utilise_go": 14.2, "total_go": 16.0})
    monkeypatch.setitem(sondes._memo_cadastre, "ok", None)
    return ouverts


def test_l_etat_complet_quand_tout_tourne(machine):
    e = sondes.etat()
    assert e["mode"] == "local" and e["modele"] == {"nom": "K2 Horizon 7B", "en_ligne": True}
    assert e["gpu"]["nom"] == "RTX 3060" and e["memoire"]["total_go"] == 16.0
    assert e["temps_reponse_s"] == 65.6, "sans réponse dans la session, le temps moyen du dernier banc"
    assert e["base"]["plu"]["connectee"] and e["base"]["plu"]["zones"] == 178 and e["base"]["plu"]["passages"] == 493
    assert e["base"]["plu"]["articles"] == 189
    assert e["base"]["cadastre"] == {"connectee": True, "source": "API Carto IGN"}
    assert e["banc"] == {"juste": 27, "total": 40, "date": "2026-10-02"}


def test_le_temps_de_reponse_est_celui_de_la_session(machine):
    assert sondes.etat([50.0, 61.0])["temps_reponse_s"] == 55.5


@pytest.mark.parametrize("eteint", ["k2", "embeddings"])
def test_sans_modele_ou_sans_recherche_l_application_passe_en_demo(machine, eteint):
    machine[sondes.K2 if eteint == "k2" else sondes.EMBEDDINGS] = False
    assert sondes.etat()["mode"] == "demo"
    assert "port 11500" in sondes.services_manquants() if eteint == "k2" else "port 11600" in sondes.services_manquants()


def test_rien_ne_manque_quand_tout_tourne(machine):
    assert sondes.services_manquants() is None


# ------------------------------------------------------------------------------------------------ le serveur
def faux_repondre(evenements):
    """Un agent simulé : rejoue des événements, puis signale qu'il a fini (ce qui libère le verrou)."""
    def repondre(question, dossier_traces=None, a_la_fin=None):
        repondre.question = question
        try:
            yield from evenements
        finally:
            a_la_fin()
    return repondre


REPONSE = {"verdict": "non", "texte": "Non.", "regles": [], "a_verifier": [], "demarche": None, "zone": "UD", "duree_s": 42.0,
           "demo": False}


@pytest.fixture
def client(machine, tmp_path):
    def fabriquer(evenements):
        app = serveur.creer_application(interface=str(tmp_path / "pas-d-interface"), dossier_traces=str(tmp_path),
                                        repondre=faux_repondre(evenements))
        return app, TestClient(app)
    return fabriquer


def test_une_question_donne_les_etapes_le_lieu_puis_la_reponse(client):
    evts = [("etape", {"id": "tri", "t": 6.2}), (None, None), ("lieu", {"zone": "UD"}), ("etape", {"id": "fin", "t": 42.0}),
            ("reponse", REPONSE)]
    app, c = client(evts)
    r = c.post("/api/question", json={"question": "  Puis-je poser un abri au 5 impasse Monnier ?  "})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    assert ": battement" in r.text
    assert lire_flux(r.text) == [e for e in evts if e[0]]
    assert app.state.durees[-1] == 42.0
    assert c.get("/api/etat").json()["temps_reponse_s"] == 42.0
    assert not app.state.occupe.locked(), "le verrou est rendu"


def test_une_seule_question_a_la_fois(client):
    app, c = client([("reponse", REPONSE)])
    app.state.occupe.acquire()
    evts = lire_flux(c.post("/api/question", json={"question": "Puis-je poser un abri ?"}).text)
    assert evts[0][0] == "erreur" and "déjà" in evts[0][1]["message"]
    app.state.occupe.release()


def test_sans_modele_une_erreur_explique_comment_le_lancer(client, machine):
    machine[sondes.K2] = False
    app, c = client([("reponse", REPONSE)])
    evts = lire_flux(c.post("/api/question", json={"question": "Puis-je poser un abri ?"}).text)
    assert evts == [("erreur", {"message": sondes.services_manquants()})]
    assert not app.state.occupe.locked()


@pytest.mark.parametrize("corps", [{"question": ""}, {"question": "ab"}, {"question": "x" * 2001}, {}],
                         ids=["vide", "trop courte", "trop longue", "absente"])
def test_une_question_invalide_est_refusee(client, corps):
    _, c = client([])
    assert c.post("/api/question", json=corps).status_code == 422


def test_l_interface_construite_est_servie_a_la_racine(machine, tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html><title>Orbi</title>", encoding="utf-8")
    c = TestClient(serveur.creer_application(interface=str(tmp_path)))
    assert "<title>Orbi</title>" in c.get("/").text
    assert c.get("/api/etat").status_code == 200, "l'API passe avant les fichiers"


def test_sans_interface_construite_l_api_marche_quand_meme(machine, tmp_path):
    c = TestClient(serveur.creer_application(interface=str(tmp_path / "absent")))
    assert c.get("/").status_code == 404 and c.get("/api/etat").status_code == 200
    assert c.get("/api/docs").status_code == 200


# ------------------------------------------------------------------------------------------------ l'agent en direct
@pytest.fixture
def faux_agent(monkeypatch):
    """L'agent grille réel, avec un faux modèle, une fausse recherche et des faits fixés : aucun réseau, aucun GPU."""
    def installer(*reponses, faits_parcelle=None):
        monkeypatch.delenv("PLU_SANS_TRACE", raising=False)
        monkeypatch.setattr(historique, "Recherche", FausseRecherche)
        monkeypatch.setattr(cerveau, "demander", FauxCerveau(*reponses))
        monkeypatch.setattr(historique, "outils_faits", lambda adresse, question, parcelle=None: faits_parcelle or faits(zone="UD"))
    return installer


def test_l_agent_en_direct_envoie_chaque_etape_au_fil_de_l_eau(faux_agent, tmp_path):
    analyse = {"regles": [ligne(PHRASE_UD7, seuil=3, sens="limite_ou_au_moins", valeur=0.5, statut="respectee",
                                exigence="sur la limite ou à 3 m au moins")]}
    faux_agent(tri("abri de jardin", surface=8), analyse)
    fini = threading.Event()
    evts = list(repondre_en_direct("Je veux poser un abri de jardin de 8 m² à 50 cm de la limite, au 5 impasse Monnier "
                                   "à Biarritz.", dossier_traces=str(tmp_path), a_la_fin=fini.set))
    noms = [n for n, _ in evts]
    etapes = [d["id"] for n, d in evts if n == "etape"]
    assert etapes[:2] == ["tri", "outils"] and "analyse" in etapes and "contrôle" in etapes and etapes[-1] == "fin"
    assert noms.index("lieu") == noms.index("etape") + 2, "le lieu part juste après l'étape « outils »"
    assert noms[-1] == "reponse" and evts[-1][1]["verdict"] == "non", "le code recalcule 0,5 m < 3 m"
    assert evts[-1][1]["regles"][0]["article"] == "UD 7" and evts[-1][1]["regles"][0]["verifiee"]
    assert fini.is_set()
    assert len(list(tmp_path.glob("*.jsonl"))) == 1, "la trace est rangée dans le dossier de l'application"


def test_une_panne_de_l_agent_devient_une_erreur_lisible(faux_agent, tmp_path):
    faux_agent(tri("abri de jardin", surface=8))

    class Panne(AgentEnDirect):
        def repondre(self, question):
            raise ConnectionError("API Carto injoignable")
    fini = threading.Event()
    evts = list(repondre_en_direct("Abri au 5 impasse Monnier ?", a_la_fin=fini.set, fabrique=Panne))
    assert evts == [("erreur", {"message": "Orbi n'a pas pu finir sa réponse (ConnectionError : API Carto injoignable)."})]
    assert fini.is_set(), "le verrou est rendu même après une panne"


def test_un_battement_de_coeur_quand_l_agent_reflechit_longtemps(faux_agent):
    lent = threading.Event()

    class Lent(AgentEnDirect):
        def repondre(self, question):
            lent.wait(0.3)
            return {"verdict_type": "oui", "reponse": "Oui.", "secondes": 0.3}
    evts = list(repondre_en_direct("Abri ?", fabrique=Lent, battement=0.05))
    assert (None, None) in evts and evts[-1][0] == "reponse"
    assert flux.BATTEMENT == 10
