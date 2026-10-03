import { estudioAdmiteExamenOrina, normalizarExamenOrina } from './limsExamenOrinaMicro';

describe('limsExamenOrinaMicro', () => {
  it('normaliza y descarta claves desconocidas', () => {
    const data = normalizarExamenOrina({ ORI_NIT: ' + ', HACK: 'x', ORI_PH: 6 });
    expect(data.ORI_NIT).toBe('+');
    expect(data.ORI_PH).toBe('6');
    expect((data as Record<string, string>).HACK).toBeUndefined();
  });

  it('incluye glucosa en tira reactiva', () => {
    const data = normalizarExamenOrina({ ORI_GLU: '++' });
    expect(data.ORI_GLU).toBe('++');
  });

  it('admite urocultivo por flag o tipo_estudio', () => {
    expect(estudioAdmiteExamenOrina({ admite_examen_orina: true })).toBe(true);
    expect(estudioAdmiteExamenOrina({ tipo_estudio: 'UROCULTIVO' })).toBe(true);
    expect(estudioAdmiteExamenOrina({ tipo_estudio: 'HEMOCULTIVO' })).toBe(false);
  });
});
