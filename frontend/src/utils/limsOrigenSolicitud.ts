import type { OrigenSolicitudLims } from '../types/lims';

export const ORIGEN_SOLICITUD_LIMS_OPTIONS: Array<{
  value: OrigenSolicitudLims;
  label: string;
  group: 'Internación' | 'Guardia' | 'Ambulatorio' | 'Ambulatorio externo';
}> = [
  { value: 'INTERNACION_UCO', label: 'Internación — UCO', group: 'Internación' },
  { value: 'INTERNACION_UCE', label: 'Internación — UCE', group: 'Internación' },
  { value: 'GUARDIA', label: 'Guardia — ICPL', group: 'Guardia' },
  { value: 'AMBULATORIO_CEHTA', label: 'Ambulatorio — CEHTA', group: 'Ambulatorio' },
  { value: 'AMBULATORIO_ICPL', label: 'Ambulatorio — ICPL', group: 'Ambulatorio' },
  { value: 'EXTERNO_CEHTA', label: 'Ambulatorio externo — CEHTA', group: 'Ambulatorio externo' },
  { value: 'EXTERNO_ICPL', label: 'Ambulatorio externo — ICPL', group: 'Ambulatorio externo' },
];

const LABELS: Record<OrigenSolicitudLims, string> = Object.fromEntries(
  ORIGEN_SOLICITUD_LIMS_OPTIONS.map((o) => [o.value, o.label])
) as Record<OrigenSolicitudLims, string>;

export function labelOrigenSolicitudLims(
  codigo: OrigenSolicitudLims | string | null | undefined,
  display?: string | null
): string {
  if (display) return display;
  if (!codigo) return '—';
  return LABELS[codigo as OrigenSolicitudLims] || codigo;
}

export function esOrigenAmbulatorioExterno(
  codigo: OrigenSolicitudLims | string | null | undefined
): boolean {
  return codigo === 'EXTERNO_CEHTA' || codigo === 'EXTERNO_ICPL';
}

/** Ambulatorio CEHTA/ICPL o receta externa (alineado a backend ``es_origen_ambulatorio``). */
export function esOrigenAmbulatorio(
  codigo: OrigenSolicitudLims | string | null | undefined
): boolean {
  const o = (codigo || '').toUpperCase();
  if (
    o === 'AMBULATORIO_CEHTA' ||
    o === 'AMBULATORIO_ICPL' ||
    o === 'EXTERNO_CEHTA' ||
    o === 'EXTERNO_ICPL'
  ) {
    return true;
  }
  // Legacy
  return o === 'EMR' || o === 'EXTERNO_PAPEL';
}

export function esOrigenInternacion(
  codigo: OrigenSolicitudLims | string | null | undefined
): boolean {
  return codigo === 'INTERNACION_UCO' || codigo === 'INTERNACION_UCE';
}

/** Internación o guardia: bloqueo de frecuencia al pedir. Ambulatorio/externo: no. */
export function origenExigeBloqueoFrecuenciaEnsayos(
  codigo: OrigenSolicitudLims | string | null | undefined
): boolean {
  const o = (codigo || '').toUpperCase();
  if (o.startsWith('AMBULATORIO') || o.startsWith('EXTERNO')) return false;
  return true;
}

/**
 * Origen LIMS sugerido según el sector de la cama (alineado a backend
 * ``origen_solicitud._sector_es_uco/_uce``).
 */
export function origenLimsDesdeSectorInternacion(
  sectorNombre: string | null | undefined
): OrigenSolicitudLims | null {
  const n = (sectorNombre || '').toUpperCase();
  if (!n.trim()) return null;
  if (n.includes('UCE')) return 'INTERNACION_UCE';
  if (n.includes('UCO')) return 'INTERNACION_UCO';
  // Internación en sector genérico → misma convención que el backend.
  return 'INTERNACION_UCE';
}

export interface OrigenProcedenciaCell {
  titulo: string;
  detalle?: string;
}

/** Título (UCO, CEHTA, guardia…) + detalle clínico (consultorio, cama, recurso). */
export function formatOrigenProcedenciaCell(row: {
  origen_solicitud?: OrigenSolicitudLims | string | null;
  origen_solicitud_display?: string | null;
  procedencia_display?: string | null;
}): OrigenProcedenciaCell {
  const titulo = labelOrigenSolicitudLims(row.origen_solicitud, row.origen_solicitud_display);
  const detalle = (row.procedencia_display || '').trim();
  const detalleNorm = detalle.toLowerCase();
  const tituloNorm = titulo.toLowerCase();
  const detalleRepiteTitulo =
    !detalle ||
    detalleNorm === tituloNorm ||
    detalle === row.origen_solicitud ||
    tituloNorm.startsWith(detalleNorm + ' —') ||
    tituloNorm.startsWith(detalleNorm + ' -') ||
    tituloNorm.startsWith(detalleNorm + ' ');
  if (detalleRepiteTitulo) {
    return { titulo };
  }
  return { titulo, detalle };
}

export type OrigenParaLugarExtraccion = {
  origen_solicitud?: OrigenSolicitudLims | string | null;
  origen_solicitud_display?: string | null;
  procedencia_display?: string | null;
};

/**
 * Sugerencia editable de lugar de extracción a partir del origen/procedencia de la orden.
 * Prefiere el detalle clínico (p. ej. cama) cuando aporta más que el título de origen.
 */
export function sugerirLugarExtraccionDesdeOrigen(row: OrigenParaLugarExtraccion | null | undefined): string {
  if (!row) return '';
  const { titulo, detalle } = formatOrigenProcedenciaCell(row);
  const preferido = (detalle || titulo || '').trim();
  if (!preferido || preferido === '—') return '';
  return preferido;
}
