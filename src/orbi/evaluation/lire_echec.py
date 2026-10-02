"""Lit la trace d'une question d'un passage du banc : ce que le modèle a mis dans la grille, ce que le code a corrigé, la décision, la réponse.
Pour diagnostiquer un échec (le modèle, la politique du code, le tri, l'étiquette du banc ?).
Usage : uv run python -m orbi.evaluation.lire_echec bancs/resultats/banc-XXXX.json D12 [D13 …]"""
import json
import os
import sys
from orbi.evaluation.traces import trace_locale  # noqa: E402

CHAMPS = ("passage", "nature", "vaut_ici", "statut", "manque", "seuil", "valeur_projet", "sens", "fait_manquant")


def lire(chemin, ident):
    d = json.load(open(chemin, encoding="utf-8"))
    l = next(x for x in d["lignes"] if x["id"] == ident)
    print("=" * 110)
    print(ident, "|", l["question"])
    print("attendu :", l["attendu"]["verdict_type"], "|", l["attendu"].get("verdict"))
    print("obtenu  :", l["obtenu"].get("verdict_type"), "| par", l["obtenu"].get("par"), "|", l["obtenu"].get("secondes"), "s | notes", {k: v for k, v in l["note"].items() if v is False})
    t = trace_locale(l["obtenu"].get("trace"))
    if not t:
        print("(pas de trace)")
        print(l["obtenu"].get("reponse"))
        return
    ev = {}
    for x in open(t, encoding="utf-8"):
        r = json.loads(x)
        ev.setdefault(r["etape"], []).append(r)
    if "tri" in ev:
        print("tri     :", json.dumps(ev["tri"][0]["resultat"], ensure_ascii=False))
    if "outils" in ev:
        f = ev["outils"][0].get("faits") or {}
        print("faits   :", (f.get("zonage") or {}).get("zone"), (f.get("parcelle") or {}).get("parcelle"), (f.get("parcelle") or {}).get("surface_m2"), "m²",
              (f.get("contraintes") or {}).get("prescriptions"), "hauteurs", (f.get("contraintes") or {}).get("hauteurs_au_plan"))
    if "verrou de zone" in ev:
        print("verrou  :", {k: ev["verrou de zone"][0].get(k) for k in ("verdicts", "article", "pourquoi")})
    for k in ("analyse", "nouvelle analyse"):
        for r in ev.get(k, []):
            print(f"--- {k} ({r.get('secondes')} s, {r.get('jetons')} jetons)")
            for g in r.get("regles") or []:
                print("   ", {c: g.get(c) for c in CHAMPS if g.get(c) not in (None, "", "aucun")})
    for r in ev.get("contrôle", []):
        print("journal :", r["journal"])
        for g in r["regles"]:
            print("   ", {c: g.get(c) for c in ("id", "article", "nature", "vaut_ici", "statut", "decisif", "seuil", "valeur_projet", "fait_manquant")})
    for r in ev.get("décision", []):
        print("décision:", {k: r.get(k) for k in ("verdict", "raison", "violations", "levees", "decisives", "inconnues", "respectees")})
    print("réponse :", l["obtenu"].get("reponse"))
    if l["obtenu"].get("a_verifier"):
        print("à vérifier :", l["obtenu"]["a_verifier"])
    if l["obtenu"].get("garde_fous"):
        print("garde-fous :", l["obtenu"]["garde_fous"])


if __name__ == "__main__":
    for i in sys.argv[2:]:
        lire(sys.argv[1], i)
