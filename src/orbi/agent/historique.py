"""L'assistant PLU : « puis-je construire X à cette adresse ? ».

Le harnais, dans l'ordre :
  1. tri (K2, réflexion courte)        ce que dit la question : adresse, parcelle, projet, surfaces, sujet, 2 recherches
  2. outils (code, API publiques)      adresse ou référence cadastrale → parcelle → zone → contraintes
  3. périmètre (code)                  hors Biarritz, taxes, recours… : réponse sans IA
  4. démarche (code)                   rien, déclaration préalable ou permis, avec les articles du Code de l'urbanisme
  5. articles (code + recherche)       la recette du projet (UD 9, UD 7…), les articles que citent les prescriptions de
                                       la parcelle (« cf. Art. 11 »), puis la recherche hybride
  6. rédaction (K2, réflexion moyenne) réponse structurée ; le code fixe les verdicts permis selon le sujet (une
                                       explication n'a ni « oui » ni « non ») ; sans JSON, nouvel essai en réflexion courte
  7. garde-fous (code)                 citation presque exacte recalée sur le texte du règlement ; zone citée = zone
                                       trouvée ; chaque citation existe mot pour mot dans son article ; chaque chiffre
                                       vient de la question, des faits ou des articles ; une seule correction permise
Chaque étape est tracée (bancs/resultats/traces/*.jsonl).

Usage : uv run python -m orbi.agent.historique "Puis-je construire une véranda de 20 m² au 12 avenue Édouard VII, Biarritz ?"
"""
import json
import os
import re
import sys
import time
from datetime import datetime

from orbi.modele import cerveau
from orbi.domaine.demarche import demarche
from orbi.reglement.donnees import RACINE, article, chapitre, cite_bien, existe, norme, page_citation, propre, raccorder, recaler
from orbi.outils.geo import faits as outils_faits
from orbi.reglement.recherche import Recherche
from orbi.reglement.savoir import SAVOIR, savoir_pour
from orbi.domaine.verrou import verrou
from orbi.chemins import TRACES  # noqa: E402

PROJETS = ["véranda", "extension", "piscine", "abri de jardin", "clôture", "surélévation", "maison neuve", "autre", "aucun"]
SUJETS = ["droit", "démarche", "explication", "délai", "taxe", "recours ou contentieux", "dérogation", "prix", "autre"]
INFORMATION = {"explication", "délai"}  # le verdict est alors « information » : imposé par le code, pas choisi
VERDICTS_PROJET = ["oui", "oui sous conditions", "non", "impossible à dire"]
RECETTES = {"véranda": ["9", "7", "11", "DG B-5"], "extension": ["9", "7", "10", "11", "12", "DG B-5"],
            "piscine": ["7", "9", "DG B-5"], "abri de jardin": ["7", "9", "2", "11", "DG B-5"], "clôture": ["11", "DG B-8"],
            "surélévation": ["10", "7", "11", "12"], "maison neuve": ["1", "2", "9"], "aucun": ["9", "DG B-5"]}
RESTRICTIFS = {"N", "Ncu", "Ner", "UG", "UY", "IIAU", "UP"}  # zones où l'article 1 (interdictions) décide souvent
HORS_SUJET = {"taxe": "la taxe d'aménagement relève des impôts (centre des finances publiques), pas du PLU",
              "recours ou contentieux": "les recours et le contentieux relèvent d'un avocat, du conciliateur ou du tribunal",
              "dérogation": "seules des « adaptations mineures » sont prévues par la loi, et c'est la mairie qui en décide",
              "prix": "le prix d'un bien ne relève pas des règles d'urbanisme"}
# une recherche « permis d'aménager » ne trouve rien d'utile dans un règlement de zone : ces mots-là sont écartés
PROCEDURE = re.compile(r"permis|d[ée]claration|autorisation|\bplu\b|d[ée]marche|formalit|dossier|mairie|architecte|taxe",
                       re.I)
# le périmètre ne se laisse pas au tri : au 2e passage, il a laissé passer une dérogation et un contentieux (V21, V24).
# Ces mots-là fixent le sujet, quoi qu'en dise le modèle (« recours à un architecte » n'est pas un contentieux).
SUJET_FIXE = [("dérogation", re.compile(r"d[ée]rogation|adaptation mineure", re.I)),
              ("recours ou contentieux", re.compile(r"oblige[rz]? à d[ée]molir|ordonner la d[ée]molition|faire d[ée]molir|"
                                                    r"sanction|amende|tribunal|plainte|proc[èe]s|contentieux|"
                                                    r"mise en demeure|\brecours\b(?!\s+(?:à|a)\s)", re.I)),
              ("taxe", re.compile(r"\btax(?:e|é|ation)|imp[ôo]t", re.I)),
              ("prix", re.compile(r"\bprix\b|combien vaut|valeur (?:du|de mon|de la) (?:bien|maison|terrain)", re.I)),
              # une question sur le contenu du règlement, pas sur le droit de construire (V15 : « c'est dans le PLU ? »)
              ("explication", re.compile(r"\bc[’']est (?:bien )?dans le P\.?L\.?U\b|\bque dit le P\.?L\.?U\b|\bc[’']est quoi\b|"
                                         r"\bquelle est la diff[ée]rence\b|\blequel s[’']applique\b", re.I))]
# effort de réflexion de la rédaction, dans l'ordre d'essai : au 2e passage, la réflexion moyenne a tourné 150 s sans
# répondre 5 fois sur 28, et la courte a répondu chaque fois en 30 s environ ; PLU_EFFORT=moyen rétablit l'ancien ordre
EFFORTS = [("medium", 2400), ("low", 1600)] if os.environ.get("PLU_EFFORT") == "moyen" else [("low", 1600), ("medium", 2400)]
# une conclusion négative sur le projet lui-même (« est interdit par », « ne peut pas être posé »), pas sur un détail
NEGATIF = re.compile(r"\b(?:est|sont) interdite?s? (?:par|en zone|dans la zone|à cet endroit|ici)\b|"
                     r"\bne (?:peut|peuvent|pourra|pourront|pourrez|pouvez) pas (?:être )?"
                     r"(?:poser|posée?s?|construire|construite?s?|réaliser|réalisée?s?)\b", re.I)
PHRASES = re.compile(r"(?<=[.!?])\s+(?=[A-ZÉÈÀÂÎÔÛÇ«])")  # « P.L.U. de 2003 » ne coupe pas : minuscule derrière
# les chiffres écrits en lettres échappaient au contrôle : « un délai de trois mois pour le permis » (V14, passage 4)
NOMBRES = {"deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9,
           "dix": 10, "douze": 12, "quinze": 15, "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50, "cent": 100}
EN_LETTRES = re.compile(r"\b(" + "|".join(NOMBRES) + r")\s+(mois|semaines?|jours?|ans|années?|mètres?|étages?|niveaux?)\b", re.I)
DELAI = re.compile(r"\b(\d+)\s*(mois|semaines?|jours?)\b", re.I)  # un délai se vérifie avec son unité : « 3 mois »
CODES = r"U[A-HPY][a-z*]{0,3}|N(?:a|b|d|er|f|F|g|h|hd|hi|r|cu)\*?|IIAU[a-z]?"
# « en secteur UDti » appliqué à une parcelle en UDa (V16, passage 4) ; « sauf en secteur UDti » reste permis
SECTEUR_APPLIQUE = re.compile(r"(\bsauf\s+|qu['’]|\bhors\s+|\bpas\s+|\bnon\s+)?\b(?:en|du|dans le|au)\s+secteurs?\s+("
                              + CODES + r")(?![A-Za-z*])")  # « ne vaut qu'en secteur Nh » reste permis


def chiffres_inventes(texte, ctx):
    """Les nombres de la réponse absents du contexte : en chiffres, en lettres, et les délais avec leur unité."""
    fautes = []
    for x in set(re.findall(r"\d+(?:[.,]\d+)?", texte)):
        if x.replace(",", ".") not in ctx:
            fautes.append(f"le chiffre « {x} » ne vient ni de la question, ni des faits, ni des articles")
    for m in EN_LETTRES.finditer(texte):
        val, unite = NOMBRES[m.group(1).lower()], m.group(2).lower()
        cherche = rf"(?<![\d.]){val}\s*{unite[:4]}" if unite.startswith(("mois", "sem", "jour", "an")) else rf"(?<![\d.]){val}(?!\d)"
        if not re.search(cherche, ctx):
            fautes.append(f"« {m.group(0)} » ne vient ni des faits ni des articles")
    for m in DELAI.finditer(texte):
        if not re.search(rf"(?<![\d.]){m.group(1)}\s*{m.group(2).lower()[:4]}", ctx):
            fautes.append(f"le délai « {m.group(0)} » ne vient pas de la démarche calculée")
    return fautes


def ref_norme(ref):
    """« UD7 », « Article UD 7 », « UD 11 2°) », « UDa 7 » → « UD 7 » ; « DG B5 » → « DG B-5 ». Au 2e passage, « UD7 » a
    fait refuser trois citations exactes (V14) : une question de forme se corrige par le code, pas par le modèle."""
    r = re.sub(r"^(?:l['’]\s*)?(?:article|art\.?)\s*", "", (ref or "").strip(), flags=re.I)
    m = re.match(r"^DG\s*([AB])\s*-?\s*([IVX]+|\d+)\b", r, flags=re.I)
    if m:
        return f"DG {m.group(1).upper()}-{m.group(2).upper()}"
    m = re.match(r"^(Ncu|Ner|IIAU|U[A-HPY]|N)[a-z*]{0,3}\s*(\d{1,2})\b", r)
    if m:
        return f"{m.group(1)} {m.group(2)}"
    # « P.L.U. DE BIARRITZ, article DG B-5 » (5e passage, V10) : la référence au milieu d'un libellé
    m = re.search(r"\bDG\s*([AB])\s*-\s*([IVX]+|\d+)\b", r)
    if m:
        return f"DG {m.group(1)}-{m.group(2)}"
    m = re.search(r"\b(Ncu|Ner|IIAU|U[A-HPY]|N)[a-z*]{0,3}\s+(\d{1,2})\b", r)
    return f"{m.group(1)} {m.group(2)}" if m else (ref or "").strip()


NATIONAL = re.compile(r"\b[RL]\s?\*?\s?\d{3}-\d+|code de l.urbanisme", re.I)  # « Code de l'urbanisme, article R111-22 »

TRI = """Tu lis la question d'un particulier sur l'urbanisme. Tu ne réponds PAS à la question : tu extrais seulement
ces informations, au format JSON. Si une information n'est pas dans la question, mets null.
- adresse : la voie telle qu'elle est écrite, avec son numéro s'il y en a un et la commune si elle est donnée
  (« 3 rue X, Biarritz », ou « allée X, Biarritz » sans numéro) ; null s'il n'y a aucune voie
- parcelle : la référence cadastrale si elle est donnée (section et numéro, par exemple « AB 0123 »), sinon null
- projet : véranda, extension (agrandissement), piscine, abri de jardin, clôture (y compris brise-vue, mur, portail),
  surélévation (rehausser, ajouter un étage), maison neuve, autre (garage, panneaux solaires, fenêtres…), ou aucun
  (pas de travaux : la question porte sur une règle, un mot, un document)
- surface_m2 : la surface totale créée par le projet, en m² ; s'il y a plusieurs éléments, additionne-les ; si la
  question donne une borne (« moins de 12 m² »), prends ce nombre
- surface_existante_m2 : la surface de la maison existante si elle est donnée (nombre ou null)
- piscine_couverte : true seulement si la question parle d'une piscine couverte ou avec un abri
- point_de_vue : voisin si la question porte sur ce qu'a fait ou fera un voisin, sinon propriétaire
- sujet :
  droit : un projet précis est-il permis, possible, conforme ; à quelle distance, quelle hauteur, quelle surface
  démarche : quelle autorisation demander, faut-il déclarer, faut-il un architecte
  explication : ce que dit ou veut dire une règle, ce qu'elle compte, si elle figure dans le PLU, laquelle prime,
    comment vérifier une information, sans demander si un projet précis est permis
  délai : combien de temps pour obtenir une réponse ou une autorisation
  taxe ; recours ou contentieux (sanction, démolition, plainte) ; dérogation ; prix ; autre
- recherches : 2 recherches très courtes (1 à 3 mots), avec les mots qu'emploie un règlement d'urbanisme (par exemple
  « véranda » et « emprise au sol », ou « clôture » et « hauteur ») ; jamais de mots de procédure (permis,
  déclaration, autorisation, PLU)"""

REDACTION = """Tu es l'assistant d'urbanisme de la commune de Biarritz. Tu réponds à un particulier UNIQUEMENT à partir des
faits, de la démarche calculée et des articles du règlement du PLU qu'on te donne. Règles impératives :
1. Tu n'affirmes rien que les articles ne disent pas. Tu ne transposes jamais une règle d'une autre zone.
2. Chaque règle que tu invoques est citée mot pour mot : une phrase exacte, copiée sans rien changer (pas même un
   accord), avec sa référence exacte telle qu'on te la donne (par exemple « UD 9 » ou « DG B-5 »).
3. Tu n'utilises que les chiffres présents dans la question, les faits, les chiffres calculés ou les articles.
4. La démarche (rien, déclaration préalable, permis, architecte) et son délai sont calculés d'après le Code de
   l'urbanisme : c'est la réponse sûre à « quelle autorisation ? », « faut-il un architecte ? », « combien de
   temps ? ». Reprends-les tels quels dans ta réponse, même si les articles du PLU n'en parlent pas.
5. Un projet dispensé de formalité doit quand même respecter le PLU.
6. verdict_type porte sur le PROJET au regard du PLU, pas sur la tournure de la question (« peut-on me refuser
   ceci ? » appelle un verdict sur ceci) :
   - oui : le projet respecte les règles, et les faits donnés suffisent à le vérifier ;
   - oui sous conditions : le projet est possible s'il respecte des règles que tu cites (distance, hauteur, emprise,
     aspect). C'est aussi le cas quand un article dit qu'une chose « pourra être interdite » ou « peut être
     refusée » : c'est un pouvoir laissé à la mairie, pas une interdiction ;
   - non : un article interdit ce projet à cet endroit, dans tous les cas ;
   - impossible à dire : tout dépend d'un fait que tu ne connais pas (une date, une hauteur existante…) ou d'un
     texte ambigu ; dis quel fait vérifier ;
   - information : la question demande une explication ou un délai, pas si un projet est permis.
   On t'indique les valeurs permises pour cette question : choisis parmi elles.
7. Dans une zone où l'article 1 interdit tout sauf des exceptions, un projet n'est admis que s'il entre dans une
   exception de l'article 1 ou de l'article 2 ET que la condition de cette exception vaut pour cette parcelle (son
   secteur, un espace vert protégé figuré au plan, une construction existant à une date…). Une exception réservée à
   un autre secteur, ou aux espaces verts protégés alors que les faits n'en signalent pas, ne s'applique pas.
8. reponse : 4 phrases au plus, en français simple, en vouvoyant, sans markdown. Commence par répondre à la
   question posée.
9. zone : la zone de la parcelle, exactement comme dans les faits (vide s'il n'y a pas d'adresse).
10. Juge le projet tel que la question le décrit : matériaux, distances, hauteurs, surfaces. Si un élément décrit est
   interdit par un article, le verdict est « non », même si un projet différent serait permis. Un projet déjà réalisé,
   le sien ou celui d'un voisin, se juge de la même façon.
11. Une règle que le projet peut encore respecter (distance, hauteur maximale, emprise, aspect) donne « oui sous
   conditions ». Un fait déjà fixé que tu ne connais pas, et dont dépend la réponse (la hauteur actuelle du bâtiment,
   son nombre d'étages, la date de construction de la maison), donne « impossible à dire » : ne le suppose jamais, dis
   quel fait vérifier."""

SCHEMA_TRI = {"type": "object", "properties": {
    "adresse": {"type": ["string", "null"]}, "parcelle": {"type": ["string", "null"]},
    "projet": {"type": "string", "enum": PROJETS},
    "surface_m2": {"type": ["number", "null"]}, "surface_existante_m2": {"type": ["number", "null"]},
    "piscine_couverte": {"type": "boolean"}, "point_de_vue": {"type": "string", "enum": ["propriétaire", "voisin"]},
    "sujet": {"type": "string", "enum": SUJETS}, "recherches": {"type": "array", "items": {"type": "string"}}},
    "required": ["adresse", "parcelle", "projet", "surface_m2", "surface_existante_m2", "piscine_couverte",
                 "point_de_vue", "sujet", "recherches"]}


def schema_reponse(verdicts):
    return {"type": "object", "properties": {
        "verdict_type": {"type": "string", "enum": verdicts}, "zone": {"type": "string"}, "reponse": {"type": "string"},
        "regles": {"type": "array", "items": {"type": "object", "properties": {
            "article": {"type": "string"}, "citation": {"type": "string"}}, "required": ["article", "citation"]}},
        "a_verifier": {"type": "array", "items": {"type": "string"}}},
        "required": ["verdict_type", "zone", "reponse", "regles", "a_verifier"]}


# emprise au sol maximale, par secteur : les chiffres des articles 9 (vérifiés dans le règlement), calculés par le code
EMPRISE = {"UC": 70, "UC*": 70, "UD": 50, "UDi": 50, "UDi*": 50, "UDt": 50, "UDa": 25, "UDa*": 25, "UDb": 25,
           "UDs": 15, "UDti": 55, "UDc": 60}
HAUTEURS = {"R": "4 m à l'égout, 8 m au faîtage", "1": "6 m à l'égout, 10 m au faîtage (R+1+comble)",
            "2": "8,50 m à l'égout, 14 m au faîtage (R+2+comble)", "3": "12,50 m à l'égout, 18 m au faîtage (R+3+comble)",
            "4": "15 m à l'égout, 21 m au faîtage (R+4+comble)", "5": "18 m à l'égout, 24 m au faîtage (R+5+comble)",
            "6": "21 m à l'égout, 27 m au faîtage"}


def nb(x):
    return f"{x:g}".replace(".", ",")


class Agent:
    def __init__(self):
        self.recherche = Recherche()
        self.trace = []

    def noter(self, etape, **d):
        self.trace.append({"etape": etape, "t": round(time.time() - self.t0, 1), **d})

    # ------------------------------------------------------------------ réponses faites par le code seul
    def sans_ia(self, verdict, reponse, dem=None, faits=None, verifier=None):
        return {"verdict_type": verdict, "reponse": reponse, "demarche": dem, "zone": ((faits or {}).get("zonage") or {}).get("zone"),
                "regles": [], "a_verifier": verifier or [], "faits": faits, "garde_fous": [], "par": "code"}

    # ------------------------------------------------------------------ la boucle
    def repondre(self, question):
        self.t0, self.trace = time.time(), []
        tri, tr = cerveau.demander(TRI, question, SCHEMA_TRI, effort="low", max_jetons=700)
        tri = tri or {}
        self.noter("tri", resultat=tri, **{k: tr[k] for k in ("secondes", "jetons")})
        tri = self.corriger_tri(question, tri)

        projet = tri.get("projet") if tri.get("projet") in PROJETS else "aucun"
        sujet = tri.get("sujet") if tri.get("sujet") in SUJETS else "droit"
        sujet = "droit" if sujet == "autre" else sujet
        for fixe, motif in SUJET_FIXE:
            m = motif.search(question)
            if m:
                if fixe != sujet:
                    self.noter("sujet fixé par le code", avant=sujet, apres=fixe, mot=m.group(0))
                sujet = fixe
                break
        requetes = [q for q in (tri.get("recherches") or []) if q and not PROCEDURE.search(q)][:2]
        requetes = requetes or ([projet] if projet not in ("aucun", "autre") else [question])
        rares = self.recherche.mots_rares(question, tri.get("adresse") or "")  # une recherche que le modèle ne choisit pas
        if rares and rares not in requetes:
            requetes = requetes + [rares]

        f = outils_faits(tri.get("adresse"), question, tri.get("parcelle")) if (tri.get("adresse") or tri.get("parcelle")) else None
        if f is not None:
            self.noter("outils", faits=f)
        if f and f.get("trouvee") and not f["dans_le_perimetre"]:
            return self.fin(self.sans_ia("hors périmètre", f"Cette adresse est à {f['adresse']['commune']} : je ne couvre pour "
                                         "l'instant que le PLU de Biarritz. Le service urbanisme de la commune pourra vous répondre.", faits=f))
        if not f or not f.get("trouvee") or not chapitre((f.get("zonage") or {}).get("zone")):
            if sujet in HORS_SUJET:
                return self.fin(self.sans_ia("hors périmètre", f"Je ne peux pas répondre sur ce point : {HORS_SUJET[sujet]}."))
            if sujet == "explication":  # une explication n'a pas besoin d'adresse : les dispositions générales suffisent
                return self.sans_adresse(question, requetes)
            if not f:
                texte = "Pour vous répondre, il me faut l'adresse exacte du terrain (numéro, rue, commune)."
            elif not f.get("trouvee"):
                texte = "Je ne trouve pas cette adresse : pouvez-vous la préciser (numéro, rue, ou référence cadastrale) ?"
            else:
                texte = "Je ne trouve pas la zone du PLU de ce terrain : pouvez-vous donner sa référence cadastrale ?"
            return self.fin(self.sans_ia("impossible à dire", texte, faits=f))

        zone = f["zonage"]["zone"]
        chap = chapitre(zone)
        c = f.get("contraintes") or {}
        protege = bool(c.get("site_patrimonial"))
        surface = tri.get("surface_m2")
        existant = tri.get("surface_existante_m2")
        total = existant + surface if (existant and surface) else None
        if projet == "autre":
            dem = {"type": "sans objet", "pourquoi": "démarche non calculée pour ce type de travaux", "textes": [], "delai": None}
        else:
            dem = demarche(projet, surface, total, zone_urbaine=f["zonage"].get("type_zone") == "U", protege=protege,
                           couverte=bool(tri.get("piscine_couverte")))
        self.noter("démarche", demarche=dem)

        if sujet in HORS_SUJET:
            texte = f"Je ne peux pas répondre sur ce point : {HORS_SUJET[sujet]}."
            if dem["type"] != "sans objet":
                texte += f" Pour la démarche, en revanche : {dem['type']} ({dem['pourquoi']})."
            return self.fin(self.sans_ia("hors périmètre", texte, dem=dem, faits=f))

        # ---------------------------------------------------------- les articles à lire
        refs = [r if r.startswith("DG") else f"{chap} {r}" for r in RECETTES.get(projet, RECETTES["aucun"])]
        if chap in RESTRICTIFS:
            refs = [f"{chap} 1", f"{chap} 2"] + refs
        # une prescription de la parcelle renvoie à son article : « Règles architecturales particulières (cf. Art. 11) »
        motifs = []
        for x in c.get("prescriptions") or []:
            for n in re.findall(r"cf\.?\s*art\.?\s*(\d+)", x, flags=re.I):
                refs.append(f"{chap} {n}")
                motifs.append(re.sub(r"\(.*?\)", "", x).strip())
        # en zone restrictive, les articles 1 et 2 sont la liste des exceptions : ils se lisent en entier. Au 2e passage,
        # la recherche dans N 2 avait gardé les passages qui disent « abri de jardin » et manqué N 2 b), qui dit « annexes »
        entiers = {f"{chap} 1", f"{chap} 2"} if chap in RESTRICTIFS else set()
        passages = self.lire(refs, requetes + motifs, [chap, "DG"], entiers=entiers)

        # ---------------------------------------------------------- chiffres calculés par le code
        chiffres = []
        s_par = (f.get("parcelle") or {}).get("surface_m2")
        if zone in EMPRISE and s_par:
            chiffres.append(f"emprise au sol maximale en {zone} : {EMPRISE[zone]} % de {nb(s_par)} m² = {nb(round(EMPRISE[zone] * s_par / 100, 1))} m²")
            if zone in ("UDa", "UDa*") and s_par < 1000:
                chiffres.append(f"si la parcelle existait avant la révision du PLU de 2003 : 40 % de {nb(s_par)} m² = "
                                f"{nb(round(0.4 * s_par, 1))} m² ; plafond de 250 m²")
        if chap in ("UA", "UB") and zone != "UAc":
            chiffres.append(f"en {zone}, aucune emprise au sol maximale n'est fixée par l'article {chap} 9")
        for h in c.get("hauteurs_au_plan") or []:
            chiffres.append(f"hauteur fixée au plan pour cette parcelle : niveau « {h} » = {HAUTEURS.get(h, '?')}")
        if total and projet in ("extension", "véranda", "surélévation"):  # pour une piscine, V01 y lisait l'emprise du projet
            chiffres.append(f"surface de la maison après travaux : {nb(existant)} + {nb(surface)} = {nb(total)} m²")
        if zone in EMPRISE and projet in ("abri de jardin", "extension", "véranda", "maison neuve") and not existant:
            # V07, deux passages de suite : « 18 m² restent sous 85,5 m² », la maison déjà construite oubliée
            chiffres.append("emprise des constructions déjà présentes sur la parcelle : non donnée dans la question ; "
                            "elle compte aussi dans la limite (DG B-5), à ajouter à celle du projet")

        # ---------------------------------------------------------- le verrou de zone (verrou.py)
        v = verrou(projet, zone)
        if v:
            self.noter("verrou de zone", **v)
        return self.conclure(question, tri, f, dem, chiffres, passages, v, sujet, projet, zone)

    def corriger_tri(self, question, tri):
        """Un point d'entrée : une variante de l'agent peut corriger ce que le tri a lu. L'agent historique ne change rien."""
        return tri

    def conclure(self, question, tri, f, dem, chiffres, passages, v, sujet, projet, zone):
        """Le dernier maillon de l'agent historique : le modèle rédige la réponse et le verdict, les garde-fous la contrôlent.
        Les variantes (grille.py) remplacent cette étape et gardent tout ce qui précède."""
        contexte = self.contexte(question, tri, f, dem, chiffres, passages, v)
        verdicts = ["information"] if sujet in INFORMATION else (v["verdicts"] if v else VERDICTS_PROJET)
        rep, fautes = self.rediger(contexte, passages, zone, verdicts)
        if v and rep and not any(g.get("article") == v["article"] for g in rep.get("regles") or []):
            rep.setdefault("regles", []).append({"article": v["article"], "citation": v["citation"]})
            self.noter("citation du verrou ajoutée", article=v["article"])
        return self.fin(self.finaliser(rep, zone, fautes, dem=dem, faits=f, question=question))

    def sans_adresse(self, question, requetes):
        """« Que veut dire… ? » sans adresse : on répond avec les dispositions générales, valables dans toutes les zones."""
        passages = self.lire([], requetes, ["DG"], k=3)
        lignes = [f"Question : {question}", "", "FAITS : aucune adresse donnée. Réponds de façon générale, avec les "
                  "dispositions générales du règlement (valables dans toutes les zones) ; ne donne aucune règle propre "
                  "à une zone.", ""] + self.lignes_savoir(question)
        lignes += ["ARTICLES DU RÈGLEMENT (référence, pages, texte) :"]
        lignes += [f"[{p['ref']}] (p. {p['pages'][0]}-{p['pages'][1]}) {p['texte']}" for p in passages]
        rep, fautes = self.rediger("\n".join(lignes), passages, None, ["information"])
        return self.fin(self.finaliser(rep, None, fautes, question=question))

    def lignes_savoir(self, question):
        """Le savoir métier utile à la question (savoir.py), avec sa source : le modèle s'en sert tel quel."""
        s = savoir_pour(question)
        if s:
            self.noter("savoir métier", cles=[x["cle"] for x in s])
            return (["SAVOIR MÉTIER (textes vérifiés à la source, à reprendre tels quels, sans les compléter) :"]
                    + [f"- {x['texte']}" for x in s] + [""])
        return []

    # ------------------------------------------------------------------ les étapes
    def lire(self, refs, requetes, chapitres, k=1, entiers=()):
        """Les articles de la recette (entiers s'ils sont courts ou s'ils sont dans « entiers », sinon leurs 2 passages les
        plus proches des recherches), puis les meilleurs passages d'autres articles, un par article, par la recherche
        hybride dans les chapitres donnés."""
        passages = []
        for ref in dict.fromkeys(refs):
            if not existe(ref):
                continue
            a = article(ref)
            texte = propre(a["texte"])
            if len(texte) <= 2500 or ref in entiers:
                passages.append({"ref": ref, "pages": a["pages"], "texte": texte})
            else:  # un long article : le meilleur passage pour chaque recherche. Au 2e passage, 2 par recherche (4 morceaux
                z, _ = ref.split(maxsplit=1)  # de l'article 11) noyaient un abri de jardin ; au 3e, un plafond à 2 ne
                # gardait que ceux de la 1re recherche et jetait le passage des parpaings, trouvé par la 2e (V18)
                for p in self.recherche.chercher(requetes, [z], k=1, refs=[ref]):
                    passages.append({"ref": ref, "pages": p["pages"], "texte": p["texte"]})
        lus = {p["ref"] for p in passages}
        for p in self.recherche.chercher(requetes, chapitres, k=k, un_par_article=True, exclure=lus):
            passages.append({"ref": p["ref"], "pages": p["pages"], "texte": p["texte"]})
        self.noter("articles", refs=[p["ref"] for p in passages], requetes=requetes)
        return passages

    def rediger(self, contexte, passages, zone, verdicts):
        schema = schema_reponse(verdicts)
        demande = contexte + f"\n\nverdict_type permis pour cette question : {', '.join(verdicts)}."
        rep, effort = None, EFFORTS[0][0]
        for i, (effort, jetons) in enumerate(EFFORTS):  # si la réflexion mange tous les jetons sans répondre : l'autre effort
            rep, tr = cerveau.demander(REDACTION, demande, schema, effort=effort, max_jetons=jetons)
            self.noter("rédaction" if i == 0 else f"nouvel essai, réflexion {'moyenne' if effort == 'medium' else 'courte'}",
                       reponse=rep, effort=effort, **{k: tr[k] for k in ("secondes", "jetons")})
            if rep:
                break
        self.reparer_citations(rep)
        fautes = self.garde_fous(rep, zone, passages, contexte)
        if fautes and rep:  # une seule correction : on dit au modèle exactement ce qui ne va pas
            self.noter("garde-fous", fautes=fautes)
            hist = [{"role": "user", "content": demande}, {"role": "assistant", "content": json.dumps(rep, ensure_ascii=False)}]
            correction = ("Vérification automatique de ta réponse : " + " ; ".join(fautes) + ". Corrige-la en respectant "
                          "les règles, et renvoie la réponse complète au même format.")
            rep2, tr2 = cerveau.demander(REDACTION, correction, schema, effort=effort, max_jetons=2400, historique=hist)
            self.noter("correction", reponse=rep2, effort=effort, **{k: tr2[k] for k in ("secondes", "jetons")})
            if rep2:
                rep = rep2
                self.reparer_citations(rep)
            fautes = self.garde_fous(rep, zone, passages, contexte)
            self.noter("garde-fous après correction", fautes=fautes)
        if rep and len(verdicts) == 1:
            rep["verdict_type"] = verdicts[0]
        return rep, fautes

    def reparer_citations(self, rep):
        """La forme des références ramenée à celle du règlement (« UD7 » → « UD 7 »), puis une citation presque exacte
        remplacée par le texte exact du règlement (voir donnees.recaler). Un article du Code de l'urbanisme cité parmi
        les règles du PLU (5e passage, V10) passe dans les sources nationales s'il vient du savoir métier, mot pour mot."""
        if not rep:
            return
        garde, nationales = [], rep.setdefault("sources_citees", [])
        for g in rep.get("regles") or []:
            if NATIONAL.search(g.get("article") or "") and not re.search(r"\bDG\b|\b(?:U[A-HPY]|Ncu|Ner|IIAU|N)\s+\d", g.get("article") or ""):
                cit = norme(g.get("citation") or "").strip(" .")
                if cit and any(cit in norme(s["texte"]) for s in SAVOIR):
                    nationales.append(g)
                    self.noter("texte national déplacé vers les sources", article=g.get("article"))
                else:
                    self.noter("texte national non vérifiable retiré", article=g.get("article"), citation=g.get("citation"))
                continue
            garde.append(g)
        rep["regles"] = garde
        for g in rep.get("regles") or []:
            brute = g.get("article") or ""
            ref = ref_norme(brute)
            if ref != brute:
                self.noter("référence normalisée", avant=brute, apres=ref)
                g["article"] = ref
            cit = g.get("citation") or ""
            if existe(ref) and not cite_bien(ref, cit):
                exact = recaler(ref, cit)
                if exact and cite_bien(ref, exact):
                    self.noter("citation recalée", article=ref, avant=cit, apres=exact)
                    g["citation"] = exact
                    continue
                cousue = raccorder(ref, cit)  # des passages exacts mis bout à bout : on remet les « … »
                if cousue and cite_bien(ref, cousue):
                    self.noter("citation raccordée", article=ref, avant=cit, apres=cousue)
                    g["citation"] = cousue

    def finaliser(self, rep, zone, fautes, dem=None, faits=None, question=""):
        rep = rep or {"verdict_type": "impossible à dire", "zone": zone or "", "reponse": "Je n'ai pas pu formuler de réponse fiable.",
                      "regles": [], "a_verifier": []}
        for g in rep.get("regles") or []:  # la page de chaque règle citée, prise dans le règlement (pas dans le modèle)
            g["page"] = page_citation(g.get("article", ""), g.get("citation", ""))
            g["verifiee"] = cite_bien(g.get("article", ""), g.get("citation", ""))
        sources = [x["source"] for x in savoir_pour(question)]  # les textes nationaux utilisés, à afficher sous la réponse
        return {**rep, "demarche": dem, "faits": faits, "garde_fous": fautes, "sources": sources, "par": "K2"}

    def contexte(self, question, tri, f, dem, chiffres, passages, v=None):
        c = f.get("contraintes") or {}
        projet = [{"autre": "autres travaux", "aucun": "aucun projet de travaux"}.get(tri.get("projet"), tri.get("projet") or "?")]
        if tri.get("surface_m2"):
            projet.append(f"surface créée : {nb(tri['surface_m2'])} m²")
        if tri.get("surface_existante_m2"):
            projet.append(f"maison existante : {nb(tri['surface_existante_m2'])} m²")
        if tri.get("piscine_couverte"):
            projet.append("piscine couverte")
        if tri.get("point_de_vue") == "voisin":
            projet.append("c'est le projet d'un voisin")
        lignes = [f"Question : {question}", "", "PROJET (lu dans la question) : " + ", ".join(projet), "",
                  "FAITS (outils publics) :",
                  f"- adresse : {f['adresse']['label']}",
                  f"- parcelle : {(f.get('parcelle') or {}).get('parcelle')}, {(f.get('parcelle') or {}).get('surface_m2')} m²",
                  f"- zone du PLU : {f['zonage']['zone']} (chapitre {chapitre(f['zonage']['zone'])} du règlement)",
                  f"- prescriptions sur la parcelle : {', '.join(c.get('prescriptions') or []) or 'aucune'}"
                  + (" (« Règles architecturales particulières (cf. Art. 11) » : la construction est repérée au plan comme "
                     "construction d'intérêt architectural, le « liseré à denticules » du règlement)"
                     if any("Règles architecturales particulières" in x for x in c.get("prescriptions") or []) else ""),
                  f"- servitudes : {', '.join(c.get('servitudes') or []) or 'aucune'}"
                  + (" (site patrimonial remarquable : avis de l'Architecte des Bâtiments de France)" if c.get("site_patrimonial") else ""),
                  "", f"DÉMARCHE (calculée, à reprendre telle quelle) : {dem['type']} — {dem['pourquoi']}"
                  + (f" ; délai d'instruction (le temps que met la mairie à répondre, pas un délai pour déposer) : "
                     f"{dem['delai']}" if dem.get("delai") else ""), ""]
        if v:
            lignes += [f"VERROU DE ZONE (écrit dans le code, vérifié dans le règlement) : {v['pourquoi']}. Article {v['article']} : "
                       f"« {v['citation']} ». Verdicts possibles : {', '.join(v['verdicts'])}.", ""]
        lignes += self.lignes_savoir(question)
        if chiffres:
            lignes += ["CHIFFRES CALCULÉS :"] + [f"- {x}" for x in chiffres] + [""]
        lignes += ["ARTICLES DU RÈGLEMENT (référence, pages, texte) :"]
        for p in passages:
            lignes.append(f"[{p['ref']}] (p. {p['pages'][0]}-{p['pages'][1]}) {p['texte']}")
        return "\n".join(lignes)

    def garde_fous(self, rep, zone, passages, contexte):
        if not rep:
            return ["réponse illisible (pas de JSON)"]
        fautes = []
        if zone and norme(rep.get("zone") or "") != norme(zone):
            fautes.append(f"la zone doit être « {zone} » (c'est celle que donne le Géoportail), pas « {rep.get('zone')} »")
        donnees = {p["ref"] for p in passages}
        citations = " ".join(norme(g.get("citation") or "") for g in rep.get("regles") or [])
        for g in rep.get("regles") or []:
            ref = (g.get("article") or "").strip()
            if ref not in donnees:
                fautes.append(f"l'article « {ref} » ne fait pas partie des articles fournis ({', '.join(sorted(donnees))})")
            elif not cite_bien(ref, g.get("citation") or ""):
                fautes.append(f"la citation attribuée à {ref} n'existe pas mot pour mot dans cet article : copie une phrase exacte")
        # la consigne dit « en vouvoyant » ; au 2e passage, une réponse a tutoyé (V01) sans qu'aucune note ne le voie
        tu = re.search(r"\b(?:tu|te|toi|ta|ton|tes)\b", rep.get("reponse") or "", flags=re.I)
        if tu:
            fautes.append(f"la réponse tutoie la personne (« {tu.group(0)} ») : vouvoie-la")
        # le verdict et le texte disent la même chose : au 3e passage, « Oui, vous pouvez poser un abri » puis « l'abri de
        # jardin est interdit par l'article N 1 » (V28). Rejoué sur 52 réponses : ce seul cas, aucune fausse alerte.
        texte, verdict = (rep.get("reponse") or "").strip(), rep.get("verdict_type")
        neg = NEGATIF.search(texte)
        if verdict in ("oui", "oui sous conditions") and neg:
            fautes.append(f"le verdict dit « {verdict} » mais la réponse dit « {neg.group(0)} » : mets-les d'accord")
        if verdict == "non" and re.match(r"oui\b", texte, flags=re.I):
            fautes.append("le verdict dit « non » mais la réponse commence par « Oui » : mets-les d'accord")
        n = len(PHRASES.split(texte)) if texte else 0
        if n > 4:
            fautes.append(f"la réponse fait {n} phrases : 4 au plus, en commençant par répondre à la question")
        fautes += chiffres_inventes(rep.get("reponse") or "", norme(contexte).replace(",", "."))
        # les vrais codes de secteur seulement (« Non » ou « Nous » ne sont pas des secteurs N…)
        autres = set(re.findall(rf"\b(?:{CODES})\b", rep.get("reponse") or "")) - {zone, chapitre(zone)}
        for s in autres:
            if norme(s) not in citations:
                fautes.append(f"la réponse parle du secteur « {s} » alors que la parcelle est en {zone} : ne transpose pas "
                              "une règle d'un autre secteur (sauf en la citant mot pour mot)")
        if zone:  # même cité, un autre secteur ne s'applique pas à la parcelle
            for m in SECTEUR_APPLIQUE.finditer(rep.get("reponse") or ""):
                if not m.group(1) and m.group(2) not in (zone, chapitre(zone)):
                    fautes.append(f"la réponse applique une règle « {m.group(0)} » alors que la parcelle est en {zone} : "
                                  "retire-la ou dis qu'elle ne s'applique pas ici")
        return fautes

    def fin(self, res):
        res["secondes"] = round(time.time() - self.t0, 1)
        if os.environ.get("PLU_SANS_TRACE"):  # le rejeu (orbi.evaluation.rejeu) ne doit pas remplir les traces
            return res
        dossier = getattr(self, "dossier_traces", None) or TRACES  # l'application range ses traces à part
        os.makedirs(dossier, exist_ok=True)
        chemin = os.path.join(dossier, f"{datetime.now():%Y%m%d-%H%M%S-%f}.jsonl")
        with open(chemin, "w", encoding="utf-8") as fo:
            for e in self.trace:
                fo.write(json.dumps(e, ensure_ascii=False, default=str) + "\n")
            fo.write(json.dumps({"etape": "fin", "resultat": res}, ensure_ascii=False, default=str) + "\n")
        res["trace"] = chemin
        return res


def afficher(res):
    print(f"\n{res['verdict_type'].upper()}  ·  {res.get('zone') or ''}  ·  {res['secondes']} s  ·  par {res['par']}")
    print(res["reponse"])
    d = res.get("demarche") or {}
    if d and d.get("type") != "sans objet":
        print(f"\nDémarche : {d['type']} ({d['pourquoi']})" + (f" · délai : {d['delai']}" if d.get("delai") else ""))
    for g in res.get("regles") or []:
        print(f"  {'✓' if g.get('verifiee') else '✗'} {g['article']} p. {g.get('page') or '?'} : « {g['citation']} »")
    for v in res.get("a_verifier") or []:
        print(f"  · à vérifier : {v}")
    if res.get("garde_fous"):
        print("  ! garde-fous non satisfaits :", " ; ".join(res["garde_fous"]))


if __name__ == "__main__":
    afficher(Agent().repondre(" ".join(sys.argv[1:])))
