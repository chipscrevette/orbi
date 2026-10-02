"""Compléte adresses-candidates-2.json pour les zones naturelles, qui n'ont souvent aucune adresse : les parcelles sont désignées par
leur référence cadastrale (« parcelle BX 0012 »), comme le ferait un propriétaire. Tout vient des API publiques, sans clé.
Usage : uv run --with shapely --with requests python outils/banc_parcelles2.py"""
import json
import os
import random
import sys

from shapely.geometry import Point, shape

from orbi.outils.geo import contraintes, parcelle, zonage  # noqa: E402
from orbi.chemins import DONNEES, JEUX  # noqa: E402

random.seed(5)
zones = json.load(open(os.path.join(DONNEES, "zones-biarritz.geojson"), encoding="utf-8"))["features"]
chemin = os.path.join(JEUX, "adresses-candidates-2.json")
cand = json.load(open(chemin, encoding="utf-8"))
# les parcelles déjà vues par l'agent : bancs de mise au point et 1er banc caché (adresses ET références cadastrales)
DEJA = {"CA 0044"}
for f in ("questions-v2.json", "questions-cachees.json"):
    for x in json.load(open(os.path.join(JEUX, f), encoding="utf-8")):
        DEJA.add((x.get("faits") or {}).get("parcelle"))
cand = [a for a in cand if a.get("parcelle") not in DEJA]  # on retire d'abord les candidats déjà vus
vues = {a.get("parcelle") for a in cand} | DEJA
VOULUES = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"Ner": 3, "N": 3, "Ncu": 2}

for lib, n in VOULUES.items():
    polys = [f for f in zones if f["properties"]["libelle"] == lib]
    random.shuffle(polys)
    trouves = 0
    for f in polys:
        if trouves >= n:
            break
        g = shape(f["geometry"])
        for essai in range(8):
            p = g.representative_point() if essai == 0 else None
            if p is None:
                x0, y0, x1, y1 = g.bounds
                p = Point(random.uniform(x0, x1), random.uniform(y0, y1))
                if not g.contains(p):
                    continue
            par = parcelle(p.x, p.y)
            if not par or par["parcelle"] in vues:
                continue
            z = zonage(p.x, p.y)
            if not z or z["zone"] != lib:
                continue
            c = contraintes(par["geometrie"])
            ref = par["parcelle"]
            vues.add(ref)
            cand.append({"adresse": f"parcelle {ref}, Biarritz", "ref": ref, "zone": lib, "parcelle": ref, "surface_m2": par["surface_m2"],
                         "prescriptions": [x for x in c.get("prescriptions", []) if not x.startswith("Majoration")],
                         "hauteurs_au_plan": c.get("hauteurs_au_plan"), "servitudes": c.get("servitudes"),
                         "site_patrimonial": c.get("site_patrimonial")})
            trouves += 1
            print(f"{lib:4s} parcelle {ref} | {par['surface_m2']} m² | SPR {c.get('site_patrimonial')}", flush=True)
            break
json.dump(cand, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(cand), "candidats")
