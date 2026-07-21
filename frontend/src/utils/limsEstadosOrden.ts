import type { EstadoSolicitudLims } from '../types/lims';

export const ESTADOS_ORDEN_LIMS: EstadoSolicitudLims[] = [
  'PENDIENTE',
  'EN_PROCESO',
  'INFORMADO_PARCIAL',
  'FINALIZADO',
];

export const ESTADO_ORDEN_LABEL: Record<EstadoSolicitudLims, string> = {
  PENDIENTE: 'Pendiente',
  EN_PROCESO: 'En proceso',
  INFORMADO_PARCIAL: 'Informado parcialmente',
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
    case 'FINALIZADO':
      return 'success';
    default:
      return 'default';
  }
}

export function ordenPuedeCargarResultados(estado: EstadoSolicitudLims): boolean {
  return estado === 'EN_PROCESO' || estado === 'INFORMADO_PARCIAL';
}

export function ordenPuedeCorregirResultados(estado: EstadoSolicitudLims): boolean {
  // Fase A: tras FINALIZADO los resultados quedan bloqueados.
  return estado === 'EN_PROCESO' || estado === 'INFORMADO_PARCIAL';
}

/** Completos y aún no liberados: listos para validación del bioquímico. */
export function ordenListaParaValidar(estado: EstadoSolicitudLims, resultadosCompletos: boolean): boolean {
  return resultadosCompletos && (estado === 'EN_PROCESO' || estado === 'INFORMADO_PARCIAL');
}

export function ordenPuedeEnviarInforme(estado: EstadoSolicitudLims): boolean {
  return estado === 'FINALIZADO' || estado === 'INFORMADO_PARCIAL';
}

export function ordenEsFinalizada(estado: EstadoSolicitudLims): boolean {
  return estado === 'FINALIZADO';
}
