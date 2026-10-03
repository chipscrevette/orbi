/**
 * Le moteur local : le serveur Python d'Orbi (uv run orbi-serveur, http://127.0.0.1:4770). Au lancement de l'application,
 * s'il répond déjà, on s'en sert (« externe ») ; sinon on le démarre et on attend qu'il réponde (« pret »), au plus 30 s.
 * À la fermeture, on n'arrête que ce qu'on a démarré.
 */
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

export type EtatMoteur = 'inconnu' | 'demarrage' | 'pret' | 'externe' | 'indisponible';

export interface StatutMoteur {
  etat: EtatMoteur;
  message: string | null;
}

export const ADRESSE_MOTEUR = 'http://127.0.0.1:4770';
const DELAI_DEMARRAGE_MS = 30_000;
const PAS_SONDE_MS = 500;

/** Le moteur répond-il ? Une requête courte à /api/etat. */
export async function moteurRepond(adresse = ADRESSE_MOTEUR, delaiMs = 1500): Promise<boolean> {
  try {
    const r = await fetch(`${adresse}/api/etat`, { signal: AbortSignal.timeout(delaiMs) });
    return r.ok;
  } catch {
    return false;
  }
}

/** Le dossier du projet orbi (celui de pyproject.toml) : ORBI_RACINE, sinon le parent du dossier de l'application. */
export function racineProjet(dossierApplication: string, env: NodeJS.ProcessEnv = process.env): string | null {
  const candidats = [env.ORBI_RACINE, join(dossierApplication, '..')].filter((c): c is string => Boolean(c));
  return candidats.find((c) => existsSync(join(c, 'pyproject.toml'))) ?? null;
}

export class Moteur {
  private processus: ChildProcess | null = null;
  private statutCourant: StatutMoteur = { etat: 'inconnu', message: null };

  constructor(
    private readonly dossierApplication: string,
    private readonly signaler: (statut: StatutMoteur) => void,
  ) {}

  get statut(): StatutMoteur {
    return this.statutCourant;
  }

  private changer(etat: EtatMoteur, message: string | null = null): StatutMoteur {
    this.statutCourant = { etat, message };
    this.signaler(this.statutCourant);
    return this.statutCourant;
  }

  /** Utiliser le moteur s'il tourne déjà, sinon le démarrer et attendre qu'il réponde. */
  async demarrer(): Promise<StatutMoteur> {
    if (await moteurRepond()) {
      return this.changer(this.processus ? 'pret' : 'externe');
    }
    const racine = racineProjet(this.dossierApplication);
    if (!racine) {
      return this.changer('indisponible', 'projet orbi introuvable (variable ORBI_RACINE)');
    }
    this.changer('demarrage', 'uv run orbi-serveur');
    try {
      this.processus = spawn('uv', ['run', 'orbi-serveur'], {
        cwd: racine,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8' },
        windowsHide: true,
        stdio: 'ignore',
      });
    } catch (erreur) {
      return this.changer('indisponible', `lancement impossible : ${String(erreur)}`);
    }
    let sorti: string | null = null;
    this.processus.once('error', (e) => (sorti = `uv introuvable ou lancement impossible : ${e.message}`));
    this.processus.once('exit', (code) => {
      sorti = sorti ?? `le serveur s'est arrêté (code ${code})`;
      this.processus = null;
    });
    const limite = Date.now() + DELAI_DEMARRAGE_MS;
    while (Date.now() < limite && sorti === null) {
      if (await moteurRepond()) return this.changer('pret');
      await new Promise((r) => setTimeout(r, PAS_SONDE_MS));
    }
    this.arreter();
    return this.changer('indisponible', sorti ?? `aucune réponse après ${DELAI_DEMARRAGE_MS / 1000} s`);
  }

  async relancer(): Promise<StatutMoteur> {
    this.arreter();
    return this.demarrer();
  }

  /** Arrêter le serveur démarré par l'application (et ses enfants : uv lance Python). */
  arreter(): void {
    const p = this.processus;
    this.processus = null;
    if (!p?.pid) return;
    if (process.platform === 'win32') {
      spawnSync('taskkill', ['/pid', String(p.pid), '/T', '/F'], { windowsHide: true });
    } else {
      p.kill('SIGTERM');
    }
  }
}
