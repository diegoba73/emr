import { formatFecha, formatFechaDisplay, formatHora } from './dateFieldFormat';

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

  test('formatFechaDisplay no atrasa un día en fechas solo-día', () => {
    // El bug: new Date('1973-09-01') → 31/08 en zonas UTC-.
    expect(formatFechaDisplay('1973-09-01')).toBe(
      new Date(1973, 8, 1).toLocaleDateString('es-AR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    );
  });

  test('formatFechaDisplay vacío', () => {
    expect(formatFechaDisplay('')).toBe('N/A');
    expect(formatFechaDisplay(null)).toBe('N/A');
  });
});
