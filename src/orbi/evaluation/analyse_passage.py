"""Lit un ou deux passages du banc (résultats JSON) et résume : verdict exact, bon sens, contresens, « trop permissif » (permis alors que
le projet est interdit ou indéterminé), « trop timide » (indéterminé ou interdit alors que le projet est permis), par groupe et au total.
Usage : uv run python -m orbi.evaluation.analyse_passage bancs/resultats/banc-cache2-grille-XXXX.json [bancs/resultats/banc-cache2-XXXX.json]"""
import json
import os
import sys
from collections import defaultdict

from orbi.evaluation.notation import renoter  # noqa: E402
from orbi.domaine.verrou import verrou  # noqa: E402
from orbi.chemins import JEUX  # noqa: E402

CLASSE = {"oui": "permis", "oui sous conditions": "permis", "non": "interdit", "impossible à dire": "indéterminé"}


def lire(chemin):
    d = renoter(chemin)
    fichier = d["resume"].get("banc", "questions-v2.json")
    Q = {x["id"]: x for x in json.load(open(os.path.join(JEUX, fichier), encoding="utf-8"))}
    return d, Q


def resume(chemin):
    d, Q = lire(chemin)
    par_groupe = defaultdict(lambda: defaultdict(int))
    echecs = []
    for l in d["lignes"]:
        g = Q[l["id"]].get("groupe", "-")
        par_verrou = bool(verrou(Q[l["id"]].get("projet"), (Q[l["id"]].get("faits") or {}).get("zone")))  # décidé par le code, sans modèle
        att, obt = l["attendu"]["verdict_type"], l["obtenu"].get("verdict_type")
        ca, co = CLASSE.get(att), CLASSE.get(obt)
        cases = {"n": 1, "exact": att == obt and l["note"]["verdict"], "sens": bool(l["note"]["sens"]), "sens_n": l["note"]["sens"] is not None,
                 "contresens": ca is not None and co is not None and {ca, co} == {"permis", "interdit"},
                 "permissif": ca in ("interdit", "indéterminé") and co == "permis",
                 "timide": ca == "permis" and co in ("indéterminé", "interdit")}
        for k, v in cases.items():
            par_groupe[g][k] += int(bool(v))
            par_groupe["TOTAL"][k] += int(bool(v))
            par_groupe["verrou" if par_verrou else "modèle"][k] += int(bool(v))  # les cas du verrou de zone, et ceux où le modèle compte
        if not l["note"]["verdict"]:
            gr = ((l["obtenu"].get("trace") and None) or None)
            echecs.append((l["id"], g, att, obt, l["obtenu"].get("par"), l["question"][:110]))
    return d, par_groupe, echecs


def afficher(chemin):
    d, pg, echecs = resume(chemin)
    r = d["resume"]
    print(f"\n=== {os.path.basename(chemin)} · {r.get('pipeline')} · banc {r.get('banc')} · {r['questions']} questions · {r.get('temps_moyen_s')} s en moyenne")
    for g in sorted(pg, key=lambda x: (x in ("TOTAL", "verrou", "modèle"), x == "TOTAL", x)):
        c = pg[g]
        print(f"  {g:6s} n={c['n']:2d}  exact {c['exact']:2d}  bon sens {c['sens']:2d}/{c['sens_n']:2d}  contresens {c['contresens']}  trop permissif {c['permissif']}  trop timide {c['timide']}")
    for e in echecs:
        print("   ✗", e)


if __name__ == "__main__":
    for chemin in sys.argv[1:]:
        afficher(chemin)
