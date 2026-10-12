import {
  estadosMicroDesdeFiltroLab,
  mapMicroToPendiente,
  sortPedidosPorNumero,
} from './limsPendientesUnificados';
import type { EstudioMicrobiologia } from '../types/lims';

describe('estadosMicroDesdeFiltroLab', () => {
  it('Todos no filtra microbiología', () => {
    expect(estadosMicroDesdeFiltroLab('')).toBeNull();
  });

  it('Finalizado de lab corresponde a validado/informado en micro', () => {
    expect(estadosMicroDesdeFiltroLab('FINALIZADO')).toEqual(['VALIDADO', 'INFORMADO']);
  });
});

describe('mapMicroToPendiente extracción', () => {
  const base = {
    id: 50,
    numero: 'LAB-2026-00050',
    paciente: 1,
    paciente_nombre: 'EVANS, LORENA',
    estado: 'PENDIENTE',
    created_at: '2026-10-10T20:34:41.564719-03:00',
    fecha_programada_toma: '2026-10-10',
    fecha_inicio: null,
  } as EstudioMicrobiologia;

  it('PENDIENTE sin recepción no muestra Extracción (ni created_at)', () => {
    const row = mapMicroToPendiente(base);
    expect(row.fecha_toma_muestra).toBeNull();
  });

  it('solo tras RECIBIDO con fecha_inicio', () => {
    const row = mapMicroToPendiente({
      ...base,
      estado: 'RECIBIDO',
      fecha_inicio: '2026-10-10T21:00:00-03:00',
    });
    expect(row.fecha_toma_muestra).toBe('2026-10-10T21:00:00-03:00');
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
