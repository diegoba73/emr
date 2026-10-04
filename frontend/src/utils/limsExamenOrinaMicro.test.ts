import {
  VALOR_NO_CONTIENE,
  estudioAdmiteExamenOrina,
  examenOrinaVacio,
  normalizarExamenOrina,
} from './limsExamenOrinaMicro';

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

  it('vacío prellena NO CONTIENE en tira y sedimento cualitativos', () => {
    const vacio = examenOrinaVacio();
    expect(vacio.ORI_GLU).toBe(VALOR_NO_CONTIENE);
    expect(vacio.ORI_LEU).toBe(VALOR_NO_CONTIENE);
    expect(vacio.ORI_CRIS).toBe(VALOR_NO_CONTIENE);
    expect(vacio.ORI_COLOR).toBe('');
    expect(vacio.ORI_PH).toBe('');
    expect(vacio.ORI_CONC).toBe('');
  });

  it('admite urocultivo por flag o tipo_estudio', () => {
    expect(estudioAdmiteExamenOrina({ admite_examen_orina: true })).toBe(true);
    expect(estudioAdmiteExamenOrina({ tipo_estudio: 'UROCULTIVO' })).toBe(true);
    expect(estudioAdmiteExamenOrina({ tipo_estudio: 'HEMOCULTIVO' })).toBe(false);
  });
});
