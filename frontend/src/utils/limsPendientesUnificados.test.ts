import {
  estadosMicroDesdeFiltroLab,
  sortPedidosPorNumero,
} from './limsPendientesUnificados';

describe('estadosMicroDesdeFiltroLab', () => {
  it('Todos no filtra microbiología', () => {
    expect(estadosMicroDesdeFiltroLab('')).toBeNull();
  });

  it('Finalizado de lab corresponde a validado/informado en micro', () => {
    expect(estadosMicroDesdeFiltroLab('FINALIZADO')).toEqual(['VALIDADO', 'INFORMADO']);
  });
});

describe('sortPedidosPorNumero', () => {
  it('ordena solo por numero ascendente', () => {
    const rows = [
      { id: 1, numero: 'LAB-2026-00001' },
      { id: 2, numero: 'LAB-2026-00010' },
      { id: 3, numero: 'LAB-2026-00002' },
    ];
    expect(sortPedidosPorNumero(rows).map((r) => r.numero)).toEqual([
      'LAB-2026-00001',
      'LAB-2026-00002',
      'LAB-2026-00010',
    ]);
  });

  it('pone sin numero al final', () => {
    const rows = [
      { id: 1, numero: null },
      { id: 4, numero: 'LAB-2026-00005' },
      { id: 7, numero: 'LAB-2026-00003' },
    ];
    expect(sortPedidosPorNumero(rows).map((r) => r.id)).toEqual([7, 4, 1]);
  });
});
