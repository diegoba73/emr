import {
  estudioAdmiteExamenFresco,
  examenFrescoVacio,
  normalizarExamenFresco,
  seccionesExamenDirecto,
  TITULO_APARTADO_UI,
  tituloUiExamenFresco,
} from './limsExamenFrescoMicro';

describe('limsExamenFrescoMicro', () => {
  it('normaliza y descarta claves desconocidas', () => {
    const data = normalizarExamenFresco({
      EXF_CEL: ' 6-10 por campo ',
      HACK: 'x',
      EXF_GRAM: 'BGN',
    });
    expect(data.EXF_CEL).toBe('6-10 por campo');
    expect(data.EXF_GRAM).toBe('BGN');
    expect((data as Record<string, string>).HACK).toBeUndefined();
  });

  it('vacío deja campos en blanco', () => {
    const vacio = examenFrescoVacio();
    expect(vacio.EXF_CEL).toBe('');
    expect(vacio.EXF_MICOL).toBe('');
    expect(vacio.EXF_GRAM).toBe('');
  });

  it('técnicas por cultivo', () => {
    expect(seccionesExamenDirecto({ tipo_estudio: 'VAGINAL' }).map((s) => s.tecnica)).toEqual([
      'fresco',
      'koh',
    ]);
    expect(seccionesExamenDirecto({ tipo_estudio: 'ESPUTO' }).map((s) => s.tecnica)).toEqual([
      'gram',
    ]);
    expect(
      seccionesExamenDirecto({ tipo_estudio: 'ASPIRADO_TRAQUEAL_BRONQUIAL' }).map((s) => s.tecnica)
    ).toEqual(['gram']);
    expect(seccionesExamenDirecto({ tipo_estudio: 'LCR' }).map((s) => s.tecnica)).toEqual([
      'fresco',
      'gram',
    ]);
    expect(seccionesExamenDirecto({ tipo_estudio: 'COPROCULTIVO' }).map((s) => s.tecnica)).toEqual([
      'parasito',
    ]);
    expect(seccionesExamenDirecto({ tipo_estudio: 'UROCULTIVO' })).toEqual([]);
  });

  it('solapa siempre es examen microscópico directo', () => {
    expect(tituloUiExamenFresco({ tipo_estudio: 'ESPUTO' })).toBe(TITULO_APARTADO_UI);
    expect(tituloUiExamenFresco({ tipo_estudio: 'VAGINAL' })).toBe(TITULO_APARTADO_UI);
  });

  it('admite por flag o tipo_estudio', () => {
    expect(estudioAdmiteExamenFresco({ admite_examen_fresco: true })).toBe(true);
    expect(estudioAdmiteExamenFresco({ tipo_estudio: 'HEMOCULTIVO' })).toBe(true);
    expect(estudioAdmiteExamenFresco({ tipo_estudio: 'HONGOS_UNAS' })).toBe(true);
    expect(estudioAdmiteExamenFresco({ tipo_estudio: 'UROCULTIVO' })).toBe(false);
  });
});
