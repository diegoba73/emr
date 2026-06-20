import {
  buildCargarResultadoPayload,
  filterMuestrasProcesables,
  muestrasCompatiblesParaTipo,
  validateCargaResultadosMuestra,
  type DraftCargaRow,
} from './limsCargaMuestra';
import type { LimsTipoExamen, MuestraTransaccional, ResultadoExamenLims } from '../types/lims';

const draftRow = (muestra_id: number | null): DraftCargaRow => ({
  valor: '10',
  valor_numerico: '',
  unidad: '',
  es_patologico: false,
  es_critico: false,
  observaciones: '',
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
    expect(filterMuestrasProcesables(list).map((m) => m.id)).toEqual([1, 3, 4]);
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

  it('prefiltra muestras por tipo requerido', () => {
    const proc = [muestra(1, 1, 'RECIBIDA'), muestra(2, 2, 'EN_PROCESO')];
    expect(muestrasCompatiblesParaTipo(proc, 1).map((m) => m.id)).toEqual([1]);
  });
});
