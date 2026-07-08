import type { LimsTipoExamen, LimsTipoMuestra, MuestraTransaccional, SolicitudExamenLims } from '../types/lims';

export interface TipoMuestraRequeridoOrden {
  tipoMuestraId: number;
  codigo: string;
  nombre: string;
  examenesAsociados: string[];
}

const MUESTRA_ESTADOS_TERMINALES = new Set(['RECHAZADA', 'DESCARTADA', 'CANCELADA']);

/** Tipos de muestra distintos exigidos por los exámenes de la orden. */
export function getTiposMuestraRequeridosPorOrden(
  orden: SolicitudExamenLims,
  catalog: Map<number, LimsTipoExamen>,
  tiposMuestraCatalog: LimsTipoMuestra[]
): TipoMuestraRequeridoOrden[] {
  const tiposMap = new Map(tiposMuestraCatalog.map((t) => [t.id, t]));
  const byTipo = new Map<number, { examenes: string[]; codigo?: string; nombre?: string }>();
  const ids = orden.tipos_examen || [];
  const nombres = orden.tipos_examen_nombres || [];

  ids.forEach((teId, idx) => {
    const te = catalog.get(teId);
    if (!te?.tipo_muestra_requerida) return;
    const tmId = te.tipo_muestra_requerida;
    const entry = byTipo.get(tmId) || {
      examenes: [],
      codigo: te.tipo_muestra_codigo,
      nombre: te.tipo_muestra_nombre,
    };
    entry.examenes.push(nombres[idx] || te.nombre);
    byTipo.set(tmId, entry);
  });

  return Array.from(byTipo.entries()).map(([tipoMuestraId, meta]) => {
    const tm = tiposMap.get(tipoMuestraId);
    return {
      tipoMuestraId,
      codigo: tm?.codigo || meta.codigo || String(tipoMuestraId),
      nombre: tm?.nombre || meta.nombre || `Tipo ${tipoMuestraId}`,
      examenesAsociados: meta.examenes,
    };
  });
}

/** Quita tipos ya registrados con muestra activa en la orden. */
export function filterTiposMuestraPendientes(
  requeridos: TipoMuestraRequeridoOrden[],
  muestrasExistentes: MuestraTransaccional[]
): TipoMuestraRequeridoOrden[] {
  const tomados = new Set(
    muestrasExistentes
      .filter((m) => !MUESTRA_ESTADOS_TERMINALES.has(m.estado))
      .map((m) => m.tipo_muestra)
  );
  return requeridos.filter((r) => !tomados.has(r.tipoMuestraId));
}

export interface TipoMuestraTomarOpcion {
  tipoMuestraId: number;
  codigo: string;
  nombre: string;
  colorTubo?: string;
  requeridoPorOrden: boolean;
  examenesAsociados: string[];
  yaTomado: boolean;
}

/** Opciones del catálogo para el diálogo de toma (activas, no tomadas aún). */
export function buildOpcionesTiposMuestraTomar(
  orden: SolicitudExamenLims,
  catalog: Map<number, LimsTipoExamen>,
  tiposMuestraCatalog: LimsTipoMuestra[],
  muestrasExistentes: MuestraTransaccional[]
): TipoMuestraTomarOpcion[] {
  const requeridos = getTiposMuestraRequeridosPorOrden(orden, catalog, tiposMuestraCatalog);
  const requeridosMap = new Map(requeridos.map((r) => [r.tipoMuestraId, r]));
  const tomados = new Set(
    muestrasExistentes
      .filter((m) => !MUESTRA_ESTADOS_TERMINALES.has(m.estado))
      .map((m) => m.tipo_muestra)
  );

  return tiposMuestraCatalog
    .filter((t) => t.activo !== false)
    .map((t) => ({
      tipoMuestraId: t.id,
      codigo: t.codigo,
      nombre: t.nombre,
      colorTubo: t.color_tubo,
      requeridoPorOrden: requeridosMap.has(t.id),
      examenesAsociados: requeridosMap.get(t.id)?.examenesAsociados ?? [],
      yaTomado: tomados.has(t.id),
    }))
    .filter((t) => !t.yaTomado)
    .sort((a, b) => {
      if (a.requeridoPorOrden !== b.requeridoPorOrden) return a.requeridoPorOrden ? -1 : 1;
      return a.nombre.localeCompare(b.nombre, 'es');
    });
}

export function idsTiposMuestraRequeridosPendientes(
  orden: SolicitudExamenLims,
  catalog: Map<number, LimsTipoExamen>,
  tiposMuestraCatalog: LimsTipoMuestra[],
  muestrasExistentes: MuestraTransaccional[]
): number[] {
  const requeridos = getTiposMuestraRequeridosPorOrden(orden, catalog, tiposMuestraCatalog);
  return filterTiposMuestraPendientes(requeridos, muestrasExistentes).map((t) => t.tipoMuestraId);
}
