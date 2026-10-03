/**
 * Le processus principal d'Electron : une fenêtre sans cadre (les pastilles de l'interface la ferment, la réduisent,
 * l'agrandissent), le moteur local démarré au lancement et arrêté à la fermeture, et une interface chargée :
 *  - en développement, depuis le serveur de Vite (qui relaie /api vers le moteur) ;
 *  - construite, depuis le moteur lui-même (il sert app/out/renderer à la racine) : même origine pour /api ;
 *  - sans moteur, depuis le fichier local : l'interface passe d'elle-même en démo.
 */
import { join } from 'node:path';
import { BrowserWindow, Menu, app, ipcMain, shell } from 'electron';
import { ADRESSE_MOTEUR, Moteur, moteurRepond, type StatutMoteur } from './moteur';

let fenetre: BrowserWindow | null = null;
const moteur = new Moteur(app.getAppPath(), (statut: StatutMoteur) => fenetre?.webContents.send('moteur:statut', statut));

function icone(): string {
  return app.isPackaged ? join(process.resourcesPath, 'icon.png') : join(app.getAppPath(), 'build', 'icon.png');
}

/** Ce qui sort de l'application (Légifrance, sources) s'ouvre dans le navigateur ; le PDF du règlement reste dedans. */
function externe(url: string): boolean {
  return /^https?:/i.test(url) && !url.startsWith(ADRESSE_MOTEUR) && !url.startsWith(process.env.ELECTRON_RENDERER_URL ?? '\0');
}

async function chargerInterface(f: BrowserWindow, statut: StatutMoteur): Promise<void> {
  const dev = process.env.ELECTRON_RENDERER_URL;
  if (dev) {
    await f.loadURL(dev);
    return;
  }
  if (statut.etat === 'pret' || statut.etat === 'externe') {
    try {
      const r = await fetch(`${ADRESSE_MOTEUR}/`, { signal: AbortSignal.timeout(2000) });
      if (r.ok) {
        await f.loadURL(`${ADRESSE_MOTEUR}/`);
        return;
      }
    } catch {
      // le moteur ne sert pas l'interface construite : le fichier local, en démo
    }
  }
  await f.loadFile(join(__dirname, '../renderer/index.html'));
}

async function creerFenetre(): Promise<void> {
  fenetre = new BrowserWindow({
    width: 1536,
    height: 1024,
    minWidth: 1100,
    minHeight: 700,
    frame: false,
    show: false,
    backgroundColor: '#eaf2fb',
    title: 'Orbi',
    icon: icone(),
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  fenetre.once('ready-to-show', () => fenetre?.show());
  fenetre.on('closed', () => (fenetre = null));
  fenetre.webContents.setWindowOpenHandler(({ url }) => {
    if (externe(url)) {
      void shell.openExternal(url);
      return { action: 'deny' };
    }
    return { action: 'allow' };
  });
  fenetre.webContents.on('will-navigate', (evenement, url) => {
    if (externe(url)) {
      evenement.preventDefault();
      void shell.openExternal(url);
    }
  });
  // le modèle met ~1 min 30 à charger : l'interface s'ouvre dès que le serveur Orbi répond, puis passe en local seule
  const demarrage = moteur.demarrer();
  const limite = Date.now() + 40_000;
  while (Date.now() < limite && !(await moteurRepond())) {
    if (moteur.statut.etat === 'indisponible') break;
    await new Promise((r) => setTimeout(r, 400));
  }
  const pret = await moteurRepond();
  if (fenetre) await chargerInterface(fenetre, pret ? { etat: 'pret', message: null } : moteur.statut);
  void demarrage;
}

ipcMain.on('fenetre:fermer', () => fenetre?.close());
ipcMain.on('fenetre:reduire', () => fenetre?.minimize());
ipcMain.on('fenetre:agrandir', () => {
  if (!fenetre) return;
  if (fenetre.isMaximized()) fenetre.unmaximize();
  else fenetre.maximize();
});
ipcMain.handle('moteur:statut', () => moteur.statut);
ipcMain.handle('moteur:relancer', () => moteur.relancer());

if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.on('second-instance', () => {
    if (!fenetre) return;
    if (fenetre.isMinimized()) fenetre.restore();
    fenetre.focus();
  });
  void app.whenReady().then(() => {
    Menu.setApplicationMenu(null);
    void creerFenetre();
  });
  app.on('window-all-closed', () => app.quit());
  app.on('before-quit', () => moteur.arreter());
}
