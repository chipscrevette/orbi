/**
 * Le renderer seul, dans un navigateur : `npm run dev:web` (avec le relais `/api` vers le moteur local)
 * et `npm run build:web` (site statique à chemins relatifs pour GitHub Pages : pas d'API, donc mode démo).
 */
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { pluginPolitiqueContenu, proxyApi } from './vite.commun.mts';

export default defineConfig(({ command }) => ({
  root: '.',
  base: './',
  plugins: [react(), pluginPolitiqueContenu()],
  define: { __SANS_API__: JSON.stringify(command === 'build') },
  server: { port: 5173, strictPort: true, proxy: proxyApi() },
  preview: { port: 4173, strictPort: true },
  build: { outDir: 'dist/web', emptyOutDir: true, target: 'es2022' },
}));
