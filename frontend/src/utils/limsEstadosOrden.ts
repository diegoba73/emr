import type { EstadoSolicitudLims, SolicitudExamenLims } from '../types/lims';

/** Lab/bioquímico pueden intentar agregar (API valida si cabe en tubos tras etiquetas). */
export function ordenPuedeAgregarExamenes(orden: Pick<
  SolicitudExamenLims,
  'puede_agregar_examenes' | 'orden_abierta' | 'esperando_recepcion'
>): boolean {
  if (typeof orden.puede_agregar_examenes === 'boolean') {
    return orden.puede_agregar_examenes;
  }
  return Boolean(orden.orden_abierta || orden.esperando_recepcion);
}

export const ESTADOS_ORDEN_LIMS: EstadoSolicitudLims[] = [
  'PENDIENTE',
  'EN_PROCESO',
  'INFORMADO_PARCIAL',
  'LISTO_PARA_VALIDAR',
  'FINALIZADO',
];

export const ESTADO_ORDEN_LABEL: Record<EstadoSolicitudLims, string> = {
  PENDIENTE: 'Pendiente',
  EN_PROCESO: 'En proceso',
  INFORMADO_PARCIAL: 'Informado parcialmente',
  LISTO_PARA_VALIDAR: 'Listo para validar',
  FINALIZADO: 'Finalizado',
};

export function labelEstadoOrdenLims(estado: EstadoSolicitudLims | string): string {
  return ESTADO_ORDEN_LABEL[estado as EstadoSolicitudLims] || estado;
}

export function estadoOrdenColor(
  estado: EstadoSolicitudLims
): 'default' | 'primary' | 'success' | 'error' | 'warning' | 'info' {
  switch (estado) {
    case 'PENDIENTE':
      return 'warning';
    case 'EN_PROCESO':
      return 'primary';
    case 'INFORMADO_PARCIAL':
      return 'info';
    case 'LISTO_PARA_VALIDAR':
      return 'warning';
    case 'FINALIZADO':
      return 'success';
    default:
      return 'default';
  }
}

export function ordenPuedeCargarResultados(estado: EstadoSolicitudLims): boolean {
  return (
    estado === 'EN_PROCESO' ||
    estado === 'INFORMADO_PARCIAL' ||
    estado === 'LISTO_PARA_VALIDAR'
  );
}

export function ordenPuedeCorregirResultados(estado: EstadoSolicitudLims): boolean {
  // Tras FINALIZADO los resultados quedan bloqueados.
  return ordenPuedeCargarResultados(estado);
}

/** Estado LISTO_PARA_VALIDAR (resultados completos pendientes de bioquímico). */
export function ordenListaParaValidar(
  estado: EstadoSolicitudLims,
  _resultadosCompletos?: boolean
): boolean {
  return estado === 'LISTO_PARA_VALIDAR';
}

/** Solo informe validado (FINALIZADO): sin borradores ni parciales. */
export function ordenPuedeEnviarInforme(estado: EstadoSolicitudLims): boolean {
  return estado === 'FINALIZADO';
}

export function ordenEsFinalizada(estado: EstadoSolicitudLims): boolean {
  return estado === 'FINALIZADO';
}
