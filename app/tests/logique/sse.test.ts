import { describe, expect, it } from 'vitest';
import { analyserMessage, creerLecteurSse, lireFlux, type MessageSse } from '../../src/logique/sse.ts';

const FLUX = [
  'event: etape\ndata: {"id": "tri", "t": 6.2}\n\n',
  ': battement\n\n',
  'event: lieu\ndata: {"adresse": "32b Rue Petricot 64200 Biarritz", "point": [-1.560632, 43.471773], "zone": "UH"}\n\n',
  'event: etape\ndata: {"id": "contrôle", "t": 56.1}\n\n',
  'event: reponse\ndata: {"verdict": "oui sous conditions", "texte": "Oui, sous conditions.", "regles": []}\n\n',
].join('');

function toutLire(morceaux: readonly string[]): MessageSse[] {
  const lecteur = creerLecteurSse();
  const messages = morceaux.flatMap((m) => lecteur.pousser(m));
  return [...messages, ...lecteur.terminer()];
}

const ATTENDU = toutLire([FLUX]);

describe('lecteur SSE', () => {
  it('lit un flux complet en messages, sans les battements de cœur', () => {
    expect(ATTENDU.map((m) => m.evenement)).toEqual(['etape', 'lieu', 'etape', 'reponse']);
    expect(JSON.parse(ATTENDU[0]!.donnees)).toEqual({ id: 'tri', t: 6.2 });
  });

  it('recolle un événement coupé en deux paquets, à toutes les positions possibles', () => {
    for (let coupure = 1; coupure < FLUX.length; coupure += 1) {
      expect(toutLire([FLUX.slice(0, coupure), FLUX.slice(coupure)])).toEqual(ATTENDU);
    }
  });

  it('résiste à un découpage en petits morceaux de tailles variées', () => {
    const tailles = [1, 2, 3, 5, 7, 11, 13];
    const morceaux: string[] = [];
    let i = 0;
    let k = 0;
    while (i < FLUX.length) {
      const taille = tailles[k % tailles.length]!;
      morceaux.push(FLUX.slice(i, i + taille));
      i += taille;
      k += 1;
    }
    expect(toutLire(morceaux)).toEqual(ATTENDU);
  });

  it('accepte les fins de ligne \\r\\n, même coupées entre le \\r et le \\n', () => {
    const crlf = FLUX.replace(/\n/g, '\r\n');
    for (let coupure = 1; coupure < crlf.length; coupure += 1) {
      expect(toutLire([crlf.slice(0, coupure), crlf.slice(coupure)])).toEqual(ATTENDU);
    }
  });

  it('ignore les commentaires, même au milieu d’un événement', () => {
    const messages = toutLire(['event: etape\n: battement\ndata: {"id":"tri","t":1}\n\n']);
    expect(messages).toEqual([{ evenement: 'etape', donnees: '{"id":"tri","t":1}' }]);
  });

  it('joint les lignes « data » multiples par un saut de ligne', () => {
    expect(toutLire(['data: a\ndata: b\n\n'])).toEqual([{ evenement: 'message', donnees: 'a\nb' }]);
  });

  it('rend le dernier événement non suivi d’une ligne vide à la fin du flux', () => {
    expect(toutLire(['event: fin\ndata: {}'])).toEqual([{ evenement: 'fin', donnees: '{}' }]);
  });

  it('ne rend rien pour un flux vide ou fait de battements', () => {
    expect(toutLire([])).toEqual([]);
    expect(toutLire([''])).toEqual([]);
    expect(toutLire([': battement\n\n: battement\n\n'])).toEqual([]);
  });
});

describe('lireFlux (octets)', () => {
  async function* octets(morceaux: Uint8Array[]): AsyncGenerator<Uint8Array> {
    for (const m of morceaux) yield m;
  }

  it('recolle un caractère accentué coupé entre deux paquets d’octets', async () => {
    const tout = new TextEncoder().encode('event: etape\ndata: {"id": "décision", "t": 56.2}\n\n');
    const position = tout.indexOf(0xc3); // premier octet de « é »
    const recus: MessageSse[] = [];
    for await (const m of lireFlux(octets([tout.slice(0, position + 1), tout.slice(position + 1)]))) recus.push(m);
    expect(recus).toEqual([{ evenement: 'etape', donnees: '{"id": "décision", "t": 56.2}' }]);
  });

  it('lit un ReadableStream comme fetch le fournit', async () => {
    const encodeur = new TextEncoder();
    const flux = new ReadableStream<Uint8Array>({
      start(controleur) {
        controleur.enqueue(encodeur.encode('event: etape\ndata: {"id":"tri",'));
        controleur.enqueue(encodeur.encode('"t":6.2}\n\nevent: etape\ndata: {"id":"fin","t":9}\n\n'));
        controleur.close();
      },
    });
    const recus: string[] = [];
    for await (const m of lireFlux(flux.getReader())) recus.push(m.donnees);
    expect(recus).toEqual(['{"id":"tri","t":6.2}', '{"id":"fin","t":9}']);
  });
});

describe('analyserMessage', () => {
  it('type les événements du contrat', () => {
    expect(analyserMessage({ evenement: 'etape', donnees: '{"id":"tri","t":6.2}' })).toEqual({
      type: 'etape',
      etape: { id: 'tri', t: 6.2 },
    });
    const lieu = analyserMessage({
      evenement: 'lieu',
      donnees: '{"adresse":"1 Rue Haraout","point":[-1.5454,43.47831],"zone":"UDc","servitudes":[]}',
    });
    expect(lieu.type).toBe('lieu');
    if (lieu.type === 'lieu') expect(lieu.lieu.point).toEqual([-1.5454, 43.47831]);
    const reponse = analyserMessage({ evenement: 'reponse', donnees: '{"verdict":"non","texte":"Non.","duree_s":47.2}' });
    expect(reponse.type).toBe('reponse');
    if (reponse.type === 'reponse') {
      expect(reponse.reponse.duree_s).toBe(47.2);
      expect(reponse.reponse.regles).toEqual([]);
    }
  });

  it('lit une erreur et donne un message par défaut', () => {
    expect(analyserMessage({ evenement: 'erreur', donnees: '{"message":"Orbi répond déjà à une question…"}' })).toEqual({
      type: 'erreur',
      message: 'Orbi répond déjà à une question…',
    });
    const sansMessage = analyserMessage({ evenement: 'erreur', donnees: '{}' });
    expect(sansMessage.type).toBe('erreur');
  });

  it('range l’illisible et l’inattendu en « inconnu » sans lever d’exception', () => {
    expect(analyserMessage({ evenement: 'etape', donnees: 'pas du json' })).toEqual({ type: 'inconnu', nom: 'etape' });
    expect(analyserMessage({ evenement: 'progression', donnees: '{}' })).toEqual({ type: 'inconnu', nom: 'progression' });
    expect(analyserMessage({ evenement: 'etape', donnees: '{"t":3}' })).toEqual({ type: 'inconnu', nom: 'etape' });
  });
});

describe('réponse de conversation', () => {
  it('lit un message d’Orbi (« coucou ») avec sa durée', () => {
    expect(analyserMessage({ evenement: 'message', donnees: '{"texte": "Bonjour !", "duree_s": 4.2}' })).toEqual({
      type: 'message',
      texte: 'Bonjour !',
      dureeS: 4.2,
    });
  });

  it('un message sans texte est inconnu, pas une réponse vide', () => {
    expect(analyserMessage({ evenement: 'message', donnees: '{"duree_s": 4.2}' })).toEqual({ type: 'inconnu', nom: 'message' });
  });
});
