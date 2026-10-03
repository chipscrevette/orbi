/** Assemble des noms de classes en ignorant les valeurs vides. */
export function cx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}
