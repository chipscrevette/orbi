"""Le texte sort du verdict : sur chacun des cas du moteur de décision, la fiche composée par le code doit commencer par le mot
du verdict et ne jamais contenir le mot du verdict contraire. C'est la garantie « plus de contradiction verdict / texte » (au banc,
V28 écrivait « Oui, vous pouvez poser un abri » puis « l'abri est interdit »)."""
import pytest

from tests.unitaires.cas_decision import CAS
from orbi.domaine.decision import decider
from orbi.domaine.fiche import _manque, composer

DEBUT = {"non": "Non", "oui": "Oui, ce projet respecte", "oui sous conditions": "Oui, sous conditions",
         "impossible à dire": ("Je ne peux pas conclure", "Je n'ai trouvé aucune règle")}
VERROU = {"verdicts": ["non"], "article": "Ncu 1", "citation": "Toutes constructions", "pourquoi": "une maison neuve n'entre dans aucune exception"}
DEM = {"type": "déclaration préalable", "pourquoi": "de 5 à 20 m²", "delai": "1 mois"}


@pytest.mark.parametrize("groupe, nom, regles, attendu, verrou, abf, stricte", CAS, ids=[f"{c[0]} · {c[1]}" for c in CAS])
def test_la_fiche_dit_le_verdict(groupe, nom, regles, attendu, verrou, abf, stricte):
    regles = [dict(r, article="UD 7", constat="Votre projet est à 0,5 m", citation="une phrase du règlement", page=69,
                   exigence=r.get("exigence") or "une règle", nature=r["nature"]) for r in regles]
    d = decider(regles, verrou=verrou, abf=abf, zone_stricte=stricte)
    verrou_fiche = dict(verrou, article="N 2", citation="les annexes", pourquoi="une annexe n'est admise que pour une maison de 1995",
                        fait_manquant="la date de la maison") if verrou and "impossible à dire" in verrou["verdicts"] else (
        dict(verrou, article="Ncu 1", citation="Toutes constructions", pourquoi="aucune exception ne couvre ce projet") if verrou else None)
    texte = composer(d, regles, DEM, verrou=verrou_fiche)["reponse"]
    debut = DEBUT[d["verdict"]]
    assert texte.strip()
    assert texte.startswith(debut) if isinstance(debut, str) else any(texte.startswith(x) for x in debut), texte[:120]
    # un « oui » ne contient pas « Non, ce projet » ; un « non » ou un « impossible à dire » ne commence pas par « Oui »
    if d["verdict"] in ("oui", "oui sous conditions"):
        assert "Non, ce projet" not in texte
    else:
        assert not texte.startswith("Oui")
    if d["verdict"] == "non":
        assert "Démarche" not in texte, "pas de démarche pour un projet interdit"


@pytest.mark.parametrize("avant, apres", [
    ("le projet ne précise pas si le rehaussement est une saillie", "si le rehaussement est une saillie"),
    ("la question ne donne pas la hauteur actuelle", "la hauteur actuelle"),
    ("la date de la maison", "la date de la maison"),
])
def test_un_fait_manquant_s_ecrit_comme_un_fait(avant, apres):
    assert _manque(avant) == apres
