"""Le client du modèle local : extraire le JSON d'une réponse quoi qu'il y ait autour, et parler au serveur K2 avec un format
de réponse imposé. Un faux serveur remplace le vrai : aucun modèle n'est chargé."""
import pytest
import requests

from orbi.modele import cerveau
from orbi.modele.cerveau import premier_json


# ------------------------------------------------------------------------------------------------ extraire le JSON
@pytest.mark.parametrize("texte, attendu", [
    ('{"a": 1}', {"a": 1}),
    ('```json\n{"a": 1}\n```', {"a": 1}),
    ('Voici ma réponse : {"verdict": "non"} Fin.', {"verdict": "non"}),
    ('{"texte": "une accolade } dans une chaîne", "n": 2}', {"texte": "une accolade } dans une chaîne", "n": 2}),
    ('{"texte": "un guillemet \\" échappé"}', {"texte": 'un guillemet " échappé'}),
    ('{"a": {"b": [1, {"c": 2}]}}', {"a": {"b": [1, {"c": 2}]}}),
    ('{pas du json} puis {"bon": true}', {"bon": True}),
], ids=["JSON seul", "bloc de code", "texte autour", "accolade dans une chaîne", "guillemet échappé", "imbriqué",
        "un faux départ puis le vrai"])
def test_le_premier_json_valide_est_trouve(texte, attendu):
    assert premier_json(texte) == attendu


@pytest.mark.parametrize("texte", [None, "", "aucune accolade", "{ inachevé"], ids=["None", "vide", "sans JSON", "inachevé"])
def test_sans_json_valide_rien_n_est_invente(texte):
    assert premier_json(texte) is None


# ------------------------------------------------------------------------------------------------ parler au serveur
class FauxServeur:
    def __init__(self, message, eval_count=42):
        self.message, self.eval_count, self.corps = message, eval_count, None

    def __call__(self, url, json=None, timeout=None):
        self.url, self.corps = url, json
        serveur = self

        class Reponse:
            def json(self):
                return {"message": serveur.message, "eval_count": serveur.eval_count}
        return Reponse()


def test_la_demande_impose_le_format_et_l_effort(monkeypatch):
    faux = FauxServeur({"content": '{"ok": true}', "thinking": "je réfléchis"})
    monkeypatch.setattr(cerveau.requests, "post", faux)
    schema = {"type": "object"}
    obj, trace = cerveau.demander("système", "question", schema, effort="medium", max_jetons=900, temperature=0.5,
                                  historique=[{"role": "user", "content": "avant"}])
    assert obj == {"ok": True}
    c = faux.corps
    assert faux.url == cerveau.K2 and c["stream"] is False and c["format"] == schema and c["think"] == "medium"
    assert c["options"] == {"temperature": 0.5, "num_predict": 900}
    assert [m["role"] for m in c["messages"]] == ["system", "user", "user"], "système, historique, puis la question"
    assert trace["jetons"] == 42 and trace["effort"] == "medium" and trace["reflexion"] == "je réfléchis"
    assert trace["brut"] == '{"ok": true}' and trace["secondes"] >= 0


def test_un_json_cache_dans_la_reflexion_est_recupere(monkeypatch):
    """Quand la réflexion mange tous les jetons, la réponse peut n'exister que dans la réflexion."""
    monkeypatch.setattr(cerveau.requests, "post", FauxServeur({"content": "", "thinking": 'brouillon {"verdict": "oui"}'}))
    obj, _ = cerveau.demander("s", "u", {})
    assert obj == {"verdict": "oui"}


def test_une_reponse_sans_json_rend_none(monkeypatch):
    monkeypatch.setattr(cerveau.requests, "post", FauxServeur({"content": "je ne sais pas"}))
    obj, trace = cerveau.demander("s", "u", {})
    assert obj is None and trace["brut"] == "je ne sais pas"


def test_pret_quand_le_serveur_repond(monkeypatch):
    monkeypatch.setattr(cerveau.requests, "post", FauxServeur({"content": "ok"}))
    assert cerveau.pret() is True


def test_pas_pret_quand_le_serveur_est_eteint(monkeypatch):
    def eteint(*a, **k):
        raise requests.ConnectionError("refusé")
    monkeypatch.setattr(cerveau.requests, "post", eteint)
    assert cerveau.pret() is False
