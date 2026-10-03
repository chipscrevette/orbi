/**
 * Les appels au moteur local : uniquement des URL relatives (`/api/etat`, `/api/question`), relayées par Vite en
 * développement et servies par le serveur Python en production. Le flux SSE est lu avec fetch, en POST.
 */
import { estObjet, lireEtat, texte } from '../logique/contrat.ts';
import { analyserMessage, lireFlux } from '../logique/sse.ts';
import type { EtatServeur, EvenementFlux, Point } from '../logique/types.ts';

export const URL_ETAT = '/api/etat';
export const URL_QUESTION = '/api/question';
const DELAI_ETAT_MS = 4000;

/** `GET /api/etat`, ou `null` si le moteur ne répond pas (ou ne ressemble pas à Orbi). */
export async function chargerEtat(): Promise<EtatServeur | null> {
  try {
    const reponse = await fetch(URL_ETAT, {
      headers: { accept: 'application/json' },
      cache: 'no-store',
      signal: AbortSignal.timeout(DELAI_ETAT_MS),
    });
    if (!reponse.ok || !(reponse.headers.get('content-type') ?? '').includes('json')) return null;
    return lireEtat(await reponse.json());
  } catch {
    return null;
  }
}

async function messageHttp(reponse: Response): Promise<string> {
  let detail: string | null = null;
  try {
    const json: unknown = await reponse.json();
    if (estObjet(json)) {
      detail = texte(json.message) ?? texte(json.detail) ?? texte(json.erreur);
      if (detail === null && Array.isArray(json.detail)) {
        detail = json.detail
          .map((d: unknown) => (estObjet(d) ? texte(d.msg) : null))
          .filter((m): m is string => m !== null)
          .join(' ; ');
      }
    }
  } catch {
    detail = null;
  }
  if (reponse.status === 422) return `Le moteur local refuse cette question${detail ? ` : ${detail}` : ' (longueur ou format).'}`;
  if (reponse.status === 502 || reponse.status === 503 || reponse.status === 504) {
    return detail && detail !== 'moteur local injoignable' ? detail : 'Le moteur local ne répond pas.';
  }
  return `Le moteur local a répondu ${reponse.status}${detail ? ` : ${detail}` : '.'}`;
}

/**
 * `POST /api/question` : appelle `surEvenement` à chaque événement du flux, au fil de l'eau.
 * Se termine quand le flux se ferme ; lève une erreur lisible si la requête échoue.
 */
export async function poserQuestion(
  question: string,
  surEvenement: (evenement: EvenementFlux) => void,
  signal: AbortSignal,
): Promise<void> {
  const reponse = await fetch(URL_QUESTION, {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'text/event-stream' },
    body: JSON.stringify({ question }),
    cache: 'no-store',
    signal,
  });
  if (!reponse.ok) throw new Error(await messageHttp(reponse));
  const type = reponse.headers.get('content-type') ?? '';
  if (!type.includes('text/event-stream')) {
    // Une réponse JSON au lieu d'un flux : c'est un refus, on le montre comme une erreur.
    const message = await messageHttp(reponse);
    surEvenement({ type: 'erreur', message });
    return;
  }
  if (!reponse.body) throw new Error('Le moteur local a renvoyé une réponse vide.');
  for await (const message of lireFlux(reponse.body.getReader())) surEvenement(analyserMessage(message));
}

/** L'adresse la plus proche d'un point (Base adresse nationale), ou `null`. */
export async function adresseAuPoint(point: Point, signal?: AbortSignal): Promise<string | null> {
  const [lon, lat] = point;
  const url = `https://api-adresse.data.gouv.fr/reverse/?lon=${lon.toFixed(6)}&lat=${lat.toFixed(6)}&limit=1`;
  try {
    const reponse = await fetch(url, { signal: signal ?? AbortSignal.timeout(6000) });
    if (!reponse.ok) return null;
    const json: unknown = await reponse.json();
    if (!estObjet(json) || !Array.isArray(json.features)) return null;
    const premiere: unknown = json.features[0];
    if (!estObjet(premiere) || !estObjet(premiere.properties)) return null;
    return texte(premiere.properties.label);
  } catch {
    return null;
  }
}

/** Un fichier JSON statique livré avec l'interface (chemin relatif : `donnees/…`). */
export async function chargerJsonStatique(chemin: string): Promise<unknown> {
  const reponse = await fetch(chemin);
  if (!reponse.ok) throw new Error(`${chemin} : ${reponse.status}`);
  return reponse.json();
}
