"""Les vraies zones du PLU autour de la parcelle du film (15 avenue de la Marne, AB 0073, zone UAs), en chemins SVG."""
import json
import math
import re

LON, LAT = -1.555387, 43.484388
L, H = 640, 400          # taille de la carte dans le film
RAYON_M = 420            # demi-largeur couverte, en mètres


def famille(code):
    c = (code or "").upper()
    if re.match(r"^(I{1,2}|1|2)?AU", c):
        return "#E36AA5"
    for pref, coul in (("UA", "#E5484D"), ("UB", "#F2883A"), ("UC", "#F2883A"), ("UD", "#EDBE2C")):
        if c.startswith(pref):
            return coul
    if re.match(r"^U[GHPY]", c):
        return "#8B5CF0"
    return "#3BA55C" if c.startswith("N") else "#8A96AD"


kx = 111320 * math.cos(math.radians(LAT))
ky = 110540
echelle = (L / 2) / RAYON_M


def xy(lon, lat):
    return round(L / 2 + (lon - LON) * kx * echelle, 1), round(H / 2 - (lat - LAT) * ky * echelle, 1)


g = json.load(open("../../app/public/donnees/zones.geojson", encoding="utf-8"))
chemins = []
for f in g["features"]:
    geo = f["geometry"]
    polys = geo["coordinates"] if geo["type"] == "MultiPolygon" else [geo["coordinates"]]
    d = []
    for poly in polys:
        for anneau in poly:
            pts = [xy(*p) for p in anneau]
            if all(x < -50 or x > L + 50 for x, _ in pts) or all(y < -50 or y > H + 50 for _, y in pts):
                continue
            d.append("M" + "L".join(f"{x},{y}" for x, y in pts) + "Z")
    if d:
        code = f["properties"]["libelle"]
        chemins.append({"d": "".join(d), "couleur": famille(code), "code": code})
json.dump({"chemins": chemins, "point": xy(LON, LAT), "l": L, "h": H}, open("carte.json", "w", encoding="utf-8"))
print(len(chemins), "zones ;", sorted({c["code"] for c in chemins}), "point", xy(LON, LAT))
