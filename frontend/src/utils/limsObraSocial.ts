import type { ChipProps } from '@mui/material';

export type EstadoObraSocialLims =
  | ''
  | 'AUTORIZADO'
  | 'DEBE_ORDEN'
  | 'FALTA_AUTORIZACION'
  | 'DEBE_ABONAR';

export const ESTADOS_OBRA_SOCIAL: Array<{
  value: EstadoObraSocialLims;
  label: string;
}> = [
  { value: 'AUTORIZADO', label: 'Autorizado' },
  { value: 'DEBE_ORDEN', label: 'Debe orden' },
  { value: 'FALTA_AUTORIZACION', label: 'Falta autorización' },
  { value: 'DEBE_ABONAR', label: 'Debe abonar' },
];

const LABEL: Record<string, string> = {
  AUTORIZADO: 'Autorizado',
  DEBE_ORDEN: 'Debe orden',
  FALTA_AUTORIZACION: 'Falta autorización',
  DEBE_ABONAR: 'Debe abonar',
};

export function labelEstadoObraSocial(estado?: string | null): string {
  const code = String(estado || '').trim();
  if (!code) return 'Sin cargar';
  return LABEL[code] || code;
}

export function formatMontoDebeAbonar(monto?: string | number | null): string | null {
  if (monto === null || monto === undefined || monto === '') return null;
  const n = typeof monto === 'number' ? monto : Number(String(monto).replace(',', '.'));
  if (!Number.isFinite(n)) return null;
  return n.toLocaleString('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Etiqueta de chip/resumen: incluye monto solo si DEBE_ABONAR y hay valor. */
export function labelObraSocialConMonto(
  estado?: string | null,
  monto?: string | number | null
): string {
  const base = labelEstadoObraSocial(estado);
  if (normalizeEstadoObraSocial(estado) !== 'DEBE_ABONAR') return base;
  const fmt = formatMontoDebeAbonar(monto);
  return fmt ? `${base} — ${fmt}` : base;
}

export function colorEstadoObraSocial(
  estado?: string | null
): ChipProps['color'] {
  switch (String(estado || '').trim()) {
    case 'AUTORIZADO':
      return 'success';
    case 'DEBE_ORDEN':
      return 'warning';
    case 'FALTA_AUTORIZACION':
      return 'error';
    case 'DEBE_ABONAR':
      return 'info';
    default:
      return 'default';
  }
}

export function normalizeEstadoObraSocial(estado?: string | null): EstadoObraSocialLims {
  const code = String(estado || '').trim().toUpperCase();
  if (
    code === 'AUTORIZADO' ||
    code === 'DEBE_ORDEN' ||
    code === 'FALTA_AUTORIZACION' ||
    code === 'DEBE_ABONAR'
  ) {
    return code;
  }
  return '';
}

const ORIGENES_REQUIEREN_AUTORIZACION = new Set([
  'AMBULATORIO_CEHTA',
  'AMBULATORIO_ICPL',
  'EXTERNO_CEHTA',
  'EXTERNO_ICPL',
]);

export function origenRequiereAutorizacionObraSocial(origen?: string | null): boolean {
  return ORIGENES_REQUIEREN_AUTORIZACION.has(String(origen || ''));
}

export function ordenPuedeValidarObraSocial(orden: {
  origen_solicitud?: string | null;
  estado_obra_social?: string | null;
  requiere_autorizacion_obra_social?: boolean;
  obra_social_permite_validar?: boolean;
}): boolean {
  if (typeof orden.obra_social_permite_validar === 'boolean') {
    return orden.obra_social_permite_validar;
  }
  const requiere =
    typeof orden.requiere_autorizacion_obra_social === 'boolean'
      ? orden.requiere_autorizacion_obra_social
      : origenRequiereAutorizacionObraSocial(orden.origen_solicitud);
  if (!requiere) return true;
  return normalizeEstadoObraSocial(orden.estado_obra_social) === 'AUTORIZADO';
}
