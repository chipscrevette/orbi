/**
 * La carte des zones du PLU. Un clic : la zone (code, nature, caractère tiré du règlement), l'adresse la plus proche
 * (Base adresse nationale), et deux suites possibles : lire le règlement de la zone, ou poser une question sur l'adresse.
 */
import { ArrowRight, BookOpen, LoaderCircle, MapPin, MousePointerClick, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { adresseAuPoint } from '../api/client.ts';
import { CarteZones } from '../composants/Carte/CarteZones.tsx';
import { Legende } from '../composants/Carte/Legende.tsx';
import { useReglement } from '../etat/useReglement.ts';
import { zoneAuPoint, type CollectionZones, type EntiteZone } from '../logique/geo.ts';
import type { Lieu, Point } from '../logique/types.ts';
import { caractereZone, chapitreDeZone, familleDeZone, TYPES_ZONE } from '../logique/zones.ts';
import styles from './Vues.module.css';

interface Choix {
  point: Point;
  zone: EntiteZone | null;
  /** `undefined` : recherche en cours ; `null` : introuvable. */
  adresse: string | null | undefined;
}

interface Props {
  zones: CollectionZones | null;
  lieu: Lieu | null;
  onLireChapitre: (chapitre: string) => void;
  onUtiliserAdresse: (adresse: string) => void;
}

export function VueCartes({ zones, lieu, onLireChapitre, onUtiliserAdresse }: Props) {
  const [choix, setChoix] = useState<Choix | null>(null);
  const reglement = useReglement();
  const requete = useRef<AbortController | null>(null);

  useEffect(() => () => requete.current?.abort(), []);

  const choisir = useCallback(
    (point: Point) => {
      const zone = zones ? zoneAuPoint(zones.features, point) : null;
      setChoix({ point, zone, adresse: undefined });
      requete.current?.abort();
      const controleur = new AbortController();
      requete.current = controleur;
      void adresseAuPoint(point, controleur.signal).then((adresse) => {
        if (controleur.signal.aborted) return;
        setChoix((actuel) => (actuel && actuel.point === point ? { ...actuel, adresse } : actuel));
      });
    },
    [zones],
  );

  const proprietes = choix?.zone?.properties ?? null;
  const code = proprietes?.libelle ?? null;
  const famille = choix?.zone ? familleDeZone(code, proprietes?.typezone) : null;
  const chapitres = reglement.chapitres?.map((c) => c.cle) ?? [];
  const chapitre = code ? chapitreDeZone(code, chapitres) : null;
  const caractere = code ? caractereZone(code, proprietes?.libelong) : null;
  const nature = proprietes?.typezone ? TYPES_ZONE[proprietes.typezone] : null;

  return (
    <section className={styles.page} aria-labelledby="titre-cartes">
      <header className={styles.enteteVue}>
        <h1 id="titre-cartes" className={styles.titreVue}>
          Zones du PLU de Biarritz
        </h1>
        <p className={styles.aideVue}>
          <MousePointerClick aria-hidden="true" strokeWidth={2} />
          Cliquez sur la carte : la zone, son règlement et l’adresse du point.
        </p>
      </header>
      <div className={styles.cadreCarte}>
        <CarteZones
          zones={zones}
          lieu={lieu}
          zoneChoisie={choix?.zone ?? null}
          pointChoisi={choix?.point ?? null}
          interactive
          onClic={choisir}
          className={styles.carteGrande}
          libelle="Carte des zones du PLU de Biarritz"
        />
        <div className={styles.legendeCarte}>
          <Legende />
        </div>
        {choix && (
          <aside className={styles.fiche} aria-label="Le point choisi">
            <button type="button" className={styles.ficheFermer} onClick={() => setChoix(null)} aria-label="Fermer">
              <X aria-hidden="true" strokeWidth={2} />
            </button>
            {choix.zone && famille ? (
              <>
                <p className={styles.ficheZone}>
                  <span className={styles.ficheCouleur} style={{ background: famille.couleur }} aria-hidden="true" />
                  zone <strong>{code}</strong>
                </p>
                <p className={styles.ficheNature}>
                  {[nature, famille.libelle].filter(Boolean).join(' · ')}
                  {proprietes?.libelong && proprietes.libelong !== code ? ` · ${proprietes.libelong}` : ''}
                </p>
                {caractere && <p className={styles.ficheCaractere}>« {caractere} »</p>}
                {chapitre ? (
                  <button type="button" className={styles.ficheAction} onClick={() => onLireChapitre(chapitre)}>
                    <BookOpen aria-hidden="true" strokeWidth={2} />
                    Lire le règlement de la zone {chapitre}
                    <ArrowRight aria-hidden="true" strokeWidth={2} />
                  </button>
                ) : (
                  reglement.statut === 'pret' && (
                    <p className={styles.ficheNote}>Le règlement découpé ne contient pas de chapitre pour cette zone.</p>
                  )
                )}
              </>
            ) : (
              <p className={styles.ficheNature}>Ce point est hors des zones du PLU de Biarritz.</p>
            )}
            <hr className={styles.ficheSeparateur} />
            <p className={styles.ficheAdresse}>
              {choix.adresse === undefined ? (
                <LoaderCircle className={styles.tourne} aria-hidden="true" strokeWidth={2} />
              ) : (
                <MapPin aria-hidden="true" strokeWidth={2} />
              )}
              {choix.adresse === undefined ? 'Recherche de l’adresse…' : (choix.adresse ?? 'Adresse introuvable à cet endroit')}
            </p>
            {choix.adresse && (
              <button type="button" className={styles.ficheAction} onClick={() => onUtiliserAdresse(choix.adresse!)}>
                Poser une question sur cette adresse
                <ArrowRight aria-hidden="true" strokeWidth={2} />
              </button>
            )}
          </aside>
        )}
      </div>
    </section>
  );
}
