"""Petit générateur de fichiers Excalidraw : cartes (rectangle + titre + détail), textes, flèches liées."""
import itertools, json, random

random.seed(7)
_ids = itertools.count(1)
BLEU, VERT, ORANGE, ROUGE, VIOLET, GRIS, JAUNE, BLANC = (
    ("#d0ebff", "#1971c2"), ("#d3f9d8", "#2f9e44"), ("#ffe8cc", "#e8590c"), ("#ffe3e3", "#e03131"),
    ("#e5dbff", "#6741d9"), ("#f1f3f5", "#868e96"), ("#fff3bf", "#f08c00"), ("#ffffff", "#1e1e1e"))
ENCRE, GRISTEXTE = "#1e1e1e", "#495057"


def nid(p):
    return f"{p}{next(_ids)}"


def base(t, x, y, w, h, **k):
    e = {"id": k.pop("id", nid(t[:3])), "type": t, "x": x, "y": y, "width": w, "height": h, "angle": 0,
         "strokeColor": k.pop("stroke", ENCRE), "backgroundColor": k.pop("bg", "transparent"),
         "fillStyle": "solid", "strokeWidth": k.pop("sw", 2), "strokeStyle": k.pop("ss", "solid"),
         "roughness": 1, "opacity": 100, "groupIds": k.pop("groups", []), "frameId": None,
         "roundness": k.pop("roundness", None), "seed": random.randint(1, 2 ** 30), "version": 1,
         "versionNonce": random.randint(1, 2 ** 30), "isDeleted": False, "boundElements": [], "updated": 1,
         "link": None, "locked": False}
    e.update(k)
    return e


class Schema:
    def __init__(self):
        self.els = []

    def texte(self, x, y, w, s, taille=20, couleur=ENCRE, align="left", groupes=None):
        h = (s.count("\n") + 1) * taille * 1.25
        e = base("text", x, y, w, h, stroke=couleur, groups=groupes or [], text=s, originalText=s, fontSize=taille,
                 fontFamily=5, textAlign=align, verticalAlign="top", containerId=None, lineHeight=1.25,
                 autoResize=False)
        self.els.append(e)
        return e

    def cadre(self, x, y, w, h, couleurs=GRIS, pointille=False):
        e = base("rectangle", x, y, w, h, bg=couleurs[0], stroke=couleurs[1], ss="dashed" if pointille else "solid",
                 roundness={"type": 3})
        self.els.append(e)
        return e

    def rond(self, x, y, w, h, couleurs=GRIS, texte=None, taille=28):
        """Une ellipse, avec un texte centré (une étape, une planète)."""
        g = nid("g")
        e = base("ellipse", x, y, w, h, bg=couleurs[0], stroke=couleurs[1], groups=[g])
        self.els.append(e)
        if texte:
            ht = (texte.count("\n") + 1) * taille * 1.25
            self.texte(x, y + (h - ht) / 2, w, texte, taille, ENCRE, "center", [g])
        return e

    def carte(self, x, y, w, h, titre, detail=None, couleurs=BLANC, ttitre=22, tdetail=16, pointille=False):
        g = nid("g")
        r = base("rectangle", x, y, w, h, bg=couleurs[0], stroke=couleurs[1], groups=[g], roundness={"type": 3},
                 ss="dashed" if pointille else "solid")
        self.els.append(r)
        ht = (titre.count("\n") + 1) * ttitre * 1.25
        hd = (detail.count("\n") + 1) * tdetail * 1.25 if detail else 0
        ecart = 10 if detail else 0
        y0 = y + (h - ht - ecart - hd) / 2
        self.texte(x + 12, y0, w - 24, titre, ttitre, ENCRE, "center", [g])
        if detail:
            self.texte(x + 12, y0 + ht + ecart, w - 24, detail, tdetail, GRISTEXTE, "center", [g])
        return r

    def fleche(self, points, de=None, vers=None, pointille=False, couleur=ENCRE):
        x0, y0 = points[0]
        rel = [[px - x0, py - y0] for px, py in points]
        xs, ys = [p[0] for p in rel], [p[1] for p in rel]
        a = base("arrow", x0, y0, max(xs) - min(xs), max(ys) - min(ys), stroke=couleur,
                 ss="dashed" if pointille else "solid", roundness=None if len(points) > 2 else {"type": 2},
                 points=rel, lastCommittedPoint=None,
                 startBinding={"elementId": de["id"], "focus": 0, "gap": 4} if de else None,
                 endBinding={"elementId": vers["id"], "focus": 0, "gap": 4} if vers else None,
                 startArrowhead=None, endArrowhead="arrow", elbowed=False)
        for el in (de, vers):
            if el:
                el["boundElements"].append({"type": "arrow", "id": a["id"]})
        self.els.append(a)
        return a

    def bornes(self, marge=40):
        xs, ys = [], []
        for e in self.els:
            if e["type"] == "arrow":
                xs += [e["x"] + px for px, _ in e["points"]]
                ys += [e["y"] + py for _, py in e["points"]]
            else:
                xs += [e["x"], e["x"] + e["width"]]
                ys += [e["y"], e["y"] + e["height"]]
        return min(xs) - marge, min(ys) - marge, max(xs) + marge, max(ys) + marge

    def ecrire(self, chemin):
        doc = {"type": "excalidraw", "version": 2, "source": "https://excalidraw.com", "elements": self.els,
               "appState": {"gridSize": None, "viewBackgroundColor": "#ffffff"}, "files": {}}
        with open(chemin, "w", encoding="utf-8") as f:
            json.dump(doc, f, ensure_ascii=False, indent=1)
        return doc
