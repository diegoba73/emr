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
    const eab = grupos.find((g) => g.codigo === 'PAN_EAB_ART');
    const glu = grupos.find((g) => g.resultados[0]?.tipo_examen_codigo === 'GLU');
    expect(eab?.titulo).toBe('EAB arterial');
    expect(eab?.resultados).toHaveLength(3);
    expect(glu).toBeTruthy();
    // Orden formulario papel: Glucemia antes que EAB arterial
    expect(grupos.indexOf(glu!)).toBeLessThan(grupos.indexOf(eab!));
  });

  it('aplica orden_grupos_informe custom (reorden manual)', () => {
    const resultados = [res(1, 1), res(2, 4), res(3, 99)];
    const grupos = groupResultadosPorPanel(
      {
        ...orden,
        orden_grupos_informe: ['resultado-3', 'panel-11', 'panel-10'],
      },
      resultados
    );
    expect(grupos.map((g) => g.key)).toEqual(['resultado-3', 'panel-11', 'panel-10']);
  });

  it('clearance incluye CREATI y queda antes de orina completa', () => {
    const ordenClear: Pick<SolicitudExamenLims, 'paneles_resumen' | 'tipos_examen'> = {
      paneles_resumen: [
        {
          id: 20,
          codigo: 'PAN_CLEAR',
          nombre: 'Clearance de creatinina',
          tipos_examen_ids: [101, 102, 103, 104],
        },
        {
          id: 21,
          codigo: 'PAN_ORI',
          nombre: 'Orina completa',
          tipos_examen_ids: [201],
        },
      ],
      tipos_examen: [],
    };
    const resultados: ResultadoExamenLims[] = [
      {
        ...res(1, 101),
        tipo_examen_codigo: 'CREATI',
        tipo_examen_nombre: 'Creatininemia',
        tipo_examen_muestra_codigo: 'SUERO',
      },
      {
        ...res(2, 102),
        tipo_examen_codigo: 'CREA_U',
        tipo_examen_nombre: 'Creatininuria',
        tipo_examen_muestra_codigo: 'ORINA',
      },
      {
        ...res(3, 103),
        tipo_examen_codigo: 'DIUR',
        tipo_examen_nombre: 'Diuresis',
        tipo_examen_muestra_codigo: 'ORINA_24_H',
      },
      {
        ...res(4, 104),
        tipo_examen_codigo: 'CLEAR_CREA',
        tipo_examen_nombre: 'Clearance',
        tipo_examen_muestra_codigo: 'ORINA_24_H',
      },
      {
        ...res(5, 201),
        tipo_examen_codigo: 'ORI_PH',
        tipo_examen_nombre: 'pH',
        tipo_examen_muestra_codigo: 'ORINA',
      },
    ];
    const grupos = groupResultadosPorPanel(
      {
        ...ordenClear,
        orden_grupos_informe: ['panel-21', 'panel-20'],
      },
      resultados
    );
    expect(grupos[grupos.length - 1].codigo).toBe('PAN_ORI');
    const clear = grupos.find((g) => g.codigo === 'PAN_CLEAR');
    expect(clear?.resultados.map((r) => r.tipo_examen_codigo)).toEqual([
      'CREATI',
      'CREA_U',
      'DIUR',
      'CLEAR_CREA',
    ]);
    expect(grupos.indexOf(clear!)).toBeLessThan(
      grupos.indexOf(grupos.find((g) => g.codigo === 'PAN_ORI')!)
    );
  });
});
