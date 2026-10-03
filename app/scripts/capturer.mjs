// Capture l'interface à une taille donnée (1536×1024 par défaut, celle de la maquette) avec Chrome sans fenêtre, en
// pilotant la page par le protocole DevTools : cliquer sur un texte, taper une question, attendre, puis photographier.
// Usage : node scripts/capturer.mjs <url> <sortie.png> [actions...]
//   actions : clic:<texte visible>  taper:<texte>  entree  attendre:<ms>  photo:<fichier.png>
// Exemple : node scripts/capturer.mjs http://localhost:5173/ accueil.png clic:"Règlement PLU" attendre:9000 photo:reponse.png
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const CHROME = process.env.CHROME ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const [url, sortie, ...actions] = process.argv.slice(2);
const [largeur, hauteur] = (process.env.TAILLE ?? '1536x1024').split('x').map(Number);
if (!url || !sortie) {
  console.error('usage : node scripts/capturer.mjs <url> <sortie.png> [actions...]');
  process.exit(2);
}

const port = 9300 + Math.floor(Math.random() * 500);
const profil = join(process.env.TEMP ?? tmpdir(), `orbi-capture-${port}`);
mkdirSync(profil, { recursive: true });
const chrome = spawn(CHROME, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profil}`, '--no-first-run',
  '--hide-scrollbars', `--window-size=${largeur},${hauteur}`, 'about:blank',
], { stdio: 'ignore' });

const pause = (ms) => new Promise((r) => setTimeout(r, ms));
async function cible() {
  for (let i = 0; i < 50; i += 1) {
    try {
      const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      const page = pages.find((p) => p.type === 'page');
      if (page) return page.webSocketDebuggerUrl;
    } catch {
      // Chrome démarre encore
    }
    await pause(200);
  }
  throw new Error('Chrome ne répond pas');
}

const ws = new WebSocket(await cible());
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
let numero = 0;
const attentes = new Map();
ws.addEventListener('message', (m) => {
  const d = JSON.parse(m.data);
  if (d.id && attentes.has(d.id)) {
    attentes.get(d.id)(d);
    attentes.delete(d.id);
  }
});
function cdp(methode, params = {}) {
  numero += 1;
  ws.send(JSON.stringify({ id: numero, method: methode, params }));
  return new Promise((r) => attentes.set(numero, r));
}
async function evaluer(expression) {
  const r = await cdp('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
  if (r.result?.exceptionDetails) throw new Error(r.result.exceptionDetails.text);
  return r.result?.result?.value;
}
async function photo(fichier) {
  const r = await cdp('Page.captureScreenshot', { format: 'png' });
  writeFileSync(fichier, Buffer.from(r.result.data, 'base64'));
  console.log(`photo : ${fichier}`);
}

try {
  await cdp('Page.enable');
  await cdp('Emulation.setDeviceMetricsOverride', { width: largeur, height: hauteur, deviceScaleFactor: 1, mobile: false });
  await cdp('Page.navigate', { url });
  await pause(4000);
  for (const action of actions) {
    const [genre, ...reste] = action.split(':');
    const valeur = reste.join(':');
    if (genre === 'attendre') await pause(Number(valeur));
    else if (genre === 'photo') await photo(valeur);
    else if (genre === 'entree') {
      await cdp('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
      await cdp('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Enter', code: 'Enter', windowsVirtualKeyCode: 13 });
    } else if (genre === 'taper') await cdp('Input.insertText', { text: valeur });
    else if (genre === 'clic') {
      const ok = await evaluer(`(() => {
        const texte = ${JSON.stringify(valeur)};
        const els = [...document.querySelectorAll('button, a, [role="button"], [role="tab"], textarea, input')];
        const el = els.find((e) => (e.innerText || e.getAttribute('aria-label') || e.placeholder || '').includes(texte));
        if (!el) return false;
        el.focus(); el.click(); return true;
      })()`);
      if (!ok) throw new Error(`rien à cliquer avec le texte « ${valeur} »`);
    } else throw new Error(`action inconnue : ${action}`);
  }
  await photo(sortie);
} finally {
  ws.close();
  chrome.kill();
}
