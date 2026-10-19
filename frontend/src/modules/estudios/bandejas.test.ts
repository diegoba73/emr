import { BANDEJA_OPTIONS, MODULO_ESTUDIOS_LABEL, emptyBandejasResumen } from './bandejas';

describe('bandejas A5', () => {
  it('expone todas las bandejas de la matriz y Todos', () => {
    const keys = BANDEJA_OPTIONS.map((o) => o.key);
    expect(keys).toEqual([
      'todos',
      'pendiente_programar',
      'programados',
      'documentacion_pendiente',
      'pendiente_entrega',
      'finalizados',
      'anulados',
    ]);
  });

  it('nombre de módulo visible', () => {
    expect(MODULO_ESTUDIOS_LABEL).toBe('Estudios y procedimientos');
  });

  it('resumen vacío tiene las mismas claves', () => {
    expect(Object.keys(emptyBandejasResumen()).sort()).toEqual(
      BANDEJA_OPTIONS.map((o) => o.key).sort()
    );
  });
});
