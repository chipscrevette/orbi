"""Des tests qui ne détectent aucune panne ne prouvent rien. On casse volontairement le moteur de décision, en mémoire, de
plusieurs façons, et on vérifie que les cas du moteur s'en aperçoivent : chaque mutation doit faire échouer au moins un cas."""
import pytest

import orbi.domaine.decision as decision
from tests.unitaires.cas_decision import CAS

SOURCE = open(decision.__file__, encoding="utf-8").read()
MUTATIONS = [
    ("une violation ne donne plus « non »", 'return rendre("non", "violation")  # au moins une violation', 'return rendre("oui", "violation")  # au moins une violation'),
    ("une violation en zone stricte ne donne plus « non »", 'if zone_stricte:\n            return rendre("non", "violation")', 'if zone_stricte:\n            return rendre("oui", "violation")'),
    ("une exception lève les violations de tous les articles", 'return a == regle.get("article") or str(a or "").startswith("DG")', "return True"),
    ("l'absence de règle autorise", 'return rendre("impossible à dire", "aucune_regle")\n\n    # 6, 7.', 'return rendre("oui", "aucune_regle")\n\n    # 6, 7.'),
    ("l'avis de l'ABF est oublié", "    if abf:\n        return rendre(\"oui sous conditions\", \"abf\")\n", ""),
    ("la zone stricte autorise sans exception", 'return rendre("impossible à dire", "aucune_regle")\n\n    # 3b', 'return rendre("oui", "aucune_regle")\n\n    # 3b'),
    ("un fait décisif manquant est ignoré", 'if decisives:\n        return rendre("impossible à dire", "inconnu_decisif")', "if False:\n        return rendre(\"impossible à dire\", \"inconnu_decisif\")"),
]


@pytest.mark.parametrize("nom, avant, apres", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_la_mutation_est_detectee(nom, avant, apres):
    assert avant in SOURCE, f"motif introuvable : {nom} (le moteur a changé : mettre la mutation à jour)"
    espace = {}
    exec(compile(SOURCE.replace(avant, apres, 1), "decision_mutee", "exec"), espace)
    echecs = sum(1 for _, _, regles, attendu, verrou, abf, stricte in CAS
                 if espace["decider"]([dict(r) for r in regles], verrou=verrou, abf=abf, zone_stricte=stricte)["verdict"] != attendu)
    assert echecs > 0, f"la panne « {nom} » passe inaperçue"
