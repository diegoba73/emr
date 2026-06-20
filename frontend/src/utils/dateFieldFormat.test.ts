import { formatFecha, formatHora } from './dateFieldFormat';

describe('dateFieldFormat', () => {
  test('formatFecha YYYY-MM-DD local', () => {
    const d = new Date(2025, 2, 5, 10, 0, 0);
    expect(formatFecha(d)).toBe('2025-03-05');
  });

  test('formatHora HH:mm con padding', () => {
    const d = new Date(2025, 2, 5, 9, 7, 0);
    expect(formatHora(d)).toBe('09:07');
  });

  test('fecha/hora desde mismo instante que slot de calendario', () => {
    const start = new Date(2025, 7, 20, 10, 0, 0);
    expect(formatFecha(start)).toBe('2025-08-20');
    expect(formatHora(start)).toBe('10:00');
  });
});
