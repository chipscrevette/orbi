"""Le 2e banc caché : 40 questions que l'agent n'a jamais vues, en quatre groupes de dix (la structure proposée par Kévin) :
  A. clairement permis      B. clairement interdit      C. information manquante      D. zones strictes et exceptions

Règles du jeu, tenues dans cet ordre :
  1. les adresses viennent de outils/banc_adresses2.py : aucune n'a servi au banc de mise au point ni au 1er banc caché ;
  2. les réponses attendues sont écrites ici, à partir du règlement et du Code de l'urbanisme, AVANT tout passage de l'agent ;
     les chiffres (emprise maximale…) sont calculés sur la vraie surface de la parcelle, chaque citation est vérifiée mot pour
     mot par le code ;
  3. le fichier est scellé par une empreinte SHA-256, avec celle du code de l'agent, avant le passage ;
  4. un seul passage, noté par le même code que les autres bancs, sans correction après coup.
Usage : uv run python bancs/generateurs/banc_cache2.py → bancs/jeux/questions-cachees-2.json, .html et .sha256"""
import hashlib
import html
import json
import os
import sys
from datetime import datetime

from orbi.reglement.donnees import cite_bien, page_citation  # noqa: E402
from orbi.chemins import JEUX  # noqa: E402

B = JEUX
CAND = json.load(open(os.path.join(B, "adresses-candidates-2.json"), encoding="utf-8"))
LOI = {
    "R421-2": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000050497056",
    "R421-9": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037799137/",
    "R421-12": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000034355392",
    "R421-14": "https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000031764577",
    "R431-2": "https://www.cauegironde.com/Ma-maison-fait-plus-de-150-m-et-je-veux-faire-une-extension-dois-je-recourir-a-un-architecte/",
}
SPR_TXT = "servitude AC4 : site patrimonial remarquable, l'Architecte des Bâtiments de France (ABF) donne son avis"
Q, UTILISEES = [], set()
DEJA = {"CA 0044"}
for _f in ("questions-v2.json", "questions-cachees.json"):
    for _x in json.load(open(os.path.join(B, _f), encoding="utf-8")):
        DEJA.add((_x.get("faits") or {}).get("parcelle"))


def adr(zone, parcelle):
    """La parcelle nommée, qui doit être dans la zone attendue. Les surfaces dont dépend la réponse attendue sont vérifiées plus bas."""
    a = next(a for a in CAND if a.get("parcelle") == parcelle)
    assert a["zone"] == zone, f"{parcelle} est en {a['zone']}, pas en {zone}"
    assert parcelle not in DEJA, f"{parcelle} a déjà servi à un banc"
    return a


def court(a):
    """« au 14 avenue X à Biarritz » ou, pour une parcelle désignée par sa référence, « sur la parcelle BX 0012 à Biarritz »."""
    if a.get("ref"):
        return f"sur la parcelle {a['ref']} à Biarritz"
    return "au " + a["adresse"].replace(" 64200 Biarritz", "") + " à Biarritz"


def r(article, citation, dit):
    assert cite_bien(article, citation), f"citation introuvable mot pour mot dans {article} : {citation}"
    return {"article": article, "page": page_citation(article, citation), "citation": citation, "dit": dit}


def q(n, groupe, texte, a, projet, vue, nature, verdict_type, verdict, demarche_type, demarche, regles, lois, verifier, piege):
    assert a["parcelle"] not in UTILISEES, f"la parcelle {a['parcelle']} sert deux fois"
    UTILISEES.add(a["parcelle"])
    spr = bool(a.get("site_patrimonial"))
    Q.append({"id": f"D{n:02d}", "groupe": groupe, "origine": "cas de zone (inspiré de questions de forum)", "source": None,
              "question": texte.format(adr=court(a), ADR=court(a)[0].upper() + court(a)[1:], S=int(a["surface_m2"])), "adresse": a["adresse"], "projet": projet, "point_de_vue": vue,
              "nature": nature,
              "faits": {"zone": a["zone"], "parcelle": a["parcelle"], "surface_m2": a["surface_m2"],
                        "contraintes": list(a.get("prescriptions", [])) + (["Site patrimonial remarquable de Biarritz"] if spr else [])},
              "attendu": {"verdict": verdict, "demarche": demarche, "regles": regles,
                          "loi": [{"texte": t, "url": LOI[t]} for t in lois],
                          "a_verifier": verifier + ([SPR_TXT] if spr else []), "verdict_type": verdict_type,
                          "demarche_type": demarche_type, "articles": [g["article"] for g in regles]},
              "piege": piege})


def permis(a, plein="oui"):
    """Un projet entièrement décrit : « oui » hors site patrimonial, « oui sous conditions » dans un site patrimonial (avis de l'ABF)."""
    return "oui sous conditions" if a.get("site_patrimonial") else plein


UD7 = lambda z: r(f"{z} 7", "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci",  # noqa: E731
                  "sur la limite, ou à 3 m au moins")
DP5_20 = "déclaration préalable (de 5 à 20 m² ; toujours en site patrimonial)"
PISCINE_EMPRISE = r("DG B-5", "tennis ne sont pas comprises dans l’emprise au sol", "une piscine non couverte ne compte pas dans l'emprise")

# ============================================================================================ A · 10 projets clairement permis
a = adr("UD", "AB 0521")
q(1, "A", "Terrain de {S} m² {adr}. Ma maison fait 90 m² d'emprise. Je voudrais poser un abri de jardin de 8 m² à 4 m de la limite "
  "du voisin : est-ce possible ?", a, "abri de jardin", "propriétaire", "règle", permis(a), "oui : l'emprise (90 + 8 m²) est très sous les 50 % de "
  f"{int(a['surface_m2'])} m² et la distance de 4 m dépasse les 3 m", "déclaration préalable", DP5_20,
  [UD7("UD"), r("UD 9", "L'emprise au sol maximale en UD et en secteurs UDi et UDi*, et UDt est fixée à 50%", "50 % de la parcelle au plus")],
  ["R421-9"], [], "croire qu'un abri de moins de 9 m² est dispensé de formalité, ou qu'il faut 4 m")
a = adr("UC", "AE 0450")
q(2, "A", "{ADR}, ma maison fait 80 m² d'emprise sur un terrain de {S} m². Je veux ajouter une véranda de 15 m² : ça passe ?", a, "véranda",
  "propriétaire", "règle", "oui sous conditions", "oui sous conditions : l'emprise (95 m²) reste sous les 70 % de la parcelle ; la distance à la limite "
  "et l'aspect restent à vérifier", "déclaration préalable", "déclaration préalable (15 m² créés, sous 40 m² en zone urbaine)",
  [r("UC 9", "l'emprise au sol maximale est fixée à 70 % de l'unité foncière", "70 % de la parcelle au plus"), UD7("UC")], ["R421-14"],
  ["la distance de la véranda à la limite séparative", "l'aspect de la véranda"], "appliquer 50 % ou 25 % d'une autre zone")
a = adr("UB", "AX 0460")
q(3, "A", "Je veux refaire ma clôture sur la rue avec un mur bahut de 80 cm surmonté d'une grille, 1,40 m au total, {adr}. C'est permis ?", a,
  "clôture", "propriétaire", "règle", "oui sous conditions", "oui sous conditions : en UB, 2 m au plus sur l'espace public et un mur bahut de 1 m au "
  "plus ; l'harmonie avec le voisinage reste à vérifier", "déclaration préalable", "déclaration préalable (toutes les clôtures à Biarritz, "
  "délibération du 21/09/2007)",
  [r("UB 11", "La hauteur totale des clôtures ne peut excéder 2 mètres", "2 m au plus sur l'espace public")], ["R421-12"],
  ["l'harmonie de la clôture avec les clôtures voisines"], "appliquer les 1,50 m d'UD ou d'UC à une parcelle en UB")
a = adr("UH", "BO 0015")
q(4, "A", "Je compte construire une maison en R+2, 10 m à l'égout du toit, {adr}. Les hauteurs sont-elles respectées ?", a, "maison neuve",
  "propriétaire", "règle", "oui sous conditions", "oui sous conditions : la zone UH admet jusqu'à R+4 (15 m à l'égout) ; implantation, emprise "
  "(50 %) et aspect restent à respecter", "permis de construire", "permis de construire",
  [r("UH 10", "La hauteur d'une construction ne peut excéder 5 niveaux, soit R + 4 superposés", "R+4 au plus, 15 m à l'égout")], [],
  ["l'emprise (50 % au plus) et la distance aux limites"], "appliquer la hauteur d'une autre zone")
a = adr("UDa", "AC 0235")
q(5, "A", "Je veux creuser une piscine non couverte de 32 m² dans mon jardin, {adr}. Ai-je le droit ?", a, "piscine", "propriétaire", "règle",
  permis(a), "oui : une piscine non couverte est exclue de la règle de distance et ne compte pas dans l'emprise", "déclaration préalable",
  "déclaration préalable (bassin jusqu'à 100 m²)",
  [r("UD 7", "Les piscines, spas et jacuzzis sont exclus de cette règle", "les piscines sont exclues de la règle de distance"), PISCINE_EMPRISE],
  ["R421-9"], [], "appliquer 3 m ou l'emprise à une piscine")
a = adr("UDc", "AK 0643")
q(6, "A", "Ma maison fait 125 m². Je veux l'agrandir de 30 m² {adr}, sur un terrain de {S} m². Quelle autorisation, et est-ce permis ?", a,
  "extension", "propriétaire", "règle", "oui sous conditions", "oui sous conditions : l'emprise reste sous les 60 % de la parcelle en UDc ; "
  "la maison dépasse 150 m² après travaux : permis et architecte", "permis de construire + architecte",
  "permis de construire avec architecte (155 m² après travaux, au-delà de 150 m²)",
  [r("UD 9", "En secteur UDc : L’emprise au sol maximale est fixée à 60% de l’unité foncière", "60 % de la parcelle au plus en UDc")],
  ["R421-14", "R431-2"], ["la distance de l'extension aux limites"], "oublier le permis et l'architecte (155 m² au total)")
a = adr("UD", "AB 0221")
q(7, "A", "Je veux monter un mur plein de 1,40 m sur la rue {adr}. C'est dans les clous ?", a, "clôture", "propriétaire", "règle",
  "oui sous conditions", "oui sous conditions : en UD, 1,50 m au plus sur l'espace public ; l'aspect reste à vérifier", "déclaration préalable",
  "déclaration préalable (toutes les clôtures à Biarritz)",
  [r("UD 11", "La hauteur totale des clôtures ne peut excéder 1,50 m", "1,50 m au plus sur la rue")], ["R421-12"],
  ["l'aspect du mur par rapport aux clôtures voisines"], "appliquer les 2 m des limites séparatives à une clôture sur rue")
a = adr("UD", "AL 0160")
q(8, "A", "Terrain de {S} m², maison de 100 m² d'emprise, {adr}. J'aimerais poser un abri de 15 m² (2,50 m de haut) collé à la limite "
  "de mon voisin. Possible ?", a, "abri de jardin", "propriétaire", "règle", permis(a),
  "oui : on peut construire sur la limite séparative, et la hauteur de 2,50 m reste sous D ≥ h − 3", "déclaration préalable", DP5_20,
  [UD7("UD"), r("UD 9", "L'emprise au sol maximale en UD et en secteurs UDi et UDi*, et UDt est fixée à 50%", "50 % de la parcelle au plus")],
  ["R421-9"], [], "croire qu'il faut toujours 3 m de recul")
a = adr("UC", "AL 0125")
q(9, "A", "{ADR}, je veux construire une maison de 150 m² d'emprise avec un étage et des combles, 9 m à l'égout du toit. C'est conforme au "
  "PLU ?", a, "maison neuve", "propriétaire", "règle", "oui sous conditions",
  f"oui sous conditions : 150 m² sont sous les 70 % de {int(a['surface_m2'])} m² et 9 m sous les 12 m de la zone UC ; implantation et aspect restent à "
  "respecter", "permis de construire", "permis de construire",
  [r("UC 9", "l'emprise au sol maximale est fixée à 70 % de l'unité foncière", "70 % de la parcelle au plus"),
   r("UC 10", "La hauteur d'une construction ne peut excéder 4 niveaux soit R + 3 + combles", "R+3+combles au plus, 12 m à l'égout")], [],
  ["la distance aux limites séparatives"], "appliquer la hauteur d'UD (9 m) ou d'UDa (6 m)")
a = adr("UBa", "AK 0303")
q(10, "A", "Véranda de 12 m² sur ma maison {adr}, terrain de {S} m² : c'est autorisé ?", a, "véranda", "propriétaire", "règle",
  "oui sous conditions", "oui sous conditions : en UB, aucune emprise maximale n'est fixée ; l'implantation et l'aspect restent à vérifier",
  "déclaration préalable", "déclaration préalable (12 m² créés, sous 40 m² en zone urbaine)",
  [r("UB 9", "L’EMPRISE AU SOL DES CONSTRUCTIONS Sans objet", "pas d'emprise maximale en UB")], ["R421-14"],
  ["la distance de la véranda aux limites", "l'aspect de la véranda"], "appliquer une emprise maximale qui n'existe pas en UB")

# ============================================================================================ B · 10 projets clairement interdits
a = adr("UD", "BM 0224")
q(11, "B", "Je veux poser un abri de jardin de 10 m² à 1,5 m de la limite du voisin, {adr}. J'ai le droit ?", a, "abri de jardin", "propriétaire",
  "règle", "non", "non : en UD, une construction se pose sur la limite ou à 3 m au moins ; 1,5 m n'est ni l'un ni l'autre", "déclaration préalable",
  DP5_20, [UD7("UD")], ["R421-9"], [], "croire qu'un petit abri peut s'approcher à 1,5 m")
a = adr("UDa", "AI 0156")
q(12, "B", "{ADR}, terrain de {S} m², ma maison fait 380 m² d'emprise. Je veux y ajouter 60 m² d'emprise : permis ?", a, "extension",
  "propriétaire", "règle", "non", f"non : en UDa, 25 % de {int(a['surface_m2'])} m² font {int(a['surface_m2'] * 0.25)} m² ; 440 m² dépassent (le 40 % "
  "ne vaut que sous 1 000 m²)", "permis de construire + architecte", "permis de construire avec architecte (plus de 150 m²)",
  [r("UD 9", "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa, UDa* et UDb", "25 % de la parcelle en UDa")],
  ["R421-14", "R431-2"], [], "appliquer le 40 % réservé aux parcelles de moins de 1 000 m²")
a = adr("UD", "BN 0110")
q(13, "B", "Mon voisin veut élever un mur plein de 2,40 m entre nos deux terrains, {adr}. A-t-il le droit ?", a, "clôture", "voisin", "règle",
  "non", "non en principe : en UD, 2 m au plus entre voisins ; plus haut seulement pour des raisons techniques ou esthétiques que la mairie apprécie",
  "déclaration préalable", "déclaration préalable (toutes les clôtures à Biarritz)",
  [r("UD 11", "La hauteur de la clôture ne peut excéder 2,00 mètres", "2 m au plus entre voisins")], ["R421-12"], [],
  "accepter 2,40 m parce que la clôture est « entre voisins »")
a = adr("UH", "BK 0441")
q(14, "B", "Je veux clôturer avec un grillage rigide vert de 1,80 m, sans haie, {adr}. C'est permis ?", a, "clôture", "propriétaire", "règle",
  "non", "non : en UH, un grillage non planté d'une haie est interdit", "déclaration préalable", "déclaration préalable (toutes les clôtures à Biarritz)",
  [r("UH 11", "Les clôtures composées de grillage et non plantées d’une haie et celles constituées de panneaux en béton, en plastique "
              "(polycarbonate) ou en clins de bois, sont interdites", "un grillage sans haie est interdit")], ["R421-12"], [],
  "ne regarder que la hauteur (1,80 m < 2 m)")
a = adr("UG", "BI 0083")
q(15, "B", "Puis-je construire ma maison {adr} ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en UG, les constructions destinées à l'habitation sont interdites", "sans objet", "sans objet",
  [r("UG 1", "les constructions destinées à l’habitation, sauf pour l’extension et la démolition des constructions existantes sous les conditions "
             "fixées à l’article UG 2", "pas de maison neuve en UG")], [], [], "raisonner comme en zone d'habitat")
a = adr("UY", "AP 0060")
q(16, "B", "Je voudrais construire ma maison {adr}. C'est possible ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en zone UY, les constructions destinées à l'habitation sont interdites", "sans objet", "sans objet",
  [r("UY 1", "Sont interdits en zone UY et secteurs UY*, UYi, UYt : - les constructions destinées à l’habitation", "pas d'habitation en UY")], [], [],
  "raisonner comme en zone d'habitat")
a = adr("Ner", "BM 0334")
q(17, "B", "Je veux construire une maison {adr}. Le terrain est en bord de mer. Possible ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en Ner, seules les constructions justifiées par la sécurité, les services publics ou la confortation de l'existant sont admises",
  "sans objet", "sans objet",
  [r("Ner 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité, l’équipement sanitaire, les services publics ou la confortation "
              "de l’existant", "constructions neuves interdites en Ner")], [], [], "confondre Ner et zone constructible")
a = adr("UD", "AC 0114")
q(18, "B", "Ma maison est déjà en R+2 avec 9 m à l'égout du toit. Puis-je ajouter un étage de 3 m {adr} ?", a, "surélévation", "propriétaire", "règle",
  "non", "non : en UD, 9 m à l'égout au plus (R+2+combles) ; 12 m dépassent", "dépend de la surface créée",
  "dépend de la surface créée (déclaration préalable ; permis si plus de 40 m² sont créés en zone urbaine)",
  [r("UD 10", "en zone UD et en secteur UDb : R + 2 + Comble (3 niveaux + combles) et 9 m à l'acrotère ou égout du toit et 12,50 m au faîtage",
     "R+2+combles, 9 m à l'égout")], ["R421-14"], [], "croire qu'un étage de plus entre dans les combles")
a = adr("UDb", "AA 0116")
q(19, "B", "{ADR}, terrain de {S} m², ma maison fait 150 m² d'emprise. Je veux l'agrandir de 40 m² d'emprise. C'est possible ?", a, "extension",
  "propriétaire", "règle", "non", f"non : en UDb, 30 % de {int(a['surface_m2'])} m² font {round(a['surface_m2'] * 0.3, 1)} m² ; 190 m² dépassent",
  "permis de construire + architecte", "permis de construire avec architecte (plus de 150 m² après travaux)",
  [r("UD 9", "à 0,30 pour les parcelles de surface inférieure à 1.000 m² en secteur UDb", "30 % de la parcelle en UDb sous 1 000 m²")],
  ["R421-14", "R431-2"], [], "appliquer les 25 % de UDa ou les 50 % de UD")
a = adr("UDa", "AX 0180")
q(20, "B", "Je veux construire une maison avec 9 m à l'égout du toit {adr}. C'est possible ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en UDa, R+1+combles et 6 m à l'égout au plus", "permis de construire", "permis de construire",
  [r("UD 10", "en secteurs UDa, UDa*, UDi, UDi*, UDs et UDt : R + 1 + comble (2 niveaux + combles) et 6 m à l'égout du toit", "R+1+combles, 6 m à l'égout en UDa")],
  [], [], "appliquer les 9 m d'UD")

# ============================================================================================ C · 10 cas où une information décisive manque
a = adr("N", "AA 0008")
q(21, "C", "Puis-je poser un abri de jardin de 8 m² dans mon jardin {adr} ?", a, "abri de jardin", "propriétaire", "règle", "impossible à dire",
  "impossible à dire : en zone N, une annexe n'est admise que pour une construction qui existait en mars 1995 ; la question ne dit pas de quand date la maison",
  "déclaration préalable", DP5_20,
  [r("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la révision du P.O.S. de mars 1995",
     "annexes admises seulement pour une construction existant en 1995")], ["R421-9"], ["la date de construction de la maison"],
  "raisonner comme en zone urbaine")
a = adr("N", "BT 0041")
q(22, "C", "Je voudrais creuser une piscine non couverte de 30 m² {adr}. C'est possible ?", a, "piscine", "propriétaire", "règle", "impossible à dire",
  "impossible à dire : en zone N, une annexe (piscine) n'est admise que pour une construction qui existait en mars 1995", "déclaration préalable",
  "déclaration préalable (bassin jusqu'à 100 m²)",
  [r("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la révision du P.O.S. de mars 1995",
     "annexes admises seulement pour une construction existant en 1995")], ["R421-9"], ["la date de construction de la maison"],
  "croire que la piscine échappe à la règle des annexes")
a = adr("Nh", "CE 0082")
q(23, "C", "Ma maison est en zone Nh, {adr}. Je veux l'agrandir de 30 m² : est-ce autorisé ?", a, "extension", "propriétaire", "règle", "impossible à dire",
  "impossible à dire : en Nh, l'extension est limitée à 25 % de la surface de plancher existante avant le 27 mars 1995 ; la surface de départ n'est pas donnée",
  "permis de construire", "permis de construire (plus de 20 m² hors zone urbaine)",
  [r("N 2", "l'extension des ces constructions est limitée à 25 % de la surface de plancher existante avant l’approbation du P.O.S. le 27 mars 1995",
     "25 % de la surface de 1995 au plus")], ["R421-14"], ["la surface de plancher de la maison avant mars 1995"], "appliquer les 40 m² d'une zone urbaine")
a = adr("UDa", "AT 0052")
q(24, "C", "{ADR} (terrain de {S} m²), ma maison fait 100 m² d'emprise. Je veux y ajouter 60 m² d'emprise : est-ce dans les règles ?", a, "extension",
  "propriétaire", "règle", "impossible à dire",
  f"impossible à dire : 160 m² dépassent les 25 % ({round(a['surface_m2'] * 0.25, 1)} m²) mais respectent les 40 % ({round(a['surface_m2'] * 0.4, 1)} m²) "
  "qui valent si la parcelle existait avant la révision du PLU de 2003", "permis de construire + architecte",
  "permis de construire avec architecte (plus de 150 m² après travaux)",
  [r("UD 9", "à 0,40 pour les parcelles de surface inférieure à 1.000m² en secteurs Uda et UDa*existants antérieurement à la révision du P.L.U. de 2003",
     "40 % si la parcelle existait avant 2003")], ["R421-14", "R431-2"], ["la date d'existence de la parcelle (avant ou après 2003)"],
  "appliquer 25 % sans voir l'exception de 40 %")
a = adr("UDa", "AX 0591")
q(25, "C", "Terrain de {S} m² {adr}, maison de 120 m² d'emprise, je veux ajouter une extension de 50 m² d'emprise. Possible ?", a, "extension",
  "propriétaire", "règle", "impossible à dire",
  f"impossible à dire : 170 m² dépassent les 25 % ({round(a['surface_m2'] * 0.25, 1)} m²) mais respectent les 40 % ({round(a['surface_m2'] * 0.4, 1)} m²) "
  "si la parcelle existait avant 2003", "permis de construire + architecte", "permis de construire avec architecte (plus de 150 m² après travaux)",
  [r("UD 9", "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa, UDa* et UDb", "25 % de la parcelle en UDa")],
  ["R421-14", "R431-2"], ["la date d'existence de la parcelle (avant ou après 2003)"], "répondre « non » sans connaître la date de la parcelle")
a = adr("UD", "BK 0405")
q(26, "C", "Je veux surélever ma maison d'un étage de 3 m {adr}, mais je ne sais pas à quelle hauteur est mon toit aujourd'hui. Est-ce possible ?", a,
  "surélévation", "propriétaire", "règle", "impossible à dire", "impossible à dire : en UD, 9 m à l'égout au plus ; tout dépend de la hauteur actuelle de la maison",
  "dépend de la surface créée", "dépend de la surface créée (déclaration préalable ; permis si plus de 40 m² sont créés)",
  [r("UD 10", "en zone UD et en secteur UDb : R + 2 + Comble (3 niveaux + combles) et 9 m à l'acrotère ou égout du toit et 12,50 m au faîtage",
     "R+2+combles, 9 m à l'égout")], ["R421-14"], ["la hauteur actuelle de la maison à l'égout"], "répondre sans la hauteur actuelle")
a = adr("UDa", "BR 0114")
q(27, "C", "Ma maison {adr} a un seul étage, je voudrais en ajouter un autre mais je ne connais pas la hauteur exacte de mon égout. Possible ?", a,
  "surélévation", "propriétaire", "règle", "impossible à dire", "impossible à dire : en UDa, 6 m à l'égout au plus ; tout dépend de la hauteur actuelle",
  "dépend de la surface créée", "dépend de la surface créée (déclaration préalable ; permis si plus de 40 m² sont créés)",
  [r("UD 10", "en secteurs UDa, UDa*, UDi, UDi*, UDs et UDt : R + 1 + comble (2 niveaux + combles) et 6 m à l'égout du toit", "R+1+combles, 6 m à l'égout en UDa")],
  ["R421-14"], ["la hauteur actuelle de la maison à l'égout"], "répondre sans la hauteur actuelle")
a = adr("UH", "BP 0271")
q(28, "C", "Je veux ajouter un étage de 3 m à mon immeuble {adr}. Je ne sais plus combien de niveaux il a. Possible ?", a, "surélévation",
  "propriétaire", "règle", "impossible à dire", "impossible à dire : en UH, 5 niveaux (R+4) et 15 m à l'égout au plus ; tout dépend du nombre de niveaux actuel",
  "dépend de la surface créée", "dépend de la surface créée (déclaration préalable ; permis si plus de 40 m² sont créés)",
  [r("UH 10", "La hauteur d'une construction ne peut excéder 5 niveaux, soit R + 4 superposés", "R+4 au plus, 15 m à l'égout")], ["R421-14"],
  ["le nombre de niveaux et la hauteur actuels"], "répondre sans le nombre de niveaux actuel")
a = adr("N", "CE 0057")
q(29, "C", "J'ai un jardin {adr}. Je pense y mettre un abri de jardin de 12 m². Est-ce autorisé ?", a, "abri de jardin", "propriétaire", "règle",
  "impossible à dire", "impossible à dire : en zone N, une annexe n'est admise que pour une construction existant en mars 1995", "déclaration préalable", DP5_20,
  [r("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la révision du P.O.S. de mars 1995",
     "annexes admises seulement pour une construction existant en 1995")], ["R421-9"], ["la date de construction de la maison"], "raisonner comme en zone urbaine")
a = adr("N", "AT 0178")
q(30, "C", "Piscine non couverte de 20 m² dans mon jardin, {adr}. Ai-je le droit ?", a, "piscine", "propriétaire", "règle", "impossible à dire",
  "impossible à dire : en zone N, une annexe (piscine) n'est admise que pour une construction existant en mars 1995", "déclaration préalable",
  "déclaration préalable (bassin jusqu'à 100 m²)",
  [r("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la révision du P.O.S. de mars 1995",
     "annexes admises seulement pour une construction existant en 1995")], ["R421-9"], ["la date de construction de la maison"], "croire qu'une piscine ouverte est libre en zone N")

# ============================================================================================ D · 10 zones strictes et exceptions
a = adr("Nh", "BX 0012")
q(31, "D", "Je possède un terrain en zone Nh {adr}. Je voudrais y construire une villa individuelle. C'est autorisé ?", a, "maison neuve", "propriétaire", "règle",
  "oui sous conditions", "oui sous conditions : en Nh, une villa individuelle est admise, sous condition d'insertion dans l'espace naturel", "permis de construire",
  "permis de construire",
  [r("N 2", "En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire, sous condition d’insertion dans l’espace naturel, et de ses "
            "annexes (telles que garage, piscine, abri de jardin)", "villa individuelle admise en Nh")], [], ["l'insertion dans l'espace naturel", "l'emprise (10 % au plus)"],
  "tout interdire parce que la zone est naturelle")
a = adr("Nh", "CE 0027")
q(32, "D", "Piscine non couverte de 40 m² dans le jardin de ma villa, zone Nh, {adr}. C'est possible ?", a, "piscine", "propriétaire", "règle",
  "oui sous conditions", "oui sous conditions : en Nh, les annexes d'une villa (dont la piscine) sont admises", "déclaration préalable",
  "déclaration préalable (bassin jusqu'à 100 m²)",
  [r("N 2", "En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire, sous condition d’insertion dans l’espace naturel, et de ses "
            "annexes (telles que garage, piscine, abri de jardin)", "les annexes, dont la piscine, sont admises en Nh")], ["R421-9"],
  ["l'insertion dans l'espace naturel"], "tout interdire parce que la zone est naturelle")
a = adr("Ncu", "BT 0047")
q(33, "D", "Je voudrais une piscine non couverte de 35 m² {adr} (zone Ncu). Est-ce autorisé ?", a, "piscine", "propriétaire", "règle", "oui sous conditions",
  "oui sous conditions : en Ncu, une piscine non couverte par unité foncière est admise", "déclaration préalable", "déclaration préalable (bassin jusqu'à 100 m²)",
  [r("Ncu 2", "une piscine non couverte par unité foncière", "une piscine non couverte admise")], ["R421-9"], ["une seule piscine par unité foncière"],
  "tout interdire parce que la zone est une coupure d'urbanisation")
a = adr("Ncu", "CK 0037")
q(34, "D", "Puis-je construire une maison neuve {adr} ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en Ncu, seules les constructions justifiées par la sécurité, les services publics ou la confortation de l'existant sont admises", "sans objet", "sans objet",
  [r("Ncu 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité, l’équipement sanitaire, un service public ou la confortation de l’existant",
     "constructions neuves interdites en Ncu")], [], [], "confondre Ncu et Nh")
a = adr("UG", "AM 0060")
q(35, "D", "Mon voisin veut construire une maison neuve {adr} : a-t-il le droit ?", a, "maison neuve", "voisin", "règle", "non",
  "non : en UG, les constructions destinées à l'habitation sont interdites", "sans objet", "sans objet",
  [r("UG 1", "les constructions destinées à l’habitation, sauf pour l’extension et la démolition des constructions existantes sous les conditions "
             "fixées à l’article UG 2", "pas de maison neuve en UG")], [], [], "raisonner comme en zone d'habitat")
a = adr("UY", "AK 0441")
q(36, "D", "Est-ce que je peux faire construire une villa {adr} ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en UY, les constructions destinées à l'habitation sont interdites", "sans objet", "sans objet",
  [r("UY 1", "Sont interdits en zone UY et secteurs UY*, UYi, UYt : - les constructions destinées à l’habitation", "pas d'habitation en UY")], [], [],
  "raisonner comme en zone d'habitat")
a = adr("N", "CE 0113")
q(37, "D", "Je voudrais construire une villa neuve en zone naturelle {adr}. C'est possible ?", a, "maison neuve", "propriétaire", "règle", "non",
  "non : en zone N hors secteurs habitables (Nh, Nhd), tout est interdit sauf des exceptions que ce projet ne remplit pas", "sans objet", "sans objet",
  [r("N 1", "Tous les types d'occupation ou d'utilisation des sols sont interdits", "en zone N, tout est interdit sauf exceptions")], [], [],
  "confondre la zone N et ses secteurs habitables Nh")
a = adr("Ner", "BB 0002")
q(38, "D", "Je veux poser un abri de jardin de 6 m² {adr}. Possible ?", a, "abri de jardin", "propriétaire", "règle", "non",
  "non : en Ner, un abri est une construction nouvelle que l'article Ner 1 interdit", "sans objet", "sans objet",
  [r("Ner 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité, l’équipement sanitaire, les services publics ou la confortation "
              "de l’existant", "constructions neuves interdites en Ner")], [], [], "croire qu'un petit abri est toléré")
a = adr("Ncu", "BX 0011")
q(39, "D", "Ma maison est en zone Ncu {adr}. Je veux l'agrandir de 25 m² d'emprise. C'est autorisé ?", a, "extension", "propriétaire", "règle", "non",
  "non : en Ncu, l'extension est limitée à 20 m² d'emprise au sol depuis 1995 ; 25 m² dépassent", "permis de construire",
  "permis de construire (plus de 20 m² hors zone urbaine)",
  [r("Ncu 2", "l'extension des constructions est limitée à 20 m² d’emprise au sol à partir de la date d'approbation de la révision n° 2 du P.O.S.",
     "20 m² d'extension au plus")], ["R421-14"], [], "appliquer les 40 m² d'une zone urbaine")
a = adr("Nh", "CE 0006")
q(40, "D", "Abri de jardin de 20 m² dans ma propriété en zone Nh, {adr}. Possible ?", a, "abri de jardin", "propriétaire", "règle", "oui sous conditions",
  "oui sous conditions : en Nh, les annexes (dont l'abri de jardin) sont admises ; l'emprise (10 % au plus) et l'insertion restent à vérifier",
  "déclaration préalable", DP5_20,
  [r("N 2", "En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire, sous condition d’insertion dans l’espace naturel, et de ses "
            "annexes (telles que garage, piscine, abri de jardin)", "les annexes, dont l'abri de jardin, sont admises en Nh"),
   r("N 9", "En secteurs Nh et Nhd, l’emprise au sol est fixée à 0,10 au maximum", "10 % de la parcelle au plus en Nh")], ["R421-9"],
  ["l'emprise totale (10 % au plus)"], "tout interdire parce que la zone est naturelle")

# les réponses attendues supposent ces surfaces (maison + projet sous ou sur l'emprise maximale) : on les vérifie avant de sceller
SURFACE = {x["faits"]["parcelle"]: x["faits"]["surface_m2"] for x in Q}
assert SURFACE["AB 0521"] * 0.5 >= 98 and SURFACE["AE 0450"] * 0.7 >= 95 and SURFACE["AL 0160"] * 0.5 >= 115 \
    and SURFACE["AL 0125"] * 0.7 >= 150, "D01, D02, D08, D09 : emprise sous le maximum"
assert SURFACE["AI 0156"] * 0.25 < 440 and 1000 <= SURFACE["AI 0156"] < 1760, "D12 : 440 m² dépassent 25 %"
assert SURFACE["AA 0116"] * 0.3 < 190 and SURFACE["AA 0116"] < 1000, "D19 : 190 m² dépassent 30 %"
assert SURFACE["AT 0052"] * 0.25 < 160 <= SURFACE["AT 0052"] * 0.4 and SURFACE["AT 0052"] < 1000, "D24 : entre 25 % et 40 %"
assert SURFACE["AX 0591"] * 0.25 < 170 <= SURFACE["AX 0591"] * 0.4 and SURFACE["AX 0591"] < 1000, "D25 : entre 25 % et 40 %"

if __name__ == "__main__":
    chemin = os.path.join(B, "questions-cachees-2.json")
    texte = json.dumps(Q, ensure_ascii=False, indent=1)
    open(chemin, "w", encoding="utf-8", newline="\n").write(texte)  # LF seulement : l'empreinte du fichier est celle du texte scellé
    empreinte = hashlib.sha256(texte.encode("utf-8")).hexdigest()
    open(os.path.join(B, "questions-cachees-2.sha256"), "w", encoding="utf-8").write(
        f"{empreinte}  questions-cachees-2.json  scellé le {datetime.now():%Y-%m-%d %H:%M}, avant tout passage de l'agent\n")
    e = html.escape
    cartes = "".join(
        f"<article><header><b>{x['id']}</b> <span>groupe {x['groupe']} · {e(x['faits']['zone'])} · parcelle {e(str(x['faits']['parcelle']))}, "
        f"{x['faits']['surface_m2']} m²</span></header><h2>« {e(x['question'])} »</h2>"
        f"<p class='attendu'><b>{e(x['attendu']['verdict_type'])}</b> — {e(x['attendu']['verdict'])}</p>"
        f"<p class='dem'>Démarche : {e(x['attendu']['demarche'])}</p>"
        + "".join(f"<p class='cit'><b>{e(g['article'])}, p. {g['page']}</b> « {e(g['citation'])} »</p>" for g in x['attendu']['regles']) + "</article>"
        for x in Q)
    comptes = {g: sum(1 for x in Q if x["groupe"] == g) for g in "ABCD"}
    page = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>2e banc caché · assistant PLU</title><link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>:root{{--fond:#F5F0E8;--carte:#fff;--encre:#1D1A17;--gris:#8A837B;--filet:#E4DCD0}}*{{box-sizing:border-box;margin:0}}
body{{background:var(--fond);color:var(--encre);font:400 15px/1.45 Geist,system-ui,sans-serif;padding:32px 40px 60px;max-width:1500px;margin:auto}}
h1{{font-size:36px;font-weight:800}}.chapo{{color:var(--gris);font-size:17px;margin:6px 0 20px;max-width:1100px}}
.sceau{{font-family:ui-monospace,Consolas,monospace;font-size:13px;background:var(--carte);border:1px solid var(--filet);border-radius:10px;padding:10px 14px;margin-bottom:20px;overflow-wrap:anywhere}}
main{{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}}article{{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:14px 16px;display:flex;flex-direction:column;gap:5px}}
header span{{color:var(--gris);font-size:13px}}h2{{font-size:16px;font-weight:600}}.dem{{font-size:13px;color:var(--gris)}}.attendu{{font-size:14px}}.cit{{font-size:13px;color:#4a443e}}
@media (max-width:900px){{main{{grid-template-columns:1fr}}body{{padding:20px 16px}}}}</style></head><body>
<h1>Le 2e banc caché : 40 questions en 4 groupes</h1>
<p class="chapo">A. clairement permis ({comptes['A']}) · B. clairement interdit ({comptes['B']}) · C. information manquante ({comptes['C']}) ·
D. zones strictes et exceptions ({comptes['D']}). Réponses attendues écrites et scellées avant tout passage de l'agent ; chaque citation
est vérifiée mot pour mot par le code ; adresses jamais utilisées. Un seul passage.</p>
<p class="sceau">SHA-256 {empreinte}</p><main>{cartes}</main></body></html>"""
    open(os.path.join(B, "questions-cachees-2.html"), "w", encoding="utf-8").write(page)
    import collections
    print(len(Q), "questions ;", dict(collections.Counter(x["attendu"]["verdict_type"] for x in Q)), ";",
          sum(len(x["attendu"]["regles"]) for x in Q), "citations vérifiées ; empreinte", empreinte[:16])
