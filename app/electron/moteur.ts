/**
 * Le moteur local : trois services que l'application démarre à son ouverture et arrête à sa fermeture.
 *  - api        : le serveur Python d'Orbi (uv run orbi-serveur, port 4770), prêt en quelques secondes ;
 *  - embeddings : le serveur de recherche par le sens (port 11600) ;
 *  - k2         : le modèle K2 Horizon 7B sur la carte graphique (port 11500), ~1 min 30 de chargement.
 * Un service qui tourne déjà au lancement est utilisé tel quel et n'est pas arrêté à la fermeture.
 * Où et comment lancer chaque service : services.local.json à la racine du projet (propre à la machine, hors dépôt),
 * sinon les dossiers services/ du projet.
 */
import { spawn, spawnSync, type ChildProcess } from 'node:child_process';
import { createWriteStream, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { connect } from 'node:net';
import { join } from 'node:path';

export type EtatMoteur = 'inconnu' | 'demarrage' | 'pret' | 'externe' | 'indisponible';

export interface StatutMoteur {
  etat: EtatMoteur;
  message: string | null;
}

export interface Service {
  nom: 'api' | 'embeddings' | 'k2';
  libelle: string;
  cwd: string;
  commande: string[];
  env?: Record<string, string>;
  port: number;
  delaiS: number;
}

export const ADRESSE_MOTEUR = 'http://127.0.0.1:4770';

/** Un service écoute-t-il sur ce port ? (une connexion TCP, sans réveiller le modèle) */
export function portOuvert(port: number, delaiMs = 600): Promise<boolean> {
  return new Promise((resolve) => {
    const s = connect({ host: '127.0.0.1', port });
    const fin = (ok: boolean) => {
      s.destroy();
      resolve(ok);
    };
    s.setTimeout(delaiMs, () => fin(false));
    s.once('connect', () => fin(true));
    s.once('error', () => fin(false));
  });
}

/** Le moteur répond-il ? Une requête courte à /api/etat. */
export async function moteurRepond(adresse = ADRESSE_MOTEUR, delaiMs = 1500): Promise<boolean> {
  try {
    return (await fetch(`${adresse}/api/etat`, { signal: AbortSignal.timeout(delaiMs) })).ok;
  } catch {
    return false;
  }
}

/** Le dossier du projet orbi (celui de pyproject.toml) : ORBI_RACINE, sinon le parent du dossier de l'application. */
export function racineProjet(dossierApplication: string, env: NodeJS.ProcessEnv = process.env): string | null {
  const candidats = [env.ORBI_RACINE, join(dossierApplication, '..')].filter((c): c is string => Boolean(c));
  return candidats.find((c) => existsSync(join(c, 'pyproject.toml'))) ?? null;
}

/** Les trois services : ceux de services.local.json s'il existe, complétés par ceux du projet. */
export function chargerServices(racine: string): Service[] {
  const defauts: Service[] = [
    { nom: 'api', libelle: 'serveur Orbi', cwd: racine, commande: ['uv', 'run', 'orbi-serveur'], port: 4770, delaiS: 40 },
    { nom: 'embeddings', libelle: 'recherche', cwd: join(racine, 'services', 'embeddings'), commande: ['node', 'emb_serveur.mjs', '11600'], port: 11600, delaiS: 90 },
    { nom: 'k2', libelle: 'modèle K2', cwd: join(racine, 'services', 'k2'), commande: ['uv', 'run', 'serveur_k2.py', '11500'], port: 11500, delaiS: 300 },
  ];
  const fichier = join(racine, 'services.local.json');
  if (!existsSync(fichier)) return defauts;
  try {
    const local = JSON.parse(readFileSync(fichier, 'utf-8')) as Record<string, Partial<Service>>;
    return defauts.map((d) => ({ ...d, ...(local[d.nom] ?? {}), nom: d.nom }));
  } catch {
    return defauts;
  }
}

export class Moteur {
  private processus = new Map<Service['nom'], ChildProcess>();
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

  /** Lancer un service s'il ne tourne pas, et attendre qu'il écoute. Rend null si tout va bien, sinon la raison. */
  private async lancer(s: Service, journaux: string): Promise<string | null> {
    if (await portOuvert(s.port)) return null;
    if (!existsSync(s.cwd)) return `${s.libelle} : dossier introuvable (${s.cwd})`;
    const [exe, ...args] = s.commande;
    if (!exe) return `${s.libelle} : commande vide`;
    let sorti: string | null = null;
    try {
      const journal = createWriteStream(join(journaux, `${s.nom}.log`), { flags: 'a' });
      const p = spawn(exe, args, {
        cwd: s.cwd,
        env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1', ...(s.env ?? {}) },
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      });
      p.stdout?.pipe(journal);
      p.stderr?.pipe(journal);
      p.once('error', (e) => (sorti = `${s.libelle} : lancement impossible (${e.message})`));
      p.once('exit', (code) => {
        sorti = sorti ?? `${s.libelle} s'est arrêté (code ${code}), voir conversations/journaux/${s.nom}.log`;
        this.processus.delete(s.nom);
      });
      this.processus.set(s.nom, p);
    } catch (erreur) {
      return `${s.libelle} : lancement impossible (${String(erreur)})`;
    }
    const limite = Date.now() + s.delaiS * 1000;
    while (Date.now() < limite && sorti === null) {
      if (await portOuvert(s.port)) return null;
      await new Promise((r) => setTimeout(r, 700));
    }
    return sorti ?? `${s.libelle} : aucune réponse après ${s.delaiS} s`;
  }

  /**
   * Démarrer ce qui ne tourne pas encore. Le serveur Orbi d'abord (l'interface marche aussitôt, en démo) ; puis la
   * recherche et le modèle, en parallèle ; l'interface passe en local d'elle-même quand le modèle est prêt.
   */
  async demarrer(): Promise<StatutMoteur> {
    const racine = racineProjet(this.dossierApplication);
    if (!racine) return this.changer('indisponible', 'projet orbi introuvable (variable ORBI_RACINE)');
    const services = chargerServices(racine);
    const dejaLa = await Promise.all(services.map((s) => portOuvert(s.port)));
    if (dejaLa.every(Boolean)) return this.changer('externe');
    const journaux = join(racine, 'conversations', 'journaux');
    mkdirSync(journaux, { recursive: true });
    const [api, ...modeles] = services as [Service, ...Service[]];
    this.changer('demarrage', 'démarrage du serveur Orbi…');
    const raisonApi = await this.lancer(api, journaux);
    if (raisonApi) return this.changer('indisponible', raisonApi);
    this.changer('demarrage', 'chargement du modèle K2 et de la recherche (environ 1 min 30)…');
    const raisons = (await Promise.all(modeles.map((s) => this.lancer(s, journaux)))).filter(Boolean);
    if (raisons.length) return this.changer('indisponible', raisons.join(' ; '));
    return this.changer('pret');
  }

  async relancer(): Promise<StatutMoteur> {
    this.arreter();
    return this.demarrer();
  }

  /** Arrêter les services démarrés par l'application, avec leurs enfants (uv lance Python). */
  arreter(): void {
    for (const p of this.processus.values()) {
      if (!p.pid) continue;
      if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(p.pid), '/T', '/F'], { windowsHide: true });
      else p.kill('SIGTERM');
    }
    this.processus.clear();
  }
}
