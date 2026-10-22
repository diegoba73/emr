/**
 * Creatininuria (CREA_U): valor del CM260 con orina diluida 1:20.
 * En órdenes nuevas el backend multiplica ×20; el operador tipea el valor del equipo.
 */

export const CODIGO_CREATINURIA = 'CREA_U';
export const FACTOR_DILUCION_CREATINURIA = 20;

export function esCreatininuria(codigo?: string | null): boolean {
  return (codigo || '').trim().toUpperCase() === CODIGO_CREATINURIA;
}

/** Formatea número clínico/equipo sin ceros basura (5, 5.2, 100). */
export function formatCreatinuriaNumero(n: number): string {
  if (!Number.isFinite(n)) return '';
  const rounded = Math.round(n * 10000) / 10000;
  const text = String(rounded);
  if (!text.includes('.')) return text;
  return text.replace(/\.?0+$/, '');
}

/** Valor de equipo (CM260) a partir del clínico persistido. */
export function equipoDesdeClinicoCreatinuria(clinico: number): number {
  return clinico / FACTOR_DILUCION_CREATINURIA;
}

/** Valor clínico (informe / RAC / clearance) desde lectura CM260. */
export function clinicoDesdeEquipoCreatinuria(equipo: number): number {
  return Math.round(equipo * FACTOR_DILUCION_CREATINURIA * 10000) / 10000;
}

export function parseNumeroCarga(raw: string | number | null | undefined): number | null {
  if (raw === null || raw === undefined || raw === '') return null;
  const n = Number(String(raw).trim().replace(',', '.'));
  return Number.isFinite(n) ? n : null;
}
