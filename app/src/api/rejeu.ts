/** Rejoue un plan de démo avec de vrais minuteurs. Rend une fonction qui arrête le rejeu. */
import type { PlanRejeu } from '../logique/demo.ts';
import type { EvenementFlux } from '../logique/types.ts';

export function lancerRejeu(
  plan: PlanRejeu,
  surEvenement: (evenement: EvenementFlux) => void,
  surFin: () => void,
): () => void {
  const minuteurs = plan.evenements.map(({ a_s, evenement }) =>
    setTimeout(() => surEvenement(evenement), Math.round(a_s * 1000)),
  );
  minuteurs.push(setTimeout(surFin, Math.round(plan.duree_demo_s * 1000) + 1));
  return () => {
    for (const m of minuteurs) clearTimeout(m);
  };
}
