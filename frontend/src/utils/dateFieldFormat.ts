/**
 * Formateo de campos fecha/hora para inputs (hora local del navegador, sin toISOString).
 */

const pad2 = (n: number) => String(n).padStart(2, '0');

/** YYYY-MM-DD */
export function formatFecha(date: Date): string {
  if (Number.isNaN(date.getTime())) return '';
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

/** HH:mm */
export function formatHora(date: Date): string {
  if (Number.isNaN(date.getTime())) return '';
  return `${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}
