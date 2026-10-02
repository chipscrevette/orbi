# Les services locaux

Deux processus tournent à côté d'Orbi, sur la machine. Ils parlent en HTTP local (127.0.0.1) et ne sortent jamais sur Internet.

## `k2/` · le modèle de langage (port 11500)
K2 Horizon 7B, quantifié en 4 bits (bitsandbytes NF4), servi par transformers. Même interface qu'Ollama (`POST /api/chat`).
Il faut une carte graphique de 12 Go et les poids dans le cache Hugging Face.

```bash
cd services/k2
HF_HOME=/d/tools/hf-cache HF_HUB_OFFLINE=1 uv run serveur_k2.py 11500
```

## `embeddings/` · le sens des textes (port 11600)
bge-m3 avec transformers.js : `POST /emb {"textes": [...]}` → `{"vecteurs": [[1024 nombres], ...]}`.

```bash
cd services/embeddings
npm install            # une fois ; ou ORBI_TRANSFORMERS=<dossier où @huggingface/transformers est déjà installé>
node emb_serveur.mjs 11600
```
