import { AxiosError } from 'axios';

/** Nombre de descarga seguro (sin PHI ni DNI). */
export function informeLimsPdfFilename(solicitudId: number): string {
  return `informe-lims-solicitud-${solicitudId}.pdf`;
}

export function assertValidSolicitudId(solicitudId: number): void {
  if (!Number.isInteger(solicitudId) || solicitudId <= 0) {
    throw new Error('Identificador de solicitud inválido.');
  }
}

function safeDrfDetail(error: unknown): string | null {
  const ax = error as AxiosError<{ detail?: string; error?: string }>;
  const data = ax.response?.data;
  if (data && typeof data === 'object') {
    if (typeof data.detail === 'string') return data.detail;
    if (typeof data.error === 'string') return data.error;
  }
  return null;
}

/** Mensajes de error para descarga PDF LIMS sin loguear cuerpo de respuesta. */
export function formatLimsPdfDownloadError(error: unknown): string {
  const ax = error as AxiosError;
  const status = ax.response?.status;
  if (status === 403) {
    return 'No tenés permisos para descargar el informe.';
  }
  if (status === 404) {
    return 'No se encontró la solicitud o no tenés acceso.';
  }
  if (status === 500) {
    return 'No se pudo generar el informe. Intentá nuevamente.';
  }
  if (error instanceof Error && error.message === 'Identificador de solicitud inválido.') {
    return error.message;
  }
  const detail = safeDrfDetail(error);
  if (detail) return detail;
  if (ax.message) return ax.message;
  return status ? `Error HTTP ${status}` : 'No se pudo completar la descarga.';
}
