import { turnoInicioFromApi } from './turnoDatetimeFromApi';
import { formatFecha, formatHora } from './dateFieldFormat';

describe('turnoInicioFromApi', () => {
  test('parsea ISO del API y formatea en local como en edición', () => {
    const d = turnoInicioFromApi('2025-06-15T14:30:00-03:00');
    expect(d).not.toBeNull();
    if (d) {
      expect(formatFecha(d)).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(formatHora(d)).toMatch(/^\d{2}:\d{2}$/);
    }
  });
});
