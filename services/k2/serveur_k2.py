"""K2 Horizon 7B (IFM, Apache 2.0) servi en local, avec la même interface qu'Ollama (/api/chat).

Ollama ne sait pas encore charger son architecture (trop récente) : on passe par transformers + PyTorch CUDA,
compressé en 4 bits (bitsandbytes, nf4) pour tenir dans les 12 Go de la RTX 3060. Le reste du projet
(enquete.py, examens.py, le salon) l'appelle comme n'importe quel modèle Ollama, en le nommant « k2-horizon-7b ».

  POST /api/chat   {model, messages, format (schéma JSON), options {temperature, num_predict}, think}
                   → {"message": {"role": "assistant", "content": …, "thinking": …}, "done": true}

Une requête à la fois (une seule carte graphique). N'écoute que sur 127.0.0.1.
Usage : uv run serveur_k2.py [port]   (HF_HOME doit pointer vers le cache sur D:)
"""
import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

MODELE = "IFM/K2-Horizon-7B"
VERROU = threading.Lock()

print("chargement de K2 Horizon 7B en 4 bits…", flush=True)
t0 = time.time()
TOK = AutoTokenizer.from_pretrained(MODELE, trust_remote_code=True)
LLM = AutoModelForCausalLM.from_pretrained(
    MODELE, trust_remote_code=True, device_map="cuda:0",
    quantization_config=BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                           bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True))
LLM.eval()
print(f"prêt en {time.time() - t0:.0f} s · mémoire de la carte : {torch.cuda.memory_allocated() / 1e9:.1f} Go", flush=True)


FIN_REFLEXION = re.compile(r"</ifm\|think(?:_fast|_faster)?>")


def separer(texte):
    """Sépare la réflexion de la réponse. Le gabarit de K2 ouvre la réflexion dans l'amorce
    (<ifm|think>, <ifm|think_fast> ou <ifm|think_faster> selon l'effort) : le modèle écrit sa réflexion,
    la ferme (</ifm|think…>), puis donne sa réponse."""
    morceaux = FIN_REFLEXION.split(texte, maxsplit=1)
    if len(morceaux) == 2:
        return morceaux[1].strip(), morceaux[0].strip()
    return "", texte.strip()  # réflexion jamais refermée (coupée par la limite de longueur) : tout est réflexion


def premier_json(texte):
    """Le premier objet JSON complet du texte (le modèle l'entoure parfois de phrases ou de ```json)."""
    debut = texte.find("{")
    while debut != -1:
        profondeur, dans_chaine, echappe = 0, False, False
        for i, c in enumerate(texte[debut:], debut):
            if dans_chaine:
                echappe = (c == "\\") and not echappe
                if c == '"' and not echappe:
                    dans_chaine = False
                continue
            if c == '"':
                dans_chaine = True
            elif c == "{":
                profondeur += 1
            elif c == "}":
                profondeur -= 1
                if profondeur == 0:
                    try:
                        json.loads(texte[debut:i + 1])
                        return texte[debut:i + 1]
                    except json.JSONDecodeError:
                        break
        debut = texte.find("{", debut + 1)
    return None


def respecter_schema(contenu, schema):
    """Ollama contraint les choix (enum) pendant la génération ; ici, on ramène après coup chaque valeur à
    l'option autorisée la plus proche (« conséquence » → « cause ou conséquence »)."""
    from difflib import SequenceMatcher
    try:
        obj = json.loads(contenu)
    except (json.JSONDecodeError, TypeError):
        return contenu
    for cle, prop in (schema.get("properties") or {}).items():
        options = prop.get("enum")
        if not options or cle not in obj or obj[cle] in options:
            continue
        v = str(obj[cle]).strip().lower()
        contient = [o for o in options if v and (v in o.lower() or o.lower() in v)]
        obj[cle] = contient[0] if len(contient) == 1 else max(
            contient or options, key=lambda o: SequenceMatcher(None, v, o.lower()).ratio())
    return json.dumps(obj, ensure_ascii=False)


APPEL = re.compile(r"<ifm\|tool_call>(.*?)</ifm\|tool_call>", re.S)
BLOC_APPELS = re.compile(r"<ifm\|tool_calls>.*?(?:</ifm\|tool_calls>|$)", re.S)


def preparer(messages):
    """Messages au format Ollama → format du gabarit de K2 : un message d'agent doit porter sa réflexion
    (champ reasoning_content, même vide) et les arguments d'un appel d'outil doivent être un objet."""
    sortie = []
    for m in messages:
        if m.get("role") not in ("system", "user", "assistant", "tool"):
            continue
        m = dict(m)
        if m["role"] == "assistant":
            m["reasoning_content"] = m.pop("thinking", "") or ""
            appels = []
            for a in m.get("tool_calls") or []:
                f = a.get("function", a)
                args = f.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                appels.append({"type": "function", "function": {"name": f.get("name"), "arguments": args}})
            if appels:
                m["tool_calls"] = appels
            else:
                m.pop("tool_calls", None)
            m["content"] = m.get("content") or ""
        sortie.append(m)
    return sortie


PAIRE = re.compile(r"<ifm\|arg_key>(.*?)</ifm\|arg_key>\s*(?:<ifm\|arg_type>.*?</ifm\|arg_type>\s*)?"
                   r"<ifm\|arg_value>(.*?)</ifm\|arg_value>", re.S)


def lire_valeur(texte):
    """Format XML de K2 : les textes et nombres sont écrits tels quels, tableaux et objets en JSON."""
    t = texte.strip()
    if t[:1] in "[{":
        try:
            return json.loads(t)
        except json.JSONDecodeError:
            pass
    return t


def extraire_appels(contenu):
    """Les appels d'outils écrits par K2 → format Ollama, et le texte qui reste. K2 écrit par défaut en XML
    (son format d'entraînement : nom de l'outil, puis des paires <ifm|arg_key>/<ifm|arg_value>) ; on lit
    aussi le format JSON au cas où."""
    appels = []
    for brut in APPEL.findall(contenu):
        brut = brut.strip()
        if brut.startswith("{"):
            try:
                d = json.loads(brut)
                appels.append({"function": {"name": d.get("name"), "arguments": d.get("arguments") or {}}})
            except json.JSONDecodeError:
                pass
            continue
        nom = brut.split("<ifm|", 1)[0].strip()
        if nom:
            appels.append({"function": {"name": nom, "arguments": {k.strip(): lire_valeur(v) for k, v in PAIRE.findall(brut)}}})
    return appels, BLOC_APPELS.sub("", contenu).strip()


def repondre(demande):
    messages = preparer(demande.get("messages", []))
    outils = demande.get("tools") or None
    schema = demande.get("format")
    if isinstance(schema, dict) and messages:
        # Ollama contraint la sortie par une grammaire ; ici, on le demande explicitement et on vérifie ensuite
        messages[-1]["content"] += ("\n\nRéponds uniquement par un objet JSON valide, sans texte autour, qui respecte "
                                    f"ce schéma : {json.dumps(schema, ensure_ascii=False)}")
    options = demande.get("options") or {}
    # l'effort de réflexion : « low » / « medium » / « high » demandé tel quel, sinon vrai → medium, faux → low
    think = demande.get("think")
    effort = think if think in ("low", "medium", "high") else ("medium" if think else "low")
    # transformers 5 renvoie un dictionnaire (input_ids, attention_mask), pas un simple tableau
    extra = {"tools": outils} if outils else {}  # format d'appel par défaut du gabarit : XML, celui qu'il maîtrise
    entree = TOK.apply_chat_template(messages, add_generation_prompt=True, return_tensors="pt", return_dict=True,
                                     reasoning_effort=effort, **extra).to(LLM.device)
    n = entree["input_ids"].shape[-1]
    temperature = float(options.get("temperature", 0.6))
    with torch.inference_mode():
        sortie = LLM.generate(**entree, max_new_tokens=int(options.get("num_predict", 2000)),
                              do_sample=temperature > 0, temperature=max(temperature, 1e-5), top_p=0.95,
                              pad_token_id=TOK.pad_token_id or TOK.eos_token_id)
    brut = TOK.decode(sortie[0][n:], skip_special_tokens=False)
    nb_jetons = int(sortie.shape[-1] - n)
    # rendre la mémoire gardée en cache : après des heures de longs contextes (banc PLU, 27/09), la carte de 12 Go
    # était pleine et la génération tombait de 0,06 à 1,5 s par jeton
    del sortie, entree
    torch.cuda.empty_cache()
    for special in (TOK.eos_token or "", "<|ifm|im_end|>", "<|im_end|>", "<|endoftext|>", "</s>"):
        if special:
            brut = brut.split(special)[0]
    contenu, reflexion = separer(brut)
    message = {"role": "assistant", "content": contenu, "thinking": reflexion}
    if outils:
        appels, reste = extraire_appels(contenu)
        if appels:
            message["tool_calls"], message["content"] = appels, reste
    if isinstance(schema, dict):  # sans réponse après la réflexion, on tente quand même d'y trouver le JSON
        contenu = premier_json(contenu) or premier_json(reflexion) or contenu
        message["content"] = respecter_schema(contenu, schema)
    return {"model": demande.get("model", "k2-horizon-7b"), "message": message, "done": True,
            "eval_count": nb_jetons, "brut": brut}  # « brut » : la sortie telle quelle, pour déboguer


class K2(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_error(404)
            return
        demande = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        with VERROU:
            t = time.time()
            rep = repondre(demande)
            print(f"réponse en {time.time() - t:.1f} s · {rep['eval_count']} jetons", flush=True)
        corps = json.dumps(rep, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11500
    print(f"K2 sur http://localhost:{port}/api/chat", flush=True)
    ThreadingHTTPServer(("127.0.0.1", port), K2).serve_forever()
