/** Colores de turnos en calendario — por estado (consultas y estudios). */

export interface TurnoEstadoCalendarMeta {
  value: string;
  label: string;
  color: string;
}

export const TURNO_ESTADOS_CALENDARIO: TurnoEstadoCalendarMeta[] = [
  { value: 'RESERVADO', label: 'Reservado', color: '#F59E0B' },
  { value: 'CONFIRMADO', label: 'Confirmado', color: '#3B82F6' },
  { value: 'REALIZADO', label: 'Realizado', color: '#8B5CF6' },
  { value: 'CANCELADO', label: 'Cancelado', color: '#EF4444' },
];

const COLOR_BY_ESTADO = Object.fromEntries(
  TURNO_ESTADOS_CALENDARIO.map((e) => [e.value, e.color])
) as Record<string, string>;

export function getTurnoEstadoColor(estado: string | undefined | null): string {
  if (!estado) return '#6B7280';
  return COLOR_BY_ESTADO[estado] ?? '#6B7280';
}

export function getTurnoEstadoLabel(estado: string | undefined | null): string {
  if (!estado) return '—';
  return TURNO_ESTADOS_CALENDARIO.find((e) => e.value === estado)?.label ?? estado;
}
