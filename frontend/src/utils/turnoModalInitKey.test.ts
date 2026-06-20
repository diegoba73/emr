import { getTurnoModalFormInitKey } from './turnoModalInitKey';

describe('getTurnoModalFormInitKey', () => {
  test('cerrado → clave vacía', () => {
    expect(getTurnoModalFormInitKey(false, null, null)).toBe('');
  });

  test('edición → edit:id', () => {
    expect(getTurnoModalFormInitKey(true, 42, new Date())).toBe('edit:42');
    expect(getTurnoModalFormInitKey(true, 42, null)).toBe('edit:42');
  });

  test('creación con slot → create:timestamp', () => {
    const d = new Date(2025, 5, 10, 10, 0, 0);
    expect(getTurnoModalFormInitKey(true, null, d)).toBe(`create:${d.getTime()}`);
  });

  test('creación vacía → new-empty', () => {
    expect(getTurnoModalFormInitKey(true, null, null)).toBe('new-empty');
  });

  test('mismo instante distinta referencia Date → misma clave', () => {
    const t = new Date(2025, 0, 1, 14, 30, 0).getTime();
    expect(getTurnoModalFormInitKey(true, null, new Date(t))).toBe(
      getTurnoModalFormInitKey(true, null, new Date(t))
    );
  });
});
