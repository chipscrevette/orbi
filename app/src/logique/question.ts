/** Le serveur refuse (HTTP 422) une question de moins de 3 ou de plus de 2000 caractères : on vérifie avant l'envoi. */

export const LONGUEUR_MIN_QUESTION = 3;
export const LONGUEUR_MAX_QUESTION = 2000;

export type Validation = { valide: true; question: string } | { valide: false; raison: string };

export function validerQuestion(brut: string): Validation {
  const question = brut.trim();
  if (question.length < LONGUEUR_MIN_QUESTION) {
    return { valide: false, raison: `Votre question doit faire au moins ${LONGUEUR_MIN_QUESTION} caractères.` };
  }
  if (question.length > LONGUEUR_MAX_QUESTION) {
    return {
      valide: false,
      raison: `Votre question fait ${question.length} caractères : ${LONGUEUR_MAX_QUESTION} au plus.`,
    };
  }
  return { valide: true, question };
}

/** Insère une adresse choisie sur la carte dans le brouillon de question. */
export function insererAdresse(brouillon: string, adresse: string): string {
  const texteActuel = brouillon.trimEnd();
  if (texteActuel === '') return `Au ${adresse}, `;
  return `${texteActuel} au ${adresse}`;
}
