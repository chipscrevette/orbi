"""Candidats pour le banc d'essai : de vraies adresses de Biarritz dans plusieurs zones du PLU, avec les faits que
l'agent devra retrouver (parcelle, zone, prescriptions, servitudes). Tout vient des API publiques, sans clé."""
import json
import os

from orbi.chemins import JEUX, random, time
import requests
from shapely.geometry import shape, Point

UA = {"User-Agent": "assistant-plu/0.1 (portfolio)"}
random.seed(3)
zones = json.load(open("zones-biarritz.geojson", encoding="utf-8"))["features"]
VOULUES = ["UA", "UB", "UBa", "UC", "UD", "UDa", "UG", "UH", "N", "Ncu", "Nh"]


def get(url, **params):
    for essai in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=90)
            if r.ok:
                return r.json()
        except requests.RequestException:
            pass
        time.sleep(2)
    return {}


def faits(lon, lat):
    pt = json.dumps({"type": "Point", "coordinates": [lon, lat]})
    par = get("https://apicarto.ign.fr/api/cadastre/parcelle", geom=pt).get("features", [])
    if not par:
        return None
    geom = json.dumps(par[0]["geometry"])
    pp = par[0]["properties"]
    z = [f["properties"]["libelle"] for f in get("https://apicarto.ign.fr/api/gpu/zone-urba", geom=pt).get("features", [])]
    out = {"parcelle": f"{pp['section']} {pp['numero']}", "surface_m2": pp.get("contenance"), "zone": z,
           "prescriptions": [], "informations": [], "servitudes": []}
    for couche, cle in (("prescription-surf", "prescriptions"), ("prescription-lin", "prescriptions"),
                        ("prescription-pct", "prescriptions"), ("info-surf", "informations"),
                        ("assiette-sup-s", "servitudes")):
        for f in get(f"https://apicarto.ign.fr/api/gpu/{couche}", geom=geom).get("features", []):
            p = f["properties"]
            lib = p.get("nomsuplitt") or p.get("libelle") or p.get("txt")
            if lib and lib not in out[cle]:
                out[cle].append(" ".join(str(lib).split()))
    return out


candidats = []
for lib in VOULUES:
    polys = [f for f in zones if f["properties"]["libelle"] == lib]
    random.shuffle(polys)
    trouves = 0
    for f in polys:
        g = shape(f["geometry"])
        for _ in range(6):
            p = g.representative_point() if _ == 0 else None
            if p is None:
                x0, y0, x1, y1 = g.bounds
                p = Point(random.uniform(x0, x1), random.uniform(y0, y1))
                if not g.contains(p):
                    continue
            rev = get("https://data.geopf.fr/geocodage/reverse", lon=p.x, lat=p.y, limit=1, index="address")
            if not rev.get("features"):
                continue
            a = rev["features"][0]
            lon, lat = a["geometry"]["coordinates"]
            fa = faits(lon, lat)
            if not fa or fa["zone"] != [lib] or a["properties"].get("citycode") != "64122":
                continue
            candidats.append({"adresse": a["properties"]["label"], "lon": round(lon, 6), "lat": round(lat, 6), **fa})
            print(f"{lib:4} {a['properties']['label']:45} {fa['parcelle']:9} {fa['surface_m2']} m² | "
                  f"{fa['prescriptions'][:3]} | {fa['servitudes'][:2]}", flush=True)
            trouves += 1
            break
        if trouves >= 2:
            break
json.dump(candidats, open(os.path.join(JEUX, "adresses-candidates.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(len(candidats), "adresses retenues")
