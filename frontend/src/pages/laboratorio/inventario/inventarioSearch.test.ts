import {
  filterConsumosBusqueda,
  filterInsumosBusqueda,
  filterLotesBusqueda,
  filterMovimientosBusqueda,
  filterPedidosBusqueda,
  filterReactivosBusqueda,
  matchesSearch,
} from './inventarioSearch';

describe('inventarioSearch', () => {
  it('matchesSearch ignora mayúsculas y vacíos', () => {
    expect(matchesSearch('', 'GLU')).toBe(true);
    expect(matchesSearch('glu', 'GLUCOSA')).toBe(true);
    expect(matchesSearch('xyz', 'GLU')).toBe(false);
  });

  it('filtra reactivos por código REF o nombre', () => {
    const rows = [
      { codigo: 'R-GLU', nombre: 'Glucosa', ref_comercial: '1008149', equipo_codigo: 'CM260' },
      { codigo: 'R-URE', nombre: 'Urea', ref_comercial: null, equipo_codigo: 'CM260' },
    ];
    expect(filterReactivosBusqueda(rows, '1008')).toHaveLength(1);
    expect(filterReactivosBusqueda(rows, 'urea')).toHaveLength(1);
    expect(filterReactivosBusqueda(rows, 'cm260')).toHaveLength(2);
  });

  it('filtra insumos, lotes, consumos, movimientos y pedidos', () => {
    expect(
      filterInsumosBusqueda(
        [{ codigo: 'T-EDTA', nombre: 'Tubo EDTA', tipo: 'TUBO' }],
        'edta'
      )
    ).toHaveLength(1);
    expect(
      filterLotesBusqueda(
        [{ codigo_lote: 'L1', insumo_codigo: 'R-GLU', insumo_nombre: 'Glucosa' }],
        'glu'
      )
    ).toHaveLength(1);
    expect(
      filterConsumosBusqueda(
        [{ tipo_examen_codigo: 'GLU', insumo_codigo: 'R-GLU', tipo_examen_nombre: 'Glucosa' }],
        'gluc'
      )
    ).toHaveLength(1);
    expect(
      filterMovimientosBusqueda(
        [{ tipo: 'CONSUMO', insumo_codigo: 'R-GLU', lote_codigo: 'L1', motivo: 'carga' }],
        'carga'
      )
    ).toHaveLength(1);
    expect(
      filterPedidosBusqueda([{ codigo: 'R-GLU', nombre: 'Glucosa', proveedor: 'Wiener' }], 'wiener')
    ).toHaveLength(1);
  });
});
