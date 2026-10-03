import { describe, expect, it } from 'vitest';
import {
  formatCompact,
  formatDateCourte,
  formatDuree,
  formatDureeEtape,
  formatEnviron,
  formatGo,
  formatNombre,
  formatSurface,
  pluriel,
} from '../../src/logique/format.ts';

describe('formats français', () => {
  it('écrit les durées de réponse', () => {
    expect(formatDuree(6.2)).toBe('6,2 s');
    expect(formatDuree(56.2)).toBe('56 s');
    expect(formatDuree(59.6)).toBe('1 min 00 s');
    expect(formatDuree(120.5)).toBe('2 min 01 s');
    expect(formatDuree(Number.NaN)).toBe('—');
    expect(formatDuree(-1)).toBe('—');
  });

  it('écrit les durées d’étape avec une décimale, sans erreur d’arrondi flottant', () => {
    expect(formatDureeEtape(7.3 - 7.2)).toBe('0,1 s');
    expect(formatDureeEtape(56.1 - 7.3)).toBe('48,8 s');
    expect(formatDureeEtape(0)).toBe('0,0 s');
    expect(formatDureeEtape(23.46)).toBe('23,4 s');
    expect(formatDureeEtape(114.1)).toBe('1 min 54 s');
  });

  it('écrit les jauges', () => {
    expect(formatGo(6.1, 12)).toBe('6,1 / 12 Go');
    expect(formatGo(15.0, 15.9)).toBe('15 / 15,9 Go');
    expect(formatEnviron(65.6)).toBe('~66 s');
    expect(formatCompact(6.06)).toBe('6,1');
  });

  it('écrit les nombres, surfaces et dates', () => {
    expect(formatNombre(1985)).toBe('1 985');
    expect(formatSurface(30650)).toBe('30 650 m²');
    expect(formatDateCourte('2026-10-02')).toBe('2 oct. 2026');
    expect(formatDateCourte('hier')).toBe('hier');
    expect(pluriel(1, 'zone', 'zones')).toBe('1 zone');
    expect(pluriel(178, 'zone', 'zones')).toBe('178 zones');
  });
});
