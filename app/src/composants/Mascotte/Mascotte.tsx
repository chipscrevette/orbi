/**
 * Orbi, la mascotte : le rendu 3D détouré (`src/assets/orbi-detoure.png`) s'il existe, sinon un dessin SVG fidèle
 * (brique bleu roi aux angles très arrondis, deux yeux noirs ovales vers la droite, sans bouche). Les deux traits
 * « étincelle » de la maquette sont dessinés par-dessus. Les humeurs ne sont que du mouvement (CSS).
 */
import { useId, type CSSProperties } from 'react';
import type { Humeur } from '../../logique/verdict.ts';
import { cx } from '../cx.ts';
import styles from './Mascotte.module.css';

const RENDUS = import.meta.glob<string>('../../assets/orbi-detoure.png', {
  eager: true,
  query: '?url',
  import: 'default',
});
const IMAGE_RENDU: string | null = Object.values(RENDUS)[0] ?? null;

interface Props {
  humeur?: Humeur;
  /** Largeur de la brique : des pixels, ou une longueur CSS (« clamp(…) »). */
  taille: number | string;
  etincelles?: boolean;
  ombre?: boolean;
  className?: string;
  /** Texte alternatif ; sans lui, la mascotte est décorative. */
  libelle?: string;
}

export function Mascotte({ humeur = 'repos', taille, etincelles = true, ombre = true, className, libelle }: Props) {
  const style = { '--taille': typeof taille === 'number' ? `${taille}px` : taille } as CSSProperties;
  return (
    <span
      className={cx(styles.mascotte, className)}
      data-humeur={humeur}
      style={style}
      role={libelle ? 'img' : undefined}
      aria-label={libelle}
      aria-hidden={libelle ? undefined : true}
    >
      {ombre && <span className={styles.ombre} />}
      <span className={styles.corps}>
        {IMAGE_RENDU ? (
          <img className={styles.image} src={IMAGE_RENDU} alt="" draggable={false} />
        ) : (
          <MascotteDessinee />
        )}
      </span>
      {etincelles && (
        <svg className={styles.etincelles} viewBox="0 0 100 66" aria-hidden="true">
          <line x1="101.5" y1="3" x2="108.5" y2="-6.5" />
          <line x1="106.5" y1="11" x2="118" y2="6.5" />
        </svg>
      )}
    </span>
  );
}

/** Le dessin de repli, aux proportions de l'image détourée. */
function MascotteDessinee() {
  const id = useId().replace(/:/g, '');
  return (
    <svg className={styles.dessin} viewBox="0 0 100 66" aria-hidden="true">
      <defs>
        <linearGradient id={`face-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3a77f5" />
          <stop offset="0.55" stopColor="var(--orbi-clair)" />
          <stop offset="1" stopColor="var(--orbi-ombre)" />
        </linearGradient>
        <linearGradient id={`dessus-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#4c86f7" />
          <stop offset="1" stopColor="#3570f2" />
        </linearGradient>
        <radialGradient id={`reflet-${id}`} cx="0.3" cy="0.2" r="0.6">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.22" />
          <stop offset="1" stopColor="#ffffff" stopOpacity="0" />
        </radialGradient>
      </defs>
      {/* dessus et flanc gauche, vus de trois quarts */}
      <rect x="3" y="4" width="84" height="54" rx="18" fill={`url(#dessus-${id})`} />
      {/* face avant */}
      <rect x="9" y="10" width="88" height="54" rx="19" fill={`url(#face-${id})`} />
      <rect x="9" y="10" width="88" height="54" rx="19" fill={`url(#reflet-${id})`} />
      {/* yeux ovales verticaux, vers la droite de la face, reflet blanc en haut */}
      <ellipse cx="62" cy="33" rx="4.3" ry="7.6" fill="#0b0d16" />
      <ellipse cx="76" cy="32" rx="4.3" ry="7.6" fill="#0b0d16" />
      <ellipse cx="61" cy="29" rx="1.3" ry="2" fill="#ffffff" />
      <ellipse cx="75" cy="28" rx="1.3" ry="2" fill="#ffffff" />
    </svg>
  );
}
