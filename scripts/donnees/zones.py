"""Inventaire des zones du PLU de Biarritz (Géoportail de l'Urbanisme) et découpage du règlement par zone et par article."""
import json, os, re, requests

from orbi.chemins import DONNEES
from collections import defaultdict
UA = {"User-Agent": "assistant-plu/0.1 (portfolio)"}
# emprise de la commune (donnée par le Géoportail pour ce document)
x0, y0, x1, y1 = -1.57728, 43.4475551, -1.5343914, 43.4945158
poly = {"type": "Polygon", "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]]}
r = requests.get("https://apicarto.ign.fr/api/gpu/zone-urba", params={"geom": json.dumps(poly)}, headers=UA, timeout=120)
feats = [f for f in r.json()["features"] if f["properties"].get("partition") == "DU_64122"]
json.dump({"type": "FeatureCollection", "features": feats}, open(os.path.join(DONNEES, "zones-biarritz.geojson"), "w", encoding="utf-8"))
compte = defaultdict(int)
for f in feats:
    compte[(f["properties"]["libelle"], f["properties"]["typezone"])] += 1
print(len(feats), "polygones ;", len(compte), "libellés :")
print(sorted(compte.items()))
# le règlement : où commence chaque chapitre de zone, et chaque article
pages = json.load(open(os.path.join(DONNEES, "pages.json"), encoding="utf-8"))
chap = [(p, m.group(1)) for p, t in pages for m in re.finditer(r"CHAPITRE (U[A-Z]|1?AU[A-Z]*|A|N)\b\s+DISPOSITIONS", t)]
print("chapitres :", chap)
