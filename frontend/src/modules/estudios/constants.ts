import type { EstudioEstado, EstudioPractica } from '../../types/estudios';
import type { TipoEstudioComplementario } from '../../types/estudios';
import { CEHTA_PRACTICA_OPTIONS, LEGACY_PRACTICA_OPTIONS } from './practicaOptionsCehta';

/** Catálogo UI para selectores: solo prácticas CEHTA (sin códigos históricos). */
export const PRACTICA_OPTIONS: { value: EstudioPractica; label: string }[] = [
  ...CEHTA_PRACTICA_OPTIONS,
];

/** @deprecated Use PRACTICA_OPTIONS */
export const MODALIDAD_OPTIONS = PRACTICA_OPTIONS;

const LEGACY_PRACTICA_CODES = new Set(LEGACY_PRACTICA_OPTIONS.map((o) => o.value));

export function isLegacyPractica(code: string | null | undefined): boolean {
  return Boolean(code && LEGACY_PRACTICA_CODES.has(code));
}

export function labelPractica(
  code: string | null | undefined,
  extraOptions?: { value: string; label: string }[]
): string {
  if (!code) return '—';
  const fromExtra = extraOptions?.find((o) => o.value === code);
  if (fromExtra) return fromExtra.label;
  const fromCehta = CEHTA_PRACTICA_OPTIONS.find((o) => o.value === code);
  if (fromCehta) return fromCehta.label;
  const fromLegacy = LEGACY_PRACTICA_OPTIONS.find((o) => o.value === code);
  if (fromLegacy) return fromLegacy.label;
  return code;
}

/** Opciones desde tipos activos del API (sin prácticas históricas). */
export function practicaOptionsFromTipos(
  tipos: TipoEstudioComplementario[]
): { value: string; label: string }[] {
  const seen = new Set<string>();
  const out: { value: string; label: string }[] = [];
  for (const t of tipos) {
    if (!t.activo && t.activo !== undefined) continue;
    const value = (t.practica || t.codigo || '').trim();
    if (!value || seen.has(value) || isLegacyPractica(value)) continue;
    seen.add(value);
    out.push({ value, label: t.nombre || value });
  }
  out.sort((a, b) => a.label.localeCompare(b.label, 'es'));
  return out.length ? out : PRACTICA_OPTIONS;
}

export const ESTADO_LABELS: Record<EstudioEstado, string> = {
  SOLICITADO: 'Solicitado',
  CONFIRMADO: 'Confirmado',
  REALIZADO: 'Realizado',
  INFORMADO: 'Informado',
  VALIDADO: 'Validado',
  ENTREGADO: 'Entregado',
  ANULADO: 'Anulado',
};

export const ESTADO_CHIP_COLOR: Record<
  EstudioEstado,
  'default' | 'info' | 'warning' | 'success' | 'error' | 'primary' | 'secondary'
> = {
  SOLICITADO: 'info',
  CONFIRMADO: 'success',
  REALIZADO: 'primary',
  INFORMADO: 'warning',
  VALIDADO: 'secondary',
  ENTREGADO: 'success',
  ANULADO: 'error',
};

export const ORIGEN_OPTIONS = [
  { value: 'INTERNO', label: 'Interno' },
  { value: 'EXTERNO', label: 'Externo' },
  { value: 'IMPORTADO_HISTORICO', label: 'Importado histórico' },
];

export const ARCHIVO_ROL_OPTIONS = [
  { value: 'IMAGEN', label: 'Imagen' },
  { value: 'INFORME_ESCANEADO', label: 'Informe escaneado' },
  { value: 'DICOM_ZIP', label: 'DICOM / ZIP' },
  { value: 'OTRO', label: 'Otro' },
];
