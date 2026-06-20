/**
 * Convierte el datetime devuelto por el API (string ISO) a Date para mostrar/editar en formulario.
 * Punto único de parseo desde servidor (evita dispersar `new Date(string)`).
 */
export function turnoInicioFromApi(fechaHoraInicio: string | undefined | null): Date | null {
  if (!fechaHoraInicio || typeof fechaHoraInicio !== 'string') return null;
  const d = new Date(fechaHoraInicio);
  return Number.isNaN(d.getTime()) ? null : d;
}
