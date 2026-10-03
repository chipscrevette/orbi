/**
 * Le préchargement : la seule porte entre l'interface et Electron. L'interface ne voit que window.orbi : les trois
 * commandes de la fenêtre et l'état du moteur local ; ni Node, ni ipcRenderer.
 */
import { contextBridge, ipcRenderer, type IpcRendererEvent } from 'electron';

interface StatutMoteur {
  etat: 'inconnu' | 'demarrage' | 'pret' | 'externe' | 'indisponible';
  message: string | null;
}

const pont = {
  fenetre: {
    fermer: (): void => ipcRenderer.send('fenetre:fermer'),
    reduire: (): void => ipcRenderer.send('fenetre:reduire'),
    agrandir: (): void => ipcRenderer.send('fenetre:agrandir'),
  },
  moteur: {
    statut: (): Promise<StatutMoteur> => ipcRenderer.invoke('moteur:statut'),
    relancer: (): Promise<StatutMoteur> => ipcRenderer.invoke('moteur:relancer'),
    surStatut(rappel: (statut: StatutMoteur) => void): () => void {
      const ecouteur = (_evenement: IpcRendererEvent, statut: StatutMoteur) => rappel(statut);
      ipcRenderer.on('moteur:statut', ecouteur);
      return () => ipcRenderer.removeListener('moteur:statut', ecouteur);
    },
  },
};

contextBridge.exposeInMainWorld('orbi', pont);
