import {
  MATERIALES_PEDIDO_FALLBACK,
  materialCodigoParaCultivo,
  materialesPedidoEfectivos,
  resolverMaterialesSeleccionados,
} from './limsMaterialesPedidoCatalog';

describe('limsMaterialesPedidoCatalog', () => {
  it('usa API cuando hay filas y fallback si viene vacía', () => {
    const api = [{ ...MATERIALES_PEDIDO_FALLBACK[0], nombre: 'Sangre API' }];
    expect(materialesPedidoEfectivos(api)[0].nombre).toBe('Sangre API');
    expect(materialesPedidoEfectivos([])).toBe(MATERIALES_PEDIDO_FALLBACK);
    expect(materialesPedidoEfectivos(null)).toBe(MATERIALES_PEDIDO_FALLBACK);
  });

  it('resuelve SANGRE desde códigos aunque solo exista en fallback', () => {
    const mats = resolverMaterialesSeleccionados(
      ['SANGRE'],
      MATERIALES_PEDIDO_FALLBACK
    );
    expect(mats).toHaveLength(1);
    expect(mats[0].cultivo_micro_codigo).toBe('HEMOCULTIVO');
  });

  it('asocia HEMOCULTIVO → SANGRE para armar el pedido micro', () => {
    expect(
      materialCodigoParaCultivo('HEMOCULTIVO', MATERIALES_PEDIDO_FALLBACK)
    ).toBe('SANGRE');
    expect(
      materialCodigoParaCultivo('hemocultivo', MATERIALES_PEDIDO_FALLBACK)
    ).toBe('SANGRE');
    expect(materialCodigoParaCultivo('UROCULTIVO', MATERIALES_PEDIDO_FALLBACK)).toBe(
      'ORINA'
    );
    expect(materialCodigoParaCultivo('NOEXISTE', MATERIALES_PEDIDO_FALLBACK)).toBe(
      ''
    );
  });

  it('no pierde material seleccionado si el diálogo solo tenía API vacía', () => {
    // Simula el bug: códigos del form + catálogo efectivo (fallback).
    const seleccionados = resolverMaterialesSeleccionados(
      ['SANGRE'],
      materialesPedidoEfectivos([])
    );
    expect(materialCodigoParaCultivo('HEMOCULTIVO', seleccionados)).toBe('SANGRE');
  });
});
