import {
  SOLICITUD_ANALISIS_PAPEL_ROWS,
  buildCatalogMaps,
  resolvePapelItemId,
} from './solicitudAnalisisPapelLayout';

describe('solicitudAnalisisPapelLayout', () => {
  it('tiene filas en dos columnas', () => {
    expect(SOLICITUD_ANALISIS_PAPEL_ROWS.length).toBeGreaterThan(20);
    const withLeft = SOLICITUD_ANALISIS_PAPEL_ROWS.filter((r) => r.left).length;
    const withRight = SOLICITUD_ANALISIS_PAPEL_ROWS.filter((r) => r.right).length;
    expect(withLeft).toBeGreaterThan(10);
    expect(withRight).toBeGreaterThan(10);
  });

  it('resuelve ids de catálogo por código', () => {
    const maps = buildCatalogMaps(
      [{ id: 10, codigo: 'PAN_HEMO', nombre: 'Hemograma' }],
      [{ id: 20, codigo: 'CPK', nombre: 'CPK' }]
    );
    expect(resolvePapelItemId({ kind: 'panel', codigo: 'PAN_HEMO' }, maps)).toBe(10);
    expect(resolvePapelItemId({ kind: 'examen', codigo: 'CPK' }, maps)).toBe(20);
  });
});
