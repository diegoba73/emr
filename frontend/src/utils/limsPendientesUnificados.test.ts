import {
  estadosMicroDesdeFiltroLab,
  sortPedidosMasRecientesPrimero,
} from './limsPendientesUnificados';

describe('estadosMicroDesdeFiltroLab', () => {
  it('Todos no filtra microbiología', () => {
    expect(estadosMicroDesdeFiltroLab('')).toBeNull();
  });

  it('Finalizado de lab corresponde a validado/informado en micro', () => {
    expect(estadosMicroDesdeFiltroLab('FINALIZADO')).toEqual(['VALIDADO', 'INFORMADO']);
  });
});

describe('sortPedidosMasRecientesPrimero', () => {
  it('ordena de la última solicitada a la primera', () => {
    const rows = [
      { id: 1, fecha_solicitud: '2026-01-01T10:00:00Z' },
      { id: 2, fecha_solicitud: '2026-09-15T18:00:00Z' },
      { id: 3, fecha_solicitud: '2026-09-15T12:00:00Z' },
    ];
    expect(sortPedidosMasRecientesPrimero(rows).map((r) => r.id)).toEqual([2, 3, 1]);
  });

  it('pone sin fecha al final y desempata por id', () => {
    const rows = [
      { id: 1, fecha_solicitud: null },
      { id: 4, fecha_solicitud: '2026-09-15T12:00:00Z' },
      { id: 7, fecha_solicitud: '2026-09-15T12:00:00Z' },
    ];
    expect(sortPedidosMasRecientesPrimero(rows).map((r) => r.id)).toEqual([7, 4, 1]);
  });
});
