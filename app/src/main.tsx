import '@fontsource-variable/inter';
import 'leaflet/dist/leaflet.css';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App.tsx';
import './styles/jetons.css';
import './styles/base.css';

const racine = document.getElementById('racine');
if (!racine) throw new Error('élément #racine introuvable');
document.documentElement.dataset.cadre = window.orbi ? 'electron' : 'navigateur';

createRoot(racine).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
