/**
 * Índices hematimétricos VCM / HCM / CHCM (misma fórmula que calculos_derivados).
 * VCM (fL) ≈ HTO / HEMATIES × 10
 * HCM (pg) ≈ HGB / HEMATIES × 10
 * CHCM (g/dL) ≈ HGB / HTO × 100
 */

function round2(value: number): number {
  return Math.round(value * 100) / 100;
}

export function calcVcmFl(hto: number, hematies: number): number | null {
  if (!Number.isFinite(hto) || !Number.isFinite(hematies) || hematies <= 0) return null;
  return round2((hto / hematies) * 10);
}

export function calcHcmPg(hgb: number, hematies: number): number | null {
  if (!Number.isFinite(hgb) || !Number.isFinite(hematies) || hematies <= 0) return null;
  return round2((hgb / hematies) * 10);
}

export function calcChcmGdl(hgb: number, hto: number): number | null {
  if (!Number.isFinite(hgb) || !Number.isFinite(hto) || hto <= 0) return null;
  return round2((hgb / hto) * 100);
}
