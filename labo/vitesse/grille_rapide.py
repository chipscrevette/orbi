"""Prototype de l'étape « vitesse » : la grille compacte. Le modèle ne recopie plus les citations ni ne rédige le constat ; il désigne
une phrase du règlement par son numéro (A2) et résume la règle en dix mots. Le code retrouve la phrase exacte : une citation exacte par
construction, et une sortie du modèle deux à trois fois plus courte.

La mesure se fait sur le banc de mise au point, pas sur un banc caché :
  uv run python labo/vitesse/grille_rapide.py [--ids V01,V03]      (même notation qu'orbi-banc, résultats dans bancs/resultats/banc-rapide-*.json)
Ce module vit hors du paquet orbi tant qu'il n'est pas validé : le code scellé du banc caché ne bouge pas."""
import json
import os
import re
import sys
import time
from datetime import datetime

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)
from orbi.modele import cerveau  # noqa: E402
from orbi.agent import grille as g
from orbi.domaine.controle import lettre  # noqa: E402
from orbi.domaine.schemas import NATURES, SENS, STATUTS, VAUT  # noqa: E402
from essai_clauses import clauses  # noqa: E402
from orbi.chemins import JEUX, RESULTATS  # noqa: E402

SYSTEME_RAPIDE = """Tu es l'instructeur d'un service d'urbanisme. Tu ne réponds PAS à la question et tu ne donnes AUCUN verdict (ni oui, ni
non) : tu remplis une grille d'analyse, une ligne par règle du règlement qui touche ce projet (4 lignes au plus, les plus
déterminantes). Un contrôle automatique lira ta grille et en tirera la conclusion.

Les phrases du règlement sont numérotées (A1, A2, B1…). Pour chaque ligne :
- ref : le numéro de la phrase qui porte la règle (A2). Une seule phrase.
- nature : interdit (le texte interdit quelque chose), limite (un maximum ou un minimum chiffré : distance, hauteur, emprise,
  surface), condition (une exigence non chiffrée : aspect, matériaux, avis), exception (le texte admet quelque chose malgré
  une interdiction ou une règle générale), information (définition, renvoi).
- vaut_ici : « oui » seulement si la phrase vise la zone de la parcelle (secteur compris) ET ce type de projet. « non » si elle
  vise un autre secteur (Nh, UDti…), une autre situation (aéroport, linéaire commercial, espace vert protégé que les faits ne
  signalent pas) ou un autre type de projet. « incertain » si tu ne peux pas le dire.
- dit : ce que la règle exige, en 10 mots au plus, avec ses chiffres.
- seuil, sens, valeur_projet : seulement pour une règle de nature « limite », si elle fixe un chiffre ET que la question donne le
  chiffre correspondant du PROJET LUI-MÊME (jamais celui d'un bâtiment existant que le projet ne modifie pas). sens = au_plus (un
  maximum), au_moins (un minimum), limite_ou_au_moins (« sur la limite ou à au moins 3 mètres »). Donne les deux nombres dans
  l'unité de la règle (mètres, m²) et tels qu'ils sont écrits : 50 cm s'écrit 0,5 ; le code compare lui-même, ne conclus pas. Si le
  projet est sur la limite, valeur_projet = 0. valeur_projet vient de la QUESTION (ou de la somme de deux de ses chiffres : 90 m²
  existants + 8 m² créés = 98 m²), jamais des chiffres calculés ni du règlement : ce sont les limites de la règle, pas le projet.
  Si la question ne donne pas le chiffre du projet, n'écris pas ces trois champs et mets statut = inconnue.
- statut : respectee, violee ou inconnue. « violee » seulement si la question montre que le projet ne respecte pas la règle ;
  « inconnue » si un fait manque.
- manque : pour une ligne « inconnue » seulement. « projet » si le fait qui manque est une caractéristique du projet que la
  personne choisira (la distance à la limite, la hauteur, les matériaux, l'aspect, un avis). « existant » si c'est un fait sur un
  bâtiment ou un terrain déjà là, que la question ne donne pas (la date de la maison, la hauteur actuelle du bâtiment, la surface
  déjà construite). Pour une surélévation ou un rehaussement, tout ce qui concerne le bâtiment actuel est « existant ».
- fait_manquant : pour une ligne « inconnue » seulement, le fait qui manque, en 10 mots au plus (jamais un constat).

Règles :
- Un texte qui dit qu'une chose « pourra être refusée » ou « peut être interdite » laisse l'appréciation à la mairie : c'est une
  condition, jamais une interdiction.
- Une exception (une liste de ce qui est admis dans une zone où presque tout est interdit, une implantation différente
  acceptée sous condition) est « respectee » si le projet décrit remplit sa condition, « violee » si la question montre qu'il
  ne la remplit pas (une piscine couverte ne remplit pas « piscine non couverte »), « inconnue » seulement si un fait manque.
- Une interdiction générale « sauf… » est « violee » si le projet n'entre dans aucune des exceptions du passage.
- Si la question laisse un doute sur la façon dont une règle s'applique au projet (un élément en retrait, un bâtiment déjà
  construit, une saillie), mets vaut_ici = incertain, même si un chiffre semble dépassé.
- Si le texte exclut expressément ce type de projet de la règle (« les piscines sont exclues de cette règle »), vaut_ici = non
  pour cette règle.
- L'absence de règle n'est pas une autorisation : n'invente pas de ligne.
- Tu n'utilises que les chiffres de la question, des faits, des chiffres calculés ou du règlement."""

SCHEMA_RAPIDE = {
    "type": "object",
    "properties": {"regles": {"type": "array", "items": {"type": "object", "properties": {
        "ref": {"type": "string"},
        "nature": {"type": "string", "enum": list(NATURES)},
        "vaut_ici": {"type": "string", "enum": list(VAUT)},
        "dit": {"type": "string"},
        "seuil": {"type": ["number", "null"]},
        "sens": {"type": "string", "enum": list(SENS) + ["aucun"]},
        "valeur_projet": {"type": ["number", "null"]},
        "statut": {"type": "string", "enum": list(STATUTS)},
        "manque": {"type": "string", "enum": ["projet", "existant", "aucun"]},
        "fait_manquant": {"type": ["string", "null"]}},
        "required": ["ref", "nature", "vaut_ici", "dit", "statut"]}}},
    "required": ["regles"]}

TABLE = {}  # « A2 » → (lettre du passage, phrase exacte) : remplie en construisant la demande, lue en convertissant la réponse


def construire_demande_rapide(base, passages):
    """Comme analyse.construire_demande, mais chaque passage est découpé en phrases numérotées (A1, A2…)."""
    TABLE.clear()
    lignes = []
    for i, p in enumerate(passages, 1):
        lt = lettre(i)
        lignes.append(f"[{lt}] {p['ref']} (p. {p['pages'][0]}-{p['pages'][1]})")
        for k, c in enumerate(clauses(p["texte"]), 1):
            TABLE[f"{lt}{k}"] = (lt, c)
            lignes.append(f"{lt}{k}. {c}")
    return base + "\n\nRÈGLEMENT, PHRASES NUMÉROTÉES (le numéro de la phrase, son article, ses pages) :\n" + "\n".join(lignes)


def vers_lignes(obj):
    """La grille compacte → les lignes que orbi.domaine.controle sait lire : la phrase exacte retrouvée par son numéro."""
    sortie = []
    for r in (obj or {}).get("regles") or []:
        m = re.fullmatch(r"\s*([A-Za-z])\s*[-.]?\s*(\d+)\s*\.?\s*", str(r.get("ref") or ""))
        cle = f"{m.group(1).upper()}{int(m.group(2))}" if m else None
        if cle not in TABLE:
            continue  # un numéro qui n'existe pas : la ligne ne peut pas être vérifiée, elle n'entre pas dans la grille
        lt, phrase = TABLE[cle]
        ligne = {k: v for k, v in r.items() if k not in ("ref", "dit")}
        ligne.update(passage=lt, citation=phrase, exigence=r.get("dit") or "", constat="")
        sortie.append(ligne)
    return {"regles": sortie}


class AgentGrilleRapide(g.AgentGrille):
    """La grille d'orbi.agent.grille, avec la sortie compacte du modèle."""

    def analyser(self, demande):
        for i, temperature in enumerate((0.2, 0.5)):
            obj, tr = cerveau.demander(SYSTEME_RAPIDE, demande, SCHEMA_RAPIDE, effort="low", max_jetons=2400, temperature=temperature)
            lignes = vers_lignes(obj) if isinstance(obj, dict) else None
            self.noter("analyse" if i == 0 else "nouvelle analyse", regles=(lignes or {}).get("regles"), brut=(obj or {}).get("regles"),
                       effort="low", **{k: tr[k] for k in ("secondes", "jetons")})
            if lignes is not None and isinstance(obj.get("regles"), list):
                return lignes
        return None


g.construire_demande = construire_demande_rapide  # conclure() construit la demande par ce nom de module


def main():
    from orbi.evaluation import notation as banc
    ids = set(sys.argv[sys.argv.index("--ids") + 1].split(",")) if "--ids" in sys.argv else None
    Q = [x for x in json.load(open(os.path.join(JEUX, "questions-v2.json"), encoding="utf-8")) if not ids or x["id"] in ids]
    agent, lignes, t0 = AgentGrilleRapide(), [], time.time()
    for x in Q:
        res = agent.repondre(x["question"])
        n = banc.noter(x, res)
        lignes.append({"id": x["id"], "question": x["question"], "attendu": x["attendu"], "obtenu": {
            k: res.get(k) for k in ("verdict_type", "reponse", "regles", "a_verifier", "garde_fous", "secondes", "par", "trace")},
            "demarche_obtenue": (res.get("demarche") or {}).get("type"), "note": n})
        ok = " ".join(f"{k}:{'✓' if v else '✗'}" for k, v in n.items() if v is not None)
        print(f"{x['id']}  {res.get('secondes')} s  attendu « {x['attendu']['verdict_type']} » obtenu « {res.get('verdict_type')} »  {ok}", flush=True)
    temps = [l["obtenu"]["secondes"] for l in lignes if l["obtenu"]["secondes"]]
    resume = {"date": datetime.now().isoformat(timespec="seconds"), "questions": len(lignes), "pipeline": "grille",
              "variante": "rapide (phrases numérotées, sans constat)", "banc": "questions-v2.json",
              "scores": {k: (sum(1 for l in lignes if l["note"][k]), sum(1 for l in lignes if l["note"][k] is not None))
                         for k in ("verdict", "sens", "grave", "demarche", "articles", "citations", "garde_fous")},
              "temps_moyen_s": round(sum(temps) / len(temps), 1) if temps else None, "temps_max_s": max(temps) if temps else None,
              "duree_totale_s": round(time.time() - t0)}
    print(json.dumps(resume, ensure_ascii=False, indent=1))
    chemin = os.path.join(RESULTATS, f"banc-rapide-{datetime.now():%Y%m%d-%H%M}.json")
    json.dump({"resume": resume, "lignes": lignes}, open(chemin, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    print("résultats :", chemin)


if __name__ == "__main__":
    main()
