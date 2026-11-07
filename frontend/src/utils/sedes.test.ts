import { userHasCapacidad, userSedesEfectivas } from './sedes';

describe('sedes helpers', () => {
  it('sedes vacías = sin filtro y todas las capacidades', () => {
    const u = { rol: 'secretaria', sedes: [] as string[] };
    expect(userSedesEfectivas(u)).toBeNull();
    expect(userHasCapacidad(u, 'guardia')).toBe(true);
    expect(userHasCapacidad(u, 'internacion')).toBe(true);
  });

  it('CEHTA sin guardia; internación solo lectura', () => {
    const u = { rol: 'secretaria', sedes: ['CEHTA'] };
    expect(userSedesEfectivas(u)).toEqual(['CEHTA']);
    expect(userHasCapacidad(u, 'guardia')).toBe(false);
    expect(userHasCapacidad(u, 'internacion')).toBe(true);
    expect(userHasCapacidad(u, 'internacion_escritura')).toBe(false);
  });

  it('ICPL con guardia e internación completa', () => {
    const u = { rol: 'secretaria', sedes: ['ICPL'] };
    expect(userHasCapacidad(u, 'guardia')).toBe(true);
    expect(userHasCapacidad(u, 'internacion')).toBe(true);
    expect(userHasCapacidad(u, 'internacion_escritura')).toBe(true);
  });

  it('admin ignora sedes', () => {
    const u = { rol: 'admin', sedes: ['CEHTA'] };
    expect(userSedesEfectivas(u)).toBeNull();
    expect(userHasCapacidad(u, 'guardia')).toBe(true);
  });
});
