/**
 * Agrupa resultados de una orden LIMS por panel solicitado y exámenes sueltos.
 */
import {
  applyOrdenGrupos,
  grupoKeyPanel,
  grupoKeyResultado,
} from './limsOrdenInforme';
import type { ResultadoExamenLims, SolicitudExamenLims } from '../types/lims';

export interface GrupoResultadosOrden {
  key: string;
  titulo: string;
  codigo?: string;
  resultados: ResultadoExamenLims[];
}

function sortByPanelOrder(
  resultados: ResultadoExamenLims[],
  orderedIds: number[] | undefined
): ResultadoExamenLims[] {
  if (!orderedIds?.length) {
    return resultados;
  }
  const rank = new Map(orderedIds.map((id, index) => [id, index]));
  return [...resultados].sort(
    (a, b) =>
      (rank.get(a.tipo_examen) ?? 10_000) - (rank.get(b.tipo_examen) ?? 10_000)
  );
}

export function groupResultadosPorPanel(
  orden: Pick<SolicitudExamenLims, 'paneles_resumen' | 'tipos_examen' | 'orden_grupos_informe'>,
  resultados: ResultadoExamenLims[]
): GrupoResultadosOrden[] {
  const paneles = orden.paneles_resumen ?? [];
  const assignedResultIds = new Set<number>();
  const grupos: GrupoResultadosOrden[] = [];

  for (const panel of paneles) {
    const idsPanel = new Set(panel.tipos_examen_ids);
    const rows = sortByPanelOrder(
      resultados.filter((r) => idsPanel.has(r.tipo_examen)),
      panel.tipos_examen_ids
    );
    rows.forEach((r) => assignedResultIds.add(r.id));
    if (rows.length > 0) {
      grupos.push({
        key: grupoKeyPanel(panel.id),
        titulo: panel.nombre,
        codigo: panel.codigo,
        resultados: rows,
      });
    }
  }

  const otros = resultados.filter((r) => !assignedResultIds.has(r.id));
  for (const r of otros) {
    grupos.push({
      key: grupoKeyResultado(r.id),
      titulo: r.tipo_examen_nombre || `Examen #${r.tipo_examen}`,
      resultados: [r],
    });
  }

  if (grupos.length === 0) {
    return grupos;
  }

  return applyOrdenGrupos(grupos, orden.orden_grupos_informe);
}
