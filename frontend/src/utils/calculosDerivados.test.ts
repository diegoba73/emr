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
});
