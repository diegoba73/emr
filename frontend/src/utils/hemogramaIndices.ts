/**
 * Índices hematimétricos VCM / CHCM (misma fórmula que conclusion_hemograma).
 * VCM (fL) ≈ HTO / HEMATIES × 10
 * CHCM (g/dL) ≈ HGB / HTO × 100
 */

export function calcVcmFl(hto: number, hematies: number): number | null {
  if (!Number.isFinite(hto) || !Number.isFinite(hematies) || hematies <= 0) return null;
  return Math.round((hto / hematies) * 10 * 10) / 10;
}

export function calcChcmGdl(hgb: number, hto: number): number | null {
  if (!Number.isFinite(hgb) || !Number.isFinite(hto) || hto <= 0) return null;
  return Math.round((hgb / hto) * 100 * 10) / 10;
}
