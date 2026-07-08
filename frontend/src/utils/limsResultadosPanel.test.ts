import { groupResultadosPorPanel } from './limsResultadosPanel';
import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';

function res(id: number, tipo: number): ResultadoExamenLims {
  return {
    id,
    solicitud: 1,
    tipo_examen: tipo,
    valor_obtenido: '',
  };
}

describe('groupResultadosPorPanel', () => {
  const orden: Pick<SolicitudExamenLims, 'paneles_resumen' | 'tipos_examen'> = {
    paneles_resumen: [
      { id: 10, codigo: 'PAN_HEMO', nombre: 'Hemograma', tipos_examen_ids: [1, 2, 3] },
      { id: 11, codigo: 'PAN_IONO', nombre: 'Ionograma', tipos_examen_ids: [4, 5] },
    ],
    tipos_examen: [99],
  };

  it('ordena resultados según tipos_examen_ids del panel', () => {
    const resultados = [res(4, 2), res(1, 1), res(2, 3)];
    const grupos = groupResultadosPorPanel(orden, resultados);
    expect(grupos[0].resultados.map((r) => r.tipo_examen)).toEqual([1, 2, 3]);
  });

  it('agrupa por panel y deja sueltos al final', () => {
    const resultados = [res(1, 1), res(2, 4), res(3, 99), res(4, 2)];
    const grupos = groupResultadosPorPanel(orden, resultados);
    expect(grupos).toHaveLength(3);
    expect(grupos[0].titulo).toBe('Hemograma');
    expect(grupos[0].resultados.map((r) => r.id)).toEqual([1, 4]);
    expect(grupos[0].resultados.map((r) => r.tipo_examen)).toEqual([1, 2]);
    expect(grupos[1].titulo).toBe('Ionograma');
    expect(grupos[1].resultados.map((r) => r.id)).toEqual([2]);
    expect(grupos[2].key).toBe('resultado-3');
    expect(grupos[2].resultados.map((r) => r.id)).toEqual([3]);
  });

  it('sin paneles muestra un bloque por examen', () => {
    const grupos = groupResultadosPorPanel({ tipos_examen: [1] }, [res(1, 1), res(2, 2)]);
    expect(grupos).toHaveLength(2);
    expect(grupos[0].key).toBe('resultado-1');
    expect(grupos[1].key).toBe('resultado-2');
  });
});
