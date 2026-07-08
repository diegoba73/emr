/** Utilidades de fecha local para navegación diaria en órdenes LIMS. */

export function startOfLocalDay(d: Date = new Date()): Date {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
}

export function addLocalDays(d: Date, days: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + days);
  return x;
}

/** ISO date (YYYY-MM-DD) en zona horaria local — alineado con filtro backend `fecha`. */
export function formatFechaLocal(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function parseFechaLocal(iso: string): Date {
  const [y, m, d] = iso.split('-').map(Number);
  return startOfLocalDay(new Date(y, (m || 1) - 1, d || 1));
}

export function labelDiaOrden(d: Date, ref: Date = startOfLocalDay()): string {
  const key = formatFechaLocal(d);
  if (key === formatFechaLocal(ref)) return 'Hoy';
  if (key === formatFechaLocal(addLocalDays(ref, -1))) return 'Ayer';
  return d.toLocaleDateString('es-AR', { weekday: 'short', day: 'numeric', month: 'short' });
}

/** Días consecutivos hacia atrás desde hoy (índice 0 = hoy). */
export function buildDiasLaboratorio(cantidad: number, desde: Date = new Date()): Date[] {
  const hoy = startOfLocalDay(desde);
  return Array.from({ length: Math.max(1, cantidad) }, (_, i) => addLocalDays(hoy, -i));
}

/** Cuántos días de pestañas hace falta para incluir `target` respecto de `ref` (por defecto hoy). */
export function diasVisiblesParaIncluir(target: Date, minimo = 7, ref: Date = new Date()): number {
  const hoy = startOfLocalDay(ref);
  const t = startOfLocalDay(target);
  const diffDias = Math.round((hoy.getTime() - t.getTime()) / 86_400_000);
  if (diffDias < 0) return minimo;
  return Math.max(minimo, diffDias + 1);
}
