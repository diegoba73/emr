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

/** Mensajes genéricos por acción clínica (sin parsear response.data). */
export const CLINICAL_ACTION_ERRORS = {
  turnoConfirmar: 'No se pudo confirmar el turno. Intentá nuevamente.',
  turnoCancelar:
    'No se pudo cancelar el turno. Intentá nuevamente o consultá con administración.',
  turnoRealizado: 'No se pudo marcar el turno como realizado. Intentá nuevamente.',
  turnoNoAsistio: 'No se pudo registrar la no asistencia. Intentá nuevamente.',
  turnoGuardar:
    'No se pudo guardar el turno. Revisá los datos ingresados o intentá nuevamente.',
  turnoReprogramar: 'No se pudo reprogramar el turno. Verificá la información ingresada.',
  turnoIniciarAtencion:
    'No se pudo iniciar la atención. Verificá el estado del turno o intentá nuevamente.',
  turnoSincronizarAtencion:
    'No se pudo sincronizar el turno con la atención. Intentá nuevamente.',
  internacionIngresar:
    'No se pudo ingresar al paciente. Verificá los datos ingresados o intentá nuevamente.',
  internacionActualizar:
    'No se pudo guardar el cambio. Revisá los datos ingresados o intentá nuevamente.',
  internacionAlta:
    'No se pudo dar de alta. Intentá nuevamente o consultá con administración.',
  internacionCargar: 'No se pudieron cargar los datos de internación. Intentá nuevamente.',
  camaCrear: 'No se pudo crear la cama. Revisá los datos ingresados o intentá nuevamente.',
  sectorCrear: 'No se pudo crear el sector. Revisá los datos ingresados o intentá nuevamente.',
  camaActualizar: 'No se pudo actualizar el estado de la cama. Intentá nuevamente.',
  limsDescartarAislado: 'No se pudo descartar el aislado. Intentá nuevamente.',
  limsAnularInforme: 'No se pudo anular el informe. Intentá nuevamente.',
  limsCancelarAntibiograma: 'No se pudo cancelar el antibiograma. Intentá nuevamente.',
  limsCancelarEstudioMicro: 'No se pudo cancelar el estudio. Intentá nuevamente.',
  genericClinicalAction: 'No se pudo completar la operación. Intentá nuevamente.',
} as const;

/** Mensaje seguro para UI clínica: solo status HTTP conocido + fallback por acción. */
export function getSafeClinicalActionMessage(error: unknown, fallback: string): string {
  return getSafeApiErrorMessage(error, fallback);
}
