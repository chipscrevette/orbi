"""La grille : le chemin « puis-je faire X ? » de l'assistant, en quatre temps.

  1. le modèle remplit une grille            analyse.py   une ligne par règle du règlement, aucun verdict
  2. le code contrôle chaque ligne           controle.py  preuve (citation exacte), secteur, nombres comparés par le code
  3. le code décide                          decision.py  une table de décision, testée sans modèle
  4. le code compose la fiche                fiche.py     le texte sort du verdict : aucune contradiction possible

Avant la grille, comme avant : tri, outils, périmètre, démarche, articles à lire, verrou de zone (agent.py). Quand le verrou de
zone fixe le verdict, le modèle n'est même pas appelé pour la conclusion. Les questions d'explication, de délai ou de démarche
gardent la voie historique de l'agent. Usage : uv run orbi-banc --grille"""
import re

from orbi.modele import cerveau
from orbi.agent.historique import Agent, chiffres_inventes
from orbi.modele.analyse import SYSTEME, construire_demande
from orbi.domaine.controle import controler, derives, nombres
from orbi.domaine.decision import decider
from orbi.reglement.donnees import article, cite_bien, norme, page_citation
from orbi.domaine.exclusions import articles_excluant, emprise_exclue
from orbi.domaine.fiche import composer
from orbi.domaine.verrou import ZONES_STRICTES
from orbi.reglement.donnees import chapitre
from orbi.reglement.savoir import savoir_pour
from orbi.domaine.schemas import SCHEMA_ANALYSE

# des mots que le tri lit mal : abri de piscine rangé en « autre » (C09), maison à étage rangée en surélévation (C11)
PISCINE_COUVERTE = re.compile(r"abri (?:de|pour|à) (?:ma |la |une |mon )?piscine|couvr\w+ (?:ma|la|une|mon) piscine|piscine couverte", re.I)
MAISON_NEUVE = re.compile(r"\bmaison (?:à|avec un?) (?:étage|r\+1)|\br\+1\b|construire une maison|maison individuelle|maison neuve", re.I)
PAS_NEUVE = re.compile(r"sur[ée]lev|rehauss|extension|agrandi|existante", re.I)
SUR_LA_LIMITE = re.compile(r"en limite|sur la limite|collée?s? (?:à|au|contre)|accolée?s?|adossée?s?|contre (?:le|son) mur|mitoyen", re.I)
TUTOIEMENT = re.compile(r"\b(?:tu|te|toi|ta|ton|tes)\b", re.I)
# le seul « chiffre calculé » qui décrit le projet (les autres sont des limites de la règle) : voir conclure()
CHIFFRE_PROJET = re.compile(r"^surface de la maison après travaux")
RENVOI_AU_PLAN = "La hauteur maximale est donnée au document graphique."  # UA 10


def hauteurs_ambigues(projet, question, faits, zone, regles):
    """Le plan fixe plusieurs hauteurs sur la parcelle (V26 : les niveaux « 3 » et « 5 ») et l'article 10 renvoie au plan : la hauteur
    permise dépend de l'endroit du bâtiment, que la question ne dit pas. Un fait décisif que les outils connaissent mieux que le
    modèle : la ligne est ajoutée par le code (None si le cas ne se présente pas)."""
    niveaux = sorted(set((faits.get("contraintes") or {}).get("hauteurs_au_plan") or []))
    art = f"{chapitre(zone)} 10"
    if projet != "surélévation" or len(niveaux) < 2 or re.search(r"\d\s*(?:m|cm)\b", question) or not cite_bien(art, RENVOI_AU_PLAN):
        return None
    return {"id": f"R{len(regles) + 1}", "passage": "", "citation": RENVOI_AU_PLAN, "citation_ok": True, "article": art,
            "pages": article(art)["pages"], "page": page_citation(art, RENVOI_AU_PLAN), "nature": "limite", "vaut_ici": "oui",
            "exigence": "hauteur maximale fixée par le plan, qui diffère selon l'endroit de la parcelle", "constat": "", "seuil": None,
            "sens": None, "valeur_projet": None, "statut": "inconnue", "decisif": True,
            "fait_manquant": "à quel niveau du plan se trouve le bâtiment : la parcelle en porte plusieurs (« " + " » et « ".join(niveaux) + " »)"}


def sources_nombres(question, base, chiffres, passages, faits):
    """Les deux ensembles de nombres que le contrôle accepte : ceux du PROJET et ceux de la RÈGLE.
    Projet : la question, la ligne « PROJET » lue par le tri, la surface de la parcelle, la surface après travaux, et ce qu'on en tire
    (une somme, un produit). Règle : les passages et les limites calculées (emprise maximale, hauteur au plan). La démarche (« 1 mois »)
    n'est ni l'un ni l'autre. Le modèle recopiait une limite comme valeur du projet : 12,5 m « respecte » 12,5 m (V26)."""
    ligne_projet = " ".join(l for l in base.splitlines() if l.startswith("PROJET (lu"))
    du_projet = [c for c in chiffres if CHIFFRE_PROJET.match(c)]
    nb_projet = nombres(question + " " + ligne_projet + " " + " ".join(du_projet))
    if (faits.get("parcelle") or {}).get("surface_m2"):
        nb_projet.add(float(faits["parcelle"]["surface_m2"]))
    src_projet = nb_projet | derives(nombres(question + " " + ligne_projet))
    src_regle = nombres(" ".join(p["texte"] for p in passages)) | nombres(" ".join(c for c in chiffres if not CHIFFRE_PROJET.match(c)))
    return src_projet, src_regle


class AgentGrille(Agent):
    def corriger_tri(self, question, tri):
        t = dict(tri)
        if PISCINE_COUVERTE.search(question) and t.get("projet") in ("autre", "aucun", "abri de jardin", "piscine"):
            t["projet"], t["piscine_couverte"] = "piscine", True
        elif MAISON_NEUVE.search(question) and t.get("projet") in ("autre", "aucun", "surélévation", "extension") \
                and not PAS_NEUVE.search(question):
            t["projet"] = "maison neuve"
        if t.get("projet") != tri.get("projet"):
            self.noter("projet fixé par le code", avant=tri.get("projet"), apres=t["projet"])
        return t

    def conclure(self, question, tri, f, dem, chiffres, passages, v, sujet, projet, zone):
        if sujet != "droit" or projet in ("aucun", "autre"):
            return super().conclure(question, tri, f, dem, chiffres, passages, v, sujet, projet, zone)
        abf = bool((f.get("contraintes") or {}).get("site_patrimonial"))
        sources = [x["source"] for x in savoir_pour(question)]

        # 1. le verrou de zone décide seul : le modèle n'a rien à analyser
        if v:
            dec = decider([], verrou=v, abf=abf)
            self.noter("décision", **dec)
            fiche = composer(dec, [], dem, verrou=v)
            regles = [{"article": v["article"], "citation": v["citation"], "page": None, "verifiee": True}]
            return self.fin(self.resultat(dec, fiche, regles, zone, dem, f, [], sources, par="code"))

        # 2. le modèle remplit la grille
        base = self.contexte(question, tri, f, dem, chiffres, [], None).rsplit("ARTICLES DU RÈGLEMENT", 1)[0].rstrip()
        demande = construire_demande(base, passages)
        obj = self.analyser(demande)
        if obj is None:
            dec = {"verdict": "impossible à dire", "raison": "analyse_illisible", "violations": [], "levees": [], "decisives": [],
                   "inconnues": [], "respectees": [], "ecartees": [], "a_verifier": []}
            fiche = {"reponse": "Je n'ai pas pu analyser ce cas de façon fiable : la mairie pourra vous répondre.", "lignes": [],
                     "a_verifier": []}
            return self.fin(self.resultat(dec, fiche, [], zone, dem, f, ["analyse illisible (pas de JSON)"], sources, par="K2 · grille"))

        # 3. le code contrôle chaque ligne, puis décide
        src_projet, src_regle = sources_nombres(question, base, chiffres, passages, f)
        exclus = articles_excluant(projet, passages)
        regles, journal = controler(obj["regles"], passages, zone, src_projet, src_regle, zero_ok=bool(SUR_LA_LIMITE.search(question)),
                                    exclus=exclus, emprise_exclue=emprise_exclue(projet, bool(tri.get("piscine_couverte"))),
                                    travaux_existant=projet == "surélévation")
        ambigue = hauteurs_ambigues(projet, question, f, zone, regles)
        if ambigue:
            regles.append(ambigue)
            journal.append(f"{ambigue['id']} : le plan fixe plusieurs hauteurs sur la parcelle, la question ne dit pas où est le bâtiment — "
                           "fait décisif ajouté par le code")
        ctx = norme(demande).replace(",", ".")
        for r in regles:  # les phrases libres du modèle ne servent que si leurs chiffres viennent du dossier, et sans tutoiement
            for champ in ("exigence", "constat"):
                t = r[champ]
                if t and (chiffres_inventes(t, ctx) or TUTOIEMENT.search(t)):
                    journal.append(f"{r['id']} : {champ} écartée (chiffre sans source ou tutoiement) : « {t} »")
                    r[champ] = ""
        self.noter("contrôle", journal=journal, regles=regles, proposees=len(obj["regles"]))
        dec = decider(regles, verrou=None, abf=abf, zone_stricte=chapitre(zone) in ZONES_STRICTES)
        self.noter("décision", **dec)

        # 4. le code compose la fiche
        fiche = composer(dec, regles, dem)
        cites = [{"article": r["article"], "citation": r["citation"], "page": r["page"], "verifiee": True} for r in regles
                 if r["citation_ok"] and r["vaut_ici"] != "non" and r["nature"] != "information"]
        res = self.resultat(dec, fiche, cites, zone, dem, f, [], sources, par="K2 · grille")
        res["grille"]["journal"] = journal
        res["grille"]["proposees"] = len(obj["regles"])
        return self.fin(res)

    def analyser(self, demande):
        """Un appel au modèle, réflexion courte ; un second essai (autre tirage) si le JSON manque."""
        for i, temperature in enumerate((0.2, 0.5)):
            obj, tr = cerveau.demander(SYSTEME, demande, SCHEMA_ANALYSE, effort="low", max_jetons=2400, temperature=temperature)
            self.noter("analyse" if i == 0 else "nouvelle analyse", regles=(obj or {}).get("regles"), effort="low",
                       **{k: tr[k] for k in ("secondes", "jetons")})
            if isinstance(obj, dict) and isinstance(obj.get("regles"), list):
                return obj
        return None

    def resultat(self, dec, fiche, regles, zone, dem, faits, fautes, sources, par):
        return {"verdict_type": dec["verdict"], "zone": zone, "reponse": fiche["reponse"], "regles": regles,
                "a_verifier": fiche["a_verifier"], "demarche": dem, "faits": faits, "garde_fous": fautes, "sources": sources,
                "par": par, "grille": {"lignes": fiche["lignes"], "decision": dec}}
