import type { EstadoEstudioMicrobiologia } from '../types/lims';
import { estadoOrdenColor } from './limsEstadosOrden';

/** Etiquetas técnicas (filtros / lab). No usar en chips de UI clínica. */
export const ESTADO_ESTUDIO_MICRO_LABEL_TECNICO: Record<EstadoEstudioMicrobiologia, string> = {
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

/** @deprecated Preferí ESTADO_ESTUDIO_MICRO_LABEL_TECNICO o labelEstadoEstudioMicro. */
export const ESTADO_ESTUDIO_MICRO_LABEL = ESTADO_ESTUDIO_MICRO_LABEL_TECNICO;

/**
 * Etiqueta de chip alineada con órdenes clínicas:
 * - PENDIENTE / LISTO_PARA_VALIDAR / CANCELADO: mismos textos
 * - RECIBIDO…ANTIBIOGRAMA → En proceso
 * - VALIDADO / INFORMADO → Finalizado
 */
export function labelEstadoEstudioMicro(estado: EstadoEstudioMicrobiologia | string): string {
  switch (estado) {
    case 'PENDIENTE':
      return 'Pendiente';
    case 'RECIBIDO':
    case 'SEMBRADO':
    case 'LECTURA_PRELIMINAR':
    case 'IDENTIFICACION':
    case 'ANTIBIOGRAMA':
      return 'En proceso';
    case 'LISTO_PARA_VALIDAR':
      return 'Listo para validar';
    case 'VALIDADO':
    case 'INFORMADO':
      return 'Finalizado';
    case 'CANCELADO':
      return 'Cancelado';
    default:
      return ESTADO_ESTUDIO_MICRO_LABEL_TECNICO[estado as EstadoEstudioMicrobiologia] || estado;
  }
}

export function labelEstadoEstudioMicroTecnico(
  estado: EstadoEstudioMicrobiologia | string
): string {
  return ESTADO_ESTUDIO_MICRO_LABEL_TECNICO[estado as EstadoEstudioMicrobiologia] || estado;
}

/**
 * Estados generales UI (consulta / resumen):
 * Pendiente | En proceso | Informe parcial | Listo para validar | Finalizado | Cancelado.
 */
export function labelEstadoMicroGeneral(
  estado: string,
  opts?: { tieneInformePreliminar?: boolean; tieneInformeFinal?: boolean }
): string {
  if (opts?.tieneInformeFinal || estado === 'VALIDADO' || estado === 'INFORMADO') {
    return 'Finalizado';
  }
  if (estado === 'CANCELADO') return 'Cancelado';
  if (opts?.tieneInformePreliminar) {
    return 'Informe parcial';
  }
  if (estado === 'PENDIENTE') return 'Pendiente';
  // Igual que labelEstadoOrdenGeneral: LISTO_PARA_VALIDAR → En proceso
  if (estado === 'LISTO_PARA_VALIDAR') return 'En proceso';
  return 'En proceso';
}

/**
 * Colores iguales a lab clínico (`estadoOrdenColor`):
 * Pendiente / listo para validar → warning;
 * En proceso (etapas técnicas) → primary;
 * Finalizado (validado/informado) → success;
 * Cancelado → error;
 * Informe parcial (solo vía general + opts) → info.
 */
export function estadoEstudioMicroColor(
  estado: EstadoEstudioMicrobiologia | string
): 'default' | 'primary' | 'success' | 'error' | 'warning' | 'info' {
  switch (estado) {
    case 'PENDIENTE':
      return estadoOrdenColor('PENDIENTE');
    case 'RECIBIDO':
    case 'SEMBRADO':
    case 'LECTURA_PRELIMINAR':
    case 'IDENTIFICACION':
    case 'ANTIBIOGRAMA':
      return estadoOrdenColor('EN_PROCESO');
    case 'LISTO_PARA_VALIDAR':
      return estadoOrdenColor('LISTO_PARA_VALIDAR');
    case 'VALIDADO':
    case 'INFORMADO':
      return estadoOrdenColor('FINALIZADO');
    case 'CANCELADO':
      return estadoOrdenColor('CANCELADO');
    default:
      return 'default';
  }
}

/** Color para chips de vista general (incluye informe parcial). */
export function estadoMicroGeneralColor(
  estado: string,
  opts?: { tieneInformePreliminar?: boolean; tieneInformeFinal?: boolean }
): 'default' | 'primary' | 'success' | 'error' | 'warning' | 'info' {
  if (opts?.tieneInformeFinal || estado === 'VALIDADO' || estado === 'INFORMADO') {
    return estadoOrdenColor('FINALIZADO');
  }
  if (estado === 'CANCELADO') return estadoOrdenColor('CANCELADO');
  if (opts?.tieneInformePreliminar) return estadoOrdenColor('INFORMADO_PARCIAL');
  if (estado === 'PENDIENTE') return estadoOrdenColor('PENDIENTE');
  // Misma etiqueta general "En proceso"; color warning como LISTO clínico detallado
  // o primary como EN_PROCESO — usamos warning para LISTO (compartido).
  if (estado === 'LISTO_PARA_VALIDAR') return estadoOrdenColor('LISTO_PARA_VALIDAR');
  return estadoOrdenColor('EN_PROCESO');
}
