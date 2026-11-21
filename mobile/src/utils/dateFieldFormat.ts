/** Formato de fecha/hora 24 h (sin AM/PM) para la app móvil. */

const pad2 = (n: number) => String(n).padStart(2, '0');

/** HH:mm (24 h). */
export function formatHora(date: Date): string {
  if (Number.isNaN(date.getTime())) return '';
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function formatHoraDisplay(date: Date): string {
  return formatHora(date);
}

/** Fecha + hora 24 h (dd/mm/aaaa HH:mm). */
export function formatFechaHoraDisplay(value: string | Date | null | undefined): string {
  if (value == null || value === '') return '—';
  const dt = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(dt.getTime())) return '—';
  const fecha = dt.toLocaleDateString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  return `${fecha} ${formatHora(dt)}`;
}
