/** Navegación desde Estudios complementarios → calendario para elegir horario. */
export const AGENDAR_ESTUDIO_QUERY = 'agendarEstudio';

export function turnosAgendarEstudioPath(estudioId: number): string {
  return `/turnos?${AGENDAR_ESTUDIO_QUERY}=${estudioId}`;
}
