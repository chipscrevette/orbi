"""La recherche dans le règlement : par les mots (BM25) et par le sens (bge-m3, serveur local), les deux classements
fusionnés (RRF). Mesuré sur le vrai règlement : une longue question noie les mots rares (« véranda » sortait 30e par le
sens seul) ; des questions courtes en recherche hybride le sortent 1er. Chaque résultat garde sa référence d'article."""
import json
import math
import os
import re
import sys
import unicodedata
from collections import Counter

import requests

from orbi.reglement.donnees import DONNEES, morceaux, propre

INDEX = os.path.join(DONNEES, "index-recherche.json")
EMB = "http://127.0.0.1:11600/emb"
VIDES = set(("le la les l de des du d un une et en a au aux pour par sur dans est sont ou qui que ne pas ce ces cette il "
             "elle se sa son ses leur leurs peut peuvent etre plus puis je mon ma mes").split())


# mots de la question qui ne disent rien du sujet (après mots() : sans accent ni pluriel)
OUTILS = set(("quoi quel quelle lequel laquelle lesquel doi doit fait faire faut me moi possible serait sera peut veux veut "
              "voudrai avoir ai avez donc exactement propre lui comment combien pourquoi quand si mais aussi deja tres plu "
              "petit petite grand grande autre tout toute chacun chaque cela ca ici la voisin mairie biarritz rue avenue "
              "allee chemin boulevard place impasse on cm met savoir permi declaration autorisation").split())


def mots(t):
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [re.sub(r"(s|x)$", "", m) for m in re.findall(r"[a-z0-9]+", t) if m not in VIDES and len(m) > 1]


def vecteurs(textes):
    r = requests.post(EMB, json={"textes": textes}, timeout=600)
    r.raise_for_status()
    return r.json()["vecteurs"]


def construire():
    ms = morceaux()
    print(len(ms), "morceaux à vectoriser", flush=True)
    for i in range(0, len(ms), 16):
        for m, v in zip(ms[i:i + 16], vecteurs([x["texte"] for x in ms[i:i + 16]])):
            m["v"] = [round(x, 5) for x in v]
        if i % 160 == 0:
            print(f"  {i}/{len(ms)}", flush=True)
    json.dump(ms, open(INDEX, "w", encoding="utf-8"))
    print("index écrit :", INDEX)


class Recherche:
    def __init__(self):
        self.ms = json.load(open(INDEX, encoding="utf-8"))
        self.tok = [Counter(mots(m["texte"])) for m in self.ms]
        self.moy = sum(sum(c.values()) for c in self.tok) / len(self.tok)
        self.df = Counter(w for c in self.tok for w in c)

    def mots_rares(self, question, adresse="", n=3, df_max=25):
        """Les mots de la question que le règlement emploie, mais rarement (« parpaing », « enduit ») : une recherche
        fixée par le code. Au 3e passage, le tri avait cherché « matériaux de construction » et manqué l'article qui
        interdit les parpaings nus (V18). Les mots de l'adresse, les nombres et les mots-outils sont écartés."""
        hors = set(mots(adresse or "")) | OUTILS
        rares = sorted({w for w in mots(question) if w not in hors and not w.isdigit() and 0 < self.df.get(w, 0) <= df_max},
                       key=lambda w: (self.df[w], w))  # à rareté égale, l'ordre alphabétique : une même question, une même recherche
        return " ".join(rares[:n])

    def _bm25(self, q, idx, k1=1.5, b=0.75):
        n = len(self.ms)
        out = {}
        for i in idx:
            c, L, s = self.tok[i], sum(self.tok[i].values()), 0.0
            for w in set(mots(q)):
                if w in c:
                    idf = math.log(1 + (n - self.df[w] + 0.5) / (self.df[w] + 0.5))
                    s += idf * c[w] * (k1 + 1) / (c[w] + k1 * (1 - b + b * L / self.moy))
            out[i] = s
        return out

    def chercher(self, requetes, chapitres, k=2, refs=None, un_par_article=False, exclure=()):
        """Pour chaque requête courte : les k meilleurs morceaux parmi les chapitres donnés (et, si refs est donné,
        parmi ces articles seulement). Renvoie une liste sans doublon, dans l'ordre des requêtes.
        un_par_article : un seul morceau par article, pour varier les sources (au 2e passage, deux morceaux de DG B-3
        avaient chassé DG A-I) ; exclure : des articles déjà lus en entier."""
        idx = [i for i, m in enumerate(self.ms) if m["chapitre"] in chapitres and (refs is None or m["ref"] in refs)
               and m["ref"] not in exclure]
        if not idx:
            return []
        vq = vecteurs(list(requetes))
        vus, out, refs_prises = set(), [], set()
        for q, v in zip(requetes, vq):
            sens = {i: sum(a * b for a, b in zip(v, self.ms[i]["v"])) for i in idx}
            mots_ = self._bm25(q, idx)
            r_sens = sorted(idx, key=lambda i: -sens[i])
            r_mots = sorted(idx, key=lambda i: -mots_[i])
            rrf = {i: 1 / (61 + r_sens.index(i)) + 1 / (61 + r_mots.index(i)) for i in idx}
            # la fusion noie parfois un mot rare trouvé tel quel (« parpaing » : 1er par les mots, loin par le sens) :
            # le meilleur résultat par les mots est donc toujours gardé, s'il contient vraiment un mot de la requête
            choix = ([r_mots[0]] if mots_[r_mots[0]] > 0 else []) + sorted(idx, key=lambda i: -rrf[i])
            pris = 0
            for i in dict.fromkeys(choix):
                if pris == k:
                    break
                if un_par_article and self.ms[i]["ref"] in refs_prises:  # un article déjà pris, par cette requête ou une autre
                    continue
                refs_prises.add(self.ms[i]["ref"])
                pris += 1
                if i not in vus:
                    vus.add(i)
                    m = self.ms[i]
                    out.append({"ref": m["ref"], "pages": m["pages"], "texte": propre(m["texte"]), "requete": q,
                                "sens": round(sens[i], 3), "mots": round(mots_[i], 2)})
        return out


if __name__ == "__main__" and "--construire" in sys.argv:
    construire()
