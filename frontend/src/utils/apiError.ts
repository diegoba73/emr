/** Mensajes seguros ante errores HTTP sin exponer PHI ni detalles del servidor. */

function responseStatus(error: unknown): number | undefined {
  const status = (error as { response?: { status?: number } })?.response?.status;
  return typeof status === 'number' ? status : undefined;
}

export function getSafeApiErrorMessage(
  error: unknown,
  fallback = 'No se pudo completar la operación.'
): string {
  const status = responseStatus(error);
  if (status === 403) {
    return 'No tiene permisos para realizar esta acción.';
  }
  if (status === 404) {
    return 'El recurso solicitado no está disponible.';
  }
  if (status === 401) {
    return 'Debe iniciar sesión para continuar.';
  }
  return fallback;
}

export function isForbiddenError(error: unknown): boolean {
  return responseStatus(error) === 403;
}

export function isNotFoundError(error: unknown): boolean {
  return responseStatus(error) === 404;
}
