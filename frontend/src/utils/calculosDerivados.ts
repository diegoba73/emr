/**
 * Parámetros clínicos derivados (lípido, hemo, férrico, clearance, orinas 24 hs, RAC,
 * TFG CKD-EPI, calcio iónico Zeisler).
 * Alineado a laboratorio/calculos_derivados.py y PDF ICPL de referencia.
 */

export const TG_MAX_FRIEDEWALD = 400;
export const RESULTADO_NO_CALCULABLE = 'No calculable con estos datos';
/** Factor habitual: transferrina (mg/dL) ≈ TIBC (µg/dL) × 0.8 */
export const FACTOR_TRANS_DESDE_TIBC = 0.8;
/** Minutos en 24 horas (denominador del clearance de creatinina). */
export const MINUTOS_24H = 1440;
/** Factor clínico mg/dL → mmol/L para calcio iónico estimado (Zeisler). */
export const FACTOR_CA_MG_DL_A_MMOL_L = 4.008;
/** CKD-EPI 2021: solo adultos. */
export const CKD_EPI_2021_EDAD_MIN = 18;
/** Estimable por fórmula pero editable (valor de equipo / EAB). */
export const CODIGOS_OVERRIDEABLES_ESTIMADOS = new Set(['CA_ION']);

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
  'CLEAR_CREA',
  'PROT_U_24',
  'NA_U24',
  'K_U24',
  'CL_U24',
  'MICROALB_24',
  'CA_U24',
  'MG_U24',
  'P_U24',
  'AU_U24',
  'UREA_U24',
  'CREA_U24',
  'RAC',
  'TFG',
]);

/** Medido (mg/dL) → calculado (mg/24 hs): conc × DIUR / 100. */
export const EXCRECION_MG_DL_A_24H: ReadonlyArray<readonly [string, string]> = [
  ['PROT_U_EQ', 'PROT_U_24'],
  ['CA_U', 'CA_U24'],
  ['MG_U', 'MG_U24'],
  ['P_U', 'P_U24'],
  ['AU_U', 'AU_U24'],
  ['UREA_U', 'UREA_U24'],
  ['CREA_U', 'CREA_U24'],
];

/** Medido (por L / mEq/L) → calculado (/24 hs): conc × DIUR / 1000. */
export const EXCRECION_POR_LITRO_A_24H: ReadonlyArray<
  readonly [string, string, number]
> = [
  ['NA_U', 'NA_U24', 0],
  ['K_U', 'K_U24', 0],
  ['CL_U', 'CL_U24', 0],
  ['MICROALB', 'MICROALB_24', 1],
];

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

/** Clearance (mL/min) = (creatinuria × diuresis) / (creatininemia × 1440). */
export function calcClearanceCreatinina(
  creati: number,
  creaU: number,
  diur: number
): number | null {
  if (creati <= 0) return null;
  return roundHalfUp((creaU * diur) / (creati * MINUTOS_24H), 1);
}

/** mg/24 hs = concentración (mg/dL) × diuresis (mL) / 100. */
export function calcExcrecionMgDlA24h(concMgDl: number, diurMl: number): number | null {
  if (diurMl <= 0) return null;
  return roundHalfUp((concMgDl * diurMl) / 100, 0);
}

/** Unidad/24 hs = concentración (por L) × diuresis (mL) / 1000. */
export function calcExcrecionPorLitroA24h(
  concPorL: number,
  diurMl: number,
  places = 0
): number | null {
  if (diurMl <= 0) return null;
  return roundHalfUp((concPorL * diurMl) / 1000, places);
}

/** RAC (mg/g) = (microalbuminuria mg/L ÷ creatinuria mg/dL) × 100. */
export function calcRac(microalbMgL: number, creaUMgDl: number): number | null {
  if (creaUMgDl <= 0) return null;
  return roundHalfUp((microalbMgL / creaUMgDl) * 100, 1);
}

/**
 * eGFR CKD-EPI 2021 (creatinina, sin raza), mL/min/1.73 m².
 * Adultos ≥18; sexo M/F.
 */
export function calcTfgCkdEpi2021(
  creatiMgDl: number,
  edadAnos: number,
  sexo: string | null | undefined
): number | null {
  const sexoN = (sexo || '').trim().toUpperCase();
  if (sexoN !== 'M' && sexoN !== 'F') return null;
  if (!Number.isFinite(edadAnos) || edadAnos < CKD_EPI_2021_EDAD_MIN) return null;
  if (!Number.isFinite(creatiMgDl) || creatiMgDl <= 0) return null;

  const kappa = sexoN === 'F' ? 0.7 : 0.9;
  const alpha = sexoN === 'F' ? -0.241 : -0.302;
  const sexFactor = sexoN === 'F' ? 1.012 : 1;
  const ratio = creatiMgDl / kappa;
  const minTerm = Math.pow(Math.min(ratio, 1), alpha);
  const maxTerm = Math.pow(Math.max(ratio, 1), -1.2);
  const ageTerm = Math.pow(0.9938, Math.trunc(edadAnos));
  return roundHalfUp(142 * minTerm * maxTerm * ageTerm * sexFactor, 0);
}

export type DerivadosContexto = {
  edadAnos?: number | null;
  sexo?: string | null;
};

/** Ca iónico estimado (mg/dL) por Zeisler: (6.25×CA − 0.375×PROT) / (PROT + 6.5). */
export function calcCaIonZeislerMgDl(caMgDl: number, protGDl: number): number | null {
  const denom = protGDl + 6.5;
  if (denom <= 0) return null;
  return roundHalfUp((6.25 * caMgDl - 0.375 * protGDl) / denom, 2);
}

/** Ca iónico estimado en mmol/L (Zeisler mg/dL ÷ 4.008). */
export function calcCaIonZeislerMmolL(caMgDl: number, protGDl: number): number | null {
  const mg = calcCaIonZeislerMgDl(caMgDl, protGDl);
  if (mg == null) return null;
  return roundHalfUp(mg / FACTOR_CA_MG_DL_A_MMOL_L, 2);
}

export function calcAbsolutoFormula(pct: number, leucos: number): number | null {
  if (leucos < 0 || pct < 0) return null;
  return Math.round(pct * leucos / 100);
}

/** Recuento absoluto de fórmula leucocitaria (junto al %): p. ej. «abs. 4.185/mm³». */
export function formatAbsolutoMm3(n: number): string {
  const num = Math.trunc(n)
    .toString()
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  return `abs. ${num}/mm³`;
}

/**
 * Valor de fórmula para informe/vista clínica: «45%  ·  abs. 4.185/mm³».
 * El % va pegado al porcentaje cargado, no al absoluto.
 */
export function formatValorFormulaLeucoConAbsoluto(pctTexto: string, abs: number): string {
  const base = (pctTexto || '').trim();
  if (!base) return formatAbsolutoMm3(abs);
  const conPct = /%\s*$/.test(base) ? base.replace(/\s*%\s*$/, '%') : `${base}%`;
  return `${conPct}  ·  ${formatAbsolutoMm3(abs)}`;
}

export type DerivadoValor = { numerico: number | null; informe: string };

/** Calcula derivados a partir de un mapa codigo → valor clínico. */
export function calcularDerivados(
  valores: Record<string, number | null | undefined>,
  ctx?: DerivadosContexto
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

  const creati = valores.CREATI;
  const creaU = valores.CREA_U;
  const diur = valores.DIUR;
  if (creati != null && creaU != null && diur != null) {
    const clear = calcClearanceCreatinina(creati, creaU, diur);
    if (clear != null) {
      out.CLEAR_CREA = { numerico: clear, informe: fmt(clear, 1) };
    } else {
      out.CLEAR_CREA = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  } else if (creati != null || creaU != null) {
    out.CLEAR_CREA = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
  }

  for (const [medido, calculado] of EXCRECION_MG_DL_A_24H) {
    const conc = valores[medido];
    if (conc != null && diur != null) {
      const exc = calcExcrecionMgDlA24h(conc, diur);
      if (exc != null) {
        out[calculado] = { numerico: exc, informe: fmt(exc, 0) };
      } else {
        out[calculado] = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
      }
    } else if (conc != null) {
      out[calculado] = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  }

  for (const [medido, calculado, places] of EXCRECION_POR_LITRO_A_24H) {
    const conc = valores[medido];
    if (conc != null && diur != null) {
      const exc = calcExcrecionPorLitroA24h(conc, diur, places);
      if (exc != null) {
        out[calculado] = { numerico: exc, informe: fmt(exc, places) };
      } else {
        out[calculado] = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
      }
    } else if (conc != null) {
      out[calculado] = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  }

  const microalb = valores.MICROALB;
  if (microalb != null && creaU != null) {
    const rac = calcRac(microalb, creaU);
    if (rac != null) {
      out.RAC = { numerico: rac, informe: fmt(rac, 1) };
    } else {
      out.RAC = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  } else if (microalb != null || creaU != null) {
    out.RAC = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
  }

  if (creati != null) {
    const edad = ctx?.edadAnos;
    const tfg =
      edad != null && Number.isFinite(edad)
        ? calcTfgCkdEpi2021(creati, edad, ctx?.sexo)
        : null;
    if (tfg != null) {
      out.TFG = { numerico: tfg, informe: fmt(tfg, 0) };
    } else {
      out.TFG = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  }

  const ca = valores.CA;
  const protT = valores.PROT_T;
  if (ca != null && protT != null) {
    const caIon = calcCaIonZeislerMmolL(ca, protT);
    if (caIon != null) {
      out.CA_ION = { numerico: caIon, informe: fmt(caIon, 2) };
    } else {
      out.CA_ION = { numerico: null, informe: RESULTADO_NO_CALCULABLE };
    }
  }

  return out;
}

export function esCodigoCalculado(codigo?: string | null): boolean {
  return CODIGOS_CALCULADOS.has((codigo || '').trim().toUpperCase());
}
