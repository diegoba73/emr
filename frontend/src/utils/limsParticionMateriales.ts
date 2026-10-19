/**
 * Parte la selección clínica en un grupo por material de pedido
 * (solo materiales con al menos un examen/panel marcado).
 */
import type { LimsPanelExamen, LimsTipoExamen, MaterialPedidoLims } from '../types/lims';
import { idsDeMaterial } from '../components/lims/SolicitudAnalisisMaterialesForm';
import { esOrigenAmbulatorio } from './limsOrigenSolicitud';

/** En ambulatorio se unifican en una sola orden clínica. */
export const MATERIALES_UNIFICABLES_AMBULATORIO = new Set([
  'SANGRE',
  'ORINA',
  'MATERIA_FECAL',
]);

export type GrupoPedidoMaterial = {
  material: MaterialPedidoLims;
  examenes_ids: number[];
  paneles_ids: number[];
  /** Presente si el grupo es el bucket ambulatorio unificado. */
  materialesUnificados?: string[];
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

/**
 * En ambulatorio colapsa SANGRE+ORINA+MATERIA_FECAL en un solo grupo.
 * Guardia/internación: sin cambio.
 */
export function agruparParaPedidoCompleto(
  groups: GrupoPedidoMaterial[],
  origen: string | null | undefined
): GrupoPedidoMaterial[] {
  if (!esOrigenAmbulatorio(origen) || groups.length < 2) {
    return groups;
  }

  const uni: GrupoPedidoMaterial[] = [];
  const resto: GrupoPedidoMaterial[] = [];
  for (const g of groups) {
    const mat = (g.material.codigo || '').toUpperCase();
    if (MATERIALES_UNIFICABLES_AMBULATORIO.has(mat)) {
      uni.push(g);
    } else {
      resto.push(g);
    }
  }

  const matsUni = [
    ...new Set(
      uni
        .map((g) => (g.material.codigo || '').toUpperCase())
        .filter((m) => MATERIALES_UNIFICABLES_AMBULATORIO.has(m))
    ),
  ].sort();

  if (matsUni.length < 2) {
    return groups;
  }

  const examenes_ids: number[] = [];
  const paneles_ids: number[] = [];
  const seenE = new Set<number>();
  const seenP = new Set<number>();
  for (const g of uni) {
    for (const id of g.examenes_ids) {
      if (!seenE.has(id)) {
        seenE.add(id);
        examenes_ids.push(id);
      }
    }
    for (const id of g.paneles_ids) {
      if (!seenP.has(id)) {
        seenP.add(id);
        paneles_ids.push(id);
      }
    }
  }

  const nombre = matsUni
    .map((c) => {
      const found = uni.find((g) => (g.material.codigo || '').toUpperCase() === c);
      return found?.material.nombre || c;
    })
    .join(' + ');

  const merged: GrupoPedidoMaterial = {
    material: {
      codigo: '',
      nombre,
      tipo_muestra_codigos: [],
      grilla_codigos: [],
    },
    examenes_ids,
    paneles_ids,
    materialesUnificados: matsUni,
  };

  return [merged, ...resto];
}
