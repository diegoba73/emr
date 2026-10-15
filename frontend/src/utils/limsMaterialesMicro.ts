/**
 * Cultivos de microbiología asociados a materiales de pedido.
 * Elegir un material NO auto-marca el cultivo: el operador lo pide a propósito
 * (orina no fuerza urocultivo; sangre no fuerza hemocultivo; etc.).
 */
import type { MaterialPedidoLims } from '../types/lims';

export function cultivosCodigosDeMateriales(
  materiales: Pick<MaterialPedidoLims, 'codigo' | 'cultivo_micro_codigo'>[]
): string[] {
  const codes = materiales
    .map((m) => (m.cultivo_micro_codigo || '').trim().toUpperCase())
    .filter(Boolean);
  return Array.from(new Set(codes));
}

/** Siempre vacío: no preseleccionar cultivos al agregar material. */
export function cultivosCodigosAutoPreselect(
  _materiales: Pick<MaterialPedidoLims, 'codigo' | 'cultivo_micro_codigo'>[]
): string[] {
  return [];
}

export function muestraPreferidaPorCultivoDeMateriales(
  materiales: Pick<MaterialPedidoLims, 'cultivo_micro_codigo' | 'muestra_micro_codigo'>[]
): Record<string, string> {
  const map: Record<string, string> = {};
  materiales.forEach((m) => {
    const cult = (m.cultivo_micro_codigo || '').trim();
    const muestra = (m.muestra_micro_codigo || '').trim();
    if (cult && muestra) {
      map[cult] = muestra;
      map[cult.toUpperCase()] = muestra;
    }
  });
  return map;
}

/**
 * Ajusta la lista de micro items al set de materiales:
 * - conserva cultivos que el operador ya marcó y siguen permitidos;
 * - no agrega cultivos solos (sin auto-preselect);
 * - quita cultivos de materiales que ya no están en el pedido.
 */
export function syncMicroItemsConMateriales<T extends { cultivo_codigo: string }>(
  prev: T[],
  opts: {
    permitidos: string[];
    autoPreselect: string[];
    buildItem: (cultivoCodigo: string) => T | null;
  }
): T[] {
  const allow = new Set(opts.permitidos.map((c) => c.toUpperCase()));
  const kept = allow.size
    ? prev.filter((i) => allow.has((i.cultivo_codigo || '').toUpperCase()))
    : [];
  const have = new Set(kept.map((i) => (i.cultivo_codigo || '').toUpperCase()));
  const added: T[] = [];
  for (const codigo of opts.autoPreselect) {
    const up = codigo.toUpperCase();
    if (have.has(up)) continue;
    const item = opts.buildItem(codigo);
    if (!item) continue;
    added.push(item);
    have.add(up);
  }
  if (!added.length && kept.length === prev.length) {
    const prevCodes = prev.map((i) => (i.cultivo_codigo || '').toUpperCase()).sort().join('|');
    const nextCodes = kept.map((i) => (i.cultivo_codigo || '').toUpperCase()).sort().join('|');
    if (prevCodes === nextCodes) return prev;
  }
  return [...kept, ...added];
}
