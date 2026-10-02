"""Les outils de l'agent : des API publiques, sans clé. Chaque réponse est gardée en cache sur le disque, pour que le banc
d'essai soit rejouable à l'identique et pour ne pas solliciter les serveurs publics inutilement."""
import hashlib
import json
import os
import time

import requests

from .donnees import DONNEES

UA = {"User-Agent": "assistant-plu/0.1 (projet portfolio, usage personnel)"}
CACHE = os.path.join(DONNEES, "cache-api")
os.makedirs(CACHE, exist_ok=True)
BIARRITZ = "64122"


def _get(url, **params):
    cle = hashlib.sha1((url + json.dumps(params, sort_keys=True)).encode()).hexdigest()
    chemin = os.path.join(CACHE, cle + ".json")
    if os.path.exists(chemin):
        return json.load(open(chemin, encoding="utf-8"))
    for essai in range(3):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=60)
            if r.ok:
                d = r.json()
                json.dump(d, open(chemin, "w", encoding="utf-8"))
                return d
        except requests.RequestException:
            pass
        time.sleep(2 * (essai + 1))
    return {}


def adresse(texte, commune_imposee=None):
    """Géocodage (API Adresse de l'IGN). Si commune_imposee (code INSEE) est donné, la recherche est limitée à cette
    commune : « 12 avenue Édouard VII » sans nom de ville partait sinon à Pau."""
    params = {"q": texte, "limit": 1}
    if commune_imposee:
        params["citycode"] = commune_imposee
    f = (_get("https://data.geopf.fr/geocodage/search", **params).get("features") or [None])[0]
    if not f:
        return None
    p = f["properties"]
    lon, lat = f["geometry"]["coordinates"]
    return {"label": p.get("label"), "lon": lon, "lat": lat, "commune": p.get("city"), "code_insee": p.get("citycode"),
            "fiabilite": round(p.get("score", 0), 2)}


def parcelle(lon, lat):
    pt = json.dumps({"type": "Point", "coordinates": [lon, lat]})
    f = (_get("https://apicarto.ign.fr/api/cadastre/parcelle", geom=pt).get("features") or [None])[0]
    if not f:
        return None
    p = f["properties"]
    return {"parcelle": f"{p['section']} {p['numero']}", "surface_m2": p.get("contenance"), "geometrie": f["geometry"]}


def zonage(lon, lat):
    pt = json.dumps({"type": "Point", "coordinates": [lon, lat]})
    fs = _get("https://apicarto.ign.fr/api/gpu/zone-urba", geom=pt).get("features") or []
    if not fs:
        return None
    p = fs[0]["properties"]
    return {"zone": p.get("libelle"), "type_zone": p.get("typezone"), "document": p.get("idurba")}


def contraintes(geometrie):
    """Prescriptions, informations et servitudes du Géoportail de l'Urbanisme qui touchent la parcelle."""
    g = json.dumps(geometrie)
    out = {"prescriptions": [], "informations": [], "servitudes": [], "hauteurs_au_plan": [], "site_patrimonial": False}
    for couche, cle in (("prescription-surf", "prescriptions"), ("prescription-lin", "prescriptions"),
                        ("prescription-pct", "prescriptions"), ("info-surf", "informations"), ("assiette-sup-s", "servitudes")):
        for f in _get(f"https://apicarto.ign.fr/api/gpu/{couche}", geom=g).get("features") or []:
            p = f["properties"]
            if p.get("libelle") == "Hauteur maximale" and p.get("txt"):
                if p["txt"] not in out["hauteurs_au_plan"]:
                    out["hauteurs_au_plan"].append(p["txt"])
                continue
            lib = " ".join(str(p.get("nomsuplitt") or p.get("libelle") or p.get("txt") or "").split())
            if p.get("suptype") == "ac4":
                out["site_patrimonial"] = True
            # les « secteurs de mixité sociale » portent le nom d'une zone (UA, UDa…) : sans intérêt pour un particulier
            if not lib or lib in out[cle] or lib.startswith("Majoration des volumes") or len(lib) <= 4:
                continue
            out[cle].append(lib)
    return out


AUTRES_COMMUNES = ("anglet", "bayonne", "bidart", "arcangues", "guéthary", "saint-jean-de-luz", "boucau", "pau")


def parcelle_par_reference(ref):
    """« CA 0044 » → la parcelle de Biarritz, par sa section et son numéro (API Carto cadastre)."""
    import re as _re
    m = _re.search(r"\b([A-Z]{1,2})\s*0*(\d{1,4})\b", (ref or "").upper())  # « CA 0044 », « parcelle CA 44 »
    if not m:
        return None
    f = (_get("https://apicarto.ign.fr/api/cadastre/parcelle", code_insee=BIARRITZ, section=m.group(1),
              numero=m.group(2).zfill(4)).get("features") or [None])[0]
    if not f:
        return None
    p = f["properties"]
    return {"parcelle": f"{p['section']} {p['numero']}", "surface_m2": p.get("contenance"), "geometrie": f["geometry"]}


def _point_dans(geometrie):
    """Un point à l'intérieur de la parcelle (moyenne des sommets, suffisant pour une parcelle compacte)."""
    anneau = geometrie["coordinates"][0][0] if geometrie["type"] == "MultiPolygon" else geometrie["coordinates"][0]
    return sum(x for x, _ in anneau) / len(anneau), sum(y for _, y in anneau) / len(anneau)


def faits(texte_adresse, question="", reference_parcelle=None):
    """Tous les faits d'une adresse, dans l'ordre où l'agent les obtient. La recherche d'adresse est limitée à Biarritz,
    sauf si la question nomme explicitement une autre commune (alors : hors périmètre)."""
    q = (question + " " + (texte_adresse or "")).lower()
    autre = next((c for c in AUTRES_COMMUNES if c in q), None) if "biarritz" not in q else None
    a = adresse(texte_adresse, None if autre else BIARRITZ) if texte_adresse else None
    if autre and a and a.get("code_insee") == BIARRITZ:
        # « route du Golf, Arcangues » est géocodé « Route d'Arcangues, Biarritz » : une rue de Biarritz porte le nom de la
        # commune voisine. La personne a nommé une autre commune : c'est elle qui compte (vu en préparant le banc caché)
        a = {**a, "label": texte_adresse, "commune": autre.title(), "code_insee": None}
    if not a and not reference_parcelle:
        return {"trouvee": False}
    if a and a["code_insee"] != BIARRITZ:
        return {"trouvee": True, "adresse": a, "dans_le_perimetre": False}
    p = parcelle_par_reference(reference_parcelle) if reference_parcelle else None
    if p:  # la référence cadastrale est plus sûre qu'une rue sans numéro : on se place dans la parcelle elle-même
        lon, lat = _point_dans(p["geometrie"])
        a = a or {"label": f"parcelle {p['parcelle']}, Biarritz", "lon": lon, "lat": lat, "commune": "Biarritz",
                  "code_insee": BIARRITZ, "fiabilite": 1}
    else:
        lon, lat = a["lon"], a["lat"]
        p = parcelle(lon, lat)
    f = {"trouvee": True, "adresse": a, "dans_le_perimetre": True}
    z = zonage(lon, lat)
    f.update({"parcelle": {k: v for k, v in (p or {}).items() if k != "geometrie"}, "zonage": z,
              "contraintes": contraintes(p["geometrie"]) if p else {}})
    return f
