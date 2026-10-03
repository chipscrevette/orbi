/** La légende, collée à la carte : la couleur à côté du code de zone, sans paragraphe à lire. */
import { FAMILLES } from '../../logique/zones.ts';
import { cx } from '../cx.ts';
import styles from './Legende.module.css';

export function Legende({ compacte = false }: { compacte?: boolean }) {
  return (
    <ul className={cx(styles.legende, compacte && styles.compacte)} aria-label="Légende des zones du PLU">
      {FAMILLES.map((f) => (
        <li key={f.cle} title={`${f.codes} : ${f.libelle}`}>
          <span className={styles.pastille} style={{ background: f.couleur }} aria-hidden="true" />
          <strong>{f.codes}</strong>
          {!compacte && <span className={styles.libelle}>{f.libelle}</span>}
        </li>
      ))}
    </ul>
  );
}
