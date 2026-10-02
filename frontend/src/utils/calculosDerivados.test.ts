import {
  RESULTADO_NO_CALCULABLE,
  calcLdlFriedewald,
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
});
