"""Le rejeu : refaire tourner l'agent sur les réponses enregistrées du modèle (les traces), sans K2.

Tout ce qui entoure le modèle (outils publics en cache, démarche, verrou, recherche d'articles, contrôles, décision, fiche) est
du code déterministe : rejoué sur les mêmes réponses du modèle, il doit redonner exactement les mêmes résultats. C'est le filet
de sécurité avant de découper un module, et le test de non-régression de tout changement du code qui n'est pas le modèle.
Usage : uv run python -m orbi.evaluation.rejeu bancs/resultats/banc-XXXX.json [--ids V01,V02]"""
import json
import os
import sys

os.environ["PLU_SANS_TRACE"] = "1"
from orbi.modele import cerveau  # noqa: E402
from orbi.agent.historique import Agent  # noqa: E402
from orbi.evaluation.traces import trace_locale  # noqa: E402


def sequence(trace):
    """Les réponses du modèle dans l'ordre où l'agent les a demandées, et le résultat enregistré."""
    ev = [json.loads(x) for x in open(trace, encoding="utf-8")]
    seq = []
    for e in ev:
        if e["etape"] == "tri":
            seq.append(e["resultat"])
        elif e["etape"] == "rédaction" or e["etape"].startswith("nouvel essai") or e["etape"] == "correction":
            seq.append(e.get("reponse"))
        elif e["etape"] in ("analyse", "nouvelle analyse"):
            seq.append({"regles": e["regles"]} if e.get("regles") is not None else None)
    return seq, ev[-1]["resultat"]


class ModeleEnregistre:
    def __init__(self, seq):
        self.seq = list(seq)

    def __call__(self, *a, **k):
        obj = self.seq.pop(0) if self.seq else None
        return obj, {"secondes": 0, "jetons": 0, "effort": k.get("effort"), "reflexion": "", "brut": ""}


def empreinte(res):
    return {"verdict": res.get("verdict_type"), "reponse": res.get("reponse"),
            "regles": [(g.get("article"), g.get("citation")) for g in res.get("regles") or []],
            "garde_fous": res.get("garde_fous"), "demarche": (res.get("demarche") or {}).get("type"),
            "a_verifier": res.get("a_verifier")}


def rejouer(chemin, ids=None):
    """Rejoue un passage enregistré : → (identiques, nombre de questions, différences [(id, {champ: (avant, après)})]).
    Le vrai modèle n'est jamais appelé : cerveau.demander est remplacé, le temps du rejeu, par les réponses enregistrées."""
    d = json.load(open(chemin, encoding="utf-8"))
    grille = d["resume"].get("pipeline") == "grille"
    if grille:
        from orbi.agent.grille import AgentGrille
        agent = AgentGrille()
    else:
        agent = Agent()
    identiques, diffs = 0, []
    lignes = [l for l in d["lignes"] if not ids or l["id"] in ids]
    vrai = cerveau.demander
    try:
        for l in lignes:
            trace = trace_locale(l["obtenu"].get("trace"))
            if not trace:
                continue
            seq, enregistre = sequence(trace)
            cerveau.demander = ModeleEnregistre(seq)
            try:
                rejoue = agent.repondre(l["question"])
            except Exception as e:  # noqa: BLE001
                diffs.append((l["id"], {"erreur": f"{type(e).__name__}: {e}"}))
                continue
            a, b = empreinte(enregistre), empreinte(rejoue)
            if a == b:
                identiques += 1
            else:
                diffs.append((l["id"], {k: (a[k], b[k]) for k in a if a[k] != b[k]}))
    finally:
        cerveau.demander = vrai
    return identiques, len(lignes), diffs, grille


def main(chemin, ids=None):
    identiques, n, diffs, grille = rejouer(chemin, ids)
    print(f"{identiques}/{n} questions rejouées à l'identique ({'grille' if grille else 'agent historique'})")
    for i, dd in diffs:
        print("  différence", i, json.dumps(dd, ensure_ascii=False)[:400])
    return not diffs


if __name__ == "__main__":
    ids = set(sys.argv[sys.argv.index("--ids") + 1].split(",")) if "--ids" in sys.argv else None
    sys.exit(0 if main(sys.argv[1], ids) else 1)
