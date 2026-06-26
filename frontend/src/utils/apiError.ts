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

  limsCargarEstudio: 'No se pudo cargar el estudio. Intentá nuevamente.',
  limsGuardarSiembra: 'No se pudo registrar la siembra. Intentá nuevamente.',
  limsGuardarLectura: 'No se pudo registrar la lectura. Intentá nuevamente.',
  limsGuardarAislado: 'No se pudo guardar el aislado. Intentá nuevamente.',
  limsActualizarIdentificacion: 'No se pudo actualizar la identificación. Intentá nuevamente.',
  limsGuardarAntibiograma: 'No se pudo guardar el antibiograma. Intentá nuevamente.',
  limsGuardarResultadoAntibiograma: 'No se pudo guardar el resultado del antibiograma. Intentá nuevamente.',
  limsCompletarAntibiograma: 'No se pudo completar el antibiograma. Intentá nuevamente.',
  limsGuardarInforme: 'No se pudo guardar el informe. Intentá nuevamente.',
  limsEmitirInforme: 'No se pudo emitir el informe. Intentá nuevamente.',
  limsValidarInforme: 'No se pudo validar el informe. Intentá nuevamente.',
  limsActualizarEstudioMicro: 'No se pudo actualizar el estudio. Intentá nuevamente.',
  limsCargarMuestras: 'No se pudieron cargar las muestras. Intentá nuevamente.',
  limsCrearMuestra: 'No se pudo crear la muestra. Intentá nuevamente.',
  limsActualizarMuestra: 'No se pudo actualizar la muestra. Intentá nuevamente.',
  limsCargarOrden: 'No se pudo cargar la orden. Intentá nuevamente.',
  limsActualizarOrden: 'No se pudo actualizar la orden. Intentá nuevamente.',
  limsCargarOrdenes: 'No se pudieron cargar las órdenes. Intentá nuevamente.',
  limsCargarCatalogo: 'No se pudo cargar el catálogo. Intentá nuevamente.',
  limsGuardarCatalogo: 'No se pudo guardar en el catálogo. Intentá nuevamente.',
  limsCargarEstudiosMicro: 'No se pudieron cargar los estudios. Intentá nuevamente.',
  limsCargarDatosMicro: 'No se pudieron cargar los datos. Intentá nuevamente.',
  limsCrearEstudioMicro: 'No se pudo crear el estudio. Intentá nuevamente.',
  limsGuardarResultado: 'No se pudo guardar el resultado. Intentá nuevamente.',
  limsCargarExamenes: 'No se pudieron cargar los exámenes. Intentá nuevamente.',
  genericClinicalAction: 'No se pudo completar la operación. Intentá nuevamente.',
} as const;

/** Mensaje seguro para UI clínica: solo status HTTP conocido + fallback por acción. */
export function getSafeClinicalActionMessage(error: unknown, fallback: string): string {
  return getSafeApiErrorMessage(error, fallback);
}
