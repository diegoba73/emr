import {
  RESULTADO_NO_CALCULABLE,
  calcClearanceCreatinina,
  calcExcrecionMgDlA24h,
  calcExcrecionPorLitroA24h,
  calcLdlFriedewald,
  calcRac,
  calcularDerivados,
} from './calculosDerivados';

describe('calculosDerivados Corte A', () => {
  it('no calcula LDL con TG >= 400', () => {
    expect(calcLdlFriedewald(200, 50, 400)).toBeNull();
    const out = calcularDerivados({ COL_TOT: 200, HDL: 50, TG: 450 });
    expect(out.LDL?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.COL_RESID?.informe).toBe(RESULTADO_NO_CALCULABLE);
  });

  it('sin TG no inventa LDL/VLDL', () => {
    const out = calcularDerivados({ COL_TOT: 200, HDL: 50 });
    expect(out.LDL?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.VLDL?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.COL_NO_LDL?.numerico).toBe(150);
  });

  it('sin COL/HDL no emite lipídicos', () => {
    const out = calcularDerivados({ TG: 150 });
    expect(out.LDL).toBeUndefined();
    expect(out.VLDL).toBeUndefined();
  });

  it('BIL_I inválida cuando BD > BT', () => {
    const out = calcularDerivados({ BIL_T: 0.5, BIL_D: 0.8 });
    expect(out.BIL_I?.informe).toBe(RESULTADO_NO_CALCULABLE);
  });

  it('perfil férrico calcula TIBC, saturación y transferrina', () => {
    const out = calcularDerivados({ FERR: 100, UIBC: 250 });
    expect(out.CF?.numerico).toBe(350);
    expect(out.SAT_FE?.numerico).toBe(28.6);
    expect(out.TRANS?.numerico).toBe(280);
  });

  it('perfil férrico incompleto marca no calculable', () => {
    const out = calcularDerivados({ FERR: 100 });
    expect(out.CF?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.SAT_FE?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.TRANS?.informe).toBe(RESULTADO_NO_CALCULABLE);
  });

  it('clearance calcula (CREA_U × DIUR) / (CREATI × 1440)', () => {
    expect(calcClearanceCreatinina(1.0, 100, 1500)).toBe(104.2);
    const out = calcularDerivados({ CREATI: 1.0, CREA_U: 100, DIUR: 1500 });
    expect(out.CLEAR_CREA?.numerico).toBe(104.2);
    expect(out.CLEAR_CREA?.informe).toBe('104.2');
  });

  it('clearance incompleto o creatininemia 0 marca no calculable', () => {
    expect(calcClearanceCreatinina(0, 100, 1500)).toBeNull();
    expect(calcularDerivados({ CREATI: 1.0, CREA_U: 100 }).CLEAR_CREA?.informe).toBe(
      RESULTADO_NO_CALCULABLE
    );
    expect(
      calcularDerivados({ CREATI: 0, CREA_U: 100, DIUR: 1500 }).CLEAR_CREA?.informe
    ).toBe(RESULTADO_NO_CALCULABLE);
  });

  it('orina 24 hs: proteinuria / ionograma / microalbúmina', () => {
    expect(calcExcrecionMgDlA24h(80, 1500)).toBe(1200);
    expect(calcExcrecionPorLitroA24h(100, 1500)).toBe(150);
    const out = calcularDerivados({
      PROT_U_EQ: 80,
      NA_U: 100,
      K_U: 40,
      CL_U: 90,
      MICROALB: 20,
      DIUR: 1500,
    });
    expect(out.PROT_U_24?.numerico).toBe(1200);
    expect(out.NA_U24?.numerico).toBe(150);
    expect(out.K_U24?.numerico).toBe(60);
    expect(out.CL_U24?.numerico).toBe(135);
    expect(out.MICROALB_24?.numerico).toBe(30);
  });

  it('orina 24 hs sin diuresis marca no calculable', () => {
    const out = calcularDerivados({ PROT_U_EQ: 80, NA_U: 100, MICROALB: 25 });
    expect(out.PROT_U_24?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.NA_U24?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(out.MICROALB_24?.informe).toBe(RESULTADO_NO_CALCULABLE);
  });

  it('RAC = (MICROALB / CREA_U) × 100', () => {
    expect(calcRac(30, 100)).toBe(30);
    const out = calcularDerivados({ MICROALB: 30, CREA_U: 100 });
    expect(out.RAC?.numerico).toBe(30);
    expect(out.RAC?.informe).toBe('30');
  });

  it('RAC incompleto o creatinuria cero no calculable', () => {
    expect(calcularDerivados({ MICROALB: 30 }).RAC?.informe).toBe(RESULTADO_NO_CALCULABLE);
    expect(calcularDerivados({ MICROALB: 30, CREA_U: 0 }).RAC?.informe).toBe(
      RESULTADO_NO_CALCULABLE
    );
  });
});
