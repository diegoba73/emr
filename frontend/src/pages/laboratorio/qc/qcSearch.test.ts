import {
  filterCalibracionesBusqueda,
  filterCorridasBusqueda,
  filterEquiposBusqueda,
  filterEquiposHoyBusqueda,
  filterMaterialesQcBusqueda,
  filterProductosQcBusqueda,
} from './qcSearch';

describe('qcSearch', () => {
  it('filtra corridas por producto o lote', () => {
    const rows = [
      { producto_nombre: 'Standatrol', lote_codigo: 'ST-1', estado: 'ACEPTADA', nivel: 'N1' },
      { material_nombre: 'Control TSH', lote_codigo: 'TSH-9', estado: 'RECHAZADA', nivel: 'N2' },
    ];
    expect(filterCorridasBusqueda(rows, 'standa')).toHaveLength(1);
    expect(filterCorridasBusqueda(rows, 'tsh')).toHaveLength(1);
    expect(filterCorridasBusqueda(rows, 'aceptada')).toHaveLength(1);
  });

  it('filtra productos, materiales, equipos y calibraciones', () => {
    expect(
      filterProductosQcBusqueda(
        [{ codigo: 'STAND', nombre: 'Standatrol', marca: 'Wiener', equipo_codigo: 'CM260' }],
        'cm260'
      )
    ).toHaveLength(1);
    expect(
      filterMaterialesQcBusqueda(
        [
          {
            nombre: 'Control TSH',
            tipo_examen_codigo: 'TSH',
            tipo_examen_nombre: 'TSH',
            nivel: 'N1',
            equipo_codigo: 'VIDAS_KUBE',
          },
        ],
        'vidas'
      )
    ).toHaveLength(1);
    expect(
      filterEquiposBusqueda([{ codigo: 'CM260', nombre: 'Mindray', marca_modelo: 'BS' }], 'mind')
    ).toHaveLength(1);
    expect(
      filterCalibracionesBusqueda(
        [{ equipo_codigo: 'CM260', calibrador_nombre: 'A Plus', codigo_lote: 'AP-1' }],
        'a plus'
      )
    ).toHaveLength(1);
  });

  it('filtra tablero hoy por equipo o ensayo', () => {
    const rows = [
      {
        codigo: 'CM260',
        nombre: 'Química',
        lote_codigo: 'ST-1',
        ensayos_hoy: [{ codigo: 'GLU' }],
        ensayos: [],
      },
      {
        codigo: 'VIDAS_KUBE',
        nombre: 'VIDAS',
        ensayos: [{ codigo: 'TSH', nombre: 'TSH' }],
        ensayos_hoy: [],
      },
    ];
    expect(filterEquiposHoyBusqueda(rows, 'glu')).toHaveLength(1);
    expect(filterEquiposHoyBusqueda(rows, 'tsh')).toHaveLength(1);
    expect(filterEquiposHoyBusqueda(rows, 'cm')).toHaveLength(1);
  });
});
