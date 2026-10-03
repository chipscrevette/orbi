/**
 * Lecture d'un flux « text/event-stream » reçu par morceaux arbitraires (un événement peut être coupé en deux paquets,
 * un caractère accentué peut l'être entre deux octets). Les lignes de commentaire (« : battement ») sont ignorées.
 */
import { estObjet, lireEtape, lireLieu, lireReponse, nombre, texte } from './contrat.ts';
import type { EvenementFlux } from './types.ts';

export interface MessageSse {
  evenement: string;
  donnees: string;
}

export interface LecteurSse {
  /** Ajoute un morceau de texte et rend les messages devenus complets. */
  pousser(morceau: string): MessageSse[];
  /** Fin du flux : rend le dernier message s'il n'était pas suivi d'une ligne vide. */
  terminer(): MessageSse[];
}

function lireBloc(bloc: string): MessageSse | null {
  let evenement = 'message';
  const donnees: string[] = [];
  for (const ligne of bloc.split('\n')) {
    if (ligne === '' || ligne.startsWith(':')) continue;
    const deuxPoints = ligne.indexOf(':');
    const champ = deuxPoints === -1 ? ligne : ligne.slice(0, deuxPoints);
    let valeur = deuxPoints === -1 ? '' : ligne.slice(deuxPoints + 1);
    if (valeur.startsWith(' ')) valeur = valeur.slice(1);
    if (champ === 'event') evenement = valeur || 'message';
    else if (champ === 'data') donnees.push(valeur);
  }
  // Un bloc sans « data » (un battement de cœur seul, par exemple) ne produit rien.
  return donnees.length === 0 ? null : { evenement, donnees: donnees.join('\n') };
}

export function creerLecteurSse(): LecteurSse {
  let tampon = '';

  const extraire = (final: boolean): MessageSse[] => {
    // Un « \r » en fin de morceau peut être la première moitié d'un « \r\n » : on le garde pour le morceau suivant.
    const fin = !final && tampon.endsWith('\r') ? tampon.length - 1 : tampon.length;
    const pret = tampon.slice(0, fin).replace(/\r\n?/g, '\n');
    const enAttente = tampon.slice(fin);
    const blocs = pret.split('\n\n');
    let reste = blocs.pop() ?? '';
    if (final) {
      blocs.push(reste);
      reste = '';
    }
    tampon = reste + enAttente;
    return blocs.map(lireBloc).filter((m): m is MessageSse => m !== null);
  };

  return {
    pousser(morceau) {
      tampon += morceau;
      return extraire(false);
    },
    terminer() {
      return extraire(true);
    },
  };
}

/** Transforme un message brut en événement typé ; tout ce qui est illisible devient « inconnu ». */
export function analyserMessage(message: MessageSse): EvenementFlux {
  let json: unknown;
  try {
    json = JSON.parse(message.donnees);
  } catch {
    return { type: 'inconnu', nom: message.evenement };
  }
  switch (message.evenement) {
    case 'etape': {
      const etape = lireEtape(json);
      return etape ? { type: 'etape', etape } : { type: 'inconnu', nom: message.evenement };
    }
    case 'lieu': {
      const lieu = lireLieu(json);
      return lieu ? { type: 'lieu', lieu } : { type: 'inconnu', nom: message.evenement };
    }
    case 'reponse': {
      const reponse = lireReponse(json);
      return reponse ? { type: 'reponse', reponse } : { type: 'inconnu', nom: message.evenement };
    }
    case 'message': {
      const t = estObjet(json) ? texte(json.texte) : null;
      return t
        ? { type: 'message', texte: t, dureeS: estObjet(json) ? nombre(json.duree_s) : null }
        : { type: 'inconnu', nom: message.evenement };
    }
    case 'erreur':
      return {
        type: 'erreur',
        message: (estObjet(json) ? texte(json.message) : null) ?? 'Le moteur local a signalé une erreur sans la décrire.',
      };
    default:
      return { type: 'inconnu', nom: message.evenement };
  }
}

type SourceOctets = AsyncIterable<Uint8Array> | ReadableStreamDefaultReader<Uint8Array>;

function estLecteur(source: SourceOctets): source is ReadableStreamDefaultReader<Uint8Array> {
  return typeof (source as ReadableStreamDefaultReader<Uint8Array>).read === 'function';
}

async function* depuisLecteur(lecteur: ReadableStreamDefaultReader<Uint8Array>): AsyncGenerator<Uint8Array> {
  try {
    for (;;) {
      const { done, value } = await lecteur.read();
      if (done) return;
      if (value) yield value;
    }
  } finally {
    lecteur.releaseLock();
  }
}

/** Lit des octets (corps d'une réponse `fetch`) et rend les messages SSE au fil de l'eau. */
export async function* lireFlux(source: SourceOctets): AsyncGenerator<MessageSse> {
  const decodeur = new TextDecoder('utf-8');
  const lecteur = creerLecteurSse();
  const morceaux = estLecteur(source) ? depuisLecteur(source) : source;
  for await (const octets of morceaux) {
    yield* lecteur.pousser(decodeur.decode(octets, { stream: true }));
  }
  yield* lecteur.pousser(decodeur.decode());
  yield* lecteur.terminer();
}
