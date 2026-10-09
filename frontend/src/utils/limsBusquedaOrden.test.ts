import { interpretarBusquedaOrden, interpretarNumeroOrden } from './limsBusquedaOrden';

describe('interpretarNumeroOrden', () => {
  it('vacío', () => {
    expect(interpretarNumeroOrden('')).toEqual({ tipo: 'vacio' });
    expect(interpretarNumeroOrden('   ')).toEqual({ tipo: 'vacio' });
  });

  it('secuencia corta → protocolo exacto del año en curso', () => {
    expect(interpretarNumeroOrden('130', 2026)).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00130',
    });
    expect(interpretarNumeroOrden('30', 2026)).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
    expect(interpretarNumeroOrden('00030', 2026)).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
  });

  it('año-secuencia → exacto con padding', () => {
    expect(interpretarNumeroOrden('2025-00130')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2025-00130',
    });
    expect(interpretarNumeroOrden('2026-30')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
  });

  it('LAB completo → exacto', () => {
    expect(interpretarNumeroOrden('LAB-2025-00042')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2025-00042',
    });
    expect(interpretarNumeroOrden('lab-2026-00030-01')).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
  });
});

describe('interpretarBusquedaOrden (compat)', () => {
  it('vacío', () => {
    expect(interpretarBusquedaOrden('')).toEqual({ tipo: 'vacio' });
  });

  it('números cortos → exacto año curso', () => {
    expect(interpretarBusquedaOrden('30', 2026)).toEqual({
      tipo: 'exacto',
      numero: 'LAB-2026-00030',
    });
  });

  it('texto / DNI libre', () => {
    expect(interpretarBusquedaOrden('García')).toEqual({ tipo: 'texto', q: 'García' });
    expect(interpretarBusquedaOrden('30111222')).toEqual({ tipo: 'texto', q: '30111222' });
  });
});
