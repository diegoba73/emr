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

/** Mensajes de error para descarga PDF LIMS sin exponer cuerpo de respuesta ni ax.message. */
export function formatLimsPdfDownloadError(error: unknown): string {
  const ax = error as AxiosError;
  const status = ax.response?.status;
  if (status === 401) {
    return 'La sesión no está activa. Iniciá sesión nuevamente.';
  }
  if (status === 403) {
    return 'No tenés permisos para descargar este informe.';
  }
  if (status === 404) {
    return 'El informe solicitado no está disponible.';
  }
  if (status === 500) {
    return 'No se pudo generar el informe. Intentá nuevamente.';
  }
  if (error instanceof Error && error.message === 'Identificador de solicitud inválido.') {
    return 'No se pudo descargar el informe. Intentá nuevamente.';
  }
  return 'No se pudo descargar el informe. Intentá nuevamente.';
}
