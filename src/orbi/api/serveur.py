"""Le serveur local de l'application de bureau. Il n'écoute que sur la machine (127.0.0.1).
  GET  /api/etat       l'état de la machine et des services (colonne de droite de l'application)
  POST /api/question   une question → les étapes, le lieu puis la réponse, en direct (Server-Sent Events)
  /                    l'interface construite (app/out/renderer), si elle existe
Lancer : uv run orbi-serveur   (http://127.0.0.1:4770 ; documentation de l'API : /api/docs)"""
import argparse
import os
import threading
from collections import deque

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from orbi.api import etat as sondes
from orbi.api.flux import repondre_en_direct, sse
from orbi.chemins import RACINE

PORT = 4770
ATTENTE = 10  # secondes entre deux battements de cœur quand une question attend la fin de la précédente
INTERFACE = os.path.join(RACINE, "app", "out", "renderer")
CONVERSATIONS = os.path.join(RACINE, "conversations")  # les traces des questions posées dans l'application (hors dépôt)


class Echange(BaseModel):
    question: str = Field(max_length=2000)
    reponse: str | None = Field(default=None, max_length=4000)
    adresse: str | None = Field(default=None, max_length=300)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000, description="La question, en français, avec l'adresse ou la parcelle")
    historique: list[Echange] = Field(default_factory=list, max_length=12,
                                      description="Les échanges précédents de la conversation (le plus ancien d'abord)")


def creer_application(interface=INTERFACE, dossier_traces=CONVERSATIONS, repondre=repondre_en_direct):
    app = FastAPI(title="Orbi", version="0.2.0", docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)
    app.state.durees = deque(maxlen=20)  # les temps des dernières réponses : la jauge « temps de réponse »
    app.state.occupe = threading.Lock()  # une seule question à la fois : le modèle occupe toute la carte graphique

    @app.get("/api/etat")
    def etat():
        return sondes.etat(list(app.state.durees))

    @app.post("/api/question")
    def question(q: Question):
        def flux():
            if not app.state.occupe.acquire(blocking=False):
                # une autre réponse est en cours (le modèle occupe toute la carte graphique) : on attend son tour
                yield sse("etape", {"id": "attente", "t": 0.0})
                while not app.state.occupe.acquire(timeout=ATTENTE):
                    yield ": battement\n\n"
            libere = False
            try:
                manque = sondes.services_manquants()
                if manque:
                    yield sse("erreur", {"message": manque})
                    return
                libere = True  # l'agent libère le verrou quand il a fini, même si l'application ferme la connexion avant
                historique = [e.model_dump() for e in q.historique]
                for nom, donnees in repondre(q.question.strip(), dossier_traces=dossier_traces, a_la_fin=app.state.occupe.release,
                                             historique=historique):
                    if nom is None:
                        yield ": battement\n\n"
                        continue
                    if nom == "reponse" and donnees.get("duree_s"):
                        app.state.durees.append(donnees["duree_s"])
                    yield sse(nom, donnees)
            finally:
                if not libere:
                    app.state.occupe.release()

        return StreamingResponse(flux(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    if os.path.isdir(interface):
        app.mount("/", StaticFiles(directory=interface, html=True), name="interface")
    return app


def main(argv=None):
    import uvicorn
    p = argparse.ArgumentParser(description="Le serveur local d'Orbi")
    p.add_argument("--port", type=int, default=PORT)
    a = p.parse_args(argv)
    from orbi.outils import geo
    geo.CACHE = os.path.join(CONVERSATIONS, "cache-api")  # les appels de l'application ne se mêlent pas au cache des bancs
    os.makedirs(geo.CACHE, exist_ok=True)
    print(f"Orbi écoute sur http://127.0.0.1:{a.port}  (API : /api/docs)")
    uvicorn.run(creer_application(), host="127.0.0.1", port=a.port, log_level="warning")


if __name__ == "__main__":
    main()
