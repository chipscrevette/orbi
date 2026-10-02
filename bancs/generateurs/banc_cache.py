"""Le banc caché : 20 questions que l'agent n'a jamais vues, pour mesurer sans l'avoir réglé dessus.

Règles du jeu, tenues dans cet ordre :
  1. le code de l'agent est figé avant (passage 5 du banc de mise au point, puis plus aucune modification) ;
  2. les questions viennent de vrais fils de forum (sources ci-dessous), transposées à Biarritz sur des adresses que le
     banc de mise au point n'utilise pas, plus quelques cas de zone construits (signalés comme tels) ;
  3. les réponses attendues sont écrites ici, à partir du règlement et du Code de l'urbanisme, avant tout passage de
     l'agent : chaque citation est vérifiée mot pour mot par le code, et le fichier est scellé par une empreinte SHA-256 ;
  4. un seul passage, noté par le même code que le banc de mise au point, sans correction après coup.
Usage : uv run python bancs/generateurs/banc_cache.py → bancs/jeux/questions-cachees.json, .html et .sha256"""
import hashlib
import html
import json
import os
import sys
from datetime import datetime

from orbi.reglement.donnees import cite_bien, page_citation  # noqa: E402
from orbi.outils.geo import faits  # noqa: E402
from orbi.chemins import JEUX  # noqa: E402

B = JEUX

SOURCES = {
    "fc-abri-limites": ("Forum Construire, 9 juin 2019", "https://www.forumconstruire.com/construire/topic-378360-abri-jardin-limites-separatives.php"),
    "fc-veranda-4m2": ("Forum Construire, 14 mars 2018", "https://www.forumconstruire.com/construire/topic-350093-veranda-4m2-emprise-sol-declration.php"),
    "ccm-abri-limite": ("CommentCaMarche, forum Immobilier", "https://droit-finances.commentcamarche.com/forum/affich-6088762-abri-de-jardin-en-limite-de-propriete"),
    "fc-terrasse": ("Forum Construire, 10 juin 2008", "https://www.forumconstruire.com/construire/topic-61431.php"),
    "fc-surelevation": ("Forum Construire, 31 oct. 2017", "https://www.forumconstruire.com/construire/topic-340680-surelevation-toiture-creant-nouvelle.php"),
    "ccm-mur": ("CommentCaMarche, 8 nov. 2011", "https://droit-finances.commentcamarche.com/forum/affich-4237362-le-maire-peut-il-interdire-de-rehausser-un-mu"),
    "fc-zone-naturelle": ("Forum Construire, 29 sept. 2020", "https://www.forumconstruire.com/construire/topic-406548-extension-maison-zone-naturelle.php"),
    "fc-dependance": ("Forum Construire, 5 juin 2012", "https://www.forumconstruire.com/construire/topic-183564.php"),
    "ccm-abri-piscine": ("CommentCaMarche, 13 fév. 2012", "https://droit-finances.commentcamarche.com/forum/affich-3940667-refus-de-permis-de-construire-un-abri-piscine"),
    "fc-pente": ("Forum Construire, 21 nov. 2016", "https://www.forumconstruire.com/construire/topic-318778-hauteur-egout-terrain-pente.php"),
    "fc-r1": ("Forum Construire, 16 avril 2021", "https://www.forumconstruire.com/construire/topic-420174-hauteur-maximum-construction-7m.php"),
    "fc-sdp": ("Forum Construire, 15 juil. 2021", "https://www.forumconstruire.com/construire/topic-425088-emprise-sol-126m2-surface-plancher.php"),
    "fc-450m2": ("Forum Construire, 8 avril 2023", "https://www.forumconstruire.com/construire/topic-457823-terrain-450m2-plu-20.php"),
    "fc-carport": ("Forum Construire, 19 mai 2021", "https://www.forumconstruire.com/construire/topic-422360-carport-hauvent-limite-propriete.php"),
    "ccm-cloture-delai": ("CommentCaMarche, 29 juil. 2009", "https://droit-finances.commentcamarche.com/forum/affich-4434998-cloture-declaration-prealable"),
    "fc-pergola-impots": ("Forum Construire, 29 avril 2024", "https://www.forumconstruire.com/construire/topic-477274-declaration-impots-pergola.php"),
    "ccm-derogation": ("CommentCaMarche, juillet 2019", "https://droit-finances.commentcamarche.com/forum/affich-6838210-derogation-au-plu-pour-surelevation"),
}
LOI = {
    "R421-9": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037799137/",
    "R421-12": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000034355392",
    "R421-14": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031764577",
    "R431-2": "https://www.cauegironde.com/Ma-maison-fait-plus-de-150-m-et-je-veux-faire-une-extension-dois-je-recourir-a-un-architecte/",
    "R111-22": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031721274",
}
A = {"monnier": "5 impasse Monnier, Biarritz", "tamames": "30 avenue Tamames, Biarritz", "segure": "21 avenue de Ségure, Biarritz",
     "raulet": "6 rue Eugène Raulet, Biarritz", "barroilhet": "1 allée de Barroilhet, Biarritz",
     "plage": "20 avenue de la Plage, Biarritz", "joffre": "31 avenue du Maréchal Joffre, Biarritz",
     "dassault": "28bis boulevard Marcel Dassault, Biarritz", "foret": "11 allée de la Forêt, Biarritz",
     "arcangues": "chemin de Larre, Arcangues"}
Q = []


def r(article, citation, dit):
    assert cite_bien(article, citation), f"citation introuvable mot pour mot dans {article} : {citation}"
    return {"article": article, "page": page_citation(article, citation), "citation": citation, "dit": dit}


def q(n, src, question, adresse, projet, vue, nature, verdict, verdict_type, demarche, demarche_type, regles, lois, verifier, piege):
    f = faits(A[adresse], question)
    c = f.get("contraintes") or {}
    Q.append({"id": f"C{n:02d}", "origine": "vraie question" if src else "cas de zone",
              "source": {"nom": SOURCES[src][0], "url": SOURCES[src][1]} if src else None,
              "question": question, "adresse": (f.get("adresse") or {}).get("label"), "projet": projet, "point_de_vue": vue,
              "nature": nature,
              "faits": {"zone": (f.get("zonage") or {}).get("zone") if f.get("dans_le_perimetre") else f"hors Biarritz ({(f.get('adresse') or {}).get('commune')})",
                        "parcelle": (f.get("parcelle") or {}).get("parcelle"), "surface_m2": (f.get("parcelle") or {}).get("surface_m2"),
                        "contraintes": [x for x in (c.get("prescriptions") or []) + (c.get("servitudes") or [])
                                        if not x.startswith("Majoration")]},
              "attendu": {"verdict": verdict, "demarche": demarche, "regles": regles,
                          "loi": [{"texte": t, "url": LOI[t]} for t in lois], "a_verifier": verifier,
                          "verdict_type": verdict_type, "demarche_type": demarche_type,
                          "articles": [g["article"] for g in regles]},
              "piege": piege})


UD7 = r("UD 7", "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci",
        "sur la limite, ou à 3 m au moins")
UH7 = r("UH 7", "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci",
        "sur la limite, ou à 3 m au moins")
SPR = "servitude AC4 : site patrimonial remarquable, l'Architecte des Bâtiments de France (ABF) donne son avis"

q(1, "fc-abri-limites", "Je veux poser un abri de jardin de 8 m² à 50 cm du mur du voisin et à 1 m de la limite du fond, au 5 impasse "
  "Monnier à Biarritz : c'est possible ?", "monnier", "abri de jardin", "propriétaire", "règle",
  "non à cet endroit : en UD, une construction se pose sur la limite ou à 3 m au moins ; entre les deux, elle n'est admise "
  "que si elle s'adosse contre la façade aveugle d'un bâtiment existant", "non",
  "déclaration préalable (abri de 5 à 20 m²)", "déclaration préalable", [UD7], ["R421-9"], [],
  "appliquer une distance d'une autre commune, ou croire qu'un petit abri échappe aux règles")
q(2, "fc-veranda-4m2", "Au 5 impasse Monnier à Biarritz, ma maison atteint déjà l'emprise au sol maximale. Puis-je ajouter une "
  "petite véranda de 4,5 m² à l'entrée, sans rien déclarer puisqu'elle fait moins de 5 m² ?", "monnier", "véranda",
  "propriétaire", "règle",
  "non : l'emprise maximale (50 % en UD) est déjà atteinte et une véranda y compte ; même petite, elle demande une "
  "déclaration préalable", "non", "déclaration préalable", "déclaration préalable",
  [r("UD 9", "L'emprise au sol maximale en UD et en secteurs UDi et UDi*, et UDt est fixée à 50%", "50 % de la parcelle au plus"),
   r("DG B-5", "L’ensemble des constructions sur l’unité foncière est comptabilisé dans l’emprise au sol",
     "tous les bâtiments de la parcelle comptent")], ["R421-14"], [],
  "croire qu'on peut dépasser l'emprise de quelques m², ou qu'en dessous de 5 m² rien n'est à déclarer")
q(3, "ccm-abri-limite", "Je veux mettre mon abri de jardin en limite de propriété au 30 avenue Tamames à Biarritz : c'est le "
  "débord du toit ou la dalle qui doit être sur la limite ?", "tamames", "abri de jardin", "propriétaire", "définition",
  "c'est la construction elle-même, ses murs, qui se pose sur la limite ; un débord de toit est une saillie, admise dans la "
  "bande de 3 m, qui ne doit pas surplomber le terrain du voisin", "information", "sans objet", "sans objet",
  [r("UC 7", "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci",
     "sur la limite, ou à 3 m au moins"),
   r("UC 7", "Des saillies telles que débords de toit, contreforts, murets", "le débord de toit est une saillie")], [],
  ["que le débord ne surplombe pas le terrain voisin (droit civil)"], "prendre le bord du toit pour la limite de la construction")
q(4, "fc-terrasse", "Mon constructeur m'a conseillé de ne pas déclarer la terrasse de ma maison au 21 avenue de Ségure à "
  "Biarritz. Quels risques je prends ?", "segure", "autre", "propriétaire", "hors périmètre",
  "hors périmètre : les risques et les sanctions relèvent du contentieux", "hors périmètre", "sans objet", "sans objet",
  [], [], [], "promettre qu'il n'y a aucun risque")
q(5, "fc-surelevation", "Ma maison de 90 m² au 6 rue Eugène Raulet à Biarritz : puis-je rehausser le toit d'un mètre pour créer une "
  "chambre de 25 m² sous les combles ?", "raulet", "surélévation", "propriétaire", "règle",
  "non : en zone N, l'extension d'une maison existant en mars 1995 est limitée à 10 % de sa surface de plancher, soit 9 m² "
  "ici ; 25 m² dépassent, et sans maison de 1995 rien n'est admis", "non",
  "permis de construire (plus de 20 m² créés hors zone urbaine)", "permis de construire",
  [r("N 2", "l’extension des constructions est limitée à 100m² d’emprise au sol, avec un maximum de 10% de la surface de "
     "plancher existante", "10 % de la surface existante au plus"),
   r("N 1", "Tous les types d'occupation ou d'utilisation des sols sont interdits", "en zone N, tout est interdit sauf exceptions")],
  ["R421-14"], [], "raisonner comme en zone urbaine, où 40 m² passent en déclaration")
q(6, "ccm-mur", "Le mur de clôture sur la rue, au 5 impasse Monnier à Biarritz, fait 1,50 m. Puis-je le rehausser à 1,80 m pour "
  "me protéger des regards ?", "monnier", "clôture", "propriétaire", "règle",
  "non en principe : sur l'espace public, une clôture ne dépasse pas 1,50 m en UD ; plus haut seulement pour des raisons "
  "techniques ou esthétiques que la mairie apprécie", "non",
  "déclaration préalable (toutes les clôtures à Biarritz, délibération du 21/09/2007)", "déclaration préalable",
  [r("UD 11", "clôtures sur l'espace public : La hauteur totale des clôtures ne peut excéder 1,50 m", "1,50 m au plus sur rue")],
  ["R421-12"], [], "appliquer les 2 m des limites séparatives à un mur sur rue")
q(7, "fc-zone-naturelle", "Ma maison du 1 allée de Barroilhet à Biarritz est en zone naturelle. Puis-je l'agrandir de 30 m² ?",
  "barroilhet", "extension", "propriétaire", "règle",
  "impossible à dire sans la surface de la maison avant mars 1995 : en Nh, l'extension est limitée à 25 % de la surface "
  "de plancher existante avant le P.O.S. de 1995 ; dans un espace vert protégé, 25 m² d'emprise au plus", "impossible à dire",
  "permis de construire (plus de 20 m² hors zone urbaine)", "permis de construire",
  [r("N 2", "l'extension des ces constructions est limitée à 25 % de la surface de plancher existante avant l’approbation "
     "du P.O.S. le 27 mars 1995", "25 % de la surface de 1995 au plus")], ["R421-14"],
  ["la surface de plancher de la maison avant mars 1995", "si la maison est dans l'espace vert protégé"],
  "appliquer les 40 m² des zones urbaines")
q(8, "fc-dependance", "Au 21 avenue de Ségure à Biarritz, je veux construire un abri de jardin séparé de 30 m² ; ma maison fait "
  "200 m². Faut-il un permis de construire et un architecte ?", "segure", "abri de jardin", "propriétaire", "démarche",
  "oui sous conditions : un permis de construire (plus de 20 m²), sans architecte, car c'est une construction séparée de "
  "moins de 150 m² ; il respecte l'implantation et l'emprise de la zone UH, avec l'avis de l'ABF", "oui sous conditions",
  "permis de construire, sans architecte", "permis de construire",
  [UH7, r("UH 9", "L'emprise au sol est limitée à 50%", "50 % de la parcelle au plus")], ["R421-9", "R431-2"], [SPR],
  "exiger un architecte parce que la maison dépasse 150 m²")
q(9, "ccm-abri-piscine", "Au 20 avenue de la Plage à Biarritz, puis-je couvrir ma piscine d'un abri de plus de 1,80 m de haut ?",
  "plage", "piscine", "propriétaire", "règle",
  "non : en Ncu, seule une piscine non couverte est admise ; un abri haut est une construction que l'article Ncu 1 interdit",
  "non", "permis de construire (couverture de 1,80 m ou plus)", "permis de construire",
  [r("Ncu 2", "une piscine non couverte par unité foncière", "une piscine, non couverte"),
   r("Ncu 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité", "constructions neuves interdites en Ncu")],
  ["R421-9"], [SPR], "croire qu'un abri démontable échappe au PLU")
q(10, "fc-pente", "Mon terrain au 30 avenue Tamames à Biarritz est en pente : à partir d'où se mesure la hauteur maximale d'une "
  "construction ?", "tamames", "aucun", "propriétaire", "définition",
  "à partir du sol naturel existant de la parcelle, avant travaux, jusqu'au sommet du bâtiment (ouvrages techniques et "
  "cheminées exclus) ; en UC, R+3+combles, 12 m à l'égout et 18 m au faîtage", "information", "sans objet", "sans objet",
  [r("UC 10", "la hauteur des constructions est mesurée à partir du sol existant naturel de la parcelle",
     "depuis le sol naturel de la parcelle")], [], [], "mesurer depuis la rue ou depuis le point le plus bas")
q(11, "fc-r1", "Puis-je construire une maison à étage (R+1) au 21 avenue de Ségure à Biarritz ?", "segure", "maison neuve",
  "propriétaire", "règle",
  "oui sous conditions : la zone UH admet l'habitation et jusqu'à R+4 (15 m à l'égout, 21 m au faîtage) ; il faut "
  "respecter l'implantation, l'emprise (50 %) et l'aspect, avec l'avis de l'ABF", "oui sous conditions",
  "permis de construire", "permis de construire",
  [r("UH 10", "La hauteur d'une construction ne peut excéder 5 niveaux, soit R + 4 superposés", "R+4 au plus"),
   r("UH 9", "L'emprise au sol est limitée à 50%", "50 % de la parcelle au plus"), UH7],
  [], [SPR], "appliquer la hauteur d'une autre zone")
q(12, "fc-sdp", "Au 30 avenue Tamames à Biarritz, avec l'emprise au sol autorisée, combien de surface de plancher puis-je "
  "construire ?", "tamames", "aucun", "propriétaire", "définition",
  "le PLU ne fixe pas de surface de plancher maximale : elle découle de l'emprise (70 % de la parcelle en UC), du nombre "
  "de niveaux permis (R+3+combles) et des surfaces que le Code ne compte pas (sous 1,80 m, stationnement…)", "information",
  "sans objet", "sans objet",
  [r("UC 9", "l'emprise au sol maximale est fixée à 70 % de l'unité foncière", "70 % de la parcelle au plus"),
   r("UC 10", "La hauteur d'une construction ne peut excéder 4 niveaux soit R + 3 + combles", "R+3+combles au plus")],
  ["R111-22"], [], "inventer un coefficient de surface de plancher")
q(13, "fc-450m2", "J'ai un terrain de 200 m² au 31 avenue du Maréchal Joffre à Biarritz : quelle emprise au sol ai-je le droit "
  "de construire ?", "joffre", "aucun", "propriétaire", "règle",
  "aucune limite : en UB, l'article 9 ne fixe pas d'emprise au sol ; ce sont l'implantation, la hauteur fixée au plan et "
  "l'aspect qui bornent le projet", "information", "sans objet", "sans objet",
  [r("UB 9", "L’EMPRISE AU SOL DES CONSTRUCTIONS Sans objet", "pas d'emprise maximale en UB")], [], [SPR],
  "appliquer 25 % ou 50 % d'une autre zone")
q(14, "", "Puis-je faire construire une piscine dans mon jardin au 28bis boulevard Marcel Dassault à Biarritz ?", "dassault",
  "piscine", "propriétaire", "règle",
  "oui sous conditions : en Nh, les annexes comme une piscine sont admises ; hors de l'espace boisé classé, et non couverte "
  "dans l'espace vert protégé, avec l'avis de l'ABF", "oui sous conditions", "dépend de la surface du bassin",
  "dépend de la surface du bassin",
  [r("N 2", "et les annexes (telles que garage, piscine, abri de jardin)", "les annexes sont admises en Nh")], ["R421-9"],
  ["l'emplacement hors de l'espace boisé classé", SPR], "tout interdire parce que la zone est naturelle")
q(15, "", "Mon voisin veut construire une maison neuve au 11 allée de la Forêt à Biarritz : a-t-il le droit ?", "foret",
  "maison neuve", "voisin", "règle",
  "non : en UG, les constructions destinées à l'habitation sont interdites (sauf logements de fonction d'un équipement)",
  "non", "sans objet", "sans objet",
  [r("UG 1", "les constructions destinées à l’habitation, sauf pour l’extension et la démolition des constructions existantes "
     "sous les conditions fixées à l’article UG 2", "pas de maison neuve en UG")], [], [], "raisonner comme en zone d'habitat")
q(16, "fc-carport", "Mon voisin installe un carport collé à la limite de notre terrain, au 5 impasse Monnier à Biarritz : "
  "a-t-il le droit ?", "monnier", "autre", "voisin", "règle",
  "oui sous conditions : en UD, on peut construire sur la limite séparative, si la hauteur reste sous D ≥ h − 3, soit 3 m "
  "au droit de la limite (1 m de plus pour un pignon)", "oui sous conditions", "sans objet", "sans objet",
  [UD7], [], [], "croire qu'il faut toujours 3 m de recul")
q(17, "ccm-cloture-delai", "J'ai déposé une déclaration préalable pour une clôture de 2 m au 31 avenue du Maréchal Joffre à "
  "Biarritz : combien de temps la mairie a-t-elle pour me répondre ?", "joffre", "clôture", "propriétaire", "délai",
  "2 mois : un mois d'instruction, plus un pour l'avis de l'Architecte des Bâtiments de France (site patrimonial)",
  "information", "déclaration préalable", "déclaration préalable", [], ["R421-12"], [SPR], "donner le délai de droit commun d'un mois")
q(18, "fc-pergola-impots", "La mairie a accepté les deux pergolas de ma maison au 30 avenue Tamames à Biarritz ; les impôts me "
  "demandent de les déclarer : dans quelle catégorie ?", "tamames", "autre", "propriétaire", "hors périmètre",
  "hors périmètre : une question d'impôts", "hors périmètre", "sans objet", "sans objet", [], [], [], "répondre sur la fiscalité")
q(19, "ccm-derogation", "Je voudrais créer 35 m² habitables sur le toit de ma maison au 5 impasse Monnier à Biarritz : puis-je "
  "obtenir une dérogation au PLU ?", "monnier", "surélévation", "propriétaire", "hors périmètre",
  "hors périmètre : une dérogation se demande à la mairie, qui seule en décide", "hors périmètre", "sans objet", "sans objet",
  [], [], [], "promettre une dérogation")
q(20, "", "Puis-je poser un abri de jardin de 10 m² chemin de Larre, à Arcangues ?", "arcangues", "abri de jardin",
  "propriétaire", "hors périmètre", "hors périmètre : Arcangues n'est pas couverte", "hors périmètre", "sans objet",
  "sans objet", [], [], [], "répondre avec le règlement de Biarritz")

if __name__ == "__main__":
    chemin = os.path.join(B, "questions-cachees.json")
    texte = json.dumps(Q, ensure_ascii=False, indent=1)
    open(chemin, "w", encoding="utf-8").write(texte)
    empreinte = hashlib.sha256(texte.encode("utf-8")).hexdigest()
    open(os.path.join(B, "questions-cachees.sha256"), "w", encoding="utf-8").write(
        f"{empreinte}  questions-cachees.json  scellé le {datetime.now():%Y-%m-%d %H:%M}, avant tout passage de l'agent\n")
    e = html.escape
    cartes = "".join(
        f"<article><header><b>{x['id']}</b> <span>{e(x['origine'])}{' · ' + e(x['source']['nom']) if x['source'] else ''}</span></header>"
        f"<h2>« {e(x['question'])} »</h2><p class='faits'>zone <b>{e(str(x['faits']['zone']))}</b> · parcelle "
        f"{e(str(x['faits']['parcelle']))} · {e(', '.join(x['faits']['contraintes']) or 'sans contrainte')}</p>"
        f"<p class='attendu'><b>{e(x['attendu']['verdict_type'])}</b> — {e(x['attendu']['verdict'])}</p>"
        f"<p class='dem'>Démarche : {e(x['attendu']['demarche'])}</p>"
        + "".join(f"<p class='cit'><b>{e(g['article'])}, p. {g['page']}</b> « {e(g['citation'])} »</p>" for g in x['attendu']['regles'])
        + (f"<p class='src'><a href='{e(x['source']['url'])}' target='_blank'>la question d'origine</a></p>" if x['source'] else "")
        + "</article>" for x in Q)
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Banc caché · assistant PLU</title><link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>:root{{--fond:#F5F0E8;--carte:#fff;--encre:#1D1A17;--gris:#8A837B;--filet:#E4DCD0}}*{{box-sizing:border-box;margin:0}}
body{{background:var(--fond);color:var(--encre);font:400 15px/1.45 Geist,system-ui,sans-serif;padding:32px 40px 60px;max-width:1500px;margin:auto}}
h1{{font-size:36px;font-weight:800}}.chapo{{color:var(--gris);font-size:17px;margin:6px 0 20px;max-width:1100px}}
.sceau{{font-family:ui-monospace,Consolas,monospace;font-size:13px;background:var(--carte);border:1px solid var(--filet);border-radius:10px;padding:10px 14px;margin-bottom:20px;overflow-wrap:anywhere}}
main{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}article{{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:5px}}
header span{{color:var(--gris);font-size:13px}}h2{{font-size:16px;font-weight:600}}.faits,.dem,.src{{font-size:13px;color:var(--gris)}}
.attendu{{font-size:14px}}.cit{{font-size:13px;color:#4a443e}}a{{color:#1971c2}}
@media (max-width:900px){{main{{grid-template-columns:1fr}}body{{padding:20px 16px}}}}</style></head><body>
<h1>Le banc caché : 20 questions que l'agent n'a jamais vues</h1>
<p class="chapo">Réponses attendues écrites et scellées avant tout passage de l'agent, à partir du règlement de Biarritz et du Code
de l'urbanisme ; chaque citation est vérifiée mot pour mot par le code. Un seul passage, noté comme le banc de mise au point.</p>
<p class="sceau">SHA-256 {empreinte}</p><main>{cartes}</main></body></html>"""
    open(os.path.join(B, "questions-cachees.html"), "w", encoding="utf-8").write(page)
    print(len(Q), "questions ;", sum(1 for x in Q if x["origine"] == "vraie question"), "vraies ;",
          sum(len(x["attendu"]["regles"]) for x in Q), "citations vérifiées ; empreinte", empreinte[:16])
