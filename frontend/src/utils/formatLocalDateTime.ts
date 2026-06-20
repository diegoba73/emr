/**
 * Serializa un Date construido en hora local a string sin usar toISOString (evita Z / UTC).
 */

const pad2 = (n: number) => String(n).padStart(2, '0');

export function formatLocalDateTimeSeconds(d: Date): string {
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(
    d.getMinutes()
  )}:${pad2(d.getSeconds())}`;
}
