"""Images dérivées du rendu 3D d'Orbi (src/assets/orbi.png, jamais modifié).

    python scripts/images.py      (depuis app/, avec Pillow)

Produit :
  src/assets/orbi-detoure.png   la brique détourée au plus près (+ 3 % de marge), pour l'interface
  build/icon.png                carré transparent de 512 px, brique centrée (fenêtre, barre des tâches, installateur)
  build/icon.ico                la même en 16, 24, 32, 48, 64, 128 et 256 px pour Windows
  public/favicon.png            64 px, pour l'onglet du navigateur
"""

from pathlib import Path

from PIL import Image

APP = Path(__file__).resolve().parent.parent
ORIGINAL = APP / "src" / "assets" / "orbi.png"
DETOURE = APP / "src" / "assets" / "orbi-detoure.png"
ICONE_PNG = APP / "build" / "icon.png"
ICONE_ICO = APP / "build" / "icon.ico"
FAVICON = APP / "public" / "favicon.png"

SEUIL_ALPHA = 8  # en dessous, le « bruit » transparent du rendu est effacé
MARGE = 0.03  # marge autour du contenu, en part de son plus grand côté
LARGEUR_DETOURE = 560  # l'interface l'affiche au plus vers 240 px de large : de quoi tenir en double densité
COTE_ICONE = 512
REMPLISSAGE_ICONE = 0.94  # part du carré occupée par la brique
TAILLES_ICO = [16, 24, 32, 48, 64, 128, 256]


def nettoyer(image: Image.Image) -> Image.Image:
    """Efface le voile presque transparent qui entoure le rendu."""
    rouge, vert, bleu, alpha = image.split()
    alpha = alpha.point(lambda v: 0 if v <= SEUIL_ALPHA else v)
    return Image.merge("RGBA", (rouge, vert, bleu, alpha))


def detourer(image: Image.Image) -> Image.Image:
    boite = image.getchannel("A").getbbox()
    if boite is None:
        raise SystemExit("le rendu est entièrement transparent")
    gauche, haut, droite, bas = boite
    marge = round(MARGE * max(droite - gauche, bas - haut))
    toile = Image.new("RGBA", (droite - gauche + 2 * marge, bas - haut + 2 * marge), (0, 0, 0, 0))
    toile.paste(image.crop(boite), (marge, marge))
    return toile


def reduire(image: Image.Image, largeur: int) -> Image.Image:
    if image.width <= largeur:
        return image
    hauteur = round(image.height * largeur / image.width)
    return image.resize((largeur, hauteur), Image.Resampling.LANCZOS)


def carre(image: Image.Image, cote: int) -> Image.Image:
    """La brique centrée dans un carré transparent."""
    contenu = image.crop(image.getchannel("A").getbbox())
    echelle = REMPLISSAGE_ICONE * cote / max(contenu.size)
    taille = (max(1, round(contenu.width * echelle)), max(1, round(contenu.height * echelle)))
    contenu = contenu.resize(taille, Image.Resampling.LANCZOS)
    toile = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    toile.paste(contenu, ((cote - taille[0]) // 2, (cote - taille[1]) // 2), contenu)
    return toile


def main() -> None:
    original = Image.open(ORIGINAL).convert("RGBA")
    propre = nettoyer(original)

    detoure = reduire(detourer(propre), LARGEUR_DETOURE)
    detoure.save(DETOURE, optimize=True)

    ICONE_PNG.parent.mkdir(parents=True, exist_ok=True)
    icone = carre(propre, COTE_ICONE)
    icone.save(ICONE_PNG, optimize=True)
    icone.save(ICONE_ICO, sizes=[(t, t) for t in TAILLES_ICO])
    carre(propre, 64).save(FAVICON, optimize=True)

    for chemin in (DETOURE, ICONE_PNG, ICONE_ICO, FAVICON):
        with Image.open(chemin) as im:
            print(f"{chemin.relative_to(APP)} : {im.size[0]}×{im.size[1]}, {chemin.stat().st_size // 1024} Ko")


if __name__ == "__main__":
    main()
