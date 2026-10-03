/** L'application de bureau : processus principal, préchargement et renderer (`npm run dev`, `npm run build`). */
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'electron-vite';
import { pluginPolitiqueContenu, proxyApi } from './vite.commun.mts';

const ici = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  main: {
    build: { rollupOptions: { input: { index: resolve(ici, 'electron/main.ts') } } },
  },
  preload: {
    build: { rollupOptions: { input: { index: resolve(ici, 'electron/preload.ts') } } },
  },
  renderer: {
    root: ici,
    plugins: [react(), pluginPolitiqueContenu()],
    define: { __SANS_API__: 'false' },
    server: { port: 5174, proxy: proxyApi() },
    build: { rollupOptions: { input: { index: resolve(ici, 'index.html') } } },
  },
});
