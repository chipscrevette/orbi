// Copie dans public/donnees/ les données du projet dont l'interface a besoin (règlement découpé et PDF).
// Les originaux restent dans ../donnees/ ; les copies sont hors dépôt (.gitignore). Lancé avant dev et build.
import { copyFileSync, existsSync, mkdirSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const app = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const source = resolve(app, '..', 'donnees');
const cible = join(app, 'public', 'donnees');
const FICHIERS = ['articles.json', 'reglement-biarritz.pdf'];

mkdirSync(cible, { recursive: true });
let manquants = 0;
for (const nom of FICHIERS) {
  const depuis = join(source, nom);
  const vers = join(cible, nom);
  if (!existsSync(depuis)) {
    console.warn(`[préparer] introuvable : ${depuis}`);
    manquants += 1;
    continue;
  }
  const original = statSync(depuis);
  if (existsSync(vers)) {
    const copie = statSync(vers);
    if (copie.size === original.size && copie.mtimeMs >= original.mtimeMs) continue;
  }
  copyFileSync(depuis, vers);
  console.log(`[préparer] copié : donnees/${nom}`);
}
if (manquants > 0) {
  console.warn('[préparer] sans ces fichiers, la vue Documents et les liens vers les pages du PDF restent vides.');
}
