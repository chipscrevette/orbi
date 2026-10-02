// Petit serveur local d'embeddings (bge-m3, déjà en cache pour transformers.js) : le modèle est chargé UNE fois,
// puis chaque question se vectorise en quelques centaines de millisecondes. N'écoute que sur 127.0.0.1.
//   POST /emb  {"textes": ["…", "…"]}  →  {"vecteurs": [[1024 nombres], …]}
import { createRequire } from 'module';
import { pathToFileURL } from 'url';
import http from 'http';
// transformers.js et le modèle en cache : ici, dans services/embeddings (npm install), ou dans un dossier déjà équipé
const req = createRequire(process.env.ORBI_TRANSFORMERS || new URL('./', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
const mod = await import(pathToFileURL(req.resolve('@huggingface/transformers')).href);
const pipeline = mod.pipeline || mod.default.pipeline;
const PORT = +(process.argv[2] || 11600);
const t0 = Date.now();
const f = await pipeline('feature-extraction', 'Xenova/bge-m3', { dtype: 'fp32' });
console.log(`bge-m3 prêt en ${((Date.now() - t0) / 1000).toFixed(0)} s, sur http://127.0.0.1:${PORT}/emb`);
http.createServer((rq, rs) => {
  if (rq.method !== 'POST' || rq.url !== '/emb') { rs.writeHead(404); return rs.end(); }
  let corps = '';
  rq.on('data', c => corps += c);
  rq.on('end', async () => {
    try {
      const { textes } = JSON.parse(corps);
      const v = (await f(textes, { pooling: 'cls', normalize: true })).tolist();
      rs.writeHead(200, { 'Content-Type': 'application/json' });
      rs.end(JSON.stringify({ vecteurs: v }));
    } catch (e) { rs.writeHead(500); rs.end(String(e)); }
  });
}).listen(PORT, '127.0.0.1');
