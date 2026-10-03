"""Une question, une réponse en direct. L'agent grille tourne dans un fil à part ; chaque étape qu'il note part aussitôt
vers l'application, puis le lieu (dès que les outils ont trouvé la parcelle), puis la réponse. Une réponse prend une
minute : l'application montre où en est Orbi au lieu de laisser attendre. Un message qui n'est pas une question
d'urbanisme (« coucou », « merci ») reçoit une réponse de conversation : une étape « conversation », puis un « message ».

Le format est celui des Server-Sent Events : « event: <nom> », « data: <json> », une ligne vide."""
import json
import queue
import threading

from orbi.agent.grille import AgentGrille
from orbi.api.conversation import avec_le_lieu_precedent, est_conversation, repondre_conversation, sans_cadratin

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
    dem = res.get("demarche")
    if isinstance(dem, dict):
        dem = {**dem, **{k: sans_cadratin(dem[k]) for k in ("pourquoi", "delai") if isinstance(dem.get(k), str)}}
    return {"verdict": res.get("verdict_type"), "texte": sans_cadratin(res.get("reponse")),
            "regles": [{k: r.get(k) for k in ("article", "citation", "page", "verifiee")} for r in res.get("regles") or []],
            "a_verifier": [sans_cadratin(x) for x in res.get("a_verifier") or []], "demarche": dem, "zone": res.get("zone"),
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


def demande_de_precision(res):
    """Une réponse qui ne fait que demander l'adresse ou la parcelle (rien trouvé, aucune règle) : c'est une question
    d'Orbi, pas un verdict « impossible à dire »."""
    return res.get("verdict_type") == "impossible à dire" and not res.get("regles") and not (res.get("faits") or {}).get("trouvee")


def repondre_en_direct(question, dossier_traces=None, a_la_fin=None, fabrique=AgentEnDirect, battement=BATTEMENT, historique=()):
    """Les événements d'une réponse, au fil de l'eau : des couples (nom, données) ; (None, None) est un battement de cœur.
    a_la_fin est appelé quand l'agent a fini, même si l'application a fermé la connexion avant."""
    file = queue.Queue()

    def envoyer(nom, donnees):
        file.put((nom, donnees))

    def travail():
        try:
            if est_conversation(question):
                envoyer("etape", {"id": "conversation", "t": 0.0})
                texte, secondes = repondre_conversation(question, historique)
                envoyer("message", {"texte": texte, "duree_s": secondes})
                return
            res = fabrique(envoyer, dossier_traces).repondre(avec_le_lieu_precedent(question, historique))
            if demande_de_precision(res):
                envoyer("message", {"texte": sans_cadratin(res.get("reponse")), "duree_s": res.get("secondes")})
                return
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
