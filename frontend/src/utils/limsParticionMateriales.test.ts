import {
  agruparParaPedidoCompleto,
  particionarSeleccionPorMateriales,
} from './limsParticionMateriales';
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
  const mf: MaterialPedidoLims = {
    codigo: 'MATERIA_FECAL',
    nombre: 'Materia fecal',
    tipo_muestra_codigos: ['MATERIA_FECAL'],
    grilla_codigos: ['SOH'],
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

  it('ambulatorio unifica sangre+orina+MF y deja LCR aparte', () => {
    const base = particionarSeleccionPorMateriales({
      materialesOrden: [sangre, orina, mf, lcr],
      selectedExamenesIds: new Set([1, 2, 3]),
      selectedPanelesIds: new Set([100]),
      examenes,
      paneles,
    });
    // Forzar grupo MF vacío de exámenes: agregar panel orina ya está; MF sin selección
    // no aparece. Simular tres del bucket + LCR:
    const groups = [
      { material: sangre, examenes_ids: [1], paneles_ids: [] as number[] },
      { material: orina, examenes_ids: [] as number[], paneles_ids: [100] },
      { material: mf, examenes_ids: [99], paneles_ids: [] as number[] },
      { material: lcr, examenes_ids: [2, 3], paneles_ids: [] as number[] },
    ];
    const amb = agruparParaPedidoCompleto(groups, 'AMBULATORIO_CEHTA');
    expect(amb).toHaveLength(2);
    expect(amb[0].materialesUnificados).toEqual(['MATERIA_FECAL', 'ORINA', 'SANGRE']);
    expect(amb[0].examenes_ids.sort()).toEqual([1, 99]);
    expect(amb[0].paneles_ids).toEqual([100]);
    expect(amb[1].material.codigo).toBe('LCR');

    const guardia = agruparParaPedidoCompleto(groups, 'GUARDIA');
    expect(guardia).toHaveLength(4);
    expect(base.length).toBeGreaterThan(0);
  });

  it('ambulatorio con un solo material del bucket no colapsa', () => {
    const groups = [
      { material: sangre, examenes_ids: [1], paneles_ids: [] as number[] },
    ];
    expect(agruparParaPedidoCompleto(groups, 'AMBULATORIO_ICPL')).toEqual(groups);
  });
});
