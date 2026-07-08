import type { LimsTipoExamen, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../types/lims';
import {
  buildOpcionesTiposMuestraTomar,
  filterTiposMuestraPendientes,
  getTiposMuestraRequeridosPorOrden,
  idsTiposMuestraRequeridosPendientes,
} from './limsTiposMuestraOrden';

const tiposMuestra: LimsTipoMuestra[] = [
  { id: 1, codigo: 'SNG', nombre: 'Sangre' },
  { id: 2, codigo: 'ORI', nombre: 'Orina' },
];

const catalog = new Map<number, LimsTipoExamen>([
  [10, { id: 10, codigo: 'GLU', nombre: 'Glucosa', tipo_muestra_requerida: 1 }],
  [11, { id: 11, codigo: 'HEM', nombre: 'Hemoglobina', tipo_muestra_requerida: 1 }],
  [12, { id: 12, codigo: 'URO', nombre: 'Urocultivo', tipo_muestra_requerida: 2 }],
]);

const orden: SolicitudExamenLims = {
  id: 1,
  numero: 'LAB-1',
  paciente: 1,
  medico_interno: 1,
  origen_solicitud: 'AMBULATORIO_CEHTA',
  estado: 'PENDIENTE',
  fecha_solicitud: '2026-01-01',
  tipos_examen: [10, 11, 12],
  tipos_examen_nombres: ['Glucosa', 'Hemoglobina', 'Urocultivo'],
};

describe('limsTiposMuestraOrden', () => {
  it('agrupa tipos de muestra requeridos sin duplicar', () => {
    const tipos = getTiposMuestraRequeridosPorOrden(orden, catalog, tiposMuestra);
    expect(tipos).toHaveLength(2);
    expect(tipos.find((t) => t.tipoMuestraId === 1)?.examenesAsociados).toEqual(['Glucosa', 'Hemoglobina']);
    expect(tipos.find((t) => t.tipoMuestraId === 2)?.examenesAsociados).toEqual(['Urocultivo']);
  });

  it('excluye tipos ya tomados', () => {
    const muestras: MuestraTransaccional[] = [
      { id: 1, codigo_barra: 'A', solicitud: 1, paciente: 1, tipo_muestra: 1, estado: 'TOMADA' },
    ];
    const todos = getTiposMuestraRequeridosPorOrden(orden, catalog, tiposMuestra);
    const pendientes = filterTiposMuestraPendientes(todos, muestras);
    expect(pendientes).toHaveLength(1);
    expect(pendientes[0].tipoMuestraId).toBe(2);
  });

  it('arma opciones del catálogo excluyendo ya tomadas', () => {
    const muestras: MuestraTransaccional[] = [
      { id: 1, codigo_barra: 'A', solicitud: 1, paciente: 1, tipo_muestra: 1, estado: 'TOMADA' },
    ];
    const opts = buildOpcionesTiposMuestraTomar(orden, catalog, tiposMuestra, muestras);
    expect(opts).toHaveLength(1);
    expect(opts[0].tipoMuestraId).toBe(2);
    expect(opts[0].requeridoPorOrden).toBe(true);
  });

  it('preselecciona requeridas pendientes', () => {
    const ids = idsTiposMuestraRequeridosPendientes(orden, catalog, tiposMuestra, []);
    expect(ids.sort()).toEqual([1, 2]);
  });
});
