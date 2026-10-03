/** Mise en forme française des nombres, durées et dates affichés. */

const NOMBRES = new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 });
const DATES = new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

/** 6.2 → « 6,2 » */
export function formatDecimal(n: number, decimales: number): string {
  return n.toFixed(decimales).replace('.', ',');
}

/** 1985 → « 1 985 » (espace fine insécable). */
export function formatNombre(n: number): string {
  return NOMBRES.format(n);
}

/** Un nombre à une décimale au plus : 12 → « 12 », 15.9 → « 15,9 », 6.06 → « 6,1 ». */
export function formatCompact(n: number): string {
  const arrondi = Math.round(n * 10) / 10;
  return Number.isInteger(arrondi) ? String(arrondi) : formatDecimal(arrondi, 1);
}

/** Durée d'une réponse : « 6,2 s », « 56 s », « 2 min 01 s ». */
export function formatDuree(secondes: number): string {
  if (!Number.isFinite(secondes) || secondes < 0) return '—';
  if (secondes < 10) return `${formatDecimal(secondes, 1)} s`;
  const total = Math.round(secondes);
  if (total < 60) return `${total} s`;
  const minutes = Math.floor(total / 60);
  const reste = total % 60;
  return `${minutes} min ${String(reste).padStart(2, '0')} s`;
}

/** Durée d'une étape ou minuteur : toujours une décimale sous la minute (« 0,1 s », « 48,8 s »). */
export function formatDureeEtape(secondes: number): string {
  if (!Number.isFinite(secondes) || secondes < 0) return '—';
  // Arrondi vers le bas (un minuteur n'annonce pas un dixième pas encore écoulé), à l'erreur de calcul flottant près.
  if (secondes < 60) return `${formatDecimal(Math.floor(secondes * 10 + 1e-6) / 10, 1)} s`;
  return formatDuree(secondes);
}

/** « ~66 s » */
export function formatEnviron(secondes: number): string {
  return `~${Math.round(secondes)} s`;
}

/** « 6,1 / 12 Go » */
export function formatGo(utilise: number, total: number): string {
  return `${formatCompact(utilise)} / ${formatCompact(total)} Go`;
}

/** « 2026-10-02 » → « 2 oct. 2026 ». Une date illisible est rendue telle quelle. */
export function formatDateCourte(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  const date = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return Number.isNaN(date.getTime()) ? iso : DATES.format(date);
}

/** « 30 650 m² » */
export function formatSurface(m2: number): string {
  return `${formatNombre(m2)} m²`;
}

export function pluriel(n: number, singulier: string, plurielForme: string): string {
  return `${formatNombre(n)} ${n > 1 ? plurielForme : singulier}`;
}
