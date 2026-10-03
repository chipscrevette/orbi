/**
 * La colonne de droite : le modèle local et ses jauges (vraies valeurs de /api/etat), la base documentaire,
 * et l'aperçu carte où le lieu de la dernière réponse s'éclaire.
 */
import {
  Database,
  Gpu,
  Map as IconeCarte,
  Maximize2,
  MemoryStick,
  PenTool,
  SquareTerminal,
  X,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import type { Mode } from '../../etat/fil.ts';
import { resumeBasePlu, jaugeGpu, jaugeMemoire, jaugeTemps, type Jauge } from '../../logique/etat.ts';
import type { CollectionZones } from '../../logique/geo.ts';
import type { Lieu } from '../../logique/types.ts';
import { formatNombre } from '../../logique/format.ts';
import { CarteZones } from '../Carte/CarteZones.tsx';
import { Legende } from '../Carte/Legende.tsx';
import { cx } from '../cx.ts';
import styles from './PanneauDroit.module.css';

interface Props {
  mode: Mode;
  zones: CollectionZones | null;
  lieu: Lieu | null;
  dureeMoyenneDemo: number | null;
  onOuvrirCarte: () => void;
  ouvert: boolean;
  onFermer: () => void;
}

type TonPastille = 'vert' | 'ambre' | 'rouge' | 'gris';

function Pastille({ ton, children }: { ton: TonPastille; children: string }) {
  return (
    <span className={cx(styles.pastilleEtat, styles[ton])}>
      <span className={styles.point} aria-hidden="true" />
      {children}
    </span>
  );
}

export function PanneauDroit({ mode, zones, lieu, dureeMoyenneDemo, onOuvrirCarte, ouvert, onFermer }: Props) {
  return (
    <aside className={styles.panneau} data-ouvert={ouvert} aria-label="État du moteur et aperçu carte">
      <button type="button" className={styles.fermer} onClick={onFermer} aria-label="Fermer le panneau">
        <X aria-hidden="true" strokeWidth={2} />
      </button>
      <CarteModele mode={mode} dureeMoyenneDemo={dureeMoyenneDemo} />
      <CarteBase mode={mode} zones={zones} />
      <ApercuCarte zones={zones} lieu={lieu} onOuvrirCarte={onOuvrirCarte} />
    </aside>
  );
}

function CarteModele({ mode, dureeMoyenneDemo }: { mode: Mode; dureeMoyenneDemo: number | null }) {
  const etat = mode.type === 'recherche' ? null : mode.etat;
  const nom = etat?.modele.nom ?? 'K2 Horizon 7B';
  let pastille: [TonPastille, string] = ['gris', 'Recherche…'];
  if (mode.type === 'local') pastille = mode.etat.modele.en_ligne ? ['vert', 'En ligne'] : ['rouge', 'Hors ligne'];
  else if (mode.type === 'demo') pastille = ['gris', 'Démo'];

  const enLocal = mode.type === 'local';
  const gpu = etat ? jaugeGpu(etat.gpu) : null;
  const memoire = etat ? jaugeMemoire(etat.memoire) : null;
  const temps = enLocal ? jaugeTemps(mode.etat.temps_reponse_s) : jaugeTemps(dureeMoyenneDemo);
  const absent = mode.type === 'demo' && !etat ? 'en local seulement' : '—';

  return (
    <section className={styles.carte}>
      <header className={styles.entete}>
        <span className={cx(styles.tuile, styles.tuileBleue)}>
          <SquareTerminal aria-hidden="true" strokeWidth={2} />
        </span>
        <div className={styles.titres}>
          <p className={styles.surtitre}>Modèle local</p>
          <h2 className={styles.titreModele}>{nom}</h2>
        </div>
        <Pastille ton={pastille[0]}>{pastille[1]}</Pastille>
      </header>
      <hr className={styles.separateur} />
      <ul className={styles.jauges}>
        <LigneJauge
          icone={Gpu}
          libelle={etat?.gpu?.nom ? `GPU (${etat.gpu.nom})` : 'GPU'}
          jauge={gpu}
          absent={absent}
          aide="Mémoire de la carte graphique utilisée par le modèle"
        />
        <LigneJauge icone={MemoryStick} libelle="Mémoire" jauge={memoire} absent={absent} aide="Mémoire vive de l'ordinateur" />
        <LigneJauge
          icone={Zap}
          libelle="Temps de réponse"
          jauge={temps}
          absent="—"
          aide={
            enLocal
              ? 'Temps moyen d’une réponse complète (jauge pleine à 120 s)'
              : 'Temps réel moyen des réponses enregistrées (jauge pleine à 120 s)'
          }
        />
      </ul>
    </section>
  );
}

function LigneJauge({
  icone: Icone,
  libelle,
  jauge,
  absent,
  aide,
}: {
  icone: LucideIcon;
  libelle: string;
  jauge: Jauge | null;
  absent: string;
  aide: string;
}) {
  return (
    <li className={styles.jauge} title={aide}>
      <Icone className={styles.iconeJauge} aria-hidden="true" strokeWidth={1.9} />
      <span className={styles.libelleJauge}>{libelle}</span>
      {jauge ? (
        <>
          <span
            className={styles.piste}
            role="meter"
            aria-label={libelle}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(jauge.ratio * 100)}
            aria-valuetext={jauge.texte}
          >
            <span className={cx(styles.remplissage, styles[jauge.ton])} style={{ width: `${Math.max(4, jauge.ratio * 100)}%` }} />
          </span>
          <span className={styles.valeur}>{jauge.texte}</span>
        </>
      ) : (
        <span className={styles.absent}>{absent}</span>
      )}
    </li>
  );
}

function CarteBase({ mode, zones }: { mode: Mode; zones: CollectionZones | null }) {
  let pastille: [TonPastille, string] = ['gris', 'Recherche…'];
  let plu = 'Biarritz · Règlement · Zonage';
  let cadastre = 'API Carto IGN · Parcelles · Servitudes';
  if (mode.type === 'local' || (mode.type === 'demo' && mode.etat)) {
    const etat = mode.etat!;
    const connectees = [etat.base.plu.connectee, etat.base.cadastre.connectee].filter(Boolean).length;
    pastille = connectees === 2 ? ['vert', 'Connectée'] : connectees === 1 ? ['ambre', 'Partielle'] : ['rouge', 'Déconnectée'];
    plu = resumeBasePlu(etat) || plu;
    cadastre = `${etat.base.cadastre.source ?? 'API Carto IGN'} · Parcelles · Servitudes`;
  } else if (mode.type === 'demo') {
    pastille = ['gris', 'Enregistrée'];
    if (zones) plu = `Biarritz · Règlement · ${formatNombre(zones.features.length)} zones`;
  }
  return (
    <section className={styles.carte}>
      <header className={styles.entete}>
        <span className={cx(styles.tuile, styles.tuileGrise)}>
          <Database aria-hidden="true" strokeWidth={1.9} />
        </span>
        <h2 className={styles.titreSection}>Base RAG</h2>
        <Pastille ton={pastille[0]}>{pastille[1]}</Pastille>
      </header>
      <ul className={styles.sources}>
        <li className={styles.source}>
          <span className={cx(styles.tuileSource, styles.tuileBleue)}>
            <IconeCarte aria-hidden="true" strokeWidth={1.9} />
          </span>
          <div>
            <p className={styles.sourceNom}>PLU</p>
            <p className={styles.sourceDetail}>{plu}</p>
          </div>
        </li>
        <li className={styles.source}>
          <span className={cx(styles.tuileSource, styles.tuileVerte)}>
            <PenTool aria-hidden="true" strokeWidth={1.9} />
          </span>
          <div>
            <p className={styles.sourceNom}>Cadastre</p>
            <p className={styles.sourceDetail}>{cadastre}</p>
          </div>
        </li>
      </ul>
    </section>
  );
}

function ApercuCarte({ zones, lieu, onOuvrirCarte }: { zones: CollectionZones | null; lieu: Lieu | null; onOuvrirCarte: () => void }) {
  const etiquette = lieu ? [lieu.parcelle, lieu.zone ? `zone ${lieu.zone}` : null].filter(Boolean).join(' · ') : null;
  return (
    <section className={cx(styles.carte, styles.apercu)}>
      <header className={styles.entete}>
        <span className={cx(styles.tuile, styles.tuileGrise)}>
          <IconeCarte aria-hidden="true" strokeWidth={1.9} />
        </span>
        <h2 className={styles.titreSection}>Aperçu carte</h2>
        <button type="button" className={styles.agrandir} onClick={onOuvrirCarte} aria-label="Ouvrir la carte" title="Ouvrir la carte">
          <Maximize2 aria-hidden="true" strokeWidth={1.9} />
        </button>
      </header>
      <div className={styles.cadre}>
        <CarteZones zones={zones} lieu={lieu} interactive className={styles.carteLeaflet} libelle="Aperçu des zones du PLU de Biarritz" />
        {etiquette && <p className={styles.etiquette}>{etiquette}</p>}
        <div className={styles.legende}>
          <Legende compacte />
        </div>
      </div>
    </section>
  );
}
