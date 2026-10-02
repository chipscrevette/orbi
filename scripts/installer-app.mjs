// Installe les dépendances de l'application de bureau (app/). Si le dossier des outils existe (D:/tools par défaut,
// ou ORBI_CACHES), les caches de npm, d'Electron et les fichiers temporaires y vont, plutôt que sur le disque système.
// Lancer depuis n'importe quel terminal : node scripts/installer-app.mjs
import { spawnSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const racine = join(dirname(fileURLToPath(import.meta.url)), "..");
const outils = process.env.ORBI_CACHES ?? "D:/tools";
const env = { ...process.env };
if (existsSync(outils)) {
  const caches = {
    npm_config_cache: "npm-cache",
    ELECTRON_CACHE: "electron-cache",
    electron_config_cache: "electron-cache",
    ELECTRON_BUILDER_CACHE: "electron-builder-cache",
    TEMP: "tmp",
    TMP: "tmp",
  };
  for (const [cle, dossier] of Object.entries(caches)) {
    env[cle] = join(outils, dossier);
    mkdirSync(env[cle], { recursive: true });
  }
  console.log(`caches dans ${outils}`);
}
const r = spawnSync("npm", ["install"], { cwd: join(racine, "app"), env, stdio: "inherit", shell: true });
process.exit(r.status ?? 1);
