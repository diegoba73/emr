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

  it('infiere EAB arterial por códigos si no hay paneles_resumen', () => {
    const resultados: ResultadoExamenLims[] = [
      { ...res(1, 10), tipo_examen_codigo: 'PH_ART', tipo_examen_nombre: 'pH', valor_obtenido: '7.4' },
      { ...res(2, 11), tipo_examen_codigo: 'PO2_ART', tipo_examen_nombre: 'pO2', valor_obtenido: '90' },
      { ...res(3, 12), tipo_examen_codigo: 'PCO2_ART', tipo_examen_nombre: 'pCO2', valor_obtenido: '40' },
      { ...res(4, 99), tipo_examen_codigo: 'GLU', tipo_examen_nombre: 'Glucemia', valor_obtenido: '100' },
    ];
    const grupos = groupResultadosPorPanel({ tipos_examen: [] }, resultados);
    expect(grupos[0].codigo).toBe('PAN_EAB_ART');
    expect(grupos[0].titulo).toBe('EAB arterial');
    expect(grupos[0].resultados).toHaveLength(3);
    expect(grupos[1].resultados[0].tipo_examen_codigo).toBe('GLU');
  });
});
