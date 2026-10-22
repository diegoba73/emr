import {
  clinicoDesdeEquipoCreatinuria,
  equipoDesdeClinicoCreatinuria,
  esCreatininuria,
  formatCreatinuriaNumero,
} from './creatinuriaDilucion';
import {
  draftCreatinuriaDesdeResultado,
  draftValorClinicoNumerico,
  resultadoDebeGuardarse,
  type DraftCargaRow,
} from './limsCargaMuestra';
import type { ResultadoExamenLims } from '../types/lims';

describe('creatinuriaDilucion', () => {
  it('reconoce CREA_U y convierte CM260 ↔ clínico', () => {
    expect(esCreatininuria('crea_u')).toBe(true);
    expect(clinicoDesdeEquipoCreatinuria(5)).toBe(100);
    expect(equipoDesdeClinicoCreatinuria(100)).toBe(5);
    expect(formatCreatinuriaNumero(5.2)).toBe('5.2');
  });

  it('draft desde resultado muestra valor de equipo si dilución activa', () => {
    const r = {
      valor_obtenido: '100',
      valor_numerico: 100,
      tipo_examen_codigo: 'CREA_U',
    };
    expect(draftCreatinuriaDesdeResultado(r, true)).toEqual({
      valor: '5',
      valor_numerico: '5',
    });
    expect(draftCreatinuriaDesdeResultado(r, false).valor).toBe('100');
  });

  it('no marca dirty si el borrador es el CM260 del clínico guardado', () => {
    const r = {
      id: 1,
      tipo_examen: 10,
      tipo_examen_codigo: 'CREA_U',
      valor_obtenido: '100',
      valor_numerico: 100,
    } as ResultadoExamenLims;
    const row: DraftCargaRow = {
      valor: '5',
      valor_sysmex: '',
      valor_numerico: '5',
      unidad: 'mg/dL',
      muestra_id: null,
    };
    expect(resultadoDebeGuardarse(r, row, null, { dilucionCreatinuria: true })).toBe(false);
    expect(
      resultadoDebeGuardarse(r, { ...row, valor: '6', valor_numerico: '6' }, null, {
        dilucionCreatinuria: true,
      })
    ).toBe(true);
  });

  it('draftValorClinicoNumerico aplica ×20 para derivados', () => {
    const r = {
      id: 1,
      tipo_examen: 10,
      tipo_examen_codigo: 'CREA_U',
      valor_obtenido: '',
      valor_numerico: null,
    } as ResultadoExamenLims;
    const draft = {
      1: {
        valor: '5',
        valor_sysmex: '',
        valor_numerico: '5',
        unidad: '',
        muestra_id: null,
      },
    };
    const catalog = new Map();
    expect(draftValorClinicoNumerico(r, draft, catalog, { dilucionCreatinuria: true })).toBe(100);
    expect(draftValorClinicoNumerico(r, draft, catalog, { dilucionCreatinuria: false })).toBe(5);
  });
});
