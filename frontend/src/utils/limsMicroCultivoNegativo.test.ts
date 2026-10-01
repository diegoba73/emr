import {
  TEXTO_INFORME_FINAL_SIN_DESARROLLO,
  cultivoNegativoElegibleParaInformeFinal,
  textoInformeFinalSinDesarrollo,
  todasLecturasSinDesarrollo,
} from './limsMicroCultivoNegativo';
import type { LecturaCultivo } from '../types/lims';

function lec(crecimiento: string, id = 1, recuento = ''): LecturaCultivo {
  return {
    id,
    estudio: 1,
    siembra: 1,
    crecimiento,
    recuento_bacteriano: recuento,
  } as LecturaCultivo;
}

describe('limsMicroCultivoNegativo', () => {
  it('texto base menciona ausencia de desarrollo', () => {
    expect(TEXTO_INFORME_FINAL_SIN_DESARROLLO).toMatch(/desarrollo bacteriano/i);
  });

  it('elegible con SIN_DESARROLLO y sin aislados', () => {
    expect(cultivoNegativoElegibleParaInformeFinal([lec('SIN_DESARROLLO')], [])).toBe(true);
  });

  it('no elegible sin lectura SIN_DESARROLLO', () => {
    expect(cultivoNegativoElegibleParaInformeFinal([lec('ESCASO')], [])).toBe(false);
  });

  it('bloquea si hay aislado SOSPECHADO significativo', () => {
    expect(
      cultivoNegativoElegibleParaInformeFinal(
        [lec('SIN_DESARROLLO')],
        [{ id: 1, estudio: 1, estado: 'SOSPECHADO', significancia: 'SIGNIFICATIVO' } as never]
      )
    ).toBe(false);
  });

  it('bloquea IDENTIFICADO que requiere AB', () => {
    expect(
      cultivoNegativoElegibleParaInformeFinal(
        [lec('SIN_DESARROLLO')],
        [
          {
            id: 1,
            estudio: 1,
            estado: 'IDENTIFICADO',
            requiere_antibiograma: true,
          } as never,
        ]
      )
    ).toBe(false);
  });

  it('todasLecturasSinDesarrollo', () => {
    expect(todasLecturasSinDesarrollo([lec('SIN_DESARROLLO'), lec('SIN_DESARROLLO', 2)])).toBe(
      true
    );
    expect(todasLecturasSinDesarrollo([lec('SIN_DESARROLLO'), lec('ESCASO', 2)])).toBe(false);
  });

  it('texto de conclusión no incluye recuento', () => {
    expect(textoInformeFinalSinDesarrollo([lec('SIN_DESARROLLO', 1, '<10³ UFC/ml')])).toBe(
      TEXTO_INFORME_FINAL_SIN_DESARROLLO
    );
    expect(textoInformeFinalSinDesarrollo([lec('SIN_DESARROLLO')])).toBe(
      TEXTO_INFORME_FINAL_SIN_DESARROLLO
    );
  });
});
