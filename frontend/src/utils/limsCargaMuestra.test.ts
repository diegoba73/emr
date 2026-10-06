import {
  applyAutofillVcmChcm,
  buildCargarResultadoPayload,
  draftRowClearsServerValue,
  filterMuestrasProcesables,
  muestrasCompatiblesParaTipo,
  resultadoDebeGuardarse,
  resultadoPuedeOmitirseSinMuestra,
  suggestMuestraIdForResultado,
  validateCargaResultadosMuestra,
  type DraftCargaRow,
} from './limsCargaMuestra';
import { RESULTADO_NO_CALCULABLE } from './calculosDerivados';
import type { LimsTipoExamen, MuestraTransaccional, ResultadoExamenLims } from '../types/lims';

const draftRow = (muestra_id: number | null): DraftCargaRow => ({
  valor: '10',
  valor_sysmex: '',
  valor_numerico: '',
  unidad: '',
  muestra_id,
});

const muestra = (id: number, tipo: number, estado: string): MuestraTransaccional =>
  ({
    id,
    solicitud: 1,
    paciente: 1,
    tipo_muestra: tipo,
    estado,
    codigo_barra: null,
  }) as MuestraTransaccional;

const resultado = (id: number, tipoExamen: number): ResultadoExamenLims =>
  ({
    id,
    solicitud: 1,
    tipo_examen: tipoExamen,
    tipo_examen_nombre: 'Glucosa',
    valor_obtenido: '',
  }) as ResultadoExamenLims;

const tipoExamen = (id: number, req: boolean, tipoMuestra: number): LimsTipoExamen =>
  ({
    id,
    codigo: 'GLU',
    nombre: 'Glucosa',
    tipo_muestra_requerida: tipoMuestra,
    requiere_muestra: req,
  }) as LimsTipoExamen;

describe('limsCargaMuestra', () => {
  it('filtra muestras procesables', () => {
    const list = [
      muestra(1, 1, 'RECIBIDA'),
      muestra(2, 1, 'TOMADA'),
      muestra(3, 1, 'CONSERVADA'),
      muestra(4, 1, 'EN_PROCESO'),
    ];
    expect(filterMuestrasProcesables(list).map((m) => m.id)).toEqual([1, 2, 3, 4]);
  });

  it('requiere_muestra sin muestra bloquea validación', () => {
    const cat = new Map([[10, tipoExamen(10, true, 1)]]);
    const err = validateCargaResultadosMuestra(
      [resultado(1, 10)],
      { 1: draftRow(null) },
      cat,
      []
    );
    expect(err).toMatch(/requiere una muestra/i);
  });

  it('examen CALCULADO no exige muestra aunque requiere_muestra sea true', () => {
    const clear = {
      ...tipoExamen(20, true, 1),
      codigo: 'CLEAR_CREA',
      nombre: 'Clearance de creatinina',
      modo_entrada: 'CALCULADO' as const,
    };
    const cat = new Map([[20, clear]]);
    const res = {
      ...resultado(2, 20),
      tipo_examen_nombre: 'Clearance de creatinina',
      tipo_examen_codigo: 'CLEAR_CREA',
    };
    const err = validateCargaResultadosMuestra(
      [res],
      { 2: draftRow(null) },
      cat,
      []
    );
    expect(err).toBeNull();
  });

  it('payload incluye muestra_id solo si está seleccionado', () => {
    const withM = buildCargarResultadoPayload(1, draftRow(5));
    const without = buildCargarResultadoPayload(2, draftRow(null));
    expect(withM.muestra_id).toBe(5);
    expect(without.muestra_id).toBeUndefined();
  });

  it('tipo no obligatorio sin muestra pasa validación', () => {
    const cat = new Map([[10, tipoExamen(10, false, 1)]]);
    const err = validateCargaResultadosMuestra(
      [resultado(1, 10)],
      { 1: draftRow(null) },
      cat,
      []
    );
    expect(err).toBeNull();
  });

  it('muestra incompatible con tipo requerido bloquea', () => {
    const cat = new Map([[10, tipoExamen(10, false, 1)]]);
    const err = validateCargaResultadosMuestra(
      [resultado(1, 10)],
      { 1: draftRow(99) },
      cat,
      [muestra(99, 2, 'RECIBIDA')]
    );
    expect(err).toMatch(/no corresponde al tipo requerido/i);
  });

  it('payload deriva valor_numerico desde Valor si es número', () => {
    const row: DraftCargaRow = {
      ...draftRow(null),
      valor: '120.5',
      valor_numerico: '',
    };
    const payload = buildCargarResultadoPayload(1, row);
    expect(payload.valor).toBe('120.5');
    expect(payload.valor_numerico).toBe(120.5);
  });

  it('payload no fuerza valor_numerico en texto cualitativo', () => {
    const row: DraftCargaRow = {
      ...draftRow(null),
      valor: 'Positivo',
      valor_numerico: '',
    };
    const payload = buildCargarResultadoPayload(1, row);
    expect(payload.valor).toBe('Positivo');
    expect(payload.valor_numerico).toBeUndefined();
  });

  it('payload sysmex convierte ticket hemograma', () => {
    const row: DraftCargaRow = {
      ...draftRow(null),
      valor: '',
      valor_sysmex: '93',
    };
    const payload = buildCargarResultadoPayload(1, row, { id: 0, codigo: 'LEUCO', nombre: 'LEUCO', tipo_muestra_requerida: 0, modo_entrada: 'ESTANDAR' }, 'LEUCO');
    expect(payload.valor_sysmex).toBe('93');
    expect(payload.valor).toBe('9300');
    expect(payload.valor_numerico).toBe(9300);
    expect(payload.unidad).toBe('/mm³');
  });

  it('payload sysmex fórmula cayados 70 queda 70', () => {
    const row: DraftCargaRow = {
      ...draftRow(null),
      valor: '',
      valor_sysmex: '70',
    };
    const payload = buildCargarResultadoPayload(
      1,
      row,
      { id: 0, codigo: 'NEUT_CAY', nombre: 'NEUT_CAY', tipo_muestra_requerida: 0, modo_entrada: 'ESTANDAR' },
      'NEUT_CAY'
    );
    expect(payload.valor).toBe('70');
    expect(payload.valor_numerico).toBe(70);
    expect(payload.unidad).toBe('%');
  });

  it('prefiltra muestras por tipo requerido', () => {
    const proc = [muestra(1, 1, 'RECIBIDA'), muestra(2, 2, 'EN_PROCESO')];
    expect(muestrasCompatiblesParaTipo(proc, 1).map((m) => m.id)).toEqual([1]);
  });

  it('prioriza tubos del tipo_contenedor del examen', () => {
    const proc = [
      muestra(1, 1, 'TOMADA'),
      { ...muestra(2, 1, 'TOMADA'), tipo_contenedor: 99 },
    ] as MuestraTransaccional[];
    expect(muestrasCompatiblesParaTipo(proc, 1, 99).map((m) => m.id)).toEqual([2]);
  });

  it('mismo contenedor HEPARINA distingue material art vs ven', () => {
    const proc = [
      {
        ...muestra(1, 10, 'RECIBIDA'),
        tipo_muestra_codigo: 'SANGRE_HEPARINA_ART',
        tipo_contenedor: 50,
      },
      {
        ...muestra(2, 11, 'RECIBIDA'),
        tipo_muestra_codigo: 'SANGRE_HEPARINA_VEN',
        tipo_contenedor: 50,
      },
    ] as MuestraTransaccional[];
    expect(
      muestrasCompatiblesParaTipo(proc, 10, 50, 'SANGRE_HEPARINA_ART', 'PH_ART').map((m) => m.id)
    ).toEqual([1]);
  });

  it('dual CREA_U acepta bidón ORINA_24_H aunque el catálogo diga ORINA', () => {
    const proc = [
      {
        ...muestra(7, 3, 'RECIBIDA'),
        tipo_muestra_codigo: 'ORINA_24_H',
        tipo_contenedor: 80,
      },
    ] as MuestraTransaccional[];
    const cat = new Map([
      [40, { ...tipoExamen(40, true, 2), codigo: 'CREA_U', tipo_muestra_codigo: 'ORINA' }],
    ]);
    const res = {
      ...resultado(9, 40),
      tipo_examen_codigo: 'CREA_U',
      tipo_examen_muestra_codigo: 'ORINA',
    };
    expect(suggestMuestraIdForResultado(res, proc, cat, null)).toBe(7);
    expect(
      validateCargaResultadosMuestra(
        [res],
        { 9: draftRow(7) },
        cat,
        proc
      )
    ).toBeNull();
  });

  it('reemplaza muestra legacy heparina por suero para química', () => {
    const proc = [
      { ...muestra(10, 1, 'EN_PROCESO'), tipo_muestra_codigo: 'SUERO', tipo_contenedor: 100 },
      { ...muestra(11, 2, 'EN_PROCESO'), tipo_muestra_codigo: 'PLASMA_HEPARINA', tipo_contenedor: 50 },
    ] as MuestraTransaccional[];
    const cat = new Map([
      [
        10,
        {
          ...tipoExamen(10, true, 1),
          codigo: 'CL',
          nombre: 'Cloro',
          tipo_muestra_codigo: 'SUERO',
          tipo_contenedor: 100,
        },
      ],
    ]);
    const res = {
      ...resultado(1, 10),
      tipo_examen_codigo: 'CL',
      tipo_examen_nombre: 'Cloro',
      tipo_examen_muestra_codigo: 'SUERO',
      muestra_id: 11,
    };
    expect(suggestMuestraIdForResultado(res, proc, cat, 11)).toBe(10);
    expect(
      validateCargaResultadosMuestra(
        [res],
        { 1: draftRow(11) },
        cat,
        proc
      )
    ).toBeNull();
  });

  it('con contenedor HEPARINA legacy aún encuentra tubo SUERO', () => {
    const proc = [
      { ...muestra(10, 1, 'EN_PROCESO'), tipo_muestra_codigo: 'SUERO', tipo_contenedor: 100 },
      { ...muestra(11, 2, 'EN_PROCESO'), tipo_muestra_codigo: 'PLASMA_HEPARINA', tipo_contenedor: 50 },
    ] as MuestraTransaccional[];
    const cat = new Map([
      [
        10,
        {
          ...tipoExamen(10, true, 1),
          codigo: 'CL',
          tipo_muestra_codigo: 'SUERO',
          tipo_contenedor: 50, // catálogo desfasado
        },
      ],
    ]);
    const res = {
      ...resultado(1, 10),
      tipo_examen_codigo: 'CL',
      tipo_examen_muestra_codigo: 'SUERO',
      muestra_id: 11,
    };
    expect(suggestMuestraIdForResultado(res, proc, cat, 11)).toBe(10);
  });

  it('con Suero+EDTA sugiere el tubo del tipo del examen', () => {
    const proc = [
      { ...muestra(10, 1, 'RECIBIDA'), tipo_muestra_codigo: 'SUERO', tipo_contenedor: 100 },
      { ...muestra(11, 2, 'RECIBIDA'), tipo_muestra_codigo: 'SANGRE_EDTA', tipo_contenedor: 101 },
    ] as MuestraTransaccional[];
    const cat = new Map([
      [30, { ...tipoExamen(30, true, 1), codigo: 'CPK_MB', tipo_contenedor: 100 }],
    ]);
    const res = {
      ...resultado(5, 30),
      tipo_examen_codigo: 'CPK_MB',
      tipo_examen_muestra_codigo: 'SUERO',
    };
    expect(suggestMuestraIdForResultado(res, proc, cat, null)).toBe(10);
  });

  it('sin catálogo pero con código de muestra en el resultado asocia el tubo', () => {
    const proc = [
      { ...muestra(10, 1, 'RECIBIDA'), tipo_muestra_codigo: 'SUERO' },
      { ...muestra(11, 2, 'RECIBIDA'), tipo_muestra_codigo: 'SANGRE_EDTA' },
    ] as MuestraTransaccional[];
    const res = {
      ...resultado(5, 30),
      tipo_examen_codigo: 'CPK_MB',
      tipo_examen_muestra_codigo: 'SUERO',
    };
    expect(suggestMuestraIdForResultado(res, proc, new Map(), null)).toBe(10);
  });

  it('al subir TG a 400 deja LDL y residual como no calculables', () => {
    const codigos = ['COL_TOT', 'HDL', 'TG', 'LDL', 'COL_RESID'] as const;
    const resultados = codigos.map((codigo, i) => ({
      id: i + 1,
      tipo_examen: i + 1,
      tipo_examen_codigo: codigo,
      tipo_examen_nombre: codigo,
      valor_obtenido: '',
      valor_numerico: null,
    })) as ResultadoExamenLims[];
    const catalog = new Map<number, LimsTipoExamen>(
      codigos.map((codigo, i) => [
        i + 1,
        {
          id: i + 1,
          codigo,
          nombre: codigo,
          tipo_muestra_requerida: 1,
          modo_entrada: i >= 3 ? 'CALCULADO' : 'ESTANDAR',
        },
      ])
    );
    const draft: Record<number, DraftCargaRow> = {
      1: { valor: '101', valor_sysmex: '', valor_numerico: '101', unidad: '', muestra_id: null },
      2: { valor: '33', valor_sysmex: '', valor_numerico: '33', unidad: '', muestra_id: null },
      3: { valor: '400', valor_sysmex: '', valor_numerico: '', unidad: '', muestra_id: null },
      4: { valor: '48', valor_sysmex: '', valor_numerico: '48', unidad: '', muestra_id: null },
      5: { valor: '20', valor_sysmex: '', valor_numerico: '20', unidad: '', muestra_id: null },
    };
    const next = applyAutofillVcmChcm(resultados, draft, catalog, new Set());
    expect(next[4].valor).toBe(RESULTADO_NO_CALCULABLE);
    expect(next[4].valor_numerico).toBe('');
    expect(next[5].valor).toBe(RESULTADO_NO_CALCULABLE);
    const payloadLdl = buildCargarResultadoPayload(4, next[4], catalog.get(4), 'LDL');
    expect(payloadLdl.valor).toBe(RESULTADO_NO_CALCULABLE);
    expect(payloadLdl.valor_numerico).toBeNull();
  });

  it('detecta borrado de valor ya informado y arma payload vacío', () => {
    const r = {
      ...resultado(1, 10),
      valor_obtenido: '12.5',
      valor_numerico: 12.5,
    } as ResultadoExamenLims;
    const empty: DraftCargaRow = {
      valor: '',
      valor_sysmex: '',
      valor_numerico: '',
      unidad: '',
      muestra_id: null,
    };
    expect(draftRowClearsServerValue(r, empty)).toBe(true);
    const payload = buildCargarResultadoPayload(1, empty);
    expect(payload.valor).toBe('');
    expect(payload.valor_numerico).toBeNull();
  });

  it('no reenvía filas intactas (p. ej. CREA_U al guardar otro panel)', () => {
    const r = {
      ...resultado(1, 10),
      tipo_examen_codigo: 'CREA_U',
      tipo_examen_nombre: 'Creatininuria',
      valor_obtenido: '80',
      valor_numerico: 80,
      muestra_id: null,
    } as ResultadoExamenLims;
    const same: DraftCargaRow = {
      valor: '80',
      valor_sysmex: '',
      valor_numerico: '80',
      unidad: 'mg/dL',
      muestra_id: null,
    };
    expect(resultadoDebeGuardarse(r, same)).toBe(false);
    const changed = { ...same, valor: '90', valor_numerico: '' };
    expect(resultadoDebeGuardarse(r, changed)).toBe(true);
  });

  it('omite resultado ya informado sin tubo para no bloquear otros paneles', () => {
    const te = { ...tipoExamen(10, true, 1), codigo: 'CREA_U' };
    const r = {
      ...resultado(1, 10),
      tipo_examen_codigo: 'CREA_U',
      valor_obtenido: '80',
      valor_numerico: 80,
    } as ResultadoExamenLims;
    const row: DraftCargaRow = {
      valor: '80',
      valor_sysmex: '',
      valor_numerico: '80.0',
      unidad: '',
      muestra_id: null,
    };
    expect(resultadoPuedeOmitirseSinMuestra(r, row, te)).toBe(true);
    expect(resultadoDebeGuardarse(r, row, te)).toBe(false);
  });
});
