import { MODALIDAD_OPTIONS } from '../modules/estudios/constants';
import type { EstudioModalidad, TipoEstudioComplementario } from '../types/estudios';

/** Catálogo API o, si está vacío, opciones por modalidad (ids negativos = solo modalidad al guardar). */
export function buildEstudioTipoCatalogOptions(
  catalog: TipoEstudioComplementario[]
): TipoEstudioComplementario[] {
  const activos = catalog.filter((t) => t.activo !== false);
  if (activos.length > 0) return activos;
  return MODALIDAD_OPTIONS.map((m, index) => ({
    id: -(index + 1),
    nombre: m.label,
    modalidad: m.value as EstudioModalidad,
    activo: true,
  }));
}

export function resolveEstudioModalidadFromTipoId(
  tipoId: string,
  options: TipoEstudioComplementario[]
): EstudioModalidad | undefined {
  const n = Number(tipoId);
  if (!Number.isFinite(n)) return undefined;
  const found = options.find((t) => t.id === n);
  return found?.modalidad;
}

export function isEstudioTipoCatalogFallbackId(tipoId: string): boolean {
  const n = Number(tipoId);
  return Number.isFinite(n) && n < 0;
}
