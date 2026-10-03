// Rend le film image par image : Chrome sans fenêtre charge film.html, et pour chaque image appelle rendre(t)
// puis photographie la page. Usage : node rendre.mjs images            → images/f0000.png … (600 images, 30 i/s)
//                                    node rendre.mjs essais 1.2 5.6 …  → essais/t1.2.png … (contrôle des scènes)
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const [mode, ...temps] = process.argv.slice(2);
const ICI = resolve('.');
const DUREE = 18, IPS = 30;
const port = 9400 + Math.floor(Math.random() * 400);
const profil = join(process.env.TEMP ?? ICI, `orbi-film-${port}`);
const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profil}`, '--no-first-run',
  '--hide-scrollbars', '--allow-file-access-from-files', '--force-device-scale-factor=1', '--window-size=1920,1080', 'about:blank'],
  { stdio: 'ignore' });
const pause = (ms) => new Promise((r) => setTimeout(r, ms));
let url;
for (let i = 0; i < 50 && !url; i += 1) {
  try { url = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((x) => x.type === 'page')?.webSocketDebuggerUrl; }
  catch { await pause(200); }
}
const ws = new WebSocket(url);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let n = 0; const attente = new Map();
ws.addEventListener('message', (m) => { const d = JSON.parse(m.data); if (attente.has(d.id)) { attente.get(d.id)(d); attente.delete(d.id); } });
const cdp = (method, params = {}) => { n += 1; ws.send(JSON.stringify({ id: n, method, params })); return new Promise((r) => attente.set(n, r)); };
const evaluer = async (expression) => (await cdp('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true })).result;

try {
  await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { width: 1920, height: 1080, deviceScaleFactor: 1, mobile: false });
  await cdp('Page.navigate', { url: pathToFileURL(join(ICI, 'film.html')).href });
  await pause(1500);
  const pret = await evaluer('window.pret');
  if (!pret?.result?.value) throw new Error('film.html ne s\'est pas préparé : ' + JSON.stringify(pret));
  const liste = mode === 'images' ? Array.from({ length: DUREE * IPS }, (_, i) => i / IPS) : temps.map(Number);
  const dossier = mode === 'images' ? 'images' : 'essais';
  mkdirSync(dossier, { recursive: true });
  for (const [i, t] of liste.entries()) {
    await evaluer(`rendre(${t})`);
    const r = await cdp('Page.captureScreenshot', { format: 'png' });
    const nom = mode === 'images' ? `f${String(i).padStart(4, '0')}.png` : `t${t}.png`;
    writeFileSync(join(dossier, nom), Buffer.from(r.result.data, 'base64'));
    if (mode === 'images' && i % 60 === 0) console.log(`${i}/${liste.length}`);
  }
  console.log(`${liste.length} image(s) dans ${dossier}/`);
} finally { ws.close(); chrome.kill(); }
