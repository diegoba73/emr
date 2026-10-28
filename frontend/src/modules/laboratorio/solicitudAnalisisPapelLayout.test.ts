import {
  SOLICITUD_ANALISIS_PAPEL_ROWS,
  buildCatalogMaps,
  esExamenExcluidoDeLabClinico,
  esExamenMicrobiologiaCatalogo,
  resolvePapelItemId,
} from './solicitudAnalisisPapelLayout';

describe('solicitudAnalisisPapelLayout', () => {
  it('tiene filas en dos columnas con orden operativo de Sangre', () => {
    expect(SOLICITUD_ANALISIS_PAPEL_ROWS.length).toBe(25);
    const withLeft = SOLICITUD_ANALISIS_PAPEL_ROWS.filter((r) => r.left).length;
    const withRight = SOLICITUD_ANALISIS_PAPEL_ROWS.filter((r) => r.right).length;
    expect(withLeft).toBe(25);
    expect(withRight).toBe(25);
    expect(SOLICITUD_ANALISIS_PAPEL_ROWS[0].left?.codigo).toBe('PAN_HEMO');
    expect(SOLICITUD_ANALISIS_PAPEL_ROWS[0].right?.codigo).toBe('CPK');
    expect(SOLICITUD_ANALISIS_PAPEL_ROWS[24].left?.codigo).toBe('LDH');
    expect(SOLICITUD_ANALISIS_PAPEL_ROWS[24].right?.codigo).toBe('LACT');
  });

  it('resuelve ids de catálogo por código', () => {
    const maps = buildCatalogMaps(
      [{ id: 10, codigo: 'PAN_HEMO', nombre: 'Hemograma' }],
      [{ id: 20, codigo: 'CPK', nombre: 'CPK' }]
    );
    expect(resolvePapelItemId({ kind: 'panel', codigo: 'PAN_HEMO' }, maps)).toBe(10);
    expect(resolvePapelItemId({ kind: 'examen', codigo: 'CPK' }, maps)).toBe(20);
  });

  it('excluye determinaciones de microbiología del pedido clínico', () => {
    expect(
      esExamenMicrobiologiaCatalogo({ codigo: 'OMCULT', nombre: 'Urocultivo' })
    ).toBe(true);
    expect(
      esExamenMicrobiologiaCatalogo({
        codigo: 'OPSCUL',
        nombre: 'Urocultivo por punción de sonda',
      })
    ).toBe(true);
    expect(
      esExamenMicrobiologiaCatalogo({
        codigo: 'HEMACUL1',
        nombre: 'Hemocultivo automatizado - muestra 1',
      })
    ).toBe(true);
    expect(
      esExamenMicrobiologiaCatalogo({
        codigo: 'ATBGGC1',
        nombre: 'Antibiograma Gram y cultivo germenes comunes 1',
      })
    ).toBe(true);
    expect(esExamenExcluidoDeLabClinico({ codigo: 'GLU', nombre: 'Glucemia' })).toBe(false);
    expect(
      esExamenExcluidoDeLabClinico({
        codigo: 'MICROALB_24',
        nombre: 'Microalbuminuria 24 hs',
      })
    ).toBe(false);
  });
});
