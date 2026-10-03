import type { EstudioMicrobiologia, SolicitudExamenLims } from '../types/lims';

export type TipoPedidoPendiente = 'LAB_CLINICO' | 'MICROBIOLOGIA';

export interface PendientePedidoRow {
  key: string;
  tipo: TipoPedidoPendiente;
  id: number;
  numero?: string | null;
  paciente_nombre?: string | null;
  paciente_dni?: string | null;
  medico_display?: string | null;
  origen_solicitud?: string;
  origen_solicitud_display?: string | null;
  procedencia_display?: string | null;
  estado: string;
  estado_obra_social?: string | null;
  fecha_solicitud?: string | null;
  fecha_programada_toma?: string | null;
  fecha_toma_muestra?: string | null;
  sin_etiquetas: boolean;
  esperando_recepcion: boolean;
  orden_abierta?: boolean;
  pedido_adicional?: boolean;
  puede_agregar_examenes?: boolean;
  puede_quitar_examenes?: boolean;
  tubos_pendientes_extraccion?: SolicitudExamenLims['tubos_pendientes_extraccion'];
  cultivo_nombre?: string | null;
  muestra_nombre?: string | null;
  /** Solo Lab: fila original para TomarMuestra / agregar. */
  labOrden?: SolicitudExamenLims;
  /** IQC Fase 1: ok / falta / na (sin materiales QC). */
  iqcStatus?: 'ok' | 'falta' | 'sin_config' | 'na';
}

export function mapLabToPendiente(r: SolicitudExamenLims): PendientePedidoRow {
  return {
    key: `lab-${r.id}`,
    tipo: 'LAB_CLINICO',
    id: r.id,
    numero: r.numero,
    paciente_nombre: r.paciente_nombre || String(r.paciente),
    paciente_dni: r.paciente_dni,
    medico_display: r.medico_display || r.medico_interno_nombre || null,
    origen_solicitud: r.origen_solicitud,
    origen_solicitud_display: r.origen_solicitud_display,
    procedencia_display: r.procedencia_display,
    estado: r.estado,
    estado_obra_social: r.estado_obra_social || '',
    fecha_solicitud: r.fecha_solicitud,
    fecha_programada_toma: r.fecha_programada_toma,
    fecha_toma_muestra: r.fecha_toma_muestra,
    sin_etiquetas: Boolean(r.orden_abierta),
    esperando_recepcion: Boolean(r.esperando_recepcion),
    orden_abierta: Boolean(r.orden_abierta),
    pedido_adicional: Boolean(r.pedido_adicional),
    puede_agregar_examenes: Boolean(r.puede_agregar_examenes),
    puede_quitar_examenes: Boolean(r.puede_quitar_examenes),
    tubos_pendientes_extraccion: r.tubos_pendientes_extraccion,
    labOrden: r,
  };
}

/**
 * El filtro de estado de Lab. Clínico no coincide 1:1 con microbiología
 * (no existe FINALIZADO; el cierre es VALIDADO / INFORMADO).
 */
export function estadosMicroDesdeFiltroLab(estadoLab: string): string[] | null {
  const estado = (estadoLab || '').trim();
  if (!estado) return null;
  if (estado === 'FINALIZADO') return ['VALIDADO', 'INFORMADO'];
  if (estado === 'INFORMADO_PARCIAL') return ['LECTURA_PRELIMINAR'];
  if (estado === 'EN_PROCESO') {
    return ['RECIBIDO', 'SEMBRADO', 'LECTURA_PRELIMINAR', 'IDENTIFICACION', 'ANTIBIOGRAMA'];
  }
  if (estado === 'PENDIENTE' || estado === 'LISTO_PARA_VALIDAR') return [estado];
  return [estado];
}

/** Solo por número de protocolo (ascendente: primero → último). Sin desempates. */
export function sortPedidosPorNumero<T extends { numero?: string | null }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => {
    const na = (a.numero || '').trim();
    const nb = (b.numero || '').trim();
    if (!na && !nb) return 0;
    if (!na) return 1;
    if (!nb) return -1;
    return na.localeCompare(nb, 'es', { numeric: true, sensitivity: 'base' });
  });
}

/** @deprecated Usar sortPedidosPorNumero (ahora ascendente). */
export const sortPedidosMasRecientesPrimero = sortPedidosPorNumero;

export function mapMicroToPendiente(e: EstudioMicrobiologia): PendientePedidoRow {
  return {
    key: `micro-${e.id}`,
    tipo: 'MICROBIOLOGIA',
    id: e.id,
    numero: e.numero,
    paciente_nombre: e.paciente_nombre || String(e.paciente),
    paciente_dni: e.paciente_dni,
    medico_display: e.medico_display || e.medico_externo_nombre || null,
    origen_solicitud: e.origen_solicitud,
    origen_solicitud_display: e.origen_solicitud_display,
    procedencia_display: e.procedencia_display,
    estado: e.estado,
    estado_obra_social: e.estado_obra_social || '',
    fecha_solicitud: e.created_at,
    fecha_programada_toma: e.fecha_programada_toma,
    fecha_toma_muestra: e.fecha_inicio || e.created_at,
    sin_etiquetas: Boolean(e.sin_etiquetas ?? (e.estado === 'PENDIENTE' && !e.etiquetas_impresas_at)),
    esperando_recepcion: Boolean(
      e.esperando_recepcion ?? (e.estado === 'PENDIENTE' && e.etiquetas_impresas_at)
    ),
    cultivo_nombre: e.tipo_cultivo_nombre || e.tipo_estudio,
    muestra_nombre: e.tipo_muestra_micro_nombre || e.muestra_tipo_nombre,
  };
}
