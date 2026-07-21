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
  if (!detalle || detalle === titulo || detalle === row.origen_solicitud) {
    return { titulo };
  }
  return { titulo, detalle };
}
