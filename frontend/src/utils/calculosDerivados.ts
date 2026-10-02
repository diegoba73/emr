/**
 * Parámetros clínicos derivados (perfil lipídico, bilirrubina, índices hemo, férrico).
 * Alineado a laboratorio/calculos_derivados.py y PDF ICPL de referencia.
 */

export const TG_MAX_FRIEDEWALD = 400;
export const RESULTADO_NO_CALCULABLE = 'No calculable con estos datos';
/** Factor habitual: transferrina (mg/dL) ≈ TIBC (µg/dL) × 0.8 */
export const FACTOR_TRANS_DESDE_TIBC = 0.8;

export function esResultadoNoCalculable(valor?: string | null): boolean {
  return valor?.trim() === RESULTADO_NO_CALCULABLE;
}

export const CODIGOS_CALCULADOS = new Set([
  'LDL',
  'VLDL',
  'COL_NO_LDL',
  'COL_RESID',
  'RATIO_CT_HDL',
  'BIL_I',
  'CF',
  'SAT_FE',
  'TRANS',
]);

export const FORMULA_LEUCO_CODIGOS = new Set([
  'NEUT_CAY',
  'NEUT_SEG',
  'EOS',
  'BAS',
  'LINF',
  'MONO',
]);

function roundHalfUp(value: number, places: number): number {
  const f = 10 ** places;
  return Math.round((value + Number.EPSILON) * f) / f;
}

function fmt(value: number, places: number): string {
  if (places === 0) return String(Math.round(value));
  const q = roundHalfUp(value, places);
  return String(q);
}

export function calcVldl(tg: number): number {
  return roundHalfUp(tg / 5, 0);
}

export function calcLdlFriedewald(colTot: number, hdl: number, tg: number): number | null {
  if (tg >= TG_MAX_FRIEDEWALD) return null;
  return roundHalfUp(colTot - hdl - tg / 5, 0);
}

export function calcColNoHdl(colTot: number, hdl: number): number {
  return roundHalfUp(colTot - hdl, 0);
}

export function calcColResidual(colTot: number, hdl: number, ldl: number): number {
  return roundHalfUp(colTot - hdl - ldl, 0);
}

export function calcRatioCtHdl(colTot: number, hdl: number): number | null {
  if (hdl <= 0) return null;
  return roundHalfUp(colTot / hdl, 2);
}

export function calcBilIndirecta(bilT: number, bilD: number): number | null {
  if (bilT < bilD) return null;
  return roundHalfUp(bilT - bilD, 2);
}

export function calcTibc(ferremia: number, uibc: number): number {
  return roundHalfUp(ferremia + uibc, 0);
}

export function calcSatTransferrina(ferremia: number, tibc: number): number | null {
  if (tibc <= 0) return null;
  return roundHalfUp((ferremia / tibc) * 100, 1);
}

export function calcTransferrinaDesdeTibc(tibc: number): number {
  return roundHalfUp(tibc * FACTOR_TRANS_DESDE_TIBC, 0);
}

export function calcAbsolutoFormula(pct: number, leucos: number): number | null {
  if (leucos < 0 || pct < 0) return null;
  return Math.round(pct * leucos / 100);
}

export function formatAbsolutoMm3(n: number): string {
  return Math.trunc(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

export type DerivadoValor = { numerico: number | null; informe: string };

/** Calcula derivados a partir de un mapa codigo → valor clínico. */
export function calcularDerivados(
  valores: Record<string, number | null | undefined>
): Record<string, DerivadoValor> {
  const out: Record<string, DerivadoValor> = {};
  const col = valores.COL_TOT;
  const hdl = valores.HDL;
  const tg = valores.TG;

  if (col != null && hdl != null) {
    const noHdl = calcColNoHdl(col, hdl);
    out.COL_NO_LDL = { numerico: noHdl, informe: fmt(noHdl, 0) };
    const ratio = calcRatioCtHdl(col, hdl);
    if (ratio != null) {
      out.RATIO_CT_HDL = { numerico: ratio, informe: fmt(ratio, 2) };
    }
    if (tg != null) {
      const vldl = calcVldl(tg);
      out.VLDL = { numerico: vldl, informe: fmt(vldl, 0) };
      const ldl = calcLdlFriedewald(col, hdl, tg);
      if (ldl != null) {
        out.LDL = { numerico: ldl, informe: fmt(ldl, 0) };
        const resid = calcColResidual(col, hdl, ldl);
        out.COL_RESID = { numerico: resid, informe: fmt(resid, 0) };
      } else {
        out.LDL = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
        out.COL_RESID = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
      }
    } else {
      out.VLDL = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
      out.LDL = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
      out.COL_RESID = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  }

  const bilT = valores.BIL_T;
  const bilD = valores.BIL_D;
  if (bilT != null && bilD != null) {
    const bilI = calcBilIndirecta(bilT, bilD);
    if (bilI != null) {
      out.BIL_I = { numerico: bilI, informe: fmt(bilI, 2) };
    } else {
      out.BIL_I = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  }

  const ferr = valores.FERR;
  const uibc = valores.UIBC;
  if (ferr != null && uibc != null) {
    const tibc = calcTibc(ferr, uibc);
    out.CF = { numerico: tibc, informe: fmt(tibc, 0) };
    const sat = calcSatTransferrina(ferr, tibc);
    if (sat != null) {
      out.SAT_FE = { numerico: sat, informe: fmt(sat, 1) };
    } else {
      out.SAT_FE = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
    const trans = calcTransferrinaDesdeTibc(tibc);
    out.TRANS = { numerico: trans, informe: fmt(trans, 0) };
  } else if (ferr != null || uibc != null) {
    out.CF = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    out.SAT_FE = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    out.TRANS = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
  }

  return out;
}

export function esCodigoCalculado(codigo?: string | null): boolean {
  return CODIGOS_CALCULADOS.has((codigo || '').trim().toUpperCase());
}
