import { buildCargaFocusOrder } from './CargaResultadosLims';
import type { LimsTipoExamen, ResultadoExamenLims } from '../../types/lims';
import type { GrupoResultadosOrden } from '../../utils/limsResultadosPanel';

function te(
  id: number,
  codigo: string,
  modo: LimsTipoExamen['modo_entrada'] = 'ESTANDAR'
): LimsTipoExamen {
  return {
    id,
    codigo,
    nombre: codigo,
    tipo_muestra_requerida: 1,
    modo_entrada: modo,
  };
}

function res(id: number, tipoId: number, codigo: string): ResultadoExamenLims {
  return {
    id,
    tipo_examen: tipoId,
    tipo_examen_codigo: codigo,
    tipo_examen_nombre: codigo,
  } as ResultadoExamenLims;
}

describe('buildCargaFocusOrder', () => {
  it('tras monocitos va a sugerir-conclusión y luego al próximo panel (no observaciones)', () => {
    const map = new Map<number, LimsTipoExamen>([
      [1, te(1, 'LEUCO', 'TICKET_ENTERO')],
      [2, te(2, 'MONO', 'FORMULA_PORCENTAJE')],
      [3, te(3, 'PH_ART')],
      [4, te(4, 'PO2_ART')],
      [5, te(5, 'HCO3_ART')],
    ]);
    const grupos: GrupoResultadosOrden[] = [
      {
        key: 'hemo',
        titulo: 'Hemograma',
        codigo: 'PAN_HEMO',
        resultados: [res(10, 1, 'LEUCO'), res(11, 2, 'MONO')],
      },
      {
        key: 'eab',
        titulo: 'EAB arterial',
        codigo: 'PAN_EAB_ART',
        resultados: [res(20, 3, 'PH_ART'), res(21, 4, 'PO2_ART'), res(22, 5, 'HCO3_ART')],
      },
    ];

    const order = buildCargaFocusOrder(grupos, map);

    expect(order).toEqual([
      'sysmex-10',
      'sysmex-11',
      'sugerir-conclusion',
      'valor-20',
      'valor-21',
      'valor-22',
      'observaciones',
    ]);
    const monoIdx = order.indexOf('sysmex-11');
    expect(order[monoIdx + 1]).toBe('sugerir-conclusion');
    expect(order[monoIdx + 2]).toBe('valor-20');
  });

  it('al terminar gases pasa al próximo examen, no vuelve al primero del mismo panel', () => {
    const map = new Map<number, LimsTipoExamen>([
      [1, te(1, 'PH_ART')],
      [2, te(2, 'PO2_ART')],
      [3, te(3, 'BE_ART')],
      [4, te(4, 'NA')],
      [5, te(5, 'K')],
    ]);
    const grupos: GrupoResultadosOrden[] = [
      {
        key: 'eab',
        titulo: 'EAB arterial',
        codigo: 'PAN_EAB_ART',
        resultados: [res(1, 1, 'PH_ART'), res(2, 2, 'PO2_ART'), res(3, 3, 'BE_ART')],
      },
      {
        key: 'iono',
        titulo: 'Ionograma',
        codigo: 'PAN_IONO',
        resultados: [res(4, 4, 'NA'), res(5, 5, 'K')],
      },
    ];

    const order = buildCargaFocusOrder(grupos, map);
    const lastGas = order.indexOf('valor-3');
    expect(order[lastGas + 1]).toBe('valor-4');
    expect(order[0]).toBe('valor-1');
    expect(order[lastGas + 1]).not.toBe(order[0]);
  });

  it('omite calculados del recorrido Enter', () => {
    const map = new Map<number, LimsTipoExamen>([
      [1, te(1, 'COL_TOT')],
      [2, te(2, 'LDL', 'CALCULADO')],
      [3, te(3, 'TG')],
    ]);
    const grupos: GrupoResultadosOrden[] = [
      {
        key: 'lip',
        titulo: 'Lípidos',
        codigo: 'PAN_LIP',
        resultados: [res(1, 1, 'COL_TOT'), res(2, 2, 'LDL'), res(3, 3, 'TG')],
      },
    ];
    expect(buildCargaFocusOrder(grupos, map)).toEqual([
      'valor-1',
      'valor-3',
      'observaciones',
    ]);
  });
});
