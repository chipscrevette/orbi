"""Essai : découper un article du règlement en clauses numérotées, pour que le modèle désigne une phrase par son numéro (A3) au lieu de la recopier.
Vérifie que chaque clause existe mot pour mot dans son article (cite_bien) et mesure leur longueur."""
import os
import re
import statistics
import sys

from orbi.reglement.donnees import ARTICLES, article, cite_bien, propre, references  # noqa: E402

# une phrase se termine par . ou ; et la suivante commence par une majuscule, un guillemet ou une parenthèse ; une puce coupe aussi
COUPE = re.compile(r"(?<=[.;])\s+(?=[A-ZÉÈÀÂÎÔÛÇ«\"(])|\s+(?=-\s+[A-Za-zÀ-ÿ])")


def clauses(texte, minimum=30):
    """Les clauses d'un article : les morceaux trop courts sont recollés au précédent."""
    morceaux = [m.strip() for m in COUPE.split(propre(texte)) if m and m.strip()]
    out = []
    for m in morceaux:
        if out and len(m) < minimum:
            out[-1] = out[-1] + " " + m
        else:
            out.append(m)
    return out


if __name__ == "__main__":
    n_art = n_cl = n_ko = 0
    longueurs, par_article = [], []
    for ref in [r for chap in ARTICLES for r in references(chap)]:
        t = article(ref)
        if not t:
            continue
        cl = clauses(t["texte"])
        n_art += 1
        n_cl += len(cl)
        par_article.append(len(cl))
        for c in cl:
            longueurs.append(len(c))
            if not cite_bien(ref, c):
                n_ko += 1
                if n_ko <= 5:
                    print("clause non reconnue par cite_bien dans", ref, ":", c[:120])
    print(f"{n_art} articles · {n_cl} clauses · {n_ko} non reconnues par cite_bien")
    print("clauses par article : médiane", statistics.median(par_article), "max", max(par_article))
    print("longueur d'une clause : médiane", statistics.median(longueurs), "p90", sorted(longueurs)[int(len(longueurs) * .9)], "max", max(longueurs))
