"""Le banc d'essai v1 : 20 questions réelles sur Biarritz, avec la bonne réponse écrite à partir du règlement.
Sorties : bancs/jeux/questions.json (pour la notation automatique) et bancs/jeux/questions.html (pour validation)."""
import html, json, os, re
from orbi.chemins import DONNEES, JEUX  # noqa: E402

ICI = os.path.dirname(os.path.abspath(__file__))
D = DONNEES
B = JEUX
pages = json.load(open(os.path.join(D, "pages.json"), encoding="utf-8"))
C = {c["adresse"]: c for c in json.load(open(os.path.join(B, "adresses-candidates.json"), encoding="utf-8"))}


ARTICLES = json.load(open(os.path.join(D, "articles.json"), encoding="utf-8"))


def page(article, phrase):
    """La page où se trouve vraiment la phrase, cherchée UNIQUEMENT dans les pages de l'article cité : la même phrase
    revient souvent d'une zone à l'autre (« Les piscines, spas et jacuzzis… » en UB, UC et UD)."""
    zone, num = ("DG", "0") if article.startswith("DG") else article.split()
    p0, p1 = ARTICLES[zone][num]["pages"]
    norme = lambda s: " ".join(s.replace("", " ").split())  # le PDF met des puces «  » dans les listes
    cle = norme(phrase)
    for p, t in pages:
        if p0 <= p <= p1 and cle[:60] in norme(t):
            return p
    # la phrase peut chevaucher deux pages : on la cherche dans le texte complet de l'article
    if cle[:60] in norme(ARTICLES[zone][num]["texte"]):
        return p0
    raise ValueError(f"phrase introuvable dans {article} (p. {p0}-{p1}) : {cle[:60]}")


def r(article, phrase, dit):
    return {"article": article, "page": page(article, phrase), "citation": phrase, "dit": dit}


SPR = "servitude AC4 : site patrimonial remarquable, l'Architecte des Bâtiments de France (ABF) donne son avis"
EMPRISE_DG = r("DG B-5", "toutefois les installations sportives de plein-air telles que piscines non couvertes",
               "une piscine non couverte ne compte pas dans l'emprise au sol")
Q = []


def q(n, question, adresse, projet, verdict, regles, verifier, piege, bord=False, faits=None):
    c = C.get(adresse, {})
    f = faits or {"zone": (c.get("zone") or ["?"])[0], "parcelle": c.get("parcelle"), "surface_m2": c.get("surface_m2"),
                  "contraintes": [x for x in c.get("prescriptions", []) + c.get("servitudes", [])
                                  if not re.fullmatch(r"U[A-Z][a-z]?|Majoration des volumes.*", x)]}
    Q.append({"id": f"Q{n:02d}", "type": "bord" if bord else "normale", "question": question, "adresse": adresse,
              "projet": projet, "faits": f, "attendu": {"verdict": verdict, "regles": regles, "a_verifier": verifier},
              "piege": piege})


q(1, "Puis-je construire une véranda de 20 m² à la mairie de Biarritz, 12 avenue Édouard VII ?",
  "12 Avenue Edouard VII 64200 Biarritz", "véranda", "oui sous conditions, avec un vrai risque de refus",
  [r("UA 9", "Il n'est pas fixé d'emprise au sol sauf en UAc", "aucune emprise maximale en UAs"),
   r("UA 11", "ajouts ou excroissances, vérandas etc... pourront être interdites",
     "sur un bâtiment repéré (règles architecturales particulières), une véranda peut être interdite")],
  [SPR, "déclaration préalable ou permis selon la surface"], "appliquer une limite d'emprise qui ne vaut qu'en UAc",
  faits={"zone": "UAs", "parcelle": "BA 0008", "surface_m2": 1472,
         "contraintes": ["Règles architecturales particulières (cf. Art. 11)", "Site patrimonial remarquable de Biarritz"]})
q(2, "Je veux surélever d'un étage le bâtiment du 2 rue de la Bergerie à Biarritz. C'est possible ?",
  "2 Rue de la Bergerie 64200 Biarritz", "surélévation", "impossible à dire sans savoir où est le bâtiment sur la parcelle",
  [r("UA 10", "La hauteur des constructions est fixée par le plan de P.L.U., au 1/2000è ci-annexé",
     "le plan fixe la hauteur ; ici deux niveaux coexistent sur la parcelle : « 3 » (12,50 m à l'égout, R+3+comble) et « 5 » (18 m, R+5+comble)")],
  ["la hauteur actuelle du bâtiment et sa position sur la parcelle", SPR],
  "donner une seule hauteur alors que le plan en indique deux sur cette grande parcelle (3 470 m²)")
q(3, "Puis-je ajouter un étage à ma maison au 2 avenue d'Etienne, Biarritz ?",
  "2 Avenue d'Etienne 64200 Biarritz", "surélévation", "oui si le bâtiment reste sous 8,50 m à l'égout et 14 m au faîtage",
  [r("UB 10", "La hauteur des constructions est fixée par le plan de P.L.U., au 1/2000è ci-annexé, par mention des hauteurs autorisées par parcelle ou groupe",
     "le plan indique le niveau « 2 » pour cette parcelle : 8,50 m à l'égout, 14 m au faîtage, rez-de-chaussée + 2 étages + comble")],
  ["le nombre de niveaux et la hauteur actuels", SPR], "ne pas aller chercher le code de hauteur sur le plan (Géoportail)")
q(4, "Puis-je faire une piscine non couverte au 31 avenue du Maréchal Joffre à Biarritz ?",
  "31 Avenue du Maréchal Joffre 64200 Biarritz", "piscine", "oui en principe",
  [EMPRISE_DG, r("UB 9", "L’EMPRISE AU SOL DES CONSTRUCTIONS Sans objet", "pas d'emprise maximale en UB"),
   r("UB 7", "Les piscines, spas et jacuzzis sont exclus de cette règle", "la règle de distance aux limites ne s'applique pas aux piscines")],
  [SPR, "déclaration préalable (bassin de 10 à 100 m²)"], "compter la piscine dans l'emprise au sol")
q(5, "Je veux une clôture de 2 m le long de la rue au 96 avenue de Verdun, Biarritz. C'est autorisé ?",
  "96 Avenue de Verdun 64200 Biarritz", "clôture", "oui, 2 m est le maximum sur la rue en UB",
  [r("UB 11", "e-2 - clôtures sur l'espace public : La hauteur totale des clôtures ne peut excéder 2 mètres",
     "clôture sur la rue : 2 m au plus"),
   r("UB 11", "il ne pourra être autorisé que la construction d'un mur bahut dont la hauteur n'excédera pas 1,00 mètre",
     "dans certaines rues à murs bahuts, seul un mur bahut de 1 m surmonté d'une grille est admis")],
  ["si la rue fait partie des voies à murs bahuts", SPR], "reprendre la limite de 1,50 m de la zone UD")
q(6, "Je voudrais agrandir ma maison de 40 m² au 9 allée du Moura à Biarritz. C'est possible ?",
  "9 Allée du Moura 64200 Biarritz", "extension", "oui si l'emprise totale reste sous 70 % de la parcelle (511 m² sur 730)",
  [r("UC 9", "l'emprise au sol maximale est fixée à 70 % de l'unité foncière", "emprise au sol maximale : 70 %"),
   r("UC 7", "Les constructions peuvent s'implanter sur les limites séparatives ou à au moins 3 mètres de celles-ci",
     "en limite de propriété ou à 3 m au moins")],
  ["l'emprise des constructions existantes", "la zone d'implantation obligatoire de 0 à 4 m imposée côté rue (art. UC 6)"],
  "oublier de convertir le pourcentage en m² de la vraie parcelle")
q(7, "Puis-je installer un abri de jardin de 9 m² au 30 avenue Tamames, Biarritz ?",
  "30 Avenue Tamames 64200 Biarritz", "abri de jardin", "oui hors de l'espace boisé classé, non dans sa partie classée",
  [r("UC 9", "l'emprise au sol maximale est fixée à 70 % de l'unité foncière", "emprise au sol maximale : 70 %")],
  ["où se trouve l'espace boisé classé (code de l'urbanisme, art. L113-1) sur la parcelle"],
  "ignorer l'espace boisé classé signalé par le Géoportail")
q(8, "Puis-je construire une véranda de 20 m² avenue du Docteur Claisse (parcelle AB 0323), à Biarritz ?",
  "Avenue du Docteur Claisse 64200 Biarritz", "véranda", "oui sous conditions",
  [r("UD 9", "L'emprise au sol maximale en UD et en secteurs UDi et UDi*, et UDt est fixée à 50%", "emprise au sol maximale : 50 %"),
   r("UD 11", "L'autorisation de démolir pourra être refusée sur toute ou partie des constructions situées au droit des liserés",
     "bâtiment repéré : son aménagement peut être encadré ; l'article UD 11 ne cite pas les vérandas")],
  ["l'emprise existante", SPR], "recopier la phrase « vérandas… pourront être interdites » des zones UA et UB, absente en UD")
q(9, "Une piscine non couverte au 6 rue Castellamare, à Biarritz, c'est autorisé ?",
  "6 Rue Castellamare 64200 Biarritz", "piscine", "oui en principe",
  [EMPRISE_DG, r("UD 7", "Les piscines, spas et jacuzzis sont exclus de cette règle",
                 "la règle de distance aux limites ne s'applique pas aux piscines")],
  [SPR, "déclaration préalable"], "appliquer la limite d'emprise de 25 % de la zone UDa à une piscine non couverte")
q(10, "Je veux agrandir ma maison de 25 m² au 3 rue Pierre Dartiguelongue, à Biarritz. Possible ?",
  "3 Rue Pierre Dartiguelongue 64200 Biarritz", "extension",
  "oui si l'emprise totale ne dépasse pas 85,5 m² (25 % de 342 m²), ou 136,8 m² (40 %) si la parcelle existait avant 2003",
  [r("UD 9", "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa",
     "25 % en UDa, porté à 40 % pour les parcelles de moins de 1 000 m² existant avant la révision de 2003, 250 m² au plus")],
  ["l'emprise des constructions existantes", "la date de création de la parcelle"], "ne pas voir l'exception des 40 %")
q(11, "Puis-je construire une maison individuelle au 37 allée du Moura, à Biarritz ?",
  "37 Allée du Moura 64200 Biarritz", "maison neuve", "non",
  [r("UG 1", "les constructions destinées à l’habitation", "l'habitation est interdite en UG, sauf extension de l'existant ou logement lié à l'équipement")],
  ["l'emplacement réservé pour l'élargissement de la rue du Moura (15 m)"], "répondre oui parce que la parcelle est grande (8 522 m²)")
q(12, "Au 21 avenue de Ségure à Biarritz, puis-je surélever l'immeuble ?",
  "21 Avenue de Ségure 64200 Biarritz", "surélévation", "oui jusqu'à 5 niveaux (R+4) : 15 m à l'égout, 21 m au faîtage",
  [r("UH 10", "La hauteur d'une construction ne peut excéder 5 niveaux, soit R + 4 superposés",
     "5 niveaux au plus, 15 m à l'égout ou à l'acrotère, 21 m au faîtage")],
  ["la hauteur actuelle", SPR], "ne pas savoir que UH est la zone des grandes hauteurs")
q(13, "Puis-je poser un abri de jardin au 14 rue du Moulin de Chabiague, à Biarritz ?",
  "14 Rue du Moulin de Chabiague 64200 Biarritz", "abri de jardin", "non, sauf annexe d'une construction existante",
  [r("N 1", "Tous les types d'occupation ou d'utilisation des sols sont interdits", "en zone N, tout est interdit sauf exceptions"),
   r("N 2", "l'extension, aménagement, les annexes des constructions existantes à la date d'approbation de la révision du P.O.S. de mars 1995",
     "les annexes ne sont admises que pour une construction existante en 1995")],
  ["s'il existe une construction de 1995 ou avant sur la parcelle", SPR], "raisonner comme en zone urbaine")
q(14, "Puis-je creuser une piscine au 1 allée de Barroilhet, à Biarritz ?",
  "1 Allée de Barroilhet 64200 Biarritz", "piscine", "oui sous conditions, hors espace boisé classé",
  [r("N 2", "En Nh et Nhd, la construction d’une villa individuelle à caractère pavillonnaire",
     "en Nh, la villa et ses annexes (garage, piscine, abri) sont admises sous condition d'insertion dans l'espace naturel"),
   r("N 2", "ne sont autorisés que :  les aménagements légers non bâtis",
     "dans l'espace vert protégé, seuls des aménagements limités sont admis")],
  ["où se trouvent l'espace boisé classé et l'espace vert protégé sur la parcelle"], "répondre non parce que c'est une zone N")
q(15, "Puis-je construire une maison allée Gabrielle Dorziat (parcelle CA 0044), à Biarritz ?",
  "Allée Gabrielle Dorziat 64200 Biarritz", "maison neuve", "non",
  [r("Ncu 1", "Toutes constructions qui ne seraient pas justifiées par la sécurité",
     "en Ncu (coupure d'urbanisation), une construction neuve n'est admise que pour la sécurité, un service public ou le confortement de l'existant")],
  ["espace boisé classé et espace vert protégé sur la parcelle", SPR], "confondre Ncu et Nh")
q(16, "Puis-je construire une véranda rue Marie Blanque à Anglet ?", "Rue Marie Blanque 64600 Anglet", "véranda",
  "hors périmètre : la v1 ne couvre que Biarritz", [], ["le PLU d'Anglet (ou le PLUi du Pays basque) auprès de la mairie"],
  "répondre avec le règlement de Biarritz", bord=True, faits={"zone": "hors Biarritz (commune 64024)"})
q(17, "Combien vaut ma maison au 6 rue Castellamare à Biarritz ?", "6 Rue Castellamare 64200 Biarritz", "hors carte",
  "hors carte : l'assistant répond sur les règles d'urbanisme, pas sur les prix", [], [],
  "inventer une estimation", bord=True)
q(18, "Est-ce que je peux agrandir, au 3 rue Pierre Dartiguelongue ?", "3 Rue Pierre Dartiguelongue 64200 Biarritz",
  "à préciser", "demander de quelle surface, en donnant la règle clé (25 % d'emprise en UDa)",
  [r("UD 9", "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa", "25 % d'emprise en UDa")],
  ["la surface du projet", "l'emprise existante"], "répondre oui ou non sans connaître la surface", bord=True)
q(19, "Je veux installer des panneaux solaires sur mon toit au 2 rue de la Bergerie, à Biarritz.",
  "2 Rue de la Bergerie 64200 Biarritz", "hors carte",
  "hors carte en v1 (les 6 projets couverts sont : véranda, extension, piscine, abri, clôture, surélévation)", [],
  ["la mairie, et l'ABF (site patrimonial remarquable)"], "répondre quand même sans avoir lu les règles utiles", bord=True)
q(20, "Puis-je construire une piscine couverte de 30 m² au 3 rue Pierre Dartiguelongue, à Biarritz ?",
  "3 Rue Pierre Dartiguelongue 64200 Biarritz", "piscine",
  "oui si l'emprise totale reste sous 85,5 m² (25 %) ou 136,8 m² (40 % si parcelle antérieure à 2003)",
  [EMPRISE_DG, r("UD 9", "L'emprise au sol est limitée à 25 % de l'unité foncière en secteurs UDa",
                 "une piscine couverte compte dans l'emprise : 25 % en UDa")],
  ["l'emprise existante", "la date de création de la parcelle"],
  "traiter la piscine couverte comme une piscine non couverte (hors emprise)", bord=True)

json.dump(Q, open(os.path.join(B, "questions.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# ---------------------------------------------------------------- page de validation
e = html.escape
cartes = []
for x in Q:
    f, a = x["faits"], x["attendu"]
    tags = "".join(f"<span class='tag'>{e(t)}</span>" for t in f.get("contraintes", []))
    regles = "".join(f"<li><b>{e(g['article'])}, p. {g['page']}</b> : {e(g['dit'])}<q>{e(g['citation'])}</q></li>"
                     for g in a["regles"]) or "<li class='vide'>aucune règle à citer</li>"
    verif = "".join(f"<li>{e(v)}</li>" for v in a["a_verifier"]) or "<li class='vide'>rien</li>"
    parcelle = f" · parcelle {e(str(f.get('parcelle')))} · {f.get('surface_m2')} m²" if f.get("parcelle") else ""
    cartes.append(f"""<article class="q {x['type']}">
  <header><span class="id">{x['id']}</span><span class="type">{'cas de bord' if x['type'] == 'bord' else e(x['projet'])}</span></header>
  <h2>« {e(x['question'])} »</h2>
  <p class="faits">zone <b>{e(str(f.get('zone')))}</b>{parcelle}</p><div class="tags">{tags}</div>
  <p class="verdict">{e(a['verdict'])}</p>
  <h3>Règles à citer</h3><ul>{regles}</ul>
  <h3>À vérifier en mairie</h3><ul>{verif}</ul>
  <p class="piege"><b>Piège testé :</b> {e(x['piege'])}</p>
</article>""")
page_html = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>Banc d'essai v1 · assistant PLU</title>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;600;800&display=swap" rel="stylesheet">
<style>
:root{{--fond:#F5F0E8;--carte:#fff;--encre:#1D1A17;--gris:#8A837B;--filet:#E4DCD0;--acc:#1971c2;--rouge:#C22E4A;--vert:#2f9e44}}
*{{box-sizing:border-box;margin:0}} body{{background:var(--fond);color:var(--encre);font:400 16px/1.5 Geist,system-ui,sans-serif;padding:32px 40px 60px}}
h1{{font-size:34px;font-weight:800}} .chapo{{color:var(--gris);font-size:18px;margin:6px 0 24px;max-width:1100px}}
.grille{{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:18px}}
.q{{background:var(--carte);border:1px solid var(--filet);border-radius:14px;padding:18px 20px;display:flex;flex-direction:column;gap:8px}}
.q.bord{{border-style:dashed}} header{{display:flex;gap:10px;align-items:center}}
.id{{font-weight:800;background:var(--encre);color:var(--fond);border-radius:6px;padding:2px 8px;font-size:13px}}
.type{{font-size:13px;font-weight:600;color:var(--gris);text-transform:uppercase;letter-spacing:.06em}}
h2{{font-size:18px;font-weight:600;line-height:1.35}} h3{{font-size:12px;text-transform:uppercase;letter-spacing:.08em;color:var(--gris);margin-top:6px}}
.faits{{font-size:14px;color:var(--gris)}} .faits b{{color:var(--encre)}}
.tags{{display:flex;flex-wrap:wrap;gap:6px}} .tag{{font-size:12px;background:#fff3bf;border-radius:20px;padding:2px 10px}}
.verdict{{font-size:18px;font-weight:800;color:var(--acc);border-left:4px solid var(--acc);padding-left:10px}}
ul{{padding-left:18px;font-size:14px}} li{{margin:3px 0}} q{{display:block;color:var(--gris);font-size:13px;quotes:"« " " »"}}
.vide{{color:var(--gris);list-style:none;margin-left:-18px}} .piege{{font-size:14px;color:var(--rouge);margin-top:auto;padding-top:6px;border-top:1px solid var(--filet)}}
</style></head><body>
<h1>Banc d'essai v1 : 20 questions sur Biarritz</h1>
<p class="chapo">Adresses, zones et contraintes réelles (API Adresse, cadastre, Géoportail de l'Urbanisme). Réponses attendues écrites à partir du
règlement du PLU (152 pages) ; chaque citation est retrouvée par le code à sa page exacte. 15 questions normales, 5 cas de bord (pointillés).
À valider : le verdict, les règles et les points à vérifier de chaque carte.</p>
<div class="grille">{''.join(cartes)}</div></body></html>"""
open(os.path.join(B, "questions.html"), "w", encoding="utf-8").write(page_html)
print(len(Q), "questions ;", sum(x["type"] == "bord" for x in Q), "cas de bord ;",
      sum(len(x["attendu"]["regles"]) for x in Q), "citations retrouvées à leur page")
