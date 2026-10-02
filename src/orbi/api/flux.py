"""Une question, une réponse en direct. L'agent grille tourne dans un fil à part ; chaque étape qu'il note part aussitôt
vers l'application, puis le lieu (dès que les outils ont trouvé la parcelle), puis la réponse. Une réponse prend une
minute : l'application montre où en est Orbi au lieu de laisser attendre.

Le format est celui des Server-Sent Events : « event: <nom> », « data: <json> », une ligne vide."""
import json
import queue
import threading

from orbi.agent.grille import AgentGrille

BATTEMENT = 10  # secondes sans événement avant un battement de cœur (« : … ») : la connexion reste ouverte
_FIN = object()


def sse(evenement, donnees):
    """Un événement au format Server-Sent Events. Le JSON tient sur une ligne : aucun retour à la ligne dans data."""
    return f"event: {evenement}\ndata: {json.dumps(donnees, ensure_ascii=False, default=str)}\n\n"


def lieu_depuis_faits(faits, zone=None):
    """Ce que l'application montre du terrain : adresse, point sur la carte, parcelle, zone, servitudes."""
    f = faits or {}
    a, p, c = f.get("adresse") or {}, f.get("parcelle") or {}, f.get("contraintes") or {}
    z = f.get("zonage")
    return {"adresse": a.get("label"), "commune": a.get("commune"),
            "point": [a["lon"], a["lat"]] if a.get("lon") is not None and a.get("lat") is not None else None,
            "parcelle": p.get("parcelle"), "surface_m2": p.get("surface_m2"),
            "zone": zone or (z.get("zone") if isinstance(z, dict) else z),
            "servitudes": list(c.get("servitudes") or []), "site_patrimonial": bool(c.get("site_patrimonial"))}


def reponse_depuis_resultat(res):
    """La réponse telle que l'application l'affiche : verdict, texte, règles citées, points à vérifier, démarche."""
    return {"verdict": res.get("verdict_type"), "texte": res.get("reponse"),
            "regles": [{k: r.get(k) for k in ("article", "citation", "page", "verifiee")} for r in res.get("regles") or []],
            "a_verifier": list(res.get("a_verifier") or []), "demarche": res.get("demarche"), "zone": res.get("zone"),
            "duree_s": res.get("secondes"), "demo": False}


class AgentEnDirect(AgentGrille):
    """L'agent grille, dont chaque étape notée est aussi envoyée à l'application."""

    def __init__(self, envoyer, dossier_traces=None):
        super().__init__()
        self.envoyer = envoyer
        self.dossier_traces = dossier_traces

    def noter(self, etape, **d):
        super().noter(etape, **d)
        self.envoyer("etape", {"id": etape, "t": self.trace[-1]["t"]})
        if etape == "outils":
            self.envoyer("lieu", lieu_depuis_faits(d.get("faits")))


def repondre_en_direct(question, dossier_traces=None, a_la_fin=None, fabrique=AgentEnDirect, battement=BATTEMENT):
    """Les événements d'une réponse, au fil de l'eau : des couples (nom, données) ; (None, None) est un battement de cœur.
    a_la_fin est appelé quand l'agent a fini, même si l'application a fermé la connexion avant."""
    file = queue.Queue()

    def envoyer(nom, donnees):
        file.put((nom, donnees))

    def travail():
        try:
            res = fabrique(envoyer, dossier_traces).repondre(question)
            if res.get("faits"):
                envoyer("lieu", lieu_depuis_faits(res["faits"], res.get("zone")))
            envoyer("etape", {"id": "fin", "t": res.get("secondes")})
            envoyer("reponse", reponse_depuis_resultat(res))
        except Exception as e:  # une panne (API publique, modèle) ne doit pas laisser l'application attendre
            envoyer("erreur", {"message": f"Orbi n'a pas pu finir sa réponse ({type(e).__name__} : {e})."})
        finally:
            if a_la_fin:
                a_la_fin()
            file.put(_FIN)

    threading.Thread(target=travail, daemon=True, name="orbi-reponse").start()
    while True:
        try:
            item = file.get(timeout=battement)
        except queue.Empty:
            yield None, None
            continue
        if item is _FIN:
            return
        yield item
