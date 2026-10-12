import { particionarSeleccionPorMateriales } from './limsParticionMateriales';
import type { LimsPanelExamen, LimsTipoExamen, MaterialPedidoLims } from '../types/lims';

describe('particionarSeleccionPorMateriales', () => {
  const sangre: MaterialPedidoLims = {
    codigo: 'SANGRE',
    nombre: 'Sangre',
    ui_preset: 'sangre',
    tipo_muestra_codigos: ['SUERO', 'SANGRE_EDTA'],
    grilla_codigos: [],
  };
  const orina: MaterialPedidoLims = {
    codigo: 'ORINA',
    nombre: 'Orina',
    ui_preset: 'orina',
    tipo_muestra_codigos: ['ORINA'],
    grilla_codigos: [],
  };
  const lcr: MaterialPedidoLims = {
    codigo: 'LCR',
    nombre: 'LCR',
    tipo_muestra_codigos: ['LCR'],
    grilla_codigos: ['ASP_LCR', 'GLU_LCR'],
  };

  const examenes: LimsTipoExamen[] = [
    {
      id: 1,
      codigo: 'GLU',
      nombre: 'Glucemia',
      tipo_muestra_requerida: 10,
      tipo_muestra_codigo: 'SUERO',
      activo: true,
    },
    {
      id: 2,
      codigo: 'ASP_LCR',
      nombre: 'Aspecto LCR',
      tipo_muestra_requerida: 20,
      tipo_muestra_codigo: 'LCR',
      activo: true,
    },
    {
      id: 3,
      codigo: 'GLU_LCR',
      nombre: 'Glucosa LCR',
      tipo_muestra_requerida: 20,
      tipo_muestra_codigo: 'LCR',
      activo: true,
    },
  ];

  const paneles: LimsPanelExamen[] = [
    {
      id: 100,
      codigo: 'PAN_ORI',
      nombre: 'Orina completa',
      tipos_examen: [],
      activo: true,
    },
  ];

  it('separa sangre, orina y LCR en tres grupos', () => {
    const groups = particionarSeleccionPorMateriales({
      materialesOrden: [sangre, orina, lcr],
      selectedExamenesIds: new Set([1, 2, 3]),
      selectedPanelesIds: new Set([100]),
      examenes,
      paneles,
    });
    expect(groups.map((g) => g.material.codigo)).toEqual(['SANGRE', 'ORINA', 'LCR']);
    expect(groups[0].examenes_ids).toEqual([1]);
    expect(groups[1].paneles_ids).toEqual([100]);
    expect(groups[2].examenes_ids.sort()).toEqual([2, 3]);
  });

  it('omite materiales sin selección', () => {
    const groups = particionarSeleccionPorMateriales({
      materialesOrden: [sangre, orina, lcr],
      selectedExamenesIds: new Set([2]),
      selectedPanelesIds: new Set(),
      examenes,
      paneles,
    });
    expect(groups.map((g) => g.material.codigo)).toEqual(['LCR']);
  });
});
