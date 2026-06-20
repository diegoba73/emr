import {
  filterMuestrasProcesablesMicro,
  formatMuestraTransaccionalMicroLabel,
  formatSolicitudMicroLabel,
  validateCrearEstudioMicroSelection,
} from './limsMicroUx';
import type { LimsTipoContenedor, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../types/lims';

const muestra = (id: number, estado: string, tipo = 2, contenedor: number | null = 5): MuestraTransaccional =>
  ({
    id,
    solicitud: 10,
    paciente: 1,
    tipo_muestra: tipo,
    tipo_contenedor: contenedor,
    estado,
    codigo_barra: null,
  }) as MuestraTransaccional;

describe('limsMicroUx', () => {
  it('filterMuestrasProcesablesMicro keeps RECIBIDA CONSERVADA EN_PROCESO', () => {
    const list = [
      muestra(1, 'RECIBIDA'),
      muestra(2, 'TOMADA'),
      muestra(3, 'CONSERVADA'),
      muestra(4, 'EN_PROCESO'),
    ];
    expect(filterMuestrasProcesablesMicro(list).map((m) => m.id)).toEqual([1, 3, 4]);
  });

  it('formatSolicitudMicroLabel without codigo_barra', () => {
    const s = {
      id: 42,
      numero: 'SOL-001',
      paciente: 1,
      paciente_nombre: 'Paciente Test',
      estado: 'EN_PROCESO',
      fecha_solicitud: '2026-01-01',
      origen_solicitud: 'EMR',
      medico_interno: null,
    } as SolicitudExamenLims;
    expect(formatSolicitudMicroLabel(s)).toBe('#42 · SOL-001 · Paciente Test · EN_PROCESO');
  });

  it('formatMuestraTransaccionalMicroLabel', () => {
    const tipos = new Map<number, LimsTipoMuestra>([[2, { id: 2, codigo: 'SANG', nombre: 'Sangre' }]]);
    const cont = new Map<number, LimsTipoContenedor>([[5, { id: 5, codigo: 'EDTA', nombre: 'Tubo EDTA' }]]);
    expect(formatMuestraTransaccionalMicroLabel(muestra(7, 'RECIBIDA'), tipos, cont)).toBe(
      '#7 · Sangre · Tubo EDTA · RECIBIDA'
    );
  });

  it('validateCrearEstudioMicroSelection', () => {
    expect(validateCrearEstudioMicroSelection('', '')).toMatch(/solicitud/i);
    expect(validateCrearEstudioMicroSelection(1, '')).toMatch(/muestra/i);
    expect(validateCrearEstudioMicroSelection(1, 2)).toBeNull();
  });
});
