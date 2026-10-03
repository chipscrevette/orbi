/**
 * Carte des zones du PLU sur le fond Plan IGN v2 (sans clé), zones colorées par famille. Met en évidence un lieu
 * (sa zone et son point) ou une zone choisie. Non interactive pour l'aperçu, interactive pour la vue Cartes.
 */
import type { FeatureCollection, GeoJsonObject } from 'geojson';
import L from 'leaflet';
import { useEffect, useRef } from 'react';
import { emprise, empriseCollection, zoneAuPoint, type CollectionZones, type Emprise, type EntiteZone } from '../../logique/geo.ts';
import type { Lieu, Point } from '../../logique/types.ts';
import { familleDeZone } from '../../logique/zones.ts';

export const URL_PLAN_IGN =
  'https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2' +
  '&STYLE=normal&TILEMATRIXSET=PM&FORMAT=image/png&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}';

const CENTRE_BIARRITZ: L.LatLngTuple = [43.4711, -1.5558];
const COULEUR_POINT = '#2f6bf2'; // le bleu de la mascotte

interface Props {
  zones: CollectionZones | null;
  /** Le lieu d'une réponse : sa zone et son point sont mis en évidence. */
  lieu: Lieu | null;
  /** Une zone choisie d'un clic (vue Cartes). */
  zoneChoisie?: EntiteZone | null;
  pointChoisi?: Point | null;
  interactive?: boolean;
  onClic?: (point: Point) => void;
  className?: string;
  libelle: string;
}

function styleZone(entite: EntiteZone | undefined, opacite: number): L.PathOptions {
  const p = entite?.properties ?? {};
  const famille = familleDeZone(p.libelle, p.typezone);
  return { color: famille.couleur, weight: 1, opacity: 0.85, fillColor: famille.couleur, fillOpacity: opacite };
}

/** Au survol d'une zone : son code et son libellé (texte inséré sans HTML). */
function infobulleZone(p: { libelle?: string; libelong?: string } | null): HTMLElement {
  const el = document.createElement('div');
  const code = document.createElement('strong');
  code.textContent = p?.libelle ?? 'Zone';
  el.append(code);
  if (p?.libelong) el.append(` · ${p.libelong}`);
  return el;
}

function limites(e: Emprise): L.LatLngBounds {
  return L.latLngBounds([
    [e[1], e[0]],
    [e[3], e[2]],
  ]);
}

export function CarteZones({
  zones,
  lieu,
  zoneChoisie = null,
  pointChoisi = null,
  interactive = false,
  onClic,
  className,
  libelle,
}: Props) {
  const conteneur = useRef<HTMLDivElement>(null);
  const carteRef = useRef<L.Map | null>(null);
  const evidenceRef = useRef<L.LayerGroup | null>(null);
  const cadrageRef = useRef<(() => void) | null>(null);
  const clicRef = useRef(onClic);

  useEffect(() => {
    clicRef.current = onClic;
  }, [onClic]);

  // Création de la carte (une fois par conteneur).
  useEffect(() => {
    const element = conteneur.current;
    if (!element) return;
    const carte = L.map(element, {
      zoomControl: false,
      dragging: interactive,
      scrollWheelZoom: interactive,
      doubleClickZoom: interactive,
      boxZoom: interactive,
      keyboard: interactive,
      touchZoom: interactive,
      zoomSnap: 0.25,
      zoomDelta: 0.5,
      minZoom: 11,
      maxZoom: 19,
    });
    carte.attributionControl.setPrefix(false);
    if (interactive) L.control.zoom({ position: 'topright' }).addTo(carte);
    L.tileLayer(URL_PLAN_IGN, { attribution: '© IGN', maxZoom: 19 }).addTo(carte);
    carte.setView(CENTRE_BIARRITZ, 13);
    carte.on('click', (e: L.LeafletMouseEvent) => clicRef.current?.([e.latlng.lng, e.latlng.lat]));
    evidenceRef.current = L.layerGroup().addTo(carte);
    carteRef.current = carte;
    let tailleNulle = element.clientWidth === 0 || element.clientHeight === 0;
    const observateur = new ResizeObserver(() => {
      carte.invalidateSize();
      const nulle = element.clientWidth === 0 || element.clientHeight === 0;
      if (tailleNulle && !nulle) cadrageRef.current?.();
      tailleNulle = nulle;
    });
    observateur.observe(element);
    return () => {
      observateur.disconnect();
      carte.remove();
      carteRef.current = null;
      evidenceRef.current = null;
    };
  }, [interactive]);

  // Les zones, colorées par famille.
  useEffect(() => {
    const carte = carteRef.current;
    if (!carte || !zones) return;
    const couche = L.geoJSON(zones as unknown as FeatureCollection, {
      style: (f) => styleZone(f as unknown as EntiteZone, interactive ? 0.3 : 0.38),
      interactive,
      onEachFeature: interactive
        ? (f, calque) => calque.bindTooltip(infobulleZone(f.properties), { sticky: true, direction: 'top' })
        : undefined,
    }).addTo(carte);
    couche.bringToBack();
    return () => {
      couche.remove();
    };
  }, [zones, interactive]);

  // Mise en évidence et cadrage.
  useEffect(() => {
    const carte = carteRef.current;
    const groupe = evidenceRef.current;
    if (!carte || !groupe) return;
    groupe.clearLayers();
    const point = pointChoisi ?? lieu?.point ?? null;
    let zone = zoneChoisie;
    if (!zone && zones && lieu?.point) zone = zoneAuPoint(zones.features, lieu.point);
    if (zone) {
      const p = zone.properties ?? {};
      const couleur = familleDeZone(p.libelle, p.typezone).couleur;
      const objet = zone as unknown as GeoJsonObject;
      L.geoJSON(objet, { style: { color: '#ffffff', weight: 6, opacity: 0.95, fill: false }, interactive: false }).addTo(groupe);
      L.geoJSON(objet, {
        style: { color: couleur, weight: 3, opacity: 1, fillColor: couleur, fillOpacity: 0.55 },
        interactive: false,
      }).addTo(groupe);
    }
    if (point) {
      L.circleMarker([point[1], point[0]], {
        radius: 7,
        color: '#ffffff',
        weight: 3,
        fillColor: COULEUR_POINT,
        fillOpacity: 1,
        interactive: false,
      }).addTo(groupe);
    }

    // Un clic dans la vue Cartes ne déplace pas la carte ; un nouveau lieu, si.
    if (pointChoisi) return;
    // sans animation : un zoom animé lancé pendant un changement de vue restait figé (zones minuscules, carte « vide »)
    const cadrer = () => {
      const empriseZone = zone ? emprise(zone.geometry) : null;
      if (empriseZone) carte.fitBounds(limites(empriseZone), { padding: [26, 26], maxZoom: 16.5, animate: false });
      else if (point) carte.setView([point[1], point[0]], 16, { animate: false });
      else if (zones) {
        const tout = empriseCollection(zones.features);
        // la commune remplit le cadre (zoom « couvrant ») : pas de bandes vides de part et d'autre
        if (tout) {
          const bornes = limites(tout);
          carte.setView(bornes.getCenter(), carte.getBoundsZoom(bornes, true), { animate: false });
        }
      }
    };
    cadrageRef.current = cadrer;
    cadrer();
  }, [lieu, zones, zoneChoisie, pointChoisi]);

  return <div ref={conteneur} className={className} role="region" aria-label={libelle} />;
}
