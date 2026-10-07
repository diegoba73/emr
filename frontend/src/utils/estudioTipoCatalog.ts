import { PRACTICA_OPTIONS, isLegacyPractica } from '../modules/estudios/constants';
import type { EstudioPractica, TipoEstudioComplementario } from '../types/estudios';

/** Catálogo API (sin legacy) o, si está vacío, opciones CEHTA (ids negativos = solo práctica). */
export function buildEstudioTipoCatalogOptions(
  catalog: TipoEstudioComplementario[]
): TipoEstudioComplementario[] {
  const activos = catalog.filter(
    (t) => t.activo !== false && !isLegacyPractica(t.practica || t.codigo || '')
  );
  if (activos.length > 0) return activos;
  return PRACTICA_OPTIONS.map((m, index) => ({
    id: -(index + 1),
    nombre: m.label,
    practica: m.value as EstudioPractica,
    activo: true,
  }));
}

export function resolveEstudioPracticaFromTipoId(
  tipoId: string,
  options: TipoEstudioComplementario[]
): EstudioPractica | undefined {
  const n = Number(tipoId);
  if (!Number.isFinite(n)) return undefined;
  const found = options.find((t) => t.id === n);
  return found?.practica;
}

/** @deprecated Use resolveEstudioPracticaFromTipoId */
export const resolveEstudioModalidadFromTipoId = resolveEstudioPracticaFromTipoId;

export function isEstudioTipoCatalogFallbackId(tipoId: string): boolean {
  const n = Number(tipoId);
  return Number.isFinite(n) && n < 0;
}
