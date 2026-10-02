"""Candidats pour le 2e banc caché : des adresses de Biarritz que ni le banc de mise au point ni le 1er banc caché n'ont utilisées,
réparties dans toutes les zones, avec les faits que l'agent devra retrouver. Tout vient des API publiques, sans clé.
Usage : uv run --with shapely --with requests python outils/banc_adresses2.py ['{"UD": 6}' [graine]]
Avec un argument, les nouveaux candidats s'ajoutent à ceux du fichier (même parcelle jamais reprise) ; sans argument, tirage complet."""
import json
import os
import random
import sys
import time

import requests
from shapely.geometry import Point, shape

from orbi.outils.geo import faits  # noqa: E402  (API publiques, avec cache disque)
from orbi.chemins import DONNEES, JEUX  # noqa: E402

UA = {"User-Agent": "assistant-plu/0.1 (portfolio)"}
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else 11
random.seed(SEED)
zones = json.load(open(os.path.join(DONNEES, "zones-biarritz.geojson"), encoding="utf-8"))["features"]
VOULUES = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"UA": 3, "UAs": 2, "UB": 3, "UBa": 3, "UC": 3, "UD": 3, "UDa": 4, "UDb": 2,
                                                            "UDc": 1, "UG": 3, "UH": 3, "UY": 2, "UP": 1, "N": 4, "Ncu": 3, "Ner": 3, "Nh": 3, "IIAUy": 1}
CHEMIN = os.path.join(JEUX, "adresses-candidates-2.json")
# les adresses déjà vues par l'agent ou par moi (bancs de mise au point et 1er banc caché) : à ne pas reprendre
DEJA, PARCELLES = set(), {"CA 0044"}
for f in ("questions-v2.json", "questions-cachees.json"):
    for x in json.load(open(os.path.join(JEUX, f), encoding="utf-8")):
        DEJA.add((x.get("adresse") or "").split(" 64")[0].lower())
        PARCELLES.add((x.get("faits") or {}).get("parcelle"))


def get(url, **params):
    for _ in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=90)
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2)
    return {}


sortie = json.load(open(CHEMIN, encoding="utf-8")) if len(sys.argv) > 1 else []  # ajout aux candidats existants
vues = {a["adresse"].split(" 64")[0].lower() for a in sortie}
PARCELLES |= {a.get("parcelle") for a in sortie}
for lib, n in VOULUES.items():
    polys = [f for f in zones if f["properties"]["libelle"] == lib]
    random.shuffle(polys)
    trouves = 0
    for f in polys:
        if trouves >= n:
            break
        g = shape(f["geometry"])
        for essai in range(5):
            p = g.representative_point() if essai == 0 else None
            if p is None:
                x0, y0, x1, y1 = g.bounds
                p = Point(random.uniform(x0, x1), random.uniform(y0, y1))
                if not g.contains(p):
                    continue
            rev = (get("https://data.geopf.fr/geocodage/reverse", lon=p.x, lat=p.y, limit=1, index="address").get("features") or [None])[0]
            if not rev or rev["properties"].get("citycode") != "64122":
                continue
            adresse = rev["properties"]["label"]
            cle = adresse.split(" 64")[0].lower()
            if cle in DEJA or cle in vues or not rev["properties"].get("housenumber"):
                continue
            f_ = faits(adresse, adresse)
            z = (f_.get("zonage") or {}).get("zone")
            if not f_.get("trouvee") or z != lib:  # la zone du point d'adresse peut différer de celle du polygone tiré
                continue
            if (f_.get("parcelle") or {}).get("parcelle") in PARCELLES:  # une parcelle déjà vue, ou déjà candidate
                continue
            c = f_.get("contraintes") or {}
            sortie.append({"adresse": adresse, "zone": z, "parcelle": (f_.get("parcelle") or {}).get("parcelle"),
                           "surface_m2": (f_.get("parcelle") or {}).get("surface_m2"),
                           "prescriptions": [x for x in c.get("prescriptions", []) if not x.startswith("Majoration")],
                           "hauteurs_au_plan": c.get("hauteurs_au_plan"), "servitudes": c.get("servitudes"),
                           "site_patrimonial": c.get("site_patrimonial")})
            vues.add(cle)
            PARCELLES.add((f_.get("parcelle") or {}).get("parcelle"))
            trouves += 1
            print(f"{lib:6s} {adresse} | {(f_.get('parcelle') or {}).get('parcelle')} {(f_.get('parcelle') or {}).get('surface_m2')} m²", flush=True)
            break
json.dump(sortie, open(CHEMIN, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(sortie), "adresses")
