import {
  TEXTO_INFORME_FINAL_SIN_DESARROLLO,
  cultivoNegativoElegibleParaInformeFinal,
  todasLecturasSinDesarrollo,
} from './limsMicroCultivoNegativo';
import type { AisladoMicrobiologico, LecturaCultivo } from '../types/lims';

function lec(crecimiento: string, id = 1): LecturaCultivo {
  return { id, estudio: 1, siembra: 1, crecimiento } as LecturaCultivo;
}

function aislado(partial: Partial<AisladoMicrobiologico>): AisladoMicrobiologico {
  return {
    id: 1,
    estudio: 1,
    estado: 'SOSPECHADO',
    significancia: 'SIGNIFICATIVO',
    ...partial,
  } as AisladoMicrobiologico;
}

describe('limsMicroCultivoNegativo', () => {
  it('plantilla de texto definida', () => {
    expect(TEXTO_INFORME_FINAL_SIN_DESARROLLO).toMatch(/patógenos/i);
  });

  it('elegible con SIN_DESARROLLO y sin aislados', () => {
    expect(cultivoNegativoElegibleParaInformeFinal([lec('SIN_DESARROLLO')], [])).toBe(true);
  });

  it('no elegible sin lectura SIN_DESARROLLO', () => {
    expect(cultivoNegativoElegibleParaInformeFinal([lec('MODERADO')], [])).toBe(false);
  });

  it('no elegible con SOSPECHADO significativo', () => {
    expect(
      cultivoNegativoElegibleParaInformeFinal(
        [lec('SIN_DESARROLLO')],
        [aislado({ estado: 'SOSPECHADO', significancia: 'SIGNIFICATIVO' })]
      )
    ).toBe(false);
  });

  it('elegible con SOSPECHADO flora habitual', () => {
    expect(
      cultivoNegativoElegibleParaInformeFinal(
        [lec('SIN_DESARROLLO')],
        [aislado({ estado: 'SOSPECHADO', significancia: 'FLORA_HABITUAL' })]
      )
    ).toBe(true);
  });

  it('todasLecturasSinDesarrollo', () => {
    expect(todasLecturasSinDesarrollo([lec('SIN_DESARROLLO'), lec('SIN_DESARROLLO', 2)])).toBe(
      true
    );
    expect(todasLecturasSinDesarrollo([lec('SIN_DESARROLLO'), lec('ESCASO', 2)])).toBe(false);
    expect(todasLecturasSinDesarrollo([])).toBe(false);
  });
});
