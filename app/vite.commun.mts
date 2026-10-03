/** Réglages Vite partagés par l'application de bureau (electron-vite) et le site statique (vite seul). */
import type { ServerResponse } from 'node:http';
import type { Plugin, ProxyOptions } from 'vite';

/** Adresse du moteur local (le serveur Python d'Orbi). */
export const CIBLE_API = process.env.ORBI_API ?? 'http://127.0.0.1:4770';

/**
 * En développement, `/api` est relayé vers le moteur local. Le flux SSE de `/api/question` doit passer au fil de
 * l'eau : pas de compression demandée au serveur, et les en-têtes qui interdisent toute mise en mémoire tampon.
 */
export function proxyApi(): Record<string, ProxyOptions> {
  return {
    '/api': {
      target: CIBLE_API,
      changeOrigin: true,
      configure(proxy) {
        proxy.on('proxyReq', (requete) => {
          requete.setHeader('accept-encoding', 'identity');
        });
        proxy.on('proxyRes', (reponse) => {
          if (String(reponse.headers['content-type'] ?? '').includes('text/event-stream')) {
            reponse.headers['cache-control'] = 'no-cache, no-transform';
            reponse.headers['x-accel-buffering'] = 'no';
          }
        });
        proxy.on('error', (_erreur, _requete, reponse) => {
          // Moteur éteint : une réponse 503 claire, l'interface passe en démo.
          const r = reponse as ServerResponse;
          if (typeof r.writeHead === 'function' && !r.headersSent) {
            r.writeHead(503, { 'content-type': 'application/json; charset=utf-8' });
            r.end(JSON.stringify({ erreur: 'moteur local injoignable' }));
          }
        });
      },
    },
  };
}

/** Politique de sécurité du contenu, ajoutée aux pages construites (pas en développement, où Vite injecte du script). */
export const POLITIQUE_CONTENU = [
  "default-src 'self'",
  "script-src 'self'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: https://data.geopf.fr",
  "font-src 'self' data:",
  "connect-src 'self' https://api-adresse.data.gouv.fr",
  "object-src 'none'",
  "frame-src 'self'",
  "base-uri 'self'",
].join('; ');

export function pluginPolitiqueContenu(): Plugin {
  return {
    name: 'orbi-politique-contenu',
    apply: 'build',
    transformIndexHtml(html) {
      return html.replace(
        '<head>',
        `<head>\n    <meta http-equiv="Content-Security-Policy" content="${POLITIQUE_CONTENU}" />`,
      );
    },
  };
}
