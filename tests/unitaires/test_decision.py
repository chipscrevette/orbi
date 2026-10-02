"""Le moteur de décision : du Python pur, sans modèle. Un cas = une situation réelle et le verdict attendu."""
import pytest

from orbi.domaine.decision import decider
from tests.unitaires.cas_decision import CAS


@pytest.mark.parametrize("groupe, nom, regles, attendu, verrou, abf, stricte", CAS, ids=[f"{c[0]} · {c[1]}" for c in CAS])
def test_verdict(groupe, nom, regles, attendu, verrou, abf, stricte):
    d = decider([dict(r) for r in regles], verrou=verrou, abf=abf, zone_stricte=stricte)
    assert d["verdict"] == attendu, f"raison donnée par le moteur : {d['raison']}"


def test_les_quatre_groupes_sont_couverts():
    groupes = {c[0] for c in CAS}
    assert {"permis", "interdit", "manquant", "restrictif", "garde-fous"} <= groupes
