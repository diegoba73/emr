import { interpretarBusquedaOrden } from './limsBusquedaOrden';

describe('interpretarBusquedaOrden', () => {
  it('vacío', () => {
    expect(interpretarBusquedaOrden('')).toEqual({ tipo: 'vacio' });
    expect(interpretarBusquedaOrden('   ')).toEqual({ tipo: 'vacio' });
  });

  it('secuencia corta → año en curso', () => {
    expect(interpretarBusquedaOrden('30', 2026)).toEqual({
      tipo: 'secuencia_anio',
      anio: 2026,
      secuencia: '30',
    });
    expect(interpretarBusquedaOrden('00030', 2026)).toEqual({
      tipo: 'secuencia_anio',
      anio: 2026,
      secuencia: '00030',
    });
  });

  it('año-secuencia → exacto con padding', () => {
    expect(interpretarBusquedaOrden('2026-00030')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
    expect(interpretarBusquedaOrden('2026-30')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
  });

  it('LAB completo → exacto', () => {
    expect(interpretarBusquedaOrden('LAB-2025-00042')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2025-00042',
    });
    expect(interpretarBusquedaOrden('lab-2026-00030-01')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
  });

  it('texto / DNI libre (más de 5 dígitos no es secuencia de protocolo)', () => {
    expect(interpretarBusquedaOrden('García')).toEqual({ tipo: 'texto', q: 'García' });
    expect(interpretarBusquedaOrden('30111222')).toEqual({ tipo: 'texto', q: '30111222' });
  });
});
