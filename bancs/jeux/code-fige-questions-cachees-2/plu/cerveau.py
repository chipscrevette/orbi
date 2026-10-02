"""Le cerveau : K2 Horizon 7B, servi en local (coach-lol/k2/serveur_k2.py, même interface qu'Ollama, port 11500).
Choisi sur mesure : sur le même tour de boucle, K2 répond juste là où granite 8B se trompait de secteur."""
import json
import re
import time

import requests

K2 = "http://127.0.0.1:11500/api/chat"


def premier_json(t):
    t = re.sub(r"^```(?:json)?|```$", "", (t or "").strip(), flags=re.M)
    i = t.find("{")
    while i != -1:
        prof, dans, ech = 0, False, False
        for j, c in enumerate(t[i:], i):
            if dans:
                ech = (c == "\\") and not ech
                if c == '"' and not ech:
                    dans = False
                continue
            if c == '"':
                dans = True
            elif c == "{":
                prof += 1
            elif c == "}":
                prof -= 1
                if prof == 0:
                    try:
                        return json.loads(t[i:j + 1])
                    except json.JSONDecodeError:
                        break
        i = t.find("{", i + 1)
    return None


def demander(systeme, utilisateur, schema, effort="low", max_jetons=1200, temperature=0.2, historique=None):
    """Un appel au modèle, réponse JSON imposée. Renvoie (objet, trace)."""
    messages = [{"role": "system", "content": systeme}] + (historique or []) + [{"role": "user", "content": utilisateur}]
    body = {"model": "k2-horizon-7b", "messages": messages, "stream": False, "format": schema, "think": effort,
            "options": {"temperature": temperature, "num_predict": max_jetons}}
    t = time.time()
    r = requests.post(K2, json=body, timeout=900).json()
    msg = r["message"]
    obj = premier_json(msg.get("content")) or premier_json(msg.get("thinking"))
    trace = {"secondes": round(time.time() - t, 1), "jetons": r.get("eval_count"), "effort": effort,
             "reflexion": msg.get("thinking", ""), "brut": msg.get("content", "")}
    return obj, trace


def pret():
    try:
        requests.post(K2, json={"messages": [{"role": "user", "content": "ok"}], "options": {"num_predict": 1}}, timeout=120)
        return True
    except requests.RequestException:
        return False
