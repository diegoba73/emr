import {
  formatListaTubosPendientesRecepcion,
  labelTuboPendienteRecepcion,
} from './limsTubosRecepcion';

describe('limsTubosRecepcion', () => {
  it('label incluye código y estado', () => {
    expect(
      labelTuboPendienteRecepcion({
        id: 1,
        codigo_barra: 'LAB-2026-00870-02',
        tipo_contenedor_codigo: 'LILA',
        estado: 'PENDIENTE_TOMA',
      })
    ).toContain('LAB-2026-00870-02');
    expect(
      labelTuboPendienteRecepcion({
        id: 1,
        codigo_barra: 'LAB-2026-00870-02',
        tipo_contenedor_codigo: 'LILA',
        estado: 'PENDIENTE_TOMA',
      })
    ).toContain('pendiente de toma');
  });

  it('format lista une tubos', () => {
    const s = formatListaTubosPendientesRecepcion([
      { id: 1, codigo_barra: 'A-01', estado: 'TOMADA' },
      { id: 2, codigo_barra: 'A-02', estado: 'PENDIENTE_TOMA' },
    ]);
    expect(s).toContain('A-01');
    expect(s).toContain('A-02');
  });
});
