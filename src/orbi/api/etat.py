"""L'état de la machine et des services, pour la colonne de droite de l'application : le modèle local répond-il, combien
la carte graphique et la mémoire en utilisent, combien de temps prend une réponse, ce que contient la base du PLU, et le
score du dernier banc caché. Chaque sonde est courte et ne lève jamais : une sonde muette rend None."""
import functools
import json
import os
import shutil
import socket
import subprocess
import time

from orbi.chemins import DONNEES, RESULTATS

K2 = ("127.0.0.1", 11500)  # le serveur du modèle (services/k2)
EMBEDDINGS = ("127.0.0.1", 11600)  # le serveur d'embeddings (services/embeddings)
CADASTRE = ("apicarto.ign.fr", 443)  # l'API Carto de l'IGN : parcelles, zones, servitudes
BANC_DE_REFERENCE = "banc-cache2-grille-20261002-1520-reprise.json"  # le dernier banc caché passé par l'agent grille
GO = 1024 ** 3
_memo_cadastre = {"t": 0.0, "ok": None}


def port_ouvert(adresse, delai=0.5):
    """Un service écoute-t-il à cette adresse (hôte, port) ? Une connexion TCP suffit : on ne réveille pas le modèle."""
    try:
        with socket.create_connection(adresse, timeout=delai):
            return True
    except OSError:
        return False


def lire_nvidia_smi(sortie):
    """« NVIDIA GeForce RTX 3060, 6213, 12288 » → {"nom": "RTX 3060", "utilise_go": 6.1, "total_go": 12.0}."""
    lignes = [x for x in (sortie or "").strip().splitlines() if x.strip()]
    if not lignes:
        return None
    try:
        nom, utilise, total = (x.strip() for x in lignes[0].split(","))
        return {"nom": nom.replace("NVIDIA ", "").replace("GeForce ", ""), "utilise_go": round(float(utilise) / 1024, 1),
                "total_go": round(float(total) / 1024, 1)}
    except ValueError:
        return None


def gpu():
    """La carte graphique NVIDIA, ou None sans nvidia-smi."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        sortie = subprocess.run([exe, "--query-gpu=name,memory.used,memory.total", "--format=csv,noheader,nounits"],
                                capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    return lire_nvidia_smi(sortie)


def memoire():
    """La mémoire vive utilisée et totale, en Go."""
    try:
        import psutil
        m = psutil.virtual_memory()
    except (ImportError, OSError):
        return None
    return {"utilise_go": round((m.total - m.available) / GO, 1), "total_go": round(m.total / GO, 1)}


def cadastre_joignable(maintenant=None, validite=300):
    """L'API Carto répond-elle ? Vérifié au plus une fois toutes les 5 minutes : l'état est demandé toutes les 10 s."""
    maintenant = time.time() if maintenant is None else maintenant
    if _memo_cadastre["ok"] is None or maintenant - _memo_cadastre["t"] > validite:
        _memo_cadastre.update(t=maintenant, ok=port_ouvert(CADASTRE, delai=2))
    return _memo_cadastre["ok"]


@functools.lru_cache(maxsize=1)
def base_plu():
    """Ce que contient la base du PLU : les articles du règlement, les passages de l'index de recherche, les zones de la carte."""
    def compter(fichier, combien):
        try:
            with open(os.path.join(DONNEES, fichier), encoding="utf-8") as f:
                return combien(json.load(f))
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None
    return {"commune": "Biarritz",
            "articles": compter("articles.json", lambda d: sum(len(articles) for articles in d.values())),  # chapitre → articles
            "passages": compter("index-recherche.json", len),
            "zones": compter("zones-biarritz.geojson", lambda d: len(d["features"]))}


@functools.lru_cache(maxsize=1)
def dernier_banc(fichier=BANC_DE_REFERENCE):
    """Le score du dernier banc caché (questions jamais vues, scellées avant le passage) et le temps moyen d'une réponse."""
    try:
        with open(os.path.join(RESULTATS, fichier), encoding="utf-8") as f:
            r = json.load(f)["resume"]
        juste, total = r["scores"]["verdict"]
        return {"juste": juste, "total": total, "date": r["date"][:10], "temps_moyen_s": r.get("temps_moyen_s")}
    except (OSError, ValueError, KeyError, TypeError):
        return None


def services_manquants():
    """Le message à montrer si un service local manque pour répondre, sinon None."""
    if not port_ouvert(K2):
        return ("Le modèle local (K2 Horizon 7B) ne répond pas sur le port 11500. Lancez-le : "
                "cd services/k2 && uv run serveur_k2.py 11500")
    if not port_ouvert(EMBEDDINGS):
        return ("Le serveur de recherche (embeddings) ne répond pas sur le port 11600. Lancez-le : "
                "node services/embeddings/emb_serveur.mjs 11600")
    return None


def etat(durees=()):
    """L'état complet. durees : les temps des dernières réponses de cette session (sinon, le temps moyen du banc)."""
    k2, emb = port_ouvert(K2), port_ouvert(EMBEDDINGS)
    banc = dernier_banc()
    temps = round(sum(durees) / len(durees), 1) if durees else (banc or {}).get("temps_moyen_s")
    return {
        "mode": "local" if k2 and emb else "demo",
        "modele": {"nom": "K2 Horizon 7B", "en_ligne": k2},
        "services": {"k2": k2, "embeddings": emb},
        "gpu": gpu(),
        "memoire": memoire(),
        "temps_reponse_s": temps,
        "base": {"plu": {"connectee": base_plu()["passages"] is not None, **base_plu()},
                 "cadastre": {"connectee": cadastre_joignable(), "source": "API Carto IGN"}},
        "banc": {k: banc[k] for k in ("juste", "total", "date")} if banc else None,
    }
