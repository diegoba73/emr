import type { EstadoEstudioMicrobiologia } from '../types/lims';

export const ESTADO_ESTUDIO_MICRO_LABEL: Record<EstadoEstudioMicrobiologia, string> = {
  PENDIENTE: 'Pendiente',
  RECIBIDO: 'Recibido',
  SEMBRADO: 'Sembrado',
  LECTURA_PRELIMINAR: 'Lectura preliminar',
  IDENTIFICACION: 'Identificación',
  ANTIBIOGRAMA: 'Antibiograma',
  LISTO_PARA_VALIDAR: 'Listo para validar',
  VALIDADO: 'Validado',
  INFORMADO: 'Informado',
  CANCELADO: 'Cancelado',
};

export function labelEstadoEstudioMicro(estado: EstadoEstudioMicrobiologia | string): string {
  return ESTADO_ESTUDIO_MICRO_LABEL[estado as EstadoEstudioMicrobiologia] || estado;
}

/**
 * Estados generales UI (etapas técnicas intactas en el lab):
 * Pendiente | En proceso | Informe parcial | Finalizado.
 * FINAL vigente prevalece sobre preliminar.
 */
export function labelEstadoMicroGeneral(
  estado: string,
  opts?: { tieneInformePreliminar?: boolean; tieneInformeFinal?: boolean }
): string {
  if (opts?.tieneInformeFinal || estado === 'VALIDADO' || estado === 'INFORMADO') {
    return 'Finalizado';
  }
  if (opts?.tieneInformePreliminar) {
    return 'Informe parcial';
  }
  if (estado === 'PENDIENTE') return 'Pendiente';
  if (estado === 'CANCELADO') return 'Cancelado';
  if (estado === 'LISTO_PARA_VALIDAR') return 'En proceso';
  return 'En proceso';
}

/**
 * Misma lógica visual que lab clínico (`estadoOrdenColor`):
 * Pendiente / listo para validar → amarillo (warning);
 * en curso → primary; cerrado OK → success; cancelado → error.
 */
export function estadoEstudioMicroColor(
  estado: EstadoEstudioMicrobiologia | string
): 'default' | 'primary' | 'success' | 'error' | 'warning' | 'info' {
  switch (estado) {
    case 'PENDIENTE':
      return 'warning';
    case 'RECIBIDO':
    case 'SEMBRADO':
    case 'LECTURA_PRELIMINAR':
    case 'IDENTIFICACION':
    case 'ANTIBIOGRAMA':
      return 'primary';
    case 'LISTO_PARA_VALIDAR':
      return 'warning';
    case 'VALIDADO':
    case 'INFORMADO':
      return 'success';
    case 'CANCELADO':
      return 'error';
    default:
      return 'default';
  }
}
