"""Rejoue, avec le même code, les questions d'un passage du banc où les API publiques n'ont pas répondu (« je ne trouve pas cette
adresse », « je ne trouve pas la zone du PLU de ce terrain »). Ces réponses ne disent rien du modèle ni de la table de décision : l'agent n'a
reçu aucun fait. Règle écrite avant la lecture du passage de l'ancien agent : une question dont la réponse est une panne d'API est rejouée
une fois, pour les deux agents, quand les API répondent. Le passage d'origine est gardé tel quel ; le nouveau fichier porte « reprise_api ».
Usage : uv run python -m orbi.evaluation.rejouer_infra bancs/resultats/banc-cache2-grille-XXXX.json [--grille]"""
import json
import os
import sys
import time
from datetime import datetime

from orbi.evaluation import notation as banc  # noqa: E402
from orbi.outils.geo import adresse  # noqa: E402
from orbi.chemins import JEUX  # noqa: E402

PANNES = ("ne trouve pas cette adresse", "ne trouve pas la zone du PLU")


def api_repond():
    """Le géocodeur répond-il pour une adresse qui existe ?"""
    t = time.time()
    a = adresse("1 avenue de la Marne, Biarritz", "64122")
    return bool(a), round(time.time() - t, 1)


def main(chemin, grille):
    d = json.load(open(chemin, encoding="utf-8"))
    fichier = d["resume"]["banc"]
    Q = {x["id"]: x for x in json.load(open(os.path.join(JEUX, fichier), encoding="utf-8"))}
    pannes = [l["id"] for l in d["lignes"] if any(p in (l["obtenu"].get("reponse") or "") for p in PANNES)]
    print("questions en panne d'API :", pannes)
    if not pannes:
        return
    ok, s = api_repond()
    print(f"le géocodeur répond : {ok} ({s} s)")
    if not ok:
        print("les API ne répondent pas encore : rien n'est rejoué")
        return
    if grille:
        from orbi.agent.grille import AgentGrille
        agent = AgentGrille()
    else:
        from orbi.agent.historique import Agent
        agent = Agent()
    for i in pannes:
        x = Q[i]
        res = agent.repondre(x["question"])
        n = banc.noter(x, res)
        nouvelle = {"id": i, "question": x["question"], "attendu": x["attendu"], "obtenu": {
            k: res.get(k) for k in ("verdict_type", "reponse", "regles", "a_verifier", "garde_fous", "secondes", "par", "trace")},
            "demarche_obtenue": (res.get("demarche") or {}).get("type"), "note": n, "premiere_reponse": next(
                l["obtenu"].get("verdict_type") for l in d["lignes"] if l["id"] == i)}
        d["lignes"] = [nouvelle if l["id"] == i else l for l in d["lignes"]]
        print(f"{i}  {res.get('secondes')} s  attendu « {x['attendu']['verdict_type']} » obtenu « {res.get('verdict_type')} »  "
              + " ".join(f"{k}:{'✓' if v else '✗'}" for k, v in n.items() if v is not None), flush=True)
    d["resume"]["reprise_api"] = pannes
    d["resume"]["scores"] = {k: (sum(1 for l in d["lignes"] if l["note"][k]), sum(1 for l in d["lignes"] if l["note"][k] is not None))
                             for k in ("verdict", "sens", "grave", "demarche", "articles", "citations", "garde_fous")}
    sortie = chemin.replace(".json", "-reprise.json")
    json.dump(d, open(sortie, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("résultats :", sortie, "·", datetime.now().strftime("%H:%M"))


if __name__ == "__main__":
    main(sys.argv[1], "--grille" in sys.argv)
