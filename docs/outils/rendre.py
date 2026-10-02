"""Rend un schéma Excalidraw en PNG, avec Excalidraw lui-même (exportToSvg, chargé depuis esm.sh) et Chrome sans fenêtre.
Usage : uv run python docs/outils/rendre.py docs/schemas/orbi-architecture.excalidraw  → docs/schemas/orbi-architecture.png"""
import json
import os
import subprocess
import sys
import tempfile

ICI = os.path.dirname(os.path.abspath(__file__))
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def bornes(elements, marge=30):
    xs, ys = [], []
    for e in elements:
        if e.get("isDeleted"):
            continue
        if e["type"] == "arrow":
            xs += [e["x"] + px for px, _ in e["points"]]
            ys += [e["y"] + py for _, py in e["points"]]
        else:
            xs += [e["x"], e["x"] + e["width"]]
            ys += [e["y"], e["y"] + e["height"]]
    return min(xs) - marge, min(ys) - marge, max(xs) + marge, max(ys) + marge


def rendre(chemin_excalidraw):
    doc = json.load(open(chemin_excalidraw, encoding="utf-8"))
    modele = open(os.path.join(ICI, "_modele-rendu.html"), encoding="utf-8").read()
    debut = modele.index("const data = ") + len("const data = ")
    fin = modele.index(";\ntry {")
    page = os.path.join(ICI, "rendu-" + os.path.basename(chemin_excalidraw).replace(".excalidraw", ".html"))
    open(page, "w", encoding="utf-8").write(modele[:debut] + json.dumps(doc, ensure_ascii=False) + modele[fin:])
    x0, y0, x1, y1 = bornes(doc["elements"])
    largeur, hauteur = int(x1 - x0) + 40, int(y1 - y0) + 40
    png = os.path.abspath(chemin_excalidraw.replace(".excalidraw", ".png"))
    with tempfile.TemporaryDirectory() as profil:
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", f"--user-data-dir={profil}", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={largeur},{hauteur}", "--virtual-time-budget=120000",
                        f"--screenshot={png}", "file:///" + page.replace(os.sep, "/")], check=True, timeout=300,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("PNG :", png, f"({largeur}×{hauteur})")
    return png


if __name__ == "__main__":
    for c in sys.argv[1:]:
        rendre(c)
