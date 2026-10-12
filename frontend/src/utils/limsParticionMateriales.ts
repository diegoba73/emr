/**
 * Parte la selección clínica en un grupo por material de pedido
 * (solo materiales con al menos un examen/panel marcado).
 */
import type { LimsPanelExamen, LimsTipoExamen, MaterialPedidoLims } from '../types/lims';
import { idsDeMaterial } from '../components/lims/SolicitudAnalisisMaterialesForm';

export type GrupoPedidoMaterial = {
  material: MaterialPedidoLims;
  examenes_ids: number[];
  paneles_ids: number[];
};

export function particionarSeleccionPorMateriales(opts: {
  materialesOrden: MaterialPedidoLims[];
  selectedExamenesIds: Set<number>;
  selectedPanelesIds: Set<number>;
  examenes: LimsTipoExamen[];
  paneles: LimsPanelExamen[];
}): GrupoPedidoMaterial[] {
  const remainingEx = new Set(opts.selectedExamenesIds);
  const remainingPan = new Set(opts.selectedPanelesIds);
  const groups: GrupoPedidoMaterial[] = [];

  for (const mat of opts.materialesOrden) {
    const { panelIds, examenIds } = idsDeMaterial(mat, opts.paneles, opts.examenes);
    const examenes_ids = examenIds.filter((id) => remainingEx.has(id));
    const paneles_ids = panelIds.filter((id) => remainingPan.has(id));
    examenes_ids.forEach((id) => remainingEx.delete(id));
    paneles_ids.forEach((id) => remainingPan.delete(id));
    if (examenes_ids.length > 0 || paneles_ids.length > 0) {
      groups.push({ material: mat, examenes_ids, paneles_ids });
    }
  }

  // Huérfanos (fuera de grilla de los materiales elegidos): van al primer grupo.
  if (remainingEx.size > 0 || remainingPan.size > 0) {
    if (groups.length > 0) {
      const first = groups[0];
      first.examenes_ids = [...first.examenes_ids, ...Array.from(remainingEx)];
      first.paneles_ids = [...first.paneles_ids, ...Array.from(remainingPan)];
    } else if (opts.materialesOrden.length > 0) {
      groups.push({
        material: opts.materialesOrden[0],
        examenes_ids: Array.from(remainingEx),
        paneles_ids: Array.from(remainingPan),
      });
    }
  }

  return groups;
}
