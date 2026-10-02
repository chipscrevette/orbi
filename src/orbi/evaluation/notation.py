"""Le banc d'essai : l'agent répond aux 30 questions (bancs/jeux/questions-v2.json), le code note.
  verdict     le type de verdict est-il le bon ? (oui, sous conditions, non, impossible à dire, information, hors périmètre)
  démarche    la démarche calculée est-elle la bonne ? (seulement quand la question en appelle une)
  articles    au moins un des articles attendus est-il cité ?
  citations   toutes les citations existent-elles mot pour mot dans leur article ?
  garde-fous  aucune faute restante (zone, chiffres, secteur transposé) ?
Usage : uv run orbi-banc [--grille] [--cache | --cache2] [--ids V01,V05] ; résultats dans bancs/resultats/banc-<date>.json"""
import json
import os
import sys
import time
from datetime import datetime

from orbi.agent.historique import EFFORTS, Agent
from orbi.reglement.donnees import RACINE
from orbi.chemins import JEUX, RESULTATS  # noqa: E402


def normer_dem(t):
    t = (t or "").strip()
    return "dépend" if t.startswith("dépend") else t


SENS = {"oui": 1, "oui sous conditions": 1, "non": -1}
# le sens du verdict : « oui » et « oui sous conditions » sont deux nuances du même sens (permis) ; « non » et « impossible à dire »
# sont d'autres sens. Dire « oui » au lieu de « oui sous conditions » est une nuance ; dire « non » au lieu de « oui » est une erreur.
CLASSE = {"oui": "permis", "oui sous conditions": "permis", "non": "interdit", "impossible à dire": "indéterminé"}


def noter(x, res):
    a = x["attendu"]
    cites = [g.get("article") for g in res.get("regles") or []]
    sens_a, sens_o = SENS.get(a["verdict_type"]), SENS.get(res.get("verdict_type"))
    # sans réponse du modèle, l'agent affiche « impossible à dire » par défaut : ce n'est pas un verdict juste, même
    # quand c'est la valeur attendue (V16 et V26 au 1er passage)
    sans_reponse = "réponse illisible (pas de JSON)" in (res.get("garde_fous") or [])
    n = {"verdict": res.get("verdict_type") == a["verdict_type"] and not sans_reponse,
         # l'erreur grave : dire oui quand c'est non, ou non quand c'est oui (confondre « oui » et « oui sous
         # conditions » est une nuance ; répondre « impossible à dire » est prudent, pas grave)
         "sens": None if a["verdict_type"] not in CLASSE else CLASSE[a["verdict_type"]] == CLASSE.get(res.get("verdict_type")) and not sans_reponse,
         "grave": None if sens_a is None else not (sens_o is not None and sens_o == -sens_a),
         "demarche": None if a["demarche_type"] == "sans objet" else
         normer_dem((res.get("demarche") or {}).get("type")) == normer_dem(a["demarche_type"]),
         "articles": None if not a["articles"] or a["verdict_type"] == "hors périmètre" else any(c in a["articles"] for c in cites),
         "citations": all(g.get("verifiee") for g in res.get("regles") or []),
         "garde_fous": not res.get("garde_fous")}
    return n


def main():
    ids = None
    if "--ids" in sys.argv:
        ids = set(sys.argv[sys.argv.index("--ids") + 1].split(","))
    # le banc de mise au point (questions-v2), le 1er banc caché (--cache, déjà connu) ou le 2e (--cache2, passé une seule fois)
    fichier = ("questions-cachees-2.json" if "--cache2" in sys.argv else
               "questions-cachees.json" if "--cache" in sys.argv else "questions-v2.json")
    Q = json.load(open(os.path.join(JEUX, fichier), encoding="utf-8"))
    Q = [x for x in Q if not ids or x["id"] in ids]
    if "--grille" in sys.argv:  # la voie « grille » (orbi.agent.grille), comparée à l'agent historique sur les mêmes questions
        from orbi.agent.grille import AgentGrille
        agent = AgentGrille()
    else:
        agent = Agent()
    lignes, t0 = [], time.time()
    for x in Q:
        try:
            res = agent.repondre(x["question"])
        except Exception as e:  # une erreur ne doit pas arrêter le banc : elle compte comme un échec
            res = {"verdict_type": "erreur", "reponse": f"{type(e).__name__}: {e}", "regles": [], "garde_fous": ["erreur"],
                   "secondes": None}
        n = noter(x, res)
        lignes.append({"id": x["id"], "question": x["question"], "attendu": x["attendu"], "obtenu": {
            k: res.get(k) for k in ("verdict_type", "reponse", "regles", "a_verifier", "garde_fous", "secondes", "par", "trace")},
            "demarche_obtenue": (res.get("demarche") or {}).get("type"), "note": n})
        ok = " ".join(f"{k}:{'✓' if v else '✗'}" for k, v in n.items() if v is not None)
        print(f"{x['id']}  {res.get('secondes')} s  attendu « {x['attendu']['verdict_type']} » obtenu "
              f"« {res.get('verdict_type')} »  {ok}", flush=True)
    total = {k: (sum(1 for l in lignes if l["note"][k]), sum(1 for l in lignes if l["note"][k] is not None))
             for k in ("verdict", "sens", "grave", "demarche", "articles", "citations", "garde_fous")}
    temps = [l["obtenu"]["secondes"] for l in lignes if l["obtenu"]["secondes"]]
    resume = {"date": datetime.now().isoformat(timespec="seconds"), "questions": len(lignes), "scores": total,
              "efforts": [e for e, _ in EFFORTS], "banc": fichier, "pipeline": "grille" if "--grille" in sys.argv else "historique",
              "temps_moyen_s": round(sum(temps) / len(temps), 1) if temps else None,
              "temps_max_s": max(temps) if temps else None, "duree_totale_s": round(time.time() - t0)}
    print("\n" + json.dumps(resume, ensure_ascii=False, indent=1))
    os.makedirs(RESULTATS, exist_ok=True)
    prefixe = ("cache2-" if "--cache2" in sys.argv else "cache-" if "--cache" in sys.argv else "") + ("grille-" if "--grille" in sys.argv else "")
    chemin = os.path.join(RESULTATS, f"banc-{prefixe}{datetime.now():%Y%m%d-%H%M}.json")
    json.dump({"resume": resume, "lignes": lignes}, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("résultats :", chemin)


def renoter(chemin):
    """Un passage du banc renoté avec le banc et la notation d'aujourd'hui (les réponses, elles, ne changent pas)."""
    d = json.load(open(chemin, encoding="utf-8"))
    fichier = d["resume"].get("banc", "questions-v2.json")
    Q = {x["id"]: x for x in json.load(open(os.path.join(JEUX, fichier), encoding="utf-8"))}
    for l in d["lignes"]:
        l["attendu"] = Q[l["id"]]["attendu"]
        l["note"] = noter(Q[l["id"]], {**l["obtenu"], "demarche": {"type": l.get("demarche_obtenue")}})
    d["resume"]["scores_publies"] = d["resume"]["scores"]
    d["resume"]["scores"] = {k: (sum(1 for l in d["lignes"] if l["note"][k]), sum(1 for l in d["lignes"] if l["note"][k] is not None))
                             for k in d["lignes"][0]["note"]}
    return d


if __name__ == "__main__":
    main()
