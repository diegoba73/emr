/**
 * Proteinograma: % = g/dL_fracción / PROT_T × 100 (alineado al backend).
 */
export const CODIGO_PROT_T = 'PROT_T';
export const CODIGOS_ELP_FRACCIONES = [
  'ELP_ALB',
  'ELP_A1',
  'ELP_A2',
  'ELP_B1',
  'ELP_B2',
  'ELP_GAM',
] as const;

export type CodigoElpFraccion = (typeof CODIGOS_ELP_FRACCIONES)[number];

export function esCodigoElpFraccion(codigo?: string | null): codigo is CodigoElpFraccion {
  const c = (codigo || '').trim().toUpperCase();
  return (CODIGOS_ELP_FRACCIONES as readonly string[]).includes(c);
}

export function porcentajeFraccionElp(
  gdlFraccion: number | null | undefined,
  protT: number | null | undefined
): number | null {
  if (gdlFraccion == null || protT == null) return null;
  if (!Number.isFinite(gdlFraccion) || !Number.isFinite(protT) || protT === 0) return null;
  return Math.round((gdlFraccion / protT) * 1000) / 10;
}

export function formatPctElp(pct: number | null): string {
  if (pct == null || !Number.isFinite(pct)) return '';
  return `${pct.toFixed(1).replace('.', ',')} %`;
}
